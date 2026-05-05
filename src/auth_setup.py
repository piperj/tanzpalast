#!/usr/bin/env python3
"""One-time OAuth bootstrap: reads credentials.json, writes token.json.

Run once:
    uv run python src/auth_setup.py
"""
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
ROOT = Path(__file__).parent.parent

flow = InstalledAppFlow.from_client_secrets_file(str(ROOT / "credentials.json"), SCOPES)
creds = flow.run_local_server(port=0)
(ROOT / "token.json").write_text(creds.to_json())
print("token.json written — keep this file secret, never commit it.")
