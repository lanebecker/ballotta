"""Build the Ballotta site from template-travis.html and the routing data.

    python3 source/build_site.py             # index.html: the live site
    python3 source/build_site.py --check     # CI: rebuilds in memory and compares with what is committed; writes nothing (#81)
    python3 source/build_site.py --site DIR  # the Pages workflow: after --check passes, copies only the site's files to DIR (#83)
    python3 source/build_site.py --preview   # next/, while the phone layout isn't live: the page with it on; counts nothing
                                             # (once it is, the main build writes next/: the street map's preview until
                                             # STREETS_LIVE, then a page that sends people on)

Rebuild rules first if the answer key or district data change:  python3 source/build_rules.py
"""
import base64, hashlib, json, re, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import check_release  # VERSION, CHANGELOG.md and version.json in step (source/check_release.py)
# Public address of the site.
BASE_URL = "https://ballotta.org/"
# Umami Cloud website ID (anonymous, cookieless counts). Empty string = no analytics script at all.
UMAMI_ID = "51b98962-382e-4070-bbd0-f43aba4143ae"
# Hostnames whose visits count; anything else (local test runs, previews) is ignored by the tracker.
UMAMI_DOMAINS = "ballotta.org,www.ballotta.org"   # lanebecker.github.io/ballotta redirects to ballotta.org (#85)
# The pinned tracker's sha256 (issue #68): the build refuses a different umami.js, and the tag's integrity= makes
# browsers refuse one too. To update the tracker, review the new copy, then change this, the README and the test.
UMAMI_SHA256 = "91a876d767646fd5b7701b6fabf97f8a99ae53b94e7e5b58d465bad1e5d763e0"
# The laptop layout (1024px and wider) is marked in the template: /*DESK*/ ... /*/DESK*/ in CSS and JS,
# <!--DESK--> ... <!--/DESK--> in HTML. Until Lane approves the preview at ballotta.org/next/, the live build
# removes every marked block, so index.html stays byte-for-byte what it was. Promotion: set DESK_LIVE = True.
DESK_LIVE = True
# The phone layout (narrower than 1024px: the laptop app folded up, plus Add to Home Screen and an offline copy) is
# marked the same way: /*PHONE*/ ... /*/PHONE*/ and <!--PHONE--> ... <!--/PHONE-->. Until Lane approves the preview at
# ballotta.org/next/, the live build removes every marked block, so index.html stays byte-for-byte what it was.
# Promotion: set PHONE_LIVE = True (docs/plans/2026-10-15-phone-layout.md, Task 13). Promoted Oct 17 (Lane): next/
# now only hands people on (moved_page), and its worker removes itself; the main build writes both.
PHONE_LIVE = True
# The offline copy (sw.js). False writes a sw.js that removes itself and its copies from every phone that has it, and
# the page stops installing it: the switch to pull if offline copies ever cause trouble. Rebuild and push to apply.
OFFLINE = True
# The street map (Lane, Oct 19): freeways, highways, major streets and water under the vote-center dots, drawn on the
# device from source/data/streets.json (written by source/fetch_streets.py from the U.S. Census Bureau's TIGER/Line
# files, public domain), so drawing it asks nothing of anyone. Marked /*STREETS*/ ... /*/STREETS*/ and <!--STREETS-->
# ... <!--/STREETS-->, like the two layouts were. Until Lane approves it at ballotta.org/next/, the main build removes
# every marked block, so index.html stays as it was (the street data too), and next/ is a preview again: the main
# page with the street map on, with its own Home Screen app and offline copy, counting nothing. Promotion: set
# STREETS_LIVE = True; next/ then goes back to sending people on (docs/plans/2026-10-19-street-map.md, Task 9).
# Promoted on 2026-10-19 (Lane): the main page has it, and next/ sends people on.
STREETS_LIVE = True


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


def strip_streets(html):
    return strip_marked(html, 'STREETS')


