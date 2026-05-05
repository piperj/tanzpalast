#!/usr/bin/env python3
"""Apply a Claude-generated YAML insertion plan from stdin to tanzpalast.yaml.

Input (stdin): JSON with keys: dance, create_new_dance, yaml_block, rationale
Output: modifies tanzpalast.yaml in-place; exits non-zero on failure.

Failures are appended to data/scan-failures.log so you can review and retry.
"""
import json
import re
import sys
from pathlib import Path

import yaml as pyyaml
from ruamel.yaml import YAML
from ruamel.yaml.compat import StringIO

ROOT = Path(__file__).parent.parent
YAML_PATH = ROOT / "tanzpalast.yaml"
FAILURES_LOG = ROOT / "data" / "scan-failures.log"


def _fail(msg, context=""):
    line = f"[{context}] {msg}" if context else msg
    print(f"ERROR: {line}", file=sys.stderr)
    FAILURES_LOG.parent.mkdir(exist_ok=True)
    with FAILURES_LOG.open("a") as f:
        f.write(line + "\n")
    sys.exit(1)


def apply_insert(plan_json, yaml_path=YAML_PATH):
    """Parse plan_json and apply insertion to yaml_path. Returns filename inserted."""
    if not plan_json.strip():
        _fail("Claude returned empty output — check 'claude -p' is working and authenticated")
    try:
        plan = json.loads(plan_json)
    except json.JSONDecodeError as e:
        preview = plan_json[:200].replace('\n', '\\n')
        _fail(f"Claude returned invalid JSON: {e}\nReceived: {preview}")

    dance = plan.get("dance", "").strip()
    create_new = bool(plan.get("create_new_dance", False))
    yaml_block = plan.get("yaml_block", "")

    if not dance:
        _fail("Plan missing 'dance' field")
    if not yaml_block:
        _fail("Plan missing 'yaml_block' field", dance)

    # Parse yaml_block to extract and validate the stub entry
    try:
        stub_list = pyyaml.safe_load(yaml_block)
    except Exception as e:
        _fail(f"yaml_block failed to parse: {e}", dance)

    if not isinstance(stub_list, list) or len(stub_list) != 1:
        _fail(f"yaml_block must be a single-item YAML list", dance)

    stub = stub_list[0]
    filename = stub.get("filename", "")
    if not filename:
        _fail("yaml_block entry missing 'filename'", dance)

    yaml_path = Path(yaml_path)
    original_text = yaml_path.read_text()

    # Snapshot original refs for post-insert validation
    original = pyyaml.safe_load(original_text)
    original_refs = {
        v.get("filename") or v.get("url")
        for entry in (original or [])
        for v in (entry.get("videos") or [])
        if v.get("filename") or v.get("url")
    }

    # Load with ruamel for comment-preserving round-trip
    ryaml = YAML()
    ryaml.preserve_quotes = True
    data = ryaml.load(original_text)
    dance_names = [e["dance"] for e in data]

    if create_new:
        if dance in dance_names:
            _fail(f"create_new_dance=true but '{dance}' already exists", filename)
        stub_seq = ryaml.load(yaml_block)  # CommentedSeq with one entry
        new_entry = ryaml.load(f"- dance: {dance}\n  videos: []\n")[0]
        new_entry["videos"] = stub_seq
        data.append(new_entry)
    else:
        if dance not in dance_names:
            _fail(f"Dance '{dance}' not found (set create_new_dance: true to add it)", filename)
        idx = dance_names.index(dance)
        entry_data = ryaml.load(yaml_block)
        data[idx]["videos"].append(entry_data[0])

    # Serialize and validate no original refs were lost
    buf = StringIO()
    ryaml.dump(data, buf)
    # ruamel preserves blank lines that originally separated dance blocks; after
    # appending, that blank line lands inside the videos list. Remove any blank
    # line followed by indented content (video entries start with spaces, not '-').
    new_text = re.sub(r'\n\n( {2,})', r'\n\1', buf.getvalue())

    new_parsed = pyyaml.safe_load(new_text)
    new_refs = {
        v.get("filename") or v.get("url")
        for entry in (new_parsed or [])
        for v in (entry.get("videos") or [])
        if v.get("filename") or v.get("url")
    }

    lost = original_refs - new_refs
    if lost:
        _fail(f"Refs lost after insert: {lost}", filename)
    if filename not in new_refs:
        _fail(f"New filename '{filename}' not found after insert", filename)

    yaml_path.write_text(new_text)
    print(f"  inserted '{filename}' under '{dance}'")
    return filename


def main():
    apply_insert(sys.stdin.read())


if __name__ == "__main__":
    main()
