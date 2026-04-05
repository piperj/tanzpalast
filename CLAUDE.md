# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Tanzpalast is a static, single-page dance video catalog. It fetches a JSON data file from Google Drive at runtime and renders a searchable, filterable list of dance videos. No build step, no framework, no npm.

## Stack

- Plain HTML, CSS, vanilla JavaScript — no transpilation
- Data: `tanzpalast-data.json` hosted on Google Drive (publicly shared, fetched via `uc?export=download&id=FILE_ID`)
- Hosting: GitHub Pages (`main` branch, root)
- Python tooling (validation scripts) managed with `uv`

## Data

The JSON file lives on Google Drive, not in this repo. The canonical schema and field definitions are in `SPEC.md`. A local copy for development can be placed at `data/tanzpalast-data.json` — this is also what the CI workflow validates.

## CI

`.github/workflows/test.yaml` validates all JSON files in `data/` and checks required fields using `uv run python`.

## Key decisions

- All page logic lives in `index.html` for v1 — acceptable until complexity grows
- Google Drive direct-download URL is hardcoded in `index.html` as `DATA_URL`
- Videos link directly to their source (iCloud, YouTube, Vimeo) — no embedding
