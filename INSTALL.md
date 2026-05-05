# INSTALL.md

## Prerequisites

- Python 3.11+, `uv`, `ffmpeg` (`brew install ffmpeg`)
- A Google account with access to the Drive folder where your videos live

## 1. Clone the repo

```bash
git clone https://github.com/piperj/tanzpalast.git
```

## 2. Install dependencies

```bash
uv sync
```

## 3. Google Drive API setup (one time)

### 3a. Create credentials

1. Go to https://console.cloud.google.com
2. Create a project (e.g. "Tanzpalast")
3. Enable the **Google Drive API**
4. Credentials → **Create credentials** → **OAuth 2.0 Client ID** → Desktop App
5. Download `credentials.json` and place it in the repo root (it is gitignored)

### 3b. Authenticate

```bash
uv run python src/auth_setup.py
```

This opens a browser, you log in, and `token.json` is written. Both files are gitignored — never commit them.

### 3c. Set your Drive root folder ID

Find the folder ID from the URL when you open your Dance Videos folder in Drive:
`https://drive.google.com/drive/folders/THIS_IS_THE_ID`

Export it in your shell profile:

```bash
export TANZPALAST_DRIVE_ROOT=your_folder_id_here
```

Or prefix it to `make` commands:

```bash
TANZPALAST_DRIVE_ROOT=... make scan
```

## 4. First-time migration (existing repos only)

If the repo already has Drive `url:` entries in `tanzpalast.yaml`, migrate them to the new `filename:` form:

```bash
make scan                          # build drive-index.json
uv run python src/migrate_yaml.py  # rewrite Drive url: → filename:
make build                         # verify JSON builds cleanly
```

Review the YAML diff before committing.

## 5. Day-to-day workflow

```
Film on phone
  → Photos auto-syncs to Mac
  → drag .mov to right Drive folder AND keep a copy in data/
  → make stubs          # scan Drive; Claude infers and inserts YAML entries
  → review YAML diff    # fix titles, remove or reassign tags as needed
  → make all            # thumbnails + JSON build
  → make publish        # commit + push
```

## 6. Local development server

```bash
python3 -m http.server 8080 --bind 0.0.0.0 --directory .
# open http://localhost:8080
```

## 7. Makefile targets

| Target | What it does |
|---|---|
| `make all` | thumbnails + JSON build |
| `make scan` | refresh `data/drive-index.json` from Drive |
| `make stubs` | scan + ask Claude to insert new filenames into YAML |
| `make build` | compile YAML → JSON |
| `make thumbnails` | extract JPEG frames from any new `.mov` in `data/` |
| `make publish` | `all` + git commit + push |
| `make clean` | remove generated JSON and index |
