#!/usr/bin/env python3
"""Compile tanzpalast.yaml → data/tanzpalast-data.json."""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
YAML_PATH = ROOT / "tanzpalast.yaml"
DATA_DIR = ROOT / "data"
JSON_PATH = DATA_DIR / "tanzpalast-data.json"


def _video_dict(raw, video_id):
    return {
        "id": video_id,
        "title": raw["title"],
        "url": raw["url"],
        "type": raw.get("type", "video"),
        "tags": raw.get("tags") or [],
        "description": raw.get("description") or "",
    }


def build():
    with YAML_PATH.open() as f:
        dances = yaml.safe_load(f)

    if not isinstance(dances, list):
        print("ERROR: tanzpalast.yaml must be a YAML list", file=sys.stderr)
        sys.exit(1)

    next_id = 1
    output = []

    for entry in dances:
        dance_name = entry.get("dance", "").strip()
        if not dance_name:
            print("ERROR: entry missing 'dance' field", file=sys.stderr)
            sys.exit(1)

        featured_raw = entry.get("featured")
        if not featured_raw:
            print(f"ERROR: dance '{dance_name}' missing 'featured'", file=sys.stderr)
            sys.exit(1)

        featured = _video_dict(featured_raw, next_id)
        next_id += 1

        videos = []
        for v in entry.get("videos") or []:
            videos.append(_video_dict(v, next_id))
            next_id += 1

        output.append({"dance": dance_name, "featured": featured, "videos": videos})

    DATA_DIR.mkdir(exist_ok=True)
    with JSON_PATH.open("w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Wrote {len(output)} dance(s) → {JSON_PATH}")


if __name__ == "__main__":
    build()
