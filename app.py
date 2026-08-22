#!/usr/bin/env python3
"""
Kellyart Photography — local gallery curation & publishing app.

Run with:  python3 app.py
Then open: http://localhost:8765

What it does
------------
- Serves a small browser UI (this file only, no install needed beyond Python 3 + Pillow)
  for browsing your photo library, choosing which shots go into which album/page,
  writing captions, and picking a homepage hero image.
- "Build site" renders a real static multi-page website into ./docs (one page per
  album/location, a home page with a card for each album, a Home button on every page).
- "Publish" commits and pushes ./docs (and the rest of this folder) to your GitHub repo,
  which GitHub Pages serves live. First run will offer to create the repo for you via the
  `gh` CLI if it's installed and authenticated; otherwise it prints the manual steps.

Requires: Python 3.9+, Pillow (`pip3 install --user pillow`), and for one-click repo
creation the GitHub CLI (`gh`, already authenticated) — optional, manual setup works too.
"""

import json, os, re, sys, io, shutil, subprocess, threading, webbrowser, hashlib, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print("\nPillow is required for thumbnails and building the site.")
    print("Install it once with:\n\n    pip3 install --user pillow\n")
    sys.exit(1)

# ----------------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------------

APP_DIR = Path(__file__).resolve().parent
STATE_PATH = APP_DIR / "content.json"
DOCS_DIR = APP_DIR / "docs"
CACHE_DIR = APP_DIR / ".thumb_cache"
PORT = int(os.environ.get("PORT", "8765"))
HOST = "127.0.0.1"  # this Mac only

DEFAULT_ROOT = "/Volumes/Public/Network Photos/PORTFOLIO"
SITE_TITLE = "Kellyart Photography"
SITE_TAGLINE = "Landscape photography from the fells, tarns and lakes of Cumbria — a growing collection, organised by location."
GITHUB_USER = "Kellyart7"
GITHUB_REPO = "kellyart-photography"

# --- Contact form (Formspree) --------------------------------------------
# One-time setup: create a free form at https://formspree.io, then paste the
# form ID (the part after /f/ in the endpoint it gives you) below. Until you
# do, the contact page shows a plain "email me" link instead of the form —
# see README.md for the exact steps.
FORMSPREE_FORM_ID = "REPLACE_WITH_FORMSPREE_ID"
CONTACT_EMAIL = "kellyart7@yahoo.co.uk"

# --- Comments (giscus, powered by GitHub Discussions) ---------------------
# One-time setup: turn on "Discussions" for your GitHub repo, then configure
# https://giscus.app for that repo and paste the two IDs it gives you below.
# Until you do, the comments section is simply left off each page — see
# README.md for the exact steps.
GISCUS_REPO = f"{GITHUB_USER}/{GITHUB_REPO}"
GISCUS_CATEGORY = "Comments"
GISCUS_REPO_ID = "REPLACE_WITH_REPO_ID"
GISCUS_CATEGORY_ID = "REPLACE_WITH_CATEGORY_ID"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic"}
THUMB_MAX = 640
FULL_MAX = 1600
THUMB_QUALITY = 72
FULL_QUALITY = 80

# ----------------------------------------------------------------------------
# Seed content — your existing Lake District curation, so the app opens with
# the same 12 albums that are already live. Edit freely from the UI afterwards.
# ----------------------------------------------------------------------------

LD = "/Volumes/Public/Network Photos/PORTFOLIO/Genre/Landscapes Locations/England/Lake District"

def _album(key, title, blurb, folder, photos):
    return {
        "key": key,
        "title": title,
        "blurb": blurb,
        "sourceFolder": f"{LD}/{folder}",
        "photos": [
            {"file": fn, "caption": cap, "include": True}
            for fn, cap in photos
        ],
    }

