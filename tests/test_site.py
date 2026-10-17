"""End-to-end checks for the Ballotta test site (index.html), run against the live Travis County lookup services.

    python3 tests/test_site.py                                    # builds nothing; checks the live page (index.html)
    BALLOTTA_PAGE=next/index.html python3 tests/test_site.py      # checks the preview, phone layout included

Analytics: cloud.umami.is is stubbed so each test can see exactly which events (and which details) would be sent.
"""
import http.server, threading, functools, json, pathlib, re, sys, traceback, urllib.parse, hashlib, importlib.util, os
from playwright.sync_api import sync_playwright, expect

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = int(os.environ.get('BALLOTTA_PORT', '8765'))
PAGE = os.environ.get('BALLOTTA_PAGE', 'index.html')
BASE = f'http://127.0.0.1:{PORT}/{PAGE}'
HAS_DESK = 'id="dk-app"' in (ROOT / PAGE).read_text(encoding='utf-8')
HAS_PHONE = 'id="ph-bar"' in (ROOT / PAGE).read_text(encoding='utf-8')
# sha256 of the live index.html as built from commit 06b7030 (Oct 15). The phone layout must not change it until
# Lane promotes the preview. A data rebuild (ballot or League data) changes it legitimately: re-pin it in that commit.
LIVE_SHA = 'e9c4086f4dbfa41272f59b8a9e5fc7dd55913583c446e81c5c63332cc46fde7b'  # round J (Oct 17): pick column; "Print your choices"; "My ballot choices"; title spacing and size
UMAMI_STUB = "window.__events=[];window.umami={track:function(n,d){window.__events.push([n,d||{}]);}};"

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve():
    h = functools.partial(Quiet, directory=str(ROOT))
    s = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s

def new_page(browser, sent=None, wide=False, csp=False, touch=False, size=None, sw=False, ua=None):
    # The page's Content-Security-Policy (#36) forbids eval, which Playwright's wait_for_function polls with: tests run
    # with it bypassed unless they ask (csp=True), and those poll from Python instead (see poll()). The offline copy
    # (sw.js) is blocked unless a test asks (sw=True): a service worker would answer requests the stubs below expect.
    ctx = browser.new_context(viewport=size or ({'width': 1440, 'height': 900} if wide else {'width': 400, 'height': 900}), permissions=['clipboard-read', 'clipboard-write'],
                              bypass_csp=not csp, has_touch=touch, service_workers='allow' if sw else 'block', **({'user_agent': ua} if ua else {}))
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
    assert ['ballot_found', {'match': 'exact', 'layout': 'phone'}] in ev and ['lookup_started', {'layout': 'phone'}] in ev, ev
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
    frag = url.split('#', 1)[1]
    assert re.fullmatch(r'k2[A-Za-z0-9_-]{16,}', frag), url                 # v2: nothing after '#' that chat apps cut at
    assert ['keep_created', {'via': 'copy', 'layout': 'phone'}] in events(pg)
    ctx.close()
    sent2 = []
    ctx, pg = new_page(b, sent2); pg.goto(url)
    assert pg.evaluate('location.hash') == '', 'fragment must be stripped from the address bar'
    pg.wait_for_selector('#d-restore[open]')
    s = pg.inner_text('#restoresum'); assert 'Precinct 300' in s and 'of 63' in s, s
    pg.click('#restore-go')
    pg.wait_for_selector('#result:not(.hidden)')
    assert pg.text_content('#k-total') == '63'
    assert 'Qadri' in pg.inner_text('#sc070') and pg.input_value('#wc071') == 'More shade and pools near us.'
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'keep_restored')")
    for u in sent + sent2:
        assert frag[2:40] not in u and 'shade' not in urllib.parse.unquote(u), u
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
    o = pg.evaluate("unpackFrag(document.getElementById('share-out').textContent.split('#')[1])")
    assert not o.get('w') and len(o['p']) == 2, o
    assert [e for e in events(pg) if e[0] == 'share_created'][1][1]['reasons'] == 'no'
    ctx.close()
    sent = []
    ctx, pg = new_page(b, sent); pg.goto(url)
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
        assert url.split('#', 1)[1][2:40] not in u and 'Maya' not in u, u
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
    src = (ROOT / PAGE).read_text()
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
    src = (ROOT / PAGE).read_text()
    assert re.search(r'<script defer src="(\.\./)?umami\.js"', src) and 'cloud.umami.is/script.js"' not in src            # A14
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

@test
def double_tap_share_counts_once(b):
    ctx, pg = new_page(b)
    pg.add_init_script("navigator.share = () => new Promise(r => setTimeout(r, 800));")   # a share sheet that stays open a moment
    pg.goto(BASE); lookup(pg); pick(pg, 'c001', 'Ted Brown')
    pg.click('#a-share'); pg.fill('#sharename', 'Dee'); pg.wait_for_timeout(200)
    pg.click('#share-go'); pg.click('#share-go', force=True); pg.wait_for_timeout(1500)
    made = [e for e in events(pg) if e[0] == 'share_created']
    assert len(made) == 1 and made[0][1]['via'] == 'share', made
    ctx.close()

# ---------- laptop layout (preview build only; skipped when the page has no laptop layout) ----------
DESK_TESTS = set()
def desk_test(fn): TESTS.append(fn); DESK_TESTS.add(fn.__name__); return fn
PHONE_TESTS = set()                                            # run only where the page has the phone layout (the preview)
def phone_test(fn): TESTS.append(fn); PHONE_TESTS.add(fn.__name__); return fn
# These drive the phone page as it is live today (the accordion list, its cards and buttons). On the preview a phone
# gets the new layout instead, so they run on index.html only; promotion moves them to the new layout (plan, Task 13).
OLD_PHONE_TESTS = {
    'audit_a10_a11_generation_and_own_ballot', 'audit_a14_a15_tracker_and_targets', 'audit_a1_a2_a3_guide_data',
    'audit_a4_a9_keep_link_limits', 'audit_a6_sheet_padding_tap_keeps_it_open', 'audit_b3_b4_counts_and_dedupe',
    'backup_nudge_after_fifth_pick', 'counts_progress_sources_and_clearing', 'counts_where_people_drop_off',
    'desk_crib_options_and_print', 'desk_failures_never_break_the_phone_flow', 'desk_landing_plum_band_and_faq',
    'desk_old_link_warning_gone_after_new_lookup', 'desk_resize_keeps_layouts_in_step', 'desk_stays_quiet_on_phones',
    'desk_why_box_grows_with_the_reason', 'double_tap_share_counts_once', 'extra_pick_is_explained',
    'friend_card_long_names_and_honest_copy', 'keep_link_round_trip', 'lookup_courthouse_and_ballot_found',
    'measure_card_prop_a', 'page_is_locked_down', 'persistent_storage_asked_at_first_pick',
    'phone_can_clear_everything_from_the_footer', 'phone_new_day_keeps_focus_on_a_directions_link',
    'race_learn_more_is_symmetric_and_attributed', 'share_friend_compare_and_events', 'stored_junk_in_share_fields',
    'stored_junk_never_breaks_keep_or_share', 'where_to_vote_sorted_by_distance'
}

