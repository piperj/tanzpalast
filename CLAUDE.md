# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Tanzpalast is a static, single-page dance video catalog. It fetches a JSON data file from Google Drive at runtime and renders a filterable catalog of dance videos grouped by collection and dance. No build step, no framework, no npm.

## Stack

- Plain HTML, CSS, vanilla JavaScript — no transpilation, all logic in `index.html` for v1
- Data: `tanzpalast-data.json` hosted on Google Drive (publicly shared)
- Hosting: GitHub Pages (`main` branch, root)
- Python tooling (build script, tests) managed with `uv`
- Testing: Playwright via `uv` — iPhone 15 viewport (390×844), no Node required

## Data

The JSON file lives on Google Drive, not in this repo. `data/tanzpalast-data.json` is gitignored — it is only present locally for development. Cloners supply their own Google Drive file.

The canonical schema and field definitions are in `SPEC.md`. The YAML source file is `tanzpalast.yaml`.

### Environment detection

`index.html` must detect its environment and pick the right data source:
```js
const isLocal = location.hostname === 'localhost' || location.protocol === 'file:';
const DATA_URL = isLocal ? 'data/tanzpalast-data.json' : 'GOOGLE_DRIVE_URL';
```

Never hardcode the Google Drive URL without this guard — cloners would hit a URL they don't own.

## Current State (2026-04-05)

- `tanzpalast.yaml` exists but uses the old flat schema — needs migration to nested structure
- `data/tanzpalast-data.json` exists with 9 flat entries — needs regeneration after schema migration
- `index.html` does not exist yet — app not started
- `scripts/build.py` does not exist yet — needs to be written for nested YAML → JSON
- `tests/test_ui.py` does not exist yet — Playwright tests needed

## Build Sequence

Work in strict order. Each step = one commit. Run Playwright tests + manual iPhone check before committing.

| Step | Goal | Key files |
|------|------|-----------|
| 0 | Migrate YAML to nested schema; write `scripts/build.py`; regenerate JSON | `tanzpalast.yaml`, `scripts/build.py`, `data/tanzpalast-data.json` |
| 1 | `index.html` — fetch data (env detection), group by dance, render flat list | `index.html` |
| 2 | Card structure — featured video in header + collapsible sub-list | `index.html` |
| 3 | iPhone layout — sticky header, single-column cards, 44px tap targets | `index.html` |
| 4 | Collection filter — hamburger panel + active collection in header | `index.html` |
| 5 | Mixed media icons — video vs. pdf vs. image based on `type` field | `index.html` |
| 6 | Loading + error states | `index.html` |

## UI Structure

See `SPEC.md` for the full ASCII layout. Key points:
- Sticky header: `≡  Tanzpalast · {ActiveCollection}  🏛`
- Hamburger opens a slide-out panel listing the 5 collections; tap filters + closes panel
- Cards grouped by dance within the active collection
- Card header = dance name + featured video (always visible) + large play button
- Sub-videos expand on card tap (collapsed by default)
- Mixed media uses a document icon (📄) instead of play button

## Testing

```bash
uv run python -m pytest tests/ -v
```

Each test uses `playwright` (installed via `uv`). Tests start a local HTTP server pointed at the repo root and drive a headless Chromium in iPhone 15 viewport. Also do a manual check in Safari/Chrome mobile simulation before each commit.

## CI

`.github/workflows/test.yaml` validates all JSON files in `data/` and checks required fields. Update this workflow when the JSON schema changes (nested structure changes the required-field check).

## Shell commands

`$PWD` is already set to the project root — never use `cd` before running commands.

## Key Decisions

- All page logic lives in `index.html` for v1 — refactor only when it becomes unwieldy
- Environment detection chooses local file vs. Google Drive URL — never hardcode Drive URL alone
- YAML is nested (collection → dance → videos) to mirror the UI hierarchy; intuitive for non-developers
- JSON output mirrors the nested YAML structure — no flattening, grouping is done at data level
- Collections are: Standard, Smooth, Latin, Rhythm, Club (see SPEC.md for dances per collection)
- One `featured: true` video per dance = the card header video (full choreography reference)
- `type` field on videos: `video` (default), `pdf`, `image`
- No search in v1 — filter by collection only
- Videos open their source URL directly — no embedding
