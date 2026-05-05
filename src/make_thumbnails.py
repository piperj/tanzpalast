#!/usr/bin/env python3
"""Extract thumbnail frames from local .mov source files.

Reads tanzpalast.yaml for `filename:` (Drive) and legacy `thumbnail:` fields,
looks for the source .mov in data/, writes JPEG to thumbnails/.

Usage:
    uv run python src/make_thumbnails.py          # process all (skip existing)
    uv run python src/make_thumbnails.py --at 14  # choose timestamp
    uv run python src/make_thumbnails.py --force  # overwrite existing
    uv run python src/make_thumbnails.py --file data/waltz_smooth.mov
"""

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
YAML_PATH = ROOT / "tanzpalast.yaml"
DATA_DIR = ROOT / "data"
THUMB_DIR = ROOT / "thumbnails"


def _mov_slug(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r'[^a-z0-9]+', '-', stem.lower()).strip('-')


def _extract(src: Path, dest: Path, at: float) -> bool:
    result = subprocess.run(
        ["ffmpeg", "-y", "-ss", str(at), "-i", str(src),
         "-frames:v", "1", "-q:v", "2", str(dest)],
        capture_output=True,
    )
    if result.returncode != 0:
        print(result.stderr.decode()[-300:], file=sys.stderr)
    return result.returncode == 0


def collect_sources():
    """Return {mov_filename: slug} from tanzpalast.yaml."""
    with YAML_PATH.open() as f:
        dances = yaml.safe_load(f)
    sources = {}
    for entry in dances or []:
        for v in entry.get("videos") or []:
            mov = v.get("filename") or v.get("thumbnail")
            if mov and mov.lower().endswith(".mov") and mov not in sources:
                sources[mov] = _mov_slug(mov)
    return sources


def main():
    parser = argparse.ArgumentParser(description="Generate thumbnails from .mov files")
    parser.add_argument("--at", type=float, default=12.0, metavar="SECONDS",
                        help="timestamp to extract (default: 12)")
    parser.add_argument("--force", action="store_true", help="overwrite existing thumbnails")
    parser.add_argument("--file", metavar="PATH",
                        help="process a single .mov file (skips YAML scan)")
    args = parser.parse_args()

    if not shutil.which("ffmpeg"):
        print("ERROR: ffmpeg not found — brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    THUMB_DIR.mkdir(exist_ok=True)

    if args.file:
        src = Path(args.file)
        dest = THUMB_DIR / f"{_mov_slug(src.name)}.jpg"
        if dest.exists() and not args.force:
            print(f"  skipped (exists): {dest.name}")
            return
        if not src.exists():
            print(f"  ✗ missing: {src}", file=sys.stderr)
            sys.exit(1)
        ok = _extract(src, dest, args.at)
        print(f"  {'✓' if ok else '✗'} {dest.name}")
        sys.exit(0 if ok else 1)

    sources = collect_sources()
    if not sources:
        print("No .mov sources found in tanzpalast.yaml")
        return

    ok = err = skipped = 0
    for mov, slug in sorted(sources.items()):
        src = DATA_DIR / mov
        dest = THUMB_DIR / f"{slug}.jpg"
        if dest.exists() and not args.force:
            skipped += 1
            continue
        if not src.exists():
            print(f"  ✗ missing source: {mov}")
            err += 1
            continue
        if _extract(src, dest, args.at):
            print(f"  ✓ {dest.name}")
            ok += 1
        else:
            print(f"  ✗ ffmpeg failed: {mov}")
            err += 1

    print(f"\n{ok} generated, {skipped} skipped, {err} errors")


if __name__ == "__main__":
    main()