# ---- Content-Security-Policy (#36). Only the page's own inline scripts (by hash) and files from this site run; data
# goes only to the county map server and the counting service; frames only from this site (the Census sandbox).
PAGE_CSP = ("default-src 'none'; script-src 'self' {hashes}; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; "
            "connect-src 'self' https://taxmaps.traviscountytx.gov https://gateway.umami.is; frame-src 'self'; base-uri 'none'; form-action 'none'")


def script_json(obj, compact=False):
    """obj as a JavaScript literal that can sit inside an inline <script> (#85): no "</" (ends the script), no "<!--"
    (changes how the script is parsed), no U+2028/U+2029 (line ends in older JavaScript). Every "<" is written \\u003c,
    which reads back as the same text. compact: no spaces after "," and ":" (the street map's data: a third smaller)."""
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":") if compact else None).replace("<", "\\u003c")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


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
    keep = "['./']" if preview else "['./', 'next/', 'picks/']"   # picks/: where share links go, so the first one opens offline too (1.2.0, Pass 1)
    js = SW_JS
    if not preview and not STREETS_LIVE:   # next/ is the street map's preview (600 KB), not the hand-off page: no phone fetches it unasked,
        keep = "['./', 'picks/']"           # and a hand-off page kept before is dropped, so it is never shown for the preview (Oct 19, Pass 2)
        js = js.replace(STALE_NEXT[0], STALE_NEXT[1], 1)
        assert STALE_NEXT[1] in js
    return js.replace("'ballotta-1'", "'" + cache_prefix(preview) + "1'").replace("PREFIX", cache_prefix(preview)).replace("KEEP.map", keep + ".map")


# While a preview is at next/, the main copy's install also deletes a kept next/ (the old hand-off page) before keeping the rest.
STALE_NEXT = ("e.waitUntil(caches.open(CACHE).then((c) => Promise.all(",
              "e.waitUntil(caches.open(CACHE).then((c) => c.delete(new URL('next/', location.href).href).catch(() => {}).then(() => c)).then((c) => Promise.all(")


def sw_off_js(preview):
    return SW_OFF_JS.replace("PREFIX", cache_prefix(preview))


