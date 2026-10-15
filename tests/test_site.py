"""End-to-end checks for the Ballotta test site (index.html), run against the live Travis County lookup services.

    python3 tests/test_site.py            # builds nothing; serves the repo root and runs every check

Analytics: cloud.umami.is is stubbed so each test can see exactly which events (and which details) would be sent.
"""
import http.server, threading, functools, json, pathlib, re, sys, traceback, urllib.parse
from playwright.sync_api import sync_playwright, expect

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8765
BASE = f'http://127.0.0.1:{PORT}/index.html'
UMAMI_STUB = "window.__events=[];window.umami={track:function(n,d){window.__events.push([n,d||{}]);}};"

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve():
    h = functools.partial(Quiet, directory=str(ROOT))
    s = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s

def new_page(browser, sent=None):
    ctx = browser.new_context(viewport={'width': 400, 'height': 900}, permissions=['clipboard-read', 'clipboard-write'])
    ctx.route(re.compile(r'.*/umami\.js$'), lambda r: r.fulfill(status=200, content_type='application/javascript', body=UMAMI_STUB))
    ctx.route('https://cloud.umami.is/**', lambda r: r.abort())
    ctx.route('https://gateway.umami.is/**', lambda r: r.abort())
    ctx.route('https://fonts.googleapis.com/**', lambda r: r.abort())
    pg = ctx.new_page()
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

@test
def lookup_courthouse_and_ballot_found(b):
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg)
    assert pg.text_content('#k-total') == '63', pg.text_content('#k-total')
    ev = events(pg)
    assert ['ballot_found', {'match': 'exact'}] in ev, ev
    ctx.close()

@test
def race_learn_more_is_symmetric_and_attributed(b):
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg); open_race(pg, 'c070')
    body = pg.inner_text('#rc070')
    assert 'One of 10 district council members' in body
    kai = pg.locator('#rc070 .optw', has_text='Kai Huang').inner_text()
    assert 'Didn’t answer the League guide' in kai and 'No campaign site listed' in kai, kai
    zo = pg.locator('#rc070 .optw', has_text='Qadri')
    assert zo.locator('a', has_text='Campaign site').get_attribute('href') == 'https://zoforaustin.com'
    assert zo.locator('a', has_text='League guide answers, p. 33').get_attribute('href').endswith('LWVAA-VG-EN.pdf#page=33')
    # every candidate row carries exactly two link slots (site + guide): symmetric
    for row in pg.locator('#rc070 .optw').all():
        assert row.locator('.links > *').count() == 2, row.inner_text()
    assert 'League of Women Voters of the Austin Area 2026 Voters Guide' in body
    srcs = [a.get_attribute('href') for a in pg.locator('#rc070 .srcs a').all()]
    assert srcs[0].endswith('#page=32') and any('austintexas.gov/voterinfo' in s for s in srcs), srcs
    ctx.close()

@test
def measure_card_prop_a(b):
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg); open_race(pg, 'c071')
    body = pg.inner_text('#rc071')
    assert 'principle of and interest in bonds' in body          # verbatim, typos included
    assert '$65.5M' in body and '$14.34' in body and 'the City may sell these bonds' in body
    assert 'Supporters' not in body and 'Opponents' not in body     # Lane: no argument boxes
    pick(pg, 'c071', 'For')
    assert pg.locator('#rc071 .opt[aria-pressed=true]').inner_text().strip() == 'For'
    ctx.close()

@test
def where_to_vote_sorted_by_distance(b):
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg)
    sites = pg.locator('#sites .site')
    assert sites.count() == 5, sites.count()
    d = [float(re.search(r'([\d.]+) mi', s.inner_text()).group(1)) for s in sites.all()]
    assert d == sorted(d) and d[0] < 1, d
    first5 = pg.inner_text('#sites')
    for name in ['Austin Recreation Center', 'Travis County Civil and Family Courts Facility', 'UT Texas Union']:
        assert name in first5, first5
    assert 'Open till 10pm Oct 29–30' in first5
    pg.click('#allsites'); assert pg.locator('#sites .site').count() == 45
    pg.click('#t-eday'); assert pg.locator('#sites .site').count() == 201
    assert 'Election%20Day' in pg.get_attribute('#waits', 'href')
    ctx.close()