SEED_ALBUMS = [
    _album("blea-tarn", "Blea Tarn", "A small, still tarn cradled beneath the Langdale Pikes.", "Blea Tarn", [
        ("Blea Tarn.jpeg", "Blea Tarn, morning calm"),
        ("BleaTarn06_00.jpeg", "Reflections across the water"),
        ("BleaTarn06_06.jpeg", "Pikes above the tarn"),
        ("BleaTarn06_10.jpeg", "Shoreline pines"),
        ("BleaTarn06_35.jpeg", "Still water study"),
        ("BleaTarn06_90.jpeg", "Late light on the tarn"),
    ]),
    _album("buttermere", "Buttermere", "Lakeshore paths, mist and mirror-still water in the western fells.", "Buttermere", [
        ("buttermere copy.jpg", "Buttermere shoreline"),
        ("Buttermerewateerfall copy.jpg", "Waterfall above the lake"),
        ("buttermererockmist.jpeg", "Rock and morning mist"),
        ("buttermereTreeframe.jpeg", "Framed by lakeside trees"),
        ("classicfence.jpg", "The classic fence line"),
        ("CrummokPano copy.jpg", "Crummock Water panorama"),
        ("knarleyTree.jpg", "The gnarled lakeside tree"),
        ("LoneButttermereTree.jpeg", "Lone tree, Buttermere"),
    ]),
    _album("derwentwater", "Derwentwater", "Keswick's lake, bridges and soft valley light.", "Derwent", [
        ("Bridge-Pano copy.jpg", "Bridge panorama"),
        ("KeswickHDR.jpeg", "Keswick shoreline"),
        ("_MG_0235.jpeg", "Derwentwater, morning"),
        ("_MG_0250.jpeg", "Along the shore"),
        ("_MG_0269.jpeg", "Fells across the water"),
        ("_MG_0315.jpeg", "Derwentwater study"),
    ]),
    _album("elterwater", "Elterwater & Langdale", "Reed-fringed water beneath the Langdale Pikes.", "Elterwater", [
        ("LangdalesTreeframe.jpeg", "The Langdale Pikes, framed"),
        ("AutumnReflections.jpeg", "Autumn reflections"),
        ("CowsonBeach.jpg", "Cowson beach"),
        ("JKRGElterWater.jpeg", "Elterwater, still morning"),
        ("redMushMerge.jpeg", "Woodland fungi study"),
        ("SQBratheySnowy.jpeg", "Brathay in snow"),
        ("sunrays.jpeg", "Sunrays through the trees"),
        ("TreeShadowsBrath.jpeg", "Tree shadows, Brathay"),
    ]),
    _album("grasmere", "Grasmere", "Wordsworth's village lake, cottages and island views.", "Grassmere", [
        ("BWvillage.jpeg", "The village, black and white"),
        ("grasmereCottage copy.jpg", "Lakeland cottage"),
        ("GrassmereGold.jpeg", "Golden hour, Grasmere"),
        ("GrassmereIsland.jpeg", "The island"),
        ("GrassmereSeagull.jpeg", "Seagull over the lake"),
        ("whitehouse.jpeg", "The white house"),
    ]),
    _album("haweswater", "Haweswater", "A remote reservoir valley, wide skies and rock shorelines.", "Hawswater", [
        ("HawswaterPANO.jpeg", "Haweswater panorama"),
        ("169lake.jpeg", "Wide lake view"),
        ("RockLake.jpeg", "Rock shoreline"),
        ("_MG_2198.jpeg", "Haweswater, morning"),
        ("_MG_2246.jpeg", "Valley light"),
        ("_MG_2286.jpeg", "Haweswater study"),
    ]),
    _album("loughrigg", "Loughrigg Fell", "High views over Elterwater, Rydal and Windermere.", "Loughrigg", [
        ("LoughrigPANO.jpeg", "View from Loughrigg, panorama"),
        ("BWRydalPat.jpg", "Path above Rydal, black and white"),
        ("CumbrianPaths.jpg", "Cumbrian fell paths"),
        ("ElterEpic.jpeg", "Elterwater from the fell"),
        ("FluffyWaterfall.jpeg", "Waterfall, long exposure"),
        ("RydalWalkers.jpg", "Walkers above Rydal"),
        ("ViewtoElterwater.jpg", "Looking toward Elterwater"),
        ("WindermereSelfy.jpg", "Windermere from the summit"),
    ]),
    _album("further-views", "Further Views", "A few more favourites from around the valleys.", "Other", [
        ("LakesandGeese copy.jpg", "Geese on the water"),
        ("BrathyWalkers copy.jpg", "Walkers by the Brathay"),
        ("_MG_1093.jpeg", "Lakeland view"),
        ("_MG_1820.jpeg", "Valley study"),
        ("_MG_1849.jpeg", "Fellside light"),
        ("_MG_1924.jpeg", "Lakeland view"),
    ]),
    _album("rydal-water", "Rydal Water", "A small lake between Grasmere and Ambleside, quiet and wooded.", "Rydal", [
        ("rydal.jpeg", "Rydal Water, morning"),
        ("RydalPano1.jpeg", "Rydal Water panorama"),
        ("RydalLoneTreeBW.jpeg", "Lone tree, black and white"),
        ("RydalCave copy.jpeg", "Rydal Cave"),
        ("_MG_1153.jpeg", "Rydal Water study"),
        ("RydalWalkers.jpeg", "Walkers by the lake"),
    ]),
    _album("tarn-hows", "Tarn Hows", "A National Trust beauty spot of pine, water and mist.", "Tarn Hows", [
        ("FoggyMorningPano.jpg", "Foggy morning panorama"),
        ("Bracken copy.jpg", "Autumn bracken"),
        ("MistyFence copy.jpg", "Fence in the mist"),
        ("ReflectingTree copy.jpg", "Reflecting tree"),
        ("TarnHowsGoldenL (1).jpg", "Golden light"),
        ("TarnHowsGraphicBW copy (1).jpg", "Graphic study, black and white"),
        ("THGlow.jpg", "Evening glow"),
        ("TarnHowsSundown.jpeg", "Sundown at Tarn Hows"),
    ]),
    _album("thirlmere", "Thirlmere", "A dramatic reservoir valley with waterfalls and autumn colour.", "Thirlemere", [
        ("_MG_0527-Enhanced-NR.jpg", "Thirlmere, enhanced"),
        ("AutumnBurst copy.jpg", "Autumn colour burst"),
        ("CrazyGrasshue.jpeg", "Grasses in the wind"),
        ("ragingTorrent.jpeg", "A raging torrent"),
        ("WaterFallHDR copy.jpg", "Waterfall, HDR"),
        ("WetandMistyautum.jpeg", "Wet and misty autumn"),
        ("yellowSplashtree.jpeg", "Autumn tree, yellow splash"),
    ]),
    _album("ullswater", "Ullswater", "England's 'most beautiful lake', wide waters beneath the fells.", "Ullswater", [
        ("QuiteSiteUllswater20220615_05.jpeg", "A quiet spot on Ullswater"),
        ("SensetUllswater.jpeg", "Sunset over Ullswater"),
        ("SunsetTreeUllswater.jpeg", "Sunset tree"),
        ("UllwateQuiteSitePANO.jpeg", "Ullswater panorama"),
    ]),
]

DEFAULT_STATE = {
    "site": {
        "title": SITE_TITLE,
        "tagline": SITE_TAGLINE,
        "eyebrow": "Lake District · England",
        "root": DEFAULT_ROOT,
        "hero": {"album": "loughrigg", "photo": "LoughrigPANO.jpeg"},
        "github": {"user": GITHUB_USER, "repo": GITHUB_REPO},
    },
    "albums": SEED_ALBUMS,
}

# ----------------------------------------------------------------------------
# State
# ----------------------------------------------------------------------------

def load_state():
    if STATE_PATH.exists():
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    save_state(DEFAULT_STATE)
    return json.loads(json.dumps(DEFAULT_STATE))

def save_state(state):
    tmp = STATE_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp.replace(STATE_PATH)

# ----------------------------------------------------------------------------
# Image helpers
# ----------------------------------------------------------------------------

def safe_under_root(path, root):
    try:
        Path(path).resolve().relative_to(Path(root).resolve())
        return True
    except Exception:
        return False

def slugify(name):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "item"

def load_and_orient(path):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

def resized_jpeg_bytes(path, max_dim, quality):
    img = load_and_orient(path)
    w, h = img.size
    scale = min(1.0, max_dim / max(w, h))
    if scale < 1.0:
        img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue(), img.size

def cached_thumb(path, max_dim, quality):
    CACHE_DIR.mkdir(exist_ok=True)
    try:
        mtime = int(os.path.getmtime(path))
    except OSError:
        mtime = 0
    key = hashlib.sha1(f"{path}|{max_dim}|{quality}|{mtime}".encode("utf-8")).hexdigest()
    cache_file = CACHE_DIR / f"{key}.jpg"
    if cache_file.exists():
        return cache_file.read_bytes()
    data, _ = resized_jpeg_bytes(path, max_dim, quality)
    cache_file.write_bytes(data)
    return data

# ----------------------------------------------------------------------------
# Site builder
# ----------------------------------------------------------------------------

