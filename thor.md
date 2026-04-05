# Engineer's Notebook — Tanzpalast

---

## 2026-04-04 — Project genesis: static site + living data

### The problem

290 dance videos scattered across a shared iCloud album with no way to filter by style, level, or anything else. Finding the right Quickstep reference in a sea of thumbnails is like digging through a pile of VHS tapes — technically everything is there, but practically useless.

### What we decided

**Architecture: static shell, dynamic data.** The HTML/JS site is deployed once to GitHub Pages and never needs redeployment to update content. All video metadata lives in a single JSON file on Google Drive. On page load, JavaScript fetches it, builds the catalog, and renders it in the browser. No backend, no build pipeline, no npm. Just a file and a fetch.

This is sometimes called a "JAMstack without the stack" — the J (JavaScript) does the work, the A (API) is just Google Drive, and the M (markup) is hand-written HTML. It's a good pattern for content that changes frequently but doesn't need per-user personalisation.

**Why Google Drive over Dropbox:** The user already has their data and iCloud album there. Dropbox raw links (`?raw=1`) are slightly simpler, but Google Drive direct-download links (`uc?export=download&id=FILE_ID`) are just as reliable for publicly shared files and avoid creating another dependency.

**Why GitHub Pages over Netlify/Cloudflare:** For plain HTML with no build step, GitHub Pages is zero friction — push to `main`, it's live. Netlify's 2024 credit model adds billing complexity for what is essentially a file server. Cloudflare Pages would be worth it at scale; for a personal catalog, the speed difference is imperceptible.

### Data schema

Settled on a flat array of objects — no nesting, no relational structure. Each entry carries: `id`, `title`, `dance`, `style`, `level`, `tags`, `url`, `source`, `notes`. The `source` field (`YouTube`, `iCloud`, `Vimeo`) matters because iCloud shared album links behave differently — they don't embed, they open the Photos viewer. The catalog links out rather than embeds, so this isn't a problem for v1.

### First real data

Loaded 11 entries from the user's notes: the full International Level 2 Standard and Latin syllabus (YouTube reference videos) plus two personal iCloud recordings tagged `chrystal`. The tag structure (`international`, `level-2`, `chrystal`, `personal`) emerged naturally from the data rather than being designed upfront — a good sign that the schema is flexible enough.

### CI

GitHub Actions workflow validates JSON on every push using `uv run python` — no dependencies to install, no lockfile to maintain. The check is intentionally minimal: valid JSON + required fields present. Schema validation with jsonschema can be added later if the data grows complex enough to warrant it.

### Open questions

- iCloud shared album links: do they work reliably as direct URLs from a browser? Need to test whether `share.icloud.com/photos/...` opens cleanly on mobile without requiring an Apple ID login.
- CORS: Google Drive direct-download links work for JSON, but worth verifying once `index.html` is written.
- v2 wishlist: favourites via localStorage, count badges per dance, offline support via service worker.