def build_module():
    spec = importlib.util.spec_from_file_location('build_site', ROOT / 'source' / 'build_site.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def lookup_wide(pg, street='1000 Guadalupe St', zip_='78701'):
    pg.fill('#street', street); pg.fill('#zip', zip_); pg.click('#go')
    pg.wait_for_selector('body.dk-app-on', timeout=30000)
    pg.wait_for_function("/ of \\d+ decided$/.test(document.getElementById('dk-count').textContent)", timeout=30000)

def cur(pg, cid): return pg.evaluate(f"current('{cid}')")

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
    if m.PHONE_LIVE:
        assert 'id="ph-bar"' in live and "worker-src 'self'" in live, 'promoted: the live page carries the phone layout'
    else:
        assert 'id="ph-bar"' not in live and 'PHONE' not in live and 'rel="manifest"' not in live and "worker-src" not in live, 'phone layout leaked into the live build'
        got = hashlib.sha256(live.encode('utf-8')).hexdigest()
        assert got == LIVE_SHA, f'live index.html changed ({got}). Expected only after a data rebuild: re-pin LIVE_SHA in that commit.'
        assert (ROOT / 'next/index.html').read_bytes() == prev.encode('utf-8'), 'next/index.html on disk is not what the build writes'
        assert (ROOT / 'next/manifest.webmanifest').read_text(encoding='utf-8') == m.manifest(True) and (ROOT / 'next/sw.js').read_text(encoding='utf-8') == (m.sw_js(True) if m.OFFLINE else m.sw_off_js(True))
        assert not (ROOT / 'sw.js').exists() and not (ROOT / 'manifest.webmanifest').exists(), 'no offline copy on the live site before promotion'
    assert 'id="ph-bar"' in prev and "manifest-src 'self'; worker-src 'self'" in prev and '"name": "Ballotta (preview)"' in m.manifest(True)
    assert 'id="dk-app"' in prev and 'data-domains="preview.invalid"' in prev and 'src="../umami.js"' in prev
    assert (ROOT / 'index.html').read_bytes() == live.encode('utf-8'), 'index.html on disk is not what the build writes (stale, left mutated, or its line endings changed)'
    if not m.PHONE_LIVE: assert hashlib.sha256((ROOT / 'index.html').read_bytes()).hexdigest() == LIVE_SHA, 'the file on disk differs from the pinned live page'
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
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.whys')).c070") == 'Knows the district s'
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
def desk_why_box_grows_with_the_reason(b):
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
    pg.set_viewport_size({'width': 400, 'height': 900}); open_race(pg, 'c070'); pg.wait_for_timeout(100)
    assert pg.evaluate("getComputedStyle(document.getElementById('wc070')).height") == '70px', 'phones unchanged until the phone round'
    open_race(pg, 'c071'); pg.click('#wc071'); pg.keyboard.type(LONG_WHY)
    assert pg.evaluate("(() => { const t = document.getElementById('wc071'); return getComputedStyle(t).height + '|' + t.style.height; })()") == '70px|', 'typing on a phone leaves the box as it is today'
    ctx.close()

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
    pg.click('#dk-all'); assert pg.locator('#dk-sites .dk-site').count() == 45
    pg.click('[data-period="eday"]'); assert pg.locator('#dk-sites .dk-site').count() == 201
    assert 'Election%20Day' in pg.locator('#dk-paper a.btn').get_attribute('href')
    for u in sent:                                                                                # drawn on the page: no map service sees the address
        assert not re.search(r'tile|maps\.googleapis|openstreetmap|mapbox|arcgisonline', u), u
    ctx.close()

@desk_test
def desk_crib_options_and_print(b):
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
    pg.emulate_media(media='screen'); pg.set_viewport_size({'width': 400, 'height': 900})
    pg.wait_for_function("!document.getElementById('crib').classList.contains('two')", timeout=3000)   # the resize event lands a frame later
    assert t034 in pg.inner_text('#crib'), 'laptop print options stay on the laptop'
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
    for _ in range(6): pg.keyboard.press('Tab')                                                  # tab out of the menu
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
def desk_failures_never_break_the_phone_flow(b):
    ctx, pg = new_page(b); pg.add_init_script(JUNK_STORAGE)
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    fresh_goto(pg, link('s', DESK_FRIEND)); pg.wait_for_selector('#friend:not(.hidden)', timeout=5000)   # a non-text reason in storage
    pg.evaluate("() => { for (const k of ['ballot', 'refresh', 'cribSkip']) desk[k] = () => { throw new Error('boom'); }; }")   # even if laptop code throws
    pg.click('#f-own'); lookup(pg)
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'ballot_found')", timeout=30000)
    assert 'United States Senator' in pg.inner_text('#crib') and not errs, errs                          # the crib sheet still renders
    assert 'lookup_failed' not in names(pg) and pg.locator('#status.bad').count() == 0, 'a laptop-code failure is not reported as a county outage'
    ctx.close()
    ctx, pg = new_page(b, wide=True); pg.add_init_script(JUNK_STORAGE); pg.goto(BASE)
    pg.wait_for_selector('body.dk-app-on'); assert pg.locator('.dk-row').count() == 2
    ctx.close()

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
def desk_stays_quiet_on_phones(b):
    ctx, pg = new_page(b); fresh_goto(pg, link('s', DESK_FRIEND)); pg.wait_for_selector('#friend:not(.hidden)')
    assert pg.is_hidden('#dk-hdr') and pg.is_hidden('#dk-app') and pg.is_visible('main.wrap') and pg.is_visible('#f-own')
    pg.click('#f-own'); lookup(pg); pg.wait_for_timeout(1000)
    assert names(pg).count('share_compare') == 0, 'the hidden laptop layout must not count a compare'
    pg.evaluate('document.activeElement.blur()')                                                # not typing in the address box
    pg.keyboard.press('1'); assert cur(pg, 'c001') == [], 'no laptop shortcuts on a phone'
    ctx.close()