SW_JS = (
    "// Built by source/build_site.py; don't edit sw.js. Ballotta's offline copy: network first, kept copy as a fallback.\n"
    "const CACHE = 'ballotta-1';\n"
    "// The page keeps a copy of itself from the start, so it opens offline before its next visit, and so does a Home\n"
    "// Screen app that installed the preview, whose next/ now sends it on to ./ (promotion audit #3). Nothing fails if it can't,\n"
    "// and a slow line never holds the install up for more than 8 seconds (no-cache: a 304 when the page hasn't changed).\n"
    "self.addEventListener('install', (e) => { self.skipWaiting(); e.waitUntil(caches.open(CACHE).then((c) => Promise.all(KEEP.map((u) => {\n"
    "  const at = new URL(u, location.href).href, stop = new AbortController(), t = setTimeout(() => stop.abort(), 8000);\n"
    "  return fetch(at, { cache: 'no-cache', signal: stop.signal }).then((res) => res.ok && res.type === 'basic' && !res.redirected && c.put(at, res))\n"
    "    .catch(() => {}).finally(() => clearTimeout(t)); })))); });\n"
    "self.addEventListener('activate', (e) => e.waitUntil(caches.keys()\n"
    "  .then((ks) => Promise.all(ks.filter((k) => k.startsWith('PREFIX') && !k.startsWith('PREFIXnext-') && k !== CACHE).map((k) => caches.delete(k))))\n"
    "  .then(() => self.clients.claim())));\n"
    "self.addEventListener('fetch', (e) => {\n"
    "  const r = e.request, u = new URL(r.url);\n"
    "  if (r.method !== 'GET' || u.origin !== location.origin || r.headers.has('range')) return;  // the browser handles it, as if there were no copy\n"
    "  const key = u.origin + u.pathname.replace(/\\/index\\.html$/, '/');  // one copy per file, whatever ?query a link adds; / and /index.html are one page (#76)\n"
    "  const net = fetch(r).then((res) => {\n"
    "    if (res.ok && res.type === 'basic') { const copy = res.clone(); e.waitUntil(caches.open(CACHE).then((c) => c.put(key, copy)).catch(() => {})); }\n"
    "    return res;\n"
    "  });\n"
    "  e.waitUntil(net.catch(() => {}));  // a late answer still refreshes the kept copy\n"
    "  e.respondWith(Promise.race([net.catch(() => 'offline'), new Promise((ok) => setTimeout(ok, 4000, 'slow'))])\n"
    "    .then(async (first) => {\n"
    "      // A server error (5xx), a timeout or a rate limit (408, 429) inside 4 seconds (a deploy, a proxy) counts as no answer when a copy is kept (#74); a 404 is shown,\n"
    "      // so a page that's really gone is never masked by its copy (Wave 4 Pass 1).\n"
    "      const bad = typeof first !== 'string' && first.type === 'basic' && (first.status >= 500 || first.status === 408 || first.status === 429);\n"
    "      if (typeof first !== 'string' && !bad) return first;  // the network's own answer\n"
    "      const kept = await caches.open(CACHE).then((c) => c.match(key));  // only its own copies\n"
    "      if (!kept) return net;  // nothing kept: wait for the network\n"
    "      const page = r.mode === 'navigate' && (kept.headers.get('content-type') || '').startsWith('text/html');  // never an image or the manifest, even opened directly\n"
    "      return page ? said(kept.clone(), bad ? 'error' : first).catch(() => kept) : kept;\n"
    "    }));\n"
    "});\n"
    "// A page answered from the kept copy says so, and why, before any of its scripts run (Lane, B4): <html data-copy=\"offline\">,\n"
    "// \"slow\" or \"error\". It marks the document's own opening tag, whatever attributes it has, so a template change can't quietly stop it (#75).\n"
    "const said = (res, why) => res.text().then((t) => { const h = new Headers(res.headers); h.delete('content-length'); h.delete('content-encoding');\n"
    "  return new Response(t.replace(/^(\\s*(?:<!--(?:-?>|(?!-?>)(?:(?!-->)[\\s\\S])*-->)\\s*)*(?:<!doctype[^>]*>\\s*)?(?:<!--(?:-?>|(?!-?>)(?:(?!-->)[\\s\\S])*-->)\\s*)*<html)(?=[\\s>])/i, '$1 data-copy=\"' + why + '\"'), { status: res.status, statusText: res.statusText, headers: h }); });\n")
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


# ---- After promotion (#21). ballotta.org/next/ then only sends people on to the main page. Its script first asks the
# browser to fetch next/sw.js again (the self-removing worker), for the preview's own registration only (scope check:
# a page one folder down must never update the main page's worker), then goes on with the #fragment, so a Keep or
# Share link made on the preview still opens its picks. Without scripts, the link does it (the fragment is lost).
MOVED_JS = (
    "(() => { const go = () => location.replace(new URL('../', location.href).href + location.hash);\n"
    "  try { const sw = navigator.serviceWorker; if (!sw) return go();\n"
    "    Promise.race([sw.getRegistration('./').then((g) => g && g.scope === new URL('./', location.href).href && g.update()),\n"
    "                  new Promise((ok) => setTimeout(ok, 1500))]).catch(() => {}).then(go);\n"
    "  } catch (e) { go(); } })();\n")
# (While a preview is up again, the street map's since Oct 19, this refreshes the preview's own worker instead: a phone that
# installed the old preview and hasn't opened Ballotta since fetches the preview once. Left as is: changing it changes the live page.)
# The main page does the same for a phone that installed the preview but only ever opens ballotta.org/ now: it asks for
# next/sw.js again, and the self-removing worker takes the preview's copy away. A failed fetch removes nothing.
SW_NEXT = ("sw.getRegistration('next/').then((g) => g && g.scope === new URL('next/', location.href).href && g.update()).catch(() => {});")


