"""End-to-end checks for the Ballotta test site (index.html), run against the live Travis County lookup services.

    python3 tests/test_site.py                                    # builds nothing; checks the live page (index.html),
                                                                  # laptop and phone layouts (promoted Oct 17)
    BALLOTTA_STUB_COUNTY=1 python3 tests/test_site.py             # the county's answers from tests/county_answers.json (#78),
                                                                  # for when taxmaps is down or slow; county_is_live still asks it
    BALLOTTA_RECORD_COUNTY=1 python3 tests/test_site.py           # asks the county and saves every answer to that file

Analytics: cloud.umami.is is stubbed so each test can see exactly which events (and which details) would be sent.
"""
import http.server, threading, functools, json, pathlib, re, sys, traceback, urllib.parse, hashlib, importlib.util, os
from playwright.sync_api import sync_playwright, expect

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = int(os.environ.get('BALLOTTA_PORT', '8765'))
PAGE = os.environ.get('BALLOTTA_PAGE', 'index.html')
# Run the suite as of another moment, e.g. BALLOTTA_TODAY=2026-11-01T12:00:00-05:00 (#64: several views change with the
# date: early voting from Oct 19, Election Day lists from Oct 31). Every page from new_page()/phone_page() gets it.
import datetime as _dt
TODAY = _dt.datetime.fromisoformat(os.environ['BALLOTTA_TODAY']) if os.environ.get('BALLOTTA_TODAY') else None
BASE = f'http://127.0.0.1:{PORT}/{PAGE}'
HAS_DESK = 'id="dk-app"' in (ROOT / PAGE).read_text(encoding='utf-8')
HAS_PHONE = 'id="ph-bar"' in (ROOT / PAGE).read_text(encoding='utf-8')
HAS_STREETS = '.dk-map .st-wat{' in (ROOT / PAGE).read_text(encoding='utf-8')   # the street map (next/ until STREETS_LIVE)
HAS_RESULTS = 'id="rs-top"' in (ROOT / PAGE).read_text(encoding='utf-8')   # results on your ballot (RESULTS_LIVE, from 1.4.0)
if not HAS_DESK and "location.replace(new URL('../'" in (ROOT / PAGE).read_text(encoding='utf-8'):   # promotion audit #5
    sys.exit(f'{PAGE} only sends people on to the main page now that the phone layout is live: test index.html')
UMAMI_STUB = "window.__events=[];document.addEventListener('DOMContentLoaded',function(){window.umami={track:function(n,d){window.__events.push([n,d||{}]);}};},{once:true});"
NOJS = 'Ballotta needs JavaScript to look up your ballot. Turn it on for ballotta.org, or use the Travis County Voter Lookup.'
def stub_tracker(ctx):
    # A stand-in for the tracker that records events. The real tag carries integrity= (issue #68), so a stand-in served as
    # umami.js would be refused: it goes in before the page's scripts instead and appears when a deferred script would
    # (just before DOMContentLoaded's other listeners), and umami.js itself is never fetched.
    ctx.add_init_script(UMAMI_STUB); ctx.route(re.compile(r'.*/umami\.js$'), lambda r: r.abort())

# #78: the county's lookup server (taxmaps) answering slowly or not at all made the whole suite, and both mutation runners,
# fail for reasons that had nothing to do with the page. BALLOTTA_STUB_COUNTY=1 answers its requests from recorded answers
# (the mutation runners set it unless told BALLOTTA_STUB_COUNTY=0); BALLOTTA_RECORD_COUNTY=1 records them. Either way
# county_is_live asks the real server, so a change in its answers still shows up. A test's own route for taxmaps wins.
COUNTY = re.compile(r'https://taxmaps\.traviscountytx\.gov/.*')
COUNTY_FILE = ROOT / 'tests/county_answers.json'
COUNTY_MODE = 'record' if os.environ.get('BALLOTTA_RECORD_COUNTY', '0') not in ('', '0') else 'stub' if os.environ.get('BALLOTTA_STUB_COUNTY', '0') not in ('', '0') else 'live'
COUNTY_ANSWERS = json.loads(COUNTY_FILE.read_text(encoding='utf-8')) if COUNTY_FILE.exists() else {}
COUNTY_MISSES = []
def route_county(ctx, mode=None):
    mode = mode or COUNTY_MODE
    if mode == 'live': return
    def answer(route):
        url = route.request.url
        if mode == 'record':
            try: r = route.fetch(timeout=30000)
            except Exception: return route.abort()                 # an outage is not an answer worth keeping
            body = r.text()
            try: failed = 'error' in json.loads(body)                  # ArcGIS reports a failed query as 200 {"error": …}
            except ValueError: failed = True
            if r.ok and not failed and COUNTY_ANSWERS.get(url) != body:   # a fresh answer replaces an old one
                COUNTY_ANSWERS[url] = body
                COUNTY_FILE.write_text(json.dumps(COUNTY_ANSWERS, indent=1, sort_keys=True) + '\n', encoding='utf-8')
            return route.fulfill(response=r, body=body)
        if url not in COUNTY_ANSWERS:                                # say which, and pass it on (to the real county, unless a test
            COUNTY_MISSES.append(url); print('no recorded county answer for', url, '(asking the county; BALLOTTA_RECORD_COUNTY=1 records it)', file=sys.stderr, flush=True)
            return route.fallback()                                  # routed it first): refusing it made any changed request a "kill" (Pass 1)
        route.fulfill(status=200, headers={'content-type': 'application/json; charset=utf-8', 'access-control-allow-origin': '*'}, body=COUNTY_ANSWERS[url])
    ctx.route(COUNTY, answer)

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve():
    h = functools.partial(Quiet, directory=str(ROOT))
    s = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s

def new_page(browser, sent=None, wide=False, csp=False, touch=False, size=None, sw=False, ua=None, tz=None, county=None):
    # The page's Content-Security-Policy (#36) forbids eval, which Playwright's wait_for_function polls with: tests run
    # with it bypassed unless they ask (csp=True), and those poll from Python instead (see poll()). The offline copy
    # (sw.js) is blocked unless a test asks (sw=True): a service worker would answer requests the stubs below expect.
    ctx = browser.new_context(viewport=size or ({'width': 1440, 'height': 900} if wide else {'width': 400, 'height': 900}), permissions=['clipboard-read', 'clipboard-write'],
                              bypass_csp=not csp, has_touch=touch, service_workers='allow' if sw else 'block', **({'user_agent': ua} if ua else {}), **({'timezone_id': tz} if tz else {}))
    stub_tracker(ctx)
    ctx.route('https://cloud.umami.is/**', lambda r: r.abort())
    ctx.route('https://gateway.umami.is/**', lambda r: r.abort())
    ctx.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    route_county(ctx, county)                                  # live unless BALLOTTA_STUB_COUNTY / _RECORD_COUNTY (#78)
    pg = ctx.new_page()
    if TODAY: pg.clock.install(time=TODAY)                     # BALLOTTA_TODAY: the whole suite as of that moment (#64); a test's own clock still wins
    if sent is not None:
        pg.on('request', lambda req: sent.append(req.url))
    return ctx, pg

def events(pg): return pg.evaluate('window.__events || []')
def names(pg): return [e[0] for e in events(pg)]

def lookup(pg, street='1000 Guadalupe St', zip_='78701'):
    pg.fill('#street', street); pg.fill('#zip', zip_); pg.click('#go')
    pg.wait_for_selector('#result:not(.hidden)', timeout=30000)
    pg.wait_for_function("document.getElementById('k-total').textContent !== '0'", timeout=30000)

def open_race(pg, cid):
    pg.evaluate(f"document.getElementById('r{cid}').open = true")

def pick(pg, cid, label):
    open_race(pg, cid)
    pg.locator(f'#r{cid} .opt', has_text=label).first.click()

TESTS = []
def test(fn): TESTS.append(fn); return fn


def make_picks(pg):
    pick(pg, 'c070', 'Qadri'); pg.fill('#wc070', 'Knows the district')
    pick(pg, 'c071', 'For'); pg.fill('#wc071', 'More shade and pools near us.')
    pick(pg, 'c001', 'Ted Brown')
    open_race(pg, 'c002'); pg.click('#rc002 .skip') if pg.locator('#rc002').count() else None


@test
def damaged_link_is_handled(b):
    ctx, pg = new_page(b); pg.goto(BASE + '#s=not-a-real-payload')
    assert 'damaged' in pg.inner_text('#lookupmsg') and pg.locator('#friend.hidden').count() == 1
    ctx.close()

@test
def hostile_share_payload_is_escaped(b):
    import base64
    o = {'v': 1, 'n': '<img src=x onerror=alert(1)>', 'c': 'abc', 'g': 1, 'p': {'70': 0, '71': 99, '999': 0}, 'w': {'70': '<script>x</script>'}}
    s = base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip('=')
    ctx, pg = new_page(b); pg.goto(BASE + '#s=' + s); pg.wait_for_selector('#friend:not(.hidden)')
    assert pg.locator('#friend img').count() == 0 and pg.locator('#friend script').count() == 0
    t = pg.inner_text('#friend'); assert 'shared 1 pick' in t and '<script>x</script>' in t, t
    assert pg.evaluate('s => esc(s)', '&<>"\'') == '&amp;&lt;&gt;&quot;&#39;', 'esc() escapes all five, for attributes too (#72)'
    ctx.close()

@test
def link_decoding_guards_hold(b):
    # Issue #72: the guards around opening a link, each pinned. A link that inflates past 500 KB is refused; a payload
    # in another version of the format is "damaged", not read; and when two links arrive at once, the newer one wins
    # however their decoding finishes.
    ctx, pg = new_page(b); pg.goto(BASE)
    big = pg.evaluate("async () => { const f = await packFrag('k', { v: 1, z: 'a'.repeat(2000000) }); return [f.length, await unpackFrag(f)]; }")
    assert big[0] < 40000 and big[1] is None, ('a short link that inflates to 2 MB opened', big[0])
    assert pg.evaluate("async () => (await unpackFrag(await packFrag('k', { v: 1, z: 'a'.repeat(400000) }))).z.length") == 400000, 'the probe itself: 400 KB still opens'
    ctx.close()
    ctx, pg = new_page(b); pg.goto(link('s', {'v': 2, 'n': 'Al', 'c': 'abcd2349', 'g': 1, 'p': {'70': 0}}))
    expect(pg.locator('#lookupmsg')).to_contain_text('damaged'); assert pg.locator('#friend.hidden').count() == 1, 'a version-2 payload was read'
    ctx.close()
    ctx, pg = new_page(b); pg.goto(BASE)
    pg.evaluate("""async () => {
        const real = unpackFrag; window.__gates = [];
        window.unpackFrag = (f) => new Promise(ok => window.__gates.push(() => real(f).then(ok)));
        const older = await packFrag('s', { v: 1, n: 'Olga', c: 'abcd2401', g: 1, p: { 70: 0 } }), newer = await packFrag('s', { v: 1, n: 'Nina', c: 'abcd2402', g: 1, p: { 70: 0 } });
        handleIncoming(older, true); handleIncoming(newer, true);
    }""")
    pg.evaluate('window.__gates[1]()'); pg.wait_for_selector('#friend:not(.hidden)'); pg.wait_for_timeout(300)
    pg.evaluate('window.__gates[0]()'); pg.wait_for_timeout(600)
    t = pg.inner_text('#friend'); assert 'Nina' in t and 'Olga' not in t, ('the older link, decoded last, replaced the newer', t)
    ctx.close()

@test
def feedback_never_includes_fragment(b):
    # The mailto body is built from baseURL() (origin + path), never location.href.
    import base64
    s = base64.urlsafe_b64encode(json.dumps({'v': 1, 'n': 'Al', 'c': 'abcdefgh', 'g': 1, 'p': {'70': 0}}).encode()).decode().rstrip('=')
    ctx, pg = new_page(b); pg.goto(BASE + '#s=' + s); pg.wait_for_selector('#friend:not(.hidden)')
    pg.evaluate("window.__mail=null; const d=Object.getOwnPropertyDescriptor(Location.prototype,'href');")
    src = (ROOT / PAGE).read_text()
    assert "'\\nPage: ' + baseURL()" in src and "Page: ' + location.href" not in src
    assert pg.evaluate('baseURL()') == BASE
    ctx.close()

import base64
def link(kind, o): return BASE + '#' + kind + '=' + base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip('=')
def fresh_goto(pg, url): pg.goto('about:blank'); pg.goto(url)


@test
def audit_a5_a8_a12_hostile_share(b):
    ctx, pg = new_page(b)
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    fresh_goto(pg, link('s', {'v': 1, 'n': 'League of Women Voters', 'c': 'abcdefgh', 'g': 1, 'p': {'70': 0}}))
    pg.wait_for_selector('#friend:not(.hidden)')
    assert 'Your friend shared 1 pick' in pg.inner_text('#friend') and 'League of Women' not in pg.inner_text('#friend')   # A5
    for bad in ['ＬＥＡＧＵＥ ＯＦ ＷＯＭＥＮ', 'Lea\u00adgue Austin', 'Vote411', 'Travis Co. Tax Office', 'Green Party of Texas', 'Site Admin', 'Lea\u034fgue', 'City\u3164of Austin', 'L.W.V.']:                       # B2
        assert pg.evaluate('n => safeName(n)', bad) == '', bad
    for ok in ['Maya', 'Partyka', 'Admina', 'José']:
        assert pg.evaluate('n => safeName(n)', ok) == ok, ok
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Al', 'c': 'abcdefgh', 'g': 1, 'p': None}))
    pg.wait_for_selector('#friend:not(.hidden)')
    assert not errs, errs                                                                                                # A8
    assert 'didn’t contain any picks' in pg.inner_text('#friend')
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Al', 'c': 'abcdefgh', 'g': 1, 'p': {'113': [0, 0]}}))
    pg.wait_for_selector('#friend:not(.hidden)')
    t = pg.inner_text('#friend'); assert 'Sarah Ponder, Sarah Ponder' not in t and 'Sarah Ponder' in t, t               # A12
    ctx.close()


@test
def audit_a7_same_tab_link(b):
    ctx, pg = new_page(b); pg.goto(BASE)
    pg.goto(link('s', {'v': 1, 'n': 'Al', 'c': 'sametab2', 'g': 1, 'p': {'70': 0}}))   # same document: only the fragment changes
    pg.wait_for_selector('#friend:not(.hidden)', timeout=5000)
    assert pg.evaluate('location.hash') == ''
    ctx.close()


@test
def links_are_short_and_safe_for_chat_apps(b):
    # Lane's real share (48 picks, 9 reasons) was 1,427 characters as v1 and got cut at "#s" in Messages.
    ctx, pg = new_page(b); pg.goto(BASE)
    o = {'v': 1, 'n': 'Lane', 'c': 'kpbykhry', 'g': 1, 'p': {str(i): i % 3 for i in range(1, 73)},
         'w': {str(i): 'I can not stress enough how necessary this bond measure is for our parks, honestly. ' * 2 for i in range(1, 10)}}
    v2 = pg.evaluate("o => packFrag('s', o)", o)
    v1 = 's=' + pg.evaluate("o => b64e(o)", o)
    assert re.fullmatch(r's2[A-Za-z0-9_-]+', v2) and len(v2) < len(v1) * 0.6, (len(v2), len(v1))
    assert pg.evaluate("f => unpackFrag(f)", v2) == o
    assert pg.evaluate("f => unpackFrag(f)", v1) == o                       # older links still open
    assert pg.evaluate("f => unpackFrag(f)", 's2' + 'A' * 40) is None       # garbage → null, not a crash
    ctx.close()
    # Chat apps sometimes glue punctuation onto the end of a link: it must still open, and leave the address bar.
    ctx, pg = new_page(b); pg.goto(BASE)
    v2 = pg.evaluate("o => packFrag('s', o)", {'v': 1, 'n': 'Al', 'c': 'trailing', 'g': 1, 'p': {'70': 0}})
    for tail in ['.', ')', '%20']:
        fresh_goto(pg, BASE + '#' + v2 + tail)
        pg.wait_for_selector('#friend:not(.hidden)')
        assert pg.evaluate('location.hash') == '' and 'Al shared 1 pick' in pg.inner_text('#friend'), tail
    fresh_goto(pg, BASE + '#s2abc')                                         # cut short
    pg.wait_for_function("!document.getElementById('lookupmsg').classList.contains('hidden')")
    assert pg.evaluate('location.hash') == '' and 'damaged' in pg.inner_text('#lookupmsg')
    pg.goto(BASE + '#' + v2)                                                # then a good link in the same tab
    pg.wait_for_selector('#friend:not(.hidden)')
    assert pg.locator('#lookupmsg.hidden').count() == 1                     # the old error doesn't linger
    ctx.close()
    # A browser without deflate-raw: links still get made (older format), and a v2 link says "too old", not "damaged".
    ctx, pg = new_page(b)
    pg.add_init_script("window.CompressionStream = function(){ throw new TypeError('Unsupported compression format'); }; window.DecompressionStream = window.CompressionStream;")
    pg.goto(BASE)
    assert pg.evaluate("o => packFrag('s', o)", {'v': 1, 'p': {}}).startswith('s=')
    fresh_goto(pg, BASE + '#' + v2)
    pg.wait_for_function("!document.getElementById('lookupmsg').classList.contains('hidden')")
    assert 'too old' in pg.inner_text('#lookupmsg'), pg.inner_text('#lookupmsg')
    ctx.close()
    src = (ROOT / PAGE).read_text()
    assert "handOff(url, {}, $('share-out')" in src                          # share sheet gets the link only, no long text


# ---------- laptop layout (preview build only; skipped when the page has no laptop layout) ----------
DESK_TESTS = set()
def desk_test(fn): TESTS.append(fn); DESK_TESTS.add(fn.__name__); return fn
PHONE_TESTS = set()                                            # run only where the page has the phone layout (the preview)
def phone_test(fn): TESTS.append(fn); PHONE_TESTS.add(fn.__name__); return fn
STREETS_TESTS = set()                                          # run only where the page has the street map (Lane, Oct 19)
def streets_test(fn): TESTS.append(fn); STREETS_TESTS.add(fn.__name__); return fn

def build_module():
    spec = importlib.util.spec_from_file_location('build_site', ROOT / 'source' / 'build_site.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def lookup_wide(pg, street='1000 Guadalupe St', zip_='78701'):
    pg.fill('#street', street); pg.fill('#zip', zip_); pg.click('#go')
    pg.wait_for_selector('body.dk-app-on', timeout=30000)
    pg.wait_for_function("/ of \\d+ decided$/.test(document.getElementById('dk-count').textContent)", timeout=30000)

def cur(pg, cid): return pg.evaluate(f"current('{cid}')")

@test
def county_is_live(b):
    # #78: the canary. Whatever BALLOTTA_STUB_COUNTY says, this test asks the real county, and every answer it gets must
    # be the one recorded in tests/county_answers.json: the stubbed suite is only as good as that file.
    got = []
    ctx, pg = new_page(b, wide=True, county='live')
    pg.on('response', lambda r: got.append(r) if COUNTY.match(r.url) else None)
    pg.goto(BASE); lookup_wide(pg)
    rec = json.loads(COUNTY_FILE.read_text(encoding='utf-8'))
    assert got, 'the lookup asked the county nothing'
    missing = [r.url for r in got if r.url not in rec]
    stale = [r.url for r in got if r.url in rec and json.loads(r.text()) != json.loads(rec[r.url])]
    assert not missing and not stale, ('the county answers differently now: rerun with BALLOTTA_RECORD_COUNTY=1', missing, stale)
    ctx.close()

@test
def link_preview_card_is_drawn_from_its_source(b):
    # #85: og.png had no source. source/og.html draws it (make_icons.py --og), and og.png carries the sha256 of what it
    # was drawn from (og.html and its fonts), so any change to the source without redrawing fails here, on any machine
    # (Pass 2: counting pixels missed a colour change and failed on a different font renderer). The picture itself must
    # still be the source's: a wholly different image would differ in far more than 3% of its pixels.
    # Since 1.2.0 the same holds for the share card, og-picks.png, drawn from source/og-picks.html.
    import base64
    spec = importlib.util.spec_from_file_location('make_icons', ROOT / 'source' / 'make_icons.py')
    mk = importlib.util.module_from_spec(spec); spec.loader.exec_module(mk)
    assert set(mk.CARDS) == {'og.png', 'og-picks.png'}, mk.CARDS
    for card, src in mk.CARDS.items():
        used = {str((ROOT / 'source' / u).resolve().relative_to(ROOT)) for u in re.findall(r'url\(([^)]+)\)', (ROOT / src).read_text(encoding='utf-8'))}
        assert used and used <= set(mk.og_from(src)), (src, 'uses a file og_source() does not hash', used - set(mk.og_from(src)))
        png = (ROOT / card).read_bytes()
        assert mk.png_text(png).get('ballotta-source') == mk.og_source(src), (f'{card} is not drawn from {src} as it is now: run python3 source/make_icons.py --og', mk.png_text(png))
        drawn = mk.og(b, src)
        assert mk.png_text(drawn).get('ballotta-source') == mk.og_source(src)
        ctx, pg = new_page(b); pg.goto(BASE)
        off = pg.evaluate("""async ([a, b]) => {
            const img = async s => { const i = new Image(); i.src = s; await i.decode(); const c = new OffscreenCanvas(1200, 630);
                const x = c.getContext('2d'); x.drawImage(i, 0, 0); return [i.naturalWidth, i.naturalHeight, x.getImageData(0, 0, 1200, 630).data]; };
            const [A, B] = [await img(a), await img(b)]; let n = 0;
            for (let k = 0; k < A[2].length; k += 4) if (Math.max(Math.abs(A[2][k] - B[2][k]), Math.abs(A[2][k+1] - B[2][k+1]), Math.abs(A[2][k+2] - B[2][k+2])) > 40) n++;
            return [A[0], A[1], B[0], B[1], n];
        }""", ['data:image/png;base64,' + base64.b64encode(png).decode(), 'data:image/png;base64,' + base64.b64encode(drawn).decode()])
        ctx.close()
        assert off[:4] == [1200, 630, 1200, 630], (card, off)
        assert off[4] < 1200 * 630 * 0.03, (f'{card} is not the picture {src} draws', off[4])
    a, b2 = (ROOT / 'og.png').read_bytes(), (ROOT / 'og-picks.png').read_bytes()
    assert a != b2, 'the share card is the generic card'

@test
def a_share_link_has_its_own_card(b):
    # Lane, Oct 18: a Share my picks link pasted into Messages or WhatsApp showed the generic Ballotta card. Share links now
    # go to ballotta.org/picks/, a page with the share card (option B, Lane's choice: "Here's how I'm voting") that hands
    # the picks straight on to the page itself. The picks still travel only after the #, which no server ever sees, and
    # the hand-off replaces its own history entry. Keep links and the site keep the generic card.
    html = (ROOT / 'picks/index.html').read_text(encoding='utf-8')
    meta = dict(re.findall(r'<meta (?:property|name)="([^"]+)" content="([^"]*)"', html))
    assert meta.get('og:title') == 'My picks for Nov 3 · Ballotta' and re.search(r'<title>My picks for Nov 3 · Ballotta</title>', html), meta
    assert meta.get('og:description') == 'My Travis County picks for Nov 3. Open to see them next to your own ballot.', meta
    assert meta.get('og:image') == 'https://ballotta.org/og-picks.png' and meta.get('twitter:card') == 'summary_large_image', meta
    assert meta.get('robots') == 'noindex' and meta.get('referrer') == 'no-referrer', meta
    assert meta.get('og:url') == 'https://ballotta.org/picks/' and 'rel="canonical"' not in html, ('an unfurler following the canonical would show the generic card', meta)
    assert 'umami' not in html and 'gateway' not in html, 'the hand-off page counts nothing'
    csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html).group(1)
    assert "default-src 'none'" in csp and "script-src 'sha256-" in csp and 'unsafe' not in csp, csp
    main = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'content="https://ballotta.org/og.png"' in main, 'the site keeps the generic card'
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); saved_ballot(pg, [1, 70, 71]); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("pick('c070', optionsOf(BYID.c070)[0])")
    pg.evaluate("openShare()"); pg.fill('#sharename', 'Lane'); pg.click('#share-go'); pg.wait_for_selector('#share-out:not(.hidden)')
    url = pg.evaluate('sharePrep.url') or pg.inner_text('#share-out').strip()
    origin = BASE.split('/' + PAGE)[0]
    assert re.fullmatch(re.escape(origin) + r'/picks/#s2[A-Za-z0-9_-]+', url), url
    keep = pg.evaluate('keepURL()')
    assert '/picks/' not in keep, 'a Keep link went to the share card'
    ctx.close()
    ctx, pg = new_page(b, wide=True); pg.goto('about:blank'); pg.goto(url)
    pg.wait_for_function("!!window.friend", timeout=10000)
    assert pg.evaluate('location.pathname') in ('/', '/' + PAGE) and pg.evaluate('location.hash') == '', pg.url
    assert pg.evaluate("friend.name") == 'Lane'
    assert pg.evaluate('history.length') == 2, ('the hand-off stayed in the history', pg.evaluate('history.length'))   # about:blank, then the page
    ctx.close()

@test
def the_site_folder_is_the_whole_site(b):
    # #83: Pages publishes only what `build_site.py --site` copies. Served from that folder alone, both layouts, a lookup,
    # the offline copy's install and the Home Screen manifest find every file they ask for, and the repo's other files
    # (tests, docs, sources, the README) aren't there.
    import subprocess, tempfile
    out = pathlib.Path(tempfile.mkdtemp()) / 'site'
    r = subprocess.run([sys.executable, str(ROOT / 'source/build_site.py'), '--site', str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-400:] + r.stderr[-400:]
    s = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(out)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    site = f'http://127.0.0.1:{s.server_address[1]}/'
    try:
        missing, probing = [], []                                                    # the repo-file probes below are meant to 404
        note = lambda r: missing.append((r.status, r.url)) if r.url.startswith(site) and r.status >= 400 and not probing else None
        watch = lambda pg: pg.on('response', note)
        ctx, pg = new_page(b, wide=True, county='stub'); watch(pg)
        pg.goto(site); lookup_wide(pg); pg.click('#dk-views [data-view="vote"]'); pg.wait_for_timeout(300); ctx.close()
        ctx, pg = phone_page(b, sw=True, county='stub'); watch(pg)                     # one stub, not two (Pass 3)
        ctx.on('response', note)                                                     # the offline copy's own requests too
        pg.goto(site); lookup_phone(pg)
        pg.wait_for_function('navigator.serviceWorker.controller !== null || document.readyState === "complete"', timeout=15000)
        icons = pg.evaluate("""async () => { const m = await (await fetch('manifest.webmanifest')).json();
            return Promise.all(m.icons.map(async i => [i.src, (await fetch(i.src)).status])); }""")
        markup = re.sub(r'<script>.*?</script>', '', (out / 'index.html').read_text(encoding='utf-8'), flags=re.S)   # the page's own tags, not its scripts' strings
        named = sorted(set(re.findall(r'(?:href|src)="([\w./-]+)"', markup)))       # umami.js is stubbed above: ask for it here
        assert 'umami.js' in named and 'favicon.svg' in named, named
        for u in named + ['next/', 'next/manifest.webmanifest', 'og.png', 'og-picks.png', 'picks/', 'fonts/OFL.txt', 'version.json', 'census.html']:
            missing += [(st, u) for st in [pg.evaluate('u => fetch(u).then(r => r.status)', u)] if st >= 400]
        probing.append(1)
        gone = {u: pg.evaluate('u => fetch(u).then(r => r.status)', u) for u in ('tests/test_site.py', 'README.md', 'source/build_site.py', 'docs/', 'VERSION', 'CHANGELOG.md')}
        ctx.close()
        assert not missing, ('the site asks for files the site folder lacks', missing)
        assert icons and all(st == 200 for _, st in icons), icons
        assert all(st == 404 for st in gone.values()), ('repo files in the site folder', gone)
    finally:
        s.shutdown()

@test
def county_stub_answers_from_the_file(b):
    # #78: the stub answers from the recorded file, not the network (a recorded answer altered here shows on the page),
    # and a request it has no answer for is named and passed to the real county (Pass 1: refusing it made the page
    # report an outage, so any mutant that changed a request counted as a kill).
    saved = dict(COUNTY_ANSWERS); COUNTY_ANSWERS.clear(); COUNTY_ANSWERS.update(json.loads(COUNTY_FILE.read_text(encoding='utf-8')))
    try:
        q = [u for u in COUNTY_ANSWERS if 'VotingAddresses' in u and 'GUADALUPE' in urllib.parse.unquote_plus(u).upper()]
        assert q, 'no recorded answer for the courthouse'
        for u in q:
            d = json.loads(COUNTY_ANSWERS[u])
            for f_ in d.get('features', []): f_['attributes']['Precinct'] = 301
            COUNTY_ANSWERS[u] = json.dumps(d)
        ctx, pg = new_page(b, wide=True, county='stub')
        pg.goto(BASE); lookup_wide(pg)
        assert str(pg.evaluate('lastLookup.precinct')) == '301', pg.evaluate('lastLookup.precinct')
        ctx.close()
        ctx, pg = new_page(b, county='live'); n = len(COUNTY_MISSES); passed = []        # live: no stub yet; a stand-in for the county
        ctx.route(COUNTY, lambda r: (passed.append(r.request.url), r.fulfill(status=200, headers={'access-control-allow-origin': '*'}, body='{"candidates": []}')))
        ctx.route('https://geocoding.geo.census.gov/**', lambda r: r.abort())           # no match sends the page to the Census: offline here (Pass 3)
        route_county(ctx, 'stub')                                                       # routed last, so it answers first
        pg.goto(BASE); pg.fill('#street', '2 Nowhere At All St'); pg.fill('#zip', '78701'); pg.click('#go')
        pg.wait_for_function("(window.__events || []).some(e => e[0] === 'lookup_failed')", timeout=15000)
        miss = [u for u in COUNTY_MISSES[n:] if 'Nowhere' in urllib.parse.unquote_plus(u)]
        assert miss and miss == [u for u in passed if 'Nowhere' in urllib.parse.unquote_plus(u)], ('an unrecorded request is named and passed on, not refused', miss, passed)
        ctx.close()
    finally:
        COUNTY_ANSWERS.clear(); COUNTY_ANSWERS.update(saved)

@test
def live_build_is_unchanged_until_promotion(b):
    m = build_module()
    assert m.strip_desk('a\n/*DESK*/\nb\n/*/DESK*/\nc\n') == 'a\nc\n'                         # whole-line block
    assert m.strip_desk('x();/*DESK*/ y();/*/DESK*/\nz\n') == 'x();\nz\n'                       # inline block
    assert m.strip_desk('<i><!--DESK--><b><!--/DESK--></i>\n') == '<i></i>\n'
    try:
        m.strip_desk('/*DESK*/ x')
        unpaired_caught = False
    except AssertionError:
        unpaired_caught = True
    assert unpaired_caught, 'an unpaired marker must stop the build'
    for bad in ['a\n/*DESK*/\nb\n/*/DESK*/ }\nc\n/*DESK*/\nd\n/*/DESK*/\n',              # text after a closing marker
                'x /*DESK*/ y\n/*/DESK*/\n', '<!--DESK-->\n<b>\n</div><!--/DESK-->\n',      # a marker neither alone nor paired on its line
                *[f'a\n/*DESK*/\nb\n/*/DESK*/{ws}\nshared();\n/*DESK*/\nc\n/*/DESK*/\n' for ws in ('\r', '\xa0', '\f')],   # odd whitespace after a close
                'a\n/*DESK*/\nb\n/*/DESK*/\r\nshared();\n/*DESK*/\r\nc\n/*/DESK*/\nd\n',                       # ...and before the next open
                'a\n/*DESK*/\nb\n}/*/DESK*/\nshared();\n<i>/*DESK*/\nc\n/*/DESK*/\nd\n']:
        try:
            m.strip_desk(bad); refused = False
        except AssertionError:
            refused = True
        assert refused, f'malformed markers must stop the build, not eat shared code: {bad!r}'
    assert m.strip_phone('a\n<!--PHONE-->\nb\n<!--/PHONE-->\nc;/*PHONE*/ d;/*/PHONE*/\n') == 'a\nc;\n'      # the same rules, for PHONE
    for bad in ('/*PHONE*/ x', 'a\n/*PHONE*/\nb\n/*/PHONE*/ }\n', 'x /*PHONE*/ y\n/*/PHONE*/\n', 'a /*PHONE*/ b <!--/PHONE--> c <!--PHONE--> d /*/PHONE*/\n'):
        try:
            m.strip_phone(bad); refused = False
        except AssertionError:
            refused = True
        assert refused, f'malformed PHONE markers must stop the build: {bad!r}'
    live, prev = m.build(preview=False), m.build(preview=True)
    if m.DESK_LIVE:
        assert 'id="dk-app"' in live, 'promoted: the live page carries the laptop layout'
    else:
        assert 'id="dk-app"' not in live and 'DESK' not in live, 'laptop layout leaked into the live build'
    # Every file the main build writes is on disk as written, before and after promotion (promotion audit #2: after
    # it, next/index.html, next/sw.js, sw.js and manifest.webmanifest are the build's too, and a stale or missing one
    # would ship). No hash pin (#77): re-pinned with every change, it guarded nothing this comparison doesn't.
    for path, text in m.outputs(False).items():
        assert (ROOT / path).exists() and (ROOT / path).read_bytes() == text.encode('utf-8'), f'{path} on disk is not what build_site.py writes: rebuild, and commit it'
    if m.PHONE_LIVE:
        assert 'id="ph-bar"' in live and "worker-src 'self'" in live, 'promoted: the live page carries the phone layout'
    else:
        assert 'id="ph-bar"' not in live and 'PHONE' not in live and 'rel="manifest"' not in live and "worker-src" not in live, 'phone layout leaked into the live build'
        assert (ROOT / 'next/index.html').read_bytes() == prev.encode('utf-8'), 'next/index.html on disk is not what the build writes'
        assert (ROOT / 'next/manifest.webmanifest').read_text(encoding='utf-8') == m.manifest(True) and (ROOT / 'next/sw.js').read_text(encoding='utf-8') == (m.sw_js(True) if m.OFFLINE else m.sw_off_js(True))
        assert m.outputs(False)['sw.js'] == m.sw_off_js(False), 'rolled back: the main sw.js removes the offline copy phones kept since promotion'
    assert 'id="ph-bar"' in prev and "manifest-src 'self'; worker-src 'self'" in prev and '"name": "Ballotta (preview)"' in m.manifest(True)
    assert 'id="dk-app"' in prev and 'data-domains="preview.invalid"' in prev and 'src="../umami.js"' in prev
    assert (ROOT / 'index.html').read_bytes() == live.encode('utf-8'), 'index.html on disk is not what the build writes (stale, left mutated, or its line endings changed)'
    assert "url('../fonts/" in prev and '[Preview]' in prev and 'data-domains="preview.invalid"' not in live

@desk_test
def desk_layout_header_and_rail(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    assert pg.is_visible('#start') and pg.is_visible('.dk-steps') and pg.is_hidden('#dk-app') and pg.is_hidden('#dk-share')
    lookup_wide(pg)
    assert pg.is_hidden('main.wrap') and pg.is_visible('#dk-paper') and pg.is_visible('#dk-notes')
    loc = pg.inner_text('#dk-loc'); assert 'Precinct 300' in loc and '1000 Guadalupe St' in loc and 'change' in loc, loc
    h, s = pg.locator('#dk-help').bounding_box(), pg.locator('#dk-share').bounding_box()
    assert h['x'] + h['width'] <= s['x'], 'Feedback & Info sits left of Share my picks'
    assert pg.inner_text('#dk-help') == 'Feedback & Info', pg.inner_text('#dk-help')                 # Lane, Oct 15
    assert pg.locator('.dk-row').count() == 63 and pg.inner_text('#dk-count') == '0 of 63 decided'
    assert 'United States Senator' in pg.inner_text('#dk-paper h1')                                 # first undecided contest
    for width in (1280, 1366, 1412, 1440, 1920, 2560):                                                   # paper and notes centred together; gap 24 to 32px
        pg.set_viewport_size({'width': width, 'height': 900})
        p, n = pg.locator('#dk-paper').bounding_box(), pg.locator('#dk-notes').bounding_box()
        left, mid, right = p['x'] - 288, n['x'] - (p['x'] + p['width']), width - (n['x'] + n['width'])
        assert min(left, mid, right) >= 23 and abs(left - right) <= 2, (width, left, mid, right)           # centred, never cramped
        assert mid <= 33 and abs(mid - min(32, left)) <= 2, (width, left, mid, right)                  # Lane: at most 1/3 inch apart
        if width == 1412: assert abs(left - 28) <= 1 and abs(mid - 28) <= 1, (width, left, mid)        # mid-way, all three grow together
    pg.set_viewport_size({'width': 1440, 'height': 900})
    stored = json.dumps(pg.evaluate('Object.assign({}, localStorage)')).upper()
    assert 'GUADALUPE' not in stored, 'the street is shown for this visit only, never saved'
    ctx.close()

@desk_test
def desk_decide_pick_keys_and_sync(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c070"]')
    assert pg.inner_text('#dk-paper h1') == 'City Council Member, District 9'
    pg.locator('.dk-line', has_text='Qadri').click()
    assert pg.locator('.dk-line', has_text='Qadri').get_attribute('aria-pressed') == 'true'
    assert 'Qadri' in pg.inner_text('.dk-row[data-row="c070"]') and 'Qadri' in pg.inner_text('#sc070')   # phone layout agrees
    pg.keyboard.press('2'); assert cur(pg, 'c070') == ['Katie Kam']
    pg.keyboard.press('s'); assert cur(pg, 'c070') == ['__skip']
    pg.keyboard.press('s'); assert cur(pg, 'c070') == []
    pg.click('#dk-w'); pg.keyboard.type('Knows the district s')                                   # typing an "s" must not skip
    assert cur(pg, 'c070') == [] and pg.input_value('#wc070') == 'Knows the district s'
    pg.wait_for_function("(JSON.parse(localStorage.getItem('ballotta.whys')) || {}).c070 === 'Knows the district s'", timeout=2000)   # saved once typing pauses (#91)
    pg.keyboard.press('Escape'); pg.keyboard.press('j')
    assert 'Proposition A' in pg.inner_text('#dk-paper h1')
    assert pg.evaluate('document.activeElement.id') == 'dk-paper', 'keyboard moves keep focus on the paper'
    pg.keyboard.press('k'); assert pg.inner_text('#dk-paper h1') == 'City Council Member, District 9'
    pg.keyboard.press('n'); assert 'Proposition A' in pg.inner_text('#dk-paper h1')                  # next undecided after D9
    assert pg.evaluate('document.activeElement.id') == 'dk-paper'
    pg.keyboard.press('1'); assert cur(pg, 'c071') == ['FOR']
    pg.keyboard.down('2'); pg.keyboard.down('2'); pg.keyboard.up('2')                              # a held key repeats
    assert cur(pg, 'c071') == ['AGAINST'], 'holding a number key picks once, it does not flicker'
    pg.keyboard.press('/'); assert pg.evaluate('document.activeElement.id') == 'dk-q'
    pg.keyboard.type('Qadri'); assert pg.locator('.dk-row').count() == 1
    ctx.close()

LONG_WHY = ('I read both candidates’ League answers twice. ' * 4 + '\n') * 4                       # a few real paragraphs

def fits(pg, sel):                                                                                # shows everything, no inner scrollbar
    return pg.evaluate(f"(() => {{ const t = document.querySelector('{sel}'); return t.scrollHeight <= t.clientHeight + 1 && t.clientHeight > 150; }})()")


@desk_test
def desk_learn_more_symmetric_and_measure(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c070"]')
    for row in pg.locator('#dk-paper .dk-lw').all():
        assert row.locator('.links > *').count() == 2, row.inner_text()                           # same two slots for everyone
    kai = pg.locator('#dk-paper .dk-lw', has_text='Kai Huang').inner_text()
    assert 'Didn’t answer the League guide' in kai and 'No campaign site listed' in kai, kai
    site = pg.locator('#dk-paper .dk-lw', has_text='Qadri').locator('a', has_text='Campaign site')
    assert site.get_attribute('href') == 'https://zoforaustin.com' and site.get_attribute('target') == '_blank'
    notes = pg.inner_text('#dk-notes')
    assert 'One of 10 district council members' in notes and 'League of Women Voters of the Austin Area 2026 Voters Guide' in notes
    pg.click('.dk-row[data-row="c071"]'); body = pg.inner_text('#dk-paper')
    assert 'principle of and interest in bonds' in body and '$65.5M' in body and '$14.34' in body and 'Supporters' not in body
    pg.click('.dk-line[data-pick="FOR"]'); assert pg.get_attribute('.dk-line[data-pick="FOR"]', 'aria-pressed') == 'true'
    pg.click('.dk-row[data-row="c034"]')
    assert 'Unopposed · no questions in the League guide' in pg.inner_text('#dk-paper') and pg.inner_text('.dk-meta').startswith('Unopposed')
    ctx.close()

@desk_test
def desk_glance_selects_and_filters(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('#dk-views [data-view="glance"]')
    pg.select_option('select[data-sel="c001"]', 'Ted Brown'); assert cur(pg, 'c001') == ['Ted Brown']
    assert pg.inner_text('#dk-count') == '1 of 63 decided'
    pg.select_option('select[data-sel="c001"]', ''); assert cur(pg, 'c001') == []
    pg.select_option('select[data-sel="c001"]', '__skip'); assert cur(pg, 'c001') == ['__skip']
    assert pg.locator('tr[data-tr="c034"]').count() == 1
    pg.check('#dk-hideu')
    assert pg.locator('tr[data-tr="c034"]').count() == 0 and pg.locator('tr[data-tr="c070"]').count() == 1
    a = pg.locator('tr[data-tr="c070"] a')
    assert a.inner_text() == 'League guide, p. 32' and a.get_attribute('href').endswith('#page=32'), a.inner_text()
    pg.click('#dk-filt [data-f="und"]'); assert pg.locator('.dk-row[data-row="c001"]').count() == 0
    pg.click('tr[data-tr="c071"] [data-why]')
    assert pg.evaluate('document.activeElement.id') == 'dk-w' and 'Proposition A' in pg.inner_text('#dk-paper h1')
    ctx.close()

@desk_test
def desk_glance_picks_fit_their_names(b):
    # Lane, Oct 17: with reasons written, the reason column took the room and every pick read "Jame", "Greg". Every
    # dropdown is now wide enough for its longest name (the widest on the ballot is 176px of text), at 1024px and up,
    # with the contest and reason columns wrapping instead; "Learn more" stays on one line from 1200px.
    WHYS = ('() => { const w = {}; ballot.forEach(b => { w[b.c.id] = "First democratic senator from Texas in 3 decades? Yes, please. Has done a solid job so far."; });'
            ' localStorage.setItem("ballotta.whys", JSON.stringify(w)); }')
    for w in (1024, 1288, 1440):
        ctx, pg = new_page(b, wide=True); pg.set_viewport_size({'width': w, 'height': 900}); pg.goto(BASE)
        saved_ballot(pg, list(range(1, 64))); pg.wait_for_selector('body.dk-app-on'); pg.evaluate(WHYS); pg.reload(); pg.wait_for_selector('body.dk-app-on')
        pg.click('#dk-views [data-view="glance"]'); pg.wait_for_selector('.dk-tbl .dk-wt')
        r = pg.evaluate("""() => { const c = document.createElement('canvas').getContext('2d'); c.font = '14px "Public Sans"';
          const sels = [...document.querySelectorAll('.dk-tbl select')];
          const short = sels.filter(s => s.offsetWidth < Math.max(...[...s.options].map(o => c.measureText(o.text).width)) + 40).map(s => s.dataset.sel);
          const links = [...document.querySelectorAll('.dk-tbl td a')].filter(a => a.getClientRects().length > 1).length;
          return { sels: sels.length, short, links, head: (() => { const r = document.createRange(); r.selectNodeContents(document.querySelector('.dk-tbl thead th:nth-child(2)')); return r.getClientRects().length; })(),
                   sideways: document.scrollingElement.scrollWidth - innerWidth }; }""")
        assert r['sels'] > 40 and not r['short'], (w, 'a pick is cut off', r['short'][:5])
        assert r['head'] == 1, (w, '"Your pick" wraps', r['head'])   # its text's lines (the header row is as tall as its tallest cell)
        assert r['sideways'] <= 0 and (w < 1200 or r['links'] == 0), (w, r)
        ctx.close()

@test
def mud_41_reaches_no_address_until_its_code_is_confirmed(b):
    # Round-2 audit #1 (Oct 18): the county's district codes run in sequence, not by district number, so M41 is very
    # likely an older district, not MUD No. 41 (created May 2026; its order describes raw land). Its 7 contests go to
    # nobody until the Tax Office confirms a code (#56), and the page says one district can't be placed. This reverses
    # Oct 17's routing to M41 (0.6.3).
    rows = [f['attributes'] for f in json.loads((ROOT / 'source/data/district_combos.json').read_text())['features']]
    m41 = next(r for r in rows if (r.get('MUD') or '').strip() == 'M41')
    ctx, pg = new_page(b); pg.goto(BASE)
    ids = pg.evaluate("DATA.contests.filter(c => c.entity === 'Travis County MUD No. 41').map(c => c.id)")
    assert len(ids) == 7, ids
    assert all(pg.evaluate("id => DATA.rules[id].clauses === null && DATA.rules[id].conf === 'unrouted'", i) for i in ids), 'MUD 41 still has a rule'
    assert pg.evaluate("r => route(r).some(x => x.c.entity === 'Travis County MUD No. 41')", m41) is False, 'MUD 41 reached the M41 addresses'
    assert pg.evaluate("r => route(r).length", m41) > 20, 'the M41 addresses still get the rest of their ballot'
    assert "one district on the county ballot (Travis County MUD No. 41) can't be placed on a map yet" in pg.content(), 'the page no longer says MUD 41 cannot be placed'
    # A ballot saved, or a Keep link made, while 1.1.4 routed it still lists the 7 contests: they no longer show, and a
    # Keep link made now leaves them out.
    nums = [-int(i[1:]) for i in ids]
    pg.evaluate("b => localStorage.setItem('ballotta.ballot', JSON.stringify({ pr: '142', b, mode: 'exact', at: 0, pt: null, ln: [] }))", [1, 3] + nums); pg.reload()
    pg.wait_for_selector('body.dk-app-on')
    assert pg.evaluate("ballot.map(x => x.c.id)") == ['c001', 'c003'], pg.evaluate("ballot.map(x => x.c.id)")
    o = pg.evaluate("keepURL().then(u => unpackFrag(u.split('#')[1]))")
    assert o['b'] == [1, 3], ('a Keep link made now carries MUD 41', o)
    ctx.close()

@test
def two_tabs_stay_in_step(b):
    # #92: two tabs on the same ballot each kept their own copy of the picks and reasons, so whichever saved last wrote
    # over the other's changes without a word. A tab now takes the other's saved copy, everywhere it shows it; a reason
    # being typed when the other tab saves is kept, not lost.
    ctx, a = new_page(b, wide=True, county='stub'); a.goto(BASE); lookup_wide(a)
    t = ctx.new_page(); t.goto(BASE); t.wait_for_selector('body.dk-app-on')
    first = lambda pg, k: pg.evaluate('''k => { const c = ballot[k].c.id;                       // a choice as its button names it
        return [c, document.querySelector('[data-c="' + c + '"][data-pick]:not([data-pick="__skip"])').dataset.pick]; }''', k)
    (c0, v0), (c1, v1), (c2, v2), (c3, v3) = first(a, 0), first(a, 1), first(a, 2), first(a, 3)
    a.evaluate('([c, v]) => pick(c, v)', [c0, v0])
    t.wait_for_function('c => current(c).length === 1', arg=c0, timeout=5000)
    t.evaluate('([c, v]) => pick(c, v)', [c1, v1])                                  # the other tab's pick must not undo A's
    a.wait_for_function('c => current(c).length === 1', arg=c1, timeout=5000)
    saved = a.evaluate("JSON.parse(localStorage.getItem('ballotta.picks'))")
    assert saved.get(c0) == [v0] and saved.get(c1) == [v1], ('a pick was lost between tabs', saved)
    for pg in (a, t):                                                               # what each tab shows, not just its memory
        assert pg.text_content('#dk-count').startswith('2 of '), pg.text_content('#dk-count')
        on = pg.evaluate("([c, v]) => [...document.querySelectorAll('[data-c=\"' + c + '\"][data-pick]')].filter(x => x.dataset.pick === v).map(x => x.getAttribute('aria-pressed'))", [c0, v0])
        assert on and all(x == 'true' for x in on), (on, 'a picked choice is not shown as picked')
    here = a.evaluate("document.querySelector('#dk-paper [data-pick]').dataset.c")
    a.fill('#dk-w', 'because A said so')
    t.wait_for_function('([c, w]) => whys[c] === w', arg=[here, 'because A said so'], timeout=5000)
    if t.evaluate("document.querySelector('#dk-paper [data-pick]').dataset.c") == here:
        t.wait_for_function("document.getElementById('dk-w').value === 'because A said so'", timeout=5000)
    t.click('#dk-w'); t.keyboard.press('End'); t.keyboard.type(', and B agrees')              # B is typing...
    t.keyboard.press('Home')                                                        # ...with the caret moved to the start...
    a.evaluate('([c, v]) => pick(c, v)', [c2, v2])                                  # ...when A saves a pick
    t.wait_for_function('c => current(c).length === 1', arg=c2, timeout=5000)
    t.keyboard.type('Q')                                                            # the caret stayed where B left it
    t.wait_for_timeout(500)
    assert t.input_value('#dk-w') == 'Qbecause A said so, and B agrees', t.input_value('#dk-w')
    t.keyboard.press('End'); t.keyboard.type('!')                                    # B types, A saves at once, B types nothing more:
    a.evaluate('([c, v]) => pick(c, v)', [c3, v3])                                  # B's last keystroke must still be saved
    t.wait_for_function('c => current(c).length === 1', arg=c3, timeout=5000)
    t.wait_for_timeout(500)
    final = t.evaluate("[JSON.parse(localStorage.getItem('ballotta.picks')), JSON.parse(localStorage.getItem('ballotta.whys'))]")
    assert all(final[0].get(c) for c in (c0, c1, c2, c3)) and final[1].get(here) == 'Qbecause A said so, and B agrees!', final
    assert t.input_value('#dk-w') == 'Qbecause A said so, and B agrees!'
    t.click('#dk-views [data-view="glance"]')                                          # B looks At a glance while A picks (Pass 1)
    c4, v4 = first(a, 4); c5 = first(a, 5)[0]
    t.focus('[data-sel="%s"]' % c5)                                                 # B's keyboard is on another contest's dropdown
    a.evaluate('([c, v]) => pick(c, v)', [c4, v4])
    t.wait_for_function('([c, v]) => (document.querySelector(\'[data-sel="\' + c + \'"]\') || {}).value === v', arg=[c4, v4], timeout=5000)
    assert t.evaluate('document.activeElement.dataset.sel') == c5, ('the redraw took the keyboard away (Pass 2)', t.evaluate('document.activeElement.outerHTML.slice(0, 80)'))
    c6, v6 = first(a, 6)
    t.focus('#dk-paper button[data-go="%s"]:not([data-why])' % c5)               # a button, not a dropdown (Pass 3)
    a.evaluate('([c, v]) => pick(c, v)', [c6, v6])
    t.wait_for_function('c => current(c).length === 1', arg=c6, timeout=5000); t.wait_for_timeout(300)
    assert t.evaluate('[document.activeElement.dataset.go, document.activeElement.dataset.why || ""]') == [c5, ''], t.evaluate('document.activeElement.outerHTML.slice(0, 80)')
    t.click('#dk-views [data-view="decide"]')
    t.click('#dk-w'); t.keyboard.press('End'); t.keyboard.type(' SECRET')           # B types; A clears everything at once:
    with t.expect_navigation(timeout=10000):                                        # nothing B was about to save comes back (Pass 1)
        a.evaluate("window.confirm = () => true; clearEverything()")
    t.wait_for_load_state(); a.wait_for_load_state(); t.wait_for_timeout(500)
    left = t.evaluate("Object.keys(localStorage).filter(k => k.startsWith('ballotta.')).map(k => k + '=' + localStorage.getItem(k))")
    assert not [x for x in left if 'SECRET' in x or x.startswith(('ballotta.whys', 'ballotta.picks'))], left
    ctx.close()

@test
def reasons_are_saved_when_typing_pauses(b):
    # #91: every keystroke in a reason box saved all reasons (a storage event in every other tab each time) and redrew
    # the rail and the crib sheet. Now the reason is kept in memory at once and saved and redrawn once typing pauses
    # (150 ms), and at once if the page is hidden or closed, so nothing typed is lost.
    ctx, pg = new_page(b, wide=True, county='stub')
    pg.add_init_script("""window.__whySaves = 0; const _set = Storage.prototype.setItem;
        Storage.prototype.setItem = function (k, v) { if (k === 'ballotta.whys') window.__whySaves++; return _set.call(this, k, v); };""")
    pg.goto(BASE); lookup_wide(pg)
    here = pg.evaluate("document.querySelector('#dk-paper [data-pick]').dataset.c")
    before = pg.evaluate('window.__whySaves')
    assert pg.text_content('#dk-filt [data-f="why"]') == 'Reasons 0'
    pg.click('#dk-w'); pg.keyboard.type('a reason typed quickly', delay=15)
    mid = pg.evaluate('[window.__whySaves, whys[arguments[0]] || "", document.querySelector("#dk-filt [data-f=why]").textContent]'.replace('arguments[0]', repr(here)))
    assert mid[0] - before <= 1 and mid[1] == 'a reason typed quickly', ('saved on every keystroke, or not kept in memory', mid, before)
    pg.wait_for_timeout(500)
    after = pg.evaluate('[window.__whySaves, JSON.parse(localStorage.getItem("ballotta.whys"))[%r], document.querySelector("#dk-filt [data-f=why]").textContent]' % here)
    assert after[0] - before <= 2 and after[1] == 'a reason typed quickly' and after[2] == 'Reasons 1', after
    saved = lambda: pg.evaluate("JSON.parse(localStorage.getItem('ballotta.whys'))[%r]" % here)
    pg.keyboard.type(' X'); pg.evaluate("dispatchEvent(new PageTransitionEvent('pagehide'))")            # the page going away
    assert saved() == 'a reason typed quickly X', saved()
    pg.keyboard.type('Y'); pg.evaluate("Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange')); delete document.hidden")
    assert saved() == 'a reason typed quickly XY', saved()                                           # the tab going to the background
    pg.evaluate("document.getElementById('withwhy').checked = true; renderCrib()")                  # a printout with reasons
    pg.keyboard.type('Z'); pg.evaluate("dispatchEvent(new Event('beforeprint'))")                   # printing at once (Pass 1)
    assert saved() == 'a reason typed quickly XYZ' and 'a reason typed quickly XYZ' in pg.text_content('#crib'), 'the printout misses the reason just typed'
    pg.fill('#dk-w', 'a reason typed quickly')
    pg.keyboard.type(' and more'); pg.reload(); pg.wait_for_selector('body.dk-app-on')      # leaving at once still saves it
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.whys'))[%r]" % here) == 'a reason typed quickly and more'
    pg.evaluate("document.getElementById('withwhy').checked = true; renderCrib()")                  # (a reload turned it off)
    keep = pg.evaluate("localStorage.getItem('ballotta.ballot')")                    # the ballot gone (cleared elsewhere) while a
    pg.click('#dk-w'); pg.keyboard.type(' late'); pg.evaluate("localStorage.removeItem('ballotta.ballot')")   # save waits:
    pg.wait_for_timeout(400)                                                        # nothing is written back (Pass 2)
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.whys'))[%r]" % here) == 'a reason typed quickly and more'
    assert 'a reason typed quickly and more late' in pg.text_content('#crib'), 'nothing written, but the crib sheet still follows (Pass 3)'
    pg.evaluate("b => localStorage.setItem('ballotta.ballot', b)", keep)
    pg.click('#dk-w'); pg.keyboard.type(' SECRET')                                  # typing, then Clear everything at once:
    with pg.expect_navigation(timeout=10000):                                       # the reason must not come back (Pass 1)
        pg.evaluate("window.confirm = () => true; clearEverything()")
    pg.wait_for_load_state(); pg.wait_for_timeout(300)
    assert pg.evaluate("localStorage.getItem('ballotta.whys')") is None, pg.evaluate("localStorage.getItem('ballotta.whys')")
    ctx.close()

@test
def shared_link_stays_on_screen_after_sharing(b):
    # Found Oct 17 (a flaky phone test): after Share link copied the link, the handler packed a fresh link code with
    # prepShare(), which hides the link "so an older one never sits next to new choices", so the link just shown
    # vanished at once; where copying fails, the selected link the voter was to copy by hand vanished too.
    for wide, clip in ((False, True), (True, True), (False, False)):
        ctx, pg = (new_page(b, wide=True) if wide else phone_page(b)); pg.goto(BASE); saved_ballot(pg, [70, 71])
        pg.evaluate("() => { pick('c070', optionsOf(BYID.c070)[0]); }")
        if not clip: pg.evaluate("() => { Object.defineProperty(navigator, 'clipboard', { value: { writeText: () => Promise.reject(new Error('no')) } }); }")
        pg.evaluate("openShare()"); pg.fill('#sharename', 'Lane'); pg.click('#share-go')
        pg.wait_for_function("(window.__events || []).some(e => e[0] === 'share_created')", timeout=10000); pg.wait_for_timeout(300)
        assert pg.is_visible('#share-out') and '#s2' in pg.inner_text('#share-out'), ('wide' if wide else 'phone', 'clipboard' if clip else 'no clipboard', 'the shared link vanished')
        if not clip: assert pg.evaluate("getSelection().toString()") == pg.inner_text('#share-out'), 'the link to copy by hand is not selected'
        pg.fill('#sharename', 'Lane B'); pg.dispatch_event('#sharename', 'input'); pg.dispatch_event('#sharename', 'change')
        pg.evaluate("document.querySelector('#sharesecs input').click()")       # new choices: the old link goes
        assert not pg.is_visible('#share-out'), 'an older link stayed next to new choices'
        ctx.close()

@test
def page_is_built_locked_down(b):
    # #36, from the retired page_is_locked_down (its browser half lives on in phone_page_is_locked_down): what the
    # build writes, from the template and build_site.py (index.html on disk equals it: live_build test), has a
    # Content-Security-Policy before any script: only the page's own scripts (by hash) and files from this site run,
    # data goes only to the county map server and the counting service, frames only from this site; and no referrer.
    html = build_module().build()
    m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', html)
    assert m and html.index(m.group(0)) < html.index('<script'), 'a CSP meta tag before the first script'
    pol = dict((d.split(' ', 1) + [''])[:2] for d in m.group(1).split('; '))
    assert pol['default-src'] == "'none'" and pol['frame-src'] == "'self'" and pol['base-uri'] == "'none'" and pol['form-action'] == "'none'", pol
    assert pol['connect-src'] == "'self' https://taxmaps.traviscountytx.gov https://gateway.umami.is", pol['connect-src']   # 'self': the saved-copy bar's check (#73)
    srcs = pol['script-src'].split()
    assert srcs[0] == "'self'" and all(x.startswith("'sha256-") for x in srcs[1:]) and len(srcs) == 1 + html.count('<script>'), srcs
    assert '<meta name="referrer" content="no-referrer">' in html and html.index('name="referrer"') < html.index('<script')
    # Issue #68: the tracker is pinned by its sha256: here, in build_site.py, on the tag (the browser refuses any other
    # copy: tracker_runs_only_as_pinned) and in the README.
    pin = '91a876d767646fd5b7701b6fabf97f8a99ae53b94e7e5b58d465bad1e5d763e0'
    assert __import__('hashlib').sha256((ROOT / 'umami.js').read_bytes()).hexdigest() == pin, 'umami.js changed: review the new copy, then update the pin here, in build_site.py and in the README'
    assert build_module().UMAMI_SHA256 == pin and pin in (ROOT / 'README.md').read_text(encoding='utf-8')
    sri = 'sha256-' + __import__('base64').b64encode(bytes.fromhex(pin)).decode()
    assert f'src="umami.js" integrity="{sri}"' in html, 'the tag carries the pin'
    assert 'data-domains="ballotta.org,www.ballotta.org"' in html, 'counting only on ballotta.org (lanebecker.github.io redirects there; #85)'
    m = build_module(); m.UMAMI_SHA256 = '0' * 64
    try: m.build(); raise AssertionError('the build used a umami.js that is not the pinned copy')
    except SystemExit as e: assert 'pinned' in str(e), e
    # Issue #69: GitHub Pages can't send frame-ancestors, so the page's first script hides it when it's framed.
    g = '<style id="frame-guard">body>:not(noscript){display:none!important}.framed{display:block!important}'
    assert html.count(g) == 1 and html.index(g) < html.index('<script'), 'hidden from the start (Pass 1)'
    assert html.count('<noscript>') == 2 and html.index('<noscript><style>.framed{display:none!important}</style></noscript>') < html.index('<body>') < html.rindex('<noscript>'), \
        'one JavaScript note, in the body; with JavaScript off, no framed line (round-2 #13)'
    assert re.search(r"<script>\s*if \(top === self\) \{ var guard = document\.getElementById\('frame-guard'\); if \(guard\) guard\.remove\(\); \}", html), 'only the first script shows it, and only when not framed'

@test
def tracker_runs_only_as_pinned(b):
    # Issue #68: a changed umami.js (on the server or in transit) never runs; the pinned one does.
    for extra in ('', '\n/* changed */'):
        ctx = b.new_context(); route_county(ctx); ctx.route('https://gateway.umami.is/**', lambda r: r.abort()); pg = ctx.new_page()
        js = lambda route, extra=extra.encode(): (lambda r: route.fulfill(response=r, body=r.body() + extra))(route.fetch())
        ctx.route('**/umami.js', lambda route: js(route)); pg.goto(BASE); pg.wait_for_timeout(1200)
        assert pg.evaluate('typeof window.umami') == ('object' if not extra else 'undefined'), extra
        ctx.close()

@test
def page_refuses_to_show_in_another_sites_frame(b):
    # Issue #69: framed by another site, the page shows nothing (so it can't be dressed up to trick a visitor).
    # The framer is another origin (localhost, not 127.0.0.1) on the same test server: Chrome won't let a stubbed page,
    # which it counts as public, frame a loopback address at all.
    # Hidden until the page's own script shows it, so a frame with scripts turned off (sandbox) shows nothing of the page
    # either (Pass 1), only the JavaScript note, which is harmless anywhere (Lane, Oct 17).
    # Round-2 audit #13 (#111): where scripts run, the frame shows one line, a link (Lane's words), not a blank.
    FRAMED = 'Open ballotta.org directly.'
    for sandbox, shown in ((None, FRAMED), ('', NOJS), ('allow-forms allow-popups', NOJS), ('allow-scripts', FRAMED)):
        ctx, pg = new_page(b); pg.goto(f'http://localhost:{PORT}/census.html')
        pg.evaluate("([u, s]) => new Promise(ok => { const f = document.createElement('iframe'); if (s !== null) f.setAttribute('sandbox', s); f.src = u; f.width = 400; f.height = 800; f.onload = ok; document.body.appendChild(f); })", [BASE, sandbox])
        fr = [f for f in pg.frames if f != pg.main_frame][0]
        assert fr.url == BASE, (sandbox, fr.url)
        assert fr.inner_text('body').strip() == shown and not fr.locator('#street').is_visible(), ('shown in a frame', sandbox, fr.inner_text('body')[:200])
        seen = fr.evaluate("[...document.querySelectorAll('body *')].filter(e => e.checkVisibility() && !e.closest('noscript')).map(e => e.tagName + (e.id ? '#' + e.id : ''))")
        assert seen == ([] if shown == NOJS else ['P', 'A']), ('visible in a frame, text or not (Pass 3)', sandbox, seen[:10])
        if shown == FRAMED: assert fr.get_attribute('.framed a', 'href') == 'https://ballotta.org/' and fr.get_attribute('.framed a', 'target') == '_blank'
        ctx.close()
    ctx, pg = new_page(b); pg.goto(BASE)
    assert pg.locator('#street').is_visible() and NOJS not in pg.inner_text('body') and 'ballotta.org directly' not in pg.inner_text('body'), 'not framed: shown, without either note'
    ctx.close()
    # JavaScript off (Tor Browser's Safest setting, NoScript): the note, with the county's own lookup (Lane, Oct 17).
    ctx = b.new_context(java_script_enabled=False); route_county(ctx); pg = ctx.new_page(); pg.goto(BASE)
    assert pg.inner_text('body').strip() == NOJS and not pg.locator('#street').is_visible(), pg.inner_text('body')[:300]
    assert pg.get_attribute('.nojs:not(.framed) a', 'href') == 'https://votetravis.gov/voter-lookup/'
    ctx.close()
    # Pass 2: the guard can never take the first script's link scrub down with it, even if its style were missing.
    ctx, pg = new_page(b)
    ctx.route(re.compile(r'.*/index\.html$'), lambda r: (lambda res: r.fulfill(response=res, body=re.sub(r'<style id="frame-guard">.*?</style>', '', res.text(), count=1)))(r.fetch()))
    pg.goto(BASE + '#k2SECRETPICKSAAAAAAAAAAAA'); pg.wait_for_timeout(500)
    assert pg.locator('#frame-guard').count() == 0, 'the probe itself: the guard style is gone'
    assert pg.evaluate('location.hash') == '', 'the picks link stayed in the address bar'
    ctx.close()

@desk_test
def desk_extra_pick_is_explained(b):
    # #33, the laptop half of the retired extra_pick_is_explained (the phone half is phone_extra_pick_is_explained):
    # on a "vote for up to 2" race a third pick changes nothing and says why, as a status; a refused key pick isn't
    # announced as a pick; the note clears on the next pick.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); saved_ballot(pg, [113]); pg.wait_for_selector('body.dk-app-on')
    opts, msg = pg.evaluate('optionsOf(BYID.c113)'), 'You can pick up to 2. Unpick one first.'
    line = lambda i: pg.locator('#dk-paper .dk-line').nth(i); note = pg.locator('#dk-paper [data-limit="c113"]')
    line(0).click(); line(1).click(); expect(note).to_have_text('')
    line(2).click()
    assert pg.evaluate("current('c113')") == opts[:2], pg.evaluate("current('c113')")
    expect(note).to_have_text(msg); assert note.get_attribute('role') == 'status'
    assert line(2).get_attribute('aria-pressed') == 'false'
    pg.focus('#dk-paper'); pg.keyboard.press('3'); pg.wait_for_timeout(300)
    assert pg.evaluate("current('c113')") == opts[:2] and pg.text_content('#dk-live') == '', ('a refused key pick was announced', pg.text_content('#dk-live'))
    line(0).click(); expect(note).to_have_text('')
    line(2).click(); assert pg.evaluate("current('c113')") == [opts[1], opts[2]]
    ctx.close()

@test
def a_good_link_clears_a_damaged_links_notice(b):
    # #40, on both layouts: a damaged link's notice goes once a good Keep link brings a new ballot (the path that skips
    # the landing page, whose own reset hides it too).
    for wide in ((True, False) if HAS_PHONE else (True,)):
        ctx, pg = (new_page(b, wide=True) if wide else phone_page(b)); pg.goto(BASE); saved_ballot(pg, [1, 70]); pg.wait_for_selector('body.dk-app-on')
        pg.evaluate("location.hash = '#s2' + 'A'.repeat(40)")
        pg.wait_for_function("!document.getElementById('dk-say').classList.contains('hidden')", timeout=5000)
        fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, 70], 'p': {'70': 0}}))
        pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go'); pg.wait_for_selector('body.dk-app-on')
        assert pg.evaluate("document.getElementById('dk-say').classList.contains('hidden')"), ('wide' if wide else 'phone', 'the damaged link\'s notice outlived a good link')
        ctx.close()

# ---------- wave 2 (cold audit, Oct 17): look-ups and dates ----------
# A stand-in for Travis County's map server: getJSON() is the page's one door to it, so a test can answer instead.
# answers: [[url substring, delay ms, JSON body | 'error'], ...]; the first match wins; every URL asked is kept in window.__county.
COUNTY_REC = {'Address': '1000 GUADALUPE ST', 'Unit': '', 'ZIP': 78701, 'Precinct': 300, 'Commissioner': 'P03', 'Congressional': 'G10', 'JPConstable': 'J05',
              'Legislative': 'L49', 'Senate': 'N14', 'Muni': 'C10', 'MuniSMD': 'CA9', 'ISD': 'S01', 'ISDSMD': 'T45', 'College': 'ACC', 'MUD': '', 'ESD': '',
              'ESD2': '', 'Library': '', 'WCID': '', 'Temp': '', 'CodeCat': '300P03G10J05L49N14C10CA9S01T45ACC'}
def stub_county(pg, answers):
    pg.evaluate("""a => { window.__county = []; getJSON = async (url) => { window.__county.push(url); const m = a.find(x => url.includes(x[0]));
        if (!m) throw new Error('no stub for ' + url); if (m[1]) await new Promise(r => setTimeout(r, m[1]));
        if (m[2] === 'error') throw new Error('HTTP 503'); return JSON.parse(JSON.stringify(m[2])); }; }""", answers)
def candidate(address, zip_='78757', score=100): return {'candidates': [{'address': f'{address}, AUSTIN, {zip_}', 'score': score, 'location': {'x': -97.72, 'y': 30.36}}]}
def county_where(pg): return [urllib.parse.parse_qs(urllib.parse.urlsplit(u).query).get('where', [''])[0] for u in pg.evaluate('window.__county') if 'VotingAddresses' in u]

@test
def an_excluded_district_does_not_get_the_contest(b):
    # Issue #72: ballot routing, which every ballot rests on, gets a test of its own. A "field!" excludes (ESD No. 9
    # votes on c206 except its part coded E09A), and the precinct table supplies the U.S. and Texas House districts.
    ctx, pg = new_page(b); pg.goto(BASE)
    ids = lambda rec: pg.evaluate('r => route(r).map(x => x.c.id)', rec)
    base = ids(COUNTY_REC)
    assert 'c002' in base and 'c026' in base, ('precinct 300 votes in U.S. House G10 and Texas House L49, from the precinct table', base)
    assert 'c206' not in base and 'c206' in ids(dict(COUNTY_REC, ESD='E09'))
    assert 'c206' not in ids(dict(COUNTY_REC, ESD='E09', Temp='E09A')), 'the E09A part of ESD No. 9 is outside the contest'
    ctx.close()

@test
def lookup_keeps_street_names_that_start_like_a_unit(b):
    # #57 (audit #6): the unit strip took any word starting UNIT/APT/STE, so "2505 STECK AVE" was asked as "2505" and an
    # exact match fell to "nearby". A unit marker is a whole word with something after it; "#" is one on its own.
    import time
    cases = {'2505 STECK AVE': '2505 STECK AVE', '555 UNITY DR': '555 UNITY DR', '123 STEVENS RD': '123 STEVENS RD', '4 STEINER RANCH BLVD': '4 STEINER RANCH BLVD',
             '9 APTOS LN': '9 APTOS LN', '2505 STECK AVE UNIT 5': '2505 STECK AVE', '10 MAIN ST APT 3B': '10 MAIN ST', '10 MAIN ST STE 200': '10 MAIN ST',
             '10 MAIN ST # 4': '10 MAIN ST', '10 MAIN ST #4': '10 MAIN ST', '10 MAIN ST APT3': '10 MAIN ST', '10 MAIN ST UNIT#5': '10 MAIN ST',
             '10 MAIN ST STE-200': '10 MAIN ST', '10 MAIN ST UNIT-B': '10 MAIN ST', '10 MAIN ST APT. 4': '10 MAIN ST'}
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); wrong = []
    for typed, asked in cases.items():
        rec = dict(COUNTY_REC, Address=asked, ZIP=78757)
        stub_county(pg, [['findAddressCandidates', 0, candidate(typed)], ['VotingAddresses', 0, {'features': [{'attributes': rec}]}]])
        pg.evaluate("(s) => { document.getElementById('street').value = s; document.getElementById('zip').value = '78757'; lookup(); }", typed)
        end = time.time() + 5
        while not county_where(pg) and time.time() < end: pg.wait_for_timeout(50)
        w = county_where(pg)
        if not w or f"Address = '{asked}'" not in w[0]: wrong.append((typed, w))
    assert not wrong, wrong
    # The unit typed in the form finds the county's unit, however it's written (Pass 1).
    recs = [dict(COUNTY_REC, Address='10 MAIN ST', Unit=un, CodeCat=cc) for un, cc in (('3', 'A'), ('4', 'B'))]
    two = [dict(COUNTY_REC, Address='10 MAIN ST', Unit=un, CodeCat=cc) for un, cc in (('', 'A'), ('3', 'B'))]
    for typed in ('#', 'APT', 'Ste.'):                                                            # no unit really typed: ask (Pass 2)
        stub_county(pg, [['findAddressCandidates', 0, candidate('10 MAIN ST')], ['VotingAddresses', 0, {'features': [{'attributes': r} for r in two]}]])
        pg.evaluate("(u) => { document.getElementById('street').value = '10 MAIN ST'; document.getElementById('zip').value = '78757'; document.getElementById('unit').value = u; lookup(); }", typed)
        pg.wait_for_timeout(400)
        assert not pg.evaluate("document.getElementById('units').classList.contains('hidden')"), (typed, 'picked the no-unit address without asking')
    for typed in ('Apt #3', 'APT3', 'Unit-3', '#3', '3', 'ste. 3'):
        stub_county(pg, [['findAddressCandidates', 0, candidate('10 MAIN ST')], ['VotingAddresses', 0, {'features': [{'attributes': r} for r in recs]}]])
        pg.evaluate("(u) => { document.getElementById('street').value = '10 MAIN ST'; document.getElementById('zip').value = '78757'; document.getElementById('unit').value = u; lookup(); }", typed)
        pg.wait_for_timeout(400)
        assert pg.evaluate("document.getElementById('units').classList.contains('hidden')"), (typed, 'asked which unit though one was typed')
    ctx.close()

@test
def a_newer_lookup_wins_over_a_slower_older_one(b):
    # #58 (audit #7): two lookups at once (Enter twice, a ZIP corrected quickly): the later one's ballot stands, whatever
    # order the county answers in; only one ballot is found and stored; a superseded lookup asks the county nothing more.
    a, z = dict(COUNTY_REC, Address='1 SLOW ST', Precinct=300), dict(COUNTY_REC, Address='2 FAST ST', Precinct=301)
    for slow_step, gap in (('find', 0), ('records', 300)):     # the older one still finding the address / already fetching its records
        ctx, pg = new_page(b, wide=True); pg.goto(BASE)
        stub_county(pg, [['SingleLine=1+SLOW', 1500 if slow_step == 'find' else 0, candidate('1 SLOW ST')], ['SingleLine=2+FAST', 0, candidate('2 FAST ST')],
                         ["Address+%3D+%271+SLOW", 1500 if slow_step == 'records' else 0, {'features': [{'attributes': a}]}], ["Address+%3D+%272+FAST", 0, {'features': [{'attributes': z}]}]])
        pg.evaluate("() => { document.getElementById('zip').value = '78757'; document.getElementById('street').value = '1 SLOW ST'; lookup(); }")
        pg.wait_for_timeout(gap)
        pg.evaluate("() => { document.getElementById('street').value = '2 FAST ST'; lookup(); }")
        pg.wait_for_timeout(2500)
        assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.ballot')).pr") == '301', (slow_step, 'the older, slower lookup overwrote the newer one')
        assert names(pg).count('ballot_found') == 1, (slow_step, names(pg))
        if slow_step == 'find':
            assert not [w for w in county_where(pg) if 'SLOW' in w], 'a superseded lookup still asked the county for its records'
        ctx.close()

@test
def dates_follow_central_time_wherever_the_visitor_is(b):
    # #61 (audit #10): early voting starts Oct 19 and Election Day lists take over Oct 31 in Travis County, whatever the
    # visitor's own clock says: a phone in Tokyo or Los Angeles sees what Austin sees at that moment.
    import datetime as dt
    for tz, when, want_period, note in (('Asia/Tokyo', '2026-10-18T20:00:00-05:00', 'early', True),       # Oct 19 in Tokyo, still Oct 18 in Austin
                                         ('America/Los_Angeles', '2026-10-31T00:30:00-05:00', 'eday', None)):   # Oct 30 in LA, Oct 31 in Austin
        ctx, pg = new_page(b, wide=True, tz=tz); pg.clock.install(time=dt.datetime.fromisoformat(when)); pg.goto(BASE)
        saved_ballot(pg, [70, 71], [-97.743, 30.272]); pg.wait_for_selector('body.dk-app-on')
        assert pg.evaluate('period') == want_period, (tz, when, pg.evaluate('period'))
        if note is not None:
            pg.click('#dk-views [data-view="vote"]')
            assert ('fills in once voting starts Oct 19' in pg.inner_text('#dk-paper')) == note, (tz, 'the wait-times note follows the visitor\'s clock')
        ctx.close()

@test
def an_unknown_precinct_still_gets_its_federal_and_state_contests(b):
    # Round-2 audit #8 (#106): an address whose precinct the Legislative Council table doesn't list (one the county adds
    # or renumbers before Nov 3, or none) lost its US Rep, State Senator and State Rep without a word. They now come from
    # the county's own district fields, marked Double-check with their own note (Lane's words), after a reload too.
    NOTE = 'Matched from the county’s district record for your address; your precinct is new to us. Check your official ballot.'
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    ids = lambda: pg.evaluate("ballot.map(x => x.c.id)")
    def look(rec, street):
        stub_county(pg, [['findAddressCandidates', 0, candidate(street)], ['VotingAddresses', 0, {'features': [{'attributes': rec}]}]])
        pg.evaluate("s => { document.getElementById('street').value = s; document.getElementById('zip').value = '78757'; lookup(); }", street)
        pg.wait_for_function("s => (window.__events || []).filter(e => e[0] === 'ballot_found').length >= s", arg=look.n, timeout=10000); look.n += 1
        return pg.evaluate("Object.fromEntries(ballot.map(x => [x.c.id, [x.conf, x.note || '']]))")
    look.n = 1
    known = look(COUNTY_REC, '1 KNOWN ST')
    by_district = pg.evaluate("ballot.filter(x => (DATA.rules[x.c.id].clauses || []).some(cl => 'CD' in cl || 'HD' in cl || 'SD' in cl)).map(x => x.c.id)")
    assert 'c002' in by_district and 'c026' in by_district and all(known[i][0] == 'high' for i in by_district), (by_district, known)
    for pr in (None, 9999):   # with no precinct at all, a reload can't tell why, so it says the generic line; 9999 is kept
        new = look(dict(COUNTY_REC, Precinct=pr), f'{pr or 2} NEW ST')
        assert set(new) == set(known), (pr, 'contests differ', set(known) ^ set(new))
        assert all(new[i] == ['medium', NOTE] for i in by_district), (pr, {i: new[i] for i in by_district})
        assert all(new[i] == known[i] for i in new if i not in by_district), (pr, 'other contests changed')
    pg.reload(); pg.wait_for_selector('body.dk-app-on')
    after = pg.evaluate("Object.fromEntries(ballot.map(x => [x.c.id, [x.conf, x.note || '']]))")
    assert all(after[i] == ['medium', NOTE] for i in by_district), ('after a reload', {i: after[i] for i in by_district})
    pg.evaluate("localStorage.setItem('ballotta.ballot', JSON.stringify({ pr: '9999', b: [1, -2, -26], mode: 'exact', at: 0, pt: null, ln: [] }))"); pg.reload(); pg.wait_for_selector('body.dk-app-on')
    assert pg.evaluate("ballot.find(x => x.c.id === 'c002').note") == NOTE
    pg.evaluate("localStorage.setItem('ballotta.ballot', JSON.stringify({ pr: '9999', b: [1, -2, -26], mode: 'exact', at: 0, pt: null }))"); pg.reload(); pg.wait_for_selector('body.dk-app-on')
    assert pg.evaluate("ballot.find(x => x.c.id === 'c002').note") == NOTE, 'a ballot saved without the line list'
    pg.evaluate("localStorage.setItem('ballotta.ballot', JSON.stringify({ pr: '300', b: [1, -2, -26], mode: 'exact', at: 0, pt: null, ln: [] }))"); pg.reload(); pg.wait_for_selector('body.dk-app-on')
    assert pg.evaluate("ballot.find(x => x.c.id === 'c002').note") != NOTE, 'a known precinct got the county note'
    ctx.close()

@test
def a_restored_ballot_keeps_each_contests_own_caveat(b):
    # #62 (audit #11): after a reload or a Keep link, a contest marked "Double-check" says why, as the live lookup did
    # (the rule's own note), not only the generic line.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    pg.evaluate("localStorage.setItem('ballotta.ballot', JSON.stringify({ pr: '142', b: [1, -186, -187], mode: 'exact', at: 0, pt: null, ln: [] }))"); pg.reload()
    pg.wait_for_selector('body.dk-app-on')
    notes = pg.evaluate("Object.fromEntries(ballot.map(x => [x.c.id, x.note]))")
    assert 'M125' in notes['c186'] and 'M125' in notes['c187'] and notes['c001'] == '', notes
    pg.evaluate("localStorage.setItem('ballotta.ballot', JSON.stringify({ pr: '300', b: [1, -70], mode: 'nearby-mixed', at: 0, pt: null }))"); pg.reload()
    pg.wait_for_selector('body.dk-app-on')
    assert 'district line' in pg.evaluate("ballot.find(x => x.c.id === 'c070').note"), 'a contest marked near a district line says so after a reload'
    # Pass 2: an Austin limited-purpose address (Muni C11): its city propositions are uncertain by one clause of their
    # rule, and keep that clause's note after a reload, not the generic line.
    stub_county(pg, [['findAddressCandidates', 0, candidate('5 LIMITED ST')], ['VotingAddresses', 0, {'features': [{'attributes': dict(COUNTY_REC, Muni='C11', CodeCat='300P03G10J05L49N14C11CA9S01T45ACC')}]}]])
    pg.evaluate("() => { document.getElementById('street').value = '5 LIMITED ST'; document.getElementById('zip').value = '78757'; lookup(); }")
    pg.wait_for_function("(window.__events || []).filter(e => e[0] === 'ballot_found').length >= 1", timeout=10000)
    lp = pg.evaluate("(ballot.find(x => x.c.id === 'c071') || {}).note")
    pg.reload(); pg.wait_for_selector('body.dk-app-on')
    assert lp and 'limited-purpose' in lp and pg.evaluate("ballot.find(x => x.c.id === 'c071').note") == lp, (lp, pg.evaluate("ballot.find(x => x.c.id === 'c071').note"))
    # Pass 1: an address near the Austin city line: the city's propositions are flagged by the line, and say so after a
    # reload too (their rule carries a different note, about limited-purpose residents).
    # (MMD No. 1's own rule is uncertain too, so only a record of which contests the line flagged keeps its note right.)
    near = [dict(COUNTY_REC, MUD='M125', CodeCat='300P03G10J05L49N14C10CA9S01T45ACCM125', LongitudeX=-97.7201, LatitudeY=30.3601),
            dict(COUNTY_REC, Muni='', MuniSMD='', CodeCat='300P03G10J05L49N14S01T45ACC', LongitudeX=-97.7202, LatitudeY=30.3602)]
    stub_county(pg, [['findAddressCandidates', 0, candidate('7 EDGE ST')], ['Address+%3D', 0, {'features': []}], ['geometry=', 0, {'features': [{'attributes': r} for r in near]}]])
    pg.evaluate("() => { document.getElementById('street').value = '7 EDGE ST'; document.getElementById('zip').value = '78757'; lookup(); }")
    pg.wait_for_function("(window.__events || []).filter(e => e[0] === 'ballot_found').length >= 1", timeout=10000)
    live = pg.evaluate("Object.fromEntries(ballot.filter(x => ['c071', 'c186'].includes(x.c.id)).map(x => [x.c.id, x.note]))")
    pg.reload(); pg.wait_for_selector('body.dk-app-on')
    after = pg.evaluate("Object.fromEntries(ballot.filter(x => ['c071', 'c186'].includes(x.c.id)).map(x => [x.c.id, x.note]))")
    assert set(live) == {'c071', 'c186'} and all('district line' in v for v in live.values()) and after == live, (live, after)
    # Pass 3: a Keep link carries which contests the line flagged, so a restored ballot says the same.
    url = pg.evaluate('keepURL()'); fresh_goto(pg, url); pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go'); pg.wait_for_selector('body.dk-app-on')
    kept = pg.evaluate("Object.fromEntries(ballot.filter(x => ['c071', 'c186'].includes(x.c.id)).map(x => [x.c.id, x.note]))")
    assert kept == live, ('through a Keep link', live, kept)
    # Without that record (a ballot saved before it existed, a Keep link from an older page): a contest uncertain only by
    # one clause of its rule gets the generic line, never a specific reason that may be false; one whose whole rule is
    # uncertain keeps the rule's note; near a line, a contest whose rule is sure says the line.
    # (Pass 4: a rule's note says how the address was matched, so without the list it shows only on a ballot from an
    # exact or nearby match, where the line can't have added the contest.)
    for mode in ('nearby-mixed', 'saved', 'exact'):
        pg.evaluate("m => localStorage.setItem('ballotta.ballot', JSON.stringify({ pr: '300', b: [1, -70, -71, -186], mode: m, at: 0, pt: null }))", mode); pg.reload()
        pg.wait_for_selector('body.dk-app-on')
        n = pg.evaluate("Object.fromEntries(ballot.filter(x => x.conf === 'medium').map(x => [x.c.id, x.note]))")
        assert n['c071'].startswith('Not confirmed') and (('M125' in n['c186']) if mode == 'exact' else n['c186'].startswith('Not confirmed')), (mode, n)
        assert ('district line' in n['c070']) == (mode == 'nearby-mixed'), (mode, n)
    # Pass 4: another tab's lookup changes what's stored; this tab's Keep link then carries neither its line list nor its precinct.
    pg.evaluate("localStorage.setItem('ballotta.ballot', JSON.stringify({ pr: '300', b: [1, -186], mode: 'exact', at: 0, pt: null, ln: [] }))"); pg.reload()
    pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("localStorage.setItem('ballotta.ballot', JSON.stringify({ pr: '301', b: [1, -70, -186], mode: 'nearby-mixed', at: 0, pt: null, ln: [70, 186] }))")
    o = pg.evaluate("keepURL().then(u => unpackFrag(u.split('#')[1]))")
    assert 'ln' not in o and o['pr'] != '301' and o['b'] == [1, -186], o
    ctx.close()

@test
def precinct_and_point_from_a_link_or_storage_are_checked(b):
    # #63 (audit #12): a Keep link's precinct must be a precinct number (it shows in the header and the feedback email),
    # and a stored point must be two numbers in Texas (distances and the vote-center order use it).
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    for pr in ('‮123', '<b>1', '12 34', 'abc', '1234567'):
        fresh_goto(pg, link('k', {'v': 1, 'pr': pr, 'b': [1, 70], 'p': {'70': 0}}))
        pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go'); pg.wait_for_selector('body.dk-app-on')
        got = pg.evaluate("JSON.parse(localStorage.getItem('ballotta.ballot')).pr")
        assert re.fullmatch(r'\d{1,4}', got or '0') and pr not in pg.inner_text('body'), (pr, got)
    for pt, kept in ((['x', 'y'], False), ([1e9, 1e9], False), ([-97.743], False), ([-97.743, 30.272], True), ([-74.0, 40.7], False)):
        saved_ballot(pg, [1, 70], pt); pg.wait_for_selector('body.dk-app-on')
        assert (pg.evaluate('here') is not None) == kept, (pt, pg.evaluate('here'))
        pg.click('#dk-views [data-view="vote"]'); assert 'NaN' not in pg.inner_text('#dk-paper'), pt
    ctx.close()

@test
def a_stray_tap_keeps_the_keep_link(b):
    # Round-2 audit #10 (#108): a tap outside "Load your saved picks?" or Escape closed it and dropped the link for good.
    # Only "Load my picks" and "Not now" answer it now (Lane): a stray close keeps the link, and a reload asks again.
    for wide in ((True, False) if HAS_PHONE else (True,)):
        for how in ('escape', 'backdrop'):
            ctx, pg = (new_page(b, wide=True) if wide else phone_page(b)); pg.goto(BASE)
            fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, 70], 'p': {'70': 0}})); pg.wait_for_selector('#d-restore[open]')
            if how == 'escape': pg.keyboard.press('Escape')
            else: pg.mouse.click(3, 3)
            pg.wait_for_function("!document.getElementById('d-restore').open", timeout=3000); pg.wait_for_timeout(200)
            assert pg.evaluate("(sessionStorage.getItem('ballotta.incoming') || '')[0]") == 'k', (wide, how, 'the link was dropped')
            pg.reload(); pg.wait_for_selector('#d-restore[open]', timeout=5000)
            if how == 'backdrop':   # "Load my picks" answers it: loaded, and not asked again
                pg.click('#restore-go'); pg.wait_for_selector('body.dk-app-on')
                assert pg.evaluate("sessionStorage.getItem('ballotta.incoming')") is None, 'Load my picks left the link waiting'
                pg.reload(); pg.wait_for_timeout(1500); assert not pg.is_visible('#d-restore'), 'asked again after loading'
            ctx.close()

@test
def a_second_keep_link_while_asked_is_not_called_damaged(b):
    # Round-2 audit #15 (#113): a second Keep link arriving while "Load your saved picks?" is open called showModal() on an
    # open dialog, which older browsers (Chrome < 114, Safari < 17) refuse; the page then said the link was damaged.
    ctx, pg = new_page(b, wide=True)
    pg.add_init_script("""(() => { const s = HTMLDialogElement.prototype.showModal; HTMLDialogElement.prototype.showModal = function () {
        if (this.open) throw new DOMException('already open', 'InvalidStateError'); return s.call(this); }; })()""")   # as those browsers do
    pg.goto(BASE)
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, 70], 'p': {'70': 0}})); pg.wait_for_selector('#d-restore[open]')
    pg.evaluate("u => { location.hash = u.split('#')[1]; }", link('k', {'v': 1, 'pr': '300', 'b': [1, 70, 71], 'p': {'70': 0, '71': 0}}))
    pg.wait_for_function("document.getElementById('restoresum').textContent.includes('of 3')", timeout=5000)
    assert 'link_damaged' not in names(pg), events(pg)[-3:]
    assert pg.evaluate("document.getElementById('d-restore').open")
    ctx.close()

@test
def a_reload_before_answering_keeps_the_keep_link(b):
    # #66 (audit #25): reloading with "Load your saved picks?" unanswered asks again; the link is dropped only once answered.
    for wide in ((True, False) if HAS_PHONE else (True,)):
        ctx, pg = (new_page(b, wide=True) if wide else phone_page(b)); pg.goto(BASE)
        fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, 70], 'p': {'70': 0}})); pg.wait_for_selector('#d-restore[open]')
        pg.reload(); pg.wait_for_selector('#d-restore[open]', timeout=5000)
        pg.click('#d-restore [data-close]')
        pg.wait_for_function("sessionStorage.getItem('ballotta.incoming') === null", timeout=5000)   # the answer lands, then the reload (a race under load, Oct 18)
        pg.reload(); pg.wait_for_timeout(1500)
        assert not pg.is_visible('#d-restore'), 'asked again after the visitor said no'
        ctx.close()
    # Pass 1: a friend's link that arrives while the question is open is not dropped when it's answered.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, 70], 'p': {'70': 0}})); pg.wait_for_selector('#d-restore[open]')
    pg.evaluate("u => { location.hash = u.split('#')[1]; }", link('s', {'v': 1, 'n': 'Maya', 'c': 'abcd2349', 'g': 1, 'p': {'70': 0}}))
    pg.wait_for_function("!!friend", timeout=5000); pg.click('#d-restore [data-close]')
    assert (pg.evaluate("sessionStorage.getItem('ballotta.incoming')") or '').startswith('s'), 'answering the Keep question dropped the friend\'s link'
    pg.reload(); pg.wait_for_timeout(1500); assert pg.evaluate("!!friend") and not pg.is_visible('#d-restore')
    ctx.close()

@test
def a_census_outage_is_not_a_wrong_address(b):
    # #59 (audit #8): when the county has no match and the Census geocoder is down or too slow, the voter is told the
    # Census couldn't be reached (and it's counted that way), not that their address is wrong.
    frame = build_module().census_page()                         # the frame as build_site.py writes it now (so a change there counts)
    for how in ('down', 'silent'):
        ctx, pg = new_page(b, wide=True)
        ctx.route('**/census.html', lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=frame))
        if how == 'down': ctx.route('https://geocoding.geo.census.gov/**', lambda r: r.abort())
        else: ctx.route('https://geocoding.geo.census.gov/**', lambda r: None)                 # never answers
        pg.goto(BASE); stub_county(pg, [['findAddressCandidates', 0, {'candidates': []}]])
        pg.evaluate("() => { document.getElementById('street').value = '12 NOWHERE LN'; document.getElementById('zip').value = '78701'; lookup(); }")
        pg.wait_for_function("(window.__events || []).some(e => e[0] === 'lookup_failed')", timeout=15000)
        msg = pg.inner_text('#status')
        assert 'U.S. Census address finder' in msg and 'couldn’t find that address' not in msg, (how, msg)
        assert ['lookup_failed', {'reason': 'census_unreachable', 'layout': 'laptop'}] in events(pg), (how, events(pg))
        ctx.close()

@test
def the_wait_times_note_says_when_each_map_fills_in(b):
    # #60 (audit #9): from Oct 31 the page opens on Election Day, whose wait-times map is empty until Nov 3: the note
    # says so, on both layouts; on Nov 3 it goes.
    import datetime as dt
    for when, want in (('2026-10-31T10:00:00-05:00', 'fills in on Election Day, Nov 3'), ('2026-11-02T18:00:00-05:00', 'fills in on Election Day, Nov 3'),
                       ('2026-11-03T08:00:00-06:00', None), ('2026-10-18T12:00:00-05:00', 'fills in once voting starts Oct 19')):
        for wide in ((True, False) if HAS_PHONE else (True,)):
            ctx, pg = (new_page(b, wide=True) if wide else phone_page(b)); pg.clock.install(time=dt.datetime.fromisoformat(when)); pg.goto(BASE)
            saved_ballot(pg, [70, 71], [-97.743, 30.272]); pg.wait_for_selector('body.dk-app-on')
            if wide: pg.click('#dk-views [data-view="vote"]')
            else: pg.click('#ph-list'); pg.click('#dk-views [data-view="vote"]')
            text = pg.inner_text('#dk-paper')
            assert (want in text) if want else ('fills in' not in text), (when, 'laptop' if wide else 'phone', text[:300])
            ctx.close()

@test
def a_keep_link_too_long_for_chat_apps_can_leave_the_reasons_out(b):
    # #65 (audit #24): long reasons in Han script (or emoji) make a Keep link far past what Messages and email carry and
    # what this page itself accepts; the Keep sheet says so and offers the link without the reasons. Short ones say nothing.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); saved_ballot(pg, list(range(1, 73)))
    pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("() => { pick('c070', optionsOf(BYID.c070)[0]); whys.c070 = 'Short.'; }")
    pg.evaluate('openKeep()'); pg.wait_for_function("keepPrep && keepPrep.url")
    assert not pg.is_visible('#keep-long'), 'a short link was called long'
    pg.click('#d-keep [data-close]')
    pg.evaluate("""() => { ballot.forEach((x, i) => { const o = optionsOf(x.c); if (o.length) pick(x.c.id, o[0]);
        whys[x.c.id] = Array.from({ length: 600 }, (_, k) => String.fromCodePoint(0x4E00 + ((i * 600 + k) * 7919) % 20000)).join(''); }); }""")
    pg.evaluate('openKeep()'); pg.wait_for_function("keepPrep && keepPrep.url")
    assert pg.evaluate('keepPrep.url.length') > 8000 and pg.is_visible('#keep-long'), pg.evaluate('keepPrep.url.length')
    # Round-2 audit #11 (#109): a link this page itself couldn't open can't be sent or copied, until the reasons are left out.
    assert pg.evaluate('keepTooLong(keepPrep.url)') and pg.is_disabled('#keep-send') and pg.is_disabled('#keep-copy'), 'an unopenable link was offered'
    pg.evaluate("$('keep-send').disabled = false; $('keep-send').click(); $('keep-copy').disabled = false; $('keep-copy').click()"); pg.wait_for_timeout(300)   # and a tap that gets through sends nothing
    assert 'keep_created' not in names(pg) and pg.url.startswith(BASE), 'an unopenable link was sent'
    pg.evaluate("$('d-keep').close(); keepPrep = null; openKeep()"); pg.wait_for_function("keepPrep && keepPrep.url && $('keep-send').disabled")   # as opened, nothing bypassed
    pg.evaluate("$('keep-nowhy').focus(); $('keep-nowhy').click()"); pg.wait_for_function("keepPrep && keepPrep.url && keepPrep.url.length < 8000")
    assert not pg.is_disabled('#keep-send') and not pg.is_disabled('#keep-copy')
    pg.wait_for_timeout(300)
    assert pg.evaluate('document.activeElement.id') == 'keep-send', ('Pass 1: focus lost while the send button waited', pg.evaluate('document.activeElement.tagName'))
    o = pg.evaluate("unpackFrag(keepPrep.url.split('#')[1])")
    assert not o.get('w') and len(o['p']) == pg.evaluate("ballot.filter(x => current(x.c.id).length).length"), 'the picks go, the reasons stay'
    assert pg.is_visible('#keep-nowhy-done') and not pg.is_visible('#keep-long')
    # Pass 2: closed and reopened before the link without reasons is ready, the old pack touches nothing: no focus jump, and
    # the reopened sheet keeps its own warning and its disabled buttons.
    pg.evaluate("$('d-keep').close(); keepPrep = null; openKeep()"); pg.wait_for_function("keepPrep && keepPrep.url && $('keep-send').disabled")
    pg.evaluate("() => { const real = keepURL; window.keepURL = (nw) => nw ? new Promise(r => setTimeout(r, 800)).then(() => real(nw)) : real(nw); }")
    pg.evaluate("$('keep-nowhy').click(); $('d-keep').close(); openKeep()"); pg.wait_for_timeout(1500)
    assert pg.evaluate("document.activeElement.id") != 'keep-send' and pg.is_visible('#keep-long') and pg.is_disabled('#keep-send'), \
        ('an overtaken pack changed the reopened sheet', pg.evaluate("document.activeElement.id"), pg.is_visible('#keep-long'), pg.is_disabled('#keep-send'))
    ctx.close()

@test
def the_page_works_without_time_zone_support(b):
    # #61, Pass 1: a browser without formatToParts or the America/Chicago zone falls back to its own clock; the page runs.
    for kill in ("Intl.DateTimeFormat.prototype.formatToParts = undefined;",
                 "const D = Intl.DateTimeFormat; Intl.DateTimeFormat = function (l, o) { if (o && o.timeZone) throw new RangeError('Invalid time zone'); return D(l, o); };"):
        ctx, pg = new_page(b, wide=True); pg.add_init_script(kill); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(BASE); saved_ballot(pg, [70, 71]); pg.wait_for_selector('body.dk-app-on')
        assert errs == [] and pg.evaluate('period') in ('early', 'eday'), (kill[:40], errs)
        ctx.close()

@test
def too_long_to_open_means_what_the_page_refuses(b):
    # #65, Pass 2: "too long to open" is exactly what unpackFrag refuses, for both link forms, measured on the fragment.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    base = 'https://ballotta.org/#'
    for frag, refused in (('k2' + 'A' * 40000, False), ('k2' + 'A' * 40001, True), ('k=' + 'A' * 199998, False), ('k=' + 'A' * 199999, True)):
        assert pg.evaluate('u => keepTooLong(u)', base + frag) == refused, (frag[:2], len(frag), refused)
    ctx.close()

@desk_test
def desk_header_has_no_empty_precinct(b):
    # #63, Pass 1: a saved ballot whose precinct didn't pass the check shows no "Precinct" label with nothing after it.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    for pr in ('', 'abc'):
        pg.evaluate("p => localStorage.setItem('ballotta.ballot', JSON.stringify({ pr: p, b: [1, 70], mode: 'saved', at: 0, pt: null }))", pr); pg.reload()
        pg.wait_for_selector('body.dk-app-on')
        assert 'Precinct' not in pg.inner_text('#dk-loc'), (pr, pg.inner_text('#dk-loc'))
    ctx.close()

@test
def a_keep_link_too_long_to_open_says_so(b):
    # #65, Pass 1: past 40,000 characters this page itself refuses the link, so the sheet says it won't open.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); saved_ballot(pg, list(range(1, 73))); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("""() => { ballot.forEach((x, i) => { const o = optionsOf(x.c); if (o.length) pick(x.c.id, o[0]);
        let s = i * 7919 + 17; whys[x.c.id] = Array.from({ length: 600 }, () => { s = (s * 1103515245 + 12345) % 2147483648; return String.fromCodePoint(0x1F300 + (s >>> 8) % 0x2FF); }).join(''); }); }""")
    pg.evaluate('openKeep()'); pg.wait_for_function("keepPrep && keepPrep.url")
    assert pg.evaluate('keepPrep.url.length') > 40000 and pg.evaluate("unpackFrag(keepPrep.url.split('#')[1])") is None, pg.evaluate('keepPrep.url.length')
    assert 'too long to open' in pg.inner_text('#keep-long'), pg.inner_text('#keep-long')
    ctx.close()

# The ten "vote for up to N" lists in the order every page before Oct 17 had them (git show b0e514f:source/answer_key.json).
PRE_FIX_ORDER = {
    154: ['Carrington Saathoff', 'Ryan Sullivan', 'Grant Ballew', 'John Berry', 'William Waller'],
    168: ['Nicodemus Abowd', 'Denis Fletcher', 'Jeff Markey', 'Mariano Ravelo', 'Barry Marotz'],
    176: ['Daniel McElrath', 'Chase Nixon', 'Jacob Clark', 'Ross Hamilton', 'Dane Rymer'],
    179: ['Scott Moser', 'Brenda Vrabel', 'R. Lee Hill', 'Chris Capers'],
    192: ['Felicity Maxwell', 'Casey Paulson', 'Mickey Jamail', 'Daniel Kavelman', 'Ryan Puzycki'],
    199: ['Jason Nobbe', 'Kelly Schill', 'Ashtyn Bogue', 'Lyndsey Mylius', 'Jared Williams'],
    202: ['Beth Jones', 'Stephen Bodnarchuk Jr.', 'Hanoi Avila', 'David Flores', 'Kimberly Massaro', 'Linda Fabre', 'Thomas Vacek'],
    203: ['Richard Kenyon', 'Travis Wright', 'Rick Shute', 'Jason Blair'],
    204: ['Elicia Michaud', 'Larry Harlan', 'Phil Han', 'Sonja DeLaFuente', 'Ryan Carretta'],
    214: ['Rudolf J. Valenti', 'Paul Wadehra', 'Philip Waters', 'Abigail Joffrain', 'Elizabeth Martin']}

@test
def links_keep_the_old_order_for_the_ten_reordered_lists(b):
    # Cold audit, Oct 17, #1: ten "vote for up to N" lists now follow the ballot's order. Keep and Share links count
    # picks by position, so every link, old or new, counts them in the order pages had before the fix: an old link still
    # means what it meant, and a new link means the same thing to a copy of the page from before the fix (a phone's
    # offline copy, a tab left open), which would otherwise show and save the wrong candidates (wave 1 audit).
    ctx, pg = new_page(b); pg.goto(BASE)
    assert pg.evaluate("optionsOf(BYID.c154)") == ['Grant Ballew', 'John Berry', 'Carrington Saathoff', 'Ryan Sullivan', 'William Waller']
    for n, names in PRE_FIX_ORDER.items():                                   # the lists hold the same people, reordered
        assert sorted(pg.evaluate(f"optionsOf(BYID.c{n:03d}).filter(x => x !== 'Write-in')")) == sorted(names), n
    table = pg.evaluate("REORDERED")                                         # the page's table, contest by contest (Pass 2)
    assert sorted(table) == sorted(f'c{n:03d}' for n in PRE_FIX_ORDER), sorted(table)
    for n, names in PRE_FIX_ORDER.items():
        today = pg.evaluate(f"optionsOf(BYID.c{n:03d})")
        assert [today[table[f'c{n:03d}'][i]] for i in range(len(names))] == names, n
    # Every table today is its own inverse, so a mapping applied the wrong way round would pass the checks above: try
    # one that isn't (old 0 -> 1, 1 -> 2, 2 -> 0). Grant Ballew, first today, must go out as old position 2 and come back.
    turn = pg.evaluate("""() => { const keep = REORDERED.c154, was = [picks, whys]; REORDERED.c154 = [1, 2, 0, 3, 4];
      try { picks = { c154: ['Grant Ballew'] }; whys = {}; const p = packPicks(['c154'], false, false).p;
            return [p[154], unpackPicks({ v: 1, p }).P.c154]; } finally { REORDERED.c154 = keep; [picks, whys] = was; } }""")
    assert turn == [2, ['Grant Ballew']], turn
    old = pg.evaluate("unpackPicks({ v: 1, p: { 154: 0, 202: [0, 2], 1: 0 } }).P")
    assert old['c154'] == ['Carrington Saathoff'] and old['c202'] == ['Beth Jones', 'Hanoi Avila'], old
    mine = {'c154': ['Grant Ballew'], 'c214': ['Philip Waters', 'Abigail Joffrain', 'Paul Wadehra'], 'c202': ['Thomas Vacek', 'Beth Jones']}
    pg.evaluate("([p, w]) => { localStorage.setItem('ballotta.picks', JSON.stringify(p)); localStorage.setItem('ballotta.whys', JSON.stringify(w)); }", [mine, {'c154': 'met him'}])
    saved_ballot(pg, [154, 214, 202])
    for how in ("keepURL()", "(openShare(), prepShare().p)"):
        o = pg.evaluate(how + ".then(u => unpackFrag(u.split('#')[1]))")
        assert o['v'] == 1 and 'r' not in o, o                               # nothing a page from before the fix would refuse
        for n, names in PRE_FIX_ORDER.items():
            if str(n) in o['p']:
                got = [names[i] for i in (o['p'][str(n)] if isinstance(o['p'][str(n)], list) else [o['p'][str(n)]])]
                assert sorted(got) == sorted(mine[f'c{n:03d}']), (how, n, o['p'][str(n)], got)
        assert {'154', '214', '202'} <= set(o['p']), (how, o['p'])
        back = pg.evaluate("o => unpackPicks(o).P", o)                       # and today's page reads its own link back
        assert {k: sorted(v) for k, v in back.items()} == {k: sorted(v) for k, v in mine.items()}, (how, back)
    ctx.close()

TITLE_GAP = """() => { const p = document.getElementById('dk-paper'), h = p.querySelector('h1');
  const lines = (el) => { const r = document.createRange(); r.selectNodeContents(el); return [...r.getClientRects()].filter(x => x.width); };
  const above = [...p.querySelectorAll('.ov, .note')].filter(e => e.compareDocumentPosition(h) & Node.DOCUMENT_POSITION_FOLLOWING && e.getClientRects().length);
  const last = Math.max(...above.flatMap(lines).map(x => x.bottom)), top = Math.min(...lines(h).map(x => x.top));
  return Math.round(top - last); }"""

@test
def view_titles_sit_the_same_distance_below_their_line(b):
    # Lane, Oct 17: the gap between the line above a view's title and the title matches Decide's on every view.
    sizes = [(True, None)] + ([(False, {'width': 390, 'height': 844})] if HAS_PHONE else [])
    if not HAS_DESK: return
    for wide, size in sizes:
        ctx, pg = new_page(b, wide=wide, size=size, touch=not wide); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
        gaps, sizes_ = {}, {}
        for v in ('decide', 'glance', 'vote', 'crib'):
            if not wide: pg.click('#ph-list')
            pg.click(f'#dk-views [data-view="{v}"]'); pg.wait_for_timeout(200)
            gaps[v] = pg.evaluate(TITLE_GAP); sizes_[v] = pg.evaluate("getComputedStyle(document.querySelector('#dk-paper h1')).fontSize")
        assert all(abs(g - gaps['decide']) <= 1 for g in gaps.values()), ('laptop' if wide else 'phone', gaps)
        assert len(set(sizes_.values())) == 1, ('every view title the same size (Lane, Oct 17)', 'laptop' if wide else 'phone', sizes_)
        ctx.close()

@desk_test
def desk_where_to_vote_list_and_private_map(b):
    sent = []
    ctx, pg = new_page(b, sent, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('#dk-views [data-view="vote"]')
    rows = pg.locator('#dk-sites .dk-site'); assert rows.count() == 5
    d = [float(re.search(r'([\d.]+) mi', r.inner_text()).group(1)) for r in rows.all()]
    assert d == sorted(d) and d[0] < 1, d
    assert pg.locator('#dk-map .top').count() == 5 and 'Austin Recreation Center' in pg.inner_text('#dk-sites')
    pg.click('[data-period="early"]')                                                          # from Oct 31 the view opens on Election Day (#64)
    pg.click('#dk-all'); assert pg.locator('#dk-sites .dk-site').count() == 45
    pg.click('[data-period="eday"]'); assert pg.locator('#dk-sites .dk-site').count() == 201
    assert 'Election%20Day' in pg.locator('#dk-paper a.btn').get_attribute('href')
    for u in sent:                                                                                # drawn on the page: no map service sees the address
        assert not re.search(r'tile|maps\.googleapis|openstreetmap|mapbox|arcgisonline', u), u
    ctx.close()


@desk_test
def desk_help_menu_info_address_and_clear(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('#dk-help')
    assert pg.is_visible('#dk-menu') and pg.get_attribute('#dk-help', 'aria-expanded') == 'true'
    assert pg.evaluate('document.activeElement.dataset.help') == 'feedback'
    pg.keyboard.press('ArrowDown'); assert pg.evaluate('document.activeElement.dataset.help') == 'privacy'
    pg.keyboard.press('Escape'); assert pg.is_hidden('#dk-menu') and pg.evaluate('document.activeElement.id') == 'dk-help'
    pg.click('#dk-help'); pg.click('[data-help="privacy"]'); pg.wait_for_selector('#d-info[open]')
    t = pg.inner_text('#d-info')
    assert 'Ballotta never receives your address' in t and 'packed inside the link itself' in t and "isn't affiliated with Travis County" in t, t
    pg.keyboard.press('Escape'); assert pg.evaluate('document.activeElement.id') == 'dk-help', 'focus comes back to Feedback & Info'
    pg.click('#dk-help'); pg.keyboard.press('Shift+Tab'); pg.keyboard.press('Escape')               # Escape from the button, menu open
    assert pg.is_hidden('#dk-menu'), 'Escape closes the menu from the Feedback & Info button too'
    pg.click('#dk-help')
    for _ in range(pg.locator('#dk-menu [role=menuitem]').count()): pg.keyboard.press('Tab')     # tab out of the menu, however many items it has
    pg.wait_for_selector('#dk-menu', state='hidden', timeout=2000)                              # leaving the menu with the keyboard closes it
    pg.click('#dk-help'); pg.click('[data-help="address"]')
    assert pg.is_visible('#start') and pg.is_visible('#dk-back') and pg.is_hidden('#dk-app')
    pg.click('#dk-back'); assert pg.is_visible('#dk-paper')
    pg.click('.dk-row[data-row="c001"]'); pg.locator('.dk-line', has_text='Ted Brown').click()
    pg.once('dialog', lambda d: d.accept())
    pg.click('#dk-help'); pg.click('[data-help="clear"]')
    assert cur(pg, 'c001') == [] and pg.locator('.dk-line[aria-pressed="true"]').count() == 0 and pg.inner_text('#dk-count') == '0 of 63 decided'
    ctx.close()

DESK_FRIEND = {'v': 1, 'n': 'Maya', 'c': 'deskfrnd', 'g': 1, 'p': {'70': 2, '71': 0}, 'w': {'70': 'Knows the district.'}}

@desk_test
def desk_friend_link_landing_and_inline(b):
    ctx, pg = new_page(b, wide=True); fresh_goto(pg, link('s', DESK_FRIEND)); pg.wait_for_selector('#friend:not(.hidden)')
    assert 'Maya shared 2 picks' in pg.inner_text('#friend') and 'See Maya’s picks beside yours' in pg.inner_text('#dk-fcta')
    assert pg.is_hidden('#f-own') and pg.is_hidden('.dk-steps') and pg.locator('#start h1').is_hidden()
    lookup_wide(pg)
    assert pg.is_visible('.dk-fchip') and pg.locator('.dk-row[data-row="c070"] .dk-fa').count() == 1
    pg.click('.dk-row[data-row="c070"]')
    fp = pg.locator('#dk-paper .dk-lw', has_text='Qadri').inner_text(); assert 'Maya picked this' in fp and 'Knows the district.' in fp, fp
    assert 'you and maya' in pg.inner_text('#dk-notes').lower()                                  # small caps on screen
    pg.locator('.dk-line', has_text='Qadri').click()
    assert pg.inner_text('.dk-fbox .dk-kv div:first-child b') == '1'
    pg.wait_for_function("(window.__events||[]).filter(e => e[0] === 'share_compare').length === 1")
    pg.click('.dk-row[data-row="c071"]'); pg.wait_for_timeout(300)
    assert names(pg).count('share_compare') == 1, 'counted once per friend link, not per screen'
    pg.click('.dk-fchip [data-act="hidefriend"]')
    assert pg.locator('#dk-app .dk-fa').count() == 0 and pg.is_hidden('#friend')
    ctx.close()

@desk_test
def desk_friend_hide_on_landing(b):
    ctx, pg = new_page(b, wide=True); fresh_goto(pg, link('s', DESK_FRIEND)); pg.wait_for_selector('#friend:not(.hidden)')
    pg.click('#f-hide')
    assert 'dk-friend' not in pg.evaluate('document.body.className') and pg.locator('#start h1').is_visible()
    assert pg.inner_text('#dk-fcta') == '' and pg.is_visible('.dk-steps'), 'back to the plain landing page'
    ctx.close()

@desk_test
def desk_friend_link_with_saved_ballot_counts_in_order(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    fresh_goto(pg, link('s', dict(DESK_FRIEND, c='ordered1'))); pg.wait_for_selector('.dk-fchip')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'share_compare')")
    seq = [n for n in names(pg) if n in ('share_opened', 'share_compare')]
    assert seq == ['share_opened', 'share_compare'], seq                                           # the open is counted before the compare
    ctx.close()

JUNK_STORAGE = ("try { localStorage.setItem('ballotta.whys', JSON.stringify({c001: 5})); "
                "localStorage.setItem('ballotta.ballot', JSON.stringify({pr: '300', b: [1, 70], mode: 'saved', at: 0, pt: null})) } catch (e) {}")


@desk_test
def desk_compare_counted_once_per_link(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    fresh_goto(pg, link('s', dict(DESK_FRIEND, c='onceonly'))); pg.wait_for_selector('.dk-fchip')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'share_compare')")
    pg.reload(); pg.wait_for_selector('.dk-fchip'); pg.wait_for_timeout(800)
    assert names(pg).count('share_compare') == 0, 'a reload is not a second compare'
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Bo', 'c': 'nooverlp', 'g': 1, 'p': {'113': 0}})); pg.wait_for_selector('.dk-fchip'); pg.wait_for_timeout(800)
    assert names(pg).count('share_compare') == 0, 'no shared race on your ballot, nothing compared'
    pg.evaluate("() => { friend.P.c070 = ['Rich Heyman']; desk.render(); }")                          # now one of their races is on yours
    pg.wait_for_function("(window.__events||[]).filter(e => e[0] === 'share_compare').length === 1", timeout=3000)
    assert [e[1] for e in events(pg) if e[0] == 'share_compare'] == [{'layout': 'laptop'}]                # told apart from the phone's Compare tap
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Cy', 'g': 1, 'p': {'70': 0}})); pg.wait_for_selector('.dk-fchip')   # a link without a code
    pg.click('.dk-row[data-row="c071"]'); pg.click('.dk-row[data-row="c070"]'); pg.wait_for_timeout(500)
    assert names(pg).count('share_compare') == 1, 'once per page for a link without a code'
    ctx.close()


@desk_test
def desk_share_and_keep_open_as_centered_windows(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c001"]'); pg.locator('.dk-line', has_text='Ted Brown').click()
    pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]')
    r = pg.locator('#d-share').bounding_box()
    assert abs(r['x'] + r['width'] / 2 - 720) < 4 and r['y'] > 40 and r['y'] + r['height'] < 860, r
    assert names(pg).count('share_sheet_open') == 1
    pg.click('#d-share [data-close]'); pg.click('#dk-keep'); pg.wait_for_selector('#d-keep[open]')
    ctx.close()

@desk_test
def desk_restore_link_on_laptop(b):
    ctx, pg = new_page(b, wide=True)
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, 70], 'p': {'70': 2}, 'w': {'70': 'Knows'}}))
    pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go')
    pg.wait_for_selector('body.dk-app-on')
    assert pg.inner_text('#dk-count') == '1 of 2 decided'
    loc = pg.inner_text('#dk-loc'); assert 'Precinct 300' in loc and 'Guadalupe' not in loc, loc
    ctx.close()

@desk_test
def desk_hostile_friend_is_escaped(b):
    o = {'v': 1, 'n': '<img src=x onerror=alert(1)>', 'c': 'abc', 'g': 1, 'p': {'70': 0}, 'w': {'70': '<script>x</script>'}}
    ctx, pg = new_page(b, wide=True); fresh_goto(pg, link('s', o)); pg.wait_for_selector('#friend:not(.hidden)')
    assert pg.locator('#dk-fcta img').count() == 0
    lookup_wide(pg); pg.click('.dk-row[data-row="c070"]')
    assert pg.locator('#dk-app img').count() == 0 and pg.locator('#dk-app script').count() == 0
    assert '<script>x</script>' in pg.inner_text('#dk-paper') and '<img src=x' in pg.inner_text('#dk-notes')
    ctx.close()

TAGLINE = 'Don’t wait to meet your ballot in the booth.'                                        # Lane, Oct 15
FAQ = [('What is Ballotta?', 'A free, independent tool for Travis County voters.'),
       ('Does it tell me how to vote?', 'No. Ballotta doesn’t endorse, rank or recommend anyone.'),
       ('Where does the information come from?', 'We link to them rather than rewrite them.'),
       ('What happens to my address and picks?', 'the U.S. Census geocoder); we never receive it.'),        # audit: the Census fallback too
       ('What won’t you allow here?', 'No ads, no paid placement, no campaign content, and no selling or sharing data. We try to block'),
       ('Is this official?', 'Check your official sample ballot at VoteTravis.gov before you vote.')]

def rgba(c): v = [float(x) for x in c[c.index('(') + 1:c.index(')')].split(',')]; return v[:3], (v[3] if len(v) > 3 else 1.0)
def lum(rgb):                                                                                     # WCAG relative luminance of an opaque 'rgb(r, g, b)'
    def ch(v): v /= 255; return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b_ = rgba(rgb)[0]
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b_)
def contrast(fg, bg):                                                                             # a see-through colour is blended over its background first
    (f, a), (b_, _) = rgba(fg), rgba(bg)
    mix = 'rgb(' + ','.join(str(a * x + (1 - a) * y) for x, y in zip(f, b_)) + ')'
    hi, lo = sorted([lum(mix), lum(bg)], reverse=True); return (hi + 0.05) / (lo + 0.05)

def box(pg, sel): return pg.locator(sel).first.bounding_box()
def css(pg, sel, prop, pseudo='null'): return pg.evaluate(f"getComputedStyle(document.querySelector('{sel}'), {pseudo}).{prop}")
PLUM = 'rgb(75, 42, 107)'

def landing_band_checks(pg, paper_sel, side_sel, width):
    # Option B (Lane, Oct 15): a full-width plum band with a big logo and the tagline; the paper overlaps its foot,
    # the side column starts below it, and there's no plum corner box any more.
    assert pg.is_visible('#dk-hero'), width
    hero = box(pg, '#dk-hero')
    assert css(pg, '#dk-hero', 'backgroundColor') == PLUM and hero['x'] == 0 and abs(hero['width'] - width) <= 1, (width, hero)
    assert css(pg, '#dk-hdr', 'backgroundColor') == PLUM, 'the whole top bar is plum on the landing page'
    assert css(pg, '#dk-hdr', 'display', "'::before'") == 'none' or css(pg, '#dk-hdr', 'content', "'::before'") == 'none'
    assert pg.is_hidden('.dk-brand'), 'no small logo in the corner'
    only = box(pg, '#dk-hero .dk-only')                                                              # Lane, Oct 15: say plainly it's Travis County only
    assert css(pg, '#dk-hero .dk-only', 'backgroundColor') == 'rgb(233, 169, 42)' and only['x'] == 0 and abs(only['width'] - width) <= 1, (width, only)
    assert abs(only['y'] - hero['y']) <= 1 and only['y'] + only['height'] <= box(pg, '#dk-hero .dk-word')['y'], 'a gold strip across the top of the band'
    assert 'only works for Travis County' in pg.inner_text('#dk-hero .dk-only')
    assert contrast(css(pg, '#dk-hero .dk-only', 'color'), 'rgb(233, 169, 42)') >= 4.5
    word = pg.locator('#dk-hero .dk-word')
    assert word.inner_text() == 'Ballotta' and float(css(pg, '#dk-hero .dk-word', 'fontSize')[:-2]) >= 64, 'a big logo'
    assert pg.inner_text('#dk-hero .dk-tagline') == TAGLINE and 'share them with friends' in pg.inner_text('#dk-hero .dk-sub')
    for sel in ('.dk-word', '.dk-tagline', '.dk-sub'):
        seen = pg.evaluate(f"(() => {{ let e = document.querySelector('#dk-hero {sel}'), o = 1; for (; e; e = e.parentElement) {{ const c = getComputedStyle(e); o *= +c.opacity; if (c.filter !== 'none') o = 0; }} return o; }})()")
        assert contrast(css(pg, f'#dk-hero {sel}', 'color'), PLUM) >= 4.5 and seen == 1, (sel, width, seen)   # parents' opacity and filters too
    assert 'every race' not in pg.inner_text('#dk-hero .dk-sub'), 'audit: some small districts have no neutral sources'
    for sel in ('#dk-loc', '#dk-when'):
        if pg.is_visible(sel): assert contrast(css(pg, sel, 'color'), PLUM) >= 4.5, (sel, width)
    sub, paper, side = box(pg, '#dk-hero .dk-sub'), box(pg, paper_sel), box(pg, side_sel)
    hb = hero['y'] + hero['height']
    assert sub['y'] + sub['height'] + 16 <= paper['y'] < hb - 40, ('the paper overlaps the foot of the band, clear of the words', width, sub, paper, hb)
    assert side['y'] >= hb + 12, ('the side column starts below the band, never dark text on plum', width, side, hb)
    tops = [r['y'] for e in pg.locator(f'{side_sel} *').all() if e.is_visible() and (r := e.bounding_box())]   # display:contents has no box
    assert tops and min(tops) >= hb + 12, width

def faq_checks(pg, above_sel):
    assert pg.is_visible('#dk-faq') and pg.inner_text('#dk-faq h2') == 'What’s going on here?'
    qs = pg.locator('#dk-faq h3'); assert qs.count() == 6
    for i, (q, a) in enumerate(FAQ):
        card = pg.locator('#dk-faq .dk-q').nth(i)                                                  # inner_text reads hidden text too
        assert card.is_visible() and qs.nth(i).inner_text() == q and a in card.inner_text(), (q, a)
    assert pg.get_attribute('#dk-faq a[href*="votetravis.gov"]', 'rel') == 'noopener'
    assert 'Draft' not in pg.inner_text('#dk-faq'), 'Lane approved the wording'
    f, above = box(pg, '#dk-faq'), box(pg, above_sel)
    assert f['y'] >= above['y'] + above['height'], 'the FAQ sits below the paper'


@desk_test
def desk_launch_audit_fixes(b):
    # Pre-launch cold audit (Oct 15): #25 rail labels, #26 damaged link in the app, #30 shortcuts, #31 landmark and focus, #35 touch.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    for w in (1024, 1280, 1440):                                                                      # #25: Place 3 vs Place 4 must be readable
        pg.set_viewport_size({'width': w, 'height': 900}); pg.wait_for_function(f'innerWidth === {w}')
        clipped = pg.evaluate("[...document.querySelectorAll('.dk-rt b')].filter(e => e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1).map(e => e.textContent)")
        assert not clipped, (w, clipped[:5])
    assert pg.locator('.dk-row[title]').count() == 0, 'titles wrap, so no tooltip (a screen reader would hear each title twice)'
    pg.set_viewport_size({'width': 1440, 'height': 900})
    main = pg.get_by_role('main')                                                                     # #31: the app is the page's main content
    assert main.count() == 1 and main.locator('#dk-paper').count() == 1
    pg.click('.dk-row[data-row="c001"]')
    assert css(pg, '#dk-paper', 'outlineStyle') == 'none', 'no focus ring after a mouse click'
    pg.focus('#dk-help'); pg.keyboard.press('2')                                                       # #30: not while on a header button…
    pg.focus('.dk-row[data-row="c002"]'); pg.keyboard.press('s')                                       # …or a rail row (WCAG 2.1.4)
    assert cur(pg, 'c001') == [], cur(pg, 'c001')
    pg.click('.dk-row[data-row="c001"]'); pg.keyboard.press('2')                                       # on the paper: yes, and said out loud
    assert cur(pg, 'c001') == ['James Talarico']
    live = pg.locator('#dk-live'); assert live.get_attribute('aria-live') == 'polite'
    pg.wait_for_function("document.getElementById('dk-live').textContent.includes('James Talarico')", timeout=2000)
    assert 'United States Senator' in live.inner_text()
    pg.keyboard.press('s'); pg.wait_for_function("/skip/i.test(document.getElementById('dk-live').textContent)", timeout=2000)
    pg.keyboard.press('n'); assert pg.evaluate('document.activeElement.id') == 'dk-paper'
    assert css(pg, '#dk-paper', 'outlineStyle') != 'none', 'the paper shows keyboard focus'           # #31
    # Pass 1: shortcuts must not die after ordinary mouse use
    pg.click('#dk-views [data-view="glance"]'); pg.click('#dk-views [data-view="decide"]')        # back to Decide: keys work again
    c = pg.get_attribute('.dk-row[aria-current="true"]', 'data-row'); pg.keyboard.press('1'); assert cur(pg, c) != [], 'shortcuts after switching views'
    pg.focus('.dk-row[data-row="c002"]'); pg.keyboard.press('/')                                    # Pass 2: '/' is a single-key shortcut too (WCAG 2.1.4)
    assert pg.evaluate('document.activeElement.dataset.row') == 'c002', '/ does nothing off the paper'
    pg.click('#dk-paper h1'); pg.keyboard.press('/'); assert pg.evaluate('document.activeElement.id') == 'dk-q', '/ reaches search from the paper'
    pg.keyboard.press('Escape'); pg.click('#dk-paper h1')
    pg.focus('#dk-views [data-view="decide"]'); pg.keyboard.press('Enter')                         # Pass 2: keyboard users stay on the tabs
    assert pg.evaluate('document.activeElement.dataset.view') == 'decide'
    pg.click('#dk-paper h1')
    pg.click('#dk-w'); pg.keyboard.press('Escape'); c = pg.get_attribute('.dk-row[aria-current="true"]', 'data-row'); pg.keyboard.press('s')   # Escape from the reason box
    assert cur(pg, c) == ['__skip'], 'shortcuts after Escape from the reason box'
    assert 'ballot paper' in pg.inner_text('.dk-keysec').lower(), 'the Shortcuts box says where they work'
    fresh_goto(pg, BASE + '#s=not-a-real-payload')                                                    # #26: a damaged link with a ballot open
    pg.wait_for_selector('body.dk-app-on'); pg.wait_for_selector('#dk-say:not(.hidden)', timeout=5000)
    assert 'damaged' in pg.inner_text('#dk-say') and pg.get_attribute('#dk-say', 'role') == 'status'
    say, paper = box(pg, '#dk-say'), box(pg, '#dk-paper')
    assert say['y'] + say['height'] <= paper['y'], 'the notice sits above the paper, covering nothing'
    pg.click('#dk-say button'); assert pg.is_hidden('#dk-say')
    fresh_goto(pg, BASE + '#s=not-a-real-payload'); pg.wait_for_selector('#dk-say:not(.hidden)', timeout=5000)
    pg.evaluate('h => { location.hash = h; }', link('s', DESK_FRIEND).split('#', 1)[1]); pg.wait_for_selector('.dk-fchip')
    assert pg.is_hidden('#dk-say'), 'a good link clears the old warning'
    pg.click('#dk-views [data-view="glance"]'); pg.evaluate('window.scrollTo(0, 3000)'); pg.wait_for_function('scrollY > 1000')   # Pass 2: scrolled far down
    pg.evaluate("location.hash = '#s=not-a-real-payload-2'"); pg.wait_for_selector('#dk-say:not(.hidden)', timeout=5000)
    r = box(pg, '#dk-say'); assert r['y'] >= 0 and r['y'] + r['height'] <= 900, ('the warning is on screen', r)
    pg.click('#dk-change'); pg.wait_for_selector('body:not(.dk-app-on)'); lookup_wide(pg)              # Change address, then a new lookup
    assert pg.is_hidden('#dk-say'), 'no stale warning after Change address'
    ctx.close()
    ctx, pg = new_page(b, wide=True); pg.goto(BASE + '#s=not-a-real-payload')                       # on the landing page the form shows it
    pg.wait_for_selector('#lookupmsg:not(.hidden)'); lookup_wide(pg)
    assert pg.is_hidden('#dk-say'), 'no stale warning once the ballot opens'
    ctx.close()
    ctx = b.new_context(viewport={'width': 1366, 'height': 1024}, has_touch=True, is_mobile=True); route_county(ctx)    # #35: a tablet in landscape
    stub_tracker(ctx)
    pg = ctx.new_page(); pg.goto(BASE); lookup_wide(pg)
    assert pg.evaluate("matchMedia('(pointer: coarse)').matches")
    assert pg.locator('.kbd:visible').count() == 0, 'no keyboard hints on a touch screen'
    ctx.close()

@test
def desk_phone_layout_matches_live_page(b):
    # Phones must not change: at phone width the page with the laptop code is pixel-for-pixel the page without it,
    # before and after a lookup. Both are built in memory from the template, so this still guards phones after
    # promotion, when index.html itself carries the laptop layout (audit #28).
    m = build_module(); shots = []
    for name, desk in (('_parity_plain.html', False), ('_parity_desk.html', True)):              # served from memory: nothing is written (Pass 1)
        html = m.build(desk=desk, phone=False, streets=False)                                   # the old phone page, as a rollback would bring it back
                                                                                                # (the street map, Oct 19, has its own credit: off in both)
        ctx, pg = new_page(b); ctx.route(f'**/{name}', (lambda h: lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=h))(html))
        pg.goto(f'http://127.0.0.1:{PORT}/{name}'); pg.wait_for_timeout(600)
        assert pg.evaluate('!!document.getElementById("dk-app")') == desk, (name, 'built the wrong flavour')
        first = pg.screenshot(full_page=True)
        lookup(pg); open_race(pg, 'c070'); pg.evaluate('window.scrollTo(0, 0)'); pg.wait_for_timeout(600)
        shots.append((first, pg.screenshot(full_page=True))); ctx.close()
    assert shots[0][0] == shots[1][0], 'landing differs at phone width with the laptop code in'
    assert shots[0][1] == shots[1][1], 'ballot differs at phone width with the laptop code in'

# ---------------------------------------------------------------- anonymous counts: the privacy firewall (Umami round)
def event_names_in_page():
    src = (ROOT / 'source/template-travis.html').read_text(encoding='utf-8')
    block = src[src.index('const EVENTS = {'):src.index('};', src.index('const EVENTS = {'))]
    return re.findall(r'^  ([a-z_]+): \{', block, re.M) + re.findall(r'^EVENTS\.([a-z_]+) = \{', src, re.M)   # the phone layout adds its own (PHONE)

def no_link_opens(pg):                                     # links still fire our counting listener, but never navigate
    pg.evaluate("document.addEventListener('click', e => { if (e.target.closest && e.target.closest('a[href^=\"http\"]')) e.preventDefault(); })")

def journey_check(pg, layout):
    # Everything counted is on the list, carries the layout, and nothing our own code sent was trimmed by the firewall.
    names_ok = set(event_names_in_page())
    for n, d in events(pg):
        assert n in names_ok and d.get('layout') == layout, (n, d)
        blob = json.dumps(d)
        assert not re.search(r'Guadalupe|78701|Precinct|Paxton|Talarico|Qadri|Senator', blob), blob
    assert pg.evaluate('window.ballottaDropped') == [], pg.evaluate('window.ballottaDropped')

@test
def privacy_firewall_drops_anything_unlisted(b):
    ctx, pg = new_page(b); pg.goto(BASE)
    bs = lambda p: pg.evaluate('p => window.ballottaBeforeSend("event", p)', p)
    R = pg.evaluate('location.origin') + '/'                  # the address goes out normalized: this origin, its own path (Pass 1)
    assert bs({'name': 'not_an_event', 'data': {}}) is None, 'an unlisted event never leaves the browser'
    got = bs({'name': 'lookup_failed', 'data': {'reason': 'not_found', 'street': '1000 Guadalupe St', 'layout': 'phone'}, 'id': 'someone', 'url': '/'})
    assert got['data'] == {'reason': 'not_found', 'layout': 'phone'} and 'id' not in got and got['url'] == R, got
    assert bs({'name': 'lookup_failed', 'data': {'reason': '1000 Guadalupe St'}})['data'] == {}, 'a value off the list is dropped'
    assert bs({'name': 'progress', 'data': {'at': {'x': 1}}})['data'] == {}, 'objects are never values'
    assert bs({'name': 'share_created', 'data': {'sections': ['federal']}})['data'] == {}, 'arrays are never values'
    title = pg.evaluate('document.title')
    assert bs({'url': '/', 'title': 'Ballotta'}) == {'url': R, 'title': title}, 'page views pass, titled only with the page\'s own title'
    # Issues #50, #67: no free text in any field, and no page address but the page's own.
    assert bs({'url': '/', 'tag': 'Precinct 123'}) == {'url': R}, 'no tag'
    pg.evaluate("document.title = 'Precinct 300'")
    assert bs({'url': '/', 'title': 'Precinct 300'})['title'] == title, 'a changed title is never sent'
    ok = pg.evaluate("({ website: document.querySelector('script[data-website-id]').dataset.websiteId, hostname: location.hostname, screen: screen.width + 'x' + screen.height, language: navigator.language, url: location.origin + '/index.html' })")
    assert bs(dict(ok)) == ok, 'the tracker\'s ordinary fields pass'
    # Each field passes only as its true value, never as something shaped like one (Pass 1).
    pg.set_viewport_size({'width': 900, 'height': 400}); pg.wait_for_timeout(200)      # a phone turned sideways after load (Pass 2)
    assert pg.evaluate("screen.width + 'x' + screen.height") != ok['screen'] and bs(dict(ok)) == ok, 'the tracker\'s values from load still pass'
    for k, v in (('website', 'Precinct 300'), ('website', '00078701-0300-4000-8000-0000000000aa'), ('hostname', '1000 Guadalupe St'), ('screen', '78701'),
                 ('screen', '78701x300'), ('language', 'Qadri for Council'), ('language', 'en-Qadri-for-Council'), ('language', 'en-300')):
        assert k not in bs(dict(ok, **{k: v})), (k, v)
    assert bs({'url': '/300'}) is None, 'a path other than the page\'s own, while the page is at /'
    host = pg.evaluate('location.host')
    for u in ('https://precinct-300.qadri-for-council.example/', '//qadri.example/', '\\\\qadri.example\\', 'javascript:/', f'http://1000-Guadalupe-St:78701@{host}/'):
        assert bs({'url': u}) is None, ('only this origin, with no user name or password', u)    # Pass 1
    for u, out in (('/1000-Guadalupe-St/precinct-300/../../', R), ('/Qadri/%2e%2e/index.html', R + 'index.html')):
        assert bs({'url': u})['url'] == out, ('the address goes out normalized, never as it came', u)
    pg.evaluate("history.pushState(null, '', '/300')")
    for u in ('/300', 'https://ballotta.org/300?x=1', 'https://ballotta.org/c070/', '/next/300'):
        assert bs({'url': u}) is None and bs({'url': u, 'name': 'faq_seen', 'data': {}}) is None, ('only the page\'s own address', u)
    assert bs({'url': pg.evaluate('location.href')}) is None, 'not even after the page itself moves'
    pg.evaluate("history.replaceState(null, '', '/')")
    # Verification pass: payloads without a name, other payload types and extra fields can't carry anything either.
    assert bs({'url': '/', 'data': {'street': '1000 Guadalupe St'}, 'precinct': '300'}) == {'url': R}, 'a page view carries no details'
    odd = {'url': '/?addr=1000+Guadalupe#k=x', 'referrer': 'https://forum.example/thread/1000-guadalupe-st?q=1', 'title': {'street': 'x'}, 'tag': ['78701'], 'website': 'w'}
    assert bs(odd) == {'url': R, 'referrer': 'https://forum.example'}, 'only text fields in their shapes; no query or fragment; a referrer is just its site'
    assert bs({'url': '/', 'referrer': 'not a url'}) == {'url': R, 'referrer': ''}
    assert bs({'referrer': 'android-app://com.google.android.googlequicksearchbox/'}) == {'referrer': 'android-app://com.google.android.googlequicksearchbox'}, 'an app referrer keeps its name'
    assert bs({'referrer': 'about:blank'}) == {'referrer': ''} and bs({'referrer': 'file:///x'}) == {'referrer': ''}, 'never the string "null"'
    assert pg.evaluate('window.ballottaBeforeSend("identify", { data: { street: "1000 Guadalupe St" } })') is None, 'no session data'
    perf = pg.evaluate('window.ballottaBeforeSend("performance", { url: "/", lcp: 812.5, cls: 0.01, street: "x", data: { a: 1 } })')
    assert perf == {'url': R, 'lcp': 812.5, 'cls': 0.01}, perf
    for ev, d in (('share_opened', {'generation': 100, 'has_picks': 'yes', 'link': 'ABC!!'}), ('share_created', {'sections': 'federal,bogus'}),
                  ('faq_seen', {'layout': 'tablet'})):
        assert bs({'name': ev, 'data': d})['data'] == ({'has_picks': 'yes'} if ev == 'share_opened' else {}), (ev, d)   # pattern checks
    pg.evaluate("track('lookup_failed', { reason: 'Guadalupe' })")
    assert events(pg)[-1] == ['lookup_failed', {'layout': 'phone'}] and 'lookup_failed.reason' in pg.evaluate('window.ballottaDropped')
    for sel in ('#lookup > p.note', '#dk-faq'):                                                # the promise is on the page, too
        assert 'Do Not Track or Global Privacy Control' in pg.text_content(sel), sel
    tag = (ROOT / 'index.html').read_text(encoding='utf-8')
    assert 'data-before-send="ballottaBeforeSend"' in tag and 'data-do-not-track="true"' in tag and 'data-performance="true"' in tag
    assert -1 < tag.find('<script>window.ballottaBeforeSend = () => null;</script>') < tag.find('data-before-send='), 'fails closed until the page defines its check'
    assert 'and how quickly pages load, never your address or your picks' in pg.text_content('#lookup > p.note')
    ctx.close()
    for signal in ("Object.defineProperty(Navigator.prototype, 'globalPrivacyControl', { get: () => true })",
                   "Object.defineProperty(Navigator.prototype, 'doNotTrack', { get: () => '1' })"):
        ctx, pg = new_page(b); pg.add_init_script(signal); pg.goto(BASE)
        assert pg.evaluate('window.ballottaBeforeSend("event", { url: "/" })') is None, signal
        pg.evaluate("track('lookup_started')"); pg.fill('#street', ''); pg.click('#go')
        assert events(pg) == [], (signal, 'no events (page views: see real_tracker_sends_only_listed_events)')
        ctx.close()
    plain = build_module().build(desk=False, phone=False)                                                    # after a rollback, wide screens are phones
    ctx, pg = new_page(b, wide=True); ctx.route('**/_rollback.html', lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=plain))
    pg.goto(f'http://127.0.0.1:{PORT}/_rollback.html'); pg.evaluate("track('faq_seen')")
    assert events(pg)[-1] == ['faq_seen', {'layout': 'phone'}], events(pg)
    ctx.close()

@test
def real_tracker_sends_only_listed_events(b):
    # The real pinned umami.js, pointed at this test server: every request it makes is caught and checked.
    TOP = {'website', 'hostname', 'screen', 'language', 'title', 'url', 'referrer', 'tag', 'name', 'data', 'ttfb', 'fcp', 'lcp', 'cls', 'inp', 'duration'}
    live_phone = 'id="ph-bar"' in (ROOT / 'index.html').read_text(encoding='utf-8')            # always the live page, which may carry the phone layout
    for gpc in ('', "Object.defineProperty(Navigator.prototype, 'globalPrivacyControl', { get: () => true })",
                "Object.defineProperty(Navigator.prototype, 'doNotTrack', { get: () => '1' })"):
        sent = []
        ctx = b.new_context(viewport={'width': 400, 'height': 900}, has_touch=live_phone); route_county(ctx)
        if gpc: ctx.add_init_script(gpc)
        def page(route):
            r = route.fetch(); body = r.text().replace('data-domains="ballotta.org,www.ballotta.org"', 'data-domains="127.0.0.1"')
            route.fulfill(response=r, body=body)
        ctx.route(re.compile(r'.*/index\.html$|.*:%d/$' % PORT), page)
        ctx.route('https://gateway.umami.is/**', lambda r: (sent.append(r.request.post_data_json), r.fulfill(status=200, content_type='application/json', body='{}')))
        pg = ctx.new_page(); pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        if live_phone: lookup_phone(pg); pb_go(pg, 'c070'); pb_line(pg, 'Qadri').click(); pg.wait_for_timeout(1500)   # promoted: the phone layout
        else: lookup(pg); pick(pg, 'c070', 'Qadri'); pg.wait_for_timeout(1500)
        title = pg.evaluate('document.title')
        pg.evaluate("document.title = 'Precinct 300'; history.pushState(null, '', '/300')"); pg.wait_for_timeout(800)   # issue #67: the tracker counts a new path
        pg.evaluate("Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' }); document.dispatchEvent(new Event('visibilitychange'))")
        pg.wait_for_timeout(1500)                                                                 # the tracker sends its page-speed report on hide
        if gpc:
            assert sent == [], ('Do Not Track or Global Privacy Control: nothing at all is sent, not even page views', gpc, sent)
        else:
            names_ok = set(event_names_in_page())
            kinds = [p['payload'].get('name') for p in sent if p['type'] == 'event']
            assert None in kinds and 'lookup_started' in kinds and 'ballot_found' in kinds, kinds   # a page view and our events
            speed = [p['payload'] for p in sent if p['type'] == 'performance']
            assert speed and any(isinstance(speed[0].get(k), (int, float)) for k in ('ttfb', 'fcp', 'lcp', 'duration')), speed
            for p in sent:
                pl, blob = p['payload'], json.dumps(p)
                assert p['type'] in ('event', 'performance') and set(pl) <= TOP, p
                assert pl.get('name') is not None or 'data' not in pl, p
                assert pl.get('name') is None or pl['name'] in names_ok, p
                assert '#' not in pl.get('url', '') and '?' not in pl.get('url', ''), p
                assert not re.search(r'Guadalupe|78701|Precinct|Qadri|/300', blob), blob
                assert pl.get('title', title) == title and 'tag' not in pl, p
        ctx.close()


@desk_test
def desk_counts_laptop_features(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    ctx2, pg2 = new_page(b, wide=True); pg2.set_viewport_size({'width': 2560, 'height': 1300}); pg2.goto(BASE); pg2.wait_for_timeout(800)
    assert 'faq_seen' not in names(pg2), 'a tall window shows the FAQ at once: not counted until the visitor scrolls (audit #2)'
    pg2.evaluate("document.body.classList.add('dk-app-on'); window.dispatchEvent(new Event('scroll')); document.body.classList.remove('dk-app-on')"); pg2.wait_for_timeout(600)
    assert 'faq_seen' not in names(pg2), 'a scroll in the app view does not arm the FAQ count (Pass 2)'
    pg2.mouse.wheel(0, 200); pg2.wait_for_function("(window.__events||[]).some(e => e[0] === 'faq_seen')", timeout=3000)
    ctx2.close()
    pg.locator('#dk-faq').scroll_into_view_if_needed(); pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'faq_seen')")
    pg.evaluate('window.scrollTo(0, 0)'); lookup_wide(pg); no_link_opens(pg)
    pg.click('.dk-row[data-row="c001"]')
    for k in ('1', '1', 's', 'n', 'j', '/'): pg.keyboard.press(k)                                   # each kind counted once
    pg.keyboard.press('Escape'); pg.click('#dk-paper h1'); pg.keyboard.press('r'); pg.keyboard.press('Escape')
    used = [e[1]['kind'] for e in events(pg) if e[0] == 'shortcut_used']
    assert used == ['pick', 'skip', 'move', 'search', 'reason'], used
    pg.fill('#dk-q', 'gov'); pg.fill('#dk-q', 'gove'); pg.fill('#dk-q', '')
    pg.click('#dk-filt [data-f="und"]'); pg.click('#dk-filt [data-f="und"]'); pg.click('#dk-filt [data-f="all"]')
    assert names(pg).count('search_used') == 1 and [e[1]['filter'] for e in events(pg) if e[0] == 'filter_used'] == ['und', 'all']
    for v in ('glance', 'vote', 'crib'): pg.click(f'#dk-views [data-view="{v}"]')
    pg.click('#dk-views [data-view="glance"]')                                                    # a glance row's link knows its race (audit #8)
    pg.locator('tr[data-tr="c001"] a', has_text='League').first.click()
    assert events(pg)[-1] == ['source_opened', {'kind': 'league_guide', 'level': 'federal', 'layout': 'laptop'}], events(pg)[-1]
    pg.click('#dk-views [data-view="crib"]')
    pg.click('#dk-c2'); pg.evaluate('window.print = () => {}'); pg.click('#dk-notes [data-act="print"]')
    assert events(pg)[-1] == ['crib_printed', {'two_col': 'yes', 'hide_unopposed': 'no', 'layout': 'laptop'}], events(pg)[-1]
    pg.click('#dk-views [data-view="decide"]'); pg.click('.dk-row[data-row="c001"]')
    pg.locator('#dk-paper a', has_text='League guide answers').first.click()
    pg.locator('#dk-notes a', has_text='League of Women Voters guide').first.click()
    assert [e[1] for e in events(pg) if e[0] == 'source_opened'] == [{'kind': 'league_guide', 'level': 'federal', 'layout': 'laptop'}] * 3   # glance, paper, notes
    assert [e[1]['view'] for e in events(pg) if e[0] == 'view_opened'] == ['glance', 'vote', 'crib', 'glance', 'crib', 'decide']
    pg.click('#dk-views [data-view="vote"]')                                                       # no race level outside Decide
    pg.locator('#dk-paper a', has_text='VoteTravis.gov').first.click(); pg.locator('#dk-paper a', has_text='Check live wait times').first.click()
    assert events(pg)[-3:] == [['view_opened', {'view': 'vote', 'layout': 'laptop'}], ['source_opened', {'kind': 'official', 'layout': 'laptop'}],
                               ['wait_times_opened', {'period': pg.evaluate('period'), 'layout': 'laptop'}]], events(pg)[-3:]
    pg.click('#dk-help'); pg.click('[data-help="privacy"]'); pg.keyboard.press('Escape')
    assert events(pg)[-1] == ['help_opened', {'item': 'privacy', 'layout': 'laptop'}]
    journey_check(pg, 'laptop')
    pg.once('dialog', lambda d: d.accept()); pg.click('#dk-help'); pg.click('[data-help="clearall"]')
    pg.wait_for_selector('body:not(.dk-app-on)'); pg.wait_for_load_state()
    assert pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('ballotta.'))") == [] and pg.is_visible('#dk-hero')
    ctx.close()

@test
def readme_lists_every_counted_event(b):
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    missing = [n for n in event_names_in_page() if f'`{n}`' not in readme]
    assert not missing, ('README must list every counted event', missing)
    assert 'Global Privacy Control' in readme and 'ballotta.ownTracked' in readme and 'ballotta.progress' not in readme

# ---------------------------------------------------------------- issues round A (Oct 15): #20–#24, #32–#34, #37, #39–#42

@test
def share_names_block_lookalikes_and_nicknames(b):
    # #21: look-alike letters from other alphabets, digits standing in for letters, and party nicknames don't get a
    # share name past the reserved-name block. Real names in any alphabet still show.
    ctx, pg = new_page(b); pg.goto(BASE)
    sn = lambda n: pg.evaluate('n => safeName(n)', n)
    for bad in ['Lеague of Women Vоters', 'Travis Cоunty', 'ʟwv austin', 'Austin Dems', 'TX Dems', 'Dem', 'G.O.P.', 'Repubs of Austin',
                'RNC', 'DNC Texas', 'L3ague', 'C0unty Clerk', 'ΟFFICIAL', 'Тravis Сounty Еlections', 'ᴠᴏᴛᴇʀ ɪɴꜰᴏ', 'Ballοtta',
                'Travis-GOP', 'Tea-Party', 'Site-Admin', 'TX.State', 'Austin/Dems', 'G O P', 'D N C', 'V0te411', 'VOTE 4ll',   # Pass 1
                'Off1cial', 'C1ty of Austin', 'L1bertarian', 'ɡop', '6OP',
                'E1ect1on Info', 'Off1c1a1', 'Vote41I', 'VOTE4II', 'G. O. P.', 'D. N. C.', 'G+O+P', 'G~O~P', 'D^E^M^S', 'Off!cial', 'Ad|min',   # Pass 2
                'TravisGOP', 'AustinDems', 'GOP2026', 'Dems4Travis', 'TeaParty', 'SiteAdmin', '9OP', '8allotta', 'VoterGuide',
                'Cityof Austin', 'Travis Co. Tax Office', 'Travis County Clerk',   # Pass 3
                'voterguide', 'VOTERGUIDE', 'cityofaustin', 'travisclerk', 'texasvoters', 'travistaxoffice', 'villageofx',
                'GOPTravis', 'DNCTexas', 'VOTERInfo', 'STATEParty',   # Pass 4
                'X-GOP', 'GOP-X', 'J/RNC', 'Z+DNC', 'GOP_X',   # #94: punctuation is a space, even beside a single letter
                'Ɍepublican', 'Łwv', 'Ɠop', 'Ɗems', 'Ðems', 'Ƿarty', 'Ꝑarty', 'ɍepublican', 'łwv austin',   # #93: stroke and hook letters
                'LANEGOP', 'TRAVISDEMS', 'AUSTINRNC', 'TEXASDNC',   # #93: shouted, glued to the end
                'GØP', 'Travis GØP', 'LANEGØP', 'Đemocrat', 'Đems', 'Sŧate', 'Ƈounty', 'Øfficial', 'goƥ', 'Repuƀlican', 'Ɓallotta',   # Pass 1
                'Repʋblican', 'REPƲBLICAN', 'Coʋnty', 'Partᶌ', 'GƟP', 'Travis GƟP', 'ƟFFICIAL', 'Repʉblican', 'Coʉnty', 'Ꟈemocrat',   # Pass 2
                'ʋote411', 'Ʋote411', 'ᶌote411', 'ᴃallotta', 'Repuᴃlican', 'ᴌwv', 'Coᵾnty', 'Offᵻcial', 'Electᵻon', 'GꬾP',   # Pass 3
                'C\U0001DF1Bunty', 'Sta\U0001DF2Ae']:   # Pass 3: letters beyond 16 bits (Latin Extended-G): County, State
        assert sn(bad) == '', bad
    for good in ['Maya', 'Ana', 'José', "O'Brien", 'Dempsey', 'Ελένη', 'Ольга', '李明', 'Demetria', 'Gopal', 'Mary-Jane', 'Jean-Paul', 'A J', 'Liz 2',
                 'J R R Tolkien', 'A.J.', 'D J', 'R2-D2', "D'Angelo", 'Estate Jones', 'G O Pal', 'Işıl Yılmaz', 'Partyka', 'Admina',
                 'Gustavo Terrazas', 'Ivo Terzić', 'Felicity Ofori', 'Clerkin', 'DeMarco', 'DeShawn', 'McDonald', 'LaToya',   # Pass 3
                 'Clerkson', 'DeClerck', 'JRRTolkien', 'DJ Khaled', 'MacArthur', 'Gopinath', 'Rajagopal', 'Staten',   # Pass 4
                 'Łukasz', 'Ðorđe', 'Ɗemba', 'GOPAL', 'GOPINATH', 'ADAM', 'Lanegop', 'MARIA', 'Ådne',   # #93
                 'ERDEM', 'ERDEM YILMAZ', 'ÖZDEM', 'Erdem', 'Søren', 'Bjørn', 'Đorđe Petrović', 'Ørjan',   # Pass 1
                 'Đặng Thị Đào', 'Ɗanjuma Ƙabir', 'Ɓello Ƴaro', 'Łucja Dembska', 'Muħammad Ħili', 'Sigríður Eðvarðsdóttir']:   # Pass 2
        assert sn(good) == good, good
    odd = '¼Joﷺﬃﷺ'                                                             # Pass 2: the cut lands after a space
    assert sn(sn(odd)) == sn(odd) and sn(odd) and not sn(odd).endswith(' '), repr(sn(odd))
    ctx.close()

@test
def a_refused_share_name_is_said_to_the_sender(b):
    # #93: a name the friend's page would refuse ("Travis GOP") went into the link anyway, and the sender was never told:
    # the friend just saw "Your friend". Now the sender sees why under the box (Lane's words), and the name is neither
    # sent nor kept. Names are cut at 30 characters, never inside one (an emoji is two UTF-16 units).
    ctx, pg = new_page(b, wide=True, county='stub'); pg.goto(BASE); lookup_wide(pg)
    pg.evaluate('''() => { const c = ballot[0].c.id;
        pick(c, document.querySelector('[data-c="' + c + '"][data-pick]:not([data-pick="__skip"])').dataset.pick); }''')
    pg.evaluate('openShare()')
    note = lambda: pg.text_content('#sharename-no')
    assert note() == '' and pg.get_attribute('#sharename', 'aria-describedby') == 'sharename-no'
    pg.evaluate("window.__notes = []; new MutationObserver(() => __notes.push(document.getElementById('sharename-no').textContent)).observe(document.getElementById('sharename-no'), { childList: true, characterData: true, subtree: true })")
    pg.click('#sharename'); pg.keyboard.type('Demi', delay=60)                     # "Dem…" on the way to "Demi" is not refused (Pass 1)
    pg.wait_for_timeout(1000)
    assert not [x for x in pg.evaluate('__notes') if x] and note() == '' and pg.evaluate('sharePrep.name') == 'Demi', pg.evaluate('__notes')
    pg.fill('#sharename', 'Travis GOP')
    assert pg.evaluate('sharePrep.name') == '', 'a refused name is never sent, even before the note shows'
    pg.wait_for_function("document.getElementById('sharename-no').textContent !== ''", timeout=3000)   # once typing pauses
    assert note() == 'That name can’t be used. Try your first name.', note()
    pg.fill('#sharename', 'Maya  Lee'); assert note() == '' and pg.evaluate('sharePrep.name') == 'Maya Lee'   # cleaned, still sent
    pg.fill('#sharename', 'Travis GØP'); pg.evaluate("document.getElementById('sharename').blur()")
    assert note() == 'That name can’t be used. Try your first name.' and pg.evaluate('sharePrep.name') == ''      # leaving the box: at once
    pg.evaluate(r"document.getElementById('sharename').value = 'Travis­́GOP'; prepShare()")   # passes once, refused when checked again (Pass 1)
    assert pg.evaluate('sharePrep.name') == '', ('a name the friend\'s page would refuse goes into the link', pg.evaluate('sharePrep.name'))
    url = pg.evaluate('sharePrep.p')
    frag = url.split('#', 1)[1]
    assert pg.evaluate('f => unpackFrag(f).then(o => o.n)', frag) == '', 'a refused name went into the link'
    pg.fill('#sharename', 'Maya')
    assert note() == '' and pg.evaluate('sharePrep.name') == 'Maya'
    pg.fill('#sharename', 'Travis GOP'); pg.evaluate("$('share-go').click()"); pg.wait_for_timeout(500)
    assert pg.evaluate("localStorage.getItem('ballotta.name')") in (None, '""'), 'a refused name was kept for next time'
    # Round-2 audit #9 (#107): a refused name leaves the name kept from before alone; a box emptied on purpose clears it.
    pg.fill('#sharename', 'Maya'); pg.evaluate("$('share-go').click()"); pg.wait_for_timeout(500)
    assert pg.evaluate("localStorage.getItem('ballotta.name')") == '"Maya"', pg.evaluate("localStorage.getItem('ballotta.name')")
    pg.fill('#sharename', 'Travis GOP'); pg.evaluate("$('share-go').click()"); pg.wait_for_timeout(500)
    assert pg.evaluate("localStorage.getItem('ballotta.name')") == '"Maya"', ('a refused name wiped the kept one', pg.evaluate("localStorage.getItem('ballotta.name')"))
    pg.fill('#sharename', ''); pg.evaluate("$('share-go').click()"); pg.wait_for_timeout(500)
    assert pg.evaluate("localStorage.getItem('ballotta.name')") == '""', 'an emptied box kept the old name'
    pg.evaluate(r"document.getElementById('sharename').value = 'a'.repeat(29) + '\u{1F600}\u{1F600}'; prepShare()")
    got = pg.evaluate('sharePrep.name')
    assert got == 'a' * 29 + '\U0001F600' and len(got.encode('utf-16-le')) == 62, ('cut inside a character', [hex(ord(c)) for c in got[-2:]])
    assert pg.evaluate(r"safeName('b'.repeat(29) + '\u{1F600}x')") == 'b' * 29 + '\U0001F600'
    ctx.close()

@desk_test
def desk_change_link_focus_ring_is_whole(b):
    # #22: the header box that cuts a long address short with "…" must not also cut off the 4px focus ring around
    # "change", in the app and on the landing page it returns to.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    for where in ('app', 'landing'):
        c, l = box(pg, '#dk-change'), box(pg, '#dk-loc')
        assert l['x'] <= c['x'] - 4 and l['y'] <= c['y'] - 4 and l['x'] + l['width'] >= c['x'] + c['width'] + 4 and l['y'] + l['height'] >= c['y'] + c['height'] + 4, (where, c, l)
        if where == 'app': pg.click('#dk-change'); pg.wait_for_selector('body:not(.dk-app-on)')
    ctx.close()


@desk_test
def desk_friend_pick_in_rail_has_a_name(b):
    # #32: a friend's pick in a rail row is read out ("Maya picked …"), not just the letter on the chip.
    ctx, pg = new_page(b, wide=True); fresh_goto(pg, link('s', {'v': 1, 'n': 'Maya', 'c': 'abcd2346', 'g': 1, 'p': {'70': 0}}))
    pg.wait_for_selector('#friend:not(.hidden)'); lookup_wide(pg)
    first = pg.evaluate('optionsOf(BYID.c070)[0]')
    row = pg.locator('#dk-out [data-row="c070"]')
    expect(row).to_have_accessible_name(re.compile('Maya picked ' + re.escape(first)))
    assert row.locator('.dk-fa').get_attribute('aria-hidden') == 'true'
    ctx.close()


@test
def dates_move_on_in_a_tab_left_open(b):
    # #34: today's date is read when drawing, so a tab left open past midnight moves on: Election Day after Oct 30,
    # and the laptop header's line. A period the visitor chose stays chosen.
    import datetime as dt
    for wide, choose in ((False, False), (False, True)) + (((True, False),) if HAS_DESK else ()):
        ctx, pg = new_page(b, wide=wide); pg.clock.install(time=dt.datetime(2026, 10, 30, 23, 58)); pg.goto(BASE)
        eday = lambda: pg.get_attribute('#t-eday', 'aria-pressed')
        assert eday() == 'false', (wide, choose)
        if wide: assert pg.text_content('#dk-when') == 'Early voting through Fri Oct 30 · 7am–7pm', pg.text_content('#dk-when')
        if choose: pg.evaluate("document.getElementById('t-early').click()")
        pg.clock.run_for(5 * 60 * 1000)
        assert eday() == ('false' if choose else 'true'), (wide, choose)
        if wide: assert pg.text_content('#dk-when') == 'Election Day is Tue Nov 3 · 7am–7pm', pg.text_content('#dk-when')
        ctx.close()
    if HAS_DESK:
        # Typing a reason on the laptop across midnight: the new day must not take focus away, or the rest of the
        # sentence would run as shortcuts (picks, skips, moves) (Pass 1).
        st = json.dumps({'pr': '999', 'b': [70, 71, 113], 'mode': 'saved', 'at': 0, 'pt': None})
        ctx, pg = new_page(b, wide=True); pg.clock.install(time=dt.datetime(2026, 10, 30, 23, 58)); pg.goto(BASE)
        pg.evaluate('s => localStorage.setItem("ballotta.ballot", s)', st); pg.reload(); pg.wait_for_selector('body.dk-app-on')
        cid = pg.evaluate('ballot[0].c.id')
        pg.focus('#dk-w'); pg.keyboard.type('Because she ')
        pg.clock.run_for(5 * 60 * 1000)
        assert pg.text_content('#dk-when') == 'Election Day is Tue Nov 3 · 7am–7pm', 'the header still moves on'
        pg.keyboard.type('knows 1 thing, and so on')
        assert pg.evaluate('document.activeElement.id') == 'dk-w', pg.evaluate('document.activeElement.tagName')
        assert pg.evaluate(f"whys['{cid}']") == 'Because she knows 1 thing, and so on', pg.evaluate('whys')
        assert pg.evaluate('JSON.stringify(picks)') == '{}', pg.evaluate('JSON.stringify(picks)')
        ctx.close()
        # In the vote view, the new day re-draws the hours but keeps the visitor's place (Pass 2).
        ctx, pg = new_page(b, wide=True); pg.clock.install(time=dt.datetime(2026, 10, 30, 23, 58)); pg.goto(BASE)
        pg.evaluate('s => localStorage.setItem("ballotta.ballot", s)', st); pg.reload(); pg.wait_for_selector('body.dk-app-on')
        pg.click('#dk-views [data-view="vote"]'); pg.focus('#dk-paper [data-period="early"]')
        pg.clock.run_for(5 * 60 * 1000)
        assert pg.get_attribute('#dk-paper [data-period="eday"]', 'aria-pressed') == 'true', 'the vote view moved on to Election Day'
        assert pg.evaluate('document.activeElement.id') == 'dk-paper', 'a new list: focus on the paper, not on another center (Pass 4)'
        ctx.close()
        # ...and on a Directions link, by its position in the list (Pass 3)
        ctx, pg = new_page(b, wide=True); pg.clock.install(time=dt.datetime(2026, 10, 18, 23, 58)); pg.goto(BASE)
        pg.evaluate('s => localStorage.setItem("ballotta.ballot", s)', st); pg.reload(); pg.wait_for_selector('body.dk-app-on')
        pg.click('#dk-views [data-view="vote"]'); link3 = pg.locator('#dk-paper a', has_text='Directions').nth(2); link3.focus()
        href = link3.get_attribute('href'); pg.clock.run_for(5 * 60 * 1000)
        assert pg.text_content('#dk-when') == 'Early voting through Fri Oct 30 · 7am–7pm', pg.text_content('#dk-when')
        assert pg.evaluate('document.activeElement.getAttribute("href")') == href, pg.evaluate('document.activeElement.outerHTML.slice(0, 120)')
        ctx.close()

@test
def build_inserts_data_last(b):
    # #37: the ballot data goes in after every other placeholder, so text in the data that looks like one is never
    # changed by the build.
    import types
    m = build_module()
    odd = '{"x": "__OG_IMAGE__ <!--ANALYTICS--> <!--FONTS-->f<!--/FONTS--> url(\'fonts/ href=\\"favicon.svg\\" __DATA__"}'
    m.json = types.SimpleNamespace(load=json.load, dumps=lambda *a, **k: odd)
    for preview in (False, True):
        html = m.build(preview=preview)
        assert 'const DATA = ' + odd.replace('<', '\\u003c') + ';' in html, preview   # every "<" is escaped since #85

@desk_test
def desk_moves_are_announced(b):
    # #39: J, K and N say where they landed ("Contest 2 of 63: …"), since the paper's own label never changes.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    n = pg.evaluate('ballot.length'); t = lambda i: pg.evaluate(f'cleanTitle(ballot[{i}].c)')
    said = lambda text: pg.wait_for_function('t => document.getElementById("dk-live").textContent === t', arg=text, timeout=3000)
    pg.locator('#dk-out .dk-row').first.click(); said(f'Contest 1 of {n}: {t(0)}. No pick yet.')
    pg.keyboard.press('j'); said(f'Contest 2 of {n}: {t(1)}. No pick yet.')
    first = pg.evaluate('optionsOf(ballot[1].c)[0]')
    pg.keyboard.press('1'); pg.wait_for_timeout(1200); pg.keyboard.press('k'); said(f'Contest 1 of {n}: {t(0)}. No pick yet.')   # apart: see #45
    pg.keyboard.press('j'); said(f'Contest 2 of {n}: {t(1)}. Picked {first}.')
    pg.keyboard.press('n'); said(f'Contest 3 of {n}: {t(2)}. No pick yet.')
    ctx.close()


@test
def mutation_runner_judges_mutants_honestly(b):
    # Cold audit #26 (#70): a mutant written into a built page leaves its Content-Security-Policy hashes stale, so a test
    # run under the page's own policy failed because the whole script was refused, not because of the mutant. The runner
    # now recomputes them: the unmutated page round-trips exactly, a mutated script gets its own hash.
    # Cold audit #27 (#71): a Playwright timeout counted as a kill; now a timeout counts only if it happens again.
    import subprocess
    code = r"""
import sys, json, re, types; sys.argv = ['mutate_desk.py']; sys.path.insert(0, %r); import mutate_desk as R
page = R.PREV.read_text(encoding='utf-8')
same = R.mutate(R.PREV, page, '<title>', '<title>') == page
src = re.search(r'<script>(.*?)</script>', page, re.S).group(1)
mut = R.mutate(R.PREV, page, src, src + ' ')
meta = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', mut).group(1)
hashed = R.T.build_module().sha(src + ' ') in meta and R.T.build_module().sha(src) not in meta
others = {p: R.mutate(R.ROOT / p, (R.ROOT / p).read_text(encoding='utf-8'), '<title>', '<title>') == (R.ROOT / p).read_text(encoding='utf-8')
          for p in ('census.html', 'next/index.html')}                     # each keeps its own policy (Pass 1)
phone = 'worker-src' in R.mutate(R.PREV, page, 'id="ph-bar"', 'id="ph-bar-x"') if 'id="ph-bar"' in page else True
calls = {}
def fake(name, plan):
    def f(b):
        n = calls[name] = calls.get(name, 0) + 1
        e = plan[n - 1] if n <= len(plan) else None
        if e: raise e
    setattr(R.T, name, f)
class TimeoutError(Exception): pass
fake('once', [TimeoutError('slow')]); fake('twice', [TimeoutError('slow'), TimeoutError('slow')]); fake('fails', [AssertionError('no')]); fake('fine', [])
print(json.dumps({'same': same, 'hashed': hashed, 'others': others, 'phone': phone, 'once': R.run_targets(None, ['once']), 'twice': R.run_targets(None, ['twice']),
                  'fails': R.run_targets(None, ['fails']), 'fine': R.run_targets(None, ['fine'])}))
""" % str(ROOT / 'tests')
    r = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, cwd=str(ROOT), timeout=120)
    assert r.returncode == 0, r.stderr[-1500:]
    got = json.loads(r.stdout.strip().splitlines()[-1])
    assert got['same'] and got['hashed'], ('the page CSP after a mutant', got)
    assert all(got['others'].values()) and got['phone'], ('only the page is re-hashed, by what it was before the mutant', got)
    assert got['once'] == [] and got['twice'] == ['twice:TimeoutError x2'] and got['fails'] == ['fails:AssertionError'] and got['fine'] == [], got

@test
def mutation_runner_restores_on_any_signal(b):
    # #41: Ctrl-C, a kill or a hang-up while a mutant is on disk always puts the original back before exiting.
    import subprocess, tempfile, signal as S
    assert "\nif __name__ == '__main__':" in (ROOT / 'tests/mutate_desk.py').read_text(encoding='utf-8'), 'importing the runner must not start a run'
    for sig in (S.SIGINT, S.SIGTERM, S.SIGHUP):
        f = pathlib.Path(tempfile.mkdtemp()) / 'page.html'; f.write_text('original', encoding='utf-8')
        code = ('import sys, time, pathlib; sys.argv = ["mutate_desk.py"]; sys.path.insert(0, %r); import mutate_desk as R\n'
                'f = pathlib.Path(%r); R.PENDING.append((f, "original")); R.put(f, "MUTANT"); print("ready", flush=True); time.sleep(60)') % (str(ROOT / 'tests'), str(f))
        p = subprocess.Popen([sys.executable, '-c', code], cwd=ROOT, stdout=subprocess.PIPE, text=True)
        assert p.stdout.readline().strip() == 'ready', sig
        assert f.read_text(encoding='utf-8') == 'MUTANT', 'precondition: the mutant is on disk'
        p.send_signal(sig); p.wait(20)
        assert f.read_text(encoding='utf-8') == 'original', (sig, f.read_text(encoding='utf-8'))

@test
def mutation_runner_runs_alone(b):
    # #79: two runners in one clone, or a build while one runs, put mutants on disk that nobody restores. A run takes
    # .mutate-lock (atomically) and refuses to start while a lock or a half-written *.mutate-tmp is there. A signal
    # restores the file and then drops the lock; a kill -9 can't restore, so it leaves the lock and the next run stops.
    # #80: a mutant whose targets can't see the file it changes (a template mutant aimed at browser tests) is refused.
    import subprocess, tempfile, signal as S
    head = 'import sys, time, pathlib; sys.argv = ["mutate_desk.py"]; sys.path.insert(0, %r); import mutate_desk as R\nd = pathlib.Path(%r)\n'
    def child(d, body, wait=True):
        p = subprocess.Popen([sys.executable, '-c', head % (str(ROOT / 'tests'), str(d)) + body], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if not wait: return p
        out, err = p.communicate(timeout=60); return p.returncode, out + err
    d = pathlib.Path(tempfile.mkdtemp())
    rc, out = child(d, 'R.take_lock(d); print("first", (d / ".mutate-lock").exists()); R.take_lock(d)')
    assert 'first True' in out and rc != 0 and '.mutate-lock' in out, ('a second run took the lock', rc, out[-600:])
    rc, out = child(d, 'R.ROOT = d; R.main([])')                                     # main itself checks, before any server starts
    assert rc != 0 and '.mutate-lock' in out and 'baseline' not in out, ('main ran with a lock in place', rc, out[-600:])
    (d / '.mutate-lock').unlink(); (d / 'next').mkdir(); (d / 'next/index.html.mutate-tmp').write_text('half')
    rc, out = child(d, 'R.take_lock(d)')
    assert rc != 0 and 'index.html.mutate-tmp' in out, ('a half-written file was ignored', rc, out[-600:])
    (d / 'next/index.html.mutate-tmp').unlink()
    for sig, kept in ((S.SIGTERM, False), (S.SIGKILL, True)):
        f = d / 'page.html'; f.write_text('original', encoding='utf-8')
        p = child(d, 'R.take_lock(d); f = d / "page.html"; R.PENDING.append((f, "original")); R.put(f, "MUTANT"); print("ready", flush=True); time.sleep(60)', wait=False)
        assert p.stdout.readline().strip() == 'ready', sig
        p.send_signal(sig); p.wait(20)
        assert (d / '.mutate-lock').exists() == kept, (sig, 'lock left' if not kept else 'lock dropped with a mutant on disk')
        assert f.read_text(encoding='utf-8') == ('MUTANT' if kept else 'original'), sig
    rc, out = child(d, 'R.take_lock(d)')
    assert rc != 0 and 'compare the whole tree with git' in out, ('after a kill -9 the next run must stop and say how to check', out[-600:])
    (d / '.mutate-lock').unlink()
    rc, out = child(d, 'R.take_lock(d); R.PENDING.append((d / "x", "x")); R.drop_lock(); print("held", (d / ".mutate-lock").exists()); '
                       'R.PENDING.clear(); R.drop_lock(); print("gone", not (d / ".mutate-lock").exists())')
    assert rc == 0 and 'held True' in out and 'gone True' in out, ('the lock goes only once nothing is pending', out[-600:])
    (d / '.mutate-lock').write_text('x')                                            # if the #80 check failed, main stops at the lock, not at the real repo
    rc, out = child(d, 'R.ROOT = d; R.main([("X1", R.TPL, "<title>", "<title>x", ["phone_add_to_home_screen_three_ways"])])')
    assert rc != 0 and "can't see" in out and 'baseline' not in out, ('a template mutant aimed at a browser test ran', out[-600:])
    rc, out = child(d, 'R.ROOT = d; R.main([("X2", R.PREV, "<title>", "<title>x", ["no_such_test_named_this"])])')
    assert rc != 0 and 'no test named no_such_test_named_this' in out, ('a misspelled target ran', out[-600:])
    rc, out = child(d, 'R.ROOT = d; R.main([("X5", R.PREV, "<title>", "<title>x", ["lookup_wide"])])')   # a helper, not a test (Pass 1)
    assert rc != 0 and 'no test named lookup_wide' in out, ('a helper ran as a target', out[-600:])
    rc, out = child(d, 'R.ROOT = d; R.main([("X3", R.PREV, "<title>", "<title>x", ["desk_phone_layout_matches_live_page"])])')
    assert rc != 0 and "can't see" in out, ('a built-page mutant aimed at a test that builds from the template ran (L9)', out[-600:])
    rc, out = child(d, 'R.ROOT = d; R.main([("X4", R.BLD, "hashlib.sha256(js.encode(", "hashlib.sha256(js.encode(", ["census_runs_in_a_sandbox"])])')   # a test that runs the build
    assert rc != 0 and "can't see" not in out and '.mutate-lock' in out, ('a build-script mutant aimed at a test that runs the build was refused', out[-600:])
    ignored = (ROOT / '.gitignore').read_text(encoding='utf-8').split()
    assert '*.mutate-tmp' in ignored and '.mutate-lock' in ignored, ignored


@desk_test
def desk_print_button_opens_the_crib_sheet(b):
    # Lane (Oct 15): the left column's Print opens the Crib sheet view (with its print options); it doesn't print.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.evaluate('() => { window.__printed = 0; window.print = () => { window.__printed++; }; }')   # a function: a bare assignment string would be called once by evaluate
    assert pg.text_content('#dk-print') == 'Print…'                                # it opens options: an ellipsis (Pass 2)
    pg.focus('#dk-print'); pg.keyboard.press('Enter')
    assert pg.get_attribute('#dk-views [data-view="crib"]', 'aria-current') == 'page'
    assert pg.locator('#dk-notes #dk-c2').count() == 1 and pg.evaluate('window.__printed') == 0
    assert pg.evaluate('document.activeElement.dataset.act') == 'print', 'keyboard users land on the real Print button (Pass 2)'
    assert 'crib_printed' not in names(pg) and events(pg)[-1] == ['view_opened', {'view': 'crib', 'layout': 'laptop'}], events(pg)[-1]
    pg.focus('#dk-print'); pg.keyboard.press('Enter')                              # already there: not counted again (Pass 2)
    assert [e[1].get('view') for e in events(pg) if e[0] == 'view_opened'] == ['crib'], events(pg)
    pg.click('#dk-views [data-view="decide"]'); pg.click('#dk-print')               # a mouse click doesn't move focus: Space won't print (Pass 3)
    assert pg.evaluate('document.activeElement.dataset.act') != 'print'
    pg.set_viewport_size({'width': 1100, 'height': 800})                            # the notes sit below the paper at 1024–1279px (Pass 3)
    pg.click('#dk-views [data-view="decide"]'); pg.focus('#dk-print'); pg.keyboard.press('Enter')
    r = pg.evaluate('(() => { const r = document.activeElement.getBoundingClientRect(); return [document.activeElement.dataset.act, r.top, r.bottom, innerHeight]; })()')
    assert r[0] == 'print' and r[1] >= 0 and r[2] <= r[3], ('the focused Print button is off screen', r)
    pg.click('#dk-views [data-view="decide"]'); pg.focus('#dk-print'); before = pg.evaluate('window.__printed')
    for _ in range(3): pg.keyboard.down('Enter')                                    # a held Enter: its repeats don't print (Pass 4)
    pg.keyboard.up('Enter'); assert pg.evaluate('window.__printed') == before, 'holding Enter on Print… printed'
    pg.click('#dk-notes [data-act="print"]')
    assert pg.evaluate('window.__printed') == 1 and events(pg)[-1][0] == 'crib_printed'
    ctx.close()

# ---------------------------------------------------------------- issues round B (Oct 15): #36 hardening, #38 untangling
def poll(pg, js, timeout=30):                                   # a wait that works under the page's CSP (no eval in the page)
    import time
    end = time.time() + timeout
    while not pg.evaluate(js):
        if time.time() > end: raise AssertionError('timed out waiting for ' + js)
        pg.wait_for_timeout(100)

def lookup_strict(pg, wide=False):
    pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '78701'); pg.click('#go')
    poll(pg, "document.body.classList.contains('dk-app-on') && / of \\d+ decided$/.test(document.getElementById('dk-count').textContent)" if wide
         else "!document.getElementById('result').classList.contains('hidden') && document.getElementById('k-total').textContent !== '0'")

CSP_WATCH = "window.__csp = []; document.addEventListener('securitypolicyviolation', e => window.__csp.push(e.effectiveDirective + ' ' + e.blockedURI));"


@test
def page_data_cannot_break_out_of_its_script(b):
    # #85 (audit #38): the build writes the page's data inside a script, so no string in it may end the script ("</"),
    # open an HTML comment ("<!--" changes how the script is read) or end a line of JavaScript (U+2028, U+2029); and
    # every campaign site and source link must be http(s), never javascript: or data:.
    import types
    m = build_module()
    nasty = {'n': '</script><script>alert(1)</script><!--     x'}
    out = m.script_json(nasty)
    assert not re.search('</|<!--|[  ]', out), out
    ctx, pg = new_page(b); pg.goto(BASE)
    assert pg.evaluate('() => (' + out + ')') == nasty, 'the data still reads back exactly'
    ctx.close()
    def shim(edit):
        J = types.ModuleType('json'); J.__dict__.update(json.__dict__)
        def load(f, **k):
            d = json.load(f, **k)
            if str(getattr(f, 'name', '')).endswith('learn.json'): edit(d)
            return d
        J.load = load; return J
    m = build_module(); m.json = shim(lambda d: d['c001'].update(office=d['c001']['office'] + ' </script><!--  '))
    html = m.build(); i = html.index('const DATA = '); data = html[i:html.index('\n', i)]
    assert '</' not in data and '<!--' not in data and ' ' not in data, 'the page\'s data goes in through script_json'
    for edit in (lambda d: d['c001']['cands']['Ken Paxton'].update(s='javascript:alert(1)'), lambda d: d['c001']['src'][0].update(u='data:text/html,x')):
        m = build_module(); m.json = shim(edit)
        try: m.build(); raise AssertionError('the build accepted a link that is not http(s)')
        except SystemExit as e: assert 'http' in str(e), e

@test
def census_answers_only_from_its_sandboxed_frame(b):
    # #85 (audit #38): the page takes the Census point only from its own frame (e.source) and only from the sandbox,
    # whose origin is "null" (e.origin), so a message dressed up as the frame's from any real origin is ignored.
    ctx, pg = new_page(b)
    ctx.route(re.compile(r'https://geocoding\.geo\.census\.gov/.*'), lambda r: None)       # the Census never answers
    pg.goto(BASE); pg.evaluate("() => { window.__cp = 'pending'; censusPoint('1 Main St', '78701').then(v => { window.__cp = v; }); }")   # not awaited
    pg.wait_for_selector('iframe[title="Census address lookup"]', state='attached')
    send = "([o, d]) => window.dispatchEvent(new MessageEvent('message', { data: d, origin: o, source: document.querySelector('iframe[title=\"Census address lookup\"]').contentWindow }))"
    pt = {'x': -97.74, 'y': 30.27, 'label': 'FORGED'}
    pg.evaluate("d => window.dispatchEvent(new MessageEvent('message', { data: d, origin: 'null', source: window }))", pt); pg.wait_for_timeout(300)
    assert pg.evaluate('window.__cp') == 'pending', 'a sandboxed answer from another window is ignored'
    pg.evaluate(send, ['https://evil.example', pt]); pg.wait_for_timeout(300)
    assert pg.evaluate('window.__cp') == 'pending', 'an answer from a real origin is ignored'
    pg.evaluate(send, ['null', pt]); pg.wait_for_timeout(300)
    assert pg.evaluate('window.__cp') == pt, ('the probe itself works: the sandbox\'s answer is taken', pg.evaluate('window.__cp'))
    ctx.close()

@test
def census_runs_in_a_sandbox(b):
    # #36: the Census geocoder only answers as JSONP (a script), so it runs in a sandboxed frame (census.html) that
    # can't reach this page or its storage and can hand back only a point, which the page checks.
    m = build_module()
    assert (ROOT / 'census.html').read_text(encoding='utf-8') == m.census_page(), 'census.html on disk is not what the build writes'
    assert "f.src = '../census.html'" in m.build(preview=True), 'the preview (one folder down) finds census.html at the root (Pass 1)'
    # Embedded by another page without a sandbox, census.html does nothing (it would run as this site) (Pass 1).
    ctx, pg = new_page(b, csp=True); hits = []
    ctx.route(re.compile(r'https://geocoding\.geo\.census\.gov/.*'), lambda r: (hits.append(r.request.url), r.abort()))
    pg.goto(BASE)
    pg.evaluate("() => new Promise(ok => { const f = document.createElement('iframe'); f.src = 'census.html'; f.onload = () => { f.contentWindow.postMessage('1 Main St, TX 78701', '*'); setTimeout(ok, 800); }; document.body.appendChild(f); })")
    assert hits == [], ('census.html ran outside its sandbox', hits)
    ctx.close()
    def census(route, body):
        route.fulfill(status=200, content_type='application/javascript', body=body)
    match = '{"coordinates":{"x":-97.74,"y":30.27},"matchedAddress":"1 NOWHERE ST, AUSTIN, TX, 78701"}'
    hostile = ("cb({\"result\":{\"addressMatches\":[" + match + "]}});"
               "try { parent.document.body.dataset.pwned = '1'; } catch (e) {}"
               "try { parent.localStorage.setItem('ballotta.pwned', '1'); } catch (e) {}"
               "try { localStorage.setItem('ballotta.pwned', '1'); } catch (e) {}"
               "try { top.location.hash = '#pwned'; } catch (e) {}")
    looper = "location.href = 'census.html?again';"                                                       # reloads the frame (Pass 1)
    for body, reason in ((hostile, 'no_voters_nearby'),                                                  # a point came back
                         (looper, 'census_unreachable'),                                    # never answers: unreachable, not a wrong address (#59)
                         ('cb({"result":{"addressMatches":[{"coordinates":{"x":"-97.7; alert(1)","y":30.27},"matchedAddress":"x"}]}})', 'not_found'),
                         ('cb({"result":{"addressMatches":[{"coordinates":{"x":2.35,"y":48.85},"matchedAddress":"PARIS"}]}})', 'not_found')):
        ctx, pg = new_page(b, csp=True); refs = []
        ctx.route(re.compile(r'.*GeocodeServer/findAddressCandidates.*'), lambda r: r.fulfill(status=200, content_type='application/json', body='{"candidates":[]}'))
        ctx.route(re.compile(r'.*VotingAddresses/VA/MapServer/0/query.*'), lambda r: r.fulfill(status=200, content_type='application/json', body='{"features":[]}'))
        ctx.route(re.compile(r'https://geocoding\.geo\.census\.gov/.*'), (lambda bd: lambda r: (refs.append(r.request.headers.get('referer')), census(r, bd)))(body))
        pg.goto(BASE); pg.evaluate("() => { window.__spam = setInterval(() => postMessage({ x: -97.74, y: 30.27, label: 'FAKE' }, '*'), 5); }")   # only the frame's answer counts
        pg.fill('#street', '1 Nowhere St'); pg.fill('#zip', '78701'); pg.click('#go')
        poll(pg, "(window.__events||[]).some(e => e[0] === 'lookup_failed')", 15)
        assert events(pg)[-1] == ['lookup_failed', {'reason': reason, 'layout': 'phone'}], (body[:40], events(pg))
        assert pg.evaluate("document.body.dataset.pwned") is None and pg.evaluate("localStorage.getItem('ballotta.pwned')") is None and pg.evaluate('location.hash') == ''
        assert refs == [None], ('one Census request, with no referrer: a reloading frame does not loop', len(refs), refs[:2])
        assert pg.locator('iframe').count() == 0, 'the frame is removed after use'
        ctx.close()

@test
def campaign_links_use_https_where_they_work(b):
    # #36: the three campaign sites that load over https:// in a browser are linked that way; the four that answered
    # only on http:// stay so (an https:// link to them would show a certificate error). A new http:// site fails here
    # until someone checks it.
    learn = json.loads((ROOT / 'source/learn.json').read_text(encoding='utf-8'))
    sites = {c['s'] for L in learn.values() for c in (L.get('cands') or {}).values() if c.get('s')}
    plain = {u for u in sites if u.startswith('http://')}
    assert plain == {'http://Kirk4AISD.com', 'http://SavingManor.org', 'http://votedibianca.com', 'http://voteneillsnider.com'}, plain
    for u in ('https://cuero4rrisd.com', 'https://juliefortexassenate.com', 'https://www.FarrahAbraham.com'):
        assert u in sites, u

@desk_test
def desk_works_without_phone_buttons(b):
    # #38: the laptop layout calls shared, named functions instead of clicking the phone layout's hidden buttons or
    # copying its markup: with those buttons gone, every laptop action still works.
    src = (ROOT / 'source/template-travis.html').read_text(encoding='utf-8')
    page = (ROOT / PAGE).read_text(encoding='utf-8')                     # the page under test (mutants change it)
    deskjs = page[page.index('const desk = (() => {'):page.index('window.desk = desk;')]
    assert not re.findall(r"\$\('[\w-]+'\)\.click\(\)", deskjs), re.findall(r"\$\('[\w-]+'\)\.click\(\)", deskjs)
    for read in ("$('hours')", "$('sitehead')", "$('waits')", "$('crib').innerHTML"):
        assert read not in deskjs, read
    ctx, pg = new_page(b, wide=True); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Maya', 'c': 'abcd2348', 'g': 1, 'p': {'70': 0}}))
    pg.wait_for_selector('#friend:not(.hidden)'); lookup_wide(pg)
    pg.evaluate("() => { ['a-share', 'a-keep', 'print', 'reset', 'reset-all', 'feedback', 'f-hide'].forEach(id => { const e = document.getElementById(id); if (e) e.id = id + '-gone'; }); }")
    pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]'); pg.keyboard.press('Escape')
    pg.click('#dk-keep'); pg.wait_for_selector('#d-keep[open]'); pg.keyboard.press('Escape')
    pg.click('#dk-paper [data-act="hidefriend"]'); pg.wait_for_function('!friend')
    assert pg.locator('.dk-fchip').count() == 0 and pg.evaluate("document.getElementById('friend').classList.contains('hidden')")
    pg.click('#dk-views [data-view="vote"]')
    assert '7am–7pm' in pg.inner_text('#dk-paper') and 'electionlink.net' in pg.get_attribute('#dk-paper a.btn', 'href')
    pg.evaluate('() => { window.__printed = 0; window.print = () => { window.__printed++; }; }')
    pg.click('#dk-views [data-view="crib"]'); pg.click('#dk-notes [data-act="print"]')
    assert pg.evaluate('window.__printed') == 1 and events(pg)[-1][0] == 'crib_printed'
    assert 'My ballot choices' in pg.inner_text('#dk-page') and 'My ballot notes' not in pg.inner_text('#dk-page')   # Lane, Oct 17
    pg.click('#dk-views [data-view="decide"]'); pg.locator('#dk-paper .dk-line').first.click()
    assert pg.evaluate('Object.keys(picks).length') == 1
    pg.click('#dk-help'); pg.once('dialog', lambda d: d.accept()); pg.click('#dk-menu [data-help="clear"]')
    assert pg.evaluate('Object.keys(picks).filter(k => current(k).length).length') == 0
    pg.click('#dk-help'); pg.once('dialog', lambda d: d.accept()); pg.click('#dk-menu [data-help="clearall"]')
    pg.wait_for_function("!Object.keys(localStorage).some(k => k.startsWith('ballotta.'))", timeout=5000)
    assert errs == [], errs
    ctx.close()

# ---------------------------------------------------------------- issues round C (Oct 15): #43–#49
def saved_ballot(pg, nums, pt=None):
    pg.evaluate('s => localStorage.setItem("ballotta.ballot", s)', json.dumps({'pr': '999', 'b': nums, 'mode': 'saved', 'at': 0, 'pt': pt})); pg.reload()

@desk_test
def desk_next_never_points_at_the_open_contest(b):
    # #53: when the contest that is open is the only undecided one, the laptop's Next control named it and went nowhere.
    # As on the phone (round I), Next is never the contest already open: it goes on to the next contest in order, and
    # from the last one to At a glance.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    ui = lambda: pg.evaluate('[desk.ph.ui.view, desk.ph.ui.cur]')
    for decided, open_, after in ((['c001', 'c071'], 'c070', ['decide', 'c071']), (['c001', 'c070'], 'c071', ['glance', 'c071'])):
        pg.evaluate("ids => localStorage.setItem('ballotta.picks', JSON.stringify(Object.fromEntries(ids.map(id => [id, [optionsOf(BYID[id])[0]]]))))", decided)
        saved_ballot(pg, [1, 70, 71]); pg.wait_for_selector('body.dk-app-on')
        pg.evaluate('id => desk.ph.go(id)', open_); pg.wait_for_timeout(200)
        assert ui() == ['decide', open_], ui()
        label = pg.inner_text('#dk-next')
        assert 'Next undecided' not in label, (open_, 'names the contest already open', label)
        assert label.startswith('Next: ' if open_ == 'c070' else 'Last contest · see At a glance'), (open_, label)   # Lane, Oct 18
        pg.click('#dk-next'); pg.wait_for_timeout(200)
        assert ui() == after, (open_, ui())
        pg.evaluate('id => desk.ph.go(id)', open_); pg.focus('#dk-paper'); pg.keyboard.press('n'); pg.wait_for_timeout(200)
        assert ui() == after, (open_, 'N', ui())
    ctx.close()

@phone_test
def next_keeps_going_past_a_contest_left_undecided(b):
    # Round-2 audit #28 (#125): with one contest left undecided and open, Next went on in order, and from there "Next
    # undecided" pointed back at it: Next and N alternated between the two forever. Moving on from it with Next means
    # leaving it for now: Next keeps going in order, to At a glance (laptop) or the crib sheet (phone), not back.
    for wide in (True, False):
        ctx, pg = (new_page(b, wide=True) if wide else phone_page(b)); pg.goto(BASE)
        pg.evaluate("ids => localStorage.setItem('ballotta.picks', JSON.stringify(Object.fromEntries(ids.map(id => [id, [optionsOf(BYID[id])[0]]]))))", ['c001', 'c071', 'c072'])
        saved_ballot(pg, [1, 70, 71, 72]); pg.wait_for_selector('body.dk-app-on')
        ui = lambda: pg.evaluate('[desk.ph.ui.view, desk.ph.ui.cur]')
        pg.evaluate("desk.ph.go('c070')"); pg.wait_for_timeout(200)
        nxt = (lambda: pg.click('#dk-next')) if wide else (lambda: pg.click('#ph-next'))
        nxt(); pg.wait_for_timeout(200); assert ui() == ['decide', 'c071'], (wide, ui())
        label = pg.inner_text('#dk-next') if wide else pg.inner_text('#ph-next')
        assert 'undecided' not in label.lower(), (wide, 'points back at the contest just left', label)
        pg.evaluate("desk.ph.go('c001')"); assert pg.evaluate("(desk.ph.upNext() || { c: {} }).c.id") == 'c070', (wide, 'another move kept it left')   # Pass 1
        pg.evaluate("desk.ph.go('c070')"); nxt(); pg.wait_for_timeout(200); assert ui() == ['decide', 'c071'], (wide, ui())
        nxt(); pg.wait_for_timeout(200); assert ui() == ['decide', 'c072'], (wide, 'went back', ui())
        nxt(); pg.wait_for_timeout(200); assert ui()[0] == ('glance' if wide else 'crib'), (wide, ui())
        assert pg.evaluate("(desk.ph.upNext() || { c: {} }).c.id") == 'c070', (wide, 'from another view it is named again')
        pg.evaluate("desk.ph.go('c001')"); pg.wait_for_timeout(200)   # Pass 1: any other move forgets it: named again
        label = pg.inner_text('#dk-next') if wide else pg.inner_text('#ph-next')
        assert 'undecided' in label.lower() and pg.evaluate("desk.ph.upNext().c.id") == 'c070', (wide, 'from elsewhere, the contest left undecided is still named', label)
        pg.evaluate("desk.ph.go('c070')"); nxt(); pg.wait_for_timeout(200); assert ui() == ['decide', 'c071'], (wide, ui())   # left again,
        pg.evaluate("() => { window.confirm = () => true; document.querySelector('#dk-menu [data-help=clear]').click(); ['c001', 'c071', 'c072'].forEach(id => pick(id, optionsOf(BYID[id])[0])); }")   # then Clear my picks
        assert pg.evaluate('desk.ph.ui.cur') == 'c071' and pg.evaluate("(desk.ph.upNext() || { c: {} }).c.id") == 'c070', (wide, 'Clear my picks kept it left')
        ctx.close()

@desk_test
def a_long_reason_is_cut_in_the_printout_and_the_glance_table(b):
    # Round-2 audit #28 (#126; Lane): a pasted essay printed page after page on the crib sheet and stretched At a glance.
    # Both show a reason's first 600 characters, then "…", as links already keep; the box keeps every word, and never
    # cuts a character in two.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); saved_ballot(pg, [1, 70, 71]); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate(r"""() => { pick('c070', optionsOf(BYID.c070)[0]); pick('c071', optionsOf(BYID.c071)[0]);
        whys.c070 = 'a'.repeat(599) + '\u{1F600}' + 'b'.repeat(4000); whys.c071 = 'Short and sweet.'; LS.set('ballotta.whys', whys); $('withwhy').checked = true; desk.render(); }""")
    want = 'a' * 599 + '\U0001F600' + '…'
    pg.click('#dk-views [data-view="glance"]')
    shown = pg.evaluate("[...document.querySelectorAll('.dk-wt')].map(e => e.textContent)")
    assert want in shown and 'Short and sweet.' in shown, [x[-5:] for x in shown]
    pg.click('#dk-views [data-view="crib"]')
    crib = pg.evaluate("[...document.querySelectorAll('#dk-paper .why, #crib .why')].map(e => e.textContent)")
    assert crib and all(x in (want, 'Short and sweet.') for x in crib) and want in crib, [x[-5:] for x in crib]
    assert pg.evaluate("whys.c070.length") == 599 + 2 + 4000, 'the reason itself was cut'
    ctx.close()

@desk_test
def clearing_picks_drops_a_reason_waiting_to_be_saved(b):
    # Round-2 audit #12 (#110): "Clear my picks", and loading a Keep link, left a reason typed in the last 150 ms waiting
    # to be saved: if another tab saved meanwhile, the box's old text came back into memory and was saved again.
    # Both now drop it, as Clear everything does.
    for how in ('clear', 'restore'):
        ctx, a = new_page(b, wide=True); a.goto(BASE); saved_ballot(a, [1, 70, 71]); a.wait_for_selector('body.dk-app-on')
        t = ctx.new_page(); t.goto(BASE); t.wait_for_selector('body.dk-app-on')
        a.evaluate("desk.ph.go('c070')"); a.wait_for_selector('#dk-w')
        if how == 'restore':   # a Keep link is waiting to be loaded
            a.evaluate("u => { location.hash = u.split('#')[1]; }", link('k', {'v': 1, 'pr': '300', 'b': [1, 70, 71], 'p': {'71': 0}})); a.wait_for_selector('#d-restore[open]')
        a.evaluate("""h => { window.confirm = () => true; const w = document.getElementById('dk-w'); w.value = 'typed just now'; w.dispatchEvent(new Event('input', { bubbles: true }));
            if (h === 'restore') document.getElementById('restore-go').click(); else clearPicks(); }""", how)
        t.evaluate("pick('c001', optionsOf(BYID.c001)[0])")   # another tab saves inside the 150 ms
        a.wait_for_timeout(600)
        assert not a.evaluate("whys.c070") and 'typed just now' not in (a.evaluate("localStorage.getItem('ballotta.whys')") or ''), (how, 'the cleared reason came back', a.evaluate("whys.c070"))
        ctx.close()

@test
def a_new_share_name_hides_the_link_just_shared(b):
    # #98: right after a share, the link just shared stays on screen; typing a new name means another link, so the old
    # one goes, as it does when the sections change.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); saved_ballot(pg, [1, 70, 71]); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("pick('c070', optionsOf(BYID.c070)[0])")
    pg.evaluate("openShare()"); pg.fill('#sharename', 'Lane'); pg.click('#share-go'); pg.wait_for_selector('#share-out:not(.hidden)')
    pg.type('#sharename', 'y'); pg.wait_for_timeout(200)
    assert not pg.is_visible('#share-out'), 'the old link stayed next to a new name'
    ctx.close()

@test
def hiding_a_friends_picks_keeps_a_waiting_keep_link(b):
    # #130: since #108 a stray close keeps a Keep link waiting; hiding a friend's picks dropped it anyway (it deleted
    # whatever link was stored), so a reload no longer asked. It now drops only the friend's link.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Maya', 'c': 'abcd2349', 'g': 1, 'p': {'70': 0}})); pg.wait_for_function("!!friend", timeout=5000)
    pg.evaluate("u => { location.hash = u.split('#')[1]; }", link('k', {'v': 1, 'pr': '300', 'b': [1, 70], 'p': {'70': 0}})); pg.wait_for_selector('#d-restore[open]')
    pg.keyboard.press('Escape'); pg.wait_for_function("!document.getElementById('d-restore').open")
    pg.evaluate('hideFriend()')
    assert pg.evaluate("(sessionStorage.getItem('ballotta.incoming') || '')[0]") == 'k', 'the waiting Keep link was dropped'
    pg.reload(); pg.wait_for_selector('#d-restore[open]', timeout=5000)
    ctx.close()

@test
def share_names_close_remaining_gaps(b):
    # #43: Unicode's look-alike table (not a hand-made map), flag letters, a stray space next to a single letter,
    # short glued forms and symbol stand-ins. Real names in many scripts still show.
    ctx, pg = new_page(b); pg.goto(BASE)
    sn = lambda n: pg.evaluate('n => safeName(n)', n)
    for bad in ['V oter Guide', 'C ity of Austin', 'G OP', 'GO P', 'RN C', 'TXVOTERS', 'Gօp', 'Ballօtta', 'ᏀOP', 'ᎠNC',
                '🇬🇴🇵', '🇩🇳🇨', '€lection Office', 'Travis ©ounty', 'Travis ¢ounty', 'ᏞWV', 'Ꮩoter guide', 'ℒeague',
                'G O P Texas', 'Travis G O P', 'D N C Team', 'R N C Chair', 'D E M S Austin', 'A D M I N Team', 'g op', 'v oter guide',
                'ꓖꓳꓑ', 'ꓓꓠꓚ Texas',   # Pass 1 (Lisu letters: caseless, so only the table itself maps them)
                'G Oᴘ', 'G Oᴘ Texas', 'V Oᴛᴇʀ Guide', 'R Nᴄ', 'D Nᴄ Team', 'Dn C', 'Go P Texas', 'G Op Texas', 'Бallotta', 'БALLOTTA Team',   # Pass 2
                'V Oꭲꭼꮢ Guide', 'D Eꮇꮪ', 'D Eꮇꮪ Texas', 'D Eмѕ', 'V Oтer Guide', 'G Oᴩ',   # Pass 3
                '9overnment', 'Vote 9OP']:   # #94: 9 reads as g
        assert sn(bad) == '', bad
    assert sn('ϹOUNTY') == 'ΣOUNTY', 'display normalization turns a lunate sigma into Σ: no longer a look-alike'
    for good in ['Mary J Blige', 'J Smith', 'Νίκος', 'Ηλέκτρα', 'Γιώργος', 'Георгий', 'Борис', 'Ольга Петрова', 'Արամ', 'Անի', 'ᏣᎳᎩ',
                 'ანა', 'Ελένη', 'Đặng Thu', 'Nguyễn Văn An', 'محمد', 'דוד', 'Priya', 'Gustavo Terrazas', 'Clerkson', 'DeClerck', 'Le Clerc',
                 'José', 'Dempsey', 'Gopinath', 'Statham', 'Partridge', 'Ivo Terzić', 'A J', 'J R R Tolkien',
                 'S Tate', 'S. Tate', 'P Arty', 'Нильс Бор', 'Ольга Бор', 'Борис Бор']:   # Pass 1, 2
        assert sn(good) == good, good
    ctx.close()


@desk_test
def desk_quick_pick_then_move_keeps_both_announcements(b):
    # #45: a key pick followed quickly by a move is announced together ("…: picked X. Contest 2 of n: …"), not cut off;
    # quick moves alone don't pile up.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.locator('#dk-out .dk-row').first.click(); pg.wait_for_timeout(1200)
    pg.keyboard.press('1'); pg.keyboard.press('n'); pg.wait_for_timeout(400)
    live = pg.text_content('#dk-live')
    assert ': picked ' in live and 'Contest 2 of ' in live and live.index(': picked ') < live.index('Contest 2 of '), live
    pg.wait_for_timeout(1200); pg.keyboard.press('j'); pg.keyboard.press('j'); pg.wait_for_timeout(400)
    live = pg.text_content('#dk-live')
    assert live.startswith('Contest 4 of ') and live.count('Contest ') == 1, live
    pg.keyboard.press('1'); pg.wait_for_timeout(700); pg.keyboard.press('j'); pg.wait_for_timeout(400)   # the pick was already said: not again (Pass 1)
    live = pg.text_content('#dk-live')
    assert live.startswith('Contest 5 of ') and 'picked' not in live, live
    pg.wait_for_timeout(700); pg.keyboard.press('1'); pg.wait_for_timeout(150); pg.keyboard.press('j'); pg.wait_for_timeout(500)   # at typing speed (Pass 2)
    live = pg.text_content('#dk-live'); assert ': picked ' in live and 'Contest 6 of ' in live, live
    pg.wait_for_timeout(700); pg.keyboard.press('1'); pg.keyboard.press('j'); pg.keyboard.press('j'); pg.wait_for_timeout(500)   # two quick moves keep the pick (Pass 2)
    live = pg.text_content('#dk-live'); assert ': picked ' in live and live.count('Contest ') == 1 and 'Contest 8 of ' in live, live
    # Pick, move, pick at typing speed: the first pick is said, and the move describes the contest as it is by then (Pass 3)
    t = lambda i: pg.evaluate(f'cleanTitle(ballot[{i}].c)')
    pg.wait_for_timeout(700); here = pg.evaluate("ballot.findIndex(x => x.c.id === document.getElementById('dk-paper').dataset.c)")
    pg.keyboard.press('1'); pg.wait_for_timeout(120); pg.keyboard.press('j'); pg.wait_for_timeout(120); pg.keyboard.press('1'); pg.wait_for_timeout(600)
    live = pg.text_content('#dk-live')
    assert live.startswith(t(here) + ': picked ') and f'Contest {here + 2} of ' in live and 'No pick yet' not in live, live
    assert live.count(t(here + 1)) == 1, ('the contest moved to is described once', live)   # Pass 4
    ctx.close()

@desk_test
def desk_print_by_touch_and_announced(b):
    # #46: Print… on a touch screen (where a screen reader's double-tap is a touch) also moves focus to the real Print
    # button, and every activation says where it went.
    ctx, pg = new_page(b, wide=True, touch=True); pg.goto(BASE); lookup_wide(pg)
    pg.tap('#dk-print')
    assert pg.evaluate('document.activeElement.dataset.act') == 'print', pg.evaluate('document.activeElement.outerHTML.slice(0, 80)')
    pg.wait_for_timeout(300); assert 'Crib sheet' in pg.text_content('#dk-live'), pg.text_content('#dk-live')
    ctx.close()
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('#dk-print'); pg.wait_for_timeout(300)
    assert 'Crib sheet' in pg.text_content('#dk-live') and pg.evaluate('document.activeElement.dataset.act') != 'print'
    ctx.close()


def backup_card(pg, wide): return pg.locator('#dk-nudge' if wide else '#nudge')


# ---------------------------------------------------------------- phone layout (preview build only until promotion)
import urllib.request, time
PHONE = {'width': 390, 'height': 844}                      # an iPhone 13/14/15's screen in CSS pixels

def phone_page(b, sent=None, csp=False, sw=False, size=None, init=None, ua=None, county=None):
    ctx, pg = new_page(b, sent, csp=csp, touch=True, size=size or PHONE, sw=sw, ua=ua, county=county)
    if init: pg.add_init_script(init)
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.__dict__['errs'] = errs
    return ctx, pg

def lookup_phone(pg):
    pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '78701'); pg.click('#go')
    pg.wait_for_selector('body.dk-app-on', timeout=30000)
    pg.wait_for_function("/ \\d+ decided$/.test(document.getElementById('ph-count').textContent)", timeout=30000)

def h1(pg): return pg.inner_text('#dk-paper h1')
def focused(pg): return pg.evaluate("(() => { const a = document.activeElement; return a ? (a.id || a.tagName) : null; })()")
def sideways(pg): return pg.evaluate('document.scrollingElement.scrollWidth - document.scrollingElement.clientWidth')
def to_contest(pg, title):                                  # through the "Your ballot" sheet, as a voter would
    pg.click('#ph-list'); pg.fill('#dk-q', title); pg.locator('.dk-row', has_text=title).first.click()
    expect(pg.locator('.dk-rail')).to_be_hidden()

@phone_test
def phone_landing_band_form_and_faq(b):
    ctx, pg = phone_page(b); pg.goto(BASE)
    for sel in ('#dk-hdr', '#dk-hero', '#start', '#lookup', '.dk-steps', '#ph-faq', '#dk-help'):
        expect(pg.locator(sel)).to_be_visible()
    for sel in ('.wrap > .brand', '#dk-faq', '#ph-bar', '#dk-share', '.dk-logo', '#dk-loc', '#ph-paste', '#ph-list'):
        expect(pg.locator(sel).first).to_be_hidden()
    assert pg.locator('.wrap > section.card:visible, .wrap > footer:visible').count() == 0, 'About and Feedback live in the menu'
    assert pg.text_content('.dk-tagline') == 'Don’t wait to meet your ballot in the booth.'
    assert css(pg, '#dk-hdr', 'backgroundColor') == PLUM and css(pg, '#dk-hero', 'backgroundColor') == PLUM
    hero, paper = box(pg, '#dk-hero'), box(pg, '#start')
    assert paper['y'] < hero['y'] + hero['height'] - 40, ('the paper overlaps the band', hero, paper)
    qs = pg.locator('#ph-faq details')
    assert qs.count() == pg.locator('#dk-faq .dk-q').count() == 6 and pg.locator('#ph-faq details[open]').count() == 0
    pg.mouse.wheel(0, 3000); pg.wait_for_function("(window.__events || []).some(e => e[0] === 'faq_seen')", timeout=5000)
    assert [e for e in events(pg) if e[0] == 'faq_seen'] == [['faq_seen', {'layout': 'phone'}]]
    qs.nth(3).locator('summary').click()
    assert pg.inner_text('#ph-faq details[open] p') == pg.locator('#dk-faq .dk-q p').nth(3).inner_text()   # the same words
    hb = box(pg, '#dk-help')
    assert hb['width'] >= 44 and hb['height'] >= 44 and pg.get_by_role('button', name='Feedback & Info').count() == 1
    assert sideways(pg) <= 0
    pg.set_viewport_size({'width': 320, 'height': 640}); pg.wait_for_timeout(100)
    assert sideways(pg) <= 0, 'nothing sideways on a 320px phone'
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def phone_lookup_opens_the_app_at_its_top(b):
    ctx, pg = phone_page(b); pg.goto(BASE); pg.evaluate('window.scrollTo(0, 400)'); lookup_phone(pg)
    expect(pg.locator('#ph-bar')).to_be_visible(); expect(pg.locator('.wrap')).to_be_hidden(); expect(pg.locator('.dk-rail')).to_be_hidden()
    assert pg.text_content('#ph-count') == '0 of 63 decided' and pg.text_content('#ph-next') == 'Next undecided →'
    assert h1(pg) == 'United States Senator' and focused(pg) == 'H1' and pg.evaluate('scrollY') == 0
    assert 'Precinct 300 · Saved on this device' in pg.inner_text('#dk-paper .dk-top') and pg.is_hidden('#dk-loc') and pg.is_visible('#dk-share')
    hdr, title, info = box(pg, '#dk-hdr'), box(pg, '#ph-list'), box(pg, '#dk-help')                 # option B (Lane, Oct 16)
    assert title['y'] >= hdr['y'] and title['y'] + title['height'] <= hdr['y'] + hdr['height'] and title['height'] >= 44 and title['x'] < info['x'], (hdr, title, info)
    assert pg.is_hidden('#dk-hdr .dk-brand b') and pg.is_visible('#dk-hdr .dk-brand svg'), 'the mark, not the wordmark, beside the title'
    assert pg.get_by_role('button', name='Your ballot').count() == 1 and pg.get_attribute('#ph-list', 'aria-expanded') == 'false'
    assert 'circle' in css(pg, '#dk-help', 'backgroundImage') and pg.get_by_role('button', name='Feedback & Info').count() == 1, 'Feedback & Info is an (i), not a second menu icon'
    assert pg.text_content('#ph-back') == '← Previous' and pg.is_disabled('#ph-back'), 'nothing before the first contest'
    assert pg.locator('#ph-step, #ph-prev, #ph-step-next').count() == 0 and not pg.locator('#ph-bar svg').count(), 'one Previous, in the bar'
    pg.set_viewport_size({'width': 320, 'height': 640}); pg.wait_for_timeout(100)
    pg.evaluate("document.getElementById('ph-count').textContent = '10 of 63 decided'")   # the widest it gets
    assert pg.evaluate("(() => { const e = document.getElementById('ph-count'); return e.scrollWidth <= e.clientWidth; })()"), 'the title is cut off on a 320px phone'
    for w in (320, 280):                                                                      # 280: a 390px phone at 140% zoom (Pass 1)
        pg.set_viewport_size({'width': w, 'height': 640}); pg.wait_for_timeout(100)
        fit = pg.evaluate("""(() => { const r = (s) => document.querySelector(s).getBoundingClientRect(), fits = (s) => { const e = document.querySelector(s); return e.scrollWidth <= e.clientWidth; };
            return { next: r('#ph-next').right <= innerWidth && fits('#ph-next'), back: fits('#ph-back'), title: r('#ph-list b').height <= 24,
                     inside: r('#ph-list').bottom <= r('#dk-hdr').bottom && r('#ph-list').right <= r('#dk-help').left }; })()""")
        assert all(fit.values()), (w, fit)                                                   # the words, not just the boxes (Pass 2)
    pg.set_viewport_size(PHONE); pg.wait_for_timeout(100)
    sb = box(pg, '#dk-share'); assert sb['width'] >= 44 and pg.get_by_role('button', name='Share my picks').count() == 1
    assert ['ballot_found', {'match': 'exact', 'layout': 'phone'}] in events(pg)
    paper, bar = box(pg, '#dk-paper'), box(pg, '#ph-bar')
    assert abs(bar['y'] + bar['height'] - PHONE['height']) < 1 and paper['x'] >= 8, (paper, bar)
    assert sideways(pg) <= 0 and pg.errs == [], pg.errs
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(150)                # Pass 1: the laptop's paper line
    assert pg.inner_text('#dk-paper .dk-top .note') == 'Saved on this device', ('the laptop shows the precinct in its own header', pg.inner_text('#dk-paper .dk-top .note'))
    pg.set_viewport_size(PHONE); pg.wait_for_timeout(100)
    assert 'Precinct 300 · Saved on this device' in pg.inner_text('#dk-paper .dk-top')
    pg.evaluate('localStorage.setItem("ballotta.ballot", JSON.stringify({ pr: "", b: [70, 71, 1], mode: "saved", at: 0 }))'); pg.reload(); pg.wait_for_selector('body.dk-app-on')
    assert pg.inner_text('#dk-paper .dk-top .note') == 'Saved on this device', ('no precinct, no "Precinct ·" (Pass 1)', pg.inner_text('#dk-paper .dk-top .note'))
    ctx.close()

PERSIST = ("window.__persist = 0; Object.defineProperty(navigator, 'storage', { configurable: true, value: {"
           " persisted: () => Promise.resolve(false), persist: () => { window.__persist++; return Promise.resolve(true); } } });")

@phone_test
def phone_pick_reason_fold_and_steps(b):
    ctx, pg = phone_page(b, init=PERSIST); pg.goto(BASE); lookup_phone(pg)
    to_contest(pg, 'District 9')
    assert h1(pg) == 'City Council Member, District 9' and focused(pg) == 'H1'
    pg.locator('.dk-line', has_text='Qadri').click()
    assert pg.locator('.dk-line', has_text='Qadri').get_attribute('aria-pressed') == 'true' and cur(pg, 'c070') == ['Zohaib “Zo” Qadri']
    pg.wait_for_function("document.getElementById('ph-count').textContent === '1 of 63 decided'")
    pg.fill('#dk-w', 'Knows the district')
    pg.wait_for_function("(JSON.parse(localStorage.getItem('ballotta.whys')) || {}).c070 === 'Knows the district'", timeout=2000)   # saved once typing pauses (#91)
    assert pg.evaluate('window.__persist') == 1, 'the browser is asked to keep the picks at the first one (#49)'
    fold = pg.locator('#ph-fold')
    assert fold.inner_text() == 'About this office · Learn more' and fold.get_attribute('aria-expanded') == 'false'
    expect(pg.locator('#dk-notes')).to_be_hidden()
    fold.click()
    expect(pg.locator('#dk-notes')).to_be_visible(); assert 'One of 10 district council members' in pg.inner_text('#dk-notes')
    assert fold.get_attribute('aria-expanded') == 'true' and not pg.is_visible('.dk-keysec'), 'no keyboard shortcuts on a phone'
    pg.click('#ph-next')                                                                  # the next undecided contest is the next one here
    assert h1(pg) == 'Austin Proposition A' or h1(pg).endswith('Proposition A'), h1(pg)
    assert fold.inner_text() == 'Sources' and fold.get_attribute('aria-expanded') == 'true', 'the fold stays open from contest to contest'
    assert focused(pg) == 'H1'
    pg.click('#ph-back'); assert h1(pg) == 'City Council Member, District 9' and focused(pg) == 'H1'
    to_contest(pg, 'United States Senator')
    assert pg.is_disabled('#ph-back') and pg.get_by_role('button', name='Previous contest').count() == 1
    expect(pg.locator('.dk-nav')).to_be_hidden()
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def phone_next_undecided_then_the_crib_sheet(b):
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
    assert h1(pg) == 'United States Senator' and pg.text_content('#ph-count') == '0 of 3 decided'
    assert focused(pg) == 'BODY', 'a ballot saved on this phone opens without moving focus'
    pg.locator('.dk-line', has_text='Ted Brown').click(); pg.click('#ph-next')
    assert h1(pg) == 'City Council Member, District 9' and focused(pg) == 'H1'
    pg.click('.skip'); pg.click('#ph-next'); assert h1(pg).endswith('Proposition A'), h1(pg)
    pg.locator('.dk-line', has_text='For').first.click()
    pg.wait_for_function("document.getElementById('ph-next').textContent === 'Crib sheet →'")
    pg.click('#ph-back'); assert h1(pg) == 'City Council Member, District 9'
    assert pg.text_content('#ph-next') == 'Next →', ('all decided: step through them in order', pg.text_content('#ph-next'))
    pg.click('#ph-next'); assert h1(pg).endswith('Proposition A') and pg.text_content('#ph-next') == 'Crib sheet →'
    pg.click('#ph-next')
    assert h1(pg) == 'Crib sheet' and pg.is_hidden('#ph-next') and ['view_opened', {'view': 'crib', 'layout': 'phone'}] in events(pg)
    assert pg.text_content('#ph-count') == '3 of 3 decided' and pg.text_content('#ph-back') == '← Contest 3' and not pg.is_disabled('#ph-back')
    assert pg.get_by_role('button', name='Contest 3, go back').count() == 1, 'say where it goes, starting with what it shows (Pass 1, 2)'
    pg.click('#ph-back'); assert h1(pg).endswith('Proposition A') and ['view_opened', {'view': 'decide', 'layout': 'phone'}] in events(pg)
    ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')   # Pass 1
    pg.locator('.dk-line', has_text='Ted Brown').click(); pg.click('#ph-next'); pg.click('#ph-next')                  # 1st decided; on to the 3rd
    pg.locator('.dk-line', has_text='For').first.click(); pg.click('#ph-back'); assert h1(pg) == 'City Council Member, District 9'
    assert pg.text_content('#ph-next') == 'Next →', ('the only undecided contest is this one: Next must still move', pg.text_content('#ph-next'))
    pg.click('#ph-next'); assert h1(pg).endswith('Proposition A'), h1(pg)
    pg.click('#ph-list'); pg.click('#dk-views [data-view="glance"]'); pg.click('#ph-back')                         # Pass 2: from another view
    pg.click('#ph-list'); pg.click('#dk-views [data-view="glance"]'); assert pg.text_content('#ph-next') == 'Next undecided →'
    pg.click('#ph-next'); assert h1(pg) == 'City Council Member, District 9', ('from At a glance, Next goes to the open contest when it is the one left', h1(pg))
    ctx.close()

@phone_test
def phone_ballot_list_sheet(b):
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); to_contest(pg, 'District 9')
    pg.click('#ph-list')
    rail = box(pg, '.dk-rail'); assert rail['x'] == 0 and rail['y'] == 0 and rail['width'] == PHONE['width'] and rail['height'] == PHONE['height'], rail
    assert pg.evaluate("['dk-hdr', 'dk-desk', 'ph-bar'].every(id => document.getElementById(id).inert)"), 'the page behind is out of reach'
    assert pg.evaluate("document.activeElement.getAttribute('aria-current')") == 'true' and 'District 9' in pg.evaluate('document.activeElement.textContent')
    assert pg.get_attribute('#ph-list', 'aria-expanded') == 'true'
    pg.keyboard.press('Escape'); expect(pg.locator('.dk-rail')).to_be_hidden(); assert focused(pg) == 'ph-list'
    assert not pg.evaluate("document.getElementById('dk-desk').inert")
    pg.click('#ph-list'); pg.click('#ph-done'); expect(pg.locator('.dk-rail')).to_be_hidden(); assert focused(pg) == 'ph-list'
    pg.click('#ph-list'); assert pg.input_value('#dk-q') == 'District 9' and pg.locator('.dk-row').count() == 1   # the search stays, as on a laptop
    pg.fill('#dk-q', ''); pg.click('#dk-filt [data-f="und"]'); expect(pg.locator('.dk-rail')).to_be_visible()
    assert pg.locator('.dk-row').count() == 63
    pg.click('#dk-keep'); pg.wait_for_selector('#d-keep[open]'); pg.click('#d-keep [data-close]'); expect(pg.locator('.dk-rail')).to_be_visible()
    pg.click('#dk-views [data-view="glance"]'); expect(pg.locator('.dk-rail')).to_be_hidden()
    assert h1(pg) == 'Your whole ballot' and focused(pg) == 'H1' and ['view_opened', {'view': 'glance', 'layout': 'phone'}] in events(pg)
    assert pg.text_content('#ph-count') == '0 of 63 decided' and pg.text_content('#ph-back').startswith('← Contest '), pg.text_content('#ph-count')
    pg.click('#ph-list'); pg.click('#dk-print'); expect(pg.locator('.dk-rail')).to_be_hidden()
    assert h1(pg) == 'Crib sheet' and pg.evaluate('document.activeElement.dataset.act') == 'print'
    ctx.close()

@phone_test
def phone_glance_vote_and_crib_fit_the_screen(b):
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg)
    pg.click('#ph-list'); pg.click('#dk-views [data-view="glance"]')
    assert css(pg, '[data-sel="c006"]', 'fontSize') == '16px' and css(pg, '#dk-q', 'fontSize') == '16px', 'iPhones zoom into smaller fields'
    pg.locator('[data-sel="c006"]').select_option(index=1); assert cur(pg, 'c006') == [pg.evaluate("optionsOf(BYID.c006)[0]")]
    pg.evaluate('window.scrollTo(0, 2000)'); pg.locator('[data-go="c070"]').first.click()
    assert h1(pg) == 'City Council Member, District 9' and pg.evaluate('scrollY') == 0 and focused(pg) == 'H1', 'a name in At a glance opens its contest at the top'
    pg.click('#ph-list'); pg.click('#dk-views [data-view="glance"]')
    expect(pg.locator('.dk-tbl thead')).to_be_hidden(); expect(pg.locator('.dk-tbl td:nth-child(4)').first).to_be_hidden()
    assert sideways(pg) <= 0
    pg.click('#ph-list'); pg.click('#dk-views [data-view="vote"]')
    assert pg.locator('.dk-site').count() == 5 and pg.locator('.ph-mapfold:not([open])').count() == 1
    expect(pg.locator('#dk-map')).to_be_hidden(); pg.click('.ph-mapfold summary'); expect(pg.locator('#dk-map')).to_be_visible()
    pg.click('[data-period="eday"]'); assert pg.locator('.ph-mapfold').count() == 1, 'redrawn: one fold, never two'
    assert pg.locator('.ph-mapfold[open]').count() == 1 and pg.locator('#dk-map').is_visible(), 'redrawn: the fold stays open (#76)'
    assert sideways(pg) <= 0
    pg.click('#ph-list'); pg.click('#dk-views [data-view="crib"]')
    for t in ('#dk-cw', '#dk-c2', '#dk-cu'): expect(pg.locator(t)).to_be_visible()
    pg.click('#dk-c2'); pg.click('#dk-cu'); assert pg.get_attribute('#dk-page', 'class') == 'dk-page two'
    pg.evaluate("() => { window.print = () => { window.__printed = (window.__printed || 0) + 1; }; }")
    pg.click('#dk-notes [data-act="print"]')
    assert pg.evaluate('window.__printed') == 1 and events(pg)[-1] == ['crib_printed', {'two_col': 'yes', 'hide_unopposed': 'yes', 'layout': 'phone'}], events(pg)[-1]
    pg.emulate_media(media='print')                                                  # what the printer gets: the crib sheet alone
    assert pg.is_visible('#crib') and 'two' in pg.get_attribute('#crib', 'class') and not pg.is_visible('#dk-app') and not pg.is_visible('#ph-bar') and not pg.is_visible('#dk-hdr')
    pg.emulate_media(media='screen')
    pg.set_viewport_size({'width': 320, 'height': 640}); pg.wait_for_timeout(100); assert sideways(pg) <= 0
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(100); assert pg.is_checked('#dk-c2') and pg.is_checked('#dk-cu')
    pg.set_viewport_size(PHONE); pg.wait_for_timeout(100)
    assert pg.is_checked('#dk-c2') and pg.is_checked('#dk-cu') and 'two' in pg.get_attribute('#crib', 'class'), 'print options survive a narrower window: a phone shows them now'
    ctx.close()

@phone_test
def phone_menu_is_a_sheet(b):
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg)
    assert pg.get_attribute('#dk-help', 'aria-haspopup') == 'dialog' and pg.get_attribute('#dk-help', 'aria-controls') is None
    pg.click('#dk-help'); pg.wait_for_selector('#ph-menu[open]'); expect(pg.locator('#dk-menu')).to_be_hidden()
    got = pg.locator('#ph-mitems button b').all_inner_texts(); want = pg.locator('#dk-menu button b').all_text_contents()   # the laptop menu's own items
    k = want.index('Change address') + 1                                                         # the phone adds Home Screen after Change address
    assert got == want[:k] + ['Add to your Home Screen'] + want[k:] and pg.locator('#ph-mitems hr').count() == 1, (got, want)
    pg.locator('#ph-mitems button', has_text='How your privacy works').click()
    pg.wait_for_selector('#d-info[open]'); assert not pg.evaluate("document.getElementById('ph-menu').open")
    assert ['help_opened', {'item': 'privacy', 'layout': 'phone'}] in events(pg)
    pg.click('#d-info [data-close]')
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Change address').click()
    expect(pg.locator('#start')).to_be_visible(); expect(pg.locator('#dk-back')).to_be_visible(); expect(pg.locator('#ph-bar')).to_be_hidden()
    pg.click('#dk-back'); expect(pg.locator('#ph-bar')).to_be_visible()
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(100)
    assert pg.get_attribute('#dk-help', 'aria-haspopup') == 'menu'
    pg.click('#dk-help'); expect(pg.locator('#dk-menu')).to_be_visible(); assert not pg.evaluate("document.getElementById('ph-menu').open")
    ctx.close()

@phone_test
def phone_friend_link_landing_then_inline(b):
    o = {'v': 1, 'n': 'Maya', 'c': 'abcd1234', 'g': 1, 'p': {'70': 2, '71': 0}, 'w': {'70': 'Knows the district.'}}
    ctx, pg = phone_page(b); pg.goto(BASE); fresh_goto(pg, link('s', o))
    expect(pg.locator('#friend')).to_be_visible(); assert 'Maya shared 2 picks' in pg.inner_text('#friend')
    expect(pg.locator('#f-own')).to_be_hidden(); expect(pg.locator('#f-cmp')).to_be_hidden()
    expect(pg.locator('.dk-fcta')).to_be_visible(); assert 'See Maya’s picks beside yours' in pg.inner_text('.dk-fcta')
    assert box(pg, '#friend')['y'] < box(pg, '#start')['y'], 'their picks first, then the form'
    lookup_phone(pg); to_contest(pg, 'District 9')
    expect(pg.locator('.dk-fchip')).to_be_visible(); assert 'Maya picked this' in pg.inner_text('.dk-fp')
    assert pg.inner_text('#ph-fold').startswith('You and Maya · ')
    assert [e for e in events(pg) if e[0] == 'share_compare'] == [['share_compare', {'layout': 'phone'}]], events(pg)
    pg.click('#ph-next'); assert [e for e in events(pg) if e[0] == 'share_compare'] == [['share_compare', {'layout': 'phone'}]], 'once'
    pg.locator('.dk-fchip [data-act="hidefriend"]').click(); expect(pg.locator('.dk-fchip')).to_be_hidden()
    assert not pg.inner_text('#ph-fold').startswith('You and')
    ctx.close()

@phone_test
def phone_backup_card_sits_above_the_bar(b):
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, list(range(1, 41))); pg.wait_for_selector('body.dk-app-on')
    ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:5])
    card = pg.locator('#dk-nudge'); expect(card).to_be_visible(); expect(pg.locator('#ph-home-nudge')).to_be_hidden()
    c, bar = box(pg, '#dk-nudge'), box(pg, '#ph-bar'); assert c['y'] + c['height'] <= bar['y'], ('the card covers the bar', c, bar)
    card.locator('[data-nudge="dismiss"]').click(); expect(card).to_be_hidden()
    assert focused(pg) in ('dk-paper',) or pg.evaluate("document.activeElement.closest('#dk-paper') !== null"), focused(pg)
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[5:25])
    expect(card).to_be_visible(); expect(pg.locator('#ph-home-nudge')).to_be_visible()
    pg.click('#ph-home-nudge'); pg.wait_for_selector('#ph-install[open]'); expect(card).to_be_hidden()
    ev = events(pg)
    assert ['backup_nudge', {'at': '25', 'action': 'home', 'layout': 'phone'}] in ev and ['home_screen', {'action': 'opened', 'from': 'card', 'layout': 'phone'}] in ev, ev
    assert pg.evaluate('window.ballottaDropped') == []
    ctx.close()

IPHONE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
CHROME_IOS_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/129.0.6668.69 Mobile/15E148 Safari/604.1'
FIREFOX_IOS_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/131.0 Mobile/15E148 Safari/605.1.15'
IPAD_UA = 'Mozilla/5.0 (iPad; CPU OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
INSTAGRAM_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 350.0.0.32.104 (iPhone14,5; iOS 18_0; en_US; en; scale=3.00; 1170x2532; 640245296)'
FACEBOOK_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 [FBAN/FBIOS;FBAV/480.0.0.40.104;FBBV/650000000;FBDV/iPhone14,5;FBMD/iPhone;FBSN/iOS;FBSV/18.0;FBSS/3;FBLC/en_US;FBOP/5]'
OPERA_IOS_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1 OPX/2.1.0'
GOOGLE_APP_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) GSA/340.0.689177329 Mobile/15E148 Safari/604.1'
FAKE_BIP = ("() => { const e = new Event('beforeinstallprompt', { cancelable: true }); e.prompt = () => { window.__prompted = (window.__prompted || 0) + 1; return Promise.resolve(); };"
            " e.userChoice = Promise.resolve({ outcome: 'accepted' }); window.dispatchEvent(e); }")

@phone_test
def phone_add_to_home_screen_three_ways(b):
    # Android (the browser's own prompt), iPhone (steps, and a copy of the picks to carry over), anything else (where to look).
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pg.evaluate(FAKE_BIP)
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click(); pg.wait_for_selector('#ph-install[open]')
    expect(pg.locator('#ph-i-add')).to_be_visible(); expect(pg.locator('#ph-i-ios')).to_be_hidden(); expect(pg.locator('#ph-i-other')).to_be_hidden()
    pg.click('#ph-i-add'); pg.wait_for_function("!document.getElementById('ph-install').open")
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click()
    expect(pg.locator('#ph-i-other')).to_be_visible(); expect(pg.locator('#ph-i-add')).to_be_hidden()   # the prompt is used up, nothing installed yet: say where to look
    pg.click('#ph-install [data-close]')
    pg.evaluate("window.dispatchEvent(new Event('appinstalled'))")
    assert pg.evaluate('window.__prompted') == 1
    hs = [e[1] for e in events(pg) if e[0] == 'home_screen']
    assert hs == [{'action': 'opened', 'from': 'menu', 'layout': 'phone'}, {'action': 'prompted', 'layout': 'phone'}, {'action': 'opened', 'from': 'menu', 'layout': 'phone'}, {'action': 'added', 'layout': 'phone'}], hs
    pg.click('#dk-help'); assert 'Add to your Home Screen' not in pg.inner_text('#ph-mitems'), 'installed: no longer offered (#76)'
    ctx.close()
    ctx, pg = phone_page(b, ua=IPHONE_UA); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click()
    expect(pg.locator('#ph-i-carry')).to_be_hidden(), 'no picks yet: nothing to carry'
    pg.click('#ph-install [data-close]'); pg.locator('.dk-line').first.click()
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click()
    expect(pg.locator('#ph-i-ios')).to_be_visible(); expect(pg.locator('#ph-i-carry')).to_be_visible(); expect(pg.locator('#ph-i-add')).to_be_hidden()
    pg.click('#ph-i-copy'); pg.wait_for_function("(window.__events || []).some(e => e[0] === 'keep_created')")
    clip = pg.evaluate('navigator.clipboard.readText()')
    assert re.fullmatch(re.escape(BASE) + r'#k2[A-Za-z0-9_-]{16,}', clip), clip
    assert ['home_screen', {'action': 'copied', 'layout': 'phone'}] in events(pg) and ['keep_created', {'via': 'copy', 'layout': 'phone'}] in events(pg)
    ctx.close()

STANDALONE = "Object.defineProperty(navigator, 'standalone', { configurable: true, get: () => true });"

@phone_test
def a_page_left_open_learns_of_a_newer_release(b):
    # Round-2 audit #7 (#105): a Home Screen app resumed, or a tab left open, never reloads by itself, so it kept a fixed
    # page forever. When it comes back into view, or every 10 minutes while in view (never more often), it asks for
    # version.json past every cache; a newer release brings the bar "A newer Ballotta is available." with Reload (Lane's
    # words). It never reloads by itself. The same release, an older one (a kept copy), or no answer bring nothing.
    import datetime as dt
    for wide in (False, True):
        for live, want in (('9.9.9', True), (None, False), ('0.0.1', False), ('fail', False)):
            ctx, pg = (new_page(b, wide=True) if wide else phone_page(b))
            hits = []
            def answer(route, _req=None, live=live):   # Playwright passes (route, request) to a two-argument handler
                hits.append(route.request.url)
                if live == 'fail': return route.abort()
                v = live or json.loads((ROOT / 'version.json').read_text())['version']
                route.fulfill(status=200, content_type='application/json', body=json.dumps({'version': v}))
            ctx.route('**/version.json*', answer)
            pg.clock.install(time=dt.datetime(2026, 10, 20, 12, 0)); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
            pg.evaluate("window.__stay = 1; document.dispatchEvent(new Event('visibilitychange')); window.dispatchEvent(new Event('focus'))")
            pg.clock.run_for(2000)
            assert hits == [], (wide, live, 'asked again within 10 minutes of loading', hits)
            pg.evaluate("Object.defineProperty(document, 'visibilityState', { configurable: true, get: () => 'hidden' })")   # out of view: never asks
            pg.clock.run_for(10 * 60 * 1000 + 1000); pg.wait_for_timeout(200)
            assert hits == [], (wide, live, 'asked while out of view', hits)
            pg.evaluate("delete document.visibilityState; document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(300)   # back in view
            assert len(hits) == 1 and re.search(r'^https?://[^/]+/version\.json\?\d+$', hits[0]), (wide, live, hits)   # past every cache
            bar = pg.evaluate("(() => { const p = document.getElementById('ph-saved'); return [p.classList.contains('hidden'), p.querySelector('b').textContent, document.getElementById('ph-saved-go').textContent, p.getClientRects().length > 0]; })()")
            if want: assert bar == [False, 'A newer Ballotta is available.', 'Reload', True], (wide, live, bar)
            else: assert bar[0], (wide, live, 'the bar showed', bar)
            pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); pg.clock.run_for(2000)
            assert len(hits) == 1, (wide, live, 'asked again within 10 minutes', hits)
            assert pg.evaluate('window.__stay') == 1, 'the page reloaded by itself'
            if not want:   # still in view: asked again every 10 minutes, with no event at all
                pg.clock.run_for(11 * 60 * 1000)
                for _ in range(30):
                    if len(hits) >= 2: break
                    pg.wait_for_timeout(100)
                assert len(hits) == 2, (wide, live, 'not asked again while in view', hits)
            if want:
                pg.clock.run_for(30 * 60 * 1000)
                assert len(hits) == 1, (wide, 'kept asking after it knew', hits)
                with pg.expect_navigation(): pg.click('#ph-saved-go')
                assert pg.evaluate('window.__stay') is None, 'Reload did not reload'
            ctx.close()

@phone_test
def phone_print_in_a_home_screen_app_says_how(b):
    # Round-2 audit #6: Print does nothing in an iPhone Home Screen app (Lane tried it on his iPhone, Oct 18; Safari
    # prints). There the note under Print says how to print from Safari, and a tap on Print turns it into a warning, on
    # screen where the voter tapped (not under the bottom bar; an iPad in landscape too: Pass 2) and said by a screen
    # reader, and never calls print. Safari on the same iPhone, and a Home Screen app elsewhere (Android's prints), are unchanged.
    NO = 'Printing doesn’t work in a Home Screen app. To print, tap Keep my picks, then Copy link, and open the link in Safari. Print from there.'
    IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15'
    for init, ua, home, size in ((STANDALONE, IPHONE_UA, True, None), (STANDALONE, IPHONE_UA, True, {'width': 320, 'height': 568}),
                                 (STANDALONE + "Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 }); Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });", IPAD, True, {'width': 1180, 'height': 820}),
                                 (None, IPHONE_UA, False, None), (STANDALONE, None, False, None)):
        ctx, pg = phone_page(b, init=init, ua=ua, size=size); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
        pg.evaluate('() => { window.__printed = 0; window.print = () => { window.__printed++; }; }')
        if size and size['width'] >= 1024: pg.click('#dk-views [data-view="crib"]')
        else: pa_view(pg, 'crib')
        note = pg.inner_text('#dk-notes [data-act="print"] + .note')
        assert (note == NO) == home, (init, ua, size, note)
        assert (pg.get_attribute('#dk-notes [data-act="print"] + .note', 'role') == 'status') == home, 'a screen reader isn\'t told'
        assert pg.evaluate("document.getElementById('noprint').textContent") == (NO if home else ''), 'the plain layout\'s note'
        pg.evaluate("""() => { window.__texts = []; const n = document.querySelector('#dk-notes [data-act="print"] + *');
            new MutationObserver(() => window.__texts.push(n.textContent)).observe(n, { childList: true, characterData: true, subtree: true }); }""")
        for tap in (1, 2):   # Pass 3: the second tap too (the first one's class change hid the note from the next)
            pg.evaluate("document.querySelector('#dk-notes [data-act=\"print\"]').scrollIntoView({ block: 'end' })")   # the button at the screen's bottom edge, as a tap leaves it
            pg.evaluate("window.__texts.length = 0; document.querySelector('#dk-notes [data-act=\"print\"]').click()"); pg.wait_for_timeout(400)
            assert pg.evaluate('__printed') == (0 if home else tap), (init, ua, size, tap, 'print was called' if home else 'print was not called')
            said = pg.evaluate("""(() => { const n = document.querySelector('#dk-notes [data-act="print"] + *'), r = n.getBoundingClientRect();
                const seen = r.top >= 0 && r.bottom <= innerHeight && [0.1, 0.5, 0.9].every(f => n.contains(document.elementFromPoint(r.left + r.width / 2, r.top + r.height * f)));
                return [n.className, n.textContent, seen]; })()""")
            assert (said[0] == 'status warn' and said[1] == NO and said[2]) == home, (init, ua, size, tap, 'a tap says nothing where the voter can see it', said)
            if home: assert pg.evaluate('__texts') == ['', NO], (tap, 'the warning isn\'t set anew, so a screen reader may say nothing', pg.evaluate('__texts'))
        assert NO not in pg.inner_text('#lookupmsg'), 'the address form keeps the print message (Pass 1)'
        assert (names(pg)[-1:] == ['crib_printed']) != home, names(pg)[-3:]
        ctx.close()

@phone_test
def an_ipad_home_screen_app_held_sideways_can_paste_picks(b):
    # Round-2 audit #14 (#112): an iPad's Home Screen app held sideways (1024px or wider) gets the laptop layout, whose
    # menu had no "Paste my picks link", and a Home Screen app can't open a link: its picks from Safari couldn't come in.
    IPAD = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15'
    TOUCH = "Object.defineProperty(navigator, 'maxTouchPoints', { get: () => 5 }); Object.defineProperty(navigator, 'platform', { get: () => 'MacIntel' });"
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("pick('c070', optionsOf(BYID.c070)[0])"); keep = pg.evaluate('keepURL()'); ctx.close()
    for init, want in ((STANDALONE + TOUCH, True), (TOUCH, False), (STANDALONE, False)):   # an iPad app; iPad Safari; a Mac app
        ctx, pg = phone_page(b, init=init, ua=IPAD, size={'width': 1180, 'height': 820}); pg.goto(BASE)
        pg.evaluate("localStorage.setItem('ballotta.ballot', JSON.stringify({ pr: '300', b: [1, 70, 71], mode: 'saved', at: 0, pt: null }))"); pg.reload(); pg.wait_for_selector('body.dk-app-on')
        pg.click('#dk-help'); items = pg.inner_text('#dk-menu')
        assert ('Paste my picks link' in items) == want, (init, items)
        assert pg.evaluate("[...document.querySelectorAll('#ph-mitems button')].filter(b => b.textContent.includes('Paste my picks link')).length") == (1 if want else 0), 'the phone sheet lists it once'
        assert 'undefined' not in pg.evaluate("[...document.querySelectorAll('#ph-mitems button')].map(b => b.dataset.ph).join()")
        if want:
            pg.click('#dk-menu >> text=Paste my picks link'); pg.wait_for_selector('#ph-paste-d[open]')
            assert pg.evaluate("document.getElementById('dk-menu').classList.contains('hidden')"), 'the menu stayed open'
            pg.click('#ph-paste-d [data-close]'); pg.wait_for_function("!document.getElementById('ph-paste-d').open")
            assert pg.evaluate('document.activeElement.id') == 'dk-help', ('focus lost when the sheet closed', pg.evaluate('document.activeElement.outerHTML.slice(0, 80)'))
            pg.click('#dk-help'); pg.click('#dk-menu >> text=Paste my picks link'); pg.wait_for_selector('#ph-paste-d[open]')
            pg.fill('#ph-p-in', keep); pg.click('#ph-p-go'); pg.wait_for_selector('#d-restore[open]')
            pg.click('#restore-go'); pg.wait_for_function("current('c070').length === 1")
        ctx.close()

@phone_test
def copy_my_picks_link_for_the_home_screen_always_opens_there(b):
    # #129 (round-2 wave 1 audit, F1 and F3): the Add to Home Screen steps' "Copy my picks link" copied a link too long for
    # the Home Screen app to open when the reasons were long, and silently left the reasons out if "Leave my reasons out"
    # was pressed earlier in the Keep sheet. It now copies picks and reasons; when that link is too long, the picks only,
    # and says so (Lane's words).
    LONG = """() => { ballot.forEach((x, i) => { const o = optionsOf(x.c); if (o.length) pick(x.c.id, o[0]);
        whys[x.c.id] = Array.from({ length: 600 }, (_, k) => String.fromCodePoint(0x4E00 + ((i * 600 + k) * 7919) % 20000)).join(''); }); }"""
    for long_ in (False, True):
        ctx, pg = phone_page(b, ua=IPHONE_UA); pg.goto(BASE); saved_ballot(pg, list(range(1, 73))); pg.wait_for_selector('body.dk-app-on')
        if long_: pg.evaluate(LONG)
        else: pg.evaluate("() => { pick('c070', optionsOf(BYID.c070)[0]); whys.c070 = 'A short reason.'; keepNoWhy = true; }")   # as if left out in the Keep sheet before
        pa_menu(pg, 'Add to your Home Screen'); pg.wait_for_selector('#ph-install[open]')
        pg.click('#ph-i-copy'); pg.wait_for_function("(window.__events || []).some(e => e[0] === 'keep_created')", timeout=20000)
        clip = pg.evaluate('navigator.clipboard.readText()')
        o = pg.evaluate("f => unpackFrag(f)", clip.split('#', 1)[1])
        assert o and o != 'too old' and pg.evaluate('u => !keepTooLong(u)', clip), (long_, 'the copied link would not open', len(clip))
        assert bool(o.get('w')) != long_, (long_, 'reasons', bool(o.get('w')))
        assert len(o['p']) == pg.evaluate("ballot.filter(x => current(x.c.id).length).length"), 'every pick is in it'
        ok = pg.inner_text('#ph-i-ok')
        assert ok == ('✓ Copied (picks only: your reasons made the link too long)' if long_ else '✓ Copied'), (long_, ok)
        if long_:   # Pass 1: the clipboard refused, the link shown to copy by hand: it says so too
            pg.evaluate("() => { navigator.clipboard.writeText = () => Promise.reject(new Error('refused')); }")
            pg.click('#ph-install [data-close]'); pa_menu(pg, 'Add to your Home Screen'); pg.wait_for_selector('#ph-install[open]')
            pg.click('#ph-i-copy'); pg.wait_for_selector('#ph-i-out:not(.hidden)')
            shown = pg.inner_text('#ph-i-out'); o2 = pg.evaluate("f => unpackFrag(f)", shown.strip().split('#', 1)[1])
            assert not o2.get('w') and pg.is_visible('#ph-i-ok') and pg.inner_text('#ph-i-ok') == 'Picks only: your reasons made the link too long', pg.inner_text('#ph-i-ok')
        ctx.close()

@phone_test
def phone_home_screen_app_pastes_picks(b):
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("pick('c070', 'Zohaib “Zo” Qadri'); whys.c070 = 'Knows the district'; LS.set('ballotta.whys', whys)")
    keep = pg.evaluate('keepURL()'); share = pg.evaluate("packFrag('s', { v: 1, n: 'Maya', p: { '70': 1 } })")
    ctx.close()
    ctx, pg = phone_page(b, init=STANDALONE); pg.goto(BASE)                                # Android's Home Screen app shares Chrome's storage
    expect(pg.locator('#ph-paste')).to_be_hidden(); pg.click('#dk-help'); t = pg.inner_text('#ph-mitems')
    assert 'Paste my picks link' not in t and 'Add to your Home Screen' not in t, t
    ctx.close()
    ctx, pg = phone_page(b, init=STANDALONE, ua=IPHONE_UA); pg.goto(BASE)
    expect(pg.locator('#ph-paste')).to_be_visible(); assert 'Copy my picks link' in pg.inner_text('#ph-paste'), pg.inner_text('#ph-paste')
    pg.click('#dk-help'); t = pg.inner_text('#ph-mitems')
    assert 'Paste my picks link' in t and 'Add to your Home Screen' not in t, t
    pg.click('#ph-menu [data-close]'); pg.click('#ph-paste-open'); pg.wait_for_selector('#ph-paste-d[open]')
    pg.fill('#ph-p-in', 'hello'); pg.click('#ph-p-go'); assert 'doesn’t look like a Ballotta link' in pg.inner_text('#ph-p-msg')
    assert 'not the Share my picks link' in pg.inner_text('#ph-paste-d .lead'), pg.inner_text('#ph-paste-d .lead')
    pg.fill('#ph-p-in', BASE + '#' + share); pg.click('#ph-p-go'); assert 'Share my picks link, for friends' in pg.inner_text('#ph-p-msg'), pg.inner_text('#ph-p-msg')
    pg.fill('#ph-p-in', 'My picks: ' + keep + '.'); pg.click('#ph-p-go')               # extra words around it, as in a note
    pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go'); pg.wait_for_selector('body.dk-app-on')
    assert cur(pg, 'c070') == ['Zohaib “Zo” Qadri'] and pg.evaluate('whys.c070') == 'Knows the district'
    ev = events(pg)
    assert ['home_screen', {'action': 'pasted', 'layout': 'phone', 'app': 'yes'}] in ev and ['keep_restored', {'layout': 'phone', 'app': 'yes'}] in ev, ev
    expect(pg.locator('#ph-paste')).to_be_hidden()
    assert pg.evaluate('window.ballottaDropped') == []
    ctx.close()
    ctx, pg = phone_page(b, init=STANDALONE, ua=IPHONE_UA); pg.goto(BASE)                 # straight from the clipboard
    pg.evaluate("navigator.clipboard.writeText('my bank PIN is 1234')"); pg.click('#ph-paste-open'); pg.click('#ph-p-clip')
    pg.wait_for_selector('#ph-p-msg:not(.hidden)')                                     # the clipboard is read in the background
    assert pg.input_value('#ph-p-in') == '' and 'doesn’t look like a Ballotta link' in pg.inner_text('#ph-p-msg'), 'other clipboard text is never shown'
    pg.evaluate('u => navigator.clipboard.writeText(u)', keep)
    pg.click('#ph-p-clip'); pg.wait_for_selector('#d-restore[open]')
    ctx.close()

class Flip(http.server.SimpleHTTPRequestHandler):           # the repo's files, except any path in swap (served as given) or gone (404)
    swap, gone, fail, hits, slow, gzip = {}, set(), {}, [], {}, False   # fail: path -> a status to answer instead (503, say); hits: paths asked for; slow: path -> seconds; gzip: pages sent gzipped, as GitHub Pages does
    moved, stall = {}, {}   # moved: path -> where a 301 sends it; stall: path -> seconds to hang after sending half the page (#54)
    def log_message(self, *a): pass
    def do_HEAD(self):                                       # the saved-copy bar's check that the site answers again (#73)
        p = self.path.split('?')[0]
        Flip.hits.append('HEAD ' + p)
        if p in Flip.slow: time.sleep(Flip.slow[p])
        if p in Flip.gone or p in Flip.fail: self.send_response(404 if p in Flip.gone else Flip.fail[p]); self.end_headers(); return
        return super().do_HEAD()
    def do_GET(self):
        Flip.hits.append(self.path.split('?')[0])
        if self.path.split('?')[0] in Flip.slow: time.sleep(Flip.slow[self.path.split('?')[0]])
        if self.path.split('?')[0] in Flip.gone: return self.send_error(404)
        if self.path.split('?')[0] in Flip.fail: return self.send_error(Flip.fail[self.path.split('?')[0]])
        if self.path.split('?')[0] in Flip.moved:
            self.send_response(301); self.send_header('Location', Flip.moved[self.path.split('?')[0]]); self.send_header('Content-Length', '0'); self.end_headers(); return
        if self.path.split('?')[0] in Flip.stall:
            body = Flip.swap.get(self.path.split('?')[0]) or (ROOT / self.path.split('?')[0].lstrip('/')).read_bytes()
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(body))); self.end_headers()
            self.wfile.write(body[:len(body) // 2]); self.wfile.flush(); time.sleep(Flip.stall[self.path.split('?')[0]]); return
        body = Flip.swap.get(self.path.split('?')[0])
        if body is None and Flip.gzip and self.path.split('?')[0].endswith('.html'):
            import gzip as gz; body = gz.compress((ROOT / self.path.split('?')[0].lstrip('/')).read_bytes())
            self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Encoding', 'gzip'); self.send_header('Content-Length', str(len(body)))
            self.end_headers(); self.wfile.write(body); return
        if body is None: return super().do_GET()
        self.send_response(200); self.send_header('Content-Type', 'application/javascript' if self.path.endswith('.js') else 'image/png' if self.path.endswith('.png') else 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)

def own_server():                                           # a spare port of the system's choosing, never 8765
    s = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Flip, directory=str(ROOT)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f'http://127.0.0.1:{s.server_address[1]}/{PAGE}'

@phone_test
def a_share_link_opens_from_the_offline_copy(b):
    # 1.2.0, Pass 1: share links go to picks/, which the offline copy kept only once a share link had been opened online.
    # A phone with the copy, in line with no signal, opening its first share link got the browser's own error, where a
    # 1.1.7 link (to the page itself) opened from the copy. The copy now keeps picks/ from the start, as it does the page.
    if PAGE.startswith('next/'):                                         # a share link goes to the main site's picks/, which only
        return print('  (not on the preview: share links open on the main site)')   # the main page's offline copy keeps (Oct 19)
    Flip.swap, Flip.gone, Flip.fail, Flip.slow, Flip.gzip = {}, set(), {}, {}, False; srv, url = own_server()
    site = url.rsplit('/', 1)[0]
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); saved_ballot(pg, [1, 70, 71]); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("pick('c070', optionsOf(BYID.c070)[0])")
    pg.evaluate("openShare()"); pg.fill('#sharename', 'Lane'); pg.click('#share-go'); pg.wait_for_selector('#share-out:not(.hidden)')
    frag = pg.evaluate('sharePrep.url').split('#', 1)[1]; ctx.close()
    ctx, pg = phone_page(b, sw=True)
    try:
        pg.goto(url); poll(pg, '!!navigator.serviceWorker.controller', 15); pg.reload(); poll(pg, "document.readyState === 'complete'")
        pg.wait_for_timeout(1500)                                            # the install's own fetches settle
        Flip.fail = {'/picks/': 503, '/': 503, '/' + PAGE: 503}                 # no answer from the site, as with no signal
        pg.goto('about:blank'); pg.goto(site + '/picks/#' + frag)
        poll(pg, '!!window.friend', 10)
        assert pg.evaluate('friend.name') == 'Lane' and pg.get_attribute('html', 'data-copy') == 'error', (pg.url, pg.get_attribute('html', 'data-copy'))
    finally:
        Flip.fail = {}; ctx.close(); srv.shutdown()

@phone_test
def phone_offline_copy_after_one_visit(b):
    # Network first (Lane): online, a changed page shows at once; the page, its fonts and icons are kept; with the server
    # gone (the offline copy's own network included), the kept copy opens. The page's CSP stays on throughout.
    Flip.swap, Flip.gone = {}, set(); srv, url = own_server(); up = True
    ctx, pg = phone_page(b, csp=True, sw=True); pg.add_init_script(CSP_WATCH)
    try:
        pg.goto(url.rsplit('/', 1)[0] + '/manifest.webmanifest')                           # same site, before any copy exists
        pg.evaluate("u => caches.open('aaa-other').then(c => c.put(u, new Response('<h1>Not ours</h1>', { headers: { 'Content-Type': 'text/html' } })))", url)
        pg.goto(url)
        assert pg.evaluate('Promise.race([navigator.serviceWorker.ready.then(() => true), new Promise(ok => setTimeout(ok, 15000, false))])'), 'no offline copy installed'
        poll(pg, '!!navigator.serviceWorker.controller', 15)                             # and in charge of this page
        meta = pg.get_attribute('meta[http-equiv="Content-Security-Policy"]', 'content')
        assert "manifest-src 'self'" in meta and "worker-src 'self'" in meta, meta
        scope = pg.evaluate("navigator.serviceWorker.getRegistration().then(r => r && r.scope)")
        assert scope == url.rsplit('/', 1)[0] + '/', scope
        murl = pg.evaluate("document.querySelector('link[rel=manifest]').href")    # read from here: the page itself may only fetch from the county
        m = json.loads(urllib.request.urlopen(murl).read())
        assert m['display'] == 'standalone' and m['start_url'] == './' and {i['purpose'] for i in m['icons']} == {'any', 'maskable'}, m
        for i in m['icons']:
            r = urllib.request.urlopen(urllib.parse.urljoin(murl, i['src'])); assert r.headers['Content-Type'] == 'image/png' and r.read(8) == b'\x89PNG\r\n\x1a\n', i
        pg.reload(); poll(pg, "document.fonts.status === 'loaded'")
        Flip.swap['/' + PAGE] = (ROOT / PAGE).read_bytes().replace(b"<h1>What's on your ballot?</h1>", b"<h1>A newer page</h1>", 1)
        pg.reload(); assert pg.inner_text('#start h1') == 'A newer page', 'online, the newest page wins (network first)'
        Flip.swap = {}; pg.reload(); assert pg.inner_text('#start h1') == "What's on your ballot?"
        kept = pg.evaluate("n => caches.open(n).then(c => c.keys()).then(ks => ks.map(r => r.url))", 'ballotta-next-1' if PAGE.startswith('next/') else 'ballotta-1')   # each scope its own
        origin = url.split('/' + PAGE)[0]
        assert re.sub(r'index\.html$', '', url) in kept and any(k.endswith('.woff2') for k in kept) and all(k.startswith(origin + '/') for k in kept), kept   # the page is kept as its folder (#76)
        srv.shutdown(); srv.server_close(); up = False                                   # now there is no network at all
        pg.reload(); poll(pg, "document.fonts.status === 'loaded'")
        assert pg.inner_text('#start h1') == "What's on your ballot?" and pg.evaluate("document.fonts.check('16px \"Public Sans\"')"), 'offline, another cache answered'
        assert pg.evaluate('window.__csp') == [], pg.evaluate('window.__csp')
    finally:
        ctx.close()
        if up: srv.shutdown(); srv.server_close()

@phone_test
def phone_home_screen_steps_name_the_right_buttons(b):
    # Lane, Oct 16: "Share" read as Ballotta's own Share my picks; on iOS 26 Safari's Share sits behind its ••• button;
    # some iPhones need View More. The steps name the browser's own buttons, draw them, and mark the step to do now.
    def open_steps(pg):
        pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click(); pg.wait_for_selector('#ph-install[open]')
    def now(pg): return pg.evaluate("[...document.querySelectorAll('#ph-i-ios li')].filter(l => l.classList.contains('ph-now') && l.getClientRects().length).map(l => l.id)")
    ctx, pg = phone_page(b, ua=IPHONE_UA); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
    open_steps(pg); t = pg.inner_text('#ph-i-ios')
    assert 'Safari’s buttons, not Ballotta’s' in t and 'View More' in t and 'bottom right' in t, t
    assert 'If another app opened this page' in t, ('an app\'s Safari view looks like Safari: say how out (Pass 2)', t)
    assert 'Paste my picks link' not in t, ('no picks yet: nothing to paste', t)
    assert now(pg) == ['ph-i-icon'], now(pg)
    icons = pg.evaluate("[...document.querySelectorAll('#ph-i-icon .ph-ico')].map(i => [i.getAttribute('role'), i.getAttribute('aria-label') || '', !!i.querySelector('svg')])")
    assert len(icons) >= 2 and all(i[0] == 'img' and i[1] and i[2] for i in icons) and any('three dots' in i[1] for i in icons), icons
    pg.click('#ph-install [data-close]'); pg.locator('.dk-line').first.click()
    open_steps(pg); t = pg.inner_text('#ph-i-ios')
    assert now(pg) == ['ph-i-carry'] and pg.locator('#ph-i-ok').is_hidden(), now(pg)
    assert 'not the Share my picks link' in t and 'Paste my picks link' in t and 'Paste bubble' in t and 'iPhone' in t, t
    pg.click('#ph-i-copy'); pg.wait_for_function("(window.__events || []).some(e => e[0] === 'home_screen' && e[1].action === 'copied')")
    assert now(pg) == ['ph-i-icon'] and pg.locator('#ph-i-ok').is_visible(), ('after the copy, step 2 is the one to do', now(pg))
    pg.click('#ph-install [data-close]'); open_steps(pg)
    assert now(pg) == ['ph-i-carry'] and pg.locator('#ph-i-ok').is_hidden(), ('picks may have changed: a new look starts at step 1', now(pg))
    assert pg.evaluate("(() => { const d = document.getElementById('ph-install'); return d.scrollWidth - d.clientWidth; })()") == 0, 'the steps run off the sheet'
    ctx.close()
    for ua, want, gone in ((CHROME_IOS_UA, 'Chrome’s buttons', 'Safari'), (FIREFOX_IOS_UA, 'your browser’s buttons', 'Safari'), (OPERA_IOS_UA, 'your browser’s buttons', 'Safari'), (IPAD_UA, 'Safari’s buttons', 'bottom right')):
        ctx, pg = phone_page(b, ua=ua); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
        pg.locator('.dk-line').first.click(); open_steps(pg); t = pg.inner_text('#ph-i-ios')
        assert want in t and gone not in t and 'View More' in t, (ua, t)
        if ua == IPAD_UA: assert 'iPad' in t and 'iPhone' not in t, t
        ctx.close()
    for ua in (INSTAGRAM_UA, FACEBOOK_UA, GOOGLE_APP_UA):                                  # an app's own browser can't add to the Home Screen (Pass 1)
        ctx, pg = phone_page(b, ua=ua); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
        pg.locator('.dk-line').first.click(); open_steps(pg); t = pg.inner_text('#ph-i-ios')
        assert 'Open this page in Safari first' in t and 'Open in Safari' in t and 'View More' not in t and 'Safari’s buttons' not in t, (ua, t)
        assert 'Paste my picks link' in t, ('the copied link still carries the picks to the Home Screen app', t)
        ctx.close()

@phone_test
def phone_saved_copy_says_so(b):
    # Lane (B4, Oct 16): when a dead network or the 4-second rule opens the copy kept on the phone, a bar says which,
    # with Try again; a fresh page never shows it; it goes when the network comes back. The page's CSP stays on.
    Flip.swap, Flip.gone, Flip.fail, Flip.slow, Flip.gzip = {}, set(), {}, {}, True; srv, url = own_server(); up = True
    ctx, pg = phone_page(b, csp=True, sw=True); pg.add_init_script(CSP_WATCH)
    try:
        pg.goto(url); poll(pg, '!!navigator.serviceWorker.controller', 15)
        pg.reload(); poll(pg, "document.fonts.status === 'loaded'")
        bar = pg.locator('#ph-saved')
        assert bar.is_hidden() and pg.get_attribute('html', 'data-copy') is None, 'a fresh page says it is the saved copy'
        Flip.slow = {'/' + PAGE: 7}; pg.reload(timeout=20000); Flip.slow = {}                 # no answer within 4 seconds
        assert bar.is_visible(), 'the 4-second rule opened the kept copy without saying so'
        t = bar.inner_text(); assert 'Slow connection' in t and 'copy saved on your phone' in t and 'Looking up an address needs a connection' in t, t
        go = pg.locator('#ph-saved-go'); assert go.bounding_box()['height'] >= 44, go.bounding_box()
        assert sideways(pg) == 0
        with pg.expect_navigation(timeout=20000): go.click()
        poll(pg, "document.readyState === 'complete'"); assert bar.is_hidden(), 'Try again got a fresh page but the bar stayed'
        png = url.rsplit('/', 1)[0] + '/x.png'; Flip.swap['/' + png.split('/', 3)[3]] = (ROOT / 'icon-192.png').read_bytes()
        pg.goto(png); pg.goto(url); poll(pg, "document.readyState === 'complete'")             # a non-page file in the copy's reach, kept
        pg.evaluate('localStorage.setItem("ballotta.ballot", JSON.stringify({ pr: "999", b: [99999], mode: "saved", at: 0 }))')   # a ballot this page can't show
        srv.shutdown(); srv.server_close(); up = False                                   # no network at all
        pg.goto(png); assert pg.evaluate("document.images.length === 1 && document.images[0].naturalWidth === 192"), 'the kept copy of an image no longer opens'
        pg.goto(url); poll(pg, "document.readyState === 'complete'")
        t = bar.inner_text(); assert bar.is_visible() and 'Looking up an address needs a connection' in t, ('the form is showing, not picks', t)
        pg.evaluate("renderStored({ pr: '999', b: [70, 71, 1], mode: 'saved' }, 'test')"); poll(pg, "document.body.classList.contains('dk-app-on')")   # picks arrive with no reload (a pasted link)
        assert 'Your picks are all here' in bar.inner_text(), ('the bar still says to look up an address (Pass 2)', bar.inner_text())
        pg.emulate_media(media='print'); assert bar.is_hidden(), 'the bar prints on the crib sheet (Pass 2)'; pg.emulate_media(media='screen')
        pg.add_init_script("window.__firstSay = null; new MutationObserver((m, o) => { const e = document.querySelector('#ph-saved b + span'); if (e && e.textContent) { window.__firstSay = e.textContent; o.disconnect(); } }).observe(document, { subtree: true, childList: true, characterData: true });")
        saved_ballot(pg, [70, 71, 1]); poll(pg, "document.body.classList.contains('dk-app-on')")
        t = bar.inner_text(); assert bar.is_visible() and 'No connection' in t and 'Your picks are all here' in t, t
        assert pg.evaluate('window.__firstSay') == 'Your picks are all here.', ('before start() draws it, a saved ballot must still count (Pass 3)', pg.evaluate('window.__firstSay'))
        assert pg.evaluate("document.querySelector('#ph-bar').getBoundingClientRect().bottom") <= 844 and sideways(pg) == 0
        pg.click('#ph-list'); assert pg.evaluate("document.getElementById('ph-saved').inert"), 'Try again stays reachable behind the open sheet'
        pg.click('#ph-done')
        pg.set_viewport_size({'width': 1180, 'height': 820}); pg.wait_for_timeout(200)     # a tablet turned sideways: the laptop layout (Pass 1)
        assert pg.evaluate("document.querySelector('.dk-rail').getBoundingClientRect().bottom <= innerHeight && document.getElementById('dk-print').getBoundingClientRect().bottom <= innerHeight"), 'the bar pushed the rail off the screen'
        assert bar.is_visible() and 'copy saved on your phone' in bar.inner_text(), ('sideways, the kept copy must still say so (Pass 2)', bar.inner_text() if bar.is_visible() else 'hidden')
        assert pg.evaluate("document.getElementById('ph-saved').getBoundingClientRect().top >= document.getElementById('dk-hdr').getBoundingClientRect().bottom - 1"), 'the bar covers the top bar'
        assert pg.evaluate("(() => { const r = document.getElementById('ph-saved').getBoundingClientRect(), g = document.getElementById('ph-saved-go').getBoundingClientRect(); return g.top >= r.top && g.bottom <= r.bottom && getComputedStyle(document.getElementById('ph-saved')).overflow === 'visible'; })()"), 'Try again or its focus ring is clipped by the bar (Pass 3)'
        pg.evaluate('window.scrollTo(0, 400)'); assert pg.evaluate("(() => { const r = document.getElementById('ph-saved').getBoundingClientRect(), a = document.querySelector('.dk-rail').getBoundingClientRect(); return r.top >= document.getElementById('dk-hdr').getBoundingClientRect().bottom - 1 && r.bottom <= a.top + 1; })()"), 'scrolled, the bar hides under the top bar or over the rail'
        pg.evaluate('window.scrollTo(0, 0)')
        pg.set_viewport_size(PHONE); pg.wait_for_timeout(200); assert bar.is_visible(), 'back on the phone layout, the bar must show again'
        pg.evaluate("window.dispatchEvent(new Event('online'))"); pg.wait_for_timeout(1500)   # the phone says it's online, the site doesn't answer (Wave 4 Pass 1)
        assert bar.is_visible() and 'No connection' in bar.inner_text(), ('the bar claimed the site was back', bar.inner_text())
        assert pg.evaluate('window.__csp') == [] and pg.errs == [], (pg.evaluate('window.__csp'), pg.errs)
    finally:
        ctx.close()
        if up: srv.shutdown(); srv.server_close()
        Flip.gzip, Flip.swap = False, {}

@phone_test
def laptops_get_no_offline_copy_or_install_prompt(b):
    # Laptops stay as they are: no offline copy, and Chrome's own install offer is left alone.
    ctx, pg = new_page(b, wide=True, sw=True); pg.goto(BASE); pg.wait_for_timeout(1500)
    assert pg.evaluate("navigator.serviceWorker.getRegistration().then(r => !r)"), 'a laptop got the offline copy'
    assert not pg.evaluate("() => { const e = new Event('beforeinstallprompt', { cancelable: true }); window.dispatchEvent(e); return e.defaultPrevented; }")
    ctx.close()

@phone_test
def phone_whole_visit_counts_only_listed_events(b):
    # Today's phone page has journey tests; this is the phone layout's: sources, directions, wait times, photo ID, a keep
    # link there and back, a share link, clearing picks and everything. Everything counted is listed and says "phone".
    ctx, pg = phone_page(b); pg.goto(BASE); no_link_opens(pg); lookup_phone(pg); to_contest(pg, 'District 9')
    pg.locator('.dk-line', has_text='Qadri').click(); pg.fill('#dk-w', 'Knows the district')
    pg.locator('.dk-paper .links a', has_text='Campaign site').first.click()
    pg.click('#ph-fold'); pg.locator('#dk-notes a', has_text='League').first.click()
    pg.click('#ph-list'); pg.click('#dk-views [data-view="vote"]')
    vote = pg.text_content('#dk-paper'); assert 'Bring a photo ID' in vote and 'Moved here from another Texas county' in vote, 'photo ID and notes, as on today\'s phone page'
    pg.locator('#dk-paper a', has_text='Check live wait times').click(); pg.locator('#dk-paper a', has_text='Directions').first.click()
    ev = events(pg)
    for want in (['source_opened', {'kind': 'campaign_site', 'level': 'city', 'layout': 'phone'}], ['source_opened', {'kind': 'league_guide', 'level': 'city', 'layout': 'phone'}],
                 ['wait_times_opened', {'period': pg.evaluate('period'), 'layout': 'phone'}], ['directions_opened', {'period': pg.evaluate('period'), 'layout': 'phone'}]):
        assert want in ev, (want, ev)
    pg.click('#ph-list'); pg.click('#dk-keep'); pg.click('#keep-copy'); pg.wait_for_selector('#keep-out:not(.hidden)')
    keep = pg.inner_text('#keep-out'); pg.click('#d-keep [data-close]'); pg.click('#ph-done')   # Keep opened over the list; the list is still there
    pg.click('#dk-share'); pg.fill('#sharename', 'Lane'); pg.click('#share-go'); pg.wait_for_selector('#share-out:not(.hidden)')
    assert '#s2' in pg.inner_text('#share-out'); pg.click('#d-share [data-close]')
    pg.once('dialog', lambda d: d.accept()); pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Clear my picks').click()
    assert cur(pg, 'c070') == [] and pg.text_content('#ph-count') == '0 of 63 decided'
    names_ = names(pg)
    assert {'keep_created', 'share_sheet_open', 'share_created', 'cleared', 'help_opened'} <= set(names_), names_
    journey_check(pg, 'phone')
    ctx.close()
    ctx, pg = phone_page(b); pg.goto(keep); pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go')
    pg.wait_for_selector('body.dk-app-on'); assert cur(pg, 'c070') == ['Zohaib “Zo” Qadri'] and pg.evaluate('whys.c070') == 'Knows the district'
    pg.once('dialog', lambda d: d.accept()); pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Clear everything').click()
    pg.wait_for_function("!Object.keys(localStorage).some(k => k.startsWith('ballotta.'))", timeout=5000)
    pg.wait_for_load_state(); expect(pg.locator('#start')).to_be_visible(); expect(pg.locator('#ph-bar')).to_be_hidden()
    journey_check(pg, 'phone')
    ctx.close()

@phone_test
def phone_runs_under_the_page_lock(b):
    # The phone layout keeps the page's Content-Security-Policy (#36): a whole visit, a friend's link to the Home Screen
    # steps, trips nothing (its icons are data: images, which the policy allows); an injected script still can't run.
    ctx, pg = phone_page(b, csp=True); pg.add_init_script(CSP_WATCH); pg.goto(BASE)
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Maya', 'c': 'abcd2350', 'g': 1, 'p': {'70': 0}}))
    poll(pg, "!document.getElementById('friend').classList.contains('hidden')")
    pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '78701'); pg.click('#go')
    poll(pg, "document.body.classList.contains('dk-app-on') && / of \\d+ decided$/.test(document.getElementById('ph-count').textContent)")
    pg.locator('.dk-line').first.click(); pg.click('#ph-fold'); pg.click('#ph-next')
    for v in ('glance', 'vote', 'crib'):
        pg.click('#ph-list'); pg.click(f'#dk-views [data-view="{v}"]')
        if v == 'vote': pg.click('.ph-mapfold summary')
    pg.click('#dk-help'); poll(pg, "document.getElementById('ph-menu').open")
    pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click(); poll(pg, "document.getElementById('ph-install').open")
    pg.click('#ph-install [data-close]'); pg.click('#dk-share'); poll(pg, "document.getElementById('d-share').open"); pg.click('#d-share [data-close]')
    pg.wait_for_timeout(500)
    assert pg.evaluate('window.__csp') == [], pg.evaluate('window.__csp')
    pg.evaluate("() => { const s = document.createElement('script'); s.textContent = 'window.__pwned = 1'; document.body.appendChild(s); }")
    pg.wait_for_timeout(200)
    assert pg.evaluate('window.__pwned') is None and any(v.startswith('script-src') for v in pg.evaluate('window.__csp')), 'an injected script ran'
    ctx.close()

@phone_test
def phone_resize_keeps_things_in_step(b):
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pg.click('#ph-list')
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(100)
    assert not pg.evaluate("document.body.classList.contains('ph-list') || document.getElementById('dk-desk').inert")
    expect(pg.locator('.dk-rail')).to_be_visible(); expect(pg.locator('#ph-bar')).to_be_hidden(); expect(pg.locator('#ph-fold')).to_be_hidden()
    pg.set_viewport_size(PHONE); pg.wait_for_timeout(100)
    expect(pg.locator('#ph-bar')).to_be_visible(); expect(pg.locator('.dk-rail')).to_be_hidden()
    ctx.close()

@phone_test
def laptop_unchanged_by_the_phone_code(b):
    # Laptops must not change: at laptop widths the page with the phone code is pixel-for-pixel the page without it,
    # on the landing page and in each view. Both are built in memory from the template (as the phone-parity test does).
    m = build_module(); shots = {}
    for name, ph in (('_lp_plain.html', False), ('_lp_phone.html', True)):
        html = m.build(phone=ph, results=False)                                                 # results need the phone code, so leave them out of both
        for size in ({'width': 1440, 'height': 900}, {'width': 1024, 'height': 640}):
            ctx, pg = new_page(b, wide=True); ctx.route(f'**/{name}', (lambda h: lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=h))(html))
            pg.set_viewport_size(size); pg.goto(f'http://127.0.0.1:{PORT}/{name}'); pg.wait_for_timeout(500)
            assert pg.evaluate('!!document.getElementById("ph-bar")') == ph, (name, 'built the wrong flavour')
            got = [pg.screenshot(full_page=True)]
            lookup_wide(pg); pg.wait_for_timeout(300); got.append(pg.screenshot(full_page=True))
            pg.click('[data-row="c070"]'); pg.locator('.dk-line', has_text='Qadri').click(); pg.fill('#dk-w', 'Knows the district'); pg.wait_for_timeout(200)
            got.append(pg.screenshot(full_page=True))
            for v in ('glance', 'vote', 'crib'):
                pg.click(f'#dk-views [data-view="{v}"]'); pg.wait_for_timeout(300); got.append(pg.screenshot(full_page=True))
            pg.click('#dk-help'); pg.wait_for_timeout(100); got.append(pg.screenshot())
            shots[(name, size['width'])] = got; ctx.close()
    for w in (1440, 1024):
        for k, (a, z) in enumerate(zip(shots[('_lp_plain.html', w)], shots[('_lp_phone.html', w)])):
            assert a == z, f'laptop differs with the phone code in: width {w}, shot {k} (landing, ballot, pick, glance, vote, crib, menu)'

# ---------------------------------------------------------------- phone audit, Pass 1 (Oct 16): findings A1–A9, B1–B3, C1–C7
LANDSCAPE = {'width': 844, 'height': 390}                  # an iPhone on its side

def obscured(pg):
    # The focused control's box against the sticky top bar and anything fixed at the bottom (the backup card, the bar).
    return pg.evaluate("""() => {
      const a = document.activeElement; if (!a || a === document.body || a.closest('#dk-hdr, #ph-bar, #dk-nudge')) return null;
      const r = a.getBoundingClientRect(), top = document.getElementById('dk-hdr').getBoundingClientRect().bottom;
      const lows = ['ph-bar', 'dk-nudge'].map(id => document.getElementById(id)).filter(e => e.getClientRects().length).map(e => e.getBoundingClientRect().top);
      const bottom = Math.min(innerHeight, ...lows);
      return r.top < top - 1 || r.bottom > bottom + 1 ? [a.id || a.tagName, Math.round(r.top), Math.round(r.bottom), Math.round(top), Math.round(bottom)] : null; }""")

@phone_test
def phone_list_sheet_on_a_landscape_phone(b):
    # A1, A5, A6 and the sheet's name: on a phone on its side the list still shows contests; Escape always closes it;
    # widening the window keeps focus on the row it was on; open, it is a named modal sheet.
    ctx, pg = phone_page(b, size=LANDSCAPE); pg.goto(BASE); saved_ballot(pg, list(range(1, 41))); pg.wait_for_selector('body.dk-app-on')
    pg.click('#ph-list')
    rail = pg.locator('.dk-rail')
    assert rail.get_attribute('role') == 'dialog' and rail.get_attribute('aria-modal') == 'true' and rail.get_attribute('aria-label') == 'Your ballot'
    rows = pg.evaluate("() => { const o = document.getElementById('dk-out').getBoundingClientRect(); return [...document.querySelectorAll('.dk-row')].filter(r => { const b = r.getBoundingClientRect(); return b.top >= Math.max(0, o.top) && b.bottom <= Math.min(innerHeight, o.bottom); }).length; }")
    pg.evaluate("document.querySelector('.dk-rail').scrollTo(0, 99999)")
    room = pg.evaluate("document.getElementById('dk-out').getBoundingClientRect().height")
    assert room >= 3 * 48, ('no room for contests on a landscape phone', room, rows)   # three rows, at least, by scrolling the sheet
    pg.locator('#dk-keep').scroll_into_view_if_needed(); assert pg.locator('#dk-keep').is_visible(), 'Keep my picks out of reach'
    pg.click('.dk-rhd h2'); assert focused(pg) == 'BODY'
    pg.keyboard.press('Escape'); expect(rail).to_be_hidden()
    assert rail.get_attribute('role') is None and rail.get_attribute('aria-modal') is None, 'closed, it is the laptop rail again'
    pg.click('#ph-list'); pg.fill('#dk-q', 'Senator'); pg.focus('#dk-q')
    pg.keyboard.press('Escape'); assert pg.input_value('#dk-q') == '' and rail.is_visible(), 'the first Escape clears the search'
    pg.keyboard.press('Escape'); expect(rail).to_be_hidden()
    pg.click('#ph-list'); row = pg.locator('.dk-row').nth(1); row.focus(); rid = row.get_attribute('data-row')
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(150)
    assert pg.evaluate('document.activeElement.dataset.row') == rid, 'widening drops focus'
    ctx.close()

@phone_test
def phone_long_friend_name_stays_on_screen(b):
    # A2: the longest name a link may carry, with no spaces, arriving while the app is open.
    nm = 'M' * 30
    for w in (320, 390):
        ctx, pg = phone_page(b, size={'width': w, 'height': 700}); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
        pg.evaluate("u => { location.hash = u.split('#')[1]; }", link('s', {'v': 1, 'n': nm, 'c': 'abcd2351', 'g': 1, 'p': {'70': 0}}))
        pg.wait_for_selector('.dk-fchip'); to_contest(pg, 'District 9')
        assert pg.inner_text('#ph-fold').startswith('You and ' + nm[:5]) and sideways(pg) <= 0, (w, sideways(pg))
        ctx.close()

@phone_test
def phone_focus_never_hides_under_the_bars(b):
    # A3, A4, A8: Tab and Shift+Tab never leave the focused control under the top bar, the backup card or the bottom bar;
    # on a phone on its side the card is compact; on a phone it comes after the paper in Tab order, on a laptop before.
    for size, card in ((PHONE, False), (PHONE, True), (LANDSCAPE, False), (LANDSCAPE, True)):
        ctx, pg = phone_page(b, size=size); pg.goto(BASE); saved_ballot(pg, list(range(1, 41))); pg.wait_for_selector('body.dk-app-on')
        if card:
            ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)')
            pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:5]); expect(pg.locator('#dk-nudge')).to_be_visible()
            if size == LANDSCAPE: assert box(pg, '#dk-nudge')['height'] <= 110, ('the card fills a landscape screen', box(pg, '#dk-nudge'))
        for view in ('decide', 'glance'):
            if view == 'glance': pg.click('#ph-list'); pg.click('#dk-views [data-view="glance"]')
            for key in ('Tab', 'Shift+Tab'):
                pg.evaluate('window.scrollTo(0, 600)'); pg.focus('#dk-paper'); bad = []
                for _ in range(25):
                    pg.keyboard.press(key); o = obscured(pg)
                    if o: bad.append(o)
                assert not bad, (size, card, view, key, bad[:3])
        ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, list(range(1, 41))); pg.wait_for_selector('body.dk-app-on')
    ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:5])
    pg.evaluate("""() => { const f = document.getElementById('ph-fold'), all = [...document.querySelectorAll('#dk-desk a[href], #dk-desk button, #dk-desk textarea, #dk-desk input')].filter(e => e.getClientRects().length && !e.closest('#dk-nudge'));
        const prev = all[all.indexOf(f) - 1], bar = document.getElementById('ph-bar').getBoundingClientRect().top;
        window.scrollBy(0, f.getBoundingClientRect().top - bar + 20); prev.focus({ preventScroll: true }); }""")   # the fold straddles the bottom bar's edge
    pg.keyboard.press('Tab'); assert focused(pg) == 'ph-fold' and obscured(pg) is None, ('Tab left the fold under the bottom bar', obscured(pg))
    pg.focus('#ph-fold'); pg.keyboard.press('Tab')                                         # the fold is the paper's last stop (its notes closed)
    assert pg.evaluate('document.activeElement.dataset.nudge') == 'keep', ('the card is skipped in Tab order', focused(pg))
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(150)
    assert pg.evaluate("document.getElementById('dk-nudge').nextElementSibling.id") == 'dk-paper', 'the laptop order changed'
    ctx.close()

@phone_test
def phone_targets_and_resize_leftovers(b):
    # A9, A7/C5, C3: contest names in At a glance are 44px targets; the menu button's state is true after a round trip;
    # narrowing closes the laptop menu; widening closes every phone sheet (the laptop's keys work again).
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pg.click('#ph-list'); pg.click('#dk-views [data-view="glance"]')
    small = pg.evaluate("[...document.querySelectorAll('.dk-tbl tbody th .dk-link')].filter(e => e.getBoundingClientRect().height < 44).length")
    assert small == 0, (small, 'contest names under 44px')
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(100); pg.click('#dk-help'); expect(pg.locator('#dk-menu')).to_be_visible()
    pg.set_viewport_size({'width': 800, 'height': 900}); pg.wait_for_timeout(100)
    assert pg.evaluate("document.getElementById('dk-menu').classList.contains('hidden')"), 'the laptop menu stays open on a phone'
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(100)
    assert pg.get_attribute('#dk-help', 'aria-expanded') == ('false' if pg.evaluate("document.getElementById('dk-menu').classList.contains('hidden')") else 'true')
    pg.click('#dk-help'); assert pg.get_attribute('#dk-help', 'aria-expanded') == 'true' and pg.is_visible('#dk-menu')
    pg.keyboard.press('Escape')
    pg.set_viewport_size(PHONE); pg.wait_for_timeout(100)
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click(); pg.wait_for_selector('#ph-install[open]')
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(150)
    assert pg.evaluate("[...document.querySelectorAll('dialog[open]')].map(d => d.id)") == [], 'a phone sheet left open on a laptop'
    ctx.close()

@phone_test
def phone_paste_shows_only_the_link(b):
    # B1 and the nit: a note around a link never reaches the screen, only the link does; a lone marker shows nothing;
    # the box empties when the sheet closes; a damaged link isn't counted as pasted.
    ctx, pg = phone_page(b, init=STANDALONE, ua=IPHONE_UA); pg.goto(BASE); pg.click('#ph-paste-open')
    pg.evaluate("navigator.clipboard.writeText('Dr. Patel 2pm re: results. Maya: https://ballotta.org/#s2AAAAAAAAAAAAAAAAAAAA')"); pg.click('#ph-p-clip')
    pg.wait_for_selector('#ph-p-msg:not(.hidden)'); v = pg.input_value('#ph-p-in')
    assert 'Patel' not in v and v.endswith('#s2AAAAAAAAAAAAAAAAAAAA'), v
    pg.evaluate("navigator.clipboard.writeText('reset code 739201 #k2 (ignore)')"); pg.click('#ph-p-clip'); pg.wait_for_timeout(300)
    assert pg.input_value('#ph-p-in') == '', pg.input_value('#ph-p-in')
    pg.fill('#ph-p-in', 'x'); pg.click('#ph-paste-d [data-close]'); pg.wait_for_timeout(200); assert pg.input_value('#ph-p-in') == '', 'the box keeps what was pasted'
    pg.click('#ph-paste-open'); pg.fill('#ph-p-in', BASE + '#k2' + 'A' * 40); pg.click('#ph-p-go'); pg.wait_for_timeout(500)
    assert 'pasted' not in [e[1].get('action') for e in events(pg) if e[0] == 'home_screen'], events(pg)
    assert 'damaged' in pg.inner_text('#ph-p-msg') or 'incomplete' in pg.inner_text('#ph-p-msg'), pg.inner_text('#ph-p-msg')
    ctx.close()

@phone_test
def phone_offline_kill_switch_and_promotion(b):
    # B2, B3: OFFLINE = False removes the copy and its caches for good (a later load can't bring the cache back);
    # the preview keeps its own cache name; once promoted, the build writes a self-removing next/sw.js.
    m = build_module(); pv = PAGE.startswith('next/')                                # the preview, or the promoted main page (promotion audit #1)
    folder = PAGE.rsplit('/', 1)[0] + '/' if '/' in PAGE else ''; mine = 'ballotta-next-1' if pv else 'ballotta-1'
    on, off = m.sw_js(True), m.sw_off_js(True)
    assert "'ballotta-next-1'" in on and "'ballotta-1'" in m.sw_js(False) and "startsWith('ballotta-next-')" in off and "startsWith('ballotta-')" in m.sw_off_js(False)
    was = m.STREETS_LIVE; m.PHONE_LIVE = m.STREETS_LIVE = True; out = m.outputs(False); main_sw = m.sw_js(False); m.PHONE_LIVE, m.STREETS_LIVE = False, was   # nothing in preview (Oct 19)
    assert out['next/sw.js'] == m.sw_off_js(True) and out['sw.js'] == main_sw and out['next/index.html'] == m.moved_page(), sorted(out)
    Flip.swap = {}; srv, url = own_server()
    ctx, pg = phone_page(b, sw=True)
    try:
        pg.goto(url); assert pg.evaluate('Promise.race([navigator.serviceWorker.ready.then(() => true), new Promise(ok => setTimeout(ok, 15000, false))])')
        poll(pg, '!!navigator.serviceWorker.controller', 15); pg.reload(); poll(pg, f"caches.open('{mine}').then(c => c.match(location.href.replace(/index\\.html$/, ''))).then(r => !!r)", 15)   # a copy kept, not just a cache made (Pass 2)
        m.OFFLINE = False; page = m.build(preview=pv, phone=True); m.OFFLINE = True
        Flip.swap = {'/' + PAGE: page.encode('utf-8'), '/' + folder + 'sw.js': m.sw_off_js(pv).encode('utf-8')}
        pg.reload(); poll(pg, "navigator.serviceWorker.getRegistrations().then(r => r.length === 0)", 15)
        poll(pg, "caches.keys().then(k => !k.some(x => x.startsWith('ballotta')))", 15)
        pg.evaluate("() => new Promise(ok => { const i = new Image(); i.onload = i.onerror = ok; i.src = '../icon-512.png?late'; })"); pg.wait_for_timeout(500)
        assert pg.evaluate("caches.keys()") == [], 'a later load brought a cache back'
        ctx.close()
        for wide, gone in ((True, False), (False, 503)):                                  # a laptop-width window; a hiccup
            Flip.swap, Flip.gone, Flip.fail = {}, set(), {}
            ctx, pg = (new_page(b, wide=True, sw=True) if wide else phone_page(b, sw=True)); pg.goto(url)
            if wide: pg.evaluate("navigator.serviceWorker.register('sw.js')")             # an older install, before laptops were left out
            poll(pg, "navigator.serviceWorker.getRegistrations().then(r => r.length === 1)", 15)
            pg.evaluate(f"caches.open('{mine}').then(c => c.put(location.href, new Response('x')))")
            Flip.swap = {'/' + PAGE: page.encode('utf-8')}
            swp = '/' + folder + 'sw.js'
            if gone == 503: Flip.fail = {swp: 503}
            else: Flip.swap[swp] = m.sw_off_js(pv).encode('utf-8')
            pg.wait_for_timeout(3000); Flip.hits = []                                       # let the browser's own update check settle first
            pg.reload()
            if gone == 503:                                                                  # a hiccup is not "gone": the copy stays
                pg.wait_for_timeout(2500)
                assert 'getRegistration(\'./\')' in pg.content() and swp in Flip.hits, ('the kill switch never asked for sw.js', Flip.hits)
                assert pg.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.length)") == 1 and pg.evaluate(f"caches.has('{mine}')"), 'a 503 removed the copy'
            else:
                poll(pg, "navigator.serviceWorker.getRegistrations().then(r => r.length === 0)", 15)
                poll(pg, "caches.keys().then(k => !k.some(x => x.startsWith('ballotta')))", 15)
            ctx.close()
        Flip.swap, Flip.gone, Flip.fail = {}, set(), {}                                    # a page never touches another folder's copy (Pass 3)
        ctx, pg = phone_page(b, sw=True); pg.goto(url); poll(pg, "navigator.serviceWorker.getRegistrations().then(r => r.length === 1)", 15)
        other = '/_other.html' if pv else '/next/_other.html'                              # a page in another folder
        Flip.swap = {other: m.build(phone=True).encode('utf-8')}; Flip.fail = {'/' + folder + 'sw.js': 503}
        origin = url.split('/', 3)[0] + '//' + url.split('/', 3)[2]
        pg.goto(origin + other); pg.wait_for_timeout(2500)
        assert pg.evaluate("s => navigator.serviceWorker.getRegistrations().then(r => r.some(g => g.scope === s))", origin + '/' + folder), 'another page removed this folder\'s copy'
    finally:
        Flip.swap, Flip.gone, Flip.fail = {}, set(), {}; ctx.close(); srv.shutdown(); srv.server_close()

@test
def promotion_hands_the_preview_on(b):
    # Cold audit #21: promotion is the build's job. With PHONE_LIVE, the main build writes next/index.html as a page that
    # asks for next/sw.js again (the self-removing worker; the preview's own registration only) and then sends people
    # on to the main page, #fragment and all, so a link made on the preview still opens; and the main page asks for
    # next/sw.js too, for a phone that installed the preview but now only opens ballotta.org. A failed fetch removes
    # nothing (Pass 3).
    m = build_module()
    pre = m.outputs(True)
    was = m.STREETS_LIVE; m.PHONE_LIVE = m.STREETS_LIVE = True                              # nothing else in preview at next/ (Oct 19)
    try: post = m.outputs(False)
    finally: m.PHONE_LIVE, m.STREETS_LIVE = False, was
    assert post['next/index.html'] == m.moved_page() and post['next/sw.js'] == m.sw_off_js(True), sorted(post)
    assert post['index.html'].count(m.SW_NEXT) == 1 and 'id="ph-bar"' in post['index.html'], 'the promoted page clears the preview'
    live_now = m.PHONE_LIVE; m.PHONE_LIVE = False
    try: back = m.outputs(False)                                                            # a rollback after promotion (Pass 2)
    finally: m.PHONE_LIVE = live_now
    assert m.SW_NEXT not in pre['next/index.html'] and m.SW_NEXT not in back['index.html'], 'only the promoted main page does'
    assert back['sw.js'] == m.sw_off_js(False), 'a rollback must remove the offline copy phones kept since promotion'
    assert 'id="ph-bar"' not in back['index.html'] and 'PHONE' not in back['index.html'] and 'rel="manifest"' not in back['index.html'], 'a rollback brings back the old phone page, with no phone code'
    moved = post['next/index.html']
    assert '<link rel="manifest"' not in moved and 'sw.register' not in moved and m.sha(m.MOVED_JS) in moved, 'next/ can no longer be installed'
    before = {'/next/index.html': pre['next/index.html'], '/next/': pre['next/index.html'], '/next/sw.js': pre['next/sw.js']}
    after = {'/next/index.html': moved, '/next/': moved, '/next/sw.js': post['next/sw.js'], '/': post['index.html'], '/index.html': post['index.html'], '/sw.js': post['sw.js']}
    enc = lambda d: {k: v.encode('utf-8') for k, v in d.items()}
    Flip.swap, Flip.gone, Flip.fail, Flip.hits = enc(before), set(), {}, []
    srv, url = own_server(); base = url.split('/', 3)[0] + '//' + url.split('/', 3)[2] + '/'
    preview = "navigator.serviceWorker.getRegistrations().then(r => r.some(g => g.scope.endsWith('/next/')))"
    nextcache = "caches.keys().then(k => k.some(x => x.startsWith('ballotta-next-')))"
    ctx = None
    try:
        for how in ('opens next/', 'opens the main page', 'opens the main page, next/sw.js fails'):
            Flip.swap, Flip.fail = enc(before), {}
            ctx, pg = phone_page(b, sw=True); pg.goto(base + 'next/')
            poll(pg, '!!navigator.serviceWorker.controller', 15); pg.reload(); poll(pg, nextcache, 15)   # the preview, installed
            Flip.swap = enc(dict(after, **{'/next/sw.js': pre['next/sw.js']})); pg.wait_for_timeout(3000)   # the browser's own update check finds nothing new
            Flip.swap = enc(after); Flip.hits = []
            if 'fails' in how: Flip.fail = {'/next/sw.js': 503}
            if how == 'opens next/':
                pg.goto('about:blank'); pg.goto(base + 'next/#s2PREVIEWLINK', wait_until='commit'); pg.wait_for_url(base, timeout=15000)   # a new load, not a same-page #change
                assert pg.evaluate('window.__incoming') == 's2PREVIEWLINK', 'the link made on the preview was lost on the way'
                assert pg.evaluate("document.getElementById('ph-bar') !== null"), 'next/ did not land on the main page'
            else:
                pg.goto(base); pg.wait_for_timeout(2500)
            assert '/next/sw.js' in Flip.hits, (how, 'nobody asked for next/sw.js again', Flip.hits)
            if 'fails' in how:
                assert pg.evaluate(preview) and pg.evaluate(nextcache), 'a failed fetch removed the preview copy'
            else:
                poll(pg, preview.replace('r.some(', '!r.some('), 15)                          # the preview's worker, gone
                poll(pg, nextcache.replace('k.some(', '!k.some('), 15)                       # and its copies
            ctx.close(); ctx = None
        # Promotion audit #4: a phone with only the main page's worker (it never had the preview) opens next/ and then
        # the main page: neither asks the main page's worker to update; each touches only next/'s own registration.
        Flip.swap, Flip.fail = enc(after), {}
        spy = ("const u = ServiceWorkerRegistration.prototype.update; ServiceWorkerRegistration.prototype.update = function () {"
               " try { localStorage.setItem('spy.update', (localStorage.getItem('spy.update') || '') + this.scope + ' '); } catch (e) {} return u.call(this); };")
        ctx, pg = phone_page(b, sw=True, init=spy); pg.goto(base); poll(pg, '!!navigator.serviceWorker.controller', 15)
        pg.goto('about:blank'); pg.goto(base + 'next/#s2ROOTONLY', wait_until='commit'); pg.wait_for_url(base, timeout=15000)
        assert pg.evaluate('window.__incoming') == 's2ROOTONLY'
        pg.reload(); pg.wait_for_timeout(1000)
        assert pg.evaluate("localStorage.getItem('spy.update')") in (None, ''), ('a page updated a worker that isn\'t next/\'s', pg.evaluate("localStorage.getItem('spy.update')"))
        assert pg.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.map(g => g.scope))") == [base], 'the main page\'s worker was touched'
        ctx.close(); ctx = None
        # Promotion audit #3: after the hand-off, the Home Screen app (start_url next/) and the main page still open
        # with no connection at all, before any second visit: the main page's worker keeps both from its install.
        Flip.swap, Flip.fail = enc(before), {}
        ctx, pg = phone_page(b, sw=True, csp=True); pg.goto(base + 'next/')                  # under the pages' own CSP (Pass 2)
        poll(pg, '!!navigator.serviceWorker.controller', 15); pg.reload(); poll(pg, nextcache, 15)
        Flip.swap = enc(after)
        pg.goto('about:blank'); pg.goto(base + 'next/', wait_until='commit'); pg.wait_for_url(base, timeout=15000)
        poll(pg, f"caches.open('ballotta-1').then(c => Promise.all([c.match('{base}'), c.match('{base}next/')])).then(([a, n]) => !!a && !!n)", 15)
        poll(pg, preview.replace('r.some(', '!r.some('), 15)                                 # the preview's worker has gone
        srv.shutdown(); srv.server_close()                                                    # no connection at all from here
        for start in (base + 'next/', base):
            pg.goto('about:blank'); pg.goto(start, wait_until='commit'); pg.wait_for_url(base, timeout=15000); pg.wait_for_selector('#ph-bar', state='attached', timeout=15000)
            assert pg.evaluate("document.documentElement.dataset.copy") == 'offline', (start, 'not the kept copy')
    finally:
        Flip.swap, Flip.gone, Flip.fail = {}, set(), {}
        if ctx: ctx.close()
        srv.shutdown(); srv.server_close()

@test
def offline_copy_install_never_waits_on_a_slow_line(b):
    # Pass 2: the worker keeps the page at install, but a slow line holds its install (and so the 4-second fallback, and
    # any update queued behind it, the kill switch's included) for 8 seconds at most.
    m = build_module()
    files = {'/index.html': m.build(phone=True), '/sw.js': m.sw_js(False), '/next/': m.moved_page()}
    Flip.swap, Flip.gone, Flip.fail, Flip.slow = {k: v.encode('utf-8') for k, v in files.items()}, set(), {}, {'/next/': 25}
    srv, url = own_server(); base = url.split('/', 3)[0] + '//' + url.split('/', 3)[2] + '/'
    ctx, pg = phone_page(b, sw=True)
    try:
        pg.goto(base + 'index.html'); t0 = time.time()
        poll(pg, "navigator.serviceWorker.getRegistration().then(g => !!(g && g.active))", 20)
        assert time.time() - t0 < 15, ('the install waited on the slow page', time.time() - t0)
        assert pg.evaluate(f"caches.open('ballotta-1').then(c => c.match('{base}next/')).then(r => !r)"), 'a page that never arrived was kept'
        assert '/next/' in Flip.hits, 'the install never asked for next/: the slow line was never tried'
        assert pg.evaluate(f"caches.open('ballotta-1').then(c => c.match('{base}')).then(r => !!r)"), 'giving up on next/ lost the page itself'
    finally:
        Flip.swap, Flip.gone, Flip.fail, Flip.slow = {}, set(), {}, {}; ctx.close(); srv.shutdown(); srv.server_close()

@test
def offline_copy_install_skips_redirects_and_cut_downloads(b):
    # #54: the install keeps nothing that came by a redirect (a redirected answer to a page is refused when replayed
    # offline) and nothing cut off partway (the 8-second abort mid-body), and still keeps the page itself.
    m = build_module()
    files = {'/index.html': m.build(phone=True), '/sw.js': m.sw_js(False), '/next/': m.moved_page()}
    for mode in ('moved', 'stall'):
        Flip.swap, Flip.gone, Flip.fail, Flip.slow = {k: v.encode('utf-8') for k, v in files.items()}, set(), {}, {}
        Flip.moved, Flip.stall = ({'/next/': '/index.html'}, {}) if mode == 'moved' else ({}, {'/next/': 25})
        srv, url = own_server(); base = url.split('/', 3)[0] + '//' + url.split('/', 3)[2] + '/'
        ctx, pg = phone_page(b, sw=True)
        try:
            pg.goto(base + 'index.html'); t0 = time.time()
            poll(pg, "navigator.serviceWorker.getRegistration().then(g => !!(g && g.active))", 20)
            assert time.time() - t0 < 15, (mode, 'the install waited', time.time() - t0)
            assert '/next/' in Flip.hits, (mode, 'the install never asked for next/')
            assert pg.evaluate(f"caches.open('ballotta-1').then(c => c.match('{base}next/')).then(r => !r)"), (mode, 'next/ was kept')
            assert pg.evaluate(f"caches.open('ballotta-1').then(c => c.match('{base}')).then(r => !!r)"), (mode, 'the page itself was lost')
        finally:
            Flip.swap, Flip.gone, Flip.fail, Flip.slow, Flip.moved, Flip.stall = {}, set(), {}, {}, {}, {}; ctx.close(); srv.shutdown(); srv.server_close()

@test
def offline_copy_marks_any_html_tag(b):
    # #75: the worker marks a kept page by its opening <html> tag, whatever attributes it carries, not by one exact
    # string, so a template change can't quietly stop the saved-copy bar. Only the document's own opening tag.
    src = build_module().sw_js(False)
    said = src[src.index('const said = '):]
    ctx, pg = new_page(b); pg.goto(BASE)
    run = lambda html: pg.evaluate("([s, h]) => (0, eval)('(() => { ' + s + '; return said; })()')(new Response(h, { headers: { 'content-type': 'text/html' } }), 'slow').then(r => r.text())", [said, html])
    for html in ('<!doctype html>\n<html lang="en">x', '<!doctype html>\n<html lang="en" class="phone">x', '<!DOCTYPE html><HTML LANG="en">x', '<html lang="en-US" dir="ltr">x',
                 '<!-- built by build_site.py -->\n<!doctype html>\n<html lang="en">x', '<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN">\n<html>x'):   # Pass 1
        out = run(html)
        assert out.count('data-copy="slow"') == 1 and out.endswith('x'), (html, out)
    out = run('<!doctype html>\n<html lang="en"><script>const s = "<html>";</script>')
    assert out.count('data-copy') == 1 and out.index('data-copy') < out.index('<script>'), out
    out = run('<!--> <!doctype html>\n<html lang="en"><body><!-- a --><html>x')   # Pass 2: an abrupt comment; only the real tag
    assert out.count('data-copy') == 1 and out.index('data-copy') < out.index('<body>'), out
    for junk in ('<!-- a -->' * 24, '<!-->' * 30, '<!--->' * 30):              # Pass 2, 3: no runaway backtracking, abrupt comments included
        ms = pg.evaluate("([s, h]) => { const f = (0, eval)('(() => { ' + s + '; return said; })()'); const t = performance.now(); return f(new Response(h), 'slow').then(() => performance.now() - t); }", [said, junk + '<body>x'])
        assert ms < 200, ('comments before a page that has no <html> took', junk[:6], ms)
    ctx.close()

@phone_test
def phone_saved_copy_bar_follows_the_site(b):
    # #73: the "Slow connection" bar goes once the site answers again (checked when the page comes back into view, and
    # every so often), not only on the browser's "online" event, which a slow line never fires. #74: a server error that
    # arrives inside 4 seconds (a deploy, a proxy) opens the kept page, saying so, never the error.
    Flip.swap, Flip.gone, Flip.fail, Flip.slow, Flip.gzip = {}, set(), {}, {}, False; srv, url = own_server(); up = True
    ctx, pg = phone_page(b, csp=True, sw=True); pg.add_init_script(CSP_WATCH)
    bar, visible = pg.locator('#ph-saved'), lambda: pg.evaluate("!document.getElementById('ph-saved').classList.contains('hidden')")
    seen = lambda: pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    try:
        pg.goto(url); poll(pg, '!!navigator.serviceWorker.controller', 15); pg.reload(); poll(pg, "document.fonts.status === 'loaded'")
        Flip.slow = {'/' + PAGE: 7}; pg.reload(timeout=20000); Flip.slow = {}
        assert visible() and 'Slow connection' in bar.inner_text()
        back = "document.querySelector('#ph-saved b').textContent === 'Ballotta is back.' && document.getElementById('ph-saved-go').textContent === 'Reload'"
        poll(pg, back, 6)                                                  # Lane (Oct 18): the bar offers the newer page, never reloads by itself;
                                                                           # round-2 #16 (#114): first asked a second after load, not after 20 s
        assert visible() and pg.get_attribute('html', 'data-copy') == 'slow' and 'copy saved' not in bar.inner_text(), bar.inner_text()
        pg.evaluate('desk.render()'); assert bar.inner_text().replace('\n', ' ').split() == ['Ballotta', 'is', 'back.', 'Reload'], ('a redraw brought old words back', bar.inner_text())
        with pg.expect_navigation(timeout=20000): pg.click('#ph-saved-go')
        poll(pg, "document.readyState === 'complete'"); assert pg.get_attribute('html', 'data-copy') is None and not visible(), 'Reload got the fresh page'
        Flip.gone = {'/' + PAGE}; pg.reload(timeout=20000)                # Pass 1: a page that's really gone is never masked by the copy
        assert pg.get_attribute('html', 'data-copy') is None and pg.locator('#street').count() == 0, 'a 404 was hidden behind the kept copy'
        Flip.gone = set(); pg.goto(url); poll(pg, "document.readyState === 'complete'")
        Flip.fail = {'/' + PAGE: 503}; pg.reload(timeout=20000)
        assert pg.get_attribute('html', 'data-copy') == 'error' and pg.locator('#start h1').is_visible(), ('a 503 was shown, not the kept page', pg.content()[:200])
        assert visible() and "isn’t answering" in bar.inner_text() and 'copy saved on your phone' in bar.inner_text(), bar.inner_text()
        seen(); pg.wait_for_timeout(1500); assert visible(), 'the site still answers with an error: the bar stays'
        Flip.fail = {}; pg.evaluate("window.dispatchEvent(new Event('online'))"); poll(pg, back, 10)   # the phone saying it's online asks too
        pg.evaluate("window.dispatchEvent(new Event('offline'))"); assert "isn’t answering" in bar.inner_text(), ('offline: the bar takes its word back', bar.inner_text())
        Flip.slow = {'/' + PAGE: 1}; pg.evaluate("window.dispatchEvent(new Event('online'))"); pg.wait_for_timeout(300)    # Pass 3: a check in flight when the phone goes offline
        pg.evaluate("window.dispatchEvent(new Event('offline'))"); pg.wait_for_timeout(1500); Flip.slow = {}
        assert "isn’t answering" in bar.inner_text(), ('an answer that left before "offline" said the site was back', bar.inner_text())
        pg.evaluate("window.dispatchEvent(new Event('online'))"); poll(pg, back, 10)
        Flip.fail = {'/' + PAGE: 503}; seen(); pg.wait_for_timeout(1500)      # Pass 2: the site stops answering again: the bar says so again
        assert "isn’t answering" in bar.inner_text() and pg.inner_text('#ph-saved-go') == 'Try again', bar.inner_text()
        Flip.fail = {'/' + PAGE: 429}; pg.reload(timeout=20000)               # Pass 2: a rate limit is no answer too
        assert pg.get_attribute('html', 'data-copy') == 'error', 'a 429 was shown, not the kept page'
        Flip.fail = {}; Flip.slow = {'/' + PAGE: 5}; pg.reload(timeout=20000)  # Pass 2: a line answering in 5 s: Reload would land on the copy again
        assert pg.get_attribute('html', 'data-copy') == 'slow'
        seen(); pg.wait_for_timeout(6500)
        assert 'Ballotta is back.' not in bar.inner_text(), 'it said the site was back, but a reload would still take the copy'
        pg.evaluate('window.AbortController = undefined'); seen(); pg.wait_for_timeout(6500)   # a browser that can't cut a request short (older iPhones)
        assert 'Ballotta is back.' not in bar.inner_text(), 'without AbortController, a slow answer counted as back'
        Flip.slow = {}; seen(); poll(pg, back, 10)
        srv.shutdown(); srv.server_close(); up = False
        pg.reload(timeout=20000); assert visible() and 'No connection' in bar.inner_text()
        seen(); pg.evaluate("window.dispatchEvent(new Event('online'))"); pg.wait_for_timeout(1500)
        assert visible() and 'No connection' in bar.inner_text(), 'no site: the bar stays as it was'
        assert pg.evaluate('window.__csp') == [], pg.evaluate('window.__csp')
    finally:
        Flip.swap, Flip.gone, Flip.fail, Flip.slow = {}, set(), {}, {}
        ctx.close()
        if up: srv.shutdown(); srv.server_close()

@phone_test
def phone_menu_after_install_offers_no_home_screen(b):
    # #76: after an Android install, the tab's Feedback & Info sheet no longer offers "Add to your Home Screen".
    ctx, pg = phone_page(b); pg.goto(BASE)
    items = lambda: pg.evaluate("[...document.querySelectorAll('#ph-mitems button')].map(b => b.dataset.ph)")
    assert 'home' in items()
    pg.evaluate("window.dispatchEvent(new Event('appinstalled'))")
    assert 'home' not in items(), items()
    ctx.close()

@phone_test
def phone_measure_without_sources_has_no_empty_fold(b):
    # #76: a measure with nothing behind its fold shows no fold; one with sources keeps it.
    ctx, pg = phone_page(b); pg.goto(BASE)
    bare, rich = pg.evaluate("(() => { const m = DATA.contests.filter(c => c.type === 'measure'); const has = c => ((DATA.learn[c.id] || {}).src || []).length; return [m.find(c => !has(c)).id, m.find(has).id]; })()")
    saved_ballot(pg, [int(bare[1:]), int(rich[1:])]); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate('id => desk.ph.go(id)', bare); pg.wait_for_timeout(200)
    assert not pg.locator('#ph-fold').is_visible(), (bare, 'an empty fold')
    pg.evaluate('id => desk.ph.go(id)', rich); pg.wait_for_timeout(200)
    assert pg.locator('#ph-fold').is_visible(), (rich, 'its sources lost their fold')
    ctx.close()

@test
def a_tablet_turned_upright_keeps_an_offline_copy(b):
    # #76: a tablet that loads in landscape (the laptop layout) gets the offline copy once it's turned upright.
    ctx, pg = new_page(b, touch=True, size={'width': 1180, 'height': 820}, sw=True); pg.goto(BASE)
    reg = lambda: pg.evaluate("navigator.serviceWorker.getRegistration().then(g => !!g)")
    pg.wait_for_timeout(800); assert not reg(), 'landscape: no copy, as on a laptop'
    pg.set_viewport_size({'width': 820, 'height': 1180}); poll(pg, "navigator.serviceWorker.getRegistration().then(g => !!g)", 10)
    ctx.close()
    ctx, pg = new_page(b, size={'width': 1440, 'height': 900}, sw=True); pg.goto(BASE)          # a laptop narrowed: still never
    pg.set_viewport_size({'width': 700, 'height': 900}); pg.wait_for_timeout(1000); assert not reg(), 'a laptop window got the offline copy'
    ctx.close()

@phone_test
def phone_next_from_another_view_counts_decide(b):
    # #76: "Next" from At a glance or Where to vote opens a contest, and counts view_opened: decide, as "Back" does.
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, [1, 70]); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("desk.ph.setView('glance')"); pg.click('#ph-next'); pg.wait_for_timeout(200)
    assert pg.evaluate('desk.ph.ui.view') == 'decide' and any(e[0] == 'view_opened' and e[1].get('view') == 'decide' for e in events(pg)), events(pg)
    ctx.close()

@phone_test
def offline_copy_one_copy_for_the_page(b):
    # #76: / and /index.html are one page, so one kept copy, and either opens offline.
    Flip.swap, Flip.gone, Flip.fail, Flip.slow = {}, set(), {}, {}; srv, url = own_server(); up = True
    base = url.rsplit('/', 1)[0] + '/'
    ctx, pg = phone_page(b, sw=True)
    try:
        pg.goto(base + 'index.html'); poll(pg, '!!navigator.serviceWorker.controller', 15); pg.reload(); pg.wait_for_timeout(500)
        mine = 'ballotta-next-1' if PAGE.startswith('next/') else 'ballotta-1'                 # the preview keeps its own (Oct 19)
        keys = pg.evaluate(f"caches.open('{mine}').then(c => c.keys()).then(ks => ks.map(r => r.url))")
        assert base in keys and base + 'index.html' not in keys, keys
        srv.shutdown(); srv.server_close(); up = False
        for at in (base, base + 'index.html'):
            pg.goto(at); assert pg.get_attribute('html', 'data-copy') == 'offline' and pg.locator('#street').count() == 1, at
    finally:
        ctx.close()
        if up: srv.shutdown(); srv.server_close()

@test
def a_share_link_without_picks_counts_nothing(b):
    # #76: a link with no picks it can read says so, and is not counted as opened, nor starts a share generation.
    ctx, pg = new_page(b); pg.goto(link('s', {'v': 1, 'n': 'Al', 'c': 'zero0001', 'g': 3, 'p': {'9999': 0}}))
    pg.wait_for_selector('#friend:not(.hidden)')
    assert 'didn’t contain any picks' in pg.inner_text('#friend')
    assert not any(e[0] == 'share_opened' for e in events(pg)) and pg.evaluate("localStorage.getItem('ballotta.gen')") is None, events(pg)
    ctx.close()

@test
def a_new_friend_updates_the_compare_card(b):
    # #76: a second share link arriving in the same tab redraws an open comparison for the new friend.
    ctx, pg = new_page(b); pg.goto(BASE); saved_ballot(pg, [1, 70]); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("u => { location.hash = u.split('#')[1]; }", link('s', {'v': 1, 'n': 'Al', 'c': 'abcd2501', 'g': 1, 'p': {'70': 0}}))
    pg.wait_for_function("friend && friend.name === 'Al'"); pg.evaluate('showCompare()')
    assert pg.inner_text('#cmph') == 'You and Al'
    pg.evaluate("u => { location.hash = u.split('#')[1]; }", link('s', {'v': 1, 'n': 'Bea', 'c': 'abcd2502', 'g': 1, 'p': {'70': 1}}))
    pg.wait_for_function("friend && friend.name === 'Bea'")
    assert pg.inner_text('#cmph') == 'You and Bea', pg.inner_text('#cmph')
    ctx.close()

@test
def stored_picks_only_for_this_ballot(b):
    # #76: picks read from this device keep only contests and choices on today's ballot, so nothing stale counts as
    # decided or reaches a link.
    ctx, pg = new_page(b); pg.goto(BASE)
    pg.evaluate("""() => { const o = optionsOf(BYID.c071)[0];
        localStorage.setItem('ballotta.picks', JSON.stringify({ c999: ['X'], c070: ['Not a candidate'], c071: [o, 'Bogus'], c001: ['__skip'], c006: ['__skip', 'X'] }));
        localStorage.setItem('ballotta.whys', JSON.stringify({ c999: 'old', c071: 'kept' })); }""")
    pg.reload()
    o = pg.evaluate('optionsOf(BYID.c071)[0]')
    got = pg.evaluate("['c999', 'c070', 'c071', 'c001', 'c006'].map(id => current(id))")
    assert got == [[], [], [o], ['__skip'], []], got
    # Pass 1: read through a filter, never deleted: a pick saved now keeps everything another version of the page stored.
    saved_ballot(pg, [1, 81]); pg.wait_for_selector('body.dk-app-on'); pg.evaluate("desk.ph.go('c081')"); pg.locator('#dk-paper .dk-line').first.click()
    kept = pg.evaluate("JSON.parse(localStorage.getItem('ballotta.picks'))")
    assert kept.get('c999') == ['X'] and kept.get('c070') == ['Not a candidate'] and 'c081' in kept, kept
    ctx.close()

@phone_test
def phone_candidate_links_are_full_size_targets(b):
    # #51: "Campaign site" and "League guide answers" under each name are 44px tall on a phone, like every other control.
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, [1, 70]); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("desk.ph.go('c001')"); pg.wait_for_timeout(200)
    hs = pg.evaluate("[...document.querySelectorAll('#dk-paper .links a')].map(a => Math.round(a.getBoundingClientRect().height))")
    assert hs and min(hs) >= 44, hs
    assert sideways(pg) <= 0
    ctx.close()

@test
def the_map_shows_all_five_closest_centers(b):
    # #76: from an outlying address (Webberville), the five numbered centers were mostly off the map, while its label
    # promised them. The map now widens just enough to fit all five; closer in, it keeps its usual scale.
    for pt, wide in (([-97.50, 30.24], True), ([-98.10, 30.55], True), ([-98.17, 30.62], True), ([-97.7431, 30.2747], False)):   # Pass 1, 2: far northwest too
        ctx, pg = new_page(b, wide=True); pg.goto(BASE); saved_ballot(pg, [1, 70], pt=pt); pg.wait_for_selector('body.dk-app-on')
        pg.evaluate("desk.ph.setView('vote')"); pg.wait_for_selector('#dk-map')
        assert pg.locator('#dk-map .top').count() == 5, (pt, pg.locator('#dk-map .top').count())
        assert pg.evaluate("[...document.querySelectorAll('#dk-map > text')].every(t => +t.getAttribute('x') >= 48 && +t.getAttribute('x') <= 512)"), 'a town name cut off at the edge'
        assert pg.evaluate("[...document.querySelectorAll('#dk-map .top text')].pop().textContent") == '1', 'center 1 is drawn last, on top'
        assert pg.evaluate("(() => { const t = [...document.querySelectorAll('#dk-map > text')].map(e => [+e.getAttribute('x'), +e.getAttribute('y')]); return t.every((a, i) => t.every((b, j) => i === j || Math.hypot(a[0] - b[0], a[1] - b[1]) >= 60)); })()") or not wide, 'widened: town names pile up'   # Pass 2 (measured: never closer than 70px at real far points, so no spacing code)
        # The map's width in degrees, read back from where the numbered centers sit (x = W/2 + (lon - yours) / width * W).
        # Measured, not guessed from a dot count: Election Day has 201 centers, so a close-in map downtown holds ~48 dots.
        for per in ('early', 'eday'):
            pg.click(f'[data-period="{per}"]'); pg.wait_for_selector('#dk-map')
            sx = pg.evaluate("""([lon, per]) => {
              const W = 560, at = {}; DATA.sites[per].forEach(s => { at[s[0]] = s[5]; });
              const far = [...document.querySelectorAll('#dk-map .top circle')].map(c => [+c.getAttribute('cx') - W / 2, at[c.querySelector('title').textContent]])
                .sort((a, b) => Math.abs(b[0]) - Math.abs(a[0]))[0];
              return (far[1] - lon) / far[0] * W; }""", [pt[0], per])
            if wide: assert sx > 0.13, (pt, per, sx, 'widened to fit the five')
            else: assert abs(sx - 0.12) < 0.002, (pt, per, sx, 'downtown: the usual close-in map, not one widened to most of the county')
        ctx.close()


# ---------------------------------------------------------------- the street map (Lane, Oct 19; next/ until STREETS_LIVE)
STREET_SPOTS = {'south': [-97.7745, 30.2235], 'downtown': [-97.7431, 30.2747], 'mueller': [-97.7050, 30.2980],
                'domain': [-97.7195, 30.3885], 'oakhill': [-97.84, 30.235], 'far': [-98.17, 30.62]}
# Mueller: the town name sits on you; Oak Hill: highway labels compete for one corner; far: a widened map
MAP_PROBLEMS = """(() => {
  const m = document.getElementById('dk-map'), W = 560, H = 520, bb = e => { const r = e.getBBox(); return [r.x, r.y, r.x + r.width, r.y + r.height]; };
  const hit = (a, b) => a[0] < b[2] - 0.5 && b[0] < a[2] - 0.5 && a[1] < b[3] - 0.5 && b[1] < a[3] - 0.5, out = [];
  const tags = [...m.querySelectorAll('.st-tag')].map(g => ({ n: g.textContent, r: bb(g.querySelector('rect')), t: bb(g.querySelector('text')) }));
  const dots = [...m.querySelectorAll(':scope > circle, .top circle')].map(bb), you = bb(m.querySelector(':scope > g:not(.top):not(.st-tag) rect'));
  const names = [...m.querySelectorAll(':scope > text')].map(e => ({ n: e.textContent, b: bb(e) }));
  tags.forEach((g, i) => {
    if (!(g.t[0] >= g.r[0] - 0.5 && g.t[2] <= g.r[2] + 0.5 && g.t[1] >= g.r[1] - 1.5 && g.t[3] <= g.r[3] + 1.5)) out.push('label sticks out of its tag: ' + g.n);
    if (!(g.r[0] >= 0 && g.r[2] <= W && g.r[1] >= 0 && g.r[3] <= H)) out.push('tag off the edge of the map: ' + g.n);
    if (hit(g.r, you)) out.push('tag on you: ' + g.n);
    dots.forEach(d => { if (hit(g.r, d)) out.push('tag on a vote center: ' + g.n); });
    names.forEach(t => { if (hit(g.r, t.b)) out.push('tag on a town name: ' + g.n + ' / ' + t.n); });
    tags.slice(i + 1).forEach(h => { if (hit(g.r, h.r)) out.push('two tags overlap: ' + g.n + ' / ' + h.n); });
  });
  names.forEach(t => { if (hit(t.b, you)) out.push('town name on you: ' + t.n); dots.forEach(d => { if (hit(t.b, d)) out.push('town name under a vote center: ' + t.n); }); });
  m.querySelectorAll('.st-wat, .st-rd').forEach(p => (p.getAttribute('d') || '').split('M').filter(Boolean).forEach(sub => {
    const n = sub.split(/[ L]/).map(Number), xs = n.filter((_, i) => i % 2 === 0), ys = n.filter((_, i) => i % 2 === 1);
    if (Math.max(...xs) < 0 || Math.min(...xs) > W || Math.max(...ys) < 0 || Math.min(...ys) > H) out.push('a line drawn wholly outside the map: ' + p.getAttribute('class'));
  }));
  return [...new Set(out)];
})()"""

@test
def street_map_waits_for_promotion(b):
    # Lane, Oct 19: the street map is built into the preview (next/) only, until STREETS_LIVE: the main page carries none
    # of its code or data. The preview has the data compact and the credit; promotion puts it on the main page and sends
    # next/ on again; with streets off the page is exactly the main page; the street map needs the laptop layout.
    m = build_module(); was = m.STREETS_LIVE; m.PHONE_LIVE = True                           # as promoted (a phone rollback has no next/ to check)
    live, prev = m.build(), m.build(preview=True)
    data = json.loads((ROOT / 'source/data/streets.json').read_text(encoding='utf-8'))
    assert m.strip_streets('a\n/*STREETS*/\nb\n/*/STREETS*/\nc;/*STREETS*/ d;/*/STREETS*/\n') == 'a\nc;\n'
    for bad in ('/*STREETS*/ x', 'a\n/*STREETS*/\nb\n/*/STREETS*/ }\n', 'x /*STREETS*/ y\n/*/STREETS*/\n'):
        try: m.strip_streets(bad); refused = False
        except AssertionError: refused = True
        assert refused, f'malformed STREETS markers must stop the build: {bad!r}'
    assert '.dk-map .st-wat{' in prev and 'const STREETS = ' + json.dumps(data, separators=(',', ':')) + ';' in prev, 'the preview carries the street data, compact'
    assert 'Streets and water on the map: U.S. Census Bureau TIGER/Line, 2024.' in prev, 'the credit'
    assert prev.count('<meta name="robots" content="noindex">') == 1 and 'noindex' not in live, 'search engines list the main page, never the preview'
    assert "fetch('../version.json?'" in prev and "fetch('version.json?'" in live, 'a preview left open asks the one version.json, at the root'
    assert m.build(streets=False) == (live if not was else m.build(streets=False)) and '.dk-map .st-wat{' not in m.build(streets=False) and '"fwy":' not in m.build(streets=False)
    if not was:
        assert '.dk-map .st-wat{' not in live and 'TIGER/Line' not in live and '"fwy":' not in live, 'the street map leaked into the main page'
        out = m.outputs(False)
        assert out['next/index.html'] == prev and out['next/sw.js'] == (m.sw_js(True) if m.OFFLINE else m.sw_off_js(True)), 'next/ is the preview, with its own offline copy'
        if m.OFFLINE:
            assert "['./', 'picks/'].map" in out['sw.js'], "the main page's offline copy fetches the 600 KB preview at install"
            assert "c.delete(new URL('next/', location.href).href)" in out['sw.js'], 'a hand-off page kept before would be shown for the preview'
    assert "['./'].map" in m.sw_js(True) and 'c.delete(' not in m.sw_js(True), "the preview's own copy keeps only its page"
    m.STREETS_LIVE = True
    try: post = m.outputs(False); rolled = m.build(desk=True, phone=False)        # promoted, then a phone-layout rollback: it builds, street map and all
    finally: m.STREETS_LIVE = was
    assert '.dk-map .st-wat{' in rolled and 'id="ph-bar"' not in rolled, 'a phone-layout rollback after promotion'
    assert '.dk-map .st-wat{' in post['index.html'] and post['next/index.html'] == m.moved_page() and post['next/sw.js'] == m.sw_off_js(True), 'promoted: on the main page, and next/ sends people on'
    if m.OFFLINE:
        assert "['./', 'next/', 'picks/'].map" in post['sw.js'] and 'c.delete(' not in post['sw.js'], 'promoted: the offline copy keeps the hand-off page again, for Home Screen apps from a preview'
    try: m.build(desk=False, phone=False, streets=True); refused = False                   # phone off: its own refusal names the laptop layout too
    except AssertionError as e: refused = 'street map' in str(e) and 'laptop layout' in str(e)
    assert refused, 'the street map without the laptop layout that draws it: refused, saying why'

@streets_test
def street_map_draws_streets_and_asks_nobody(b):
    # Lane, Oct 19: streets, highways and water under the dots, from data in the page: drawing the map asks nothing of
    # anyone. Labels (highway tags, town names) keep off you, the vote centers and each other; a town name a dot would
    # cover moves above or below it; a widened map shows highways only; only lines that reach the view are drawn.
    for spot, pt in STREET_SPOTS.items():
        for period in ('early', 'eday'):
            ctx, pg = new_page(b, wide=True); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.goto(BASE); saved_ballot(pg, [1, 70], pt=pt); pg.wait_for_selector('body.dk-app-on')
            asked = []; pg.on('request', lambda r: asked.append(r.url))
            pg.evaluate("desk.ph.setView('vote')"); pg.click(f'[data-period="{period}"]'); pg.wait_for_selector('#dk-map')
            assert asked == [], (spot, 'drawing the map asked for', asked)
            m = pg.evaluate("""(() => { const m = document.getElementById('dk-map'), d = c => m.querySelector(c).getAttribute('d');
              return {grid: m.querySelectorAll(':scope > line').length, wat: d('.st-wat'), art: d('.st-art'), fw: d('.st-fw'), hw: d('.st-hw'),
                      tags: [...m.querySelectorAll('.st-tag text')].map(t => t.textContent), size: [...m.querySelectorAll('.st-tag text')].map(t => getComputedStyle(t).fontSize),
                      halo: [...m.querySelectorAll(':scope > text')].map(t => getComputedStyle(t).paintOrder)}; })()""")
            assert m['grid'] == 0 and (m['fw'] or m['hw']), (spot, period, 'streets in place of the grid', m['tags'])
            assert bool(m['art']) == (spot != 'far' or period == 'eday'), (spot, period, 'major streets close in; highways only on a widened map (far out, early voting: 45 centers)')
            assert m['tags'] and set(m['size']) == {'10px'} and all(h.startswith('stroke') for h in m['halo']), (spot, period, m['tags'], m['size'], m['halo'])
            if spot in ('south', 'downtown'): assert 'I-35' in m['tags'] and 'MoPac' in m['tags'] and m['wat'], (spot, period, m['tags'])
            problems = pg.evaluate(MAP_PROBLEMS)
            assert problems == [], (spot, period, problems)
            assert errs == [], errs
            ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, [1, 70], pt=STREET_SPOTS['south']); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("desk.ph.setView('vote')"); pg.click('.ph-mapfold summary'); expect(pg.locator('#dk-map')).to_be_visible()
    assert set(pg.evaluate("[...document.querySelectorAll('#dk-map .st-tag text')].map(t => getComputedStyle(t).fontSize)")) == {'12px'}, 'phone: bigger tags, as its town names are'
    problems = pg.evaluate(MAP_PROBLEMS)
    assert problems == [] and sideways(pg) <= 0 and pg.errs == [], (problems, pg.errs)
    ctx.close()

@phone_test
def laptops_stay_laptops_after_a_narrow_start(b):
    # C1, C2: a narrow window on a laptop (a mouse, not a finger) never installs the offline copy; a laptop-wide Home
    # Screen window adds no "app" detail to what it counts.
    ctx, pg = new_page(b, sw=True, size={'width': 900, 'height': 800}); pg.goto(BASE); pg.wait_for_timeout(1500)
    assert pg.evaluate("navigator.serviceWorker.getRegistration().then(r => !r)"), 'a narrow laptop window got the offline copy'
    ctx.close()
    ctx, pg = new_page(b, wide=True); pg.add_init_script(STANDALONE); pg.goto(BASE); pg.evaluate("track('faq_seen')")
    assert events(pg)[-1] == ['faq_seen', {'layout': 'laptop'}], events(pg)[-1]
    ctx.close()

@phone_test
def phone_taps_land_where_they_were_aimed(b):
    # Pass 2: a tap or click on a control half under the backup card or the top bar lands on it (the keyboard's scroll
    # doesn't move it from under the pointer); focus inside the card survives a width change; a view button in the
    # sheet keeps focus when the window widens.
    ctx, pg = phone_page(b, size={'width': 320, 'height': 844}); pg.goto(BASE); saved_ballot(pg, list(range(1, 41))); pg.wait_for_selector('body.dk-app-on')
    ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:5]); expect(pg.locator('#dk-nudge')).to_be_visible()
    pg.evaluate('ids => pick(ids[5], optionsOf(BYID[ids[5]])[0])', ids)                     # the card stays (it shows once)
    pg.wait_for_function("document.querySelector('#dk-nudge [role=status]').textContent.length > 0")   # its words arrive a moment later and it grows
    btn = '[data-prompt^="Still deciding"]'
    pg.evaluate("s => { const b = document.querySelector(s).getBoundingClientRect(), c = document.getElementById('dk-nudge').getBoundingClientRect(); window.scrollBy(0, b.top - (c.top - 12)); }", btn)
    r = box(pg, btn); before = pg.evaluate('scrollY')
    pg.mouse.click(r['x'] + 20, r['y'] + 5)
    assert pg.input_value('#dk-w').startswith('Still deciding because'), ('the click missed', before, pg.evaluate('scrollY'))
    pg.evaluate("() => { document.activeElement.blur(); const b = document.getElementById('dk-w').getBoundingClientRect(), c = document.getElementById('dk-nudge').getBoundingClientRect(); window.scrollBy(0, b.top - (c.top - 30)); }")
    r = box(pg, '#dk-w'); before = pg.evaluate('scrollY'); pg.mouse.click(r['x'] + 20, r['y'] + 10)
    assert focused(pg) == 'dk-w' and pg.evaluate('scrollY') == before, ('a tapped field jumped', before, pg.evaluate('scrollY'))
    pg.keyboard.press('Tab'); pg.wait_for_timeout(100)                                  # one Tab: that focus may scroll
    pg.evaluate("() => { const b = document.getElementById('dk-w').getBoundingClientRect(), c = document.getElementById('dk-nudge').getBoundingClientRect(); window.scrollBy(0, b.top - (c.top - 30)); }")
    before = pg.evaluate('scrollY'); pg.evaluate("() => document.getElementById('dk-w').focus({ preventScroll: true })")
    assert pg.evaluate('scrollY') == before, 'a script\'s preventScroll was overridden'
    pg.evaluate("() => { const b = document.createElement('button'); b.id = 'ph-last-test'; b.textContent = 'x'; document.body.append(b); b.focus(); }")
    pg.keyboard.press('Tab'); pg.wait_for_timeout(100)                                  # Tab out of the page: no focus arrives in it
    pg.evaluate("() => { const b = document.getElementById('dk-w').getBoundingClientRect(), c = document.getElementById('dk-nudge').getBoundingClientRect(); window.scrollBy(0, b.top - (c.top - 30)); }")
    before = pg.evaluate('scrollY'); pg.evaluate("() => document.getElementById('dk-w').focus({ preventScroll: true })")
    assert pg.evaluate('scrollY') == before, 'a Tab out of the page left the flag set'
    pg.focus('#dk-nudge [data-nudge="keep"]'); pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(150)
    assert pg.evaluate('document.activeElement.dataset.nudge') == 'keep', 'widening dropped focus from the card'
    pg.set_viewport_size(PHONE); pg.wait_for_timeout(150)
    assert pg.evaluate('document.activeElement.dataset.nudge') == 'keep', 'narrowing dropped focus from the card'
    pg.click('#dk-nudge [data-nudge="dismiss"]'); pg.click('#ph-list'); pg.focus('#dk-views [data-view="vote"]')
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(150)
    assert pg.evaluate('document.activeElement.dataset.view') == 'vote', 'widening dropped focus from a view button'
    ctx.close()

# ---------- ports of the old phone page's tests to the phone layout (cold audit #29, Oct 17) ----------
# ---------------------------------------------------------------- ports of today's phone-page tests to the phone layout (group A)
# Each drives the phone layout at phone width (or, where the old test also checked the laptop, the laptop too), so it
# keeps guarding the same behaviour now that the phone layout is the live page (the old tests went with promotion).
def pa_menu(pg, item):                                       # Feedback & Info, as a phone visitor opens it: a sheet
    pg.click('#dk-help'); pg.wait_for_selector('#ph-menu[open]')
    pg.locator('#ph-mitems button', has_text=item).click()

def pa_relookup(pg, street='1000 Guadalupe St', zip_='78701'):   # another lookup from the app: Change address, then the form
    pa_menu(pg, 'Change address'); expect(pg.locator('#start')).to_be_visible()
    pg.fill('#street', street); pg.fill('#zip', zip_); pg.click('#go')
    pg.wait_for_selector('body.dk-app-on', timeout=30000)

def pa_open(pg, cid):                                        # a contest, through the "Your ballot" sheet
    pg.click('#ph-list'); pg.locator(f'.dk-row[data-row="{cid}"]').click()
    expect(pg.locator('.dk-rail')).to_be_hidden()
    assert pg.evaluate("document.getElementById('dk-paper').dataset.c") == cid

def pa_view(pg, v):
    pg.click('#ph-list'); pg.click(f'#dk-views [data-view="{v}"]'); expect(pg.locator('.dk-rail')).to_be_hidden()

def pa_fold(pg):                                             # "About this office · Learn more": the notes under the paper
    if pg.get_attribute('#ph-fold', 'aria-expanded') != 'true': pg.click('#ph-fold')
    expect(pg.locator('#dk-notes')).to_be_visible()

@phone_test
def phone_lookup_counts_started_and_found(b):
    # Port of lookup_courthouse_and_ballot_found: the courthouse address finds all 63 contests, counted as started and
    # found (an exact match), from the phone.
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg)
    assert pg.text_content('#ph-count') == '0 of 63 decided' and pg.evaluate('ballot.length') == 63, pg.text_content('#ph-count')
    ev = events(pg)
    assert ['lookup_started', {'layout': 'phone'}] in ev and ['ballot_found', {'match': 'exact', 'layout': 'phone'}] in ev, ev
    assert names(pg).index('lookup_started') < names(pg).index('ballot_found'), ev
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def phone_learn_more_is_symmetric_and_attributed(b):
    # Port of race_learn_more_is_symmetric_and_attributed: District 9 on the phone paper and its notes fold.
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pa_open(pg, 'c070')
    kai = pg.locator('#dk-paper .dk-lw', has_text='Kai Huang').inner_text()
    assert 'Didn’t answer the League guide' in kai and 'No campaign site listed' in kai, kai
    zo = pg.locator('#dk-paper .dk-lw', has_text='Qadri')
    assert zo.locator('a', has_text='Campaign site').get_attribute('href') == 'https://zoforaustin.com'
    assert zo.locator('a', has_text='League guide answers, p. 33').get_attribute('href').endswith('LWVAA-VG-EN.pdf#page=33')
    rows = pg.locator('#dk-paper .dk-lw').all()
    assert len(rows) >= 2
    for row in rows:                                         # every candidate: exactly two link slots (site + guide)
        assert row.locator('.links > *').count() == 2, row.inner_text()
    pa_fold(pg); notes = pg.inner_text('#dk-notes')
    assert 'One of 10 district council members' in notes, notes
    assert 'League of Women Voters of the Austin Area 2026 Voters Guide' in notes, notes
    srcs = [a.get_attribute('href') for a in pg.locator('#dk-notes .srcs a').all()]
    assert srcs and srcs[0].endswith('#page=32') and any('austintexas.gov/voterinfo' in s for s in srcs), srcs
    ctx.close()

@phone_test
def phone_measure_card_prop_a(b):
    # Port of measure_card_prop_a: Prop A on the phone paper, verbatim, with the money and tax lines, no argument boxes.
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pa_open(pg, 'c071')
    body = pg.inner_text('#dk-paper')
    assert 'principle of and interest in bonds' in body                      # verbatim, typos included
    assert '$65.5M' in body and '$14.34' in body and 'the City may sell these bonds' in body, body
    pa_fold(pg); allt = body + pg.inner_text('#dk-notes')
    assert 'Supporters' not in allt and 'Opponents' not in allt              # Lane: no argument boxes
    pg.locator('#dk-paper .dk-line', has_text='For').first.click()
    assert pg.locator('#dk-paper .dk-line[aria-pressed=true]').inner_text().strip() == 'For' and cur(pg, 'c071') == ['FOR']
    ctx.close()

@phone_test
def phone_where_to_vote_sorted_by_distance(b):
    # Port of where_to_vote_sorted_by_distance, in the phone's Where to vote view. The date is pinned inside early voting
    # (cold audit #18: from Oct 31 the page opens on Election Day); timers still run.
    import datetime as dt
    ctx, pg = phone_page(b); pg.clock.set_fixed_time(dt.datetime(2026, 10, 20, 12, 0)); pg.goto(BASE); lookup_phone(pg)
    pa_view(pg, 'vote')
    sites = pg.locator('#dk-sites .dk-site')
    assert sites.count() == 5, sites.count()
    d = [float(re.search(r'([\d.]+) mi', s.inner_text()).group(1)) for s in sites.all()]
    assert d == sorted(d) and d[0] < 1, d
    first5 = pg.inner_text('#dk-sites')
    for name in ['Austin Recreation Center', 'Travis County Civil and Family Courts Facility', 'UT Texas Union']:
        assert name in first5, first5
    assert 'Open till 10pm Oct 29–30' in first5
    pg.click('#dk-all'); assert pg.locator('#dk-sites .dk-site').count() == 45
    pg.click('#dk-paper [data-period="eday"]'); assert pg.locator('#dk-sites .dk-site').count() == 201
    assert 'Election%20Day' in pg.locator('#dk-paper a', has_text='Check live wait times').get_attribute('href')
    assert sideways(pg) <= 0
    ctx.close()

@phone_test
def phone_guide_data_a1_a2_a3(b):
    # Port of audit_a1_a2_a3_guide_data: League-guide data fixes (A1 sites, A2 answers, B1, C1) and the unopposed race (A3),
    # read on the phone paper and its notes fold.
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pa_open(pg, 'c006')
    dx = pg.locator('#dk-paper .dk-lw', has_text='Pat Dixon')
    assert dx.locator('a', has_text='Campaign site').get_attribute('href') == 'https://patdixon.org', dx.inner_text()   # A1
    L = pg.evaluate('DATA.learn')
    assert L['c017']['cands']['Thomas Smith']['s'] == 'https://www.smithfortexas.org'                                  # A1
    assert L['c131']['cands']['Mike Randolph'] == {'g': 1, 'p': 50, 'a': 1}                                            # A2
    assert L['c129']['cands']['Josh Castro']['a'] == 0 and L['c129']['cands']['Josh Castro']['g'] == 1                  # A2
    assert L['c063']['lwvRace'] == 1                                                                                     # A2
    assert L['c065']['cands']['Yvonne Muñoz'] == {'g': 1, 'p': 25, 'a': 1}                                             # B1 contested, answered
    assert L['c055']['cands']['Brigid Shea'] == {'g': 1, 'p': 24, 'a': 0, 'u': 1}                                     # C1 side-by-side names
    pa_open(pg, 'c034'); pa_fold(pg)                                                                                     # A3
    t = pg.inner_text('#dk-paper') + '\n' + pg.inner_text('#dk-notes')
    assert 'Unopposed · no questions in the League guide' in t and 'League guide answers' not in t and 'Lists this race as unopposed' in t, t
    ctx.close()

@phone_test
def phone_share_generation_and_friend_over_saved_ballot(b):
    # Port of audit_a10_a11_generation_and_own_ballot. A10: your place in a share chain is fixed by your first share; a
    # later friend's link (generation 4) doesn't move it. A11, as the phone layout does it by design (plan, difference 3):
    # a friend's link opened over a saved ballot shows their picks inline (no "See my own ballot" button) and counts the
    # open, then the compare, once.
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pa_open(pg, 'c001')
    pg.locator('#dk-paper .dk-line', has_text='Ted Brown').click()
    pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]'); pg.click('#share-go')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'share_created')")
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.gen'))") == 1                                         # A10
    assert [e[1]['generation'] for e in events(pg) if e[0] == 'share_created'] == [1], events(pg)
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Bo', 'c': 'gen4link', 'g': 4, 'p': {'1': 0}}))
    pg.wait_for_selector('.dk-fchip')
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.gen'))") == 1                                         # A10
    expect(pg.locator('#f-own')).to_be_hidden(); expect(pg.locator('#ph-bar')).to_be_visible()                          # A11: straight to the inline view
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'share_compare')", timeout=5000)
    seq = [e for e in events(pg) if e[0] in ('share_opened', 'share_compare')]
    assert seq == [['share_opened', {'generation': 4, 'has_picks': 'yes', 'link': 'gen4link', 'layout': 'phone'}], ['share_compare', {'layout': 'phone'}]], seq
    pa_open(pg, 'c001'); assert 'Bo picked this' in pg.inner_text('#dk-paper')
    pg.click('#ph-next'); pg.click('#ph-back'); pg.wait_for_timeout(300)
    assert names(pg).count('share_compare') == 1, events(pg)
    ctx.close()

@phone_test
def phone_tracker_tag_and_link_targets(b):
    # Port of audit_a14_a15_tracker_and_targets. A14: the pinned tracker is served from this site and loads deferred (the
    # fail-closed stub depends on it, cold audit #15). A15: a candidate's links on the phone paper are at least 24px tall.
    src = (ROOT / PAGE).read_text(encoding='utf-8')
    assert re.search(r'<script defer src="(\.\./)?umami\.js"', src) and 'cloud.umami.is/script.js"' not in src            # A14
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pa_open(pg, 'c070')
    hs = [a.bounding_box()['height'] for a in pg.locator('#dk-paper .dk-lw .links a').all()]
    assert hs and min(hs) >= 24, hs                                                                                      # A15
    ctx.close()

@phone_test
def phone_restore_counts_and_link_dedupe(b):
    # Port of audit_b3_b4_counts_and_dedupe. B3: a keep link's repeated or unknown contests count once ("1 of 1"); C5: picks
    # for contests not on the link's ballot aren't counted. B4: a friend's link without a code is counted once, however
    # often the visitor comes back to their own ballot: share_compare once per page (the phone layout's compare,
    # by design), and share_own_ballot once across repeated lookups.
    ctx, pg = phone_page(b)
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, 1, 1, 99999], 'p': {'1': 0}}))
    pg.wait_for_selector('#d-restore[open]')
    assert '1 of 1 contests' in pg.inner_text('#restoresum'), pg.inner_text('#restoresum')                            # B3
    fresh_goto(pg, 'about:blank'); fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1], 'p': {'1': 0, '6': 0, '70': 0}}))
    pg.wait_for_selector('#d-restore[open]')
    assert '1 of 1 contests' in pg.inner_text('#restoresum'), pg.inner_text('#restoresum')                            # C5
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, 1, 1, 99999], 'p': {'1': 0}}))
    pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go')
    pg.wait_for_selector('body.dk-app-on'); assert pg.text_content('#ph-count') == '1 of 1 decided', pg.text_content('#ph-count')
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Al', 'g': 1, 'p': {'1': 0}}))                                              # no link code
    pg.wait_for_selector('.dk-fchip'); expect(pg.locator('#f-own')).to_be_hidden()
    pg.click('#ph-next'); pg.click('#ph-back'); pg.click('#ph-next'); pg.click('#ph-back'); pg.wait_for_timeout(500)
    assert names(pg).count('share_compare') == 1, events(pg)                                                           # B4
    pa_relookup(pg); pa_relookup(pg); pg.wait_for_timeout(500)
    assert names(pg).count('share_own_ballot') == 1 and names(pg).count('share_compare') == 1, events(pg)              # B4
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def phone_counts_where_people_drop_off(b):
    # Port of counts_where_people_drop_off, from the phone layout's own form (the landing, then Change address).
    ctx, pg = phone_page(b); pg.goto(BASE)
    pg.click('#go'); pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '787'); pg.click('#go')
    assert [e[1].get('reason') for e in events(pg) if e[0] == 'lookup_failed'] == ['no_street', 'bad_zip']
    pg.evaluate("chooseUnit({ a: [{ Unit: '1' }], b: [{ Unit: '2' }] }, '1 Main St', null)")
    assert names(pg).count('units_asked') == 1
    pg.fill('#zip', '78701'); pg.click('#go'); pg.wait_for_selector('body.dk-app-on', timeout=30000)
    assert names(pg).count('lookup_started') == 1 and names(pg).count('address_changed') == 0 and names(pg).count('ballot_found') == 1, names(pg)
    found = lambda k: pg.wait_for_function(f"(window.__events||[]).filter(e => e[0] === 'ballot_found').length === {k}", timeout=30000)
    pa_relookup(pg); found(2)                                                                    # the same address again: not a change
    assert names(pg).count('address_changed') == 0
    pg.evaluate("renderStored({ pr: '9', b: [1, 2], mode: 'saved' }, 'test')"); pa_relookup(pg); found(3)   # a different ballot was showing
    assert names(pg).count('address_changed') == 1
    journey_check(pg, 'phone'); ctx.close()
    ctx, pg = phone_page(b); ctx.route(re.compile(r'https://taxmaps\.traviscountytx\.gov/.*'), lambda r: r.abort()); pg.goto(BASE)
    pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '78701'); pg.click('#go')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'lookup_failed')", timeout=15000)
    assert events(pg)[-1] == ['lookup_failed', {'reason': 'county_unreachable', 'layout': 'phone'}]; ctx.close()
    def census(route, match):
        cb = re.search(r'callback=([A-Za-z0-9_]+)', route.request.url).group(1)
        m = '[{"coordinates":{"x":-97.74,"y":30.27},"matchedAddress":"1 NOWHERE ST, AUSTIN, TX, 78701"}]' if match else '[]'
        route.fulfill(status=200, content_type='application/javascript', body=cb + '({"result":{"addressMatches":' + m + '}})')
    for match, reason, va in ((False, 'not_found', 'empty'), (True, 'no_voters_nearby', 'empty'), (True, 'county_unreachable', 'down')):
        ctx, pg = phone_page(b)
        ctx.route(re.compile(r'.*GeocodeServer/findAddressCandidates.*'), lambda r: r.fulfill(status=200, content_type='application/json', body='{"candidates":[]}'))
        ctx.route(re.compile(r'.*VotingAddresses/VA/MapServer/0/query.*'), (lambda v: lambda r: r.abort() if v == 'down' else r.fulfill(status=200, content_type='application/json', body='{"features":[]}'))(va))
        ctx.route(re.compile(r'https://geocoding\.geo\.census\.gov/.*'), (lambda m: lambda r: census(r, m))(match))
        pg.goto(BASE); pg.fill('#street', '1 Nowhere St'); pg.fill('#zip', '78701'); pg.click('#go')
        pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'lookup_failed')", timeout=15000)
        assert events(pg)[-1] == ['lookup_failed', {'reason': reason, 'layout': 'phone'}], events(pg)
        if va == 'down':
            expect(pg.locator('#status')).to_be_visible()
            assert 'couldn’t reach Travis County’s map server' in pg.inner_text('#status'), 'no longer stuck on "Finding your address"'
        ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE + '#s=not-a-real-payload')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'link_damaged')")
    assert events(pg)[-1] == ['link_damaged', {'kind': 'damaged', 'layout': 'phone'}]
    expect(pg.locator('#lookupmsg')).to_be_visible(); assert 'damaged' in pg.inner_text('#lookupmsg')
    frag = pg.evaluate("packFrag('s', { v: 1, n: 'Ana', c: 'abcd2345', g: 1, p: { 70: 0 } })"); ctx.close()
    ctx, pg = phone_page(b, init='delete window.DecompressionStream'); pg.goto(BASE + '#' + frag)   # an old browser
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'link_damaged')")
    assert events(pg)[-1] == ['link_damaged', {'kind': 'too_old', 'layout': 'phone'}], events(pg); ctx.close()

PA_LS_KEYS = "Object.keys(localStorage).filter(k => k.startsWith('ballotta.')).concat(Object.keys(sessionStorage).filter(k => k.startsWith('ballotta.')))"

@phone_test
def phone_counts_progress_sources_and_clearing(b):
    # Port of counts_progress_sources_and_clearing: progress milestones, source / directions / wait-times / print counts
    # from the phone's paper and views, and clearing from the Feedback & Info sheet (picks; everything, in this tab and
    # another; with storage blocked; Cancel keeps everything).
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); no_link_opens(pg)
    pg.evaluate("ballot.slice(0, Math.ceil(ballot.length / 4)).forEach(x => pick(x.c.id, '__skip'))")
    prog = lambda: [e[1] for e in events(pg) if e[0] == 'progress']
    assert prog() == [{'at': '25', 'reasons': '0', 'skipped': '6+', 'layout': 'phone'}], prog()
    pg.evaluate("ballot.forEach(x => { if (!current(x.c.id).length) pick(x.c.id, '__skip'); })")
    assert [p['at'] for p in prog()] == ['25', '50', '75', '100'], prog()
    assert pg.text_content('#ph-count') == '63 of 63 decided', pg.text_content('#ph-count')
    pg.evaluate("renderStored({ pr: '9', b: [1, 2, 3, 4], mode: 'saved' }, 'test')")                  # shown already decided: counts nothing
    assert len(prog()) == 4, ('a ballot shown already decided is not progress', prog())
    pg.evaluate("renderStored({ pr: '9', b: [210, 211, 212, 213], mode: 'saved' }, 'test'); pick('c210', '__skip')")
    assert len(prog()) == 5 and prog()[-1]['at'] == '25', ('a pick that crosses a milestone counts', prog())
    assert pg.evaluate("localStorage.getItem('ballotta.progress')") is None, 'nothing about progress is stored'
    pg.evaluate("renderStored(JSON.parse(localStorage.getItem('ballotta.ballot')), 'test')")
    pg.reload(); pg.wait_for_selector('body.dk-app-on'); pg.wait_for_timeout(500)
    assert names(pg).count('progress') == 0, 'a returning voter is not counted again (audit #1)'
    pg.evaluate("pick(ballot.find(x => current(x.c.id)[0] === '__skip').c.id, '__skip')")               # un-skip one: still over 75%
    pg.evaluate("pick(ballot.find(x => !current(x.c.id).length).c.id, '__skip')")                      # and decide it again: back to 100%
    assert names(pg).count('progress') == 0, 'milestones reached before the reload are noted when the ballot shows (Pass 2)'
    no_link_opens(pg); pa_open(pg, 'c001')
    pg.locator('#dk-paper a', has_text='League guide answers').first.click()
    pg.locator('#dk-paper a', has_text='Campaign site').first.click()
    src = [e[1] for e in events(pg) if e[0] == 'source_opened']
    assert src == [{'kind': 'league_guide', 'level': 'federal', 'layout': 'phone'}, {'kind': 'campaign_site', 'level': 'federal', 'layout': 'phone'}], src
    for href, kind in (('https://www.texastribune.org/x', 'news'), ('https://ballotpedia.org/x', 'reference'), ('https://votetravis.gov/x', 'official'), ('https://example.com/x', 'other')):
        pg.evaluate("h => { const a = document.createElement('a'); a.href = h; a.textContent = 'x'; a.id = 'tmp-a'; document.body.append(a); a.click(); a.remove(); }", href)
        assert events(pg)[-1] == ['source_opened', {'kind': kind, 'layout': 'phone'}], (href, events(pg)[-1])   # outside a race: no level
    pg.locator('#dk-paper a', has_text='League guide answers').first.click(button='middle')            # a middle click opens a link too
    assert events(pg)[-1] == ['source_opened', {'kind': 'league_guide', 'level': 'federal', 'layout': 'phone'}], events(pg)[-1]
    pa_view(pg, 'vote'); pg.click('#dk-paper [data-period="early"]')                              # from Oct 31 the page opens on Election Day
    pg.locator('#dk-paper a', has_text='Directions').first.click(); pg.locator('#dk-paper a', has_text='Check live wait times').click()
    assert events(pg)[-2:] == [['directions_opened', {'period': 'early', 'layout': 'phone'}], ['wait_times_opened', {'period': 'early', 'layout': 'phone'}]], events(pg)[-2:]
    pa_view(pg, 'crib'); pg.evaluate('window.print = () => {}'); pg.click('#dk-notes [data-act="print"]')
    assert events(pg)[-1] == ['crib_printed', {'two_col': 'no', 'hide_unopposed': 'no', 'layout': 'phone'}], events(pg)[-1]
    pg.once('dialog', lambda d: d.accept()); pa_menu(pg, 'Clear my picks')
    assert events(pg)[-1] == ['cleared', {'what': 'picks', 'layout': 'phone'}], events(pg)[-1]
    assert pg.text_content('#ph-count') == '0 of 63 decided' and pg.evaluate("Object.keys(picks).filter(k => current(k).length).length") == 0
    journey_check(pg, 'phone')
    assert pg.evaluate(PA_LS_KEYS), 'something is saved before clearing'
    pg.evaluate("localStorage.setItem('umami.disabled', '1'); localStorage.setItem('other.site', 'x')")   # not Ballotta's: must survive
    pg.evaluate("umami.track = (n, d) => sessionStorage.setItem('__last', JSON.stringify([n, d]))")   # survives the reload
    pg.once('dialog', lambda d: d.accept()); pa_menu(pg, 'Clear everything')
    pg.wait_for_function("!document.body.classList.contains('dk-app-on')"); pg.wait_for_load_state()
    assert pg.evaluate(PA_LS_KEYS) == [], pg.evaluate(PA_LS_KEYS)
    assert pg.evaluate("JSON.parse(sessionStorage.getItem('__last'))") == ['cleared', {'what': 'everything', 'layout': 'phone'}]
    expect(pg.locator('#start')).to_be_visible(); expect(pg.locator('#ph-bar')).to_be_hidden(); assert pg.evaluate('location.hash') == ''
    assert pg.evaluate("[localStorage.getItem('umami.disabled'), localStorage.getItem('other.site')]") == ['1', 'x'], 'only ballotta.* keys are cleared'
    ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pa_open(pg, 'c070')                   # another open tab doesn't write it back (audit #5)
    pg.locator('#dk-paper .dk-line', has_text='Qadri').click()
    pg2 = ctx.new_page(); pg2.goto(BASE); pg2.wait_for_selector('body.dk-app-on')
    pg2.evaluate('window.__mark = 1'); pa_relookup(pg); pg.wait_for_timeout(500)                   # a lookup elsewhere doesn't reload this tab
    assert pg2.evaluate('window.__mark') == 1, 'only Clear everything reloads other tabs (Pass 2)'
    pg.once('dialog', lambda d: d.accept()); pa_menu(pg, 'Clear everything'); pg.wait_for_load_state()
    pg2.wait_for_function("!document.body.classList.contains('dk-app-on')", timeout=5000)
    pg2.click('#go')
    assert pg2.evaluate(PA_LS_KEYS) == [], ('the other tab started fresh', pg2.evaluate(PA_LS_KEYS))
    ctx.close()
    ctx, pg = phone_page(b)                                                                       # storage blocked: Clear everything still clears (audit #4)
    ctx.add_init_script("for (const n of ['localStorage', 'sessionStorage']) Object.defineProperty(window, n, { get() { throw new DOMException('blocked', 'SecurityError'); } })")
    pg.goto(BASE); lookup_phone(pg)
    pg.once('dialog', lambda d: d.accept()); pa_menu(pg, 'Clear everything')
    pg.wait_for_function("!document.body.classList.contains('dk-app-on')", timeout=10000)
    ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg)                                       # asking first: Cancel keeps everything
    pg.once('dialog', lambda d: d.dismiss()); pa_menu(pg, 'Clear everything'); pg.wait_for_timeout(300)
    assert pg.evaluate("localStorage.getItem('ballotta.ballot')") and pg.is_visible('#ph-bar') and pg.is_visible('#dk-paper')
    ctx.close()

@phone_test
def phone_page_is_locked_down(b):
    # Port of page_is_locked_down (#36): the page under test carries the Content-Security-Policy before any script (only
    # its own scripts by hash, data only to the county and the counting service, frames only from this site) and sends
    # no referrer; a whole phone visit (friend link, lookup, a pick, Keep and Share from the phone's own buttons) and a
    # laptop visit trip nothing and send no referrer to the county; an injected script doesn't run.
    html = (ROOT / PAGE).read_text(encoding='utf-8')
    m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', html)
    assert m and html.index(m.group(0)) < html.index('<script'), 'a CSP meta tag before the first script'
    pol = dict((d.split(' ', 1) + [''])[:2] for d in m.group(1).split('; '))
    assert pol['default-src'] == "'none'" and pol['frame-src'] == "'self'" and pol['base-uri'] == "'none'" and pol['form-action'] == "'none'", pol
    assert pol['connect-src'] == "'self' https://taxmaps.traviscountytx.gov https://gateway.umami.is", pol['connect-src']   # 'self': the saved-copy bar's check (#73)
    srcs = pol['script-src'].split()
    assert srcs[0] == "'self'" and all(x.startswith("'sha256-") for x in srcs[1:]) and len(srcs) == 1 + html.count('<script>'), srcs
    assert '<meta name="referrer" content="no-referrer">' in html and html.index('name="referrer"') < html.index('<script')
    for wide in ((False, True) if HAS_DESK else (False,)):
        ctx, pg = (new_page(b, wide=True, csp=True) if wide else phone_page(b, csp=True)); pg.add_init_script(CSP_WATCH); refs = []
        pg.on('request', lambda r: refs.append((r.url, r.headers.get('referer'))) if 'traviscountytx.gov' in r.url else None)
        pg.goto(BASE)
        if wide:
            lookup_strict(pg, True)
            for v in ('glance', 'vote', 'crib', 'decide'): pg.click(f'#dk-views [data-view="{v}"]')
            pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]'); pg.keyboard.press('Escape')
        else:
            fresh_goto(pg, link('s', {'v': 1, 'n': 'Maya', 'c': 'abcd2349', 'g': 1, 'p': {'70': 0}})); poll(pg, "!document.getElementById('friend').classList.contains('hidden')")
            pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '78701'); pg.click('#go')
            poll(pg, "document.body.classList.contains('dk-app-on') && / of \\d+ decided$/.test(document.getElementById('ph-count').textContent)")
            pg.click('#ph-list'); pg.locator('.dk-row[data-row="c070"]').click(); pg.locator('#dk-paper .dk-line', has_text='Qadri').click()
            pg.click('#ph-list'); pg.click('#dk-keep'); poll(pg, "document.getElementById('d-keep').open"); pg.click('#d-keep [data-close]'); pg.click('#ph-done')
            pg.click('#dk-share'); poll(pg, "document.getElementById('d-share').open"); pg.click('#d-share [data-close]')
        pg.wait_for_timeout(500)
        assert pg.evaluate('window.__csp') == [], (wide, pg.evaluate('window.__csp'))
        assert refs and all(r is None for _, r in refs), ('no referrer to the county', refs[:2])
        pg.evaluate("() => { const s = document.createElement('script'); s.textContent = 'window.__pwned = 1'; document.body.appendChild(s); }")
        pg.wait_for_timeout(200)
        assert pg.evaluate('window.__pwned') is None and any(v.startswith('script-src') for v in pg.evaluate('window.__csp')), 'an injected script ran'
        ctx.close()

@phone_test
def phone_extra_pick_is_explained(b):
    # Port of extra_pick_is_explained (#33), phone half: on a "vote for up to 2" race, a third pick on the phone paper
    # changes nothing and says why under "Vote for up to 2" (a status); the note clears on the next pick, and when picks
    # are cleared from the Feedback & Info sheet. (The laptop half of the old test runs there unchanged; its keyboard
    # check has no phone equivalent: no shortcuts on a phone.)
    st = json.dumps({'pr': '999', 'b': [113], 'mode': 'saved', 'at': 0, 'pt': None})
    msg = 'You can pick up to 2. Unpick one first.'
    ctx, pg = phone_page(b); pg.goto(BASE)
    pg.evaluate('s => localStorage.setItem("ballotta.ballot", s)', st); pg.reload(); pg.wait_for_selector('body.dk-app-on')
    opts = pg.evaluate('optionsOf(BYID.c113)')
    assert pg.evaluate("document.getElementById('dk-paper').dataset.c") == 'c113' and 'Vote for up to 2' in pg.inner_text('#dk-paper')
    line = lambda i: pg.locator('#dk-paper .dk-line').nth(i)
    note = pg.locator('#dk-paper [data-limit="c113"]')
    line(0).click(); line(1).click(); expect(note).to_have_text('')
    line(2).click()
    assert pg.evaluate("current('c113')") == opts[:2], pg.evaluate("current('c113')")
    expect(note).to_have_text(msg); expect(note).to_be_visible(); assert note.get_attribute('role') == 'status'
    assert line(2).get_attribute('aria-pressed') == 'false'
    line(0).click(); expect(note).to_have_text('')
    line(2).click(); assert pg.evaluate("current('c113')") == [opts[1], opts[2]]
    line(0).click(); expect(note).to_have_text(msg)
    pg.once('dialog', lambda d: d.accept()); pa_menu(pg, 'Clear my picks')
    assert pg.evaluate("current('c113')") == []; expect(note).to_have_text('')
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def phone_new_day_keeps_the_vote_list_and_focus(b):
    # Port of phone_new_day_keeps_focus_on_a_directions_link (#47), focus half: in the phone's Where to vote view, a new
    # day that doesn't change the voting period leaves the vote-center list as it was, and a focused Directions link
    # keeps focus. (The dated note half: phone_wait_times_note_says_when_it_fills_in.) Named apart from the old test, which keeps its name.
    import datetime as dt
    ctx, pg = phone_page(b); pg.clock.install(time=dt.datetime(2026, 10, 18, 23, 58)); pg.goto(BASE)
    saved_ballot(pg, [70, 71], [-97.743, 30.272]); pg.wait_for_selector('body.dk-app-on')
    pa_view(pg, 'vote')
    assert pg.get_attribute('#dk-paper [data-period="early"]', 'aria-pressed') == 'true'
    link3 = pg.locator('#dk-paper a', has_text='Directions').nth(2); link3.focus(); href = link3.get_attribute('href')
    pg.clock.run_for(5 * 60 * 1000)
    assert pg.evaluate('new Date().getDate()') == 19, 'precondition: the day moved on'
    assert pg.evaluate('document.activeElement.getAttribute("href")') == href, pg.evaluate('document.activeElement.outerHTML.slice(0, 120)')
    assert pg.locator('.ph-mapfold').count() == 1
    ctx.close()

@phone_test
def phone_wait_times_note_says_when_it_fills_in(b):
    # Port of phone_new_day_keeps_focus_on_a_directions_link (#47), dated-note half. Today's phone page says, under
    # "Check live wait times", that the county's map "fills in once voting starts Oct 19", and drops it on the new day
    # (with no redraw of the list). The phone layout's Where to vote view must say the same.
    import datetime as dt
    ctx, pg = phone_page(b); pg.clock.install(time=dt.datetime(2026, 10, 18, 23, 58)); pg.goto(BASE)
    saved_ballot(pg, [70, 71], [-97.743, 30.272]); pg.wait_for_selector('body.dk-app-on')
    pa_view(pg, 'vote')
    assert 'fills in once voting starts' in pg.inner_text('#dk-paper'), 'the phone\'s Where to vote view doesn\'t say the wait-times map is empty until Oct 19'
    link3 = pg.locator('#dk-paper a', has_text='Directions').nth(2); link3.focus(); href = link3.get_attribute('href')
    pg.clock.run_for(5 * 60 * 1000)
    assert 'fills in once voting starts' not in pg.inner_text('#dk-paper'), 'the note stayed after voting started'
    assert pg.evaluate('document.activeElement.getAttribute("href")') == href
    ctx.close()

@desk_test
def desk_wait_times_note_says_when_it_fills_in(b):
    # The laptop's Where to vote view says the same as the phone's (the old phone page always did): the county's
    # wait-times map is empty until voting starts Oct 19, and the note goes on the day.
    import datetime as dt
    for when, shown in ((dt.datetime(2026, 10, 18, 12, 0), True), (dt.datetime(2026, 10, 19, 9, 0), False)):
        ctx, pg = new_page(b, wide=True); pg.clock.install(time=when); pg.goto(BASE)
        saved_ballot(pg, [70, 71], [-97.743, 30.272]); pg.wait_for_selector('body.dk-app-on')
        pg.click('#dk-views [data-view="vote"]')
        assert ('fills in once voting starts Oct 19' in pg.inner_text('#dk-paper')) == shown, (when, pg.inner_text('#dk-paper')[:400])
        ctx.close()

@phone_test
def phone_junk_and_hook_failures_never_break_the_lookup(b):
    # Port of desk_failures_never_break_the_phone_flow. On the phone layout the laptop code *is* the phone's app, so "laptop
    # code failing leaves the phone page working" no longer applies as such; what still does: a non-text reason and a
    # saved ballot in storage, with a friend's link, never throw on a phone; a layout hook that throws during a lookup is
    # not reported as a county outage, the lookup is still counted, and the crib sheet still renders. The laptop half of
    # the old test (junk storage still opens the laptop app) is kept as it was.
    ctx, pg = phone_page(b, init=JUNK_STORAGE)
    fresh_goto(pg, link('s', DESK_FRIEND)); pg.wait_for_selector('.dk-fchip', timeout=5000)        # a non-text reason in storage, a saved ballot
    assert pg.text_content('#ph-count') == '0 of 2 decided', pg.text_content('#ph-count')
    pa_open(pg, 'c001'); assert pg.input_value('#dk-w') == '', pg.input_value('#dk-w')
    pa_relookup(pg); pg.wait_for_function("/ of 63 decided$/.test(document.getElementById('ph-count').textContent)", timeout=30000)
    assert pg.errs == [], pg.errs
    pa_menu(pg, 'Change address'); expect(pg.locator('#start')).to_be_visible()
    pg.evaluate("() => { for (const k of ['ballot', 'refresh', 'cribSkip']) desk[k] = () => { throw new Error('boom'); }; }")   # a layout hook that throws
    pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '78701'); pg.click('#go')
    pg.wait_for_function("(window.__events||[]).filter(e => e[0] === 'ballot_found').length === 2", timeout=30000)
    pg.wait_for_timeout(300)
    assert 'United States Senator' in pg.text_content('#crib') and pg.errs == [], pg.errs                    # the crib sheet still renders
    assert 'lookup_failed' not in names(pg) and pg.locator('#status.bad').count() == 0, 'a layout-code failure is not reported as a county outage'
    ctx.close()
    ctx, pg = new_page(b, wide=True); pg.add_init_script(JUNK_STORAGE); pg.goto(BASE)
    pg.wait_for_selector('body.dk-app-on'); assert pg.locator('.dk-row').count() == 2
    ctx.close()

@phone_test
def phone_takes_no_laptop_shortcuts(b):
    # Port of desk_stays_quiet_on_phones. By design the phone layout is the laptop app folded up (plan, "How it's
    # built"), so its header and paper show, and a friend's compare is counted on a phone too (difference 3; checked in
    # phone_friend_link_landing_then_inline). What still applies (difference 12): no keyboard shortcuts, and no key
    # hints, below 1024px, even with focus on the ballot paper.
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, [1, 70, 71]); pg.wait_for_selector('body.dk-app-on')
    assert h1(pg) == 'United States Senator'
    assert pg.locator('.kbd:visible').count() == 0, 'key hints on a phone'
    for where in ('BODY', 'dk-paper'):
        if where == 'dk-paper': pg.focus('#dk-paper')
        else: pg.evaluate('document.activeElement && document.activeElement.blur()')
        for k in ('1', 's', 'j', 'n', 'r', '/'): pg.keyboard.press(k)
        assert cur(pg, 'c001') == [] and h1(pg) == 'United States Senator', (where, cur(pg, 'c001'), h1(pg))
        assert focused(pg) not in ('dk-q', 'dk-w'), (where, focused(pg))
    assert 'shortcut_used' not in names(pg), events(pg)
    ctx.close()

@phone_test
def phone_resize_keeps_picks_and_reasons_in_step(b):
    # Port of desk_resize_keeps_layouts_in_step: a pick made on a laptop shows on the phone after narrowing; a pick and a
    # reason made on the phone show on the laptop after widening.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c001"]'); pg.locator('.dk-line', has_text='Ted Brown').click()
    pg.set_viewport_size(PHONE); pg.wait_for_timeout(150)
    expect(pg.locator('#ph-bar')).to_be_visible()
    assert pg.text_content('#ph-count') == '1 of 63 decided', pg.text_content('#ph-count')
    assert pg.locator('#dk-paper .dk-line', has_text='Ted Brown').get_attribute('aria-pressed') == 'true'
    pg.fill('#dk-w', 'Typed on the phone')
    pa_open(pg, 'c070'); pg.locator('#dk-paper .dk-line', has_text='Qadri').click()
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(150)
    expect(pg.locator('.dk-rail')).to_be_visible()
    assert 'Qadri' in pg.inner_text('.dk-row[data-row="c070"]') and pg.inner_text('#dk-count') == '2 of 63 decided', pg.inner_text('#dk-count')
    pg.click('.dk-row[data-row="c001"]')
    pg.wait_for_function("document.getElementById('dk-w').value === 'Typed on the phone'", timeout=3000)
    ctx.close()

# ---------------------------------------------------------------- ports of today's phone-page tests to the phone layout (B)
# Each guards what the old test (named in its first comment line) guarded, on the page a phone gets once the phone layout
# is live. Where the new layout behaves differently by design, the new design is asserted and the comment says so.
def pb_go(pg, cid):                                         # to a contest by its id, through the "Your ballot" sheet
    pg.click('#ph-list'); pg.fill('#dk-q', ''); pg.locator(f'.dk-row[data-row="{cid}"]').click()
    expect(pg.locator('.dk-rail')).to_be_hidden()
    assert pg.evaluate("document.getElementById('dk-paper').dataset.c") == cid, (cid, h1(pg))

def pb_line(pg, label): return pg.locator('#dk-paper .dk-line', has_text=label).first

def pb_make_picks(pg):                                      # make_picks(), made the way a phone voter makes them
    pb_go(pg, 'c070'); pb_line(pg, 'Qadri').click(); pg.fill('#dk-w', 'Knows the district')
    pb_go(pg, 'c071'); pb_line(pg, 'For').click(); pg.fill('#dk-w', 'More shade and pools near us.')
    pb_go(pg, 'c001'); pb_line(pg, 'Ted Brown').click()
    if pg.evaluate("ballot.some(x => x.c.id === 'c002')"): pb_go(pg, 'c002'); pg.click('#dk-paper .skip')

def pb_ids(pg): return pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)')
def pb_decide(pg, ids): pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids)
def pb_stored(pg): return pg.evaluate("Object.keys(localStorage).filter(k => k.startsWith('ballotta.')).concat(Object.keys(sessionStorage).filter(k => k.startsWith('ballotta.')))")

@phone_test
def phone_keep_link_round_trip(b):
    # Port of keep_link_round_trip: Keep my picks (in the "Your ballot" sheet on a phone) makes a short v2 link that
    # carries picks and reasons to a fresh phone; the fragment leaves the address bar and never rides on a request.
    sent = []
    ctx, pg = phone_page(b, sent); pg.goto(BASE); lookup_phone(pg); pb_make_picks(pg)
    decided = pg.text_content('#ph-count')
    pg.click('#ph-list'); pg.click('#dk-keep'); pg.wait_for_selector('#d-keep[open]')
    assert 'live only in this browser' in pg.inner_text('#keepcount'), pg.inner_text('#keepcount')
    pg.click('#keep-copy')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'keep_created')")
    url = pg.inner_text('#keep-out'); frag = url.split('#', 1)[1]
    assert re.fullmatch(r'k2[A-Za-z0-9_-]{16,}', frag), url                 # v2: nothing after '#' that chat apps cut at
    assert ['keep_created', {'via': 'copy', 'layout': 'phone'}] in events(pg), events(pg)
    assert pg.errs == [], pg.errs
    ctx.close()
    sent2 = []
    ctx, pg = phone_page(b, sent2); pg.goto(url)
    assert pg.evaluate('location.hash') == '', 'fragment must be stripped from the address bar'
    pg.wait_for_selector('#d-restore[open]')
    s = pg.inner_text('#restoresum'); assert 'Precinct 300' in s and 'of 63' in s, s
    pg.click('#restore-go'); pg.wait_for_selector('body.dk-app-on')
    expect(pg.locator('#ph-bar')).to_be_visible()
    assert pg.text_content('#ph-count') == decided and decided.endswith(' of 63 decided'), (decided, pg.text_content('#ph-count'))
    pb_go(pg, 'c070')
    assert pb_line(pg, 'Qadri').get_attribute('aria-pressed') == 'true' and pg.input_value('#dk-w') == 'Knows the district', pg.input_value('#dk-w')
    pb_go(pg, 'c071'); assert pg.input_value('#dk-w') == 'More shade and pools near us.', pg.input_value('#dk-w')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'keep_restored')")
    assert ['keep_restored', {'layout': 'phone'}] in events(pg), events(pg)
    for u in sent + sent2:
        assert frag[2:40] not in u and 'shade' not in urllib.parse.unquote(u), u
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def phone_share_friend_compare_and_events(b):
    # Port of share_friend_compare_and_events: the Share sheet (from the header's Share my picks on a phone) with its
    # section and reason switches; the friend's phone shows the picks, counts the open once per browser, and after the
    # friend's own lookup compares them. New design: no Compare button (the landing says what comes next, "See Maya's
    # picks beside yours"); after the lookup Maya's picks sit inline, race by race, with the "You and Maya" counts.
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pb_make_picks(pg)
    pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]')
    assert names(pg).count('share_sheet_open') == 1
    toggles = pg.locator('#sharesecs input')
    assert toggles.count() >= 2 and all(t.is_checked() for t in toggles.all()), 'every section starts on'
    assert pg.is_checked('#sharewhy'), 'reasons start on'
    pg.fill('#sharename', 'Maya')
    pg.locator('#sharesecs .sw', has_text='Federal').locator('input').click()                 # leave Federal out
    summ = pg.inner_text('#sharesum'); assert 'They’ll see 2 picks and 2 reasons' in summ, summ
    pg.click('#share-go')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'share_created')")
    url = pg.inner_text('#share-out')
    ev = [e for e in events(pg) if e[0] == 'share_created'][0][1]
    assert ev['reasons'] == 'yes' and ev['picks'] == '1-5' and ev['via'] == 'copy' and ev['generation'] == 1 and re.fullmatch(r'[a-z2-9]{8}', ev['link']) and ev['layout'] == 'phone', ev
    assert 'federal' not in ev['sections'] and 'city' in ev['sections'], ev
    pg.click('#sharewhy')                                   # reasons off: the link must carry none
    assert 'and 0 reasons' in pg.inner_text('#sharesum')
    pg.click('#share-go')
    pg.wait_for_function("(window.__events||[]).filter(e => e[0] === 'share_created').length === 2")
    o = pg.evaluate("unpackFrag(document.getElementById('share-out').textContent.split('#')[1])")
    assert not o.get('w') and len(o['p']) == 2, o
    assert [e for e in events(pg) if e[0] == 'share_created'][1][1]['reasons'] == 'no'
    assert pg.errs == [], pg.errs
    ctx.close()
    sent = []
    ctx, pg = phone_page(b, sent); pg.goto(url)
    assert pg.evaluate('location.hash') == ''
    pg.wait_for_selector('#friend:not(.hidden)')
    f = pg.inner_text('#friend')
    assert 'Maya shared 2 picks' in f and 'Qadri' in f and '“More shade and pools near us.”' in f and 'Ted Brown' not in f, f
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'share_opened')")
    op = [e for e in events(pg) if e[0] == 'share_opened'][0][1]
    assert op == {'generation': 1, 'has_picks': 'no', 'link': ev['link'], 'layout': 'phone'}, op
    pg.reload(); pg.wait_for_selector('#friend:not(.hidden)')       # survives a refresh, and is not double-counted
    pg.wait_for_timeout(1500)
    assert names(pg).count('share_opened') == 0
    pg2 = ctx.new_page(); pg2.goto(url)   # same link, new tab
    pg2.wait_for_selector('#friend:not(.hidden)'); pg2.wait_for_timeout(1500)
    assert names(pg2).count('share_opened') == 0, events(pg2)
    pg2.close()
    expect(pg.locator('#f-cmp')).to_be_hidden(); expect(pg.locator('.dk-fcta')).to_be_visible()
    assert 'See Maya’s picks beside yours' in pg.inner_text('.dk-fcta'), pg.inner_text('.dk-fcta')
    lookup_phone(pg)
    pb_go(pg, 'c070'); assert 'Maya picked this' in pg.inner_text('#dk-paper .dk-lw:has(.dk-fp)'), pg.inner_text('#dk-paper')
    assert 'Qadri' in pg.inner_text('#dk-paper .dk-lw:has(.dk-fp)')
    pb_go(pg, 'c071'); assert 'More shade and pools near us.' in pg.inner_text('#dk-paper'), 'their reason shows beside their pick'
    assert pg.inner_text('#ph-fold').startswith('You and Maya · '), pg.inner_text('#ph-fold')
    pg.click('#ph-fold'); c = pg.inner_text('#dk-notes').lower()
    assert 'you and maya' in c and 'you haven’t picked' in c, c
    pg.wait_for_function("['share_own_ballot','share_compare'].every(n => (window.__events||[]).some(e => e[0] === n))")
    assert [e for e in events(pg) if e[0] == 'share_compare'] == [['share_compare', {'layout': 'phone'}]], events(pg)
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.gen'))") == 2
    for e in events(pg):            # nothing personal ever rides along
        blob = json.dumps(e)
        assert 'Qadri' not in blob and 'Maya' not in blob and '300' not in blob and 'Guadalupe' not in blob, blob
    for u in sent:
        assert url.split('#', 1)[1][2:40] not in u and 'Maya' not in u, u
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def phone_double_tap_share_counts_once(b):
    # Port of double_tap_share_counts_once: a second tap on Create link while the phone's own share sheet is still open
    # makes no second link and counts one share.
    ctx, pg = phone_page(b, init="navigator.share = () => new Promise(r => setTimeout(r, 800));")   # a share sheet that stays open a moment
    pg.goto(BASE); lookup_phone(pg); pb_line(pg, 'Ted Brown').click()
    pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]'); pg.fill('#sharename', 'Dee'); pg.wait_for_timeout(200)
    pg.tap('#share-go'); pg.tap('#share-go', force=True); pg.wait_for_timeout(1500)
    made = [e for e in events(pg) if e[0] == 'share_created']
    assert len(made) == 1 and made[0][1]['via'] == 'share' and made[0][1]['layout'] == 'phone', made
    ctx.close()

@phone_test
def phone_keep_link_limits(b):
    # Port of audit_a4_a9_keep_link_limits: a keep link over the size cap, or with an empty ballot, is "damaged" on the
    # phone's landing form (no restore sheet); duplicate and unknown contests are dropped; loading over a ballot from
    # another precinct warns first, with "Not now" focused.
    ctx, pg = phone_page(b)
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1] * 5000, 'p': {}}))
    expect(pg.locator('#lookupmsg')).to_be_visible()
    assert 'damaged' in pg.inner_text('#lookupmsg') and pg.locator('#d-restore[open]').count() == 0                   # A4 over cap
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [], 'p': {'1': 0}}))
    expect(pg.locator('#lookupmsg')).to_be_visible()
    assert 'damaged' in pg.inner_text('#lookupmsg') and pg.locator('#d-restore[open]').count() == 0                   # A9 empty ballot
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, -1, 1, 6], 'p': {'1': 1}}))
    pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go'); pg.wait_for_selector('body.dk-app-on')
    assert pg.evaluate('ballot.map(x => x.c.id)') == ['c001', 'c006'] and pg.locator('.dk-row').count() == 2, pg.evaluate('ballot.map(x => x.c.id)')   # A4 de-duplicated
    assert pg.text_content('#ph-count') == '1 of 2 decided', pg.text_content('#ph-count')
    assert pg.errs == [], pg.errs
    ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pb_line(pg, 'Ted Brown').click()
    fresh_goto(pg, link('k', {'v': 1, 'pr': '999', 'b': [1], 'p': {}}))
    pg.wait_for_selector('#d-restore[open]')
    w = pg.inner_text('#restorewarn')
    assert 'Precinct 999' in w and 'Precinct 300' in w and 'picks and reasons' in w, w                                 # A9
    assert pg.evaluate('document.activeElement.textContent.trim()') == 'Not now'                                         # A13
    ctx.close()

@phone_test
def phone_share_sheet_padding_tap_keeps_it_open(b):
    # Port of audit_a6_sheet_padding_tap_keeps_it_open: on a phone the Share sheet rises from the bottom; a tap on its
    # padding keeps it open, a tap on the dimmed page above closes it.
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pb_line(pg, 'Ted Brown').click()
    pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]'); r = pg.locator('#d-share').bounding_box()
    assert r['y'] > 40 and abs(r['y'] + r['height'] - PHONE['height']) < 2, ('a bottom sheet with page above it', r)
    pg.mouse.click(r['x'] + 6, r['y'] + r['height'] / 2)                       # inside the sheet's left padding
    assert pg.locator('#d-share[open]').count() == 1
    pg.touchscreen.tap(r['x'] + 6, r['y'] + r['height'] / 2 + 20)             # and a finger there
    assert pg.locator('#d-share[open]').count() == 1
    pg.touchscreen.tap(r['x'] + 20, max(5, r['y'] - 40))                       # the backdrop above it
    assert pg.locator('#d-share[open]').count() == 0
    pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]')
    pg.mouse.click(r['x'] + 20, max(5, r['y'] - 40))
    assert pg.locator('#d-share[open]').count() == 0
    ctx.close()

PB_NUDGE = 'Your picks live only in this browser, and phones can clear them. Send yourself a backup link.'

@phone_test
def phone_backup_nudge_after_fifth_pick(b):
    # Port of backup_nudge_after_fifth_pick (#48), phone half (the laptop half: desk_backup_nudge_after_fifth_pick):
    # after the 5th pick a one-time floating card suggests a backup link ("Send myself a link" opens Keep my picks; "Not
    # now" puts it away); once more at 25 picks if no link was ever kept; never after a link is kept. Counted.
    # New design for focus: with no control to go back to, Not now puts focus on the ballot paper and Send myself a link
    # returns it to the "Your ballot" button (where Keep my picks lives on a phone), not to today's a-keep.
    nums = list(range(1, 41))
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('body.dk-app-on')
    ids = pb_ids(pg); card = pg.locator('#dk-nudge')
    pb_decide(pg, ids[0:4]); expect(card).to_be_hidden()
    pg.evaluate('id => pick(id, "__skip")', ids[4]); expect(card).to_be_hidden()            # a skip isn't a pick (Pass 1)
    pg.evaluate('id => pick(id, "__skip")', ids[4])
    top = pg.evaluate('document.getElementById("dk-paper").getBoundingClientRect().top')
    pb_decide(pg, ids[4:5]); expect(card).to_be_visible(); expect(card.locator('[role="status"]')).to_have_text(PB_NUDGE)
    expect(pg.locator('#nudge')).to_be_hidden()                                             # one card, the phone layout's
    assert pg.evaluate('document.getElementById("dk-paper").getBoundingClientRect().top') == top, 'the card pushed the page (Lane: it floats)'
    assert card.evaluate('e => getComputedStyle(e).position') == 'fixed'
    assert ['backup_nudge', {'at': '5', 'action': 'shown', 'layout': 'phone'}] in events(pg), events(pg)
    card.locator('[data-nudge="dismiss"]').click(); expect(card).to_be_hidden()
    assert focused(pg) == 'dk-paper', ('Not now: focus on the paper', focused(pg))
    pb_decide(pg, ids[5:24]); expect(card).to_be_hidden()
    pb_decide(pg, ids[24:25]); expect(card).to_be_visible()
    card.locator('[data-nudge="keep"]').click(); pg.wait_for_selector('#d-keep[open]'); expect(card).to_be_hidden()
    assert [e[1]['action'] for e in events(pg) if e[0] == 'backup_nudge'] == ['shown', 'dismiss', 'shown', 'keep'], events(pg)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    assert focused(pg) == 'dk-paper', ('Keep returns focus where the visitor was (Pass 1, 2)', focused(pg))
    pg.reload(); pg.wait_for_selector('body.dk-app-on')
    pb_decide(pg, ids[25:30]); expect(pg.locator('#dk-nudge')).to_be_hidden()               # each card once per browser
    ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('body.dk-app-on')   # nothing focused when it shows
    ids = pb_ids(pg); card = pg.locator('#dk-nudge')
    pb_decide(pg, ids[:5]); expect(card).to_be_visible()
    card.locator('[data-nudge="keep"]').click(); pg.wait_for_selector('#d-keep[open]'); pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    assert focused(pg) == 'ph-list', ('Keep returns focus to the "Your ballot" button', focused(pg))
    ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('body.dk-app-on')
    ids = pb_ids(pg); pb_decide(pg, ids[:2])
    pg.click('#ph-list'); pg.click('#dk-keep'); pg.click('#keep-copy'); pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'keep_created')")
    pg.click('#d-keep [data-close]'); pg.click('#ph-done')
    pb_decide(pg, ids[2:30]); expect(pg.locator('#dk-nudge')).to_be_hidden()                # already kept a link
    ctx.close()
    # Pass 1: a card shown is remembered (an ignored card doesn't come back next visit); Not now at 25+ picks retires the
    # 25 card too.
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('body.dk-app-on')
    ids = pb_ids(pg); card = pg.locator('#dk-nudge')
    pb_decide(pg, ids[0:5]); expect(card).to_be_visible()
    pg.reload(); pg.wait_for_selector('body.dk-app-on'); pb_decide(pg, ids[5:6]); expect(card).to_be_hidden()
    pb_decide(pg, ids[6:30]); expect(card).to_be_visible(); card.locator('[data-nudge="dismiss"]').click(); pb_decide(pg, ids[30:31]); expect(card).to_be_hidden()
    ctx.close()
    # Pass 2, 3: a pick made from the keyboard gets focus back after Not now; a pick whose contest was left since sends
    # focus to the paper (today's page: Keep my picks); with the card up, the paper's last control is not under it; no
    # room is reserved on paper.
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('body.dk-app-on')
    ids = pb_ids(pg); card = pg.locator('#dk-nudge')
    pb_decide(pg, ids[:4])
    pb_go(pg, ids[4]); pg.locator('#dk-paper .dk-line').first.focus(); pg.keyboard.press('Enter'); expect(card).to_be_visible()
    card.locator('[data-nudge="dismiss"]').focus(); pg.keyboard.press('Enter'); expect(card).to_be_hidden()
    assert pg.evaluate("[document.activeElement.dataset.c, document.activeElement.getAttribute('aria-pressed')]") == [ids[4], 'true'], pg.evaluate('document.activeElement.outerHTML.slice(0, 80)')
    pb_decide(pg, ids[5:24])
    pb_go(pg, ids[24]); pg.locator('#dk-paper .dk-line').first.focus(); pg.keyboard.press('Enter'); expect(card).to_be_visible()
    pg.click('#ph-next'); assert pg.evaluate("document.getElementById('dk-paper').dataset.c") != ids[24]   # left that contest (Pass 3)
    card.locator('[data-nudge="dismiss"]').focus(); pg.keyboard.press('Enter'); expect(card).to_be_hidden()
    assert focused(pg) == 'dk-paper', focused(pg)
    pg.evaluate("localStorage.removeItem('ballotta.nudge')"); pg.evaluate('id => pick(id, optionsOf(BYID[id])[0])', ids[25]); expect(card).to_be_visible()
    pg.evaluate('window.scrollTo(0, document.body.scrollHeight)'); pg.wait_for_timeout(200)
    hit = pg.evaluate("""() => { const all = [...document.querySelectorAll('#dk-desk a[href], #dk-desk button, #dk-desk textarea, #dk-desk input')].filter(e => e.getClientRects().length && !e.closest('#dk-nudge'));
        const l = all[all.length - 1], r = l.getBoundingClientRect(), e = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return [l.id || l.tagName, !!e && (e === l || l.contains(e))]; }""")
    assert hit[1], ('the paper\'s last control is under the card', hit)
    pg.emulate_media(media='print')
    assert pg.evaluate('getComputedStyle(document.body).paddingBottom') == '0px' and card.is_hidden(), 'no room reserved on paper, no card printed (Pass 3)'
    pg.emulate_media(media='screen')
    ctx.close()
    # Pass 2: a returning voter with 5+ picks who makes a skip sees no card (a real pick does); a 5 card left up to 30
    # picks and then put away doesn't bring the 25 card.
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('body.dk-app-on')
    ids = pb_ids(pg); card = pg.locator('#dk-nudge')
    pg.evaluate("ids => localStorage.setItem('ballotta.picks', JSON.stringify(Object.fromEntries(ids.map(id => [id, [optionsOf(BYID[id])[0]]]))))", ids[:6])
    pg.reload(); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate('id => pick(id, "__skip")', ids[6]); expect(card).to_be_hidden()
    pg.evaluate('id => pick(id, optionsOf(BYID[id])[0])', ids[7]); expect(card).to_be_visible()
    pb_decide(pg, ids[8:31]); expect(card).to_be_visible()
    card.locator('[data-nudge="dismiss"]').click(); pg.evaluate('id => pick(id, optionsOf(BYID[id])[0])', ids[31]); expect(card).to_be_hidden()
    ctx.close()
    # Clear my picks (in the Feedback & Info sheet) puts the card away.
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('body.dk-app-on')
    ids = pb_ids(pg); pb_decide(pg, ids[:5]); card = pg.locator('#dk-nudge'); expect(card).to_be_visible()
    pg.once('dialog', lambda d: d.accept()); pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Clear my picks').click()
    expect(card).to_be_hidden(); assert pg.text_content('#ph-count') == f'0 of {len(nums)} decided', pg.text_content('#ph-count')
    assert pg.errs == [], pg.errs
    ctx.close()

@desk_test
def desk_backup_nudge_after_fifth_pick(b):
    # The laptop half of backup_nudge_after_fifth_pick (#48), which is skipped wherever the phone layout exists.
    nums = list(range(1, 41))
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('body.dk-app-on')
    ids = pb_ids(pg); card = pg.locator('#dk-nudge')
    pb_decide(pg, ids[0:4]); expect(card).to_be_hidden()
    pg.evaluate('id => pick(id, "__skip")', ids[4]); expect(card).to_be_hidden()            # a skip isn't a pick (Pass 1)
    pg.evaluate('id => pick(id, "__skip")', ids[4])
    top = pg.evaluate('document.getElementById("dk-paper").getBoundingClientRect().top')
    pb_decide(pg, ids[4:5]); expect(card).to_be_visible(); expect(card.locator('[role="status"]')).to_have_text(PB_NUDGE)
    assert pg.evaluate('document.getElementById("dk-paper").getBoundingClientRect().top') == top, 'the card pushed the page (Lane: it floats)'
    assert card.evaluate('e => getComputedStyle(e).position') == 'fixed'
    assert ['backup_nudge', {'at': '5', 'action': 'shown', 'layout': 'laptop'}] in events(pg), events(pg)
    card.locator('[data-nudge="dismiss"]').click(); expect(card).to_be_hidden()
    assert pg.evaluate('document.activeElement.id') == 'dk-paper', 'focus back on the paper (Pass 1)'
    pb_decide(pg, ids[5:24]); expect(card).to_be_hidden()
    pb_decide(pg, ids[24:25]); expect(card).to_be_visible()
    card.locator('[data-nudge="keep"]').click(); pg.wait_for_selector('#d-keep[open]'); expect(card).to_be_hidden()
    assert [e[1]['action'] for e in events(pg) if e[0] == 'backup_nudge'] == ['shown', 'dismiss', 'shown', 'keep'], events(pg)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
    assert pg.evaluate('document.activeElement.id') == 'dk-paper', 'Keep returns focus where the visitor was (Pass 1, 2)'
    pg.reload(); pg.wait_for_selector('body.dk-app-on')
    pb_decide(pg, ids[25:30]); expect(pg.locator('#dk-nudge')).to_be_hidden()               # each card once per browser
    ctx.close()
    ctx, pg = new_page(b, wide=True); pg.set_viewport_size({'width': 1024, 'height': 640}); pg.goto(BASE); saved_ballot(pg, nums)   # Pass 2
    pg.wait_for_selector('body.dk-app-on'); ids = pb_ids(pg)
    pb_decide(pg, ids[:5]); expect(pg.locator('#dk-nudge')).to_be_visible()
    pg.focus('#dk-print'); pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
    hit = pg.evaluate("() => { const a = document.activeElement, r = a.getBoundingClientRect(), e = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return [a.dataset.act, e === a || a.contains(e)]; }")
    assert hit == ['print', True], ('the focused Print button is under the card', hit)
    ctx.close()

@phone_test
def phone_persistent_storage_asked_at_first_pick(b):
    # Port of persistent_storage_asked_at_first_pick (#49): at the first pick on the paper the page asks the browser to
    # keep its data (navigator.storage.persist), once, and not if it's already kept; nothing is asked before a pick.
    stub = ("window.__persist = 0; window.__persisted = %s; Object.defineProperty(navigator, 'storage', { configurable: true, value: {"
            " persisted: () => { window.__checked = (window.__checked || 0) + 1; return Promise.resolve(window.__persisted); },"
            " persist: () => { window.__persist++; return Promise.resolve(true); } } });")
    for already, want in ((False, 1), (True, 0)):
        ctx, pg = phone_page(b, init=stub % ('true' if already else 'false')); pg.goto(BASE)
        saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on'); pg.wait_for_timeout(200)
        assert pg.evaluate('window.__persist') == 0 and not pg.evaluate('window.__checked'), 'asked before any pick'
        pb_go(pg, 'c070'); pb_line(pg, 'Qadri').click(); pg.fill('#dk-w', 'Knows the district')
        pb_go(pg, 'c071'); pb_line(pg, 'For').click(); pg.wait_for_timeout(200)
        assert pg.evaluate('window.__persist') == want and pg.evaluate('window.__checked') == 1, (already, pg.evaluate('[window.__persist, window.__checked]'))
        ctx.close()

@phone_test
def phone_can_clear_everything_from_the_menu(b):
    # Port of phone_can_clear_everything_from_the_footer (#42): someone who only opened a friend's link (no ballot of
    # their own) can still clear what Ballotta stored. New design: the phone layout has no footer; Feedback & Info is on
    # the landing page and in the app, and its sheet lists the laptop menu's "Clear everything on this device…" (always
    # listed, as on a laptop, rather than shown only while this browser holds something).
    ctx, pg = phone_page(b); pg.goto(BASE)
    item = pg.locator('#ph-mitems button', has_text='Clear everything on this device')
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Maya', 'c': 'abcd2347', 'g': 1, 'p': {'70': 0}}))
    pg.wait_for_selector('#friend:not(.hidden)'); assert pb_stored(pg), 'precondition: the friend link stored something'
    expect(pg.locator('#reset-all-foot')).to_be_hidden(); expect(pg.locator('#dk-help')).to_be_visible()
    pg.click('#dk-help'); pg.wait_for_selector('#ph-menu[open]'); expect(item).to_be_visible()
    pg.once('dialog', lambda d: d.accept()); item.click()
    pg.wait_for_function("!Object.keys(localStorage).some(k => k.startsWith('ballotta.')) && !Object.keys(sessionStorage).some(k => k.startsWith('ballotta.'))", timeout=5000)
    pg.wait_for_load_state(); expect(pg.locator('#friend')).to_be_hidden(); expect(pg.locator('#start')).to_be_visible()
    assert pb_stored(pg) == [], pb_stored(pg)
    lookup_phone(pg); pg.reload(); pg.wait_for_selector('body.dk-app-on')                     # a later visit, from the app
    pg.click('#dk-help'); pg.wait_for_selector('#ph-menu[open]'); expect(item).to_be_visible()
    pg.once('dialog', lambda d: d.accept()); item.click()
    pg.wait_for_function("!Object.keys(localStorage).some(k => k.startsWith('ballotta.'))", timeout=5000)
    pg.wait_for_load_state(); expect(pg.locator('#start')).to_be_visible(); expect(pg.locator('#ph-bar')).to_be_hidden()
    assert pb_stored(pg) == [] and pg.errs == [], (pb_stored(pg), pg.errs)
    ctx.close()

@phone_test
def phone_stored_junk_in_share_fields(b):
    # Port of stored_junk_in_share_fields (#44): a stored share generation that isn't a whole number, a share name that
    # isn't text and pick values that aren't option names are ignored on a phone: nothing decided, no name, generation 1.
    ctx, pg = phone_page(b); pg.goto(BASE)
    pg.evaluate("""() => { localStorage.setItem('ballotta.gen', JSON.stringify('x')); localStorage.setItem('ballotta.name', JSON.stringify({ a: 1 }));
                          localStorage.setItem('ballotta.picks', JSON.stringify({ c070: [null], c071: 5, c001: { x: 1 } })); }""")
    pg.reload(); lookup_phone(pg)
    assert pg.text_content('#ph-count') == '0 of 63 decided', pg.text_content('#ph-count')
    pb_go(pg, 'c070'); pb_line(pg, 'Qadri').click()
    pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]')
    assert pg.input_value('#sharename') == '' and pg.evaluate('sharePrep.gen') == 1, (pg.input_value('#sharename'), pg.evaluate('sharePrep.gen'))
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def phone_stored_junk_never_breaks_keep_or_share(b):
    # Port of stored_junk_never_breaks_keep_or_share (#20): reasons that aren't text and picks that aren't an object, in
    # storage, can't make the phone layout, Keep or Share throw, and aren't shown as reasons.
    ctx, pg = phone_page(b); pg.goto(BASE)
    pg.evaluate("localStorage.setItem('ballotta.picks', 'null'); localStorage.setItem('ballotta.whys', JSON.stringify({c070: 5, c071: {x: 1}, c001: ['a']}))")
    pg.reload(); lookup_phone(pg)
    assert pg.input_value('#dk-w') == '', ('Senator: a stored ["a"] is not a reason', pg.input_value('#dk-w'))
    pb_go(pg, 'c070'); assert pg.input_value('#dk-w') == '', pg.input_value('#dk-w'); pb_line(pg, 'Qadri').click()
    pb_go(pg, 'c071'); pb_line(pg, 'For').click()
    pg.click('#ph-list'); pg.click('#dk-keep'); pg.wait_for_selector('#d-keep[open]')
    assert pg.text_content('#keepcount').startswith('Your 2 picks and 0 reasons'), pg.text_content('#keepcount')
    pg.click('#d-keep [data-close]'); pg.click('#ph-done'); pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]')
    assert '0 of these picks have reasons' in pg.text_content('#sharewhycount'), pg.text_content('#sharewhycount')
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def phone_friend_card_long_names_and_honest_copy(b):
    # Port of friend_card_long_names_and_honest_copy, phone half (#23, #24): a 30-letter name with no spaces never pushes
    # the phone page sideways (the friend's landing, then their picks beside yours and the "You and …" counts); the card
    # says most races link to neutral sources. (The laptop half: desk_friend_card_long_names_and_honest_copy.)
    name = 'Bartholomew' + 'w' * 19
    url = link('s', {'v': 1, 'n': name, 'c': 'abcd2345', 'g': 1, 'p': {'70': 0}, 'w': {'70': 'x'}})
    for size in (PHONE, {'width': 320, 'height': 640}):
        ctx, pg = phone_page(b, size=size); fresh_goto(pg, url); pg.wait_for_selector('#friend:not(.hidden)')
        txt = pg.text_content('#friend')
        assert 'Most races on your ballot link to neutral sources.' in txt and 'Each race' not in txt, txt
        assert name in txt and sideways(pg) <= 0, ('friend landing scrolls sideways', size, sideways(pg))
        lookup_phone(pg); pb_go(pg, 'c070'); expect(pg.locator('.dk-fchip')).to_be_visible()
        pg.click('#ph-fold'); expect(pg.locator('#dk-notes')).to_be_visible()
        assert name in pg.text_content('#dk-notes') and sideways(pg) <= 0, ('compare scrolls sideways', size, sideways(pg))
        assert pg.errs == [], pg.errs
        ctx.close()

@desk_test
def desk_friend_card_long_names_and_honest_copy(b):
    # The laptop half of friend_card_long_names_and_honest_copy (#23, #24), which is skipped wherever the phone layout exists.
    name = 'Bartholomew' + 'w' * 19
    url = link('s', {'v': 1, 'n': name, 'c': 'abcd2345', 'g': 1, 'p': {'70': 0}, 'w': {'70': 'x'}})
    ctx, pg = new_page(b, wide=True); fresh_goto(pg, url); pg.wait_for_selector('#friend:not(.hidden)')
    txt = pg.text_content('#friend')
    assert 'Most races on your ballot link to neutral sources.' in txt and 'Each race' not in txt, txt
    fits_width = lambda: pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert fits_width(), 'friend landing scrolls sideways'
    lookup_wide(pg); assert fits_width(), 'laptop app with the friend chip and notes scrolls sideways'
    ctx.close()

@phone_test
def laptop_crib_options_and_print_go_to_the_phone(b):
    # Port of desk_crib_options_and_print: its laptop checks unchanged; its last check is the new design. Today a phone
    # has no print options, so narrowing a laptop window dropped them ("laptop print options stay on the laptop"); the
    # phone layout has the same Crib sheet view with the same options, so they now stay when the window narrows.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c001"]'); pg.locator('.dk-line', has_text='Ted Brown').click()
    pg.fill('#dk-w', 'Wanted a third option.')
    assert pg.inner_text('#dk-views [data-view="crib"]') == 'Print your choices', pg.inner_text('#dk-views [data-view="crib"]')   # Lane, Oct 17
    pg.click('#dk-views [data-view="crib"]')
    assert pg.inner_text('#dk-paper h1') == 'Crib sheet' and pg.inner_text('#dk-paper > .ov') == 'PRINT YOUR CHOICES', (pg.inner_text('#dk-paper h1'), pg.inner_text('#dk-paper > .ov'))
    t034 = pg.evaluate("cleanTitle(BYID['c034'])")
    import io, pypdf
    norm = lambda s: ' '.join(s.split())                                                           # PDF text wraps long lines
    printed = lambda: norm(''.join(x.extract_text() for x in pypdf.PdfReader(io.BytesIO(pg.pdf(format='Letter'))).pages))
    assert norm(t034) in printed(), 'control: an unopposed race prints until it is hidden'
    page = pg.inner_text('#dk-page'); assert 'Ted Brown' in page and t034 in page and 'Wanted a third option' not in page
    pg.check('#dk-cu'); assert t034 not in pg.inner_text('#dk-page') and t034 not in pg.inner_text('#crib')
    pg.check('#dk-cw'); assert 'Wanted a third option' in pg.inner_text('#dk-page') and pg.is_checked('#withwhy')
    pg.check('#dk-c2'); assert 'two' in pg.get_attribute('#crib', 'class') and 'two' in pg.get_attribute('#dk-page', 'class')
    pg.emulate_media(media='print')
    assert pg.is_visible('#crib') and pg.is_hidden('#dk-app') and pg.is_hidden('#dk-hdr')
    pg.emulate_media(media='null')                                                                # back to normal, so pdf() prints as a browser would
    pdf = printed()                                                                                # a real print (narrower page)
    assert 'Ted Brown' in pdf and norm(t034) not in pdf, 'the printout honours Hide unopposed races'
    assert pg.is_checked('#dk-c2') and pg.is_checked('#dk-cu') and 'two' in pg.get_attribute('#crib', 'class'), 'printing keeps the options'
    pg.evaluate("() => dispatchEvent(new Event('beforeprint'))"); pg.keyboard.press('Shift')   # a print that never reports back, then any key
    pg.emulate_media(media='screen'); pg.set_viewport_size({'width': 400, 'height': 900}); pg.wait_for_timeout(300)   # the resize event lands a frame later
    expect(pg.locator('#ph-bar')).to_be_visible(); assert h1(pg) == 'Crib sheet', h1(pg)
    for t in ('#dk-cw', '#dk-c2', '#dk-cu'): expect(pg.locator(t)).to_be_visible(); assert pg.is_checked(t), t
    assert 'two' in pg.get_attribute('#crib', 'class') and t034 not in pg.inner_text('#crib') and 'Wanted a third option' in pg.inner_text('#crib'), 'the print options go with the window to the phone layout'
    ctx.close()

@phone_test
def laptop_and_phone_landing_plum_band_and_faq(b):
    # Port of desk_landing_plum_band_and_faq: its laptop checks unchanged; its last check is the new design. Today a
    # phone shows neither the plum band nor the FAQ; the phone layout has the band (with the form overlapping it) and
    # the FAQ as folds (#ph-faq), the laptop's #dk-faq staying hidden. (Details: phone_landing_band_form_and_faq.)
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    for width in (1024, 1280, 1440, 1920):
        pg.set_viewport_size({'width': width, 'height': 900}); pg.wait_for_function(f'innerWidth === {width}')
        landing_band_checks(pg, '#start', '.dk-steps', width)
        faq_checks(pg, '#start')
    for w, h in ((1440, 789), (1366, 657), (1280, 680), (1024, 768), (1024, 820), (1024, 880)):       # real browser windows, not screens (audit)
        pg.set_viewport_size({'width': w, 'height': h}); pg.wait_for_function(f'innerHeight === {h}')
        landing_band_checks(pg, '#start', '.dk-steps', w)
        assert box(pg, '#go')['y'] + box(pg, '#go')['height'] <= h, ('Show my ballot is above the fold', w, h)
    pg.set_viewport_size({'width': 1280, 'height': 600}); pg.wait_for_function('innerHeight === 600')
    assert box(pg, '#street')['y'] + box(pg, '#street')['height'] <= 600, 'even on a 150%-scaled screen the address box shows'
    pg.set_viewport_size({'width': 1440, 'height': 900})
    lookup_wide(pg)                                                                                   # the app itself is unchanged
    assert pg.is_hidden('#dk-hero') and pg.is_hidden('#dk-faq') and pg.is_visible('.dk-brand')
    assert css(pg, '#dk-hdr', 'backgroundColor') != PLUM and css(pg, '#dk-hdr', 'content', "'::before'") != 'none'
    pg.click('#dk-help'); pg.click('[data-help="address"]')                                         # "Change address" is the landing page too
    landing_band_checks(pg, '#start', '.dk-steps', 1440); faq_checks(pg, '#start')
    assert pg.is_visible('#dk-back') and pg.is_visible('#dk-share')
    for w, h in ((1366, 657), (1024, 768), (1024, 821), (1024, 880), (1024, 881)):                    # the Back button adds ~46px (audit #2)
        pg.set_viewport_size({'width': w, 'height': h}); pg.wait_for_function(f'innerHeight === {h}')
        assert box(pg, '#go')['y'] + box(pg, '#go')['height'] <= h, ('Change address: Show my ballot above the fold', w, h)
    pg.set_viewport_size({'width': 1440, 'height': 900})
    bg = css(pg, '#dk-share', 'backgroundColor')
    assert contrast(bg, PLUM) >= 3 and contrast(css(pg, '#dk-share', 'color'), bg) >= 4.5, 'Share my picks still reads as a button on the plum bar'
    ctx.close()
    ctx, pg = new_page(b, wide=True); fresh_goto(pg, link('s', DESK_FRIEND)); pg.wait_for_selector('#friend:not(.hidden)')
    for width in (1024, 1440):
        pg.set_viewport_size({'width': width, 'height': 900}); pg.wait_for_function(f'innerWidth === {width}')
        landing_band_checks(pg, '#friend', '#start', width)                                         # a friend's picks on the paper, your form beside it
        faq_checks(pg, '#friend')
    ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE)                                                            # phones: the band and the FAQ, as folds
    expect(pg.locator('#dk-hero')).to_be_visible(); expect(pg.locator('#ph-faq')).to_be_visible(); expect(pg.locator('#dk-faq')).to_be_hidden()
    assert pg.locator('#ph-faq details').count() == 6 and css(pg, '#dk-hero', 'backgroundColor') == PLUM
    ctx.close()

@phone_test
def phone_old_link_warning_gone_after_new_lookup(b):
    # Port of desk_old_link_warning_gone_after_new_lookup (#40): a damaged-link warning that arrived on a phone doesn't
    # outlive a new lookup, on the phone or after widening past 1024px. New design: the phone layout shows the warning
    # itself (the app's notice above the paper), and a new lookup is made from Feedback & Info, Change address.
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg)
    pg.evaluate("location.hash = '#s2' + 'A'.repeat(40)")
    pg.wait_for_selector('#dk-say:not(.hidden)', timeout=5000)
    expect(pg.locator('#dk-say')).to_be_visible(); assert 'damaged' in pg.inner_text('#dk-say'), pg.inner_text('#dk-say')
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Change address').click(); expect(pg.locator('#start')).to_be_visible()
    pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '78701'); pg.click('#go')
    pg.wait_for_function("(window.__events||[]).filter(e => e[0] === 'ballot_found').length === 2", timeout=30000)
    pg.wait_for_selector('body.dk-app-on'); expect(pg.locator('#ph-bar')).to_be_visible()
    assert pg.evaluate("document.getElementById('dk-say').classList.contains('hidden')"), 'stale warning after a new lookup on the phone'
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(300)
    assert pg.evaluate("document.getElementById('dk-say').classList.contains('hidden')"), 'stale warning came back on the laptop layout'
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def laptop_and_phone_why_box_grows_with_the_reason(b):
    # Port of desk_why_box_grows_with_the_reason: its laptop checks unchanged; its phone check is the new design. Today's
    # phone page keeps a fixed 70px box ("phones unchanged until the phone round"); in the phone layout the reason box is
    # the laptop's card, and it grows as you type and opens a long saved reason at full height there too.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c070"]'); h0 = pg.locator('#dk-w').bounding_box()['height']
    card = pg.evaluate("""(() => { const w = document.querySelector('.dk-why'), s = getComputedStyle(w), r = w.getBoundingClientRect(),
        k = document.querySelector('#dk-paper .skip').getBoundingClientRect();
        return {bg: s.backgroundColor, border: s.borderTopStyle, pad: parseFloat(s.paddingLeft), holds: w.contains(document.getElementById('dk-w')) && !!w.querySelector('label'), gap: r.top - k.bottom}; })()""")
    assert card['bg'] not in ('rgba(0, 0, 0, 0)', 'rgb(255, 255, 255)') and card['border'] == 'solid' and card['pad'] >= 12 and card['holds'], card
    assert card['gap'] >= 24, ('the reason card sits apart from Skip', card)                      # Lane, Oct 15: "notes card" (option A)
    pg.click('#dk-w'); pg.keyboard.type(LONG_WHY)
    assert fits(pg, '#dk-w') and pg.locator('#dk-w').bounding_box()['height'] > h0 * 3, 'the laptop box grows as you type'
    pg.click('.dk-row[data-row="c071"]'); pg.click('.dk-row[data-row="c070"]')
    assert fits(pg, '#dk-w'), 'a long saved reason opens at full height'
    pg.fill('#dk-w', LONG_WHY * 4)                                                                # long enough to fill the screen
    pg.evaluate("() => { const t = document.getElementById('dk-w'); t.focus({preventScroll: true}); t.setSelectionRange(t.value.length, t.value.length); }")
    pg.evaluate('window.scrollTo(0, document.documentElement.scrollHeight)'); y = pg.evaluate('scrollY')
    pg.keyboard.type('x')
    assert abs(pg.evaluate('scrollY') - y) <= 30, ('typing at the bottom does not jump the page', y, pg.evaluate('scrollY'))
    ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pb_go(pg, 'c070')
    h0 = pg.locator('#dk-w').bounding_box()['height']
    pg.click('#dk-w'); pg.keyboard.type(LONG_WHY)
    assert fits(pg, '#dk-w') and pg.locator('#dk-w').bounding_box()['height'] > h0 * 3, ('the phone box grows as you type', h0, pg.locator('#dk-w').bounding_box())
    pg.wait_for_function("w => (JSON.parse(localStorage.getItem('ballotta.whys')) || {}).c070 === w", arg=LONG_WHY, timeout=2000)   # saved once typing pauses (#91)
    pb_go(pg, 'c071'); assert pg.input_value('#dk-w') == ''
    pb_go(pg, 'c070'); assert fits(pg, '#dk-w') and pg.input_value('#dk-w') == LONG_WHY, 'a long saved reason opens at full height on a phone'
    assert sideways(pg) <= 0 and pg.errs == [], pg.errs
    ctx.close()

# ---------------------------------------------------------------- results on your ballot (Lane, Oct 20; docs/plans/2026-10-20-results.md)
# The page reads results.json from Nov 4, Austin time. Here it is served from tests/results_fixture.py's TEST DATA scenes,
# only by this local server (never published). The ballot is a saved one, so no lookup is needed.
RESULTS_TESTS = set()
def results_test(fn): TESTS.append(fn); RESULTS_TESTS.add(fn.__name__); return fn
def rs_fixtures():
    spec = importlib.util.spec_from_file_location('results_fixture', ROOT / 'tests/results_fixture.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m
RS_BALLOT = {'pr': '142', 'b': [1, 6, 56, 69, 71, 72, 113, 117, 121, 124, 147], 'mode': 'exact', 'at': 0, 'pt': None, 'ln': []}
RS_PICKS = {'c001': ['James Talarico'], 'c069': ['Selena Xie'], 'c071': ['AGAINST'], 'c072': ['FOR'], 'c113': ['Sarah Ponder', 'Charles Young'],
            'c121': ['__skip'], 'c124': ['Jimmy Counihan'], 'c147': ['FOR'], 'c056': ['George Morales III']}
def rs_when(s): return _dt.datetime.fromisoformat(s + '-06:00' if s >= '2026-11-01T02' else s + '-05:00')   # CST from Nov 1, 2 am
def rs_page(b, serve, when='2026-11-05T09:00', phone=False, ballot=True, picks=True, url=None, sent=None):
    """serve: {'body': str or dict, 'headers': {...}}, read at each request, so a test can change what the server says."""
    ctx, pg = phone_page(b, sent=sent) if phone else new_page(b, sent=sent, wide=True)
    if not phone:
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.__dict__['errs'] = errs
    asked = []; pg.__dict__['asked'] = asked
    def answer(route):
        asked.append(route.request.url)
        body = serve['body']
        route.fulfill(status=serve.get('status', 200), content_type='application/json', headers=serve.get('headers', {}),
                      body=body if isinstance(body, str) else json.dumps(body))
    ctx.route(re.compile(r'.*/results\.json(\?.*)?$'), answer)
    t = rs_when(when)
    if TODAY: pg.clock.set_system_time(t)
    else: pg.clock.install(time=t)
    pg.goto(BASE)
    if ballot: pg.evaluate("b => localStorage.setItem('ballotta.ballot', JSON.stringify(b))", RS_BALLOT)
    if picks: pg.evaluate("p => localStorage.setItem('ballotta.picks', JSON.stringify(p))", RS_PICKS)
    pg.goto(url or BASE); pg.wait_for_timeout(600)
    return ctx, pg
def rs_go(pg, cid, phone=False):
    if phone: pg.evaluate("id => desk.ph.go(id)", cid)
    else: pg.click(f'.dk-row[data-row="{cid}"]')
    pg.wait_for_timeout(100)
    rib = pg.query_selector('#dk-paper .rs')
    return rib.inner_text() if rib else ''

@results_test
def results_wait_for_nov_4(b):
    # Before Nov 4 (Austin time) nothing changes: the page doesn't even ask for results.json; the landing card stays hidden.
    fx = rs_fixtures()
    ctx, pg = rs_page(b, {'body': fx.scene('mixed')}, when='2026-11-03T23:30')
    assert pg.asked == [] and pg.query_selector('.rs') is None and not pg.is_visible('#rs-top'), (pg.asked,)
    pg.click('.dk-row[data-row="c071"]'); assert pg.query_selector('#dk-paper .rs') is None
    pg.evaluate("localStorage.removeItem('ballotta.ballot')"); pg.reload(); pg.wait_for_timeout(300)
    assert not pg.is_visible('#rs-or') and pg.inner_text('#go') == 'Show my ballot' and pg.asked == [] and pg.errs == [], (pg.asked, pg.errs)
    ctx.close()

@results_test
def results_show_on_the_laptop_ballot(b):
    fx = rs_fixtures(); sent = []
    ctx, pg = rs_page(b, {'body': fx.scene('mixed')}, sent=sent)
    top = pg.inner_text('#rs-top')
    assert '0/11' in top and 'official results' in top and pg.inner_text('#dk-count') == '0 of 11 official', top
    r = rs_go(pg, 'c071')
    for w in ('Unofficial · TEST DATA (not real results), posted Nov 4, 8:41 am', 'Late mail, overseas and provisional ballots are still being counted.',
              'Becomes official when the Austin City Council canvasses the vote, by Nov 17.', 'Passing', 'Your pick, Against, is behind.',
              'HOW TRAVIS COUNTY VOTED', 'Travis County’s count only. The result above includes every county in this race.'):   # the heading is set in capitals
        assert w in r, (w, r)
    r = rs_go(pg, 'c069'); assert 'Too close to call' in r and 'Your pick: Selena Xie' in r and 'canvasses the vote on Nov 12.' in r and 'behind' not in r, r
    r = rs_go(pg, 'c113'); assert 'Leading for 2 seats: Sarah Ponder, Robert Johnson' in r and '1 of your 2 picks is leading.' in r, r
    r = rs_go(pg, 'c072'); assert 'Partial · Hays County’s count isn’t in yet' in r and 'Your pick, For, is behind.' in r, r
    r = rs_go(pg, 'c117'); assert 'No votes reported yet' in r and 'Unofficial' not in r, r
    r = rs_go(pg, 'c121'); assert 'May go to a runoff' in r and 'You skipped this race.' in r, r
    r = rs_go(pg, 'c124'); assert 'Leading: Jimmy Counihan' in r and 'Your pick is leading.' in r and 'behind' not in r, r
    r = rs_go(pg, 'c001')
    assert 'Becomes official at the state canvass, Nov 21–Dec 7.' in r and 'Jade Simmons (write-in)' in r and 'Only votes for declared write-in candidates count.' in r, r
    r = rs_go(pg, 'c006'); assert 'Becomes official when the Legislature canvasses the vote, after it meets Jan 12, 2027.' in r, r
    # one neutral look: every bar the same color, no party words or marks in a ribbon
    fills = set(pg.evaluate("[...document.querySelectorAll('#dk-paper .rs-bars:not(.rs-tv .rs-bars) .rs-tr i')].map(i => getComputedStyle(i).backgroundColor)"))
    assert len(fills) == 1 and not re.search(r'Republican|Democratic|\(I\)|✓|✗', r), (fills, r)
    # At a glance after the election (Phase 3): Contest · Result · Your pick · Your reason; the result says what happened,
    # then whether it's official and when it will be
    pg.click('#dk-views [data-view="glance"]')
    heads = [x.inner_text() for x in pg.query_selector_all('.dk-tbl thead th')]
    assert heads == ['CONTEST', 'RESULT', 'YOUR PICK', 'YOUR REASON'], heads
    cells = [' / '.join(x.inner_text().split('\n')) for x in pg.query_selector_all('.rs-gl tr[data-tr] td:nth-child(2)')]
    assert cells == ['Too close to call / Unofficial · state canvass Nov 21 – Dec 7', 'Too close to call / Unofficial · the Legislature, January',
                     'Unopposed: George Morales III / Unofficial · canvass by Nov 17', 'Too close to call / Unofficial · canvass Nov 12',
                     'Passing / Unofficial · 60.0% for', 'Failing / Unofficial · 39.1% for',
                     'Leading for 2 seats: Sarah Ponder, Robert Johnson / Unofficial · canvass by Nov 17', 'No result yet',
                     'May go to a runoff / Unofficial · canvass by Nov 17', 'Leading: Jimmy Counihan / Unofficial · canvass by Nov 17',
                     'Failing / Unofficial · 21.1% for'], cells
    assert all(x.get_attribute('colspan') == '4' for x in pg.query_selector_all('tr.dk-tg th'))
    # nothing about the ballot is sent: one plain GET of the file, and only the bare event
    assert [u for u in sent if 'results' in u] and all(u.endswith('/results.json') for u in sent if 'results' in u), [u for u in sent if 'results' in u]
    assert [e for e in events(pg) if e[0] == 'results_seen'] == [['results_seen', {'layout': 'laptop'}]], events(pg)
    assert pg.errs == [], pg.errs
    ctx.close()

@results_test
def results_show_on_the_phone_ballot(b):
    fx = rs_fixtures()
    ctx, pg = rs_page(b, {'body': fx.scene('mixed')}, phone=True)
    assert pg.is_visible('#rs-top .rs-compact') and pg.inner_text('#rs-top .rs-compact').startswith('0 of 11 official · 3 of your 9 picks won or are leading'), pg.inner_text('#rs-top')
    assert not pg.is_visible('#rs-top .rs-sum') and pg.inner_text('#ph-count') == '0 of 11 official'
    r = rs_go(pg, 'c113', phone=True); assert 'Leading for 2 seats' in r and '1 of your 2 picks is leading.' in r, r
    assert sideways(pg) <= 0
    r = rs_go(pg, 'c071', phone=True); assert 'Your pick, Against, is behind.' in r and sideways(pg) <= 0, r
    pg.click('#ph-list'); sm = pg.inner_text('.dk-rail .rs-listsum')
    assert sm.startswith('0/11') and 'YOUR 9 PICKS' in sm and 'won or are leading' in sm, sm   # the summary, small, at the top of the list
    pg.click('#dk-views [data-view="all"]'); pg.wait_for_timeout(200)
    assert pg.inner_text('#dk-paper h1') == 'All Travis County results' and sideways(pg) <= 0
    assert 'Your pick' not in ''.join(x.inner_text() for x in pg.query_selector_all('#dk-paper .rs')), 'All Travis County results is nobody’s ballot'
    assert pg.is_visible('#dk-paper [data-rs="go"]'), 'a contest on your ballot links to it'
    assert [e for e in events(pg) if e[0] == 'results_seen'] == [['results_seen', {'layout': 'phone'}]], events(pg)
    assert pg.errs == [], pg.errs
    ctx.close()

@results_test
def results_say_what_changed_since_you_last_looked(b):
    fx = rs_fixtures(); serve = {'body': fx.scene('mixed')}
    ctx, pg = rs_page(b, serve)
    assert 'Since you last looked' not in pg.inner_text('#rs-top'), 'the first visit has nothing to compare'
    serve['body'] = fx.scene('official'); pg.clock.set_system_time(rs_when('2026-12-03T09:00')); pg.reload(); pg.wait_for_timeout(600)
    top = pg.inner_text('#rs-top')
    assert '4/11' in top and 'Since you last looked: 4 results became official.' in top and pg.inner_text('#dk-count') == '4 of 11 official', top
    r = rs_go(pg, 'c071'); assert r.startswith('Official · canvassed by the Austin City Council, Nov 12') and 'Passed' in r and 'Your pick, Against, didn’t win.' in r, r
    r = rs_go(pg, 'c056'); assert 'Elected: George Morales III (unopposed)' in r and 'Your pick was elected.' in r, r
    r = rs_go(pg, 'c001'); assert 'Official · canvassed by the state, Dec 2 · numbers are the last unofficial count' in r, r
    r = rs_go(pg, 'c147'); assert 'Voters didn’t confirm this district (Proposition A failed), so it won’t be created.' in r, r
    r = rs_go(pg, 'c069'); assert 'Late mail' not in r, ('after late_until, no late-ballot line', r)
    pg.reload(); pg.wait_for_timeout(600)
    assert 'Since you last looked' not in pg.inner_text('#rs-top'), 'nothing new the second time'
    fixed = fx.scene('official'); fixed['seq'] = 6
    e = fixed['contests']['c071']; e.update(verdict='failed', corrected='2026-12-03', changed=6)
    e['choices'][0][1], e['choices'][1][1] = 120000, 180000; e['choices'][0][2], e['choices'][1][2] = 40.0, 60.0
    serve['body'] = fixed; pg.reload(); pg.wait_for_timeout(600)
    top = pg.inner_text('#rs-top')
    assert 'Corrected since you last looked: 1 result. An earlier version on Ballotta was wrong.' in top, top
    r = rs_go(pg, 'c071'); assert 'Corrected Dec 3: an earlier version on Ballotta was wrong.' in r and 'Your pick, Against, won.' in r, r
    pg.clock.set_system_time(rs_when('2026-12-11T09:00')); pg.reload(); pg.wait_for_timeout(600)
    assert 'Corrected Dec 3' not in rs_go(pg, 'c071'), 'the correction note fades after a week'
    # #136: an old correction isn't news again; only races whose numbers moved count as new numbers
    import copy
    later = copy.deepcopy(fixed); later['seq'] = 7
    later['contests']['c071']['choices'][0][1] += 50
    serve['body'] = later; pg.reload(); pg.wait_for_timeout(600)
    top = pg.inner_text('#rs-top')
    assert 'Since you last looked: new numbers in 1 race.' in top and 'Corrected' not in top, top
    # a new leader is a changed result, not just new numbers
    lead = copy.deepcopy(later); lead['seq'] = 8
    e = lead['contests']['c124']; other = [x[0] for x in e['choices'] if x[0] != e['leaders'][0]][0]
    e['leaders'] = [other]; e['changed'] = 8
    serve['body'] = lead; pg.reload(); pg.wait_for_timeout(600)
    assert 'Since you last looked: 1 result changed.' in pg.inner_text('#rs-top'), pg.inner_text('#rs-top')
    # results that arrive while the page is open are seen: the next visit doesn't announce them again
    more = copy.deepcopy(lead); more['seq'] = 9; more['contests']['c069']['choices'][0][1] += 5
    serve['body'] = more
    pg.clock.run_for(11 * 60 * 1000); pg.evaluate("dispatchEvent(new Event('focus'))"); pg.wait_for_timeout(600)
    pg.reload(); pg.wait_for_timeout(600)
    assert 'Since you last looked' not in pg.inner_text('#rs-top'), ('seen while open, not news again', pg.inner_text('#rs-top'))
    assert pg.errs == [], pg.errs
    ctx.close()

@results_test
def withdrawn_results_hide_everything(b):
    fx = rs_fixtures()
    ctx, pg = rs_page(b, {'body': fx.scene('withdrawn')})
    assert pg.inner_text('#rs-top') == 'Results are paused while we check a problem with the latest numbers. Your picks aren’t affected.'
    assert rs_go(pg, 'c071') == '' and pg.locator('[data-rs="all"]:visible').count() == 0
    pg.click('#dk-views [data-view="glance"]')
    assert {x.inner_text() for x in pg.query_selector_all('.rs-gl tr[data-tr] td:nth-child(2)')} == {'Results paused'}, 'no result in At a glance either'
    pg.evaluate("localStorage.removeItem('ballotta.ballot')"); pg.reload(); pg.wait_for_timeout(400)
    assert not pg.is_visible('#rs-or') and pg.inner_text('.dk-tagline').startswith('Don’t wait') and pg.errs == [], pg.errs
    ctx.close()
    # a hurried pull that flips the switch but leaves every number in the file: still nothing shows
    ctx, pg = rs_page(b, {'body': {**fx.scene('mixed'), 'withdrawn': True}})
    assert pg.inner_text('#rs-top').startswith('Results are paused'), pg.inner_text('#rs-top')
    assert rs_go(pg, 'c071') == '' and rs_go(pg, 'c124') == '' and pg.locator('[data-rs="all"]:visible').count() == 0
    pg.click('#dk-views [data-view="glance"]')
    assert {x.inner_text() for x in pg.query_selector_all('.rs-gl tr[data-tr] td:nth-child(2)')} == {'Results paused'} and pg.errs == [], pg.errs
    ctx.close()

@results_test
def a_bad_results_file_breaks_nothing(b):
    # results.json is untrusted to the page: each malformed file shows nothing, and the ballot works as before; a single
    # bad entry is left out, never the rest.
    fx = rs_fixtures(); serve = {'body': 'not json'}
    ctx, pg = rs_page(b, serve)
    bad = ['not json', '[]', 'null', {'seq': -1}, dict(fx.scene('mixed'), election='2024-11-05'), dict(fx.scene('mixed'), contests=[]),
           {'seq': 1, 'election': '2026-11-03', 'withdrawn': False, 'late_until': '2026-11-17', 'contests': {'c071': {'state': 'unofficial'}}}]
    for body in bad:
        serve['body'] = body; pg.reload(); pg.wait_for_timeout(400)
        assert pg.query_selector('.rs') is None and not pg.is_visible('#rs-top'), body
    pg.click('.dk-row[data-row="c147"]'); pg.click('#dk-paper .dk-line[data-pick="AGAINST"]')
    assert cur(pg, 'c147') == ['AGAINST'], 'with no results the page accepts, picking still works'
    one = fx.scene('mixed'); one['contests']['c071']['choices'].reverse()                    # out of ballot order
    one['contests']['c069']['choices'][0][0] = '<img src=x onerror=alert(1)>'                  # not a ballot name
    one['contests']['c113']['sources'][0][0] = '<b>Travis</b>'                                 # text, shown as text
    serve['body'] = one; pg.reload(); pg.wait_for_timeout(500)
    assert rs_go(pg, 'c071') == '' and rs_go(pg, 'c069') == '', 'a bad entry is left out'
    r = rs_go(pg, 'c113'); assert '<b>Travis</b>' in r and pg.query_selector('#dk-paper .rs b') is None, r
    assert pg.errs == [], pg.errs
    ctx.close()

@results_test
def the_date_override_works_only_on_this_computer(b):
    # ?today= is for Lane's local look at sample results (Task 6): on ballotta.org it does nothing.
    fx = rs_fixtures()
    ctx, pg = rs_page(b, {'body': fx.scene('mixed')}, when='2026-10-20T12:00', url=BASE + '?today=2026-11-06')
    assert pg.asked and pg.is_visible('#rs-top'), 'on localhost the override opens the gate'
    ctx.close()
    ctx, pg = new_page(b, wide=True); asked = []
    ctx.route('https://ballotta.org/**', lambda r: (asked.append(r.request.url) if r.request.url.split('?')[0].endswith('results.json') else None,
              r.fulfill(path=str(ROOT / (urllib.parse.urlsplit(r.request.url).path.lstrip('/') or 'index.html')))))
    if TODAY: pg.clock.set_system_time(rs_when('2026-10-20T12:00'))                              # the suite's own date may be past Nov 4
    else: pg.clock.install(time=rs_when('2026-10-20T12:00'))
    pg.goto('https://ballotta.org/index.html'); pg.evaluate("b => localStorage.setItem('ballotta.ballot', JSON.stringify(b))", RS_BALLOT)
    pg.goto('https://ballotta.org/index.html?today=2026-11-06'); pg.wait_for_timeout(600)
    assert asked == [] and not pg.is_visible('#rs-top'), ('ballotta.org ignores ?today=', asked)
    ctx.close()

@results_test
def all_travis_county_results_need_no_address(b):
    fx = rs_fixtures()
    ctx, pg = rs_page(b, {'body': fx.scene('mixed')}, ballot=False)
    # the landing page after the election (the canvas, Oct 21)
    assert pg.inner_text('.dk-tagline') == 'The results of the Nov 3, 2026 election, as they come in' and pg.inner_text('#start h1') == 'See how your ballot did'
    assert pg.inner_text('#go') == 'Show my ballot’s results' and pg.is_visible('#rs-or'), pg.inner_text('#go')
    assert 'Where things stand' in pg.inner_text('#rs-land-tl') and 'Are these results final?' in pg.inner_text('#dk-faq') and 'All 12,' in pg.inner_text('.dk-steps')
    pg.click('#rs-or [data-rs="all"]'); pg.wait_for_timeout(200)
    assert pg.evaluate("document.body.classList.contains('dk-app-on')") and pg.inner_text('#dk-paper h1') == 'All Travis County results'
    assert pg.inner_text('.dk-rhd h2') == 'Travis County results' and pg.inner_text('#dk-count') == '12 contests · 0 official', pg.inner_text('#dk-count')
    assert not pg.is_visible('.dk-foot'), 'no address: no picks to keep or print'
    n = len(pg.query_selector_all('#dk-paper .rs-c')); assert n == 12, n
    bond = pg.locator('#dk-paper .rs-c', has=pg.locator('.rs', has_text='Needs two-thirds of the vote to pass.'))   # W68, a road bond at 63%
    assert bond.count() == 1 and 'Failing' in bond.inner_text() and 'Eastwood' in bond.inner_text(), bond.count()
    assert 'Your pick' not in pg.inner_text('#dk-paper'), 'nobody’s ballot, even with picks saved here'
    titles = lambda: [x.inner_text() for x in pg.query_selector_all('#dk-paper .rs-c h4')]
    pg.click('.dk-row[data-lv="City"]'); t = titles()
    assert t and all('City of' in x for x in t), t
    pg.click('.dk-row[data-lv="all"]'); pg.fill('#dk-q', 'Morales'); assert titles() == ['County Commissioner, Precinct 4'], titles()
    pg.fill('#dk-q', 'commissioner'); assert titles() == ['County Commissioner, Precinct 4'], titles()   # a word only in the title
    pg.fill('#dk-q', 'zzz'); assert 'Nothing matches' in pg.inner_text('#dk-paper')
    pg.fill('#dk-q', ''); pg.click('#dk-filt [data-f="und"]'); assert len(titles()) == 4, titles()   # too close or may go to a runoff
    pg.click('#dk-filt [data-f="all"]')
    pg.click('#dk-views [data-view="decide"]'); pg.wait_for_timeout(200)   # no address: Results asks for one
    assert not pg.evaluate("document.body.classList.contains('dk-app-on')") and pg.evaluate("document.activeElement.id") == 'street'
    pg.goto(BASE.replace('index.html', 'results/')); pg.wait_for_timeout(800)
    assert pg.url.endswith('/?results') and pg.inner_text('#dk-paper h1') == 'All Travis County results', pg.url
    assert pg.errs == [], pg.errs
    ctx.close()

@results_test
def a_saved_copy_says_so(b):
    # The offline copy marks a results.json it kept (x-ballotta-copy: saved, sw.js); the page says the results may be out of date.
    fx = rs_fixtures()
    ctx, pg = rs_page(b, {'body': fx.scene('mixed'), 'headers': {'x-ballotta-copy': 'saved'}})
    assert 'Saved copy · may be out of date' in pg.inner_text('#rs-top'), pg.inner_text('#rs-top')
    ctx.close()
    sw = (ROOT / 'sw.js').read_text(encoding='utf-8')
    assert "u.pathname.endsWith('/results.json') ? savedCopy(kept) : kept" in sw and "h.set('x-ballotta-copy', 'saved')" in sw

@results_test
def the_canvass_is_explained_from_the_results_and_the_menu(b):
    fx = rs_fixtures()
    ctx, pg = rs_page(b, {'body': fx.scene('mixed')})
    rs_go(pg, 'c071'); pg.click('#dk-notes [data-rs="why"]'); assert pg.evaluate("document.getElementById('rs-why').open")
    assert 'Election night counts are unofficial.' in pg.inner_text('#rs-why') and 'It doesn’t call races' in pg.inner_text('#rs-why')
    pg.keyboard.press('Escape')
    pg.click('#dk-help'); pg.click('#dk-menu [data-help="results"]')
    assert pg.evaluate("document.getElementById('rs-why').open") and events(pg)[-1] == ['help_opened', {'item': 'results', 'layout': 'laptop'}], events(pg)[-1:]
    assert pg.errs == [], pg.errs
    ctx.close()

@results_test
def results_turn_the_ballot_into_a_record(b):
    # After the election (docs/plans/2026-10-21-after-the-election.md): the menu, the rail, the summary and the timeline
    # turn to results; the paper is the result, your pick and reason with it; the picks are read-only.
    fx = rs_fixtures()
    ctx, pg = rs_page(b, {'body': fx.scene('mixed')})
    pg.evaluate("w => localStorage.setItem('ballotta.whys', JSON.stringify(w))", {'c071': 'Parks need it'}); pg.reload(); pg.wait_for_timeout(600)
    menu = [x.inner_text().strip() for x in pg.query_selector_all('#dk-views button') if x.is_visible()]
    assert menu == ['Results', 'At a glance', 'All Travis County results', 'Print your results'], menu
    assert [x.inner_text() for x in pg.query_selector_all('#dk-filt button')] == ['All 11', 'Too close 4', 'My picks 8']
    assert pg.inner_text('#dk-when') == 'Results updated Nov 4, 8:41 am', pg.inner_text('#dk-when')
    pg.evaluate("desk.today(false)")   # what the midnight check runs on a page left open
    assert pg.inner_text('#dk-when') == 'Results updated Nov 4, 8:41 am', ('the results time past midnight (#141)', pg.inner_text('#dk-when'))
    sm = pg.inner_text('#rs-top .rs-sum')
    assert '0/11' in sm and 'YOUR 9 PICKS' in sm and 'A runoff is possible' in sm, sm   # Sunset Valley's two picks count as two (#144)
    assert [x.inner_text() for x in pg.query_selector_all('#rs-top .rs-sum .three b')] == ['3', '4', '2'], 'won or leading, behind (one of the two Sunset Valley picks), too close'
    other = pg.evaluate("() => optionsOf(BYID['c124']).find(x => x !== 'Jimmy Counihan')")   # a one-seat pick that isn't leading
    pg.evaluate("o => { const p = JSON.parse(localStorage.getItem('ballotta.picks')); p.c124 = [o]; localStorage.setItem('ballotta.picks', JSON.stringify(p)); }", other)
    pg.reload(); pg.wait_for_timeout(600)
    assert [x.inner_text() for x in pg.query_selector_all('#rs-top .rs-sum .three b')] == ['2', '5', '2'], 'a pick behind in a leading race counts as behind'
    pg.evaluate("p => localStorage.setItem('ballotta.picks', JSON.stringify(p))", RS_PICKS); pg.reload(); pg.wait_for_timeout(600)
    assert pg.inner_text('#rs-top .rs-tl li.now b') == 'Late ballots and local canvasses'
    assert pg.inner_text('.dk-row[data-row="c071"] small') == 'Passing · Unofficial'
    pg.click('#dk-filt [data-f="und"]')
    assert [x.get_attribute('data-row') for x in pg.query_selector_all('.dk-row')] == ['c001', 'c006', 'c069', 'c121']
    pg.click('#dk-filt [data-f="all"]')
    r = rs_go(pg, 'c071')
    assert 'Your pick, Against, is behind.' in r and 'Parks need it' in r and 'Your reason. Only you can see it.' in r, r
    assert pg.query_selector('#dk-paper [data-pick]') is None and pg.query_selector('#dk-w') is None, 'read-only after the election'
    assert pg.inner_text('#dk-paper .dk-ro .dk-line[data-on="true"]').startswith('Against')
    pg.focus('#dk-paper'); pg.keyboard.press('1'); pg.keyboard.press('s')
    assert cur(pg, 'c071') == ['AGAINST'], 'the picking keys do nothing after the election'
    notes = pg.inner_text('#dk-notes')
    assert 'ABOUT THIS RESULT' in notes and 'CALLING RACES' in notes and 'TEST DATA (not real results), posted Nov 4, 8:41 am' in notes, notes
    assert pg.inner_text('#dk-next').startswith('Next: '), pg.inner_text('#dk-next')
    pg.click('#dk-next'); pg.wait_for_timeout(100)
    assert pg.get_attribute('.dk-row[aria-current="true"]', 'data-row') == 'c072', 'Next goes in ballot order'
    # At a glance is a record too (Lane, Oct 21): the pick and the reason are shown, nothing there changes them
    pg.click('#dk-views [data-view="glance"]'); pg.wait_for_timeout(100)
    assert pg.query_selector('#dk-paper .dk-sel') is None, 'no pick menus after the election'
    assert pg.query_selector('#dk-paper [data-why]') is None and pg.query_selector('#dk-paper td [data-go]') is None, 'no Edit, Add a reason or Choose'
    row = pg.inner_text('#dk-paper tr[data-tr="c071"]')
    assert 'Against' in row and 'Parks need it' in row, row
    none = pg.evaluate("() => ballot.map(b => b.c.id).find(id => !current(id).length)")
    assert none and 'No pick' in pg.inner_text('#dk-paper tr[data-tr="' + none + '"]'), none
    assert cur(pg, 'c071') == ['AGAINST']
    assert pg.inner_text('#dk-paper .dk-gh h1') == 'Your ballot’s results' and 'Showing 11 of 11.' in pg.inner_text('#dk-paper')
    pg.check('#dk-mine'); pg.wait_for_timeout(100)
    assert len(pg.query_selector_all('#dk-paper tr[data-tr]')) == 8 and 'Showing 8 of 11.' in pg.inner_text('#dk-paper'), 'only the contests picked in'
    assert pg.evaluate("document.activeElement.id") == 'dk-mine'
    pg.click('#dk-paper tr[data-tr="c071"] [data-go]'); pg.wait_for_timeout(100)
    assert pg.get_attribute('.dk-row[aria-current="true"]', 'data-row') == 'c071' and 'Your pick, Against, is behind.' in pg.inner_text('#dk-paper')
    # Print your results: the crib sheet's layout, each contest's result under it, the pick on the right
    pg.click('#dk-views [data-view="crib"]'); pg.wait_for_timeout(100)
    assert pg.inner_text('#dk-paper h1') == 'Your ballot’s results' and pg.inner_text('#dk-notes [data-act="print"]') == 'Print your results'
    crib = pg.eval_on_selector('#crib', 'e => e.textContent')
    assert crib.startswith('My ballot’s resultsNov 3, 2026 · Results updated Nov 4, 8:41 am'), crib[:120]
    assert 'City of Austin Proposition APassing · Unofficial · 60.0% for' in crib and 'Against' in crib and '______' not in crib, crib
    assert pg.errs == [], pg.errs
    ctx.close()
    # an official runoff: What's next names it, and the contest says when
    ctx, pg = rs_page(b, {'body': fx.scene('runoff')}, when='2026-11-14T09:00')
    assert 'Runoff · Sat, Dec 12' in pg.inner_text('#rs-top .rs-sum .next'), pg.inner_text('#rs-top .rs-sum')
    assert 'Runoffs' in pg.inner_text('#rs-top .rs-tl') and pg.inner_text('.dk-row[data-row="c121"] small').startswith('Runoff: ')
    pg.click('#rs-top .rs-sum button.next'); pg.wait_for_timeout(100)
    r = pg.inner_text('#dk-paper')
    assert 'No one won a majority, so the top two meet again on Sat, Dec 12.' in r and 'A runoff on Saturday, Dec 12' in r and 'You skipped this race.' in r, r
    pg.click('#dk-views [data-view="glance"]'); pg.wait_for_timeout(100)
    g = pg.inner_text('#dk-paper tr[data-tr="c121"]')
    assert 'Runoff: Cheryl Bradley and Candace L. Hunter' in g and 'Official · runoff Sat, Dec 12' in g and 'Skipped' in g, g
    assert pg.errs == [], pg.errs
    ctx.close()

@results_test
def every_state_reads_in_at_a_glance_and_the_printout(b):
    # Every state on the canvas's Pieces board, through At a glance and Print your results (Phase 3): the result in
    # words, then official or not and when; nothing reads "undefined", and nothing breaks.
    import copy
    fx = rs_fixtures(); base = fx.scene('mixed')
    def put(cid, extra=None, **kw):
        sc = copy.deepcopy(base); sc['contests'][cid] = fx.entry(cid, **kw); sc['contests'][cid].update(extra or {}); return sc
    cases = [
        ('c069', put('c069', verdict='tied', votes=[10000, 10000]), None, 'Tied / Unofficial · canvass by Nov 17'),
        ('c069', put('c069', state='official', verdict='tied_runoff', votes=[10000, 10000], done='2026-11-12'), None, 'Tied · goes to a runoff / Official · Nov 12'),
        ('c071', put('c071', state='official', verdict='failed_tie', votes=[150000, 150000], done='2026-11-12'), None, 'Failed (tie vote) / Official · 50.0% for'),
        ('c069', put('c069', state='recount', verdict='won', votes=[10010, 9995], done='2026-11-12', recount='https://example.com/recount'), None,
         'Won: Jeffery Bowen / Official · Nov 12 · recount requested'),
        ('c113', put('c113', state='official', verdict='elected', canvasser='the Sunset Valley City Council', votes=[400, 380, 120], leaders=['Sarah Ponder', 'Robert Johnson'], done='2026-11-12'), None,
         'Elected: Sarah Ponder, Robert Johnson / Official · Nov 12'),
        ('c071', put('c071', {'needs': 'two_thirds'}, verdict='failing', votes=[180000, 120000]), None, 'Failing / Unofficial · 60.0% for · needs two-thirds'),
        ('c121', fx.scene('runoff'), '2026-12-14T09:00', 'Runoff held Dec 12 · result not shown here / Official · Nov 13'),
        ('c117', base, None, 'No result yet'),
    ]
    # #142: an official tie is no longer "too close to call"; a recount is neither won nor lost, and the rail says so; two
    # counts that round alike get a second decimal; a tie that goes to a runoff is What's next
    ctx, pg = rs_page(b, {'body': put('c069', state='recount', verdict='won', votes=[10010, 9995], done='2026-11-12', recount='https://example.com/recount')})
    assert pg.inner_text('.dk-row[data-row="c069"] small') == 'Won: Jeffery Bowen · Official · recount requested', pg.inner_text('.dk-row[data-row="c069"] small')
    r = rs_go(pg, 'c069'); assert '10,010 · 50.04%' in r and '9,995 · 49.96%' in r, r
    sm = [x.inner_text() for x in pg.query_selector_all('#rs-top .rs-sum .three > div')]
    assert sm == ['3\nwon or are leading', '4\nare behind', '2\nnot settled yet'], ('the recount pick (lost on the count) is open, not lost', sm)
    ctx.close()
    ctx, pg = rs_page(b, {'body': fx.scene('official')}, when='2026-12-03T09:00')
    assert 'Too close 3' in pg.inner_text('#dk-filt'), ('the canvassed Senate tie is not too close to call', pg.inner_text('#dk-filt'))
    ctx.close()
    ctx, pg = rs_page(b, {'body': put('c069', {'runoff_on': '2026-12-12'}, state='official', verdict='tied_runoff', votes=[10000, 10000], done='2026-11-12')}, when='2026-11-14T09:00')
    assert 'Runoff · Sat, Dec 12' in pg.inner_text('#rs-top .rs-sum .next') and 'Runoffs' in pg.inner_text('#rs-top .rs-tl'), pg.inner_text('#rs-top')
    r = pg.inner_text('#dk-paper') if rs_go(pg, 'c069') is not None else ''
    assert 'Jeffery Bowen and Selena Xie. It’s a new choice' in r, r
    ctx.close()
    for cid, body, when, want in cases:
        ctx, pg = rs_page(b, {'body': body}, **({'when': when} if when else {}))
        pg.click('#dk-views [data-view="glance"]'); pg.wait_for_timeout(100)
        got = ' / '.join(pg.inner_text(f'#dk-paper tr[data-tr="{cid}"] td:nth-child(2)').split('\n'))
        assert got == want, (cid, got, want)
        crib = pg.eval_on_selector('#crib', 'e => e.textContent')
        assert want.replace(' / ', ' · ') in crib and not re.search(r'undefined|null|NaN', crib), (cid, crib[:300])
        assert pg.errs == [], pg.errs
        ctx.close()

def main():
    srv = serve()
    failed = skipped = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        for fn in TESTS:
            if fn.__name__ in DESK_TESTS and not HAS_DESK:
                skipped += 1; print('SKIP', fn.__name__, '- no laptop layout in', PAGE); continue
            if fn.__name__ in PHONE_TESTS and not HAS_PHONE:
                skipped += 1; print('SKIP', fn.__name__, '- no phone layout in', PAGE); continue
            if fn.__name__ in RESULTS_TESTS and not HAS_RESULTS:
                skipped += 1; print('SKIP', fn.__name__, '- no results code in', PAGE, '(RESULTS_LIVE)'); continue
            if fn.__name__ in STREETS_TESTS and not HAS_STREETS:
                skipped += 1; print('SKIP', fn.__name__, '- no street map in', PAGE, '(it is in next/index.html until STREETS_LIVE)'); continue
            try:
                fn(b); print('PASS', fn.__name__)
            except Exception as e:
                failed += 1; print('FAIL', fn.__name__, '-', (str(e) or type(e).__name__)[:400])
        b.close()
    srv.shutdown()
    ran = len(TESTS) - skipped
    print(f'{ran - failed}/{ran} passed' + (f', {skipped} skipped' if skipped else '') + f' ({PAGE})')
    sys.exit(1 if failed else 0)

if __name__ == '__main__':
    main()