@desk_test
def desk_resize_keeps_layouts_in_step(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c001"]'); pg.locator('.dk-line', has_text='Ted Brown').click()
    pg.set_viewport_size({'width': 400, 'height': 900})
    assert pg.is_visible('#result') and 'Ted Brown' in pg.inner_text('#sc001')
    pick(pg, 'c070', 'Qadri'); open_race(pg, 'c001'); pg.fill('#wc001', 'Typed on the phone')
    pg.set_viewport_size({'width': 1440, 'height': 900})
    assert 'Qadri' in pg.inner_text('.dk-row[data-row="c070"]') and pg.inner_text('#dk-count') == '2 of 63 decided'
    pg.wait_for_function("document.getElementById('dk-w').value === 'Typed on the phone'", timeout=3000)   # redrawn on the resize event
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
def desk_landing_plum_band_and_faq(b):
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
    ctx, pg = new_page(b); pg.goto(BASE)                                                              # phones: the next round, not this one
    assert pg.is_hidden('#dk-hero') and pg.is_hidden('#dk-faq')
    ctx.close()

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
    ctx = b.new_context(viewport={'width': 1366, 'height': 1024}, has_touch=True, is_mobile=True)    # #35: a tablet in landscape
    ctx.route(re.compile(r'.*/umami\.js$'), lambda r: r.fulfill(status=200, content_type='application/javascript', body=UMAMI_STUB))
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
        html = m.build(desk=desk)
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
    assert bs({'name': 'not_an_event', 'data': {}}) is None, 'an unlisted event never leaves the browser'
    got = bs({'name': 'lookup_failed', 'data': {'reason': 'not_found', 'street': '1000 Guadalupe St', 'layout': 'phone'}, 'id': 'someone', 'url': '/'})
    assert got['data'] == {'reason': 'not_found', 'layout': 'phone'} and 'id' not in got and got['url'] == '/', got
    assert bs({'name': 'lookup_failed', 'data': {'reason': '1000 Guadalupe St'}})['data'] == {}, 'a value off the list is dropped'
    assert bs({'name': 'progress', 'data': {'at': {'x': 1}}})['data'] == {}, 'objects are never values'
    assert bs({'name': 'share_created', 'data': {'sections': ['federal']}})['data'] == {}, 'arrays are never values'
    assert bs({'url': '/', 'title': 'Ballotta'}) == {'url': '/', 'title': 'Ballotta'}, 'page views pass'
    # Verification pass: payloads without a name, other payload types and extra fields can't carry anything either.
    assert bs({'url': '/', 'data': {'street': '1000 Guadalupe St'}, 'precinct': '300'}) == {'url': '/'}, 'a page view carries no details'
    odd = {'url': '/?addr=1000+Guadalupe#k=x', 'referrer': 'https://forum.example/thread/1000-guadalupe-st?q=1', 'title': {'street': 'x'}, 'tag': ['78701'], 'website': 'w'}
    assert bs(odd) == {'url': '/', 'referrer': 'https://forum.example', 'website': 'w'}, 'only text fields; no query or fragment; a referrer is just its site'
    assert bs({'url': '/', 'referrer': 'not a url'}) == {'url': '/', 'referrer': ''}
    assert bs({'referrer': 'android-app://com.google.android.googlequicksearchbox/'}) == {'referrer': 'android-app://com.google.android.googlequicksearchbox'}, 'an app referrer keeps its name'
    assert bs({'referrer': 'about:blank'}) == {'referrer': ''} and bs({'referrer': 'file:///x'}) == {'referrer': ''}, 'never the string "null"'
    assert pg.evaluate('window.ballottaBeforeSend("identify", { data: { street: "1000 Guadalupe St" } })') is None, 'no session data'
    perf = pg.evaluate('window.ballottaBeforeSend("performance", { url: "/", lcp: 812.5, cls: 0.01, street: "x", data: { a: 1 } })')
    assert perf == {'url': '/', 'lcp': 812.5, 'cls': 0.01}, perf
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
    plain = build_module().build(desk=False)                                                    # after a rollback, wide screens are phones
    ctx, pg = new_page(b, wide=True); ctx.route('**/_rollback.html', lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=plain))
    pg.goto(f'http://127.0.0.1:{PORT}/_rollback.html'); pg.evaluate("track('faq_seen')")
    assert events(pg)[-1] == ['faq_seen', {'layout': 'phone'}], events(pg)
    ctx.close()

@test
def real_tracker_sends_only_listed_events(b):
    # The real pinned umami.js, pointed at this test server: every request it makes is caught and checked.
    TOP = {'website', 'hostname', 'screen', 'language', 'title', 'url', 'referrer', 'tag', 'name', 'data', 'ttfb', 'fcp', 'lcp', 'cls', 'inp', 'duration'}
    for gpc in ('', "Object.defineProperty(Navigator.prototype, 'globalPrivacyControl', { get: () => true })",
                "Object.defineProperty(Navigator.prototype, 'doNotTrack', { get: () => '1' })"):
        sent = []
        ctx = b.new_context(viewport={'width': 400, 'height': 900})
        if gpc: ctx.add_init_script(gpc)
        def page(route):
            r = route.fetch(); body = r.text().replace('data-domains="ballotta.org,www.ballotta.org,lanebecker.github.io"', 'data-domains="127.0.0.1"')
            route.fulfill(response=r, body=body)
        ctx.route(re.compile(r'.*/index\.html$|.*:%d/$' % PORT), page)
        ctx.route('https://gateway.umami.is/**', lambda r: (sent.append(r.request.post_data_json), r.fulfill(status=200, content_type='application/json', body='{}')))
        pg = ctx.new_page(); pg.goto(f'http://127.0.0.1:{PORT}/index.html')
        lookup(pg); pick(pg, 'c070', 'Qadri'); pg.wait_for_timeout(1500)
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
                assert not re.search(r'Guadalupe|78701|Precinct|Qadri', blob), blob
        ctx.close()

@test
def counts_where_people_drop_off(b):
    ctx, pg = new_page(b); pg.goto(BASE)
    pg.click('#go'); pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '787'); pg.click('#go')
    assert [e[1].get('reason') for e in events(pg) if e[0] == 'lookup_failed'] == ['no_street', 'bad_zip']
    pg.evaluate("chooseUnit({ a: [{ Unit: '1' }], b: [{ Unit: '2' }] }, '1 Main St', null)")
    assert names(pg).count('units_asked') == 1
    lookup(pg)
    assert names(pg).count('lookup_started') == 1 and names(pg).count('address_changed') == 0 and names(pg).count('ballot_found') == 1
    found = lambda k: pg.wait_for_function(f"(window.__events||[]).filter(e => e[0] === 'ballot_found').length === {k}", timeout=30000)
    lookup(pg); found(2)                                                                         # the same address again: not a change
    assert names(pg).count('address_changed') == 0
    pg.evaluate("renderStored({ pr: '9', b: [1, 2], mode: 'saved' }, 'test')"); lookup(pg); found(3)   # a different ballot was showing
    assert names(pg).count('address_changed') == 1
    journey_check(pg, 'phone'); ctx.close()
    ctx, pg = new_page(b); ctx.route(re.compile(r'https://taxmaps\.traviscountytx\.gov/.*'), lambda r: r.abort()); pg.goto(BASE)
    pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '78701'); pg.click('#go')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'lookup_failed')", timeout=15000)
    assert events(pg)[-1] == ['lookup_failed', {'reason': 'county_unreachable', 'layout': 'phone'}]; ctx.close()
    def census(route, match):
        cb = re.search(r'callback=([A-Za-z0-9_]+)', route.request.url).group(1)
        m = '[{"coordinates":{"x":-97.74,"y":30.27},"matchedAddress":"1 NOWHERE ST, AUSTIN, TX, 78701"}]' if match else '[]'
        route.fulfill(status=200, content_type='application/javascript', body=cb + '({"result":{"addressMatches":' + m + '}})')
    for match, reason, va in ((False, 'not_found', 'empty'), (True, 'no_voters_nearby', 'empty'), (True, 'county_unreachable', 'down')):
        ctx, pg = new_page(b)
        ctx.route(re.compile(r'.*GeocodeServer/findAddressCandidates.*'), lambda r: r.fulfill(status=200, content_type='application/json', body='{"candidates":[]}'))
        ctx.route(re.compile(r'.*VotingAddresses/VA/MapServer/0/query.*'), (lambda v: lambda r: r.abort() if v == 'down' else r.fulfill(status=200, content_type='application/json', body='{"features":[]}'))(va))
        ctx.route(re.compile(r'https://geocoding\.geo\.census\.gov/.*'), (lambda m: lambda r: census(r, m))(match))   # Playwright passes the request as a 2nd argument
        pg.goto(BASE); pg.fill('#street', '1 Nowhere St'); pg.fill('#zip', '78701'); pg.click('#go')
        pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'lookup_failed')", timeout=15000)
        assert events(pg)[-1] == ['lookup_failed', {'reason': reason, 'layout': 'phone'}], events(pg)
        if va == 'down': assert 'couldn’t reach Travis County’s map server' in pg.inner_text('#status'), 'no longer stuck on "Finding your address"'
        ctx.close()
    ctx, pg = new_page(b); pg.goto(BASE + '#s=not-a-real-payload')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'link_damaged')")
    assert events(pg)[-1] == ['link_damaged', {'kind': 'damaged', 'layout': 'phone'}]
    frag = pg.evaluate("packFrag('s', { v: 1, n: 'Ana', c: 'abcd2345', g: 1, p: { 70: 0 } })"); ctx.close()
    ctx, pg = new_page(b); pg.add_init_script('delete window.DecompressionStream'); pg.goto(BASE + '#' + frag)   # an old browser
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'link_damaged')")
    assert events(pg)[-1] == ['link_damaged', {'kind': 'too_old', 'layout': 'phone'}], events(pg); ctx.close()