def moved_page():
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="referrer" content="no-referrer">\n'
            '<meta name="robots" content="noindex">\n'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src ' + sha(MOVED_JS)
            + '; worker-src \'self\'; base-uri \'none\'; form-action \'none\'">\n'
            '<title>Ballotta</title><link rel="canonical" href="' + BASE_URL + '"></head>\n'
            '<body>\n'
            '<p>The new Ballotta is now at <a href="../">ballotta.org</a>.</p>\n'
            '<script>' + MOVED_JS + '</script>\n</body></html>\n')

# ---- The share card (Lane, Oct 18). A Share my picks link goes to ballotta.org/picks/#s2…: this page, whose own preview
# card (og-picks.png, from source/og-picks.html) and title say it's someone's picks, hands the #fragment straight on to
# the page itself, replacing its own history entry. The picks travel only after the #, which no server ever sees, so
# the card can't carry a name or a pick: it is the same for everyone. No tracker here.
PICKS_JS = "location.replace(new URL('../', location.href).href + location.hash);\n"
PICKS_TITLE = "My picks for Nov 3 · Ballotta"
PICKS_DESC = "My Travis County picks for Nov 3. Open to see them next to your own ballot."


def picks_page():
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n<meta name="referrer" content="no-referrer">\n'
            '<meta name="robots" content="noindex">\n'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src ' + sha(PICKS_JS)
            + '; base-uri \'none\'; form-action \'none\'">\n'
            '<title>' + PICKS_TITLE + '</title>\n'
            '<meta property="og:title" content="' + PICKS_TITLE + '">\n'
            '<meta property="og:description" content="' + PICKS_DESC + '">\n'
            '<meta property="og:image" content="' + BASE_URL + 'og-picks.png">\n'
            '<meta property="og:image:width" content="1200">\n<meta property="og:image:height" content="630">\n'
            '<meta property="og:url" content="' + BASE_URL + 'picks/">\n'   # its own: a canonical pointing at the site would
            '<meta property="og:type" content="website">\n'                 # send some unfurlers (Facebook, WhatsApp) to the generic card
            '<meta name="twitter:card" content="summary_large_image"></head>\n'
            '<body>\n'
            '<p>Opening the shared picks on <a href="../">ballotta.org</a>…</p>\n'
            '<script>' + PICKS_JS + '</script>\n</body></html>\n')


# next/manifest.webmanifest is left as it is (a preview, the street map's since Oct 19, links it again while it is up;
# it installs as "Ballotta (preview)"): once no page links it, nothing can install from it, and a Home Screen
# app installed from the preview opens next/, which sends it on. Rewriting its start_url or scope could merge the two
# apps' identities on Android.


def outputs(preview):
    """Every file one build writes, by path from the repo root. Once the phone layout is live, next/sw.js becomes the
    self-removing worker, so phones that installed the preview drop its copy (a missing sw.js would leave it running)."""
    if preview:
        return {"next/index.html": build(True), "next/manifest.webmanifest": manifest(True),
                "next/sw.js": sw_js(True) if OFFLINE else sw_off_js(True)}
    out = {"index.html": build(False), "census.html": census_page(),
           # What the live site runs (ballotta.org/version.json; the README's badge reads it). VERSION is the one source.
           "version.json": json.dumps({"version": check_release.version(ROOT)}) + "\n",
           "picks/index.html": picks_page()}   # where Share my picks links go: their own card (Lane, Oct 18)
    if PHONE_LIVE:
        out.update({"manifest.webmanifest": manifest(False), "sw.js": sw_js(False) if OFFLINE else sw_off_js(False)})
        if STREETS_LIVE:   # nothing in preview: next/ sends people on, and its worker removes itself
            out.update({"next/sw.js": sw_off_js(True), "next/index.html": moved_page()})
        else:              # the street map's preview (Lane, Oct 19), with its own offline copy, as the layouts' was
            out.update({"next/sw.js": sw_js(True) if OFFLINE else sw_off_js(True), "next/index.html": build(True)})
    else:   # a rollback after promotion: phones keep a worker until its sw.js says otherwise, so it removes itself (Pass 2)
        out["sw.js"] = sw_off_js(False)
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
    "  s.onerror = function () { parent.postMessage('unreachable', '*'); };  // the page says so, not \"not found\" (#59)\n"
    "  document.head.appendChild(s);\n"
    "});\n")


