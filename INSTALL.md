# INSTALL.md

## Prerequisites

- A GitHub account
- A Google Drive account (for the data file)
- Git installed locally

## 1. Fork or clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/tanzpalast.git
cd tanzpalast
```

## 2. Set up the data file in Google Drive

1. Copy `data/tanzpalast-data.json` to your Google Drive
2. Right-click the file → **Share** → **Anyone with the link** → **Viewer**
3. Copy the sharing URL — it looks like:
   `https://drive.google.com/file/d/FILE_ID/view?usp=sharing`
4. Extract the `FILE_ID` from that URL
5. Your raw fetch URL will be:
   `https://drive.google.com/uc?export=download&id=FILE_ID`

## 3. Configure the data URL

In `index.html`, find the line:

```js
const DATA_URL = 'REPLACE_WITH_YOUR_GOOGLE_DRIVE_URL';
```

Replace it with your URL from step 2.

## 4. Local development

No build step needed. Open `index.html` directly in your browser:

```bash
open index.html
```

Or serve it locally to avoid CORS issues during development:

```bash
python3 -m http.server 8000
# then open http://localhost:8000
```

## 5. Deploy to GitHub Pages

1. Push your changes to GitHub
2. Go to repo **Settings → Pages**
3. Set source to **Deploy from a branch**, branch `main`, folder `/` (root)
4. Save — your site will be live at `https://YOUR_USERNAME.github.io/tanzpalast`

## 6. Adding videos to the catalog

Edit `tanzpalast-data.json` in Google Drive directly (right-click → Open with → Google Docs, or download, edit, re-upload). The site picks up changes on next page load — no redeployment needed.

See `SPEC.md` for the full field reference.

## Updating the site itself

```bash
git add .
git commit -m "your message"
git push
```

GitHub Pages redeploys automatically within ~1 minute.
