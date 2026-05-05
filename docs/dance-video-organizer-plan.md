# Dance Video Organizer — Project Plan

## The Core Problem
Google Drive file IDs are opaque strings (`1BxiMVs0XRA5nFMdKvBdBZjgm...`) that are completely
disconnected from filenames. This is what makes the current workflow painful.

## The Solution: Scan Drive Programmatically

Instead of ever looking up a file ID manually, a Python script scans your Drive folders and
builds the entire index automatically — filenames become titles, folder paths become categories.

---

## Phase 1: Google Drive API Setup

### 1.1 Create credentials
1. Go to https://console.cloud.google.com
2. Create a new project (e.g. "Dance Video Organizer")
3. Enable the **Google Drive API**
4. Create credentials → **OAuth 2.0 Client ID** → Desktop App
5. Download the `credentials.json` file into your project folder

### 1.2 Install dependencies
```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### 1.3 First-time auth (generates token.json)
```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# drive.file scope = read-only access restricted to your Dance Videos folder only
SCOPES = ['https://www.googleapis.com/auth/drive.file']

flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
creds = flow.run_local_server(port=0)

with open('token.json', 'w') as token:
    token.write(creds.to_json())
```
Run this once. It opens a browser, you log in, and `token.json` is saved for future runs.

---

## Phase 2: The Core Script — scan_drive.py

This is the heart of the project. It recursively walks your Drive folder and builds an index
with file IDs resolved automatically.

```python
import json
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive.file']

# The ID of your top-level "Dance Videos" folder in Drive
# Get this once from the URL when you open the folder in Drive:
# https://drive.google.com/drive/folders/THIS_PART_IS_THE_ID
ROOT_FOLDER_ID = 'your_root_folder_id_here'

def get_drive_service():
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    return build('drive', 'v3', credentials=creds)

def list_folder(service, folder_id, path=""):
    """Recursively list all video files in a folder, returning metadata."""
    results = []

    response = service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id, name, mimeType, modifiedTime)",
        pageSize=1000
    ).execute()

    for item in response.get('files', []):
        item_path = f"{path}/{item['name']}" if path else item['name']

        if item['mimeType'] == 'application/vnd.google-apps.folder':
            # Recurse into subfolders
            results.extend(list_folder(service, item['id'], item_path))

        elif item['mimeType'].startswith('video/'):
            # Clean up the filename to use as a title
            title = os.path.splitext(item['name'])[0]         # remove extension
            title = title.replace('_', ' ').replace('-', ' ')  # underscores/dashes to spaces
            title = title.title()                               # Title Case

            # Parse the folder path into category/subcategory
            parts = item_path.split('/')
            category    = parts[0] if len(parts) > 1 else 'Uncategorized'
            subcategory = parts[1] if len(parts) > 2 else None

            results.append({
                'id':          item['id'],
                'title':       title,
                'filename':    item['name'],
                'category':    category,
                'subcategory': subcategory,
                'path':        item_path,
                'modified':    item['modifiedTime'],
                # Direct playable URL — opens in Drive viewer
                'url': f"https://drive.google.com/file/d/{item['id']}/view",
                # Embed URL — for playing inline in your web app
                'embed_url': f"https://drive.google.com/file/d/{item['id']}/preview",
            })

    return results

def main():
    service = get_drive_service()
    print("Scanning Drive...")

    videos = list_folder(service, ROOT_FOLDER_ID)
    videos.sort(key=lambda v: (v['category'], v['subcategory'] or '', v['title']))

    index = {
        'generated': __import__('datetime').datetime.utcnow().isoformat(),
        'total': len(videos),
        'videos': videos
    }

    with open('data/videos-index.json', 'w') as f:
        json.dump(index, f, indent=2)

    print(f"Done. {len(videos)} videos indexed.")

    # Print a summary by category
    from collections import Counter
    cats = Counter(v['category'] for v in videos)
    for cat, count in cats.most_common():
        print(f"  {cat}: {count} videos")

if __name__ == '__main__':
    main()
```

---

## Phase 3: Drive Folder Structure

Organize your Drive folder so the structure becomes the index automatically:

```
Dance Videos/                          ← ROOT_FOLDER_ID points here
  Choreographies/
    Cha Cha/
      cha_cha_basic_steps.mp4          → title: "Cha Cha Basic Steps"
      new_yorker.mp4                   → title: "New Yorker"
    Rumba/
    Waltz/
  Technique/
    Footwork/
    Styling/
    Timing/
  Competitions/
    2024_sf_open.mp4
  Practice/
```

**Rules for filenames:**
- Use `snake_case` or `kebab-case` — both convert cleanly to titles
- No need for dates in filenames unless you want them in the title
- The folder = the category, so keep filenames short and descriptive

---

## Phase 4: The Web App

The web app reads `videos-index.json` and provides browse + search UI.
It plays videos using the Drive embed URL in an iframe.

### Key UI features
- Filter by category / subcategory (from folder structure)
- Search by title
- Click a card → plays inline via Drive embed
- Works on mobile for you and your wife

### Embed playback
```html
<!-- Drive preview URL plays inline — no download required -->
<iframe
  src="https://drive.google.com/file/d/FILE_ID/preview"
  width="640" height="360"
  allow="autoplay">
</iframe>
```

---

## Phase 5: Keeping It Updated

### Your workflow
```
Film on phone
  → auto-syncs to Mac via Photos
  → drag from Photos to right folder in Google Drive
  → ./update.sh
```

The drag-and-drop step is intentional — that's where you decide the category.

### update.sh — one command to do everything
```bash
#!/bin/bash
python scan_drive.py
git add data/videos-index.json
git commit -m "update video index"
git push
```

Make it executable once:
```bash
chmod +x update.sh
```

Then just run `./update.sh` whenever you add new videos. Takes a few seconds.

---

## Project File Structure

```
dance-video-organizer/
├── credentials.json          # From Google Cloud (never commit this)
├── token.json                # Generated on first run (never commit this)
├── .gitignore                # Must include credentials.json and token.json
├── scan_drive.py             # The main script
├── update.sh                 # One command: scan + commit + push
├── requirements.txt          # google-api-python-client etc.
├── data/
│   └── videos-index.json     # Generated — commit this
└── site/
    ├── index.html
    ├── style.css
    └── app.js
```

**.gitignore** — critical:
```
credentials.json
token.json
```

---

## Quick Start Sequence for Claude Code

1. Set up Google Cloud project and download `credentials.json`
2. `pip install -r requirements.txt`
3. Run auth script once to generate `token.json`
4. Set `ROOT_FOLDER_ID` in `scan_drive.py` (copy from Drive folder URL)
5. `python scan_drive.py` → inspect `data/videos-index.json`
6. Build `site/index.html` to read and display the index
7. Host on GitHub Pages

---

## The Payoff

**Old workflow:**
Copy video → open Drive → hunt for file ID → paste into markdown → run script → push to GitHub

**New workflow:**
Film → Photos auto-syncs to Mac → drag to right Drive folder → `./update.sh`

The only manual step is the intentional one: choosing the folder.