def census_page():
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="referrer" content="no-referrer">\n'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src ' + sha(CENSUS_JS)
            + ' https://geocoding.geo.census.gov; base-uri \'none\'; form-action \'none\'">\n'
            '<title>Census address lookup</title></head><body>\n<script>' + CENSUS_JS + '</script>\n</body></html>\n')


def build(preview=False, desk=None, phone=None, streets=None):
    """desk: include the laptop layout (default: on for the preview, or once DESK_LIVE). phone: include the phone layout
    (default: on for the preview, or once PHONE_LIVE). The laptop-parity test builds with and without it. streets: the
    street map (default: on for the preview, or once STREETS_LIVE; never without the laptop layout, which draws it)."""
    desk = desk if desk is not None else (preview or DESK_LIVE)
    phone = phone if phone is not None else (preview or PHONE_LIVE)
    streets = streets if streets is not None else bool((preview or STREETS_LIVE) and desk)
    assert desk or not phone, "the phone layout is built on the laptop layout's code"
    assert desk or not streets, "the street map is drawn by the laptop layout's code"
    key = json.load(open(HERE / "answer_key.json", encoding="utf-8"))
    rules = json.load(open(HERE / "rules.json"))
    tlc = json.load(open(HERE / "tlc_precincts.json"))
    contests = [{k: c[k] for k in ("id", "title", "type", "choices", "level", "entity")}
                | ({"text": c.get("text", "")} if c["type"] == "measure" else {})
                for c in key["contests"]]
    learn = json.load(open(HERE / "learn.json", encoding="utf-8"))      # built by build_learn.py
    sites = json.load(open(HERE / "vote_sites.json", encoding="utf-8"))  # Travis County Clerk site lists, geocoded
    # Every campaign site and source link must be http(s): the page links them as they are (#85).
    links = [e.get("s") for c in learn.values() for e in (c.get("cands") or {}).values()] + [x.get("u") for c in learn.values() for x in c.get("src") or []]
    bad = [u for u in links if u and not re.match(r"https?://", u)]
    if bad:
        sys.exit(f"learn.json has links that are not http(s): {bad[:5]}")
    data = script_json({"contests": contests, "rules": rules, "tlc": tlc, "learn": learn, "sites": sites,
                        "version": check_release.version(ROOT)})   # a page left open compares it with version.json (#105)
    html = (HERE / "template-travis.html").read_text(encoding="utf-8")
    if not desk:
        html = strip_desk(html)
    if not streets:   # before the phone layout's if/else below, never between them
        html = strip_streets(html)
    if not phone:
        html = strip_phone(html)
    else:
        assert html.count(SW_REGISTER) == 1, SW_REGISTER
        if not OFFLINE:
            html = html.replace(SW_REGISTER, SW_REMOVE)
        if not preview:   # the main page with the phone layout: promoted, so the preview's copy goes too (#21)
            html = html.replace(SW_REGISTER if OFFLINE else SW_REMOVE, (SW_REGISTER if OFFLINE else SW_REMOVE) + '\n      ' + SW_NEXT, 1)

    # Self-hosted fonts: the only third-party requests are the county and Census lookups.
    fonts = ("<style>@font-face{font-family:'Zilla Slab';src:url('fonts/ZillaSlab-SemiBold.woff2') format('woff2');font-weight:600;font-display:swap}"
             "@font-face{font-family:'Zilla Slab';src:url('fonts/ZillaSlab-Bold.woff2') format('woff2');font-weight:700;font-display:swap}"
             "@font-face{font-family:'Public Sans';src:url('fonts/PublicSans-wght.woff2') format('woff2');font-weight:100 900;font-display:swap}</style>")
    html = re.sub(r"<!--FONTS-->.*?<!--/FONTS-->", fonts, html, flags=re.S).replace("__OG_IMAGE__", BASE_URL + "og.png")
    # Analytics: no URL search or #fragment is ever sent (the fragment is also stripped before this script loads).
    # The tracker is a pinned copy of https://cloud.umami.is/script.js (umami.js, fetched 2026-10-14) served from this
    # site, so a change on Umami's side can never run new code on this page. It still reports to gateway.umami.is.
    if UMAMI_ID and hashlib.sha256((ROOT / 'umami.js').read_bytes()).hexdigest() != UMAMI_SHA256:
        sys.exit('umami.js is not the pinned copy (UMAMI_SHA256): review the new copy before changing the pin')
    sri = 'sha256-' + base64.b64encode(bytes.fromhex(UMAMI_SHA256)).decode()
    analytics = (f'<script defer src="umami.js" integrity="{sri}" data-website-id="{UMAMI_ID}" '
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
        # Search engines leave the preview out: the main page is the one to list (README, "noindex"; Oct 19).
        html = html.replace('<meta name="referrer" content="no-referrer">', '<meta name="referrer" content="no-referrer">\n<meta name="robots" content="noindex">', 1)
        assert html.count('<meta name="robots" content="noindex">') == 1
        for a, b in [("url('fonts/", "url('../fonts/"), ('href="favicon.svg"', 'href="../favicon.svg"'), ("f.src = 'census.html'", "f.src = '../census.html'"),
                     ('href="apple-touch-icon.png"', 'href="../apple-touch-icon.png"'),
                     ("fetch('version.json?'", "fetch('../version.json?'")]:   # the one version.json, at the root (Oct 19)
            assert a in html, a
            html = html.replace(a, b)
    html = html.replace("<!--ANALYTICS-->", analytics)
    # The street data, compact (spaces would add a third), then the rest of the data, last, so nothing in either can be
    # mistaken for one of the placeholders above (#37). The street data is numbers and highway names only.
    assert html.count("__STREETS__") == (1 if streets else 0), "__STREETS__ must appear once, inside a STREETS block"
    if streets:
        html = html.replace("__STREETS__", script_json(json.load(open(HERE / "data/streets.json", encoding="utf-8")), compact=True), 1)
    html = html.replace("__DATA__", data, 1)
    return html.replace("<!--CSP-->", csp_meta(html, phone), 1)  # last of all: it hashes the finished scripts (#36)


# ---- what the site publishes (#83). The Pages workflow uploads exactly these files, so tests/, docs/, source/ and the
# rest of the repo are never served: everything the build writes, and the files its pages point at.
STATIC = ("CNAME", "umami.js", "favicon.svg", "apple-touch-icon.png", "icon-192.png", "icon-512.png", "icon-maskable-512.png",
          "og.png", "og-picks.png", "fonts/PublicSans-wght.woff2", "fonts/ZillaSlab-Bold.woff2", "fonts/ZillaSlab-SemiBold.woff2",
          "fonts/OFL.txt",                       # the fonts' license travels with them (#84)
          "manifest.webmanifest",                # written only while the phone layout is live; a rollback keeps it for apps
          "next/manifest.webmanifest")           # the preview's: Home Screen apps added from it may still ask for it


def site_files():
    """After a phone rollback (PHONE_LIVE = False) next/ holds the preview again (`--preview`), and its page and worker
    must stay published: an installed preview app needs next/sw.js to update or remove itself."""
    return sorted(set(outputs(False)) | (set() if PHONE_LIVE else set(outputs(True))) | set(STATIC))


def refuse_while_mutating():
    """#79: a mutation run puts mutants on disk for seconds at a time; a build or a site copy made meanwhile would carry one."""
    if (ROOT / ".mutate-lock").exists():
        sys.exit("not building: a mutation run holds .mutate-lock (a mutant may be on disk). Wait for it, or see README.md if it was killed.")


def site(dest):
    """Copy the site's files, as committed, into dest (empty or new). Only after check() passes, so a build that has
    drifted from its sources, or a mutant left behind, is never published."""
    dest = pathlib.Path(dest)
    if dest.exists() and any(dest.iterdir()):
        sys.exit(f"not writing the site: {dest} is not empty")
    refuse_while_mutating()
    if bad := check():
        sys.exit("not writing the site: " + "; ".join(bad))
    files = site_files()
    for f in files:
        (dest / f).parent.mkdir(parents=True, exist_ok=True)
        (dest / f).write_bytes((ROOT / f).read_bytes())
    return files


def check():
    """What CI runs (#81): every file the build writes, rebuilt in memory and compared with the committed one (a hand
    edit or a mutant left behind fails), and both rollback builds, which run every marker check. Writes nothing."""
    bad = list(check_release.problems(ROOT))
    built = outputs(False) if PHONE_LIVE else {**outputs(True), **outputs(False)}   # a rollback publishes next/ too: it must be the preview build
    for path, text in built.items():
        p = ROOT / path
        if not p.exists() or p.read_bytes() != text.encode("utf-8"):   # bytes: a CRLF copy is not what the build writes
            bad.append(f"{path} is not what build_site.py writes: run python3 source/build_site.py" + ("" if PHONE_LIVE or not path.startswith("next/") else " --preview"))
    for desk, phone in ((False, False), (True, False)):
        try:
            build(desk=desk, phone=phone)
        except (AssertionError, SystemExit) as e:
            bad.append(f"the rollback build (laptop layout {'on' if desk else 'off'}, phone layout off) fails: {e}")
    try:
        build(streets=False)          # the street map's rollback (after promotion), which runs every STREETS marker check
    except (AssertionError, SystemExit) as e:
        bad.append(f"the street map's rollback build fails: {e}")
    bad += [f"{f} is published but missing" for f in site_files() if not (ROOT / f).is_file()]
    return bad


if __name__ == "__main__":
    if "--site" in sys.argv[1:]:                  # the Pages workflow: python3 source/build_site.py --site _site (#83)
        i = sys.argv.index("--site")
        if i + 1 >= len(sys.argv): sys.exit("--site needs a folder")
        files = site(sys.argv[i + 1])
        sys.exit(print(len(files), "files ->", sys.argv[i + 1]) or 0)
    if "--check" in sys.argv[1:]:
        bad = check()
        for x in bad:
            print("build check:", x)
        sys.exit(1 if bad else print("build check: every output matches the build, and both rollback builds pass") or 0)
    preview = "--preview" in sys.argv[1:]
    if preview and PHONE_LIVE:
        print("The phone layout is live: the main build writes next/ (the street map's preview until STREETS_LIVE, then a page that sends people on).")
        sys.exit(0)  # not an error, so `--preview && build_site.py` still builds the live page (Pass 2)
    refuse_while_mutating()
    if not preview and (bad := check_release.problems(ROOT, check_json=False)):  # VERSION and CHANGELOG.md first
        sys.exit("not building: " + "; ".join(bad))
    for path, text in outputs(preview).items():  # the page, then the files that sit next to it (#36: census.html)
        out = ROOT / path
        out.parent.mkdir(exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(path, *((len(text) // 1024, "KB") if path.endswith("index.html") else ()))
