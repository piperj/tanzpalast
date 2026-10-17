"""Unit tests for src/compact_video.py."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import compact_video


def _probe_json(width, height, bit_rate, size, duration=10.0):
    return json.dumps({
        "streams": [{"width": width, "height": height}],
        "format": {"bit_rate": str(bit_rate), "size": str(size), "duration": str(duration)},
    })


class TestProbe:
    def test_parses_ffprobe_json(self):
        with patch("compact_video.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = _probe_json(1920, 1080, 11_000_000, 80_000_000, 42.5)
            info = compact_video._probe(Path("clip.mov"))
        assert info == {"width": 1920, "height": 1080, "bit_rate": 11_000_000,
                         "size": 80_000_000, "duration": 42.5}

    def test_returns_none_on_ffprobe_failure(self):
        with patch("compact_video.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            info = compact_video._probe(Path("clip.mov"))
        assert info is None

    def test_returns_none_on_malformed_json(self):
        with patch("compact_video.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "{}"
            info = compact_video._probe(Path("clip.mov"))
        assert info is None


class TestNeedsCompaction:
    def test_flags_4k_resolution(self):
        info = {"width": 3840, "height": 2160, "bit_rate": 25_000_000}
        assert compact_video.needs_compaction(info, max_edge=1920, bitrate_threshold=8_000_000)

    def test_flags_overbitrated_1080p(self):
        info = {"width": 1920, "height": 1080, "bit_rate": 11_000_000}
        assert compact_video.needs_compaction(info, max_edge=1920, bitrate_threshold=8_000_000)

    def test_skips_efficient_720p_portrait(self):
        info = {"width": 720, "height": 1280, "bit_rate": 3_100_000}
        assert not compact_video.needs_compaction(info, max_edge=1920, bitrate_threshold=8_000_000)

    def test_checks_long_edge_regardless_of_orientation(self):
        info = {"width": 2160, "height": 3840, "bit_rate": 5_000_000}
        assert compact_video.needs_compaction(info, max_edge=1920, bitrate_threshold=8_000_000)


class TestTargetDims:
    def test_downscales_4k_landscape_to_1080p(self):
        info = {"width": 3840, "height": 2160}
        assert compact_video._target_dims(info, max_edge=1920) == (1920, 1080)

    def test_leaves_portrait_1080p_untouched(self):
        info = {"width": 1080, "height": 1920}
        assert compact_video._target_dims(info, max_edge=1920) == (1080, 1920)

    def test_leaves_already_small_video_untouched(self):
        info = {"width": 720, "height": 1280}
        assert compact_video._target_dims(info, max_edge=1920) == (720, 1280)

    def test_rounds_to_even_dimensions(self):
        info = {"width": 3000, "height": 1690}
        w, h = compact_video._target_dims(info, max_edge=1920)
        assert w % 2 == 0 and h % 2 == 0


class TestCompact:
    def _fake_ffmpeg_then_probe(self, out_duration, out_bytes=b"compacted bytes"):
        """subprocess.run side_effect: first call is ffmpeg (writes tmp), second is the
        post-encode ffprobe validation call."""
        def run(cmd, **kwargs):
            if cmd[0] == "ffmpeg":
                tmp = Path(cmd[-1])
                tmp.write_bytes(out_bytes)
                result = MagicMock()
                result.returncode = 0
                return result
            result = MagicMock()
            result.returncode = 0
            result.stdout = _probe_json(1920, 1080, 5_000_000, len(out_bytes), out_duration)
            return result
        return run

    def test_replaces_source_on_success(self, tmp_path):
        src = tmp_path / "clip.mov"
        src.write_bytes(b"original bytes")
        info = {"width": 3840, "height": 2160, "duration": 10.0}

        with patch("compact_video.subprocess.run", side_effect=self._fake_ffmpeg_then_probe(10.0)):
            ok = compact_video._compact(src, info, max_edge=1920, crf=21, preset="medium")

        assert ok is True
        assert src.read_bytes() == b"compacted bytes"
        assert not (tmp_path / "clip.compact.mov").exists()

    def test_leaves_source_untouched_on_ffmpeg_failure(self, tmp_path):
        src = tmp_path / "clip.mov"
        src.write_bytes(b"original bytes")
        info = {"width": 3840, "height": 2160, "duration": 10.0}

        with patch("compact_video.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = b"ffmpeg exploded"
            ok = compact_video._compact(src, info, max_edge=1920, crf=21, preset="medium")

        assert ok is False
        assert src.read_bytes() == b"original bytes"
        assert not (tmp_path / "clip.compact.mov").exists()

    def test_leaves_source_untouched_on_timeout(self, tmp_path):
        src = tmp_path / "clip.mov"
        src.write_bytes(b"original bytes")
        info = {"width": 3840, "height": 2160, "duration": 10.0}

        import subprocess as subprocess_module

        with patch("compact_video.subprocess.run",
                   side_effect=subprocess_module.TimeoutExpired(cmd="ffmpeg", timeout=5)):
            ok = compact_video._compact(src, info, max_edge=1920, crf=21, preset="medium", timeout=5)

        assert ok is False
        assert src.read_bytes() == b"original bytes"
        assert not (tmp_path / "clip.compact.mov").exists()

    def test_rejects_output_with_drifted_duration(self, tmp_path):
        """ffmpeg exits 0 but the output is a truncated/garbage encode — caught
        by comparing durations before the swap is allowed."""
        src = tmp_path / "clip.mov"
        src.write_bytes(b"original bytes")
        info = {"width": 3840, "height": 2160, "duration": 100.0}

        with patch("compact_video.subprocess.run", side_effect=self._fake_ffmpeg_then_probe(5.0)):
            ok = compact_video._compact(src, info, max_edge=1920, crf=21, preset="medium")

        assert ok is False
        assert src.read_bytes() == b"original bytes"
        assert not (tmp_path / "clip.compact.mov").exists()

    def test_rejects_unreadable_output(self, tmp_path):
        src = tmp_path / "clip.mov"
        src.write_bytes(b"original bytes")
        info = {"width": 3840, "height": 2160, "duration": 10.0}

        def run(cmd, **kwargs):
            if cmd[0] == "ffmpeg":
                Path(cmd[-1]).write_bytes(b"garbage")
                result = MagicMock()
                result.returncode = 0
                return result
            result = MagicMock()
            result.returncode = 1  # ffprobe can't read the garbage output
            return result

        with patch("compact_video.subprocess.run", side_effect=run):
            ok = compact_video._compact(src, info, max_edge=1920, crf=21, preset="medium")

        assert ok is False
        assert src.read_bytes() == b"original bytes"
        assert not (tmp_path / "clip.compact.mov").exists()

    def test_clears_stale_leftover_before_encoding(self, tmp_path):
        src = tmp_path / "clip.mov"
        src.write_bytes(b"original bytes")
        stale = tmp_path / "clip.compact.mov"
        stale.write_bytes(b"leftover from a crashed run")
        info = {"width": 3840, "height": 2160, "duration": 10.0}

        with patch("compact_video.subprocess.run", side_effect=self._fake_ffmpeg_then_probe(10.0)):
            ok = compact_video._compact(src, info, max_edge=1920, crf=21, preset="medium")

        assert ok is True
        assert src.read_bytes() == b"compacted bytes"


class TestCollectSources:
    def test_finds_mov_files_case_insensitively(self, tmp_path, monkeypatch):
        (tmp_path / "a.mov").write_bytes(b"x")
        (tmp_path / "b.MOV").write_bytes(b"x")
        (tmp_path / "c.mp4").write_bytes(b"x")
        monkeypatch.setattr(compact_video, "DATA_DIR", tmp_path)
        try:
            names = {p.name for p in compact_video.collect_sources()}
            assert names == {"a.mov", "b.MOV"}
        finally:
            monkeypatch.undo()

    def test_excludes_stray_compact_temp_files(self, tmp_path, monkeypatch):
        (tmp_path / "a.mov").write_bytes(b"x")
        (tmp_path / "a.compact.mov").write_bytes(b"x")
        monkeypatch.setattr(compact_video, "DATA_DIR", tmp_path)
        try:
            names = {p.name for p in compact_video.collect_sources()}
            assert names == {"a.mov"}
        finally:
            monkeypatch.undo()