STYLE_CSS = """
:root{
  --bg:#E2E4DE; --surface:#EDEEE8; --surface-2:#D6D9CF; --ink:#242923; --ink-soft:#57604F;
  --moss:#3F5741; --moss-ink:#F3F5EF; --slate:#4E5F6B; --line:rgba(36,41,35,0.12);
  --shadow:0 18px 40px -20px rgba(20,24,18,0.35); --overlay:rgba(18,20,16,0.92);
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#181D18; --surface:#212721; --surface-2:#2E352D; --ink:#E7E9E1; --ink-soft:#A6AF9E;
    --moss:#8AAE8B; --moss-ink:#152016; --slate:#9FB4C0; --line:rgba(231,233,225,0.14);
    --shadow:0 18px 44px -18px rgba(0,0,0,0.6); --overlay:rgba(8,10,7,0.94);
  }
}
:root[data-theme="dark"]{
  --bg:#181D18; --surface:#212721; --surface-2:#2E352D; --ink:#E7E9E1; --ink-soft:#A6AF9E;
  --moss:#8AAE8B; --moss-ink:#152016; --slate:#9FB4C0; --line:rgba(231,233,225,0.14);
  --shadow:0 18px 44px -18px rgba(0,0,0,0.6); --overlay:rgba(8,10,7,0.94);
}
*{box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Libre Franklin",system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased;}
h1,h2,h3,.display{font-family:"Newsreader",Georgia,"Times New Roman",serif;font-weight:500;text-wrap:balance;margin:0;}
a{color:inherit;text-decoration:none;}
img{max-width:100%;display:block;-webkit-user-select:none;user-select:none;-webkit-touch-callout:none;}
button{font-family:inherit;cursor:pointer;}

.topbar{position:sticky;top:0;z-index:40;background:color-mix(in srgb, var(--bg) 92%, transparent);-webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);border-bottom:1px solid var(--line);}
.topbar-inner{display:flex;align-items:center;gap:1rem;padding:0.85rem 1.4rem;max-width:1400px;margin:0 auto;}
.home-btn{display:flex;align-items:center;gap:0.4rem;border:1px solid var(--line);background:var(--surface);color:var(--ink);padding:0.5rem 1rem;border-radius:999px;font-size:0.86rem;font-weight:600;flex-shrink:0;}
.home-btn:hover{border-color:var(--moss);}
.home-btn svg{width:14px;height:14px;}
.topbar-title{font-family:"Newsreader",serif;font-size:1rem;color:var(--ink-soft);}
.contact-link{margin-left:auto;border:1px solid var(--line);background:transparent;color:var(--ink-soft);padding:0.5rem 1rem;border-radius:999px;font-size:0.86rem;font-weight:600;flex-shrink:0;}
.contact-link:hover{border-color:var(--moss);color:var(--ink);}

.quicklinks-bar{background:var(--surface);border-bottom:1px solid var(--line);}
.quicklinks-inner{max-width:1400px;margin:0 auto;padding:1.15rem 1.4rem;display:flex;flex-wrap:wrap;align-items:center;gap:0.7rem 0.9rem;}
.quicklinks-label{font-size:0.74rem;letter-spacing:0.12em;text-transform:uppercase;color:var(--ink-soft);font-weight:700;flex-shrink:0;}
.quicklinks-links{display:flex;flex-wrap:wrap;gap:0.5rem;}
.quicklinks-links a{border:1px solid var(--line);background:var(--surface-2);color:var(--ink);padding:0.44rem 1rem;border-radius:999px;font-size:0.83rem;font-weight:600;transition:border-color 0.15s ease, background 0.15s ease, color 0.15s ease;}
.quicklinks-links a:hover{border-color:var(--moss);background:var(--moss);color:var(--moss-ink);}

.hero{position:relative;min-height:clamp(260px,40vh,440px);display:flex;align-items:flex-end;padding:5vw 6vw 2.4rem;background:linear-gradient(180deg, rgba(20,23,18,0.12) 0%, rgba(14,16,12,0.68) 88%), var(--hero-img) center 60%/cover no-repeat;}
.hero-inner{position:relative;z-index:1;color:#F2F3EC;max-width:46rem;}
.hero-eyebrow{font-size:0.78rem;letter-spacing:0.18em;text-transform:uppercase;color:#D6DACB;margin-bottom:1rem;font-weight:600;}
.hero h1{font-size:clamp(2.4rem,6vw,4.2rem);line-height:1.02;color:#F6F6EF;}
.hero p{font-size:clamp(1rem,1.6vw,1.15rem);color:#DEE1D4;max-width:34rem;margin-top:1.1rem;line-height:1.55;}

main{max-width:1400px;margin:0 auto;padding:0 1.4rem;}

.card-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1.4rem;padding:2.6rem 0 3.5rem;}
.card{position:relative;border-radius:8px;overflow:hidden;box-shadow:var(--shadow);aspect-ratio:4/5;background:var(--surface-2);}
.card img{width:100%;height:100%;object-fit:cover;transition:transform 0.5s ease;}
.card:hover img{transform:scale(1.04);}
.card-label{position:absolute;left:0;right:0;bottom:0;padding:2.4rem 1.1rem 1rem;background:linear-gradient(0deg, rgba(10,12,8,0.82), rgba(10,12,8,0));color:#EFF1E7;}
.card-label h3{font-size:1.2rem;color:#F6F6EF;}
.card-label span{font-size:0.78rem;letter-spacing:0.06em;text-transform:uppercase;color:#C8CEBC;}

.album-head{display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:0.8rem 1.6rem;padding:2.1rem 0 1.4rem;border-bottom:1px solid var(--line);margin-bottom:1.6rem;}
.album-head-text{flex:1 1 26rem;}
.album-head h2{font-size:clamp(1.7rem,2.8vw,2.3rem);}
.album-head p{color:var(--ink-soft);font-size:1rem;max-width:36rem;line-height:1.55;margin-top:0.5rem;}
.album-count{flex-shrink:0;font-size:0.78rem;letter-spacing:0.06em;text-transform:uppercase;color:var(--ink-soft);border:1px solid var(--line);background:var(--surface);padding:0.4rem 0.9rem;border-radius:999px;margin-bottom:0.2rem;}

.grid{columns:4 240px;column-gap:1rem;padding-bottom:3rem;}
.tile{break-inside:avoid;margin-bottom:1rem;position:relative;border-radius:6px;overflow:hidden;background:var(--surface-2);box-shadow:var(--shadow);border:0;padding:0;display:block;width:100%;}
.tile img{width:100%;height:auto;display:block;transition:transform 0.5s ease;}
.tile:hover img{transform:scale(1.035);}
.tile-cap{position:absolute;left:0;right:0;bottom:0;padding:1.6rem 0.8rem 0.6rem;background:linear-gradient(0deg, rgba(10,12,8,0.72), rgba(10,12,8,0));color:#EFF1E7;font-size:0.82rem;opacity:0;transform:translateY(4px);transition:opacity 0.2s ease, transform 0.2s ease;}
.tile:hover .tile-cap,.tile:focus-visible .tile-cap{opacity:1;transform:translateY(0);}
.tile:focus-visible{outline:2px solid var(--moss);outline-offset:2px;}

footer{margin-top:3rem;padding:2.4rem 1.4rem 3rem;border-top:1px solid var(--line);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:1rem;color:var(--ink-soft);font-size:0.86rem;max-width:1400px;margin-left:auto;margin-right:auto;}

.comments-wrap{max-width:1400px;margin:0 auto;padding:0.5rem 1.4rem 3rem;}
.comments-wrap h3{font-family:"Newsreader",serif;font-weight:500;font-size:1.3rem;margin-bottom:1.2rem;}

.contact-wrap{max-width:34rem;padding:3.5rem 0 4rem;}
.contact-wrap h2{font-size:clamp(1.7rem,2.8vw,2.3rem);}
.contact-wrap>p{color:var(--ink-soft);font-size:1rem;line-height:1.55;margin-top:0.6rem;}
.contact-form{display:flex;flex-direction:column;gap:1.1rem;margin-top:1.8rem;}
.contact-form label{display:flex;flex-direction:column;gap:0.4rem;font-size:0.82rem;font-weight:600;color:var(--ink-soft);}
.contact-form input,.contact-form textarea{font-family:inherit;font-size:0.95rem;padding:0.75rem 0.9rem;border-radius:6px;border:1px solid var(--line);background:var(--surface);color:var(--ink);}
.contact-form textarea{min-height:150px;resize:vertical;}
.contact-form input:focus,.contact-form textarea:focus{outline:2px solid var(--moss);outline-offset:1px;}
.contact-form button{align-self:flex-start;background:var(--moss);color:var(--moss-ink);border:0;padding:0.8rem 1.7rem;border-radius:999px;font-weight:600;font-size:0.92rem;}
.contact-form button:hover{opacity:0.9;}
.contact-fallback{margin-top:1.8rem;font-size:0.98rem;line-height:1.6;}
.contact-fallback a{color:var(--moss);font-weight:600;text-decoration:underline;text-underline-offset:2px;}

.lightbox{position:fixed;inset:0;z-index:100;background:var(--overlay);display:flex;align-items:center;justify-content:center;opacity:0;pointer-events:none;transition:opacity 0.2s ease;}
.lightbox.open{opacity:1;pointer-events:auto;}
.lb-figure{max-width:90vw;max-height:82vh;display:flex;flex-direction:column;align-items:center;gap:0.9rem;}
.lb-figure img{max-width:90vw;max-height:74vh;width:auto;height:auto;border-radius:4px;box-shadow:0 30px 60px -20px rgba(0,0,0,0.6);}
.lb-cap{color:#EDEFE5;text-align:center;font-size:0.94rem;}
.lb-btn{position:absolute;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.22);color:#F2F3EC;width:2.6rem;height:2.6rem;border-radius:50%;display:flex;align-items:center;justify-content:center;transition:background 0.15s ease;}
.lb-btn:hover{background:rgba(255,255,255,0.18);}
.lb-btn svg{width:18px;height:18px;}
.lb-close{top:1.4rem;right:1.4rem;} .lb-prev{left:1.4rem;top:50%;transform:translateY(-50%);} .lb-next{right:1.4rem;top:50%;transform:translateY(-50%);}
@media (max-width:640px){ .lb-prev,.lb-next{width:2.2rem;height:2.2rem;} .lb-prev{left:0.5rem;} .lb-next{right:0.5rem;} .lb-close{top:0.6rem;right:0.6rem;} .grid{columns:2 160px;} }
@media (prefers-reduced-motion: reduce){ html{scroll-behavior:auto;} .tile img,.tile-cap,.card img{transition:none;} }
"""

