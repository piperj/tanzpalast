# Tanzpalast — Project Specification

## Purpose

A lightweight, browser-based catalog for dance reference and instructional videos. The goal is to quickly find the right video for the right dance out of a growing collection. Content is managed through a human-friendly YAML file that is compiled to JSON, so the catalog stays up to date without redeploying the site.

## User Need

- Browse 290+ videos organized by dance collection and style
- Open a video directly from the catalog with one tap (iPhone-first)
- Update the catalog without touching HTML or redeploying — just edit the YAML diary and regenerate

## Architecture

```
GitHub (repo)
  ├── index.html             ← page structure + JS fetch + render logic (single file for v1)
  ├── tanzpalast.yaml        ← human-friendly nested diary (source of truth)
  ├── Makefile               ← scan / stubs / build / thumbnails / publish
  ├── prompts/
  │   └── insert_video.md   ← system prompt for claude -p (infers dance/title/tags)
  ├── data/
  │   ├── tanzpalast-data.json  ← generated JSON; committed to repo
  │   └── drive-index.json      ← Drive filename → file ID map; committed to repo
  ├── thumbnails/            ← JPEG frames extracted from .mov files; committed
  ├── src/
  │   ├── build.py           ← compiles YAML → tanzpalast-data.json
  │   ├── list_drive.py      ← scans Drive, writes drive-index.json
  │   ├── new_filenames.py   ← prints Drive filenames not yet in YAML (one per line)
  │   ├── apply_insert.py    ← applies Claude's JSON insertion plan to YAML
  │   ├── migrate_yaml.py    ← one-time: rewrites Drive url: entries to filename: form
  │   ├── auth_setup.py      ← one-time: OAuth bootstrap → token.json
  │   └── make_thumbnails.py ← extracts JPEG thumbnails from local .mov files
  ├── tests/
  │   ├── test_build.py      ← unit tests for build.py
  │   ├── test_list_drive.py ← unit tests for list_drive.py (Drive API mocked)
  │   ├── test_new_filenames.py
  │   ├── test_apply_insert.py
  │   ├── test_migrate_yaml.py
  │   └── test_ui.py         ← Playwright browser tests (iPhone 15 viewport)
  └── .github/workflows/
      └── test.yaml          ← validates JSON schema on every push

GitHub Pages
  └── serves index.html + data/tanzpalast-data.json to the public
```

### Filtering

The hamburger menu lists the 6 hardcoded collections (Standard, Smooth, Latin, Rhythm, Club, Showcase). Tapping a collection filters the catalog to dances where at least one video carries a matching tag (e.g. `standard`, `latin`). Tags drive the filter — there is no `collection:` field in the data.

### Data URL

`index.html` always fetches `data/tanzpalast-data.json` via a relative URL — no environment detection needed. GitHub Pages and the local dev server both serve files at the same relative path. Cloners get the JSON from the repo directly.

## UI Layout (iPhone-first)

```
┌─────────────────────────────┐
│ ≡   Tanzpalast · Standard  🏛│  ← sticky header; active collection shown inline
├─────────────────────────────┤
│ ┌─────────────────────────┐ │
│ │ Quickstep               ▶ │  ← dance card: title + MAIN video (large play button)
│ │ International Bronze L2   │    featured: true video; opens link on tap
│ │─────────────────────────│ │
│ │   Exercise            ▶  │  ← sub-videos (collapsed by default, tap card to expand)
│ │   Slip Pivot          ▶  │    slightly smaller play button
│ │   ⋮                      │
│ │   Technique sheet    📄  │  ← mixed media (PDF/image): document icon
│ └─────────────────────────┘ │
│                              │
│ ┌─────────────────────────┐ │
│ │ Waltz                   ▶ │
│ │ ...                       │
│ └─────────────────────────┘ │
└─────────────────────────────┘
```

**Hamburger (≡)**: slides out a panel listing the 5 hardcoded collections. Tapping a collection closes the panel, updates the header, and filters cards to those whose videos are tagged with that collection.

**Cards**: collapsed by default. Tap a card to expand sub-videos. The main (featured) video row is always visible.

**Tap targets**: ≥ 44px tall on all interactive elements.

## Data Format

### YAML source (`tanzpalast.yaml`) — mirrors the card layout

Each entry is a dance card: a `videos` list in display order. The first video that matches the active collection filter becomes the featured (header) video; the rest are sub-videos. Tags on each video determine which collection filter(s) it appears under.

Each video entry is one of two shapes:

**Drive video** — `filename:` resolved via `data/drive-index.json` at build time:
```yaml
- dance: Waltz
  videos:
    - filename: waltz_natural_spin_turn.mov
      title: Waltz · Natural Spin Turn
      tags: [international, skill]
```