@test
def counts_progress_sources_and_clearing(b):
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg); no_link_opens(pg)
    n = pg.evaluate('ballot.length')
    pg.evaluate("ballot.slice(0, Math.ceil(ballot.length / 4)).forEach(x => pick(x.c.id, '__skip'))")
    prog = lambda: [e[1] for e in events(pg) if e[0] == 'progress']
    assert prog() == [{'at': '25', 'reasons': '0', 'skipped': '6+', 'layout': 'phone'}], prog()
    pg.evaluate("ballot.forEach(x => { if (!current(x.c.id).length) pick(x.c.id, '__skip'); })")
    assert [p['at'] for p in prog()] == ['25', '50', '75', '100'], (n, prog())
    pg.evaluate("renderStored({ pr: '9', b: [1, 2, 3, 4], mode: 'saved' }, 'test')")                  # shown already decided: counts nothing
    assert len(prog()) == 4, ('a ballot shown already decided is not progress', prog())
    pg.evaluate("renderStored({ pr: '9', b: [210, 211, 212, 213], mode: 'saved' }, 'test'); pick('c210', '__skip')")
    assert len(prog()) == 5 and prog()[-1]['at'] == '25', ('a pick that crosses a milestone counts', prog())
    assert pg.evaluate("localStorage.getItem('ballotta.progress')") is None, 'nothing about progress is stored'
    pg.evaluate("renderStored(JSON.parse(localStorage.getItem('ballotta.ballot')), 'test')")
    pg.reload(); pg.wait_for_selector('#result:not(.hidden)'); pg.wait_for_timeout(500)
    assert names(pg).count('progress') == 0, 'a returning voter is not counted again (audit #1)'
    pg.evaluate("pick(ballot.find(x => current(x.c.id)[0] === '__skip').c.id, '__skip')")               # un-skip one: still over 75%
    pg.evaluate("pick(ballot.find(x => !current(x.c.id).length).c.id, '__skip')")                      # and decide it again: back to 100%
    assert names(pg).count('progress') == 0, 'milestones reached before the reload are noted when the ballot shows (Pass 2)'
    no_link_opens(pg); open_race(pg, 'c001')
    pg.locator('#rc001 a', has_text='League guide answers').first.click()
    pg.locator('#rc001 a', has_text='Campaign site').first.click()
    src = [e[1] for e in events(pg) if e[0] == 'source_opened']
    assert src == [{'kind': 'league_guide', 'level': 'federal', 'layout': 'phone'}, {'kind': 'campaign_site', 'level': 'federal', 'layout': 'phone'}], src
    for href, kind in (('https://www.texastribune.org/x', 'news'), ('https://ballotpedia.org/x', 'reference'), ('https://votetravis.gov/x', 'official'), ('https://example.com/x', 'other')):
        pg.evaluate("h => { const a = document.createElement('a'); a.href = h; a.textContent = 'x'; a.id = 'tmp-a'; document.body.append(a); a.click(); a.remove(); }", href)
        assert events(pg)[-1] == ['source_opened', {'kind': kind, 'layout': 'phone'}], (href, events(pg)[-1])   # outside a race: no level
    pg.locator('#rc001 a', has_text='League guide answers').first.click(button='middle')            # a middle click opens a link too
    assert events(pg)[-1] == ['source_opened', {'kind': 'league_guide', 'level': 'federal', 'layout': 'phone'}], events(pg)[-1]
    pg.click('#t-early')                                                                         # from Oct 31 the page opens on Election Day
    pg.locator('#sites a', has_text='Directions').first.click(); pg.click('#waits')
    assert events(pg)[-2:] == [['directions_opened', {'period': 'early', 'layout': 'phone'}], ['wait_times_opened', {'period': 'early', 'layout': 'phone'}]], events(pg)[-2:]
    pg.evaluate('window.print = () => {}'); pg.click('#print')
    assert events(pg)[-1] == ['crib_printed', {'two_col': 'no', 'hide_unopposed': 'no', 'layout': 'phone'}]
    pg.once('dialog', lambda d: d.accept()); pg.click('#reset')
    assert events(pg)[-1] == ['cleared', {'what': 'picks', 'layout': 'phone'}]
    journey_check(pg, 'phone')
    LS_KEYS = "Object.keys(localStorage).filter(k => k.startsWith('ballotta.')).concat(Object.keys(sessionStorage).filter(k => k.startsWith('ballotta.')))"
    assert pg.evaluate(LS_KEYS), 'something is saved before clearing'
    pg.evaluate("localStorage.setItem('umami.disabled', '1'); localStorage.setItem('other.site', 'x')")   # not Ballotta's: must survive
    pg.evaluate("umami.track = (n, d) => sessionStorage.setItem('__last', JSON.stringify([n, d]))")   # survives the reload
    pg.once('dialog', lambda d: d.accept()); pg.click('#reset-all')
    pg.wait_for_function("!document.getElementById('result') || document.getElementById('result').classList.contains('hidden')")
    pg.wait_for_load_state()
    assert pg.evaluate(LS_KEYS) == [], pg.evaluate(LS_KEYS)
    assert pg.evaluate("JSON.parse(sessionStorage.getItem('__last'))") == ['cleared', {'what': 'everything', 'layout': 'phone'}]
    assert pg.is_hidden('#result') and pg.evaluate('location.hash') == ''
    assert pg.evaluate("[localStorage.getItem('umami.disabled'), localStorage.getItem('other.site')]") == ['1', 'x'], 'only ballotta.* keys are cleared'
    ctx.close()
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg); pick(pg, 'c070', 'Qadri')                    # another open tab doesn't write it back (audit #5)
    pg2 = ctx.new_page(); pg2.goto(BASE); pg2.wait_for_selector('#result:not(.hidden)')
    pg2.evaluate('window.__mark = 1'); lookup(pg); pg.wait_for_timeout(500)                          # a lookup elsewhere doesn't reload this tab
    assert pg2.evaluate('window.__mark') == 1, 'only Clear everything reloads other tabs (Pass 2)'
    pg.once('dialog', lambda d: d.accept()); pg.click('#reset-all'); pg.wait_for_load_state()
    pg2.wait_for_function("document.getElementById('result').classList.contains('hidden')", timeout=5000)
    pg2.click('#go')
    assert pg2.evaluate(LS_KEYS) == [], ('the other tab started fresh', pg2.evaluate(LS_KEYS))
    ctx.close()
    ctx, pg = new_page(b)                                                                         # storage blocked: Clear everything still clears (audit #4)
    ctx.add_init_script("for (const n of ['localStorage', 'sessionStorage']) Object.defineProperty(window, n, { get() { throw new DOMException('blocked', 'SecurityError'); } })")
    pg.goto(BASE); lookup(pg)
    pg.once('dialog', lambda d: d.accept()); pg.click('#reset-all')
    pg.wait_for_function("document.getElementById('result').classList.contains('hidden')", timeout=10000)
    ctx.close()
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg)                                             # asking first: Cancel keeps everything
    pg.once('dialog', lambda d: d.dismiss()); pg.click('#reset-all')
    assert pg.evaluate("localStorage.getItem('ballotta.ballot')") and pg.is_visible('#result')
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
def stored_junk_never_breaks_keep_or_share(b):
    # #20: an old format or tampering in storage (reasons that aren't text, picks that aren't an object) can't make
    # the page, Keep or Share throw.
    ctx, pg = new_page(b); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(BASE)
    pg.evaluate("localStorage.setItem('ballotta.picks', 'null'); localStorage.setItem('ballotta.whys', JSON.stringify({c070: 5, c071: {x: 1}, c001: ['a']}))")
    pg.reload(); lookup(pg); pick(pg, 'c070', 'Qadri'); pick(pg, 'c071', 'For')
    pg.click('#a-keep'); pg.wait_for_selector('#d-keep[open]')
    assert pg.text_content('#keepcount').startswith('Your 2 picks and 0 reasons'), pg.text_content('#keepcount')
    pg.click('#d-keep [data-close]'); pg.click('#a-share'); pg.wait_for_selector('#d-share[open]')
    assert '0 of these picks have reasons' in pg.text_content('#sharewhycount'), pg.text_content('#sharewhycount')
    assert errs == [], errs
    ctx.close()

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
                'GOPTravis', 'DNCTexas', 'VOTERInfo', 'STATEParty']:   # Pass 4
        assert sn(bad) == '', bad
    for good in ['Maya', 'Ana', 'José', "O'Brien", 'Dempsey', 'Ελένη', 'Ольга', '李明', 'Demetria', 'Gopal', 'Mary-Jane', 'Jean-Paul', 'A J', 'Liz 2',
                 'J R R Tolkien', 'A.J.', 'D J', 'R2-D2', "D'Angelo", 'Estate Jones', 'G O Pal', 'Işıl Yılmaz', 'Partyka', 'Admina',
                 'Gustavo Terrazas', 'Ivo Terzić', 'Felicity Ofori', 'Clerkin', 'DeMarco', 'DeShawn', 'McDonald', 'LaToya',   # Pass 3
                 'Clerkson', 'DeClerck', 'JRRTolkien', 'DJ Khaled', 'MacArthur', 'Gopinath', 'Rajagopal', 'Staten']:   # Pass 4
        assert sn(good) == good, good
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

