"""Build index.html (the GitHub Pages site) from template-travis.html and the routing data.

Run from anywhere:  python3 source/build_site.py
Rebuild rules first if the answer key or district data change:  python3 source/build_rules.py
"""
import json, re, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
# Public address of the site. Switch to "https://ballotta.org/" once the custom domain is live (see README).
BASE_URL = "https://lanebecker.github.io/ballotta/"
# Umami Cloud website ID (anonymous, cookieless counts). Empty string = no analytics script at all.
UMAMI_ID = "51b98962-382e-4070-bbd0-f43aba4143ae"
# Hostnames whose visits count; anything else (local test runs, previews) is ignored by the tracker.
UMAMI_DOMAINS = "ballotta.org,www.ballotta.org,lanebecker.github.io"

key = json.load(open(HERE / "answer_key.json", encoding="utf-8"))
rules = json.load(open(HERE / "rules.json"))
tlc = json.load(open(HERE / "tlc_precincts.json"))
contests = [{k: c[k] for k in ("id", "title", "type", "choices", "level", "entity")}
            | ({"text": c.get("text", "")} if c["type"] == "measure" else {})
            for c in key["contests"]]
learn = json.load(open(HERE / "learn.json", encoding="utf-8"))      # built by build_learn.py
sites = json.load(open(HERE / "vote_sites.json", encoding="utf-8"))  # Travis County Clerk site lists, geocoded
data = json.dumps({"contests": contests, "rules": rules, "tlc": tlc, "learn": learn, "sites": sites}, ensure_ascii=False)
data = data.replace("</", "<\\/")  # never let data close the inline <script>
html = (HERE / "template-travis.html").read_text(encoding="utf-8").replace("__DATA__", data)

# Self-hosted fonts: the only third-party requests are the county and Census lookups.
fonts = ("<style>@font-face{font-family:'Zilla Slab';src:url('fonts/ZillaSlab-SemiBold.woff2') format('woff2');font-weight:600;font-display:swap}"
         "@font-face{font-family:'Zilla Slab';src:url('fonts/ZillaSlab-Bold.woff2') format('woff2');font-weight:700;font-display:swap}"
         "@font-face{font-family:'Public Sans';src:url('fonts/PublicSans-wght.woff2') format('woff2');font-weight:100 900;font-display:swap}</style>")
html = re.sub(r"<!--FONTS-->.*?<!--/FONTS-->", fonts, html, flags=re.S).replace("__OG_IMAGE__", BASE_URL + "og.png")
# Analytics: no URL search or #fragment is ever sent (the fragment is also stripped before this script loads).
# The tracker is a pinned copy of https://cloud.umami.is/script.js (umami.js, fetched 2026-10-14) served from this
# site, so a change on Umami's side can never run new code on this page. It still reports to gateway.umami.is.
analytics = (f'<script defer src="umami.js" data-website-id="{UMAMI_ID}" '
             f'data-domains="{UMAMI_DOMAINS}" data-exclude-search="true" data-exclude-hash="true"></script>') if UMAMI_ID else ""
html = html.replace("<!--ANALYTICS-->", analytics)
(ROOT / "index.html").write_text(html, encoding="utf-8")
print("index.html", len(html) // 1024, "KB")
