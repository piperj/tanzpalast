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

The canonical schema and field definitions are in `SPEC.md`. The YAML source file is `tanzpalast.yaml`. Build with `uv run python src/build.py`.

### Environment detection

`index.html` must detect its environment and pick the right data source:
```js
const isLocal = location.hostname === 'localhost' || location.protocol === 'file:';
const DATA_URL = isLocal ? 'data/tanzpalast-data.json' : 'GOOGLE_DRIVE_URL';
```

Never hardcode the Google Drive URL without this guard — cloners would hit a URL they don't own.

## Current State (2026-04-06)

- Steps 0–6 complete and committed; `index.html` on `main`, live on GitHub Pages
- Card interaction redesigned: only the play icon opens video; tapping card body expands sub-videos
- "N more ›" badge (light blue pill) replaces the faint chevron — visible expand indicator
- Play button is now a rounded square (8px radius), not a circle
- `data/tanzpalast-data.json` has 10 dances; Showcase collection active (6th)
- `pyproject.toml` exists; `uv run python src/build.py` is the build command
- `tests/test_build.py` — 32 unit tests, 98% coverage of `src/build.py`
- `tests/test_ui.py` — Playwright tests active; run `uv run python -m pytest tests/ -v`
- Local dev server: `python3 -m http.server 8080 --bind 0.0.0.0 --directory .`

## Build Sequence

Work in strict order. Each step = one commit. Run Playwright tests + manual iPhone check before committing.

| Step | Goal | Key files |
|------|------|-----------|
| 0 | ✅ Migrate YAML to nested schema; write `src/build.py`; regenerate JSON | `tanzpalast.yaml`, `src/build.py`, `data/tanzpalast-data.json` |
| 1 | `index.html` — fetch data (env detection), group by dance, render flat list | `index.html` |
| 2 | Card structure — featured video in header + collapsible sub-list | `index.html` |
| 3 | iPhone layout — sticky header, single-column cards, 44px tap targets | `index.html` |
| 4 | Collection filter — hamburger panel + active collection in header | `index.html` |
| 5 | Mixed media icons — video vs. pdf vs. image based on `type` field | `index.html` |
| 6 | Loading + error states | `index.html` |

## UI Structure

See `SPEC.md` for the full ASCII layout. Key points:
- Sticky header: `≡  Tanzpalast · {ActiveCollection}  🏛`
- Hamburger opens a slide-out panel listing the 6 collections; tap filters + closes panel
- Cards grouped by dance within the active collection
- Card header = dance name + featured video (always visible) + large play button
- Sub-videos expand on card tap (collapsed by default)
- Mixed media uses a document icon (📄) instead of play button

## Testing

```bash
uv run python -m pytest tests/ -v                        # all tests
uv run python -m pytest tests/test_build.py -v           # unit tests only
uv run python -m pytest tests/test_build.py --cov=src --cov-report=term-missing  # with coverage
```

### Two test layers

| File | Type | Runs when |
|------|------|-----------|
| `tests/test_build.py` | Unit — pure Python, no server | Always |
| `tests/test_ui.py` | Playwright — headless Chromium, iPhone 15 viewport | `index.html` exists |

`test_ui.py` auto-skips at the module level when `index.html` is absent, so the suite stays green during pre-Step-1 development.

### Unit tests (`test_build.py`)

Cover `src/build.py` exhaustively. Target: **≥ 95% line coverage**. The only acceptable gap is the `if __name__ == "__main__"` guard (CLI entry point — not testable via import).

Conventions:
- Use `tmp_path` (pytest fixture) for all file I/O — never write to the real `data/` directory
- Monkey-patch `build.YAML_PATH`, `build.DATA_DIR`, `build.JSON_PATH` when redirecting paths; always restore originals in a `finally` block
- `TestRealData` smoke-tests against the actual `tanzpalast.yaml` — reload the module to reset patched paths

### UI tests (`test_ui.py`)

Each test uses a session-scoped local HTTP server (port 8765) serving the repo root. Tests are organized by build step so failures pinpoint which step broke.

Selector convention: use `data-*` attributes (e.g. `data-dance`, `data-featured`, `data-hamburger`, `data-nav-panel`, `data-sub-videos`, `data-loading`, `data-error`, `data-icon`). All interactive elements in `index.html` must carry the relevant `data-*` attribute so tests can target them without relying on CSS classes or tag names.

Also do a manual check in Safari/Chrome mobile simulation before each commit.

## CI

`.github/workflows/test.yaml` validates all JSON files in `data/` and checks required fields. Update this workflow when the JSON schema changes (nested structure changes the required-field check).

## Key Decisions

- All page logic lives in `index.html` for v1 — refactor only when it becomes unwieldy
- Environment detection chooses local file vs. Google Drive URL — never hardcode Drive URL alone
- YAML structure mirrors the card: `dance → featured + videos`; no collection nesting — collection membership is expressed via tags
- JSON output mirrors the YAML structure directly — no flattening
- Collections are hardcoded in the UI (Standard, Smooth, Latin, Rhythm, Club, Showcase); filtering matches cards by tag (see SPEC.md)
- `featured` is a top-level key on each dance object — the always-visible card header video
- `type` field on videos: `video` (default), `pdf`, `image`
- No search in v1 — filter by collection only
- Videos open their source URL directly — no embedding