@test
def friend_card_long_names_and_honest_copy(b):
    # #23: a 30-letter name with no spaces wraps instead of pushing the page sideways (friend card, compare, laptop
    # chip and notes). #24: the card says most races link to neutral sources: 17 small districts have none.
    name = 'Bartholomew' + 'w' * 19
    url = link('s', {'v': 1, 'n': name, 'c': 'abcd2345', 'g': 1, 'p': {'70': 0}, 'w': {'70': 'x'}})
    for wide in ((False, True) if HAS_DESK else (False,)):
        ctx, pg = new_page(b, wide=wide); fresh_goto(pg, url); pg.wait_for_selector('#friend:not(.hidden)')
        txt = pg.text_content('#friend')
        assert 'Most races on your ballot link to neutral sources.' in txt and 'Each race' not in txt, txt
        fits_width = lambda: pg.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        assert fits_width(), ('friend landing scrolls sideways', wide)
        if wide:
            lookup_wide(pg); assert fits_width(), 'laptop app with the friend chip and notes scrolls sideways'
        else:
            lookup(pg); pg.click('#f-cmp'); pg.wait_for_selector('#compare:not(.hidden)')
            assert fits_width(), 'compare scrolls sideways'
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
def extra_pick_is_explained(b):
    # #33: on a "vote for up to 2" race, a third pick changes nothing and says why, under the race's "Vote for up
    # to 2" line, on both layouts; the note clears on the next pick. A refused key pick isn't announced as a pick.
    st = json.dumps({'pr': '999', 'b': [113], 'mode': 'saved', 'at': 0, 'pt': None})
    msg = 'You can pick up to 2. Unpick one first.'
    for wide in ((False, True) if HAS_DESK else (False,)):
        ctx, pg = new_page(b, wide=wide); pg.goto(BASE)
        pg.evaluate('s => localStorage.setItem("ballotta.ballot", s)', st); pg.reload()
        opts = pg.evaluate('optionsOf(BYID.c113)')
        if wide:
            pg.wait_for_selector('body.dk-app-on')
            line = lambda i: pg.locator('#dk-paper .dk-line').nth(i)
            note = pg.locator('#dk-paper [data-limit="c113"]')
        else:
            pg.wait_for_selector('#result:not(.hidden)'); open_race(pg, 'c113')
            line = lambda i: pg.locator('#rc113 .opt').nth(i)
            note = pg.locator('#rc113 [data-limit="c113"]')
        line(0).click(); line(1).click(); expect(note).to_have_text('')
        line(2).click()
        assert pg.evaluate("current('c113')") == opts[:2], pg.evaluate("current('c113')")
        expect(note).to_have_text(msg); assert note.get_attribute('role') == 'status'
        assert line(2).get_attribute('aria-pressed') == 'false'
        if wide:
            pg.focus('#dk-paper'); pg.keyboard.press('3'); pg.wait_for_timeout(300)
            assert pg.evaluate("current('c113')") == opts[:2] and pg.text_content('#dk-live') == '', pg.text_content('#dk-live')
        line(0).click(); expect(note).to_have_text('')
        line(2).click(); assert pg.evaluate("current('c113')") == [opts[1], opts[2]]
        if not wide:                                                               # Clear my picks clears the note too (Pass 1)
            line(0).click(); expect(note).to_have_text(msg)
            pg.once('dialog', lambda d: d.accept()); pg.click('#reset')
            assert pg.evaluate("current('c113')") == []; expect(note).to_have_text('')
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
        assert 'const DATA = ' + odd + ';' in html, preview

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

