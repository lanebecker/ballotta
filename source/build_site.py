"""Build the Ballotta site from template-travis.html and the routing data.

    python3 source/build_site.py             # index.html: the live site
    python3 source/build_site.py --preview   # next/: the same page with the phone layout on (and its Home Screen files); counts nothing

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
# The phone layout (narrower than 1024px: the laptop app folded up, plus Add to Home Screen and an offline copy) is
# marked the same way: /*PHONE*/ ... /*/PHONE*/ and <!--PHONE--> ... <!--/PHONE-->. Until Lane approves the preview at
# ballotta.org/next/, the live build removes every marked block, so index.html stays byte-for-byte what it was.
# Promotion: set PHONE_LIVE = True (docs/plans/2026-10-15-phone-layout.md, Task 13).
PHONE_LIVE = False
# The offline copy (sw.js). False writes a sw.js that removes itself and its copies from every phone that has it, and
# the page stops installing it: the switch to pull if offline copies ever cause trouble. Rebuild and push to apply.
OFFLINE = True


def marks(tag):
    return r'(?:/\*' + tag + r'\*/|<!--' + tag + r'-->)', r'(?:/\*/' + tag + r'\*/|<!--/' + tag + r'-->)'


def strip_marked(html, tag):
    """Remove every block marked with tag (DESK or PHONE). A marker alone on its line (spaces or tabs around it,
    nothing else) opens or closes a block of whole lines; a marker pair inside a line removes just the text between
    and including them. One loop both checks and removes; a marker that is neither alone nor in a one-line pair
    stops the build."""
    OPEN, CLOSE = marks(tag)
    ALONE_OPEN, ALONE_CLOSE = re.compile(r'[ \t]*' + OPEN + r'[ \t]*'), re.compile(r'[ \t]*' + CLOSE + r'[ \t]*')
    opens, closes = len(re.findall(OPEN, html)), len(re.findall(CLOSE, html))
    assert opens == closes, f"{tag} markers unpaired: {opens} open, {closes} close"
    pairs = re.findall(r'/\*' + tag + r'\*/|/\*/' + tag + r'\*/|<!--' + tag + r'-->|<!--/' + tag + r'-->', html)
    for a, z in zip(pairs[0::2], pairs[1::2]):  # in order, each opener is closed in its own syntax (CSS/JS or HTML)
        assert a.startswith('/*') == z.startswith('/*') and '/' + tag not in a and '/' + tag in z, f"{tag} markers mismatched: {a} … {z}"
    out, in_block = [], False
    for n, line in enumerate(html.split('\n'), 1):
        if ALONE_OPEN.fullmatch(line):
            assert not in_block, f"line {n}: a {tag} block opens inside another (is a closing marker sharing its line?)"
            in_block = True
        elif ALONE_CLOSE.fullmatch(line):
            assert in_block, f"line {n}: a {tag} block closes without opening"
            in_block = False
        elif not in_block:
            out.append(line)
        else:
            assert not re.search(OPEN + '|' + CLOSE, line), f"line {n}: a {tag} marker inside a block isn't alone on its line"
    assert not in_block, f"a {tag} block is never closed (is its closing marker sharing its line with other characters?)"
    html = re.sub(OPEN + r'[^\n]*?' + CLOSE, '', '\n'.join(out))
    assert not re.search(OPEN + '|' + CLOSE, html), f"a {tag} marker survived stripping"
    return html


def strip_desk(html):
    return strip_marked(html, 'DESK')


def strip_phone(html):
    return strip_marked(html, 'PHONE')


# ---- Content-Security-Policy (#36). Only the page's own inline scripts (by hash) and files from this site run; data
# goes only to the county map server and the counting service; frames only from this site (the Census sandbox).
PAGE_CSP = ("default-src 'none'; script-src 'self' {hashes}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
            "connect-src https://taxmaps.traviscountytx.gov https://gateway.umami.is; frame-src 'self'; base-uri 'none'; form-action 'none'")


def sha(js):
    return "'sha256-" + base64.b64encode(hashlib.sha256(js.encode("utf-8")).digest()).decode() + "'"


# The phone layout adds two: its Home Screen description (manifest.webmanifest) and its offline copy (sw.js), both
# from this site only.
PHONE_CSP = "; manifest-src 'self'; worker-src 'self'"


def csp_meta(html, phone=False):
    hashes = " ".join(sha(s) for s in re.findall(r"<script>(.*?)</script>", html, re.S))
    return '<meta http-equiv="Content-Security-Policy" content="' + PAGE_CSP.format(hashes=hashes) + (PHONE_CSP if phone else '') + '">'


# ---- Add to Home Screen (phone layout). The manifest names the app and its icons; paths are relative to it, so the
# preview's copy (next/) and the live one (/) are two different apps on a phone: "Ballotta (preview)" and "Ballotta".
def manifest(preview=False):
    up = '../' if preview else ''
    return json.dumps({
        "id": "./", "start_url": "./", "scope": "./", "display": "standalone",
        "name": "Ballotta (preview)" if preview else "Ballotta", "short_name": "Ballotta",
        "description": "Your Travis County ballot for Nov 3, 2026, with private picks and a printable crib sheet.",
        "background_color": "#4B2A6B", "theme_color": "#4B2A6B",
        "icons": [{"src": up + "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                  {"src": up + "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                  {"src": up + "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
    }, indent=1, ensure_ascii=False) + "\n"


# ---- The offline copy. Network first: online, every request goes to the network as if this file didn't exist, and
# the answer is kept; offline, or with no answer after 4 seconds, the kept copy of that same file is used. Only this
# site's own files are kept (the page, its fonts, icons, the pinned tracker); lookups (the county, the Census) and
# counting always need the network. A #fragment (saved or shared picks) never reaches a service worker.
# The preview (next/) and the live page share one origin, so each keeps its copies under its own name and only ever
# deletes its own: "ballotta-next-…" and "ballotta-…" (Pass 1, B3).
def cache_prefix(preview):
    return 'ballotta-next-' if preview else 'ballotta-'


def sw_js(preview):
    return SW_JS.replace("'ballotta-1'", "'" + cache_prefix(preview) + "1'").replace("PREFIX", cache_prefix(preview))


def sw_off_js(preview):
    return SW_OFF_JS.replace("PREFIX", cache_prefix(preview))


SW_JS = (
    "// Built by source/build_site.py; don't edit sw.js. Ballotta's offline copy: network first, kept copy as a fallback.\n"
    "const CACHE = 'ballotta-1';\n"
    "self.addEventListener('install', () => self.skipWaiting());\n"
    "self.addEventListener('activate', (e) => e.waitUntil(caches.keys()\n"
    "  .then((ks) => Promise.all(ks.filter((k) => k.startsWith('PREFIX') && !k.startsWith('PREFIXnext-') && k !== CACHE).map((k) => caches.delete(k))))\n"
    "  .then(() => self.clients.claim())));\n"
    "self.addEventListener('fetch', (e) => {\n"
    "  const r = e.request, u = new URL(r.url);\n"
    "  if (r.method !== 'GET' || u.origin !== location.origin || r.headers.has('range')) return;  // the browser handles it, as if there were no copy\n"
    "  const key = u.origin + u.pathname;  // one copy per file, whatever ?query a link adds\n"
    "  const net = fetch(r).then((res) => {\n"
    "    if (res.ok && res.type === 'basic') { const copy = res.clone(); e.waitUntil(caches.open(CACHE).then((c) => c.put(key, copy)).catch(() => {})); }\n"
    "    return res;\n"
    "  });\n"
    "  e.waitUntil(net.catch(() => {}));  // a late answer still refreshes the kept copy\n"
    "  e.respondWith(Promise.race([net.catch(() => 'offline'), new Promise((ok) => setTimeout(ok, 4000, 'slow'))])\n"
    "    .then(async (first) => {\n"
    "      if (typeof first !== 'string') return first;  // the network's own answer\n"
    "      const kept = await caches.open(CACHE).then((c) => c.match(key));  // only its own copies\n"
    "      if (!kept) return net;  // nothing kept: wait for the network\n"
    "      const page = r.mode === 'navigate' && (kept.headers.get('content-type') || '').startsWith('text/html');  // never an image or the manifest, even opened directly\n"
    "      return page ? said(kept.clone(), first).catch(() => kept) : kept;\n"
    "    }));\n"
    "});\n"
    "// A page answered from the kept copy says so, and why, before any of its scripts run (Lane, B4): <html data-copy=\"offline\"> or \"slow\".\n"
    "const said = (res, why) => res.text().then((t) => { const h = new Headers(res.headers); h.delete('content-length'); h.delete('content-encoding');\n"
    "  return new Response(t.replace('<html lang=\"en\">', '<html lang=\"en\" data-copy=\"' + why + '\">'), { status: res.status, statusText: res.statusText, headers: h }); });\n")
SW_OFF_JS = (
    "// Built by source/build_site.py: removes Ballotta's offline copy from this browser. It takes the open pages over first,\n"
    "// so the old copy can't keep filling its cache, then deletes its caches (only Ballotta's), then itself.\n"
    "self.addEventListener('install', () => self.skipWaiting());\n"
    "self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim().then(() => caches.keys())\n"
    "  .then((ks) => Promise.all(ks.filter((k) => k.startsWith('PREFIX') && !k.startsWith('PREFIXnext-')).map((k) => caches.delete(k))))\n"
    "  .then(() => self.registration.unregister())));\n")
SW_REGISTER = "if (NARROW.matches && matchMedia('(pointer: coarse)').matches) sw.register('sw.js').catch(() => {});"
# With OFFLINE = False the page, at any width, asks the browser to fetch this folder's sw.js again at once: the
# self-removing one (outputs() always writes it) takes over, deletes its own caches and itself. Nothing is removed on a
# failed fetch: a hiccup, a portal or an outage never costs a phone its copy (Pass 3).
SW_REMOVE = "sw.getRegistration('./').then((g) => g && g.update()).catch(() => {});"


def outputs(preview):
    """Every file one build writes, by path from the repo root. Once the phone layout is live, next/sw.js becomes the
    self-removing worker, so phones that installed the preview drop its copy (a missing sw.js would leave it running)."""
    if preview:
        return {"next/index.html": build(True), "next/manifest.webmanifest": manifest(True),
                "next/sw.js": sw_js(True) if OFFLINE else sw_off_js(True)}
    out = {"index.html": build(False), "census.html": census_page()}
    if PHONE_LIVE:
        out.update({"manifest.webmanifest": manifest(False), "sw.js": sw_js(False) if OFFLINE else sw_off_js(False),
                    "next/sw.js": sw_off_js(True)})
    return out


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


def build(preview=False, desk=None, phone=None):
    """desk: include the laptop layout (default: on for the preview, or once DESK_LIVE). phone: include the phone layout
    (default: on for the preview, or once PHONE_LIVE). The laptop-parity test builds with and without it."""
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
    desk = desk if desk is not None else (preview or DESK_LIVE)
    phone = phone if phone is not None else (preview or PHONE_LIVE)
    assert desk or not phone, "the phone layout is built on the laptop layout's code"
    if not desk:
        html = strip_desk(html)
    if not phone:
        html = strip_phone(html)
    elif not OFFLINE:
        assert html.count(SW_REGISTER) == 1, SW_REGISTER
        html = html.replace(SW_REGISTER, SW_REMOVE)

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
    return html.replace("<!--CSP-->", csp_meta(html, phone), 1)  # last of all: it hashes the finished scripts (#36)


if __name__ == "__main__":
    preview = "--preview" in sys.argv[1:]
    if preview and PHONE_LIVE:
        print("The phone layout is live, and next/index.html is a redirect to the main page: not overwriting it.")
        sys.exit(0)  # not an error, so `--preview && build_site.py` still builds the live page (Pass 2)
    for path, text in outputs(preview).items():  # the page, then the files that sit next to it (#36: census.html)
        out = ROOT / path
        out.parent.mkdir(exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(path, *((len(text) // 1024, "KB") if path.endswith("index.html") else ()))
