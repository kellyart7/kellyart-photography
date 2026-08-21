# Kellyart Photography — curator & publisher

A small local app for managing kellyart-photography.com's gallery: pick which photos
go in which album, write captions, choose the homepage hero shot, then build and
publish a real multi-page site to GitHub Pages — all from your Mac, whenever you like.

## One-time setup

1. **Install Pillow** (the only dependency, used for resizing photos):
   ```
   pip3 install --user pillow
   ```

2. **Run the app** — either double-click **"Start Kellyart Curator.command"** in this
   folder (Finder may ask "Are you sure you want to open it?" the first time — click
   **Open**), or from Terminal:
   ```
   cd ~/Documents/kellyart-photography-app
   python3 app.py
   ```
   Your Mac's browser opens automatically at `http://localhost:8765`. Leave that
   window open while you use it; close it (Ctrl+C, or just close the Terminal
   window) when you're done. This only runs on this Mac — it's not reachable from
   your phone or any other device.

3. **First publish** — click **Publish**. Since you already have `git`/`gh`
   authenticated on this Mac, the app will:
   - create the GitHub repo `Kellyart7/kellyart-photography` for you (if it doesn't exist yet)
   - try to switch on GitHub Pages, serving from the `docs/` folder on `main`
   - commit and push the generated site

   If automatic repo creation doesn't work (e.g. `gh` isn't installed), the app prints
   the couple of manual commands to run instead — everything else still works locally.

   Once Pages has finished deploying (usually well under a minute), your site is live at:
   ```
   https://kellyart7.github.io/kellyart-photography/
   ```
   You can point your own domain at this later via GitHub Pages' custom domain setting,
   if you want `kellyart-photography.com` instead of the github.io address.

## Everyday use

- **Add photos to an existing album** — select the album on the left, click
  *"+ Add photos from source folder"*, tick the ones you want.
- **Start a new album/location** — click *"+ New album from folder"*, browse to any
  folder under your photo library, tick the photos, give it a title.
- **Cull a photo** — untick "include" under any photo (keeps it in your library, just
  leaves it out of the site).
- **Reorder albums or rename things** — edit the title, key (URL slug) or blurb text
  directly; changes save automatically.
- **Set the homepage photo** — tick "hero" under any included photo.
- **Preview before publishing** — click **Build site**, then open
  `docs/index.html` in this folder directly in your browser.
- **Go live** — click **Publish**. This rebuilds the site and pushes it to GitHub;
  changes usually show up on the live site within a minute or two.

## How it's organised

```
kellyart-photography-app/
  app.py            the whole app (server + site generator + curation UI)
  content.json       your albums/captions/settings — created on first run
  docs/               the generated static site (this is what GitHub Pages serves)
  .thumb_cache/       cached preview thumbnails (safe to delete any time)
```

`content.json` is the source of truth — back it up if you like, or just let git track
it (it's committed alongside `docs/` on every publish, so your curation choices are
safe even if this Mac has a problem).

Photos themselves are never copied into this folder except as resized copies inside
`docs/` at publish time — your originals stay exactly where they are in your photo
library.

## Notes

- Started with your existing 12 Lake District albums (the same ones already on your
  claude.ai gallery link), so you're not starting from scratch.
- The library root defaults to `/Volumes/Public/Network Photos/PORTFOLIO` — browse
  anywhere under there to build new albums from other genres/locations.
- If a photo file has moved or been renamed since you added it, "Build site" will skip
  it and tell you which ones in the warnings log rather than failing the whole build.
