"""Unit tests for src/make_thumbnails.py."""

import sys
from pathlib import Path
from unittest.mock import call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import make_thumbnails


class TestDuration:
    def test_returns_float_on_success(self):
        with patch("make_thumbnails.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "8.5\n"
            assert make_thumbnails._duration(Path("clip.mov")) == pytest.approx(8.5)

    def test_returns_none_on_bad_output(self):
        with patch("make_thumbnails.subprocess.run") as mock_run:
            mock_run.return_value.stdout = "N/A\n"
            assert make_thumbnails._duration(Path("clip.mov")) is None


class TestExtract:
    def _mock_run(self, duration=None, ffmpeg_rc=0):
        """Return a side_effect callable that handles both ffprobe and ffmpeg calls."""
        calls = []

        def run(cmd, **kwargs):
            from unittest.mock import MagicMock
            result = MagicMock()
            if "ffprobe" in cmd[0]:
                result.stdout = f"{duration}\n" if duration is not None else "N/A\n"
                result.returncode = 0
            else:
                result.returncode = ffmpeg_rc
                result.stderr = b""
            calls.append(cmd)
            return result

        return run, calls

    def test_uses_requested_timestamp_for_long_video(self):
        side_effect, calls = self._mock_run(duration=30.0)
        with patch("make_thumbnails.subprocess.run", side_effect=side_effect):
            make_thumbnails._extract(Path("clip.mov"), Path("out.jpg"), at=12.0)
        ffmpeg_call = calls[1]
        assert "-ss" in ffmpeg_call
        assert ffmpeg_call[ffmpeg_call.index("-ss") + 1] == "12.0"

    def test_falls_back_to_midpoint_when_at_exceeds_duration(self):
        side_effect, calls = self._mock_run(duration=8.0)
        with patch("make_thumbnails.subprocess.run", side_effect=side_effect):
            make_thumbnails._extract(Path("clip.mov"), Path("out.jpg"), at=12.0)
        ffmpeg_call = calls[1]
        used_at = float(ffmpeg_call[ffmpeg_call.index("-ss") + 1])
        assert used_at == pytest.approx(4.0)  # 8.0 * 0.5

    def test_falls_back_when_at_equals_duration(self):
        side_effect, calls = self._mock_run(duration=12.0)
        with patch("make_thumbnails.subprocess.run", side_effect=side_effect):
            make_thumbnails._extract(Path("clip.mov"), Path("out.jpg"), at=12.0)
        ffmpeg_call = calls[1]
        used_at = float(ffmpeg_call[ffmpeg_call.index("-ss") + 1])
        assert used_at == pytest.approx(6.0)

    def test_clamps_to_zero_for_zero_duration_video(self):
        side_effect, calls = self._mock_run(duration=0.0)
        with patch("make_thumbnails.subprocess.run", side_effect=side_effect):
            make_thumbnails._extract(Path("clip.mov"), Path("out.jpg"), at=12.0)
        ffmpeg_call = calls[1]
        used_at = float(ffmpeg_call[ffmpeg_call.index("-ss") + 1])
        assert used_at == pytest.approx(0.0)

    def test_midpoint_for_sub_second_video(self):
        side_effect, calls = self._mock_run(duration=0.5)
        with patch("make_thumbnails.subprocess.run", side_effect=side_effect):
            make_thumbnails._extract(Path("clip.mov"), Path("out.jpg"), at=12.0)
        ffmpeg_call = calls[1]
        used_at = float(ffmpeg_call[ffmpeg_call.index("-ss") + 1])
        assert used_at == pytest.approx(0.25)

    def test_proceeds_when_duration_unknown(self):
        side_effect, calls = self._mock_run(duration=None)
        with patch("make_thumbnails.subprocess.run", side_effect=side_effect):
            make_thumbnails._extract(Path("clip.mov"), Path("out.jpg"), at=12.0)
        ffmpeg_call = calls[1]
        assert ffmpeg_call[ffmpeg_call.index("-ss") + 1] == "12.0"

    def test_returns_true_on_success(self):
        side_effect, _ = self._mock_run(duration=30.0, ffmpeg_rc=0)
        with patch("make_thumbnails.subprocess.run", side_effect=side_effect):
            assert make_thumbnails._extract(Path("clip.mov"), Path("out.jpg"), at=5.0) is True

    def test_returns_false_on_ffmpeg_failure(self):
        side_effect, _ = self._mock_run(duration=30.0, ffmpeg_rc=1)
        with patch("make_thumbnails.subprocess.run", side_effect=side_effect):
            assert make_thumbnails._extract(Path("clip.mov"), Path("out.jpg"), at=5.0) is False
