"""Build the Ballotta site from template-travis.html and the routing data.

    python3 source/build_site.py             # index.html: the live site
    python3 source/build_site.py --preview   # next/index.html: the same page with the laptop layout on; counts nothing

Rebuild rules first if the answer key or district data change:  python3 source/build_rules.py
"""
import base64, hashlib, json, re, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
# Public address of the site.
BASE_URL = "https://ballotta.org/"
# Umami Cloud website ID (anonymous, cookieless counts). Empty string = no analytics script at all.
UMAMI_ID = "51b98962-382e-4070-bbd0-f43aba4143ae"
# Hostnames whose visits count; anything else (local test runs, previews) is ignored by the tracker.
UMAMI_DOMAINS = "ballotta.org,www.ballotta.org,lanebecker.github.io"
# The laptop layout (1024px and wider) is marked in the template: /*DESK*/ ... /*/DESK*/ in CSS and JS,
# <!--DESK--> ... <!--/DESK--> in HTML. Until Lane approves the preview at ballotta.org/next/, the live build
# removes every marked block, so index.html stays byte-for-byte what it was. Promotion: set DESK_LIVE = True.
DESK_LIVE = True

OPEN, CLOSE = r'(?:/\*DESK\*/|<!--DESK-->)', r'(?:/\*/DESK\*/|<!--/DESK-->)'


ALONE_OPEN, ALONE_CLOSE = re.compile(r'[ \t]*' + OPEN + r'[ \t]*'), re.compile(r'[ \t]*' + CLOSE + r'[ \t]*')


def strip_desk(html):
    """Remove every laptop-layout block. A marker alone on its line (spaces or tabs around it, nothing else) opens or
    closes a block of whole lines; a marker pair inside a line removes just the text between and including them.
    One loop both checks and removes; a marker that is neither alone nor in a one-line pair stops the build."""
    opens, closes = len(re.findall(OPEN, html)), len(re.findall(CLOSE, html))
    assert opens == closes, f"DESK markers unpaired: {opens} open, {closes} close"
    out, in_block = [], False
    for n, line in enumerate(html.split('\n'), 1):
        if ALONE_OPEN.fullmatch(line):
            assert not in_block, f"line {n}: a DESK block opens inside another (is a closing marker sharing its line?)"
            in_block = True
        elif ALONE_CLOSE.fullmatch(line):
            assert in_block, f"line {n}: a DESK block closes without opening"
            in_block = False
        elif not in_block:
            out.append(line)
        else:
            assert not re.search(OPEN + '|' + CLOSE, line), f"line {n}: a DESK marker inside a block isn't alone on its line"
    assert not in_block, "a DESK block is never closed (is its closing marker sharing its line with other characters?)"
    html = re.sub(OPEN + r'[^\n]*?' + CLOSE, '', '\n'.join(out))
    assert not re.search(OPEN + '|' + CLOSE, html), "a DESK marker survived stripping"
    return html


# ---- Content-Security-Policy (#36). Only the page's own inline scripts (by hash) and files from this site run; data
# goes only to the county map server and the counting service; frames only from this site (the Census sandbox).
PAGE_CSP = ("default-src 'none'; script-src 'self' {hashes}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
            "connect-src https://taxmaps.traviscountytx.gov https://gateway.umami.is; frame-src 'self'; base-uri 'none'; form-action 'none'")


def sha(js):
    return "'sha256-" + base64.b64encode(hashlib.sha256(js.encode("utf-8")).digest()).decode() + "'"


def csp_meta(html):
    hashes = " ".join(sha(s) for s in re.findall(r"<script>(.*?)</script>", html, re.S))
    return '<meta http-equiv="Content-Security-Policy" content="' + PAGE_CSP.format(hashes=hashes) + '">'


# ---- census.html (#36): the Census geocoder answers only as JSONP, so the page loads it in this sandboxed frame,
# which can't reach the page or its storage and passes back only a point.
CENSUS_JS = (
    "// Built by source/build_site.py; don't edit census.html. Ballotta's page sends one address;\n"
    "// this frame (sandboxed: no access to the page or its storage) loads the JSONP reply and passes back only a point.\n"
    "window.addEventListener('message', function on(e) {\n"
    "  // Only inside Ballotta's sandbox (an opaque origin), only for its own page, only an address (Pass 1).\n"
    "  if (self.origin !== 'null' || e.source !== parent || typeof e.data !== 'string' || e.data.length > 200) return;\n"
    "  window.removeEventListener('message', on);\n"
    "  window.cb = function (d) {\n"
    "    var m = d && d.result && d.result.addressMatches && d.result.addressMatches[0];\n"
    "    parent.postMessage(m && m.coordinates ? { x: Number(m.coordinates.x), y: Number(m.coordinates.y), label: String(m.matchedAddress || '') } : null, '*');\n"
    "  };\n"
    "  var s = document.createElement('script');\n"
    "  s.src = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?' + new URLSearchParams({ address: e.data, benchmark: 'Public_AR_Current', format: 'jsonp', callback: 'cb' });\n"
    "  s.onerror = function () { parent.postMessage(null, '*'); };\n"
    "  document.head.appendChild(s);\n"
    "});\n")


