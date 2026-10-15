"""End-to-end checks for the Ballotta test site (index.html), run against the live Travis County lookup services.

    python3 tests/test_site.py                                    # builds nothing; checks the live page (index.html)
    BALLOTTA_PAGE=next/index.html python3 tests/test_site.py      # checks the preview, laptop layout included

Analytics: cloud.umami.is is stubbed so each test can see exactly which events (and which details) would be sent.
"""
import http.server, threading, functools, json, pathlib, re, sys, traceback, urllib.parse, hashlib, importlib.util, os
from playwright.sync_api import sync_playwright, expect

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8765
PAGE = os.environ.get('BALLOTTA_PAGE', 'index.html')
BASE = f'http://127.0.0.1:{PORT}/{PAGE}'
HAS_DESK = 'id="dk-app"' in (ROOT / PAGE).read_text(encoding='utf-8')
# sha256 of the live index.html as built from commit 0ae877c (Oct 14). The laptop layout must not change it until
# Lane promotes the preview. A data rebuild (ballot or League data) changes it legitimately: re-pin it in that commit.
LIVE_SHA = 'fcbf41e3792c67b0efedc81f5e12c6c3519437fa62a5be0640d222c7d7a0a7f5'
UMAMI_STUB = "window.__events=[];window.umami={track:function(n,d){window.__events.push([n,d||{}]);}};"

class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

def serve():
    h = functools.partial(Quiet, directory=str(ROOT))
    s = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s

def new_page(browser, sent=None, wide=False):
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900} if wide else {'width': 400, 'height': 900}, permissions=['clipboard-read', 'clipboard-write'])
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
    frag = url.split('#', 1)[1]
    assert re.fullmatch(r'k2[A-Za-z0-9_-]{16,}', frag), url                 # v2: nothing after '#' that chat apps cut at
    assert ['keep_created', {'via': 'copy'}] in events(pg)
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
    assert op == {'generation': 1, 'has_picks': 'no', 'link': ev['link']}, op
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
    live, prev = m.build(preview=False), m.build(preview=True)
    if m.DESK_LIVE:
        assert 'id="dk-app"' in live, 'promoted: the live page carries the laptop layout'
    else:
        assert 'id="dk-app"' not in live and 'DESK' not in live, 'laptop layout leaked into the live build'
        got = hashlib.sha256(live.encode('utf-8')).hexdigest()
        assert got == LIVE_SHA, f'live index.html changed ({got}). Expected only after a data rebuild: re-pin LIVE_SHA in that commit.'
    assert 'id="dk-app"' in prev and 'data-domains="preview.invalid"' in prev and 'src="../umami.js"' in prev
    assert "url('../fonts/" in prev and '[Preview]' in prev and 'data-domains="preview.invalid"' not in live

@desk_test
def desk_layout_header_and_rail(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    assert pg.is_visible('#start') and pg.is_visible('.dk-steps') and pg.is_hidden('#dk-app') and pg.is_hidden('#dk-share')
    lookup_wide(pg)
    assert pg.is_hidden('main.wrap') and pg.is_visible('#dk-paper') and pg.is_visible('#dk-notes')
    loc = pg.inner_text('#dk-loc'); assert 'Precinct 300' in loc and '1000 Guadalupe St' in loc and 'change' in loc, loc
    h, s = pg.locator('#dk-help').bounding_box(), pg.locator('#dk-share').bounding_box()
    assert h['x'] + h['width'] <= s['x'], 'Help & info sits left of Share my picks'
    assert pg.locator('.dk-row').count() == 63 and pg.inner_text('#dk-count') == '0 of 63 decided'
    assert 'United States Senator' in pg.inner_text('#dk-paper h1')                                 # first undecided contest
    for width in (1280, 1366, 1440, 1920):                                                         # notes sit evenly between paper and edge
        pg.set_viewport_size({'width': width, 'height': 900})
        p, n = pg.locator('#dk-paper').bounding_box(), pg.locator('#dk-notes').bounding_box()
        left, mid, right = p['x'] - 288, n['x'] - (p['x'] + p['width']), width - (n['x'] + n['width'])
        assert min(left, mid, right) >= 23 and abs(mid - right) <= 2 and abs(left - mid) <= 2, (width, left, mid, right)
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
    pg.click('#dk-views [data-view="crib"]')
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
    pg.keyboard.press('Escape'); assert pg.evaluate('document.activeElement.id') == 'dk-help', 'focus comes back to Help & info'
    pg.click('#dk-help'); pg.keyboard.press('Shift+Tab'); pg.keyboard.press('Escape')               # Escape from the button, menu open
    assert pg.is_hidden('#dk-menu'), 'Escape closes the menu from the Help & info button too'
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

@desk_test
def desk_phone_layout_matches_live_page(b):
    # Phones must not change: the preview at phone width is pixel-for-pixel the live page, before and after a lookup.
    shots = []
    for page in ['index.html', PAGE]:
        ctx, pg = new_page(b); pg.goto(f'http://127.0.0.1:{PORT}/{page}'); pg.wait_for_timeout(600)
        first = pg.screenshot(full_page=True)
        lookup(pg); open_race(pg, 'c070'); pg.evaluate('window.scrollTo(0, 0)'); pg.wait_for_timeout(600)
        shots.append((first, pg.screenshot(full_page=True))); ctx.close()
    assert shots[0][0] == shots[1][0], 'landing differs from the live page at phone width'
    assert shots[0][1] == shots[1][1], 'ballot differs from the live page at phone width'

def main():
    srv = serve()
    failed = skipped = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        for fn in TESTS:
            if fn.__name__ in DESK_TESTS and not HAS_DESK:
                skipped += 1; print('SKIP', fn.__name__, '- no laptop layout in', PAGE); continue
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