GALLERY_JS = """
(function(){
  document.addEventListener('contextmenu', function(e){
    if(e.target && e.target.tagName === 'IMG'){ e.preventDefault(); }
  });
  document.addEventListener('dragstart', function(e){
    if(e.target && e.target.tagName === 'IMG'){ e.preventDefault(); }
  });
})();

(function(){
  var tiles = Array.prototype.slice.call(document.querySelectorAll('.tile'));
  if(!tiles.length) return;
  var lb = document.getElementById('lightbox');
  var lbImg = document.getElementById('lbImg');
  var lbText = document.getElementById('lbText');
  var current = -1;
  function render(){
    var t = tiles[current];
    lbImg.src = t.dataset.full;
    lbImg.alt = t.dataset.caption;
    lbText.textContent = t.dataset.caption;
  }
  function open(idx){ current = idx; render(); lb.classList.add('open'); lb.setAttribute('aria-hidden','false'); document.body.style.overflow='hidden'; }
  function close(){ lb.classList.remove('open'); lb.setAttribute('aria-hidden','true'); document.body.style.overflow=''; }
  function step(d){ current = (current + d + tiles.length) % tiles.length; render(); }
  tiles.forEach(function(t, i){ t.addEventListener('click', function(){ open(i); }); });
  document.getElementById('lbClose').addEventListener('click', close);
  document.getElementById('lbPrev').addEventListener('click', function(){ step(-1); });
  document.getElementById('lbNext').addEventListener('click', function(){ step(1); });
  lb.addEventListener('click', function(e){ if(e.target === lb) close(); });
  document.addEventListener('keydown', function(e){
    if(!lb.classList.contains('open')) return;
    if(e.key === 'Escape') close();
    if(e.key === 'ArrowRight') step(1);
    if(e.key === 'ArrowLeft') step(-1);
  });
})();
"""

LIGHTBOX_HTML = """
<div class="lightbox" id="lightbox" role="dialog" aria-modal="true" aria-hidden="true">
  <button class="lb-btn lb-close" id="lbClose" aria-label="Close"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
  <button class="lb-btn lb-prev" id="lbPrev" aria-label="Previous photo"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 5l-7 7 7 7"/></svg></button>
  <button class="lb-btn lb-next" id="lbNext" aria-label="Next photo"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 5l7 7-7 7"/></svg></button>
  <figure class="lb-figure"><img id="lbImg" src="" alt=""><figcaption class="lb-cap" id="lbText"></figcaption></figure>
</div>
"""

FONT_LINK = '<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400;1,6..72,500&family=Libre+Franklin:wght@400;500;600;700&display=swap" rel="stylesheet">'

def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

