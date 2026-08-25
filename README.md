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
   window) when you're done.

   Other devices on the same Wi-Fi (your iMac, iPhone, etc.) can use it too — the
   Terminal window prints the address to use, e.g. `http://kellys-macbook.local:8765`
   (if that doesn't load, it also prints a plain IP address like `http://192.168.1.23:8765`
   as a backup — this one can change from time to time, the `.local` address usually
   won't). The app still only runs while it's running on this Mac; the other devices are
   just opening it in a browser, the same as any website.

   The first time you do this, macOS will likely ask whether to allow incoming network
   connections for `python3` — click **Allow**, or other devices won't be able to reach
   it. There's no password on the curator, so anything else on the same Wi-Fi network
   could open it too — fine for a normal home network, but worth knowing.

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

## Setting up comments and the contact form (one-time, optional)

The site already has a **Jump to a location** quick-links bar on the home page, a
**Contact** page (linked from the top of every page), and a **Comments** section
on every album page. Two of those need a short one-time setup before they're
"live" — until you do this, the site still works fine: the contact page shows a
plain "email me" link, and the comments section is simply left off each page.

### Contact form (Formspree — free)

1. Go to **[formspree.io](https://formspree.io)** and sign up (free plan is
   plenty — 50 messages/month).
2. Click **+ New Form**, name it something like "Kellyart Photography contact",
   and set the notification email to wherever you want messages to land
   (defaults to your Formspree sign-up email).
3. Formspree shows you an endpoint like `https://formspree.io/f/abcdwxyz` —
   you only need the part after `/f/`, e.g. `abcdwxyz`.
4. Open **app.py** in a text editor, find this line near the top:
   ```
   FORMSPREE_FORM_ID = "REPLACE_WITH_FORMSPREE_ID"
   ```
   and replace the placeholder with your ID, e.g.:
   ```
   FORMSPREE_FORM_ID = "abcdwxyz"
   ```
5. Save, then in the app click **Build site** and **Publish**. The Contact
   page now shows a real form; submissions land straight in your inbox — your
   email address is never shown on the page itself.

### Comments (giscus — free, uses your GitHub repo's Discussions)

1. On GitHub, open **github.com/Kellyart7/kellyart-photography** → **Settings**
   → tick **Discussions** (under the "Features" section) → **Set up discussions**.
2. Still on GitHub, go to that repo's **Discussions** tab → **Categories** (the
   gear/pencil icon) and create a new category called exactly **Comments**,
   format "Open-ended discussion" (or reuse an existing one, just make sure
   the name matches what you put in `GISCUS_CATEGORY` in app.py — it's
   `"Comments"` by default).
3. Go to **[giscus.app](https://giscus.app)**, scroll to **giscus is a
   comment system powered by GitHub Discussions**, and:
   - Under **Repository**, type `Kellyart7/kellyart-photography` and wait for
     the green check (you may need to install the free "giscus" GitHub App on
     that repo first — the page links you straight to it).
   - Under **Page ↔ Discussions Mapping**, choose **pathname**.
   - Under **Discussion Category**, choose **Comments**.
   - Leave the rest on the defaults.
4. Scroll down to **Enable giscus** — it shows a snippet of HTML. You only
   need two values out of it: `data-repo-id="..."` and
   `data-category-id="..."`.
5. Open **app.py**, find these lines near the top:
   ```
   GISCUS_REPO_ID = "REPLACE_WITH_REPO_ID"
   GISCUS_CATEGORY_ID = "REPLACE_WITH_CATEGORY_ID"
   ```
   and paste in the two values from giscus.app (keep the quote marks).
6. Save, then **Build site** and **Publish**. Every album page now has a
   comments box at the bottom — visitors sign in with GitHub to comment
   (nothing to moderate on your end; comments show up as posts in your repo's
   Discussions tab, where you can delete/hide anything if needed).

### Custom domain (optional — e.g. kellyart.co.uk instead of the github.io address)

1. Register a domain with any registrar (123-reg, Namecheap, Cloudflare, etc.) —
   a `.co.uk` is usually around £8–£15/year. This is the only step with a cost;
   everything else here is free.
2. At your registrar, add DNS records pointing the domain at GitHub Pages:
   - If you're using the bare domain (`kellyart.co.uk`), add four **A** records
     for `@` pointing at:
     ```
     185.199.108.153
     185.199.109.153
     185.199.110.153
     185.199.111.153
     ```
   - If you'd rather use `www.kellyart.co.uk`, add a **CNAME** record for `www`
     pointing at `kellyart7.github.io` instead.
   - Every registrar's DNS page looks a little different — if you get stuck,
     tell me the registrar and I can give you exact click-by-click steps.
3. In the app, click the **Home page text** button, scroll to **Custom domain**,
   and type your domain in (no `https://`, no trailing slash — just e.g.
   `kellyart.co.uk`).
4. Click **Build site**, then **Publish**. This writes the file GitHub Pages
   needs and pushes it, which tells GitHub to start serving the site from your
   domain.
5. On GitHub, open **github.com/Kellyart7/kellyart-photography** → **Settings**
   → **Pages**, and confirm your domain shows up under "Custom domain" with a
   green check. Tick **Enforce HTTPS** once it's available (this can take up
   to 24 hours the first time, while GitHub issues the certificate — until
   then the site is still reachable over plain http).

DNS changes can take anywhere from a few minutes to a few hours to take effect
everywhere. Your existing `kellyart7.github.io/kellyart-photography/` address
keeps working throughout, so there's no risk of the site going down while this
settles.

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
