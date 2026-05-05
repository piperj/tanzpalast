#!/usr/bin/env python3
"""One-time migration: rewrite Drive url: entries to filename: form.

Reads data/drive-index.json (must exist — run 'make scan' first).
Rewrites tanzpalast.yaml in-place: Drive url: + thumbnail: → filename:.
YouTube/iCloud entries are left untouched.
Idempotent: safe to run multiple times.

Usage:
    uv run python src/migrate_yaml.py [--dry-run]
"""
import argparse
import json
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.compat import StringIO

ROOT = Path(__file__).parent.parent
INDEX_PATH = ROOT / "data" / "drive-index.json"
YAML_PATH = ROOT / "tanzpalast.yaml"

DRIVE_URL_RE = re.compile(r"drive\.google\.com/file/d/([^/]+)")


def load_id_to_filename(index_path=INDEX_PATH):
    """Build reverse map: Drive file ID → filename."""
    with Path(index_path).open() as f:
        index = json.load(f)
    return {v["id"]: fn for fn, v in index.items()}


def migrate(yaml_path=YAML_PATH, index_path=INDEX_PATH, dry_run=False):
    if not Path(index_path).exists():
        print(f"ERROR: {index_path} not found — run 'make scan' first", file=sys.stderr)
        sys.exit(1)

    id_to_fn = load_id_to_filename(index_path)
    ryaml = YAML()
    ryaml.preserve_quotes = True
    yaml_path = Path(yaml_path)
    data = ryaml.load(yaml_path.read_text())

    changed = 0
    for entry in data or []:
        for v in entry.get("videos") or []:
            if v.get("filename"):
                continue  # already migrated
            url = v.get("url", "")
            m = DRIVE_URL_RE.search(url)
            if not m:
                continue  # YouTube, iCloud, etc — leave alone
            file_id = m.group(1)
            fn = id_to_fn.get(file_id)
            if not fn:
                print(f"  WARN: Drive ID {file_id} not in index (url: {url})", file=sys.stderr)
                continue
            # Rewrite entry
            v["filename"] = fn
            del v["url"]
            if "thumbnail" in v:
                del v["thumbnail"]
            changed += 1
            print(f"  {'[dry-run] ' if dry_run else ''}rewrote → filename: {fn}")

    if changed == 0:
        print("Nothing to migrate.")
        return

    if not dry_run:
        buf = StringIO()
        ryaml.dump(data, buf)
        yaml_path.write_text(buf.getvalue())
        print(f"\nMigrated {changed} entries in {yaml_path.name}")
    else:
        print(f"\n[dry-run] Would migrate {changed} entries.")


def main():
    parser = argparse.ArgumentParser(description="Migrate Drive url: entries to filename: form")
    parser.add_argument("--dry-run", action="store_true", help="show what would change without writing")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