def census_page():
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="referrer" content="no-referrer">\n'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src ' + sha(CENSUS_JS)
            + ' https://geocoding.geo.census.gov; base-uri \'none\'; form-action \'none\'">\n'
            '<title>Census address lookup</title></head><body>\n<script>' + CENSUS_JS + '</script>\n</body></html>\n')


def build(preview=False, desk=None):
    """desk: include the laptop layout (default: on for the preview, or once DESK_LIVE). The phone-parity test builds both."""
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
    html = (HERE / "template-travis.html").read_text(encoding="utf-8")
    if not (desk if desk is not None else (preview or DESK_LIVE)):
        html = strip_desk(html)

    # Self-hosted fonts: the only third-party requests are the county and Census lookups.
    fonts = ("<style>@font-face{font-family:'Zilla Slab';src:url('fonts/ZillaSlab-SemiBold.woff2') format('woff2');font-weight:600;font-display:swap}"
             "@font-face{font-family:'Zilla Slab';src:url('fonts/ZillaSlab-Bold.woff2') format('woff2');font-weight:700;font-display:swap}"
             "@font-face{font-family:'Public Sans';src:url('fonts/PublicSans-wght.woff2') format('woff2');font-weight:100 900;font-display:swap}</style>")
    html = re.sub(r"<!--FONTS-->.*?<!--/FONTS-->", fonts, html, flags=re.S).replace("__OG_IMAGE__", BASE_URL + "og.png")
    # Analytics: no URL search or #fragment is ever sent (the fragment is also stripped before this script loads).
    # The tracker is a pinned copy of https://cloud.umami.is/script.js (umami.js, fetched 2026-10-14) served from this
    # site, so a change on Umami's side can never run new code on this page. It still reports to gateway.umami.is.
    analytics = (f'<script defer src="umami.js" data-website-id="{UMAMI_ID}" '
                 f'data-domains="{UMAMI_DOMAINS}" data-exclude-search="true" data-exclude-hash="true" '
                 # The privacy firewall in the page checks every payload; Do Not Track is honoured twice (here and there);
                 # page-speed measurements (load time, responsiveness) carry no personal data (Lane, Oct 15).
                 f'data-do-not-track="true" data-before-send="ballottaBeforeSend" data-performance="true"></script>') if UMAMI_ID else ""
    # Fail closed: until the page's own check is defined, the tracker's before-send drops everything.
    if analytics: analytics = '<script>window.ballottaBeforeSend = () => null;</script>' + analytics
    if preview:
        # The preview lives one folder down (next/index.html). It loads the same pinned tracker, so it behaves like the
        # live page, but with a domain list no real site matches: the tracker then never sends anything.
        if analytics:
            analytics = analytics.replace('src="umami.js"', 'src="../umami.js"').replace(f'data-domains="{UMAMI_DOMAINS}"', 'data-domains="preview.invalid"')
            assert 'preview.invalid' in analytics and '../umami.js' in analytics
        html = html.replace("<title>Ballotta ·", "<title>[Preview] Ballotta ·", 1)
        for a, b in [("url('fonts/", "url('../fonts/"), ('href="favicon.svg"', 'href="../favicon.svg"'), ("f.src = 'census.html'", "f.src = '../census.html'"),
                     ('href="apple-touch-icon.png"', 'href="../apple-touch-icon.png"')]:
            assert a in html, a
            html = html.replace(a, b)
    html = html.replace("<!--ANALYTICS-->", analytics)
    # The data goes in last, so nothing in it can be mistaken for one of the placeholders above (#37).
    html = html.replace("__DATA__", data, 1)
    return html.replace("<!--CSP-->", csp_meta(html), 1)  # last of all: it hashes the finished scripts (#36)


if __name__ == "__main__":
    preview = "--preview" in sys.argv[1:]
    if preview and DESK_LIVE:
        print("The laptop layout is live, and next/index.html is a redirect to the main page: not overwriting it.")
        sys.exit(0)  # not an error, so `--preview && build_site.py` still builds the live page (Pass 2)
    html = build(preview)
    out = ROOT / ("next/index.html" if preview else "index.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out.relative_to(ROOT).as_posix(), len(html) // 1024, "KB")
    if not preview:
        (ROOT / "census.html").write_text(census_page(), encoding="utf-8")  # the Census lookup's sandbox (#36)
        print("census.html")