def make_picks(pg):
    pick(pg, 'c070', 'Qadri'); pg.fill('#wc070', 'Knows the district')
    pick(pg, 'c071', 'For'); pg.fill('#wc071', 'More shade and pools near us.')
    pick(pg, 'c001', 'Ted Brown')
    open_race(pg, 'c002'); pg.click('#rc002 .skip') if pg.locator('#rc002').count() else None

@test
def keep_link_round_trip(b):
    sent = []
    ctx, pg = new_page(b, sent); pg.goto(BASE); lookup(pg); make_picks(pg)
    pg.click('#a-keep'); assert 'live only in this browser' in pg.inner_text('#keepcount')
    pg.click('#keep-copy')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'keep_created')")
    url = pg.inner_text('#keep-out')
    assert '#k=' in url and ['keep_created', {'via': 'copy'}] in events(pg)
    ctx.close()
    sent2 = []
    ctx, pg = new_page(b, sent2); pg.goto(url.replace(url.split('/index.html')[0], f'http://127.0.0.1:{PORT}'))
    assert pg.evaluate('location.hash') == '', 'fragment must be stripped from the address bar'
    pg.wait_for_selector('#d-restore[open]')
    s = pg.inner_text('#restoresum'); assert 'Precinct 300' in s and 'of 63' in s, s
    pg.click('#restore-go')
    pg.wait_for_selector('#result:not(.hidden)')
    assert pg.text_content('#k-total') == '63'
    assert 'Qadri' in pg.inner_text('#sc070') and pg.input_value('#wc071') == 'More shade and pools near us.'
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'keep_restored')")
    for u in sent + sent2:
        assert '#k=' not in u and 'shade' not in urllib.parse.unquote(u), u
    ctx.close()

@test
def share_friend_compare_and_events(b):
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg); make_picks(pg)
    pg.click('#a-share')
    assert names(pg).count('share_sheet_open') == 1
    toggles = pg.locator('#sharesecs input')
    assert toggles.count() >= 2 and all(t.is_checked() for t in toggles.all()), 'every section starts on'
    assert pg.is_checked('#sharewhy'), 'reasons start on'
    pg.fill('#sharename', 'Maya')
    fed = pg.locator('#sharesecs .sw', has_text='Federal').locator('input'); fed.click()   # leave Federal out
    summ = pg.inner_text('#sharesum'); assert 'They’ll see 2 picks and 2 reasons' in summ, summ
    pg.click('#share-go')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'share_created')")
    url = pg.inner_text('#share-out')
    ev = [e for e in events(pg) if e[0] == 'share_created'][0][1]
    assert ev['reasons'] == 'yes' and ev['picks'] == '1-5' and ev['via'] == 'copy' and ev['generation'] == 1 and re.fullmatch(r'[a-z2-9]{8}', ev['link']), ev
    assert 'federal' not in ev['sections'] and 'city' in ev['sections'], ev
    pg.click('#sharewhy')                                   # reasons off: the link must carry none
    assert 'and 0 reasons' in pg.inner_text('#sharesum')
    pg.click('#share-go')
    pg.wait_for_function("(window.__events||[]).filter(e => e[0] === 'share_created').length === 2")
    o = pg.evaluate("b64d(document.getElementById('share-out').textContent.split('#s=')[1])")
    assert not o.get('w') and len(o['p']) == 2, o
    assert [e for e in events(pg) if e[0] == 'share_created'][1][1]['reasons'] == 'no'
    ctx.close()
    sent = []
    ctx, pg = new_page(b, sent); pg.goto(url.replace(url.split('/index.html')[0], f'http://127.0.0.1:{PORT}'))
    assert pg.evaluate('location.hash') == ''
    pg.wait_for_selector('#friend:not(.hidden)')
    f = pg.inner_text('#friend')
    assert 'Maya shared 2 picks' in f and 'Qadri' in f and '“More shade and pools near us.”' in f and 'Ted Brown' not in f, f
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'share_opened')")
    op = [e for e in events(pg) if e[0] == 'share_opened'][0][1]
    assert op == {'generation': 1, 'has_picks': 'no', 'link': ev['link']}, op
    pg.reload(); pg.wait_for_selector('#friend:not(.hidden)')       # survives a refresh, and is not double-counted
    pg.wait_for_timeout(1500)
    assert names(pg).count('share_opened') == 0
    pg2 = ctx.new_page(); pg2.goto(url.replace(url.split('/index.html')[0], f'http://127.0.0.1:{PORT}'))   # same link, new tab
    pg2.wait_for_selector('#friend:not(.hidden)'); pg2.wait_for_timeout(1500)
    assert names(pg2).count('share_opened') == 0, events(pg2)
    pg2.close()
    pg.click('#f-cmp'); assert 'Look up your ballot first' in pg.inner_text('#lookupmsg')
    lookup(pg)
    pg.wait_for_selector('#compare:not(.hidden)')
    c = pg.inner_text('#compare'); assert 'You and Maya' in c and 'you haven’t picked' in c, c
    pg.wait_for_function("['share_own_ballot','share_compare'].every(n => (window.__events||[]).some(e => e[0] === n))")
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.gen'))") == 2
    for e in events(pg):            # nothing personal ever rides along
        blob = json.dumps(e)
        assert 'Qadri' not in blob and 'Maya' not in blob and '300' not in blob and 'Guadalupe' not in blob, blob
    for u in sent:
        assert '#s=' not in u and 'Maya' not in u, u
    ctx.close()

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
    ctx.close()