**External video** — explicit URL (YouTube, iCloud, etc.):
```yaml
- dance: Waltz
  videos:
    - title: Waltz · International · Level 2 · A
      url: https://youtu.be/...
      tags: [international]
    - title: Technique sheet
      url: https://...
      type: pdf
      tags: [international]
```

Rules:
- `filename` values must be unique across the entire Drive tree
- Newly auto-inserted stubs carry `new` as the first tag — remove after review
- IDs are assigned by the build script; do not add them to YAML

The YAML is the source of truth, authored like a diary.

### JSON output (`tanzpalast-data.json`) — mirrors YAML

`filename:` entries are resolved to Drive view URLs and thumbnail paths by `build.py`. The JSON never contains `filename:` — only `url` and optionally `thumbnail`.

```json
[
  {
    "dance": "Waltz",
    "videos": [
      {
        "id": 1,
        "title": "Waltz · Natural Spin Turn",
        "url": "https://drive.google.com/file/d/FILE_ID/view",
        "type": "video",
        "tags": ["international", "skill"],
        "description": "",
        "thumbnail": "thumbnails/waltz-natural-spin-turn.jpg"
      },
      {
        "id": 2,
        "title": "Waltz · International · Level 2 · A",
        "url": "https://youtu.be/...",
        "type": "video",
        "tags": ["international"],
        "description": ""
      }
    ]
  }
]
```

### Field reference (JSON video entry)

| Field         | Type     | Present when | Description |
|---------------|----------|-------------|-------------|
| `id`          | number   | always      | Unique integer — assigned by build script |
| `title`       | string   | always      | Descriptive name of the video or resource |
| `url`         | string   | always      | Direct link to video, PDF, or image |
| `type`        | string   | always      | `video` (default), `pdf`, `image` |
| `tags`        | string[] | always      | Collection tag + descriptive keywords; `new` tag = recently added, not yet reviewed |
| `description` | string   | always      | Free-form note: teacher name, context, etc. |
| `thumbnail`   | string   | Drive videos | Relative path e.g. `thumbnails/waltz-smooth.jpg` |

### `data/drive-index.json`

Maps video filename → Drive metadata. Generated by `src/list_drive.py`; committed to the repo so builds work offline and CI runs without Drive auth.

```json
{
  "waltz_natural_spin_turn.mov": {
    "id": "1AbCd...",
    "drive_path": "Waltz/International/waltz_natural_spin_turn.mov",
    "modified": "2024-03-15T10:00:00Z"
  }
}
```

### Collections and dances

| Collection   | Tag value  | Dances |
|--------------|------------|--------|
| **Standard** | `standard` | Waltz, Tango, Viennese Waltz, Foxtrot, Quickstep |
| **Smooth**   | `smooth`   | American Waltz, American Tango, American Foxtrot, Viennese Waltz |
| **Latin**    | `latin`    | Cha Cha, Samba, Rumba, Paso Doble, Jive |
| **Rhythm**   | `rhythm`   | Cha Cha, Bolero, East Coast Swing, Mambo, Rumba |
| **Club**     | `club`     | Salsa, Bachata, Kizomba, Swing, Zouk, Hustle |
| **Showcase** | `showcase` | Foxtrot, Tango, Hustle |

A dance card appears under a collection when any of its videos carries that collection's tag.

## Features

### v1 (current)
- Fetch and render catalog from repo JSON (`data/tanzpalast-data.json`)
- Filter by collection via hamburger nav (hardcoded 5 collections); active collection shown in header
- Filtering uses tags — a card appears when any of its videos carries the collection tag
- Cards grouped by dance; collapsed by default; tap to expand sub-videos
- First video matching the active filter is featured in the card header; the rest are sub-videos
- Mixed media support (video, pdf, image) with appropriate icons
- Loading state while JSON fetches; error state on failure
- iPhone-first layout (390px baseline, 44px tap targets)

### v2 (later)
- Full-text search across title and tags
- Favourites / pin videos (localStorage)
- Count badge per dance
- Offline support via service worker

## Hosting

- **Repo**: GitHub (public) — `tanzpalast-data.json` is committed and served from the repo
- **Hosting**: GitHub Pages (`main` branch, root)
- **Data**: `data/tanzpalast-data.json` and `data/drive-index.json` committed to the repo; built locally with `make build` and pushed

## Constraints

- No build tools, no frameworks, no npm — plain HTML, CSS, vanilla JS
- All logic in a single `index.html` is acceptable until complexity demands a split
- The YAML file must be editable by a non-developer; nested structure mirrors the UI
- Automated tests use Playwright via `uv` (Python) — no Node required
