"""Unit tests for src/new_filenames.py."""

import json
import sys
import textwrap
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import new_filenames


def _write_index(tmp_path, filenames):
    idx = {fn: {"id": str(i), "drive_path": fn, "modified": ""} for i, fn in enumerate(filenames)}
    p = tmp_path / "drive-index.json"
    p.write_text(json.dumps(idx) + "\n")
    return p


def _write_yaml(tmp_path, content):
    p = tmp_path / "tanzpalast.yaml"
    p.write_text(textwrap.dedent(content))
    return p


class TestExistingFilenames:
    def test_extracts_filename_entries(self, tmp_path):
        p = _write_yaml(tmp_path, """\
            - dance: Waltz
              videos:
                - filename: waltz.mov
                  title: Waltz
                  tags: [international]
        """)
        assert new_filenames.existing_filenames(p) == {"waltz.mov"}

    def test_ignores_url_entries(self, tmp_path):
        p = _write_yaml(tmp_path, """\
            - dance: Waltz
              videos:
                - url: https://youtu.be/abc
                  title: Waltz
                  tags: [international]
        """)
        assert new_filenames.existing_filenames(p) == set()

    def test_empty_yaml(self, tmp_path):
        p = _write_yaml(tmp_path, "- dance: Waltz\n  videos: []\n")
        assert new_filenames.existing_filenames(p) == set()


class TestNewFilenames:
    def test_returns_filenames_not_in_yaml(self, tmp_path):
        idx = _write_index(tmp_path, ["a.mov", "b.mov", "c.mov"])
        yaml_path = _write_yaml(tmp_path, """\
            - dance: Waltz
              videos:
                - filename: a.mov
                  title: A
                  tags: []
        """)
        result = new_filenames.new_filenames(idx, yaml_path)
        assert result == ["b.mov", "c.mov"]

    def test_returns_sorted(self, tmp_path):
        idx = _write_index(tmp_path, ["z.mov", "a.mov", "m.mov"])
        yaml_path = _write_yaml(tmp_path, "- dance: Waltz\n  videos: []\n")
        result = new_filenames.new_filenames(idx, yaml_path)
        assert result == ["a.mov", "m.mov", "z.mov"]

    def test_all_known_returns_empty(self, tmp_path):
        idx = _write_index(tmp_path, ["a.mov"])
        yaml_path = _write_yaml(tmp_path, """\
            - dance: Waltz
              videos:
                - filename: a.mov
                  title: A
                  tags: []
        """)
        assert new_filenames.new_filenames(idx, yaml_path) == []

    def test_missing_index_exits(self, tmp_path):
        yaml_path = _write_yaml(tmp_path, "- dance: Waltz\n  videos: []\n")
        with pytest.raises(SystemExit):
            new_filenames.new_filenames(tmp_path / "nonexistent.json", yaml_path)
