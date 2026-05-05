"""Unit tests for src/migrate_yaml.py."""

import json
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import migrate_yaml


MIXED_YAML = textwrap.dedent("""\
    - dance: Waltz
      videos:
        - title: Waltz · Drive
          url: https://drive.google.com/file/d/DRIVE_ID_1/view?usp=share_link
          thumbnail: "Waltz smooth.mov"
          tags: [smooth]
        - title: Waltz · YouTube
          url: https://youtu.be/abc
          tags: [international]
    - dance: Tango
      videos:
        - title: Tango · Drive
          url: https://drive.google.com/file/d/DRIVE_ID_2/view?usp=sharing
          thumbnail: "Tango smooth.mov"
          tags: [smooth]
""")

INDEX = {
    "Waltz smooth.mov": {"id": "DRIVE_ID_1", "drive_path": "Waltz/Waltz smooth.mov", "modified": ""},
    "Tango smooth.mov": {"id": "DRIVE_ID_2", "drive_path": "Tango/Tango smooth.mov", "modified": ""},
}


def _setup(tmp_path):
    yaml_path = tmp_path / "tanzpalast.yaml"
    yaml_path.write_text(MIXED_YAML)
    idx_path = tmp_path / "drive-index.json"
    idx_path.write_text(json.dumps(INDEX) + "\n")
    return yaml_path, idx_path


class TestMigrateYaml:
    def test_drive_entries_rewritten_to_filename(self, tmp_path):
        p, idx = _setup(tmp_path)
        migrate_yaml.migrate(yaml_path=p, index_path=idx)
        data = yaml.safe_load(p.read_text())
        waltz_vids = data[0]["videos"]
        drive_entry = waltz_vids[0]
        assert drive_entry.get("filename") == "Waltz smooth.mov"
        assert "url" not in drive_entry
        assert "thumbnail" not in drive_entry

    def test_youtube_entries_untouched(self, tmp_path):
        p, idx = _setup(tmp_path)
        migrate_yaml.migrate(yaml_path=p, index_path=idx)
        data = yaml.safe_load(p.read_text())
        yt = data[0]["videos"][1]
        assert yt["url"] == "https://youtu.be/abc"
        assert "filename" not in yt

    def test_idempotent(self, tmp_path):
        p, idx = _setup(tmp_path)
        migrate_yaml.migrate(yaml_path=p, index_path=idx)
        text_after_first = p.read_text()
        migrate_yaml.migrate(yaml_path=p, index_path=idx)
        assert p.read_text() == text_after_first

    def test_dry_run_does_not_write(self, tmp_path):
        p, idx = _setup(tmp_path)
        migrate_yaml.migrate(yaml_path=p, index_path=idx, dry_run=True)
        assert p.read_text() == MIXED_YAML

    def test_missing_index_exits(self, tmp_path):
        p, _ = _setup(tmp_path)
        with pytest.raises(SystemExit):
            migrate_yaml.migrate(yaml_path=p, index_path=tmp_path / "nonexistent.json")
