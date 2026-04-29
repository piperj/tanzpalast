#!/usr/bin/env python3
"""Extract thumbnail frames from local .mov source files listed in tanzpalast.yaml.

Usage:
    uv run python src/make_thumbnails.py          # extract at 12 s (default)
    uv run python src/make_thumbnails.py --at 14  # choose timestamp
    uv run python src/make_thumbnails.py --force  # overwrite existing
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


def main():
    parser = argparse.ArgumentParser(description="Generate thumbnails from .mov source files")
    parser.add_argument("--at", type=float, default=12.0, metavar="SECONDS",
                        help="timestamp to extract (default: 12)")
    parser.add_argument("--force", action="store_true",
                        help="overwrite existing thumbnails")
    args = parser.parse_args()

    if not shutil.which("ffmpeg"):
        print("ERROR: ffmpeg not found on PATH — install via: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    with YAML_PATH.open() as f:
        dances = yaml.safe_load(f)

    # Collect unique thumbnail source filenames
    sources = {}  # mov_filename -> slug
    for entry in dances:
        for v in entry.get("videos") or []:
            mov = v.get("thumbnail")
            if mov and mov not in sources:
                sources[mov] = _mov_slug(mov)

    if not sources:
        print("No thumbnail fields found in tanzpalast.yaml")
        return

    THUMB_DIR.mkdir(exist_ok=True)
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

        result = subprocess.run(
            ["ffmpeg", "-y", "-ss", str(args.at), "-i", str(src),
             "-frames:v", "1", "-q:v", "2", str(dest)],
            capture_output=True,
        )
        if result.returncode == 0:
            print(f"  ✓ {dest.name}")
            ok += 1
        else:
            print(f"  ✗ ffmpeg failed for {mov}")
            print(result.stderr.decode()[-300:], file=sys.stderr)
            err += 1

    print(f"\n{ok} generated, {skipped} skipped, {err} errors")


if __name__ == "__main__":
    main()
