#!/usr/bin/env python3
"""Print Drive filenames not yet in tanzpalast.yaml, one per line.

Reads data/drive-index.json and tanzpalast.yaml.
Designed for: uv run python src/new_filenames.py | while read fn; do ...; done
"""
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
INDEX_PATH = ROOT / "data" / "drive-index.json"
YAML_PATH = ROOT / "tanzpalast.yaml"


def existing_filenames(yaml_path=YAML_PATH):
    with Path(yaml_path).open() as f:
        dances = yaml.safe_load(f)
    return {v["filename"] for entry in (dances or []) for v in (entry.get("videos") or []) if v.get("filename")}


def new_filenames(index_path=INDEX_PATH, yaml_path=YAML_PATH):
    if not Path(index_path).exists():
        print(f"ERROR: {index_path} not found — run 'make scan' first", file=sys.stderr)
        sys.exit(1)
    with Path(index_path).open() as f:
        index = json.load(f)
    known = existing_filenames(yaml_path)
    return sorted(fn for fn in index if fn not in known)


def main():
    for fn in new_filenames():
        print(fn)


if __name__ == "__main__":
    main()
