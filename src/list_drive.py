#!/usr/bin/env python3
"""Scan a Drive folder tree and write data/drive-index.json.

Usage:
    TANZPALAST_DRIVE_ROOT=<folder-id> uv run python src/list_drive.py
"""
import json
import os
import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

ROOT = Path(__file__).parent.parent
TOKEN_PATH = ROOT / "token.json"
INDEX_PATH = ROOT / "data" / "drive-index.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def get_drive_service(token_path=TOKEN_PATH):
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    return build("drive", "v3", credentials=creds)


def list_videos(service, folder_id, path=""):
    results = []
    page_token = None
    while True:
        response = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        for item in response.get("files", []):
            item_path = f"{path}/{item['name']}" if path else item["name"]
            if item["mimeType"] == "application/vnd.google-apps.folder":
                results.extend(list_videos(service, item["id"], item_path))
            elif item["mimeType"].startswith("video/"):
                results.append({
                    "name": item["name"],
                    "id": item["id"],
                    "drive_path": item_path,
                    "modified": item["modifiedTime"],
                })
        page_token = response.get("nextPageToken")
        if not page_token:
            break
    return results


def write_index(items, path=INDEX_PATH):
    index = {}
    for item in items:
        name = item["name"]
        if name in index:
            print(f"ERROR: duplicate filename '{name}':", file=sys.stderr)
            print(f"  {index[name]['drive_path']}", file=sys.stderr)
            print(f"  {item['drive_path']}", file=sys.stderr)
            sys.exit(1)
        index[name] = {
            "id": item["id"],
            "drive_path": item["drive_path"],
            "modified": item["modified"],
        }
    path = Path(path)
    path.parent.mkdir(exist_ok=True)
    with path.open("w") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {len(index)} videos → {path}")
    return index


def main():
    root_id = os.environ.get("TANZPALAST_DRIVE_ROOT")
    if not root_id:
        print("ERROR: set TANZPALAST_DRIVE_ROOT to your Drive folder ID", file=sys.stderr)
        sys.exit(1)
    service = get_drive_service()
    print("Scanning Drive...")
    items = list_videos(service, root_id)
    write_index(items)


if __name__ == "__main__":
    main()