@desk_test
def desk_old_link_warning_gone_after_new_lookup(b):
    # #40: a damaged-link warning from phone width doesn't reappear after a new lookup and a widen past 1024px.
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg)
    pg.evaluate("location.hash = '#s2' + 'A'.repeat(40)")
    pg.wait_for_function("!document.getElementById('lookupmsg').classList.contains('hidden')", timeout=5000)
    assert not pg.evaluate("document.getElementById('dk-say').classList.contains('hidden')"), 'precondition: the laptop copy holds the warning'
    pg.evaluate("document.getElementById('go').click()")
    pg.wait_for_function("(window.__events||[]).filter(e => e[0] === 'ballot_found').length === 2", timeout=30000)
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(300)
    assert pg.evaluate("document.getElementById('dk-say').classList.contains('hidden')"), 'stale warning came back on the laptop layout'
    ctx.close()

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
def phone_can_clear_everything_from_the_footer(b):
    # #42: someone who only opened a friend's link (no ballot of their own) can still clear what Ballotta stored:
    # a "Clear everything on this device" button in the footer, shown only while this browser holds something.
    ctx, pg = new_page(b); pg.goto(BASE)
    foot = pg.locator('#reset-all-foot')
    expect(foot).to_be_hidden()
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Maya', 'c': 'abcd2347', 'g': 1, 'p': {'70': 0}}))
    pg.wait_for_selector('#friend:not(.hidden)'); expect(foot).to_be_visible()
    pg.once('dialog', lambda d: d.accept()); foot.click()
    pg.wait_for_function("!Object.keys(localStorage).some(k => k.startsWith('ballotta.')) && !Object.keys(sessionStorage).some(k => k.startsWith('ballotta.'))", timeout=5000)
    pg.wait_for_load_state(); expect(foot).to_be_hidden()
    other = ctx.new_page(); other.goto(BASE); other.evaluate("localStorage.setItem('ballotta.name', JSON.stringify('Maya'))")
    expect(foot).to_be_visible(); other.close()                                # another tab saved something (Pass 1)
    pg.evaluate("localStorage.removeItem('ballotta.name'); document.getElementById('reset-all-foot').classList.add('hidden')")
    lookup(pg); expect(foot).to_be_visible()                                   # shown as soon as a lookup saves the ballot
    pg.reload(); pg.wait_for_selector('#result:not(.hidden)'); expect(foot).to_be_visible()   # and on a later visit
    ctx.close()

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
def page_is_locked_down(b):
    # #36: a Content-Security-Policy before any script: only the page's own scripts (by hash) and files from this site
    # run, data goes only to the county map server and the counting service, frames only from this site; no
    # referrer is sent anywhere. A whole visit (phone and laptop) trips nothing; an injected script doesn't run.
    html = build_module().build()                                  # what the build writes (index.html on disk equals it: live_build test)
    m = re.search(r'<meta http-equiv="Content-Security-Policy" content="([^"]+)">', html)
    assert m and html.index(m.group(0)) < html.index('<script'), 'a CSP meta tag before the first script'
    pol = dict((d.split(' ', 1) + [''])[:2] for d in m.group(1).split('; '))
    assert pol['default-src'] == "'none'" and pol['frame-src'] == "'self'" and pol['base-uri'] == "'none'" and pol['form-action'] == "'none'", pol
    assert pol['connect-src'] == 'https://taxmaps.traviscountytx.gov https://gateway.umami.is', pol['connect-src']
    srcs = pol['script-src'].split()
    assert srcs[0] == "'self'" and all(x.startswith("'sha256-") for x in srcs[1:]) and len(srcs) == 1 + html.count('<script>'), srcs
    assert '<meta name="referrer" content="no-referrer">' in html and html.index('name="referrer"') < html.index('<script')
    for wide in ((False, True) if HAS_DESK else (False,)):
        ctx, pg = new_page(b, wide=wide, csp=True); pg.add_init_script(CSP_WATCH); refs = []
        pg.on('request', lambda r: refs.append((r.url, r.headers.get('referer'))) if 'traviscountytx.gov' in r.url else None)
        pg.goto(BASE)
        if wide:
            lookup_strict(pg, True)
            for v in ('glance', 'vote', 'crib', 'decide'): pg.click(f'#dk-views [data-view="{v}"]')
            pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]'); pg.keyboard.press('Escape')
        else:
            fresh_goto(pg, link('s', {'v': 1, 'n': 'Maya', 'c': 'abcd2349', 'g': 1, 'p': {'70': 0}})); pg.wait_for_selector('#friend:not(.hidden)')
            lookup_strict(pg); pick(pg, 'c070', 'Qadri')
            pg.click('#a-keep'); pg.wait_for_selector('#d-keep[open]'); pg.click('#d-keep [data-close]')
            pg.click('#a-share'); pg.wait_for_selector('#d-share[open]'); pg.click('#d-share [data-close]')
        pg.wait_for_timeout(500)
        assert pg.evaluate('window.__csp') == [], (wide, pg.evaluate('window.__csp'))
        assert refs and all(r is None for _, r in refs), ('no referrer to the county', refs[:2])
        pg.evaluate("() => { const s = document.createElement('script'); s.textContent = 'window.__pwned = 1'; document.body.appendChild(s); }")
        pg.wait_for_timeout(200)
        assert pg.evaluate('window.__pwned') is None and any(v.startswith('script-src') for v in pg.evaluate('window.__csp')), 'an injected script ran'
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
                         (looper, 'not_found'),
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
                'V Oꭲꭼꮢ Guide', 'D Eꮇꮪ', 'D Eꮇꮪ Texas', 'D Eмѕ', 'V Oтer Guide', 'G Oᴩ']:   # Pass 3
        assert sn(bad) == '', bad
    assert sn('ϹOUNTY') == 'ΣOUNTY', 'display normalization turns a lunate sigma into Σ: no longer a look-alike'
    for good in ['Mary J Blige', 'J Smith', 'Νίκος', 'Ηλέκτρα', 'Γιώργος', 'Георгий', 'Борис', 'Ольга Петрова', 'Արամ', 'Անի', 'ᏣᎳᎩ',
                 'ანა', 'Ελένη', 'Đặng Thu', 'Nguyễn Văn An', 'محمد', 'דוד', 'Priya', 'Gustavo Terrazas', 'Clerkson', 'DeClerck', 'Le Clerc',
                 'José', 'Dempsey', 'Gopinath', 'Statham', 'Partridge', 'Ivo Terzić', 'A J', 'J R R Tolkien',
                 'S Tate', 'S. Tate', 'P Arty', 'Нильс Бор', 'Ольга Бор', 'Борис Бор']:   # Pass 1, 2
        assert sn(good) == good, good
    ctx.close()

@test
def stored_junk_in_share_fields(b):
    # #44: a stored share generation that isn't a whole number, a share name that isn't text, and pick values that
    # aren't option names are ignored, never sent in a link or counted as decided.
    ctx, pg = new_page(b); errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.goto(BASE)
    pg.evaluate("""() => { localStorage.setItem('ballotta.gen', JSON.stringify('x')); localStorage.setItem('ballotta.name', JSON.stringify({ a: 1 }));
                          localStorage.setItem('ballotta.picks', JSON.stringify({ c070: [null], c071: 5, c001: { x: 1 } })); }""")
    pg.reload(); lookup(pg)
    assert pg.text_content('#k-done') == '0', pg.text_content('#k-done')
    pick(pg, 'c070', 'Qadri'); pg.click('#a-share'); pg.wait_for_selector('#d-share[open]')
    assert pg.input_value('#sharename') == '' and pg.evaluate('sharePrep.gen') == 1, (pg.input_value('#sharename'), pg.evaluate('sharePrep.gen'))
    assert errs == [], errs
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

@test
def phone_new_day_keeps_focus_on_a_directions_link(b):
    # #47: on a phone, a new day that doesn't change the voting period updates only the dated note; the vote-center
    # list (and a focused Directions link in it) stays as it was.
    import datetime as dt
    ctx, pg = new_page(b); pg.clock.install(time=dt.datetime(2026, 10, 18, 23, 58)); pg.goto(BASE)
    saved_ballot(pg, [70, 71], [-97.743, 30.272]); pg.wait_for_selector('#result:not(.hidden)')
    assert 'fills in once voting starts' in pg.text_content('#waitsnote')
    link3 = pg.locator('#sites a', has_text='Directions').nth(2); link3.focus(); href = link3.get_attribute('href')
    pg.clock.run_for(5 * 60 * 1000)
    assert pg.text_content('#waitsnote') == 'Travis County map', pg.text_content('#waitsnote')
    assert pg.evaluate('document.activeElement.getAttribute("href")') == href, pg.evaluate('document.activeElement.tagName')
    ctx.close()

def backup_card(pg, wide): return pg.locator('#dk-nudge' if wide else '#nudge')

