"""Unit tests for src/list_drive.py."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import list_drive


def _make_service(files_by_folder):
    """Build a mock Drive service that returns files_by_folder[folder_id]."""
    def list_execute(folder_id):
        mock_resp = MagicMock()
        mock_resp.execute.return_value = {"files": files_by_folder.get(folder_id, [])}
        return mock_resp

    mock_list = MagicMock(side_effect=lambda **kw: list_execute(
        kw["q"].split("'")[1]
    ))
    service = MagicMock()
    service.files.return_value.list = mock_list
    return service


class TestListVideos:
    def test_returns_video_files(self):
        service = _make_service({
            "root": [{"id": "abc", "name": "waltz.mov", "mimeType": "video/quicktime", "modifiedTime": "2024-01-01T00:00:00Z"}]
        })
        result = list_drive.list_videos(service, "root")
        assert len(result) == 1
        assert result[0]["name"] == "waltz.mov"
        assert result[0]["id"] == "abc"

    def test_skips_non_video_files(self):
        service = _make_service({
            "root": [{"id": "x", "name": "readme.txt", "mimeType": "text/plain", "modifiedTime": "2024-01-01T00:00:00Z"}]
        })
        assert list_drive.list_videos(service, "root") == []

    def test_recurses_into_subfolders(self):
        service = _make_service({
            "root": [{"id": "sub", "name": "Waltz", "mimeType": "application/vnd.google-apps.folder", "modifiedTime": ""}],
            "sub": [{"id": "vid", "name": "waltz.mov", "mimeType": "video/quicktime", "modifiedTime": "2024-01-01T00:00:00Z"}],
        })
        result = list_drive.list_videos(service, "root")
        assert len(result) == 1
        assert result[0]["drive_path"] == "Waltz/waltz.mov"

    def test_drive_path_flat(self):
        service = _make_service({
            "root": [{"id": "v", "name": "foo.mov", "mimeType": "video/mp4", "modifiedTime": "2024-01-01T00:00:00Z"}]
        })
        result = list_drive.list_videos(service, "root", path="")
        assert result[0]["drive_path"] == "foo.mov"


class TestWriteIndex:
    def test_writes_json(self, tmp_path):
        items = [{"name": "a.mov", "id": "1", "drive_path": "Waltz/a.mov", "modified": "2024-01-01T00:00:00Z"}]
        out = tmp_path / "drive-index.json"
        list_drive.write_index(items, path=out)
        data = json.loads(out.read_text())
        assert "a.mov" in data
        assert data["a.mov"]["id"] == "1"

    def test_errors_on_duplicate_filename(self, tmp_path):
        items = [
            {"name": "a.mov", "id": "1", "drive_path": "Waltz/a.mov", "modified": ""},
            {"name": "a.mov", "id": "2", "drive_path": "Tango/a.mov", "modified": ""},
        ]
        with pytest.raises(SystemExit):
            list_drive.write_index(items, path=tmp_path / "idx.json")

    def test_ends_with_newline(self, tmp_path):
        items = [{"name": "b.mov", "id": "99", "drive_path": "b.mov", "modified": ""}]
        out = tmp_path / "idx.json"
        list_drive.write_index(items, path=out)
        assert out.read_text().endswith("\n")
