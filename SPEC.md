# Tanzpalast — Project Specification

## Purpose

A lightweight, browser-based catalog for dance reference and instructional videos. The goal is to quickly find the right video for the right dance out of a growing collection (290+ videos). Content is managed through a human-friendly YAML file that is compiled to JSON, so the catalog stays up to date without redeploying the site.

## User Need

- Browse and search 290+ videos currently stored in a shared iCloud album
- Filter by dance style, level, or category
- Open a video directly from the catalog with one click
- Update the catalog without touching HTML or redeploying — just edit the YAML diary and regenerate

## Architecture

```
GitHub (repo)
  ├── index.html             ← page structure + JS fetch + render logic
  ├── style.css              ← layout and filter UI
  ├── tanzpalast.yaml        ← human-friendly diary/notebook (source of truth)
  └── scripts/
      └── build.py           ← compiles YAML → tanzpalast-data.json

data/ (gitignored — generated output)
  └── tanzpalast-data.json   ← consumed by index.html at runtime

Google Drive
  └── tanzpalast-data.json   ← published copy, fetched by the live site

GitHub Pages
  └── serves index.html to the public
```

The YAML file is the source of truth, authored by hand like a diary. The Python build script compiles it to JSON. The JSON is uploaded to Google Drive and fetched by `index.html` at runtime. No backend, no frontend build step.

## Data Format

`tanzpalast-data.json` — array of video entries:

```json
[
  {
    "id": 1,
    "title": "Natural Turn — Waltz",
    "dance": "Waltz",
    "style": "Standard",
    "level": "Beginner",
    "tags": ["footwork", "rise-and-fall"],
    "url": "https://www.icloud.com/photos/...",
    "source": "iCloud",
    "notes": ""
  }
]
```

### Field reference

| Field    | Type     | Required | Description |
|----------|----------|----------|-------------|
| `id`     | number   | yes      | Unique integer, never reused — assigned by build script, not in YAML |
| `title`  | string   | yes      | Descriptive name of the video |
| `dance`  | string   | yes      | Dance style (see controlled values below) |
| `style`  | string   | yes      | `Standard`, `Latin`, `Social`, `Other` |
| `level`  | string   | no       | `Beginner`, `Intermediate`, `Advanced` |
| `tags`   | string[] | no       | Free-form keywords for search |
| `url`    | string   | yes      | Direct link to video |
| `source` | string   | yes      | Where the video lives: `iCloud`, `YouTube`, `Vimeo` |
| `notes`  | string   | no       | Free text — teacher name, context, etc. |

### Controlled values for `dance`

Standard: Waltz, Tango, Viennese Waltz, Foxtrot, Quickstep  
Latin: Cha Cha, Samba, Rumba, Paso Doble, Jive  
Social: Salsa, Bachata, Kizomba, Swing, Zouk  
Other: Technique, Musicality, Warm-up

## Features

### v1 (MVP)
- Fetch and render catalog from Google Drive JSON
- Filter by `dance` (dropdown or tag buttons)
- Full-text search across `title`, `dance`, and `tags`
- Each card shows title, dance, level, and a direct link
- Mobile-friendly layout (use it on the dance floor)
- Loading state while JSON fetches

### v2 (later)
- Filter by `style` and `level`
- Sort by date added
- Favourite / pin videos (localStorage)
- Count badge per dance style
- Offline support via service worker

## Hosting

- **Repo**: GitHub (public or private)
- **Hosting**: GitHub Pages (`main` branch, root)
- **Data**: Google Drive shared file, direct-download link (`uc?export=download&id=FILE_ID`)
- **Custom domain**: optional later

## Constraints

- No build tools, no frameworks, no npm — plain HTML, CSS, vanilla JS
- All logic in a single `index.html` is acceptable for v1
- The YAML file must be editable by a non-developer (clear field names, diary-style format)
- CORS: Google Drive direct-download links work from the browser for publicly shared files; iCloud direct video links may need testing