@test
def backup_nudge_after_fifth_pick(b):
    # #48: after the 5th pick, a one-time card suggests a backup link ("Send myself a link" opens Keep my picks; "Not
    # now" puts it away); it comes back once at 25 picks if no link was ever kept; never after a link is kept. Counted.
    msg = 'Your picks live only in this browser, and phones can clear them. Send yourself a backup link.'
    nums = list(range(1, 41))
    for wide in ((False, True) if HAS_DESK else (False,)):
        ctx, pg = new_page(b, wide=wide); pg.goto(BASE); saved_ballot(pg, nums)
        pg.wait_for_selector('body.dk-app-on' if wide else '#result:not(.hidden)')
        ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)')
        card = backup_card(pg, wide)
        decide = lambda a, z: pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[a:z])
        decide(0, 4); expect(card).to_be_hidden()
        pg.evaluate('id => pick(id, "__skip")', ids[4]); expect(card).to_be_hidden()            # a skip isn't a pick (Pass 1)
        pg.evaluate('id => pick(id, "__skip")', ids[4])
        below = '#dk-paper' if wide else '#groups'; top = pg.evaluate(f'document.querySelector("{below}").getBoundingClientRect().top')
        decide(4, 5); expect(card).to_be_visible(); expect(card.locator('[role="status"]')).to_have_text(msg)
        assert pg.evaluate(f'document.querySelector("{below}").getBoundingClientRect().top') == top, 'the card pushed the page (Lane: it floats)'
        assert card.evaluate('e => getComputedStyle(e).position') == 'fixed'
        assert ['backup_nudge', {'at': '5', 'action': 'shown', 'layout': 'laptop' if wide else 'phone'}] in events(pg), events(pg)
        card.locator('[data-nudge="dismiss"]').click(); expect(card).to_be_hidden()
        if wide: assert pg.evaluate('document.activeElement.id') == 'dk-paper', 'focus back on the paper (Pass 1)'
        decide(5, 24); expect(card).to_be_hidden()
        decide(24, 25); expect(card).to_be_visible()
        card.locator('[data-nudge="keep"]').click(); pg.wait_for_selector('#d-keep[open]'); expect(card).to_be_hidden()
        assert [e[1]['action'] for e in events(pg) if e[0] == 'backup_nudge'] == ['shown', 'dismiss', 'shown', 'keep'], events(pg)
        pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
        assert pg.evaluate('document.activeElement.id') == ('dk-paper' if wide else 'a-keep'), 'Keep returns focus where the visitor was (Pass 1, 2)'
        pg.reload(); pg.wait_for_selector('body.dk-app-on' if wide else '#result:not(.hidden)')
        decide(25, 30); expect(backup_card(pg, wide)).to_be_hidden()                      # each card once per browser
        ctx.close()
    ctx, pg = new_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('#result:not(.hidden)')
    ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:2])
    pg.click('#a-keep'); pg.click('#keep-copy'); pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'keep_created')"); pg.click('#d-keep [data-close]')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[2:30]); expect(backup_card(pg, False)).to_be_hidden()   # already kept a link
    ctx.close()
    # Pass 1: a card shown is remembered (an ignored card doesn't come back next visit); Not now at 25+ picks retires the
    # 25 card too; Clear my picks puts the card away.
    ctx, pg = new_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('#result:not(.hidden)')
    ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)'); card = backup_card(pg, False)
    many = lambda a, z: pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[a:z])
    many(0, 5); expect(card).to_be_visible()
    pg.reload(); pg.wait_for_selector('#result:not(.hidden)'); many(5, 6); expect(card).to_be_hidden()
    many(6, 30); expect(card).to_be_visible(); card.locator('[data-nudge="dismiss"]').click(); many(30, 31); expect(card).to_be_hidden()
    ctx.close()
    # Pass 2: with the card up, nothing at the bottom of the page is stuck under it (phone footer; laptop Print button at
    # 1024x640); after Not now, focus returns to the pick just made, not to the top of the page.
    ctx, pg = new_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('#result:not(.hidden)')
    ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)'); card = backup_card(pg, False)
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:4])
    open_race(pg, ids[4]); fifth = pg.locator(f'#r{ids[4]} .opt').first; fifth.focus(); pg.keyboard.press('Enter'); expect(card).to_be_visible()
    card.locator('[data-nudge="dismiss"]').focus(); pg.keyboard.press('Enter'); expect(card).to_be_hidden()
    assert pg.evaluate('document.activeElement.dataset.c') == ids[4], pg.evaluate('document.activeElement.outerHTML.slice(0, 80)')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[5:6])   # (not a card moment: 6 picks, the 5 card was seen)
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[6:24])
    open_race(pg, ids[24]); last = pg.locator(f'#r{ids[24]} .opt').first; last.focus(); pg.keyboard.press('Enter'); expect(card).to_be_visible()
    pg.evaluate(f"document.getElementById('r{ids[24]}').open = false")                     # the race closed since: focus can't go back there (Pass 3)
    card.locator('[data-nudge="dismiss"]').focus(); pg.keyboard.press('Enter'); expect(card).to_be_hidden()
    assert pg.evaluate('document.activeElement.id') == 'a-keep', pg.evaluate('document.activeElement.tagName')
    pg.evaluate("localStorage.removeItem('ballotta.nudge')"); pg.evaluate('id => pick(id, optionsOf(BYID[id])[0])', ids[25]); expect(card).to_be_visible()
    pg.evaluate('window.scrollTo(0, document.body.scrollHeight)'); pg.wait_for_timeout(200)
    hit = pg.evaluate("() => { const r = document.getElementById('reset-all-foot').getBoundingClientRect(); const e = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return e && e.id; }")
    assert hit == 'reset-all-foot', ('the footer button is under the card', hit)
    pg.emulate_media(media='print'); assert pg.evaluate('getComputedStyle(document.body).paddingBottom') == '0px', 'no room reserved on paper (Pass 3)'
    ctx.close()
    # Pass 2: a returning voter with 5+ picks who makes a skip sees no card (a real pick does); a 5 card left up to 30
    # picks and then put away doesn't bring the 25 card.
    ctx, pg = new_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('#result:not(.hidden)')
    ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)'); card = backup_card(pg, False)
    pg.evaluate("ids => localStorage.setItem('ballotta.picks', JSON.stringify(Object.fromEntries(ids.map(id => [id, [optionsOf(BYID[id])[0]]]))))", ids[:6])
    pg.reload(); pg.wait_for_selector('#result:not(.hidden)')
    pg.evaluate('id => pick(id, "__skip")', ids[6]); expect(card).to_be_hidden()
    pg.evaluate('id => pick(id, optionsOf(BYID[id])[0])', ids[7]); expect(card).to_be_visible()
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[8:31]); expect(card).to_be_visible()
    card.locator('[data-nudge="dismiss"]').click(); pg.evaluate('id => pick(id, optionsOf(BYID[id])[0])', ids[31]); expect(card).to_be_hidden()
    ctx.close()
    if HAS_DESK:
        ctx, pg = new_page(b, wide=True); pg.set_viewport_size({'width': 1024, 'height': 640}); pg.goto(BASE); saved_ballot(pg, nums)
        pg.wait_for_selector('body.dk-app-on'); ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)')
        pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:5]); expect(backup_card(pg, True)).to_be_visible()
        pg.focus('#dk-print'); pg.keyboard.press('Enter'); pg.wait_for_timeout(300)
        hit = pg.evaluate("() => { const a = document.activeElement, r = a.getBoundingClientRect(), e = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return [a.dataset.act, e === a || a.contains(e)]; }")
        assert hit == ['print', True], ('the focused Print button is under the card', hit)
        ctx.close()
    ctx, pg = new_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('#result:not(.hidden)')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:5]); card = backup_card(pg, False); expect(card).to_be_visible()
    pg.once('dialog', lambda d: d.accept()); pg.click('#reset'); expect(card).to_be_hidden()
    ctx.close()