def page_shell(title, description, body, css_href="assets/style.css", root_prefix=""):
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
{FONT_LINK}
<link rel="stylesheet" href="{css_href}">
</head>
<body>
{body}
</body>
</html>"""

def topbar(root_prefix, show_home=True):
    home_link = f"{root_prefix}index.html" if root_prefix else "index.html"
    contact_link = f"{root_prefix}contact/index.html" if root_prefix else "contact/index.html"
    btn = f'''<a class="home-btn" href="{home_link}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 11l9-8 9 8M5 10v10h14V10"/></svg>Home</a>''' if show_home else ""
    return f'''<div class="topbar"><div class="topbar-inner">{btn}<span class="topbar-title">Kellyart Photography</span><a class="contact-link" href="{contact_link}">Contact</a></div></div>'''

def build_site(state, log=print):
    site = state["site"]
    albums = [a for a in state["albums"] if any(p.get("include", True) for p in a["photos"])]
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    (DOCS_DIR / "assets").mkdir(parents=True)
    (DOCS_DIR / "assets" / "style.css").write_text(STYLE_CSS, encoding="utf-8")
    (DOCS_DIR / "assets" / "gallery.js").write_text(GALLERY_JS, encoding="utf-8")

    warnings = []
    album_covers = {}

    giscus_ready = not (GISCUS_REPO_ID.startswith("REPLACE_") or GISCUS_CATEGORY_ID.startswith("REPLACE_"))
    comments_html = ""
    if giscus_ready:
        comments_html = f'''
<div class="comments-wrap">
  <h3>Comments</h3>
  <script src="https://giscus.app/client.js"
    data-repo="{GISCUS_REPO}"
    data-repo-id="{GISCUS_REPO_ID}"
    data-category="{GISCUS_CATEGORY}"
    data-category-id="{GISCUS_CATEGORY_ID}"
    data-mapping="pathname"
    data-strict="0"
    data-reactions-enabled="1"
    data-emit-metadata="0"
    data-input-position="bottom"
    data-theme="preferred_color_scheme"
    data-lang="en"
    crossorigin="anonymous"
    async>
  </script>
</div>'''
    else:
        warnings.append("Comments are not set up yet — giscus IDs are still placeholders (see README.md).")

    for album in albums:
        out_dir = DOCS_DIR / album["key"]
        img_dir = out_dir / "img"
        img_dir.mkdir(parents=True, exist_ok=True)
        tiles_html = []
        cover_rel = None
        for photo in album["photos"]:
            if not photo.get("include", True):
                continue
            src = Path(album["sourceFolder"]) / photo["file"]
            if not src.exists():
                warnings.append(f"Missing file, skipped: {src}")
                continue
            base = slugify(Path(photo["file"]).stem)
            thumb_name, full_name = f"{base}_thumb.jpg", f"{base}_full.jpg"
            try:
                thumb_bytes, _ = resized_jpeg_bytes(src, THUMB_MAX, THUMB_QUALITY)
                full_bytes, _ = resized_jpeg_bytes(src, FULL_MAX, FULL_QUALITY)
            except Exception as e:
                warnings.append(f"Could not process {src}: {e}")
                continue
            (img_dir / thumb_name).write_bytes(thumb_bytes)
            (img_dir / full_name).write_bytes(full_bytes)
            if cover_rel is None:
                cover_rel = f"{album['key']}/img/{thumb_name}"
            cap = esc(photo.get("caption", ""))
            tiles_html.append(
                f'<button class="tile" type="button" data-full="img/{full_name}" data-caption="{cap}" aria-label="Open photo: {cap}">'
                f'<img src="img/{thumb_name}" loading="lazy" alt="{cap}, {esc(album["title"])}">'
                f'<span class="tile-cap">{cap}</span></button>'
            )
        if cover_rel:
            album_covers[album["key"]] = cover_rel

        n_photos = len(tiles_html)
        body = topbar("../") + f'''
<main>
  <div class="album-head">
    <div class="album-head-text"><h2>{esc(album["title"])}</h2><p>{esc(album.get("blurb",""))}</p></div>
    <span class="album-count">{n_photos} photograph{"s" if n_photos != 1 else ""}</span>
  </div>
  <div class="grid">{''.join(tiles_html)}</div>
</main>
{comments_html}
<footer><span>&copy; {time.strftime("%Y")} Kellyart Photography &middot; Lake District, England</span><a href="../index.html" class="home-btn">Home</a></footer>
{LIGHTBOX_HTML}
<script src="../assets/gallery.js"></script>
'''
        html = page_shell(f'{album["title"]} — Kellyart Photography', album.get("blurb",""), body, css_href="../assets/style.css")
        (out_dir / "index.html").write_text(html, encoding="utf-8")
        log(f"Built {album['key']}/index.html ({len(tiles_html)} photos)")

    # Home page
    hero = site.get("hero", {})
    hero_rel = None
    hero_album = next((a for a in albums if a["key"] == hero.get("album")), albums[0] if albums else None)
    if hero_album:
        hero_file = hero.get("photo")
        match = next((p for p in hero_album["photos"] if p["file"] == hero_file and p.get("include", True)), None)
        if match:
            base = slugify(Path(match["file"]).stem)
            hero_rel = f'{hero_album["key"]}/img/{base}_full.jpg'
        elif hero_album["key"] in album_covers:
            hero_rel = album_covers[hero_album["key"]]

    cards = []
    for a in albums:
        cover = album_covers.get(a["key"])
        if not cover:
            continue
        n = sum(1 for p in a["photos"] if p.get("include", True))
        cards.append(
            f'<a class="card" href="{a["key"]}/index.html">'
            f'<img src="{cover}" loading="lazy" alt="{esc(a["title"])}">'
            f'<div class="card-label"><span>{n} photograph{"s" if n!=1 else ""}</span><h3>{esc(a["title"])}</h3></div>'
            f'</a>'
        )

    quicklinks = ''.join(
        f'<a href="{a["key"]}/index.html">{esc(a["title"])}</a>'
        for a in albums if a["key"] in album_covers
    )

    eyebrow = site.get("eyebrow") or "Lake District · England"
    home_body = f'''
<header class="hero" id="top" style="--hero-img:url('{hero_rel or ""}')">
  <div class="hero-inner">
    <div class="hero-eyebrow">{esc(eyebrow)}</div>
    <h1>{esc(site["title"])}</h1>
    <p>{esc(site["tagline"])}</p>
  </div>
</header>
<nav class="quicklinks-bar" aria-label="Select a project">
  <div class="quicklinks-inner">
    <span class="quicklinks-label">Select a Project</span>
    <div class="quicklinks-links">{quicklinks}</div>
  </div>
</nav>
<main>
  <div class="card-grid">{''.join(cards)}</div>
</main>
<footer><span>&copy; {time.strftime("%Y")} Kellyart Photography &middot; Lake District, England</span></footer>
<script src="assets/gallery.js"></script>
'''
    home_html = page_shell(site["title"], site["tagline"], topbar("", show_home=False) + home_body, css_href="assets/style.css")
    (DOCS_DIR / "index.html").write_text(home_html, encoding="utf-8")

    # Contact page
    formspree_ready = not FORMSPREE_FORM_ID.startswith("REPLACE_")
    if formspree_ready:
        contact_field_html = f'''<form class="contact-form" action="https://formspree.io/f/{FORMSPREE_FORM_ID}" method="POST">
      <label>Name<input type="text" name="name" required></label>
      <label>Email<input type="email" name="_replyto" required></label>
      <label>Message<textarea name="message" required></textarea></label>
      <button type="submit">Send message</button>
    </form>'''
    else:
        warnings.append("The contact form is not set up yet — FORMSPREE_FORM_ID is still a placeholder (see README.md); showing a plain email link instead.")
        contact_field_html = f'<p class="contact-fallback">Drop me a line at <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> — I read every message.</p>'

    contact_body = topbar("../") + f'''
<main>
  <div class="contact-wrap">
    <h2>Get in touch</h2>
    <p>Questions about a print, a location, or just want to say hello? Send a message below.</p>
    {contact_field_html}
  </div>
</main>
<footer><span>&copy; {time.strftime("%Y")} Kellyart Photography &middot; Lake District, England</span><a href="../index.html" class="home-btn">Home</a></footer>
'''
    contact_html = page_shell("Contact — Kellyart Photography", "Get in touch about prints, locations or feedback.", contact_body, css_href="../assets/style.css")
    (DOCS_DIR / "contact").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "contact" / "index.html").write_text(contact_html, encoding="utf-8")
    log("Built contact/index.html")

    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    log(f"Built index.html ({len(cards)} albums)")
    return {"albums": len(albums), "warnings": warnings}

# ----------------------------------------------------------------------------
# Git publish
# ----------------------------------------------------------------------------

def run(cmd, cwd=APP_DIR):
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")

def have_gh():
    return shutil.which("gh") is not None

def publish(state, log=print):
    lines = []
    def L(s):
        lines.append(s); log(s)

    if not (APP_DIR / ".git").exists():
        run(["git", "init"])
        run(["git", "branch", "-M", "main"])
        L("Initialised git repository.")

    rc, out = run(["git", "remote", "get-url", "origin"])
    if rc != 0:
        user = state["site"]["github"]["user"]
        repo = state["site"]["github"]["repo"]
        if have_gh():
            L(f"No remote yet — trying to create GitHub repo {user}/{repo} with gh...")
            rc2, out2 = run(["gh", "repo", "create", f"{user}/{repo}", "--public", "--source=.", "--remote=origin"])
            L(out2.strip())
            if rc2 != 0:
                L("Could not create the repo automatically. Create it yourself at github.com/new, "
                  f"then run: git remote add origin git@github.com:{user}/{repo}.git")
                return {"ok": False, "log": "\n".join(lines)}
            # try to enable Pages from /docs on main
            run(["gh", "api", f"repos/{user}/{repo}/pages", "-X", "POST",
                 "-f", "source[branch]=main", "-f", "source[path]=/docs"])
        else:
            L(f"No git remote configured and the gh CLI isn't available. Create a repo named "
              f"'{repo}' on github.com, then run:\n  git remote add origin git@github.com:{user}/{repo}.git")
            return {"ok": False, "log": "\n".join(lines)}
    else:
        L(f"Using existing remote: {out.strip()}")

    run(["git", "add", "-A"])
    rc, out = run(["git", "commit", "-m", f"Update gallery — {time.strftime('%Y-%m-%d %H:%M')}"])
    L(out.strip() or "Nothing to commit.")
    rc, out = run(["git", "push", "-u", "origin", "main"])
    L(out.strip())
    if rc != 0:
        return {"ok": False, "log": "\n".join(lines)}
    user = state["site"]["github"]["user"]
    repo = state["site"]["github"]["repo"]
    url = f"https://{user}.github.io/{repo}/"
    L(f"Published. Once GitHub Pages finishes deploying (usually under a minute), your site will be live at:\n{url}")
    return {"ok": True, "log": "\n".join(lines), "url": url}

# ----------------------------------------------------------------------------
# Browsing the photo library
# ----------------------------------------------------------------------------

def browse(path):
    p = Path(path) if path else Path(DEFAULT_ROOT)
    if not p.exists() or not p.is_dir():
        return {"path": str(p), "folders": [], "images": [], "error": "Folder not found"}
    folders, images = [], []
    try:
        for entry in sorted(p.iterdir(), key=lambda e: e.name.lower()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                folders.append(entry.name)
            elif entry.suffix.lower() in IMG_EXTS and entry.stat().st_size > 100_000:
                images.append(entry.name)
    except PermissionError:
        return {"path": str(p), "folders": [], "images": [], "error": "Permission denied"}
    parent = str(p.parent) if str(p) != str(p.anchor) else None
    return {"path": str(p), "parent": parent, "folders": folders, "images": images}

# ----------------------------------------------------------------------------
# Embedded curation UI
# ----------------------------------------------------------------------------

UI_HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kellyart Photography — Curator</title>
<style>
:root{--bg:#F4F4F1;--surface:#fff;--line:#DCDED6;--ink:#242923;--ink-soft:#66705F;--moss:#3F5741;--moss-ink:#fff;--danger:#9A3B34;}
*{box-sizing:border-box;} body{margin:0;font-family:-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--ink);}
header{display:flex;align-items:center;justify-content:space-between;padding:1rem 1.4rem;background:var(--surface);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:10;}
header h1{font-size:1.05rem;margin:0;}
.actions{display:flex;gap:0.6rem;}
button{font-family:inherit;cursor:pointer;border-radius:7px;border:1px solid var(--line);background:var(--surface);padding:0.55rem 1rem;font-size:0.88rem;}
button.primary{background:var(--moss);color:var(--moss-ink);border-color:var(--moss);}
button:disabled{opacity:0.5;cursor:default;}
.layout{display:grid;grid-template-columns:280px 1fr;min-height:calc(100vh - 61px);}
nav.albums{border-right:1px solid var(--line);padding:1rem;overflow-y:auto;}
nav.albums h2{font-size:0.75rem;text-transform:uppercase;letter-spacing:0.06em;color:var(--ink-soft);margin:0 0 0.6rem;}
.album-item{display:flex;justify-content:space-between;align-items:center;padding:0.55rem 0.6rem;border-radius:6px;cursor:pointer;font-size:0.9rem;}
.album-item:hover{background:var(--bg);}
.album-item.active{background:var(--moss);color:var(--moss-ink);}
.album-item small{opacity:0.7;}
main{padding:1.4rem 1.8rem;overflow-y:auto;}
.field{margin-bottom:0.8rem;}
.field label{display:block;font-size:0.76rem;text-transform:uppercase;letter-spacing:0.04em;color:var(--ink-soft);margin-bottom:0.25rem;}
.field input, .field textarea{width:100%;padding:0.5rem 0.6rem;border:1px solid var(--line);border-radius:6px;font-family:inherit;font-size:0.92rem;}
.row{display:flex;gap:1rem;}
.row .field{flex:1;}
.photo-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:1rem;margin-top:1rem;}
.photo{border:1px solid var(--line);border-radius:8px;overflow:hidden;background:var(--surface);}
.photo img{width:100%;height:130px;object-fit:cover;display:block;background:#eee;}
.photo.excluded img{opacity:0.35;}
.photo-body{padding:0.5rem 0.6rem;}
.photo-body input{width:100%;border:1px solid transparent;background:transparent;font-size:0.82rem;padding:0.2rem;}
.photo-body input:focus{border-color:var(--line);background:var(--bg);}
.photo-controls{display:flex;justify-content:space-between;align-items:center;margin-top:0.3rem;}
.photo-controls label{font-size:0.76rem;display:flex;align-items:center;gap:0.3rem;}
.hero-radio{font-size:0.72rem;color:var(--ink-soft);}
.browser{border:1px solid var(--line);border-radius:8px;padding:0.9rem;margin-top:1rem;background:var(--surface);}
.browser .path{font-size:0.8rem;color:var(--ink-soft);margin-bottom:0.5rem;word-break:break-all;}
.browser ul{list-style:none;margin:0;padding:0;max-height:220px;overflow-y:auto;}
.browser li{padding:0.35rem 0.4rem;border-radius:5px;cursor:pointer;font-size:0.88rem;}
.browser li:hover{background:var(--bg);}
.pick-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:0.5rem;margin-top:0.6rem;max-height:260px;overflow-y:auto;}
.pick-list label{font-size:0.72rem;display:flex;flex-direction:column;gap:0.2rem;align-items:center;}
.pick-list img{width:100%;height:70px;object-fit:cover;border-radius:5px;border:2px solid transparent;}
.pick-list input:checked + img{border-color:var(--moss);}
.log{white-space:pre-wrap;font-family:ui-monospace,monospace;font-size:0.78rem;background:#161b16;color:#d8ecd8;padding:0.9rem;border-radius:8px;margin-top:1rem;max-height:260px;overflow-y:auto;}
.hidden{display:none;}
.badge{font-size:0.72rem;padding:0.15rem 0.5rem;border-radius:999px;background:var(--bg);color:var(--ink-soft);}
.toast{position:fixed;bottom:1.2rem;right:1.2rem;background:var(--ink);color:#fff;padding:0.7rem 1rem;border-radius:8px;font-size:0.85rem;opacity:0;transform:translateY(6px);transition:all 0.2s ease;}
.toast.show{opacity:1;transform:translateY(0);}
</style></head>
<body>
<header>
  <h1>Kellyart Photography — Curator</h1>
  <div class="actions">
    <button id="btnBuild">Build site</button>
    <button id="btnPublish" class="primary">Publish</button>
  </div>
</header>
<div class="layout">
  <nav class="albums">
    <div id="siteSettingsBtn" class="album-item" style="margin-bottom:1rem;border-bottom:1px solid var(--line);padding-bottom:0.9rem;"><span>&#9998; Home page text</span></div>
    <h2>Albums</h2>
    <div id="albumList"></div>
    <button id="btnNewAlbum" style="width:100%;margin-top:0.8rem;">+ New album from folder</button>
  </nav>
  <main>
    <div id="albumEditor"></div>
    <div id="newAlbumPanel" class="browser hidden"></div>
    <div id="logPanel" class="log hidden"></div>
  </main>
</div>
<div class="toast" id="toast"></div>
<script>
var state = null;
var activeAlbum = null;
var showSiteEditor = false;

function toast(msg){
  var t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(function(){ t.classList.remove('show'); }, 2600);
}

function api(path, opts){
  return fetch(path, opts).then(function(r){ return r.json(); });
}

function load(){
  api('/api/state').then(function(s){ state = s; if(!activeAlbum && state.albums.length) activeAlbum = state.albums[0].key; render(); });
}

function save(){
  return api('/api/state', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(state)});
}

function render(){
  renderAlbumList();
  renderEditor();
}

function renderAlbumList(){
  var siteBtn = document.getElementById('siteSettingsBtn');
  siteBtn.classList.toggle('active', showSiteEditor);
  var el = document.getElementById('albumList');
  el.innerHTML = '';
  state.albums.forEach(function(a){
    var n = a.photos.filter(function(p){return p.include;}).length;
    var div = document.createElement('div');
    div.className = 'album-item' + (!showSiteEditor && a.key === activeAlbum ? ' active' : '');
    div.innerHTML = '<span>' + a.title + '</span><small>' + n + '</small>';
    div.addEventListener('click', function(){ showSiteEditor = false; activeAlbum = a.key; document.getElementById('newAlbumPanel').classList.add('hidden'); render(); });
    el.appendChild(div);
  });
}

function renderSiteEditor(){
  var el = document.getElementById('albumEditor');
  el.innerHTML =
    '<div class="field"><label>Subtitle (small text above the title)</label><input id="fSiteEyebrow" value="' + escAttr(state.site.eyebrow || 'Lake District · England') + '"></div>' +
    '<div class="field"><label>Site title</label><input id="fSiteTitle" value="' + escAttr(state.site.title) + '"></div>' +
    '<div class="field"><label>Home page blurb</label><textarea id="fSiteTagline" rows="3">' + escHtml(state.site.tagline || '') + '</textarea></div>' +
    '<p style="font-size:0.82rem;color:var(--ink-soft);max-width:34rem;">These are what visitors see on the hero image at the top of your home page. Changes save automatically — click Build site, then Publish, to make them live.</p>';
  el.querySelector('#fSiteEyebrow').addEventListener('change', function(e){ state.site.eyebrow = e.target.value; save(); toast('Saved.'); });
  el.querySelector('#fSiteTitle').addEventListener('change', function(e){ state.site.title = e.target.value; save(); toast('Saved.'); });
  el.querySelector('#fSiteTagline').addEventListener('change', function(e){ state.site.tagline = e.target.value; save(); toast('Saved.'); });
}

function renderEditor(){
  var el = document.getElementById('albumEditor');
  if(showSiteEditor){ renderSiteEditor(); return; }
  var album = state.albums.find(function(a){ return a.key === activeAlbum; });
  if(!album){ el.innerHTML = '<p>No album selected.</p>'; return; }
  el.innerHTML = '';

  var head = document.createElement('div');
  head.innerHTML =
    '<div class="row">' +
      '<div class="field"><label>Album title</label><input id="fTitle" value="' + escAttr(album.title) + '"></div>' +
      '<div class="field"><label>Key (URL slug)</label><input id="fKey" value="' + escAttr(album.key) + '"></div>' +
    '</div>' +
    '<div class="field"><label>Blurb</label><textarea id="fBlurb" rows="2">' + escHtml(album.blurb || '') + '</textarea></div>' +
    '<div class="field"><label>Source folder</label><input id="fFolder" value="' + escAttr(album.sourceFolder) + '"></div>' +
    '<div style="margin-top:0.4rem;"><button id="btnAddPhotos">+ Add photos from source folder</button> ' +
    '<button id="btnDeleteAlbum" style="color:#9A3B34;">Delete album</button></div>';
  el.appendChild(head);

  head.querySelector('#fTitle').addEventListener('change', function(e){ album.title = e.target.value; renderAlbumList(); save(); });
  head.querySelector('#fKey').addEventListener('change', function(e){
    var v = e.target.value.trim();
    if(v && v !== album.key){ album.key = v; activeAlbum = v; save(); render(); }
  });
  head.querySelector('#fBlurb').addEventListener('change', function(e){ album.blurb = e.target.value; save(); });
  head.querySelector('#fFolder').addEventListener('change', function(e){ album.sourceFolder = e.target.value; save(); });
  head.querySelector('#btnDeleteAlbum').addEventListener('click', function(){
    if(!confirm('Delete album "' + album.title + '"? This does not delete your original photos.')) return;
    state.albums = state.albums.filter(function(a){ return a.key !== album.key; });
    activeAlbum = state.albums.length ? state.albums[0].key : null;
    save(); render();
  });
  head.querySelector('#btnAddPhotos').addEventListener('click', function(){ openAddPhotos(album); });

  var grid = document.createElement('div');
  grid.className = 'photo-grid';
  album.photos.forEach(function(p, idx){
    var card = document.createElement('div');
    card.className = 'photo' + (p.include ? '' : ' excluded');
    var thumbSrc = '/api/thumb?path=' + encodeURIComponent(album.sourceFolder + '/' + p.file) + '&size=320';
    var isHero = state.site.hero && state.site.hero.album === album.key && state.site.hero.photo === p.file;
    card.innerHTML =
      '<img src="' + thumbSrc + '" loading="lazy">' +
      '<div class="photo-body">' +
        '<input value="' + escAttr(p.caption || '') + '" data-idx="' + idx + '" class="capInput">' +
        '<div class="photo-controls">' +
          '<label><input type="checkbox" class="incChk" data-idx="' + idx + '" ' + (p.include ? 'checked' : '') + '> include</label>' +
          '<label class="hero-radio"><input type="radio" name="hero" class="heroRadio" data-idx="' + idx + '" ' + (isHero ? 'checked' : '') + '> hero</label>' +
        '</div>' +
      '</div>';
    grid.appendChild(card);
  });
  el.appendChild(grid);

  grid.querySelectorAll('.capInput').forEach(function(inp){
    inp.addEventListener('change', function(){ album.photos[+inp.dataset.idx].caption = inp.value; save(); });
  });
  grid.querySelectorAll('.incChk').forEach(function(chk){
    chk.addEventListener('change', function(){ album.photos[+chk.dataset.idx].include = chk.checked; save(); renderEditor(); });
  });
  grid.querySelectorAll('.heroRadio').forEach(function(r){
    r.addEventListener('change', function(){
      state.site.hero = {album: album.key, photo: album.photos[+r.dataset.idx].file};
      save(); toast('Homepage hero photo set.');
    });
  });
}

function openAddPhotos(album){
  var panel = document.getElementById('newAlbumPanel');
  panel.classList.remove('hidden');
  panel.dataset.mode = 'add';
  panel.dataset.targetKey = album.key;
  renderBrowser(panel, album.sourceFolder);
  panel.scrollIntoView({behavior:'smooth'});
}

document.getElementById('siteSettingsBtn').addEventListener('click', function(){
  showSiteEditor = true; activeAlbum = null;
  document.getElementById('newAlbumPanel').classList.add('hidden');
  render();
});

document.getElementById('btnNewAlbum').addEventListener('click', function(){
  var panel = document.getElementById('newAlbumPanel');
  panel.classList.remove('hidden');
  panel.dataset.mode = 'new';
  panel.dataset.targetKey = '';
  renderBrowser(panel, state.site.root);
});

function renderBrowser(panel, path){
  panel.dataset.currentPath = path;
  api('/api/browse?path=' + encodeURIComponent(path)).then(function(res){
    var html = '<div class="path">' + escHtml(res.path) + '</div><ul>';
    if(res.parent){ html += '<li data-nav="' + escAttr(res.parent) + '">.. (up)</li>'; }
    res.folders.forEach(function(f){ html += '<li data-nav="' + escAttr(res.path + '/' + f) + '">&#128193; ' + escHtml(f) + '</li>'; });
    html += '</ul>';
    if(res.images.length){
      html += '<div style="margin-top:0.5rem;font-size:0.82rem;color:var(--ink-soft);">' + res.images.length + ' photo(s) in this folder</div>';
      html += '<div class="pick-list">';
      res.images.forEach(function(img, i){
        var thumbSrc = '/api/thumb?path=' + encodeURIComponent(res.path + '/' + img) + '&size=200';
        html += '<label><input type="checkbox" class="pickChk" value="' + escAttr(img) + '" checked style="display:none;">' +
                '<img src="' + thumbSrc + '" loading="lazy">' + escHtml(img.slice(0,14)) + '</label>';
      });
      html += '</div>';
      html += '<div class="row" style="margin-top:0.7rem;">' +
        (panel.dataset.mode === 'new' ? '<div class="field"><label>New album title</label><input id="newAlbumTitle" placeholder="e.g. Wastwater"></div>' : '') +
        '</div>' +
        '<button id="btnConfirmAdd" class="primary" style="margin-top:0.4rem;">' +
          (panel.dataset.mode === 'new' ? 'Create album with selected photos' : 'Add selected photos') +
        '</button> <button id="btnCancelBrowse">Cancel</button>';
    }
    panel.innerHTML = html;
    panel.querySelectorAll('li[data-nav]').forEach(function(li){
      li.addEventListener('click', function(){ renderBrowser(panel, li.dataset.nav); });
    });
    var confirmBtn = panel.querySelector('#btnConfirmAdd');
    if(confirmBtn){
      confirmBtn.addEventListener('click', function(){ confirmAddPhotos(panel); });
    }
    var cancelBtn = panel.querySelector('#btnCancelBrowse');
    if(cancelBtn){ cancelBtn.addEventListener('click', function(){ panel.classList.add('hidden'); }); }
  });
}

function confirmAddPhotos(panel){
  var checked = Array.prototype.slice.call(panel.querySelectorAll('.pickChk')).filter(function(c){ return c.checked; }).map(function(c){ return c.value; });
  if(!checked.length){ toast('Select at least one photo.'); return; }
  var path = panel.dataset.currentPath;
  var photos = checked.map(function(f){ return {file: f, caption: f.replace(/\\.[a-zA-Z0-9]+$/, ''), include: true}; });
  if(panel.dataset.mode === 'new'){
    var title = document.getElementById('newAlbumTitle').value.trim() || 'New album';
    var key = title.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || ('album-' + Date.now());
    state.albums.push({key: key, title: title, blurb: '', sourceFolder: path, photos: photos});
    activeAlbum = key;
  } else {
    var album = state.albums.find(function(a){ return a.key === panel.dataset.targetKey; });
    var existing = album.photos.map(function(p){ return p.file; });
    photos.forEach(function(p){ if(existing.indexOf(p.file) === -1) album.photos.push(p); });
  }
  panel.classList.add('hidden');
  save(); render();
  toast('Photos added.');
}

function escHtml(s){ return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
function escAttr(s){ return escHtml(s).replace(/"/g,'&quot;'); }

document.getElementById('btnBuild').addEventListener('click', function(){
  var log = document.getElementById('logPanel');
  log.classList.remove('hidden'); log.textContent = 'Building...';
  api('/api/build', {method:'POST'}).then(function(res){
    log.textContent = 'Built ' + res.albums + ' album page(s).' + (res.warnings.length ? '\\n\\nWarnings:\\n' + res.warnings.join('\\n') : '\\n\\nNo warnings.');
    toast('Site built into ./docs');
  });
});

document.getElementById('btnPublish').addEventListener('click', function(){
  var log = document.getElementById('logPanel');
  log.classList.remove('hidden'); log.textContent = 'Building, then publishing to GitHub...';
  api('/api/build', {method:'POST'}).then(function(){
    return api('/api/publish', {method:'POST'});
  }).then(function(res){
    log.textContent = res.log + (res.url ? '\\n\\nLive at: ' + res.url : '');
    toast(res.ok ? 'Published!' : 'Publish needs one manual step — see log.');
  });
});

load();
</script>
</body></html>
"""

