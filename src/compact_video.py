#!/usr/bin/env python3
"""Re-encode oversized local .mov sources in data/ down to a sane size.

Scans data/ for .mov/.MOV files whose long edge exceeds --max-edge or whose
bitrate exceeds --bitrate-threshold, and re-encodes each in place (same
filename, same extension) at CRF-based quality capped to --max-edge on the
long edge. Frame rate is left untouched — dance footage has fast rotational
motion and dropping fps is visibly worse than it's worth. Files that are
already small/efficient (e.g. the typical 720x1280 @ ~3.1Mbps phone clips)
are skipped automatically.

Output stays in the same container (.mov/.MOV) so tanzpalast.yaml's
`filename:` references need no changes — the file is swapped in place.

Atomicity: ffmpeg writes to a sibling `*.compact.mov` temp file; the source
is never opened for writing. The temp output is validated (readable, size>0,
duration within 10% of the source) before an atomic rename swaps it over the
original. A hang is bounded by --timeout (kills ffmpeg, original untouched).
Worst case on any failure is a stray `.compact` leftover next to the source,
which the next run's scan ignores and ffmpeg's `-y` overwrites on retry.

Usage:
    uv run python src/compact_video.py              # compact all candidates
    uv run python src/compact_video.py --dry-run     # list candidates only
    uv run python src/compact_video.py --force       # re-process everything
    uv run python src/compact_video.py --file data/x.mov
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

DEFAULT_MAX_EDGE = 1920
DEFAULT_BITRATE_THRESHOLD = 8_000_000  # bits/sec
DEFAULT_CRF = 21
DEFAULT_PRESET = "medium"
DEFAULT_TIMEOUT = 1800  # seconds; a hung/stalled ffmpeg gets killed rather than hanging forever
DURATION_TOLERANCE = 0.1  # fraction; reject an output whose duration drifts more than this from the source


def _probe(src: Path) -> dict | None:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height",
         "-show_entries", "format=bit_rate,size,duration",
         "-of", "json", str(src)],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    try:
        data = json.loads(result.stdout)
        stream = data["streams"][0]
        fmt = data["format"]
        return {
            "width": int(stream["width"]),
            "height": int(stream["height"]),
            "bit_rate": int(fmt["bit_rate"]),
            "size": int(fmt["size"]),
            "duration": float(fmt["duration"]),
        }
    except (KeyError, IndexError, ValueError):
        return None


def needs_compaction(info: dict, max_edge: int, bitrate_threshold: int) -> bool:
    long_edge = max(info["width"], info["height"])
    return long_edge > max_edge or info["bit_rate"] > bitrate_threshold


def _target_dims(info: dict, max_edge: int) -> tuple[int, int]:
    width, height = info["width"], info["height"]
    long_edge = max(width, height)
    if long_edge <= max_edge:
        return width, height
    scale = max_edge / long_edge
    new_w = round(width * scale / 2) * 2
    new_h = round(height * scale / 2) * 2
    return new_w, new_h


def _compact(src: Path, info: dict, max_edge: int, crf: int, preset: str,
             timeout: int = DEFAULT_TIMEOUT) -> bool:
    """Encode to a sibling temp file and only swap it over `src` once it
    verifiably succeeded. `src` is never opened for writing, so a hung,
    killed, or garbage-producing ffmpeg run can't corrupt the original —
    worst case it leaves a `.compact` leftover next to it, which the next
    `collect_sources()` scan ignores.
    """
    width, height = _target_dims(info, max_edge)
    tmp = src.parent / f"{src.stem}.compact{src.suffix}"
    tmp.unlink(missing_ok=True)  # clear any stale leftover from a prior crash

    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", str(src),
             "-vf", f"scale={width}:{height}",
             "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
             "-c:a", "aac", "-b:a", "128k",
             str(tmp)],
            capture_output=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"  ✗ ffmpeg timed out after {timeout}s: {src.name}", file=sys.stderr)
        tmp.unlink(missing_ok=True)
        return False

    if result.returncode != 0 or not tmp.exists():
        print(result.stderr.decode()[-500:], file=sys.stderr)
        tmp.unlink(missing_ok=True)
        return False

    # Guard against a "successful" ffmpeg exit that wrote a truncated/garbage
    # file — verify the output is a playable video of roughly the right length
    # before it's allowed anywhere near the original.
    out_info = _probe(tmp)
    if out_info is None or out_info["size"] == 0:
        print(f"  ✗ output failed validation (unreadable): {src.name}", file=sys.stderr)
        tmp.unlink(missing_ok=True)
        return False
    drift = abs(out_info["duration"] - info["duration"]) / max(info["duration"], 0.001)
    if drift > DURATION_TOLERANCE:
        print(f"  ✗ output failed validation (duration {out_info['duration']:.1f}s vs "
              f"source {info['duration']:.1f}s): {src.name}", file=sys.stderr)
        tmp.unlink(missing_ok=True)
        return False

    tmp.replace(src)  # atomic rename on the same filesystem — no partial-write window
    return True


def collect_sources():
    return sorted(
        p for p in DATA_DIR.iterdir()
        if p.suffix.lower() == ".mov" and p.is_file() and ".compact" not in p.name
    )


def main():
    parser = argparse.ArgumentParser(description="Compact oversized local .mov sources")
    parser.add_argument("--max-edge", type=int, default=DEFAULT_MAX_EDGE,
                        help=f"cap the long edge to this many pixels (default: {DEFAULT_MAX_EDGE})")
    parser.add_argument("--bitrate-threshold", type=int, default=DEFAULT_BITRATE_THRESHOLD,
                        help=f"re-encode if bitrate exceeds this, in bits/sec (default: {DEFAULT_BITRATE_THRESHOLD})")
    parser.add_argument("--crf", type=int, default=DEFAULT_CRF,
                        help=f"x264 CRF, lower = higher quality (default: {DEFAULT_CRF})")
    parser.add_argument("--preset", default=DEFAULT_PRESET,
                        help=f"x264 preset (default: {DEFAULT_PRESET})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"kill ffmpeg if a single file takes longer than this, in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--force", action="store_true",
                        help="re-process files even if they don't exceed the thresholds")
    parser.add_argument("--dry-run", action="store_true",
                        help="list candidates and estimated savings without encoding")
    parser.add_argument("--file", metavar="PATH",
                        help="process a single .mov file (skips the data/ scan)")
    args = parser.parse_args()

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print("ERROR: ffmpeg/ffprobe not found — brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    sources = [Path(args.file)] if args.file else collect_sources()
    if not sources:
        print("No .mov sources found in data/")
        return

    done = skipped = err = 0
    before_total = after_total = 0

    for src in sources:
        if not src.exists():
            print(f"  ✗ missing: {src}", file=sys.stderr)
            err += 1
            continue

        info = _probe(src)
        if info is None:
            print(f"  ✗ ffprobe failed: {src.name}", file=sys.stderr)
            err += 1
            continue

        if not args.force and not needs_compaction(info, args.max_edge, args.bitrate_threshold):
            skipped += 1
            continue

        before = info["size"]
        if args.dry_run:
            target_w, target_h = _target_dims(info, args.max_edge)
            print(f"  would compact: {src.name}  "
                  f"({info['width']}x{info['height']} @ {info['bit_rate']/1e6:.1f}Mbps, {before/1e6:.0f}MB)"
                  f"  -> {target_w}x{target_h}")
            done += 1
            before_total += before
            continue

        print(f"  compacting: {src.name} ({before/1e6:.0f}MB)...")
        if _compact(src, info, args.max_edge, args.crf, args.preset, args.timeout):
            after = src.stat().st_size
            before_total += before
            after_total += after
            pct = 100 * (1 - after / before)
            print(f"  ✓ {src.name}: {before/1e6:.0f}MB -> {after/1e6:.0f}MB ({pct:.0f}% smaller)")
            done += 1
        else:
            print(f"  ✗ failed, original untouched: {src.name}")
            err += 1

    verb = "would compact" if args.dry_run else "compacted"
    print(f"\n{done} {verb}, {skipped} skipped (already compact), {err} errors")
    if before_total:
        if args.dry_run:
            print(f"estimated size: {before_total/1e6:.0f}MB of source material flagged")
        else:
            print(f"total: {before_total/1e6:.0f}MB -> {after_total/1e6:.0f}MB "
                  f"({100 * (1 - after_total / before_total):.0f}% smaller)")


if __name__ == "__main__":
    main()