@test
def persistent_storage_asked_at_first_pick(b):
    # #49: at the first pick, the page asks the browser to keep its data (navigator.storage.persist), once, and not if
    # it's already kept; nothing is asked before a pick.
    stub = ("window.__persist = 0; window.__persisted = %s; Object.defineProperty(navigator, 'storage', { configurable: true, value: {"
            " persisted: () => { window.__checked = (window.__checked || 0) + 1; return Promise.resolve(window.__persisted); },"
            " persist: () => { window.__persist++; return Promise.resolve(true); } } });")
    for already, want in ((False, 1), (True, 0)):
        ctx, pg = new_page(b); pg.add_init_script(stub % ('true' if already else 'false')); pg.goto(BASE)
        saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('#result:not(.hidden)'); pg.wait_for_timeout(200)
        assert pg.evaluate('window.__persist') == 0 and not pg.evaluate('window.__checked'), 'asked before any pick'
        pick(pg, 'c070', 'Qadri'); pick(pg, 'c071', 'For'); pg.wait_for_timeout(200)
        assert pg.evaluate('window.__persist') == want and pg.evaluate('window.__checked') == 1, (already, pg.evaluate('[window.__persist, window.__checked]'))
        ctx.close()

# ---------------------------------------------------------------- phone layout (preview build only until promotion)
import urllib.request, time
PHONE = {'width': 390, 'height': 844}                      # an iPhone 13/14/15's screen in CSS pixels

def phone_page(b, sent=None, csp=False, sw=False, size=None, init=None, ua=None):
    ctx, pg = new_page(b, sent, csp=csp, touch=True, size=size or PHONE, sw=sw, ua=ua)
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
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.whys')).c070") == 'Knows the district'
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
    assert got == want[:4] + ['Add to your Home Screen'] + want[4:] and pg.locator('#ph-mitems hr').count() == 1, (got, want)
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
    pg.evaluate("window.dispatchEvent(new Event('appinstalled'))")
    assert pg.evaluate('window.__prompted') == 1
    hs = [e[1] for e in events(pg) if e[0] == 'home_screen']
    assert hs == [{'action': 'opened', 'from': 'menu', 'layout': 'phone'}, {'action': 'prompted', 'layout': 'phone'}, {'action': 'added', 'layout': 'phone'}], hs
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click()
    expect(pg.locator('#ph-i-other')).to_be_visible(); expect(pg.locator('#ph-i-add')).to_be_hidden()   # the prompt is used up: say where to look
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
    def log_message(self, *a): pass
    def do_GET(self):
        Flip.hits.append(self.path.split('?')[0])
        if self.path.split('?')[0] in Flip.slow: time.sleep(Flip.slow[self.path.split('?')[0]])
        if self.path.split('?')[0] in Flip.gone: return self.send_error(404)
        if self.path.split('?')[0] in Flip.fail: return self.send_error(Flip.fail[self.path.split('?')[0]])
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
        assert url in kept and any(k.endswith('.woff2') for k in kept) and all(k.startswith(origin + '/') for k in kept), kept
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
        pg.evaluate("window.dispatchEvent(new Event('online'))"); assert bar.is_hidden(), 'the network came back but the bar stayed'
        pg.set_viewport_size({'width': 1180, 'height': 820}); pg.wait_for_timeout(200)
        assert pg.evaluate("getComputedStyle(document.querySelector('.dk-rail')).top") == '56px', 'the rail kept room for a bar that is gone'
        pg.set_viewport_size(PHONE); pg.wait_for_timeout(200)
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
        html = m.build(phone=ph)
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
    m = build_module()
    on, off = m.sw_js(True), m.sw_off_js(True)
    assert "'ballotta-next-1'" in on and "'ballotta-1'" in m.sw_js(False) and "startsWith('ballotta-next-')" in off and "startsWith('ballotta-')" in m.sw_off_js(False)
    m.PHONE_LIVE = True; out = m.outputs(False); m.PHONE_LIVE = False
    assert out['next/sw.js'] == m.sw_off_js(True) and out['sw.js'] == m.sw_js(False) and 'next/index.html' not in out, sorted(out)
    Flip.swap = {}; srv, url = own_server()
    ctx, pg = phone_page(b, sw=True)
    try:
        pg.goto(url); assert pg.evaluate('Promise.race([navigator.serviceWorker.ready.then(() => true), new Promise(ok => setTimeout(ok, 15000, false))])')
        poll(pg, '!!navigator.serviceWorker.controller', 15); pg.reload(); poll(pg, "caches.keys().then(k => k.includes('ballotta-next-1'))", 15)
        m.OFFLINE = False; page = m.build(preview=True); m.OFFLINE = True
        Flip.swap = {'/' + PAGE: page.encode('utf-8'), '/' + PAGE.rsplit('/', 1)[0] + '/sw.js': m.sw_off_js(True).encode('utf-8')}
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
            pg.evaluate("caches.open('ballotta-next-1').then(c => c.put(location.href, new Response('x')))")
            Flip.swap = {'/' + PAGE: page.encode('utf-8')}
            swp = '/' + PAGE.rsplit('/', 1)[0] + '/sw.js'
            if gone == 503: Flip.fail = {swp: 503}
            else: Flip.swap[swp] = m.sw_off_js(True).encode('utf-8')
            pg.wait_for_timeout(3000); Flip.hits = []                                       # let the browser's own update check settle first
            pg.reload()
            if gone == 503:                                                                  # a hiccup is not "gone": the copy stays
                pg.wait_for_timeout(2500)
                assert 'getRegistration(\'./\')' in pg.content() and swp in Flip.hits, ('the kill switch never asked for sw.js', Flip.hits)
                assert pg.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.length)") == 1 and pg.evaluate("caches.has('ballotta-next-1')"), 'a 503 removed the copy'
            else:
                poll(pg, "navigator.serviceWorker.getRegistrations().then(r => r.length === 0)", 15)
                poll(pg, "caches.keys().then(k => !k.some(x => x.startsWith('ballotta')))", 15)
            ctx.close()
        Flip.swap, Flip.gone, Flip.fail = {}, set(), {}                                    # a page never touches another folder's copy (Pass 3)
        ctx, pg = phone_page(b, sw=True); pg.goto(url); poll(pg, "navigator.serviceWorker.getRegistrations().then(r => r.length === 1)", 15)
        Flip.swap = {'/_other.html': m.build(phone=True).encode('utf-8')}; Flip.fail = {'/' + PAGE.rsplit('/', 1)[0] + '/sw.js': 503}
        pg.goto(url.rsplit('/', 2)[0] + '/_other.html'); pg.wait_for_timeout(2500)
        assert pg.evaluate("navigator.serviceWorker.getRegistrations().then(r => r.some(g => g.scope.endsWith('/next/')))"), 'another page removed the preview copy'
    finally:
        Flip.swap, Flip.gone, Flip.fail = {}, set(), {}; ctx.close(); srv.shutdown(); srv.server_close()

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
            if fn.__name__ in OLD_PHONE_TESTS and HAS_PHONE:
                skipped += 1; print('SKIP', fn.__name__, '- drives today\'s phone page: runs on index.html'); continue
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
