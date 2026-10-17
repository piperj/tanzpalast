"""Unit tests for src/list_drive.py."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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
            "root": [{"id": "abc", "name": "waltz.mov", "mimeType": "video/quicktime", "modifiedTime": ""}]
        })
        result = list_drive.list_videos(service, "root")
        assert len(result) == 1
        assert result[0]["name"] == "waltz.mov"
        assert result[0]["id"] == "abc"

    def test_skips_non_video_files(self):
        service = _make_service({
            "root": [{"id": "x", "name": "readme.txt", "mimeType": "text/plain", "modifiedTime": ""}]
        })
        assert list_drive.list_videos(service, "root") == []

    def test_recurses_into_subfolders(self):
        service = _make_service({
            "root": [{"id": "sub", "name": "Waltz", "mimeType": "application/vnd.google-apps.folder", "modifiedTime": ""}],
            "sub": [{"id": "vid", "name": "waltz.mov", "mimeType": "video/quicktime", "modifiedTime": ""}],
        })
        result = list_drive.list_videos(service, "root")
        assert len(result) == 1
        assert result[0]["drive_path"] == "Waltz/waltz.mov"

    def test_drive_path_flat(self):
        service = _make_service({
            "root": [{"id": "v", "name": "foo.mov", "mimeType": "video/mp4", "modifiedTime": ""}]
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
            {"name": "a.mov", "id": "1", "drive_path": "Waltz/a.mov", },
            {"name": "a.mov", "id": "2", "drive_path": "Tango/a.mov", },
        ]
        with pytest.raises(SystemExit):
            list_drive.write_index(items, path=tmp_path / "idx.json")

    def test_ends_with_newline(self, tmp_path):
        items = [{"name": "b.mov", "id": "99", "drive_path": "b.mov", }]
        out = tmp_path / "idx.json"
        list_drive.write_index(items, path=out)
        assert out.read_text().endswith("\n")


class TestGetRootId:
    def test_returns_env_var(self, monkeypatch):
        monkeypatch.setenv("TANZPALAST_DRIVE_ROOT", "root-id")
        assert list_drive.get_root_id() == "root-id"

    def test_returns_none_when_unset(self, monkeypatch):
        monkeypatch.delenv("TANZPALAST_DRIVE_ROOT", raising=False)
        assert list_drive.get_root_id() is None


class TestWaitForSync:
    def test_returns_true_when_all_names_present_immediately(self, monkeypatch):
        monkeypatch.setenv("TANZPALAST_DRIVE_ROOT", "root-id")
        with patch("list_drive.get_drive_service"), \
             patch("list_drive.list_videos", return_value=[
                 {"name": "a.mov", "id": "1", "drive_path": "a.mov"},
                 {"name": "b.mov", "id": "2", "drive_path": "b.mov"},
             ]), \
             patch("list_drive.write_index", side_effect=lambda items: {i["name"]: i for i in items}):
            ok = list_drive.wait_for_sync({"a.mov", "b.mov"}, timeout=60)
        assert ok is True

    def test_polls_until_name_appears(self, monkeypatch):
        monkeypatch.setenv("TANZPALAST_DRIVE_ROOT", "root-id")
        responses = [
            [{"name": "a.mov", "id": "1", "drive_path": "a.mov"}],
            [{"name": "a.mov", "id": "1", "drive_path": "a.mov"},
             {"name": "b.mov", "id": "2", "drive_path": "b.mov"}],
        ]
        with patch("list_drive.get_drive_service"), \
             patch("list_drive.list_videos", side_effect=responses), \
             patch("list_drive.write_index", side_effect=lambda items: {i["name"]: i for i in items}), \
             patch("list_drive.time.sleep") as mock_sleep:
            ok = list_drive.wait_for_sync({"a.mov", "b.mov"}, timeout=60, poll_interval=5)
        assert ok is True
        mock_sleep.assert_called_once_with(5)

    def test_returns_false_on_timeout(self, monkeypatch):
        monkeypatch.setenv("TANZPALAST_DRIVE_ROOT", "root-id")
        with patch("list_drive.get_drive_service"), \
             patch("list_drive.list_videos", return_value=[]), \
             patch("list_drive.write_index", return_value={}), \
             patch("list_drive.time.sleep"), \
             patch("list_drive.time.monotonic", side_effect=[0, 100, 200]):
            ok = list_drive.wait_for_sync({"a.mov"}, timeout=60, poll_interval=5)
        assert ok is False

    def test_returns_false_without_drive_root_set(self, monkeypatch):
        monkeypatch.delenv("TANZPALAST_DRIVE_ROOT", raising=False)
        ok = list_drive.wait_for_sync({"a.mov"}, timeout=60)
        assert ok is False