# ----------------------------------------------------------------------------
# HTTP server
# ----------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        if parsed.path == "/":
            self._send(200, UI_HTML, "text/html")
        elif parsed.path == "/api/state":
            self._send(200, load_state())
        elif parsed.path == "/api/browse":
            path = unquote(qs.get("path", [DEFAULT_ROOT])[0])
            self._send(200, browse(path))
        elif parsed.path == "/api/thumb":
            path = unquote(qs.get("path", [""])[0])
            size = int(qs.get("size", [str(THUMB_MAX)])[0])
            try:
                data = cached_thumb(path, size, THUMB_QUALITY)
                self._send(200, data, "image/jpeg")
            except Exception as e:
                self._send(404, {"error": str(e)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b""
        if parsed.path == "/api/state":
            state = json.loads(raw)
            save_state(state)
            self._send(200, {"ok": True})
        elif parsed.path == "/api/build":
            state = load_state()
            result = build_site(state)
            self._send(200, result)
        elif parsed.path == "/api/publish":
            state = load_state()
            result = publish(state)
            self._send(200, result)
        else:
            self._send(404, {"error": "not found"})

def main():
    load_state()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"\nKellyart Photography curator running at {url}\n(Ctrl+C to stop)\n")
    threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")

if __name__ == "__main__":
    main()
