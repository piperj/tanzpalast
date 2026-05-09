"""Unit tests for src/apply_insert.py."""

import json
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import apply_insert


WALTZ_YAML = textwrap.dedent("""\
    # Tanzpalast — video diary
    - dance: Waltz
      videos:
        - filename: waltz_smooth.mov
          title: Waltz · Smooth
          tags: [smooth]
        - url: https://youtu.be/abc
          title: Waltz · YouTube
          tags: [international]
""")


def _plan(dance="Waltz", create_new=False, filename="waltz_new.mov",
          title="Waltz · New", tags="[new, international]"):
    block = f"- filename: {filename}\n  title: {title}\n  tags: {tags}\n"
    return json.dumps({
        "dance": dance,
        "create_new_dance": create_new,
        "yaml_block": block,
        "rationale": "test",
    })


class TestApplyInsert:
    def test_inserts_under_existing_dance(self, tmp_path):
        p = tmp_path / "tanzpalast.yaml"
        p.write_text(WALTZ_YAML)
        apply_insert.apply_insert(_plan(), yaml_path=p)
        data = yaml.safe_load(p.read_text())
        filenames = [v.get("filename") for v in data[0]["videos"]]
        assert "waltz_new.mov" in filenames

    def test_preserves_existing_entries(self, tmp_path):
        p = tmp_path / "tanzpalast.yaml"
        p.write_text(WALTZ_YAML)
        apply_insert.apply_insert(_plan(), yaml_path=p)
        data = yaml.safe_load(p.read_text())
        fns = [v.get("filename") or v.get("url") for v in data[0]["videos"]]
        assert "waltz_smooth.mov" in fns
        assert "https://youtu.be/abc" in fns

    def test_preserves_header_comment(self, tmp_path):
        p = tmp_path / "tanzpalast.yaml"
        p.write_text(WALTZ_YAML)
        apply_insert.apply_insert(_plan(), yaml_path=p)
        assert "# Tanzpalast" in p.read_text()

    def test_create_new_dance(self, tmp_path):
        p = tmp_path / "tanzpalast.yaml"
        p.write_text(WALTZ_YAML)
        apply_insert.apply_insert(
            _plan(dance="Tango", create_new=True, filename="tango_new.mov",
                  title="Tango · New", tags="[new, international]"),
            yaml_path=p,
        )
        data = yaml.safe_load(p.read_text())
        dances = [e["dance"] for e in data]
        assert "Tango" in dances
        tango = next(e for e in data if e["dance"] == "Tango")
        assert tango["videos"][0]["filename"] == "tango_new.mov"

    def test_create_new_fails_if_dance_exists(self, tmp_path):
        p = tmp_path / "tanzpalast.yaml"
        p.write_text(WALTZ_YAML)
        with pytest.raises(SystemExit):
            apply_insert.apply_insert(
                _plan(dance="Waltz", create_new=True, filename="x.mov"),
                yaml_path=p,
            )

    def test_insert_fails_if_dance_not_found(self, tmp_path):
        p = tmp_path / "tanzpalast.yaml"
        p.write_text(WALTZ_YAML)
        with pytest.raises(SystemExit):
            apply_insert.apply_insert(
                _plan(dance="Tango", create_new=False, filename="x.mov"),
                yaml_path=p,
            )

    def test_invalid_json_exits(self, tmp_path):
        p = tmp_path / "tanzpalast.yaml"
        p.write_text(WALTZ_YAML)
        with pytest.raises(SystemExit):
            apply_insert.apply_insert("not json", yaml_path=p)

    def test_malformed_yaml_block_exits(self, tmp_path):
        p = tmp_path / "tanzpalast.yaml"
        p.write_text(WALTZ_YAML)
        bad = json.dumps({"dance": "Waltz", "create_new_dance": False,
                          "yaml_block": ":::bad yaml:::", "rationale": ""})
        with pytest.raises(SystemExit):
            apply_insert.apply_insert(bad, yaml_path=p)

    def test_failure_logged(self, tmp_path):
        p = tmp_path / "tanzpalast.yaml"
        p.write_text(WALTZ_YAML)
        log = tmp_path / "data" / "scan-failures.log"
        # Monkey-patch the log path
        original = apply_insert.FAILURES_LOG
        apply_insert.FAILURES_LOG = log
        try:
            with pytest.raises(SystemExit):
                apply_insert.apply_insert("not json", yaml_path=p)
        finally:
            apply_insert.FAILURES_LOG = original
        assert log.exists()
        assert "invalid JSON" in log.read_text().lower() or len(log.read_text()) > 0

    def test_strips_markdown_code_fences(self, tmp_path):
        p = tmp_path / "tanzpalast.yaml"
        p.write_text(WALTZ_YAML)
        fenced = "```json\n" + _plan() + "\n```"
        apply_insert.apply_insert(fenced, yaml_path=p)
        data = yaml.safe_load(p.read_text())
        filenames = [v.get("filename") for v in data[0]["videos"]]
        assert "waltz_new.mov" in filenames

    def test_yaml_unchanged_on_failure(self, tmp_path):
        p = tmp_path / "tanzpalast.yaml"
        p.write_text(WALTZ_YAML)
        original_text = WALTZ_YAML
        with pytest.raises(SystemExit):
            apply_insert.apply_insert("not json", yaml_path=p)
        assert p.read_text() == original_text