@test
def feedback_never_includes_fragment(b):
    # The mailto body is built from baseURL() (origin + path), never location.href.
    import base64
    s = base64.urlsafe_b64encode(json.dumps({'v': 1, 'n': 'Al', 'c': 'abcdefgh', 'g': 1, 'p': {'70': 0}}).encode()).decode().rstrip('=')
    ctx, pg = new_page(b); pg.goto(BASE + '#s=' + s); pg.wait_for_selector('#friend:not(.hidden)')
    pg.evaluate("window.__mail=null; const d=Object.getOwnPropertyDescriptor(Location.prototype,'href');")
    src = (ROOT / 'index.html').read_text()
    assert "'\\nPage: ' + baseURL()" in src and "Page: ' + location.href" not in src
    assert pg.evaluate('baseURL()') == BASE
    ctx.close()

import base64
def link(kind, o): return BASE + '#' + kind + '=' + base64.urlsafe_b64encode(json.dumps(o).encode()).decode().rstrip('=')
def fresh_goto(pg, url): pg.goto('about:blank'); pg.goto(url)

@test
def audit_a1_a2_a3_guide_data(b):
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg)
    open_race(pg, 'c006')
    dx = pg.locator('#rc006 .optw', has_text='Pat Dixon')
    assert dx.locator('a', has_text='Campaign site').get_attribute('href') == 'https://patdixon.org', dx.inner_text()   # A1
    L = pg.evaluate('DATA.learn')
    assert L['c017']['cands']['Thomas Smith']['s'] == 'https://www.smithfortexas.org'                                  # A1
    assert L['c131']['cands']['Mike Randolph'] == {'g': 1, 'p': 50, 'a': 1}                                            # A2
    assert L['c129']['cands']['Josh Castro']['a'] == 0 and L['c129']['cands']['Josh Castro']['g'] == 1                  # A2
    assert L['c063']['lwvRace'] == 1                                                                                     # A2
    assert L['c065']['cands']['Yvonne Muñoz'] == {'g': 1, 'p': 25, 'a': 1}                                             # B1 contested, answered
    assert L['c055']['cands']['Brigid Shea'] == {'g': 1, 'p': 24, 'a': 0, 'u': 1}                                     # C1 side-by-side names
    open_race(pg, 'c034')                                                                                                # A3
    t = pg.inner_text('#rc034')
    assert 'Unopposed · no questions in the League guide' in t and 'League guide answers' not in t and 'Lists this race as unopposed' in t, t
    ctx.close()

