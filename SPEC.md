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
  ├── src/
  │   └── build.py           ← compiles YAML → tanzpalast-data.json
  └── tests/
      └── test_ui.py         ← Playwright browser tests (iPhone 15 viewport)

data/ (gitignored — generated output, local dev only)
  └── tanzpalast-data.json   ← used by index.html when running locally

Google Drive
  └── tanzpalast-data.json   ← published copy, fetched by the live site

GitHub Pages
  └── serves index.html to the public
```

### Filtering

The hamburger menu lists the 5 hardcoded collections (Standard, Smooth, Latin, Rhythm, Club). Tapping a collection filters the catalog to dances where at least one video carries a matching tag (e.g. `standard`, `latin`). Tags drive the filter — there is no `collection:` field in the data.

### Data environment detection

`index.html` detects its environment and picks the right data source:
- **Local** (`localhost` or `file://`): fetches from `data/tanzpalast-data.json`
- **Production** (GitHub Pages): fetches from the hardcoded `DATA_URL` (Google Drive)

This means cloners get a clean repo with no data — they supply their own Google Drive file.

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

Each entry is a dance card: a `featured` video (always visible in the card header) and a `videos` list (collapsed sub-videos). Tags on each video determine which collection filter(s) it appears under.

```yaml
- dance: Waltz
  featured:
    title: International Level 2
    url: https://youtu.be/...
    tags: [standard]
    description: ""
  videos:
    - title: Natural Turn exercise
      url: https://youtu.be/...
      tags: [standard, footwork]
    - title: Technique sheet
      url: https://...
      type: pdf
      tags: [standard]
```

The YAML is the source of truth, authored like a diary. IDs are assigned by the build script.

### JSON output (`tanzpalast-data.json`) — mirrors YAML

```json
[
  {
    "dance": "Waltz",
    "featured": {
      "id": 1,
      "title": "International Level 2",
      "url": "https://youtu.be/...",
      "type": "video",
      "tags": ["standard"],
      "description": ""
    },
    "videos": [
      {
        "id": 2,
        "title": "Natural Turn exercise",
        "url": "https://youtu.be/...",
        "type": "video",
        "tags": ["standard", "footwork"],
        "description": ""
      }
    ]
  }
]
```

### Field reference (video entry)

| Field         | Type     | Required | Description |
|---------------|----------|----------|-------------|
| `id`          | number   | yes      | Unique integer — assigned by build script, not in YAML |
| `title`       | string   | yes      | Descriptive name of the video or resource |
| `url`         | string   | yes      | Direct link to video, PDF, or image |
| `type`        | string   | no       | `video` (default), `pdf`, `image` |
| `tags`        | string[] | no       | Drive collection filtering; include the collection name (e.g. `standard`, `latin`) plus any descriptive keywords |
| `description` | string   | no       | Free-form note: teacher name, context, etc. |

### Collections and dances

| Collection   | Tag value  | Dances |
|--------------|------------|--------|
| **Standard** | `standard` | Waltz, Tango, Viennese Waltz, Foxtrot, Quickstep |
| **Smooth**   | `smooth`   | American Waltz, American Tango, American Foxtrot, Viennese Waltz |
| **Latin**    | `latin`    | Cha Cha, Samba, Rumba, Paso Doble, Jive |
| **Rhythm**   | `rhythm`   | Cha Cha, Bolero, East Coast Swing, Mambo, Rumba |
| **Club**     | `club`     | Salsa, Bachata, Kizomba, Swing, Zouk, Hustle |

A dance card appears under a collection when its `featured` video or any sub-video carries that collection's tag.

## Features

### v1 (current)
- Fetch and render catalog from Google Drive JSON (or local file in dev)
- Filter by collection via hamburger nav (hardcoded 5 collections); active collection shown in header
- Filtering uses tags — a card appears when its featured or any sub-video carries the collection tag
- Cards grouped by dance; collapsed by default; tap to expand sub-videos
- Featured video always visible in card header; opens link on tap
- Mixed media support (video, pdf, image) with appropriate icons
- Loading state while JSON fetches; error state on failure
- iPhone-first layout (390px baseline, 44px tap targets)

### v2 (later)
- Full-text search across title and tags
- Favourites / pin videos (localStorage)
- Count badge per dance
- Offline support via service worker

## Hosting

- **Repo**: GitHub (public) — data file is gitignored; cloners supply their own
- **Hosting**: GitHub Pages (`main` branch, root)
- **Data**: Google Drive shared file, direct-download link (`uc?export=download&id=FILE_ID`)

## Constraints

- No build tools, no frameworks, no npm — plain HTML, CSS, vanilla JS
- All logic in a single `index.html` is acceptable until complexity demands a split
- The YAML file must be editable by a non-developer; nested structure mirrors the UI
- Automated tests use Playwright via `uv` (Python) — no Node required
