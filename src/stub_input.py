#!/usr/bin/env python3
"""Print the JSON payload for claude -p inference of a single new filename.

Usage:
    uv run python src/stub_input.py "Foxtrot showcase routine.mov"

Outputs JSON to stdout: {filename, drive_path, yaml}
Designed to be piped directly into: claude -p "$(cat prompts/insert_video.md)"
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
INDEX_PATH = ROOT / "data" / "drive-index.json"
YAML_PATH = ROOT / "tanzpalast.yaml"


def main():
    if len(sys.argv) != 2:
        print("Usage: stub_input.py <filename>", file=sys.stderr)
        sys.exit(1)

    fn = sys.argv[1]

    with INDEX_PATH.open() as f:
        index = json.load(f)

    if fn not in index:
        print(f"ERROR: '{fn}' not in drive-index.json", file=sys.stderr)
        sys.exit(1)

    print(json.dumps({
        "filename": fn,
        "drive_path": index[fn]["drive_path"],
        "yaml": YAML_PATH.read_text(),
    }))


if __name__ == "__main__":
    main()