@test
def audit_a4_a9_keep_link_limits(b):
    ctx, pg = new_page(b)
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1] * 5000, 'p': {}}))
    assert 'damaged' in pg.inner_text('#lookupmsg') and pg.locator('#d-restore[open]').count() == 0                   # A4 over cap
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [], 'p': {'1': 0}}))
    assert 'damaged' in pg.inner_text('#lookupmsg') and pg.locator('#d-restore[open]').count() == 0                   # A9 empty ballot
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, -1, 1, 6], 'p': {'1': 1}}))
    pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go')
    assert pg.locator('#rc001').count() == 1 and pg.text_content('#k-total') == '2'                                   # A4 de-duplicated
    ctx.close()
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg); pick(pg, 'c001', 'Ted Brown')
    fresh_goto(pg, link('k', {'v': 1, 'pr': '999', 'b': [1], 'p': {}}))
    pg.wait_for_selector('#d-restore[open]')
    w = pg.inner_text('#restorewarn')
    assert 'Precinct 999' in w and 'Precinct 300' in w and 'picks and reasons' in w, w                                 # A9
    assert pg.evaluate('document.activeElement.textContent.trim()') == 'Not now'                                         # A13
    ctx.close()

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
def audit_a6_sheet_padding_tap_keeps_it_open(b):
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg); pick(pg, 'c001', 'Ted Brown')
    pg.click('#a-share'); r = pg.locator('#d-share').bounding_box()
    pg.mouse.click(r['x'] + 6, r['y'] + r['height'] / 2)                       # inside the sheet's left padding
    assert pg.locator('#d-share[open]').count() == 1
    pg.mouse.click(r['x'] + 20, max(5, r['y'] - 40))                           # the backdrop above it
    assert pg.locator('#d-share[open]').count() == 0
    ctx.close()

@test
def audit_a7_same_tab_link(b):
    ctx, pg = new_page(b); pg.goto(BASE)
    pg.goto(link('s', {'v': 1, 'n': 'Al', 'c': 'sametab2', 'g': 1, 'p': {'70': 0}}))   # same document: only the fragment changes
    pg.wait_for_selector('#friend:not(.hidden)', timeout=5000)
    assert pg.evaluate('location.hash') == ''
    ctx.close()

@test
def audit_a10_a11_generation_and_own_ballot(b):
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg); pick(pg, 'c001', 'Ted Brown')
    pg.click('#a-share'); pg.click('#share-go')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'share_created')")
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.gen'))") == 1                                         # A10
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Bo', 'c': 'gen4link', 'g': 4, 'p': {'1': 0}}))
    pg.wait_for_selector('#friend:not(.hidden)')
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.gen'))") == 1                                         # A10
    pg.click('#f-own')                                                                                                   # saved ballot already on screen
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'share_own_ballot')")                                 # A11
    ctx.close()

@test
def audit_a14_a15_tracker_and_targets(b):
    src = (ROOT / 'index.html').read_text()
    assert '<script defer src="umami.js"' in src and 'cloud.umami.is/script.js"' not in src                             # A14
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg); open_race(pg, 'c070')
    h = pg.locator('#rc070 .links a').first.bounding_box()['height']
    assert h >= 24, h                                                                                                    # A15
    ctx.close()

@test
def audit_b3_b4_counts_and_dedupe(b):
    ctx, pg = new_page(b)
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, 1, 1, 99999], 'p': {'1': 0}}))
    pg.wait_for_selector('#d-restore[open]')
    assert '1 of 1 contests' in pg.inner_text('#restoresum'), pg.inner_text('#restoresum')                            # B3
    fresh_goto(pg, 'about:blank'); fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1], 'p': {'1': 0, '6': 0, '70': 0}}))
    pg.wait_for_selector('#d-restore[open]')
    assert '1 of 1 contests' in pg.inner_text('#restoresum'), pg.inner_text('#restoresum')                            # C5
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, 1, 1, 99999], 'p': {'1': 0}}))
    pg.wait_for_selector('#d-restore[open]')
    pg.click('#restore-go')
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Al', 'g': 1, 'p': {'1': 0}}))                                              # no link code
    pg.wait_for_selector('#friend:not(.hidden)')
    pg.click('#f-own'); pg.click('#f-own'); pg.wait_for_timeout(1500)
    assert names(pg).count('share_own_ballot') == 1, events(pg)                                                       # B4
    ctx.close()

def main():
    srv = serve()
    failed = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        for fn in TESTS:
            try:
                fn(b); print('PASS', fn.__name__)
            except Exception as e:
                failed += 1; print('FAIL', fn.__name__, '-', (str(e) or type(e).__name__)[:400])
        b.close()
    srv.shutdown()
    print(f'{len(TESTS) - failed}/{len(TESTS)} passed')
    sys.exit(1 if failed else 0)

if __name__ == '__main__':
    main()
