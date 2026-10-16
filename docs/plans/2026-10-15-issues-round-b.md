# Issues round, commit B (Oct 15, 2026): #36 security hardening, #38 shared functions for both layouts

**Goal.** Lock the page down (#36) and stop the laptop layout from driving the phone page by clicking its hidden
buttons and copying its markup (#38). Lane chose to do both now rather than after Nov 3.

**Lane's decisions (Oct 15).** Referrer policy: tell outbound sites nothing (`no-referrer`). Both #36 and #38 now.

**Findings that shaped it.**
- The U.S. Census geocoder sends no `Access-Control-Allow-Origin`, so a plain `fetch` is refused; it answers only as
  JSONP. The fix isolates the JSONP instead of replacing it: a sandboxed frame (`census.html`, written by
  `build_site.py` with its own CSP) loads it, has no access to the page or its storage, and hands back only a point,
  which the page checks (from that frame, numbers, inside Texas).
- Of the seven `http://` campaign sites, three load over https:// in a browser (Cuero, Dahlberg, Abraham) and are
  linked that way (`HTTPS_OK` in `build_learn.py`). The other four blocked automated checks; they stay http:// rather
  than risk a certificate error. A test fails if a new http:// site appears.

**What changed**

| Issue | Change | Test |
|---|---|---|
| #36 | CSP meta tag, built from sha256 hashes of the finished page's inline scripts: `default-src 'none'`, scripts only `'self'` + hashes, connections only the county map server and the counting service, frames only `'self'`, `base-uri`/`form-action` `'none'` | `page_is_locked_down` (whole visit on both layouts with the CSP on: no violations; an injected script doesn't run; no referrer to the county) |
| #36 | `<meta name="referrer" content="no-referrer">` | same |
| #36 | Census lookup in a sandboxed frame; it runs only sandboxed, builds the Census URL itself (fixed callback), answers once | `census_runs_in_a_sandbox` (hostile reply can't touch the page, storage or navigation; bad or out-of-Texas points refused; spoofed messages ignored; a reloading frame can't loop; unsandboxed embedding does nothing; frame removed) |
| #36 | three campaign links over https:// | `campaign_links_use_https_where_they_work` |
| #38 | `openShare`, `openKeep`, `printCrib`, `clearPicks`, `clearEverything`, `hideFriend`, `sendFeedback`, `hoursHTML`, `siteHead`, `waitsURL`, `cribHTML`, `notify`: both layouts call them. The one deliberate copy left is static text (the privacy and about words in Feedback & Info) | `desk_works_without_phone_buttons` (no `.click()` on a phone element in the laptop code; with the phone buttons renamed away, every laptop action still works) |

**Testing note.** Playwright's `wait_for_function` polls by evaluating strings in the page, which the CSP rightly
forbids. Ordinary tests run with the CSP bypassed (they test the app's logic, which the CSP doesn't change); the two
security tests keep it on and poll from Python (`poll()`, `lookup_strict()`).

**How to apply (from the repo root, after commit A).**

```
python3 <scripts>/edits_tests_B.py     # 4 tests (RED first: all four failed on the commit-A page)
python3 <scripts>/edits_page_B.py      # the changes
python3 source/build_learn.py          # learn.json: the three https:// links
python3 <scripts>/edits_mutants_B.py   # 15 mutants, 3 re-anchored after the refactor
python3 <scripts>/rework_B1.py         # remediation audit Pass 1
python3 source/build_site.py           # index.html and census.html
python3 tests/test_site.py             # expected: 64/64 passed (index.html)
python3 tests/mutate_desk.py 214 236   # expected: 21 of 21 mutants killed
```

## Execution log

- RED: the 4 new tests failed on the commit-A page for the expected reasons. GREEN after the changes, once the
  security tests stopped using `wait_for_function` under the CSP (see Testing note).
- First mutant run: 16 of 18; C2 and C3 (laptop copying the phone hours and crib) survived because the static check
  read the template while mutants change the built page. The check now reads the page under test.
- **Remediation audit Pass 1** (independent agent): nothing high or medium. It ran full journeys on both layouts with
  the CSP on and the real pinned tracker (zero violations, beacons sent), checked every build flavour's hashes, the
  live Census and county servers without a referrer, and every event count across the refactor. Fixed (all low,
  introduced): census.html could be embedded unsandboxed by another site and given a callback name (now it runs only
  sandboxed and builds the URL itself); a reloading frame made the page re-post in a loop (now `{ once: true }`); the
  preview at /next/ looked for census.html in its own folder (now rewritten to `../census.html`).
- **Pass 2** (rework only): holds; the live Census fallback works end to end through the sandbox (0.4 s). Logged, not
  changed (low): two mutants of `build_site.py` are killed by the "census.html is out of date" check rather than by the
  new embed test (the runner doesn't rebuild census.html); for up to ~10 minutes after a deploy a browser with one old
  cached file and one new one could see the Census fallback fail closed ("couldn't find that address"). A versioned
  frame URL would close that window if it ever matters.
- **Final:** 64/64 tests; 21 of 21 mutants killed.

## Script: edits_tests_B.py

```python
"""Issues round, commit B: the tests for #36 and #38 (written first; each must fail before the fixes). Run from the repo
root after commit A:  python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
TS = ROOT / 'tests/test_site.py'
s = TS.read_text(encoding='utf-8')
if s.count('\ndef main():') != 1: sys.exit('test_site.py: main() not found once')
a = "def new_page(browser, sent=None, wide=False):\n    ctx = browser.new_context(viewport={'width': 1440, 'height': 900} if wide else {'width': 400, 'height': 900}, permissions=['clipboard-read', 'clipboard-write'])"
z = ("def new_page(browser, sent=None, wide=False, csp=False):\n"
     "    # The page's Content-Security-Policy (#36) forbids eval, which Playwright's wait_for_function polls with: tests run\n"
     "    # with it bypassed unless they ask (csp=True), and those poll from Python instead (see poll()).\n"
     "    ctx = browser.new_context(viewport={'width': 1440, 'height': 900} if wide else {'width': 400, 'height': 900}, permissions=['clipboard-read', 'clipboard-write'], bypass_csp=not csp)")
if s.count(a) != 1: sys.exit('new_page not found once')
s = s.replace(a, z)
NEW = r'''
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
    def census(route, body):
        route.fulfill(status=200, content_type='application/javascript', body=body)
    match = '{"coordinates":{"x":-97.74,"y":30.27},"matchedAddress":"1 NOWHERE ST, AUSTIN, TX, 78701"}'
    hostile = ("cb({\"result\":{\"addressMatches\":[" + match + "]}});"
               "try { parent.document.body.dataset.pwned = '1'; } catch (e) {}"
               "try { parent.localStorage.setItem('ballotta.pwned', '1'); } catch (e) {}"
               "try { localStorage.setItem('ballotta.pwned', '1'); } catch (e) {}"
               "try { top.location.hash = '#pwned'; } catch (e) {}")
    for body, reason in ((hostile, 'no_voters_nearby'),                                                  # a point came back
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
        assert refs == [None], ('the Census request carries no referrer', refs)
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
    deskjs = src[src.index('const desk = (() => {'):src.index('window.desk = desk;')]
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
    assert 'My ballot notes' in pg.inner_text('#dk-page')
    pg.click('#dk-views [data-view="decide"]'); pg.locator('#dk-paper .dk-line').first.click()
    assert pg.evaluate('Object.keys(picks).length') == 1
    pg.click('#dk-help'); pg.once('dialog', lambda d: d.accept()); pg.click('#dk-menu [data-help="clear"]')
    assert pg.evaluate('Object.keys(picks).filter(k => current(k).length).length') == 0
    pg.click('#dk-help'); pg.once('dialog', lambda d: d.accept()); pg.click('#dk-menu [data-help="clearall"]')
    pg.wait_for_function("!Object.keys(localStorage).some(k => k.startsWith('ballotta.'))", timeout=5000)
    assert errs == [], errs
    ctx.close()

def main():'''
s = s.replace('\ndef main():', NEW)
TS.write_text(s, encoding='utf-8')
print('tests B added')
```

## Script: edits_page_B.py

```python
"""Issues round, commit B: #36 (security hardening) and #38 (shared functions instead of the laptop clicking or copying
the phone layout). Run from the repo root after commit A and edits_tests_B.py:  python3 <this file>
Then:  python3 source/build_learn.py && python3 source/build_site.py"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
T, B, L, RM = 'source/template-travis.html', 'source/build_site.py', 'source/build_learn.py', 'README.md'
files = {}
def sw(path, a, z):
    s = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
    if s.count(a) != 1: sys.exit(f'{path}: FIND occurs {s.count(a)} times: {a[:80]!r}')
    files[path] = s.replace(a, z)

# ======================= #36 =======================
# Referrer policy and the CSP placeholder, before any script
sw(T, '<meta name="viewport" content="width=device-width, initial-scale=1">\n<script>',
      '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
      '<meta name="referrer" content="no-referrer">\n'
      '<!--CSP-->\n<script>')

# The Census lookup runs in a sandboxed frame (census.html) and can hand back only a point
sw(T, r"""function censusPoint(street, zip) {
  return new Promise(resolve => {
    const cb = 'cg' + Date.now(), sc = document.createElement('script');
    const done = (v) => { try { delete window[cb]; } catch (e) {} sc.remove(); resolve(v); };
    const t = setTimeout(() => done(null), 8000);
    window[cb] = (d) => { clearTimeout(t); const m = d && d.result && d.result.addressMatches && d.result.addressMatches[0]; done(m ? { x: m.coordinates.x, y: m.coordinates.y, label: m.matchedAddress } : null); };
    sc.onerror = () => { clearTimeout(t); done(null); };
    sc.src = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?' + new URLSearchParams({ address: street + ', TX ' + zip, benchmark: 'Public_AR_Current', format: 'jsonp', callback: cb });
    document.head.appendChild(sc);
  });
}""", r"""function censusPoint(street, zip) {
  // The Census geocoder answers only as JSONP (a script), so it runs in a sandboxed frame (census.html, written by
  // build_site.py) that can't reach this page or its storage. It hands back only a point, checked here: numbers, in
  // Texas, from that frame (#36).
  return new Promise(resolve => {
    const f = document.createElement('iframe');
    let t = 0;
    const done = (v) => { clearTimeout(t); window.removeEventListener('message', on); f.remove(); resolve(v); };
    function on(e) {
      if (e.source !== f.contentWindow) return;
      const d = e.data, ok = d && typeof d === 'object' && Number.isFinite(d.x) && Number.isFinite(d.y) && d.x > -107 && d.x < -93 && d.y > 25 && d.y < 37 && typeof d.label === 'string';
      done(ok ? { x: d.x, y: d.y, label: d.label.slice(0, 200) } : null);
    }
    window.addEventListener('message', on);
    t = setTimeout(() => done(null), 8000);
    f.setAttribute('sandbox', 'allow-scripts'); f.setAttribute('aria-hidden', 'true'); f.tabIndex = -1; f.hidden = true; f.title = 'Census address lookup';
    f.addEventListener('load', () => f.contentWindow.postMessage('https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?' + new URLSearchParams({ address: street + ', TX ' + zip, benchmark: 'Public_AR_Current', format: 'jsonp', callback: 'cb' }), '*'));
    f.src = 'census.html';
    document.body.appendChild(f);
  });
}""")

# build_site.py: the CSP (hashes of the finished page's inline scripts) and census.html
sw(B, "import json, re, pathlib, sys\n", "import base64, hashlib, json, re, pathlib, sys\n")
sw(B, "\ndef build(preview=False, desk=None):",
r'''
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
    "// Built by source/build_site.py; don't edit census.html. Ballotta's page sends one Census geocoder address;\n"
    "// this frame (sandboxed: no access to the page or its storage) loads the JSONP reply and passes back only a point.\n"
    "window.addEventListener('message', function on(e) {\n"
    "  if (e.source !== parent || typeof e.data !== 'string' || e.data.indexOf('https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?') !== 0) return;\n"
    "  window.removeEventListener('message', on);\n"
    "  window.cb = function (d) {\n"
    "    var m = d && d.result && d.result.addressMatches && d.result.addressMatches[0];\n"
    "    parent.postMessage(m && m.coordinates ? { x: Number(m.coordinates.x), y: Number(m.coordinates.y), label: String(m.matchedAddress || '') } : null, '*');\n"
    "  };\n"
    "  var s = document.createElement('script');\n"
    "  s.src = e.data; s.onerror = function () { parent.postMessage(null, '*'); };\n"
    "  document.head.appendChild(s);\n"
    "});\n")


def census_page():
    return ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="referrer" content="no-referrer">\n'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src ' + sha(CENSUS_JS)
            + ' https://geocoding.geo.census.gov; base-uri \'none\'; form-action \'none\'">\n'
            '<title>Census address lookup</title></head><body>\n<script>' + CENSUS_JS + '</script>\n</body></html>\n')


def build(preview=False, desk=None):''')
sw(B, "    return html.replace(\"__DATA__\", data, 1)\n",
      "    html = html.replace(\"__DATA__\", data, 1)\n"
      "    return html.replace(\"<!--CSP-->\", csp_meta(html), 1)  # last of all: it hashes the finished scripts (#36)\n")
sw(B, '    print(out.relative_to(ROOT).as_posix(), len(html) // 1024, "KB")\n',
      '    print(out.relative_to(ROOT).as_posix(), len(html) // 1024, "KB")\n'
      '    if not preview:\n'
      '        (ROOT / "census.html").write_text(census_page(), encoding="utf-8")  # the Census lookup\'s sandbox (#36)\n'
      '        print("census.html")\n')

# build_learn.py: campaign sites that load over https:// in a browser are linked that way
sw(L, "AISD = ('Board election page', 'Austin ISD', 'https://www.austinisd.org/board/elections')\n",
      "AISD = ('Board election page', 'Austin ISD', 'https://www.austinisd.org/board/elections')\n"
      "# Campaign sites the link check reached only over http:// that load over https:// in a browser (checked Oct 15, 2026):\n"
      "# linked over https:// (#36). The other http:// sites answered only on http://, so an https:// link would fail there.\n"
      "HTTPS_OK = {'cuero4rrisd.com', 'juliefortexassenate.com', 'www.farrahabraham.com'}\n")
sw(L, "                e['s'] = v['url'] if ok else None\n",
      "                url = v['url']\n"
      "                if url.startswith('http://') and url[7:].split('/')[0].lower() in HTTPS_OK:\n"
      "                    url = 'https://' + url[7:]\n"
      "                e['s'] = url if ok else None\n")

# ======================= #38: shared functions both layouts call =======================
# Crib sheet
sw(T, "function renderCrib() {\n  const withWhy = $('withwhy').checked;",
      "function cribHTML() {  // the crib sheet, for the phone page and the laptop's crib view alike (#38)\n  const withWhy = $('withwhy').checked;")
sw(T, "  $('crib').innerHTML = html;\n}\n", "  return html;\n}\nfunction renderCrib() { $('crib').innerHTML = cribHTML(); }\n")
sw(T, "'\" id=\"dk-page\">' + $('crib').innerHTML + '</div>';", "'\" id=\"dk-page\">' + cribHTML() + '</div>';")
# Hours, list heading, wait-times link
sw(T, """  $('hours').innerHTML = period === 'early'
    ? '<span class="ov">Mon Oct 19 – Fri Oct 30</span><p><b>7am–7pm every day</b>, weekends included.</p><p class="note">Some sites stay open until 10pm on Thu Oct 29 and Fri Oct 30.</p>'
    : '<span class="ov">Tuesday, Nov 3</span><p><b>7am–7pm</b> at ' + DATA.sites.eday.length + ' vote centers.</p><p class="note">If you’re in line by 7pm, you can vote.</p>';
""", "  $('hours').innerHTML = hoursHTML();\n")
sw(T, "function renderVote() {\n", """// Hours, the list heading and the wait-times link for the voting period showing: the phone section and the laptop's
// vote view both draw from these (#38).
function hoursHTML() {
  return period === 'early'
    ? '<span class="ov">Mon Oct 19 – Fri Oct 30</span><p><b>7am–7pm every day</b>, weekends included.</p><p class="note">Some sites stay open until 10pm on Thu Oct 29 and Fri Oct 30.</p>'
    : '<span class="ov">Tuesday, Nov 3</span><p><b>7am–7pm</b> at ' + DATA.sites.eday.length + ' vote centers.</p><p class="note">If you’re in line by 7pm, you can vote.</p>';
}
function siteHead(n) { return here ? (showAll ? 'All ' + n + ', closest first' : 'Closest to your address') : 'All ' + n + ' sites (look up your address to sort by distance)'; }
function waitsURL() { return 'https://updates.electionlink.net/widgets/travistx/2026-11-03/' + (period === 'early' ? 'Early%20Voting%20Dashboard.html' : 'Election%20Day%20Voting%20Dashboard.html'); }
function renderVote() {
""")
sw(T, "  $('sitehead').textContent = here ? (showAll ? 'All ' + all.length + ', closest first' : 'Closest to your address') : 'All ' + all.length + ' sites (look up your address to sort by distance)';\n",
      "  $('sitehead').textContent = siteHead(all.length);\n")
sw(T, "  $('waits').href = 'https://updates.electionlink.net/widgets/travistx/2026-11-03/' + (period === 'early' ? 'Early%20Voting%20Dashboard.html' : 'Election%20Day%20Voting%20Dashboard.html');\n",
      "  $('waits').href = waitsURL();\n")
sw(T, "<div class=\"sub\">' + $('hours').innerHTML + '</div>'", "<div class=\"sub\">' + hoursHTML() + '</div>'")
sw(T, "esc($('sitehead').textContent)", "esc(siteHead(all.length))")
sw(T, "esc($('waits').href)", "esc(waitsURL())")
# Keep, Share
sw(T, "$('a-keep').addEventListener('click', () => {\n  prepKeep();", "function openKeep() {  // Keep my picks, from either layout (#38)\n  prepKeep();")
sw(T, "  $('d-keep').showModal();\n});\n", "  $('d-keep').showModal();\n}\n$('a-keep').addEventListener('click', openKeep);\n")
sw(T, "$('a-share').addEventListener('click', () => {\n  const secs = shareSections();", "function openShare() {  // Share my picks, from either layout (#38)\n  const secs = shareSections();")
sw(T, "  track('share_sheet_open', {});\n});\n", "  track('share_sheet_open', {});\n}\n$('a-share').addEventListener('click', openShare);\n")
# Feedback
sw(T, "$('feedback').addEventListener('click', (e) => {\n  e.preventDefault();\n  const to = ['lanebecker', 'gmail.com'].join('@');",
      "function sendFeedback() {  // from either layout (#38)\n  const to = ['lanebecker', 'gmail.com'].join('@');")
sw(T, "new URLSearchParams({ subject: 'Ballotta test feedback', body }).toString().replace(/\\+/g, '%20');\n});\n",
      "new URLSearchParams({ subject: 'Ballotta test feedback', body }).toString().replace(/\\+/g, '%20');\n}\n"
      "$('feedback').addEventListener('click', (e) => { e.preventDefault(); sendFeedback(); });\n")
# Print, Clear my picks
sw(T, "$('print').addEventListener('click', () => { track('crib_printed', /*DESK*/ window.desk ? desk.cribOpts() : /*/DESK*/ { two_col: 'no', hide_unopposed: 'no' }); window.print(); });",
      "function printCrib() { track('crib_printed', /*DESK*/ window.desk ? desk.cribOpts() : /*/DESK*/ { two_col: 'no', hide_unopposed: 'no' }); window.print(); }  // from either layout (#38)\n"
      "$('print').addEventListener('click', printCrib);")
sw(T, "$('reset').addEventListener('click', () => { if (confirm('Clear all your picks and reasons?')) {",
      "function clearPicks() { if (confirm('Clear all your picks and reasons?')) {")
sw(T, "r.forEach(b => $('s' + b.c.id).innerHTML = summaryHTML(b.c.id)); refresh(); } } });",
      "r.forEach(b => $('s' + b.c.id).innerHTML = summaryHTML(b.c.id)); refresh(); } } }  // from either layout (#38)\n"
      "$('reset').addEventListener('click', clearPicks);")
# Hide a friend's picks
sw(T, "  $('f-hide').addEventListener('click', () => { f.classList.add('hidden'); $('compare').classList.add('hidden'); SS.del('ballotta.incoming'); friend = null; });",
      "  $('f-hide').addEventListener('click', hideFriend);")
sw(T, "function friendName() {",
      "function hideFriend() {  // Hide these picks, from either layout (#38)\n"
      "  $('friend').classList.add('hidden'); $('compare').classList.add('hidden'); SS.del('ballotta.incoming'); friend = null;/*DESK*/ if (window.desk) try { desk.render(); } catch (e) {}/*/DESK*/\n"
      "}\nfunction friendName() {")
# A message about an incoming link
sw(T, "  const say = (t) => { const m = $('lookupmsg'); m.textContent = t; m.classList.remove('hidden'); SS.del('ballotta.incoming');/*DESK*/ if (window.desk) try { desk.say(t); } catch (e) {}/*/DESK*/ };",
      "  const say = notify;")
sw(T, "  $('lookupmsg').classList.add('hidden');/*DESK*/ if (window.desk) try { desk.say(''); } catch (e) {}/*/DESK*/\n", "  notify('');\n")
sw(T, "async function handleIncoming(inc, fresh) {",
      "// A message about an incoming link, on both layouts (the phone's lookup form, the laptop's notice); '' clears it (#38).\n"
      "function notify(t) {\n"
      "  const m = $('lookupmsg'); m.textContent = t; m.classList.toggle('hidden', !t);\n"
      "  if (t) SS.del('ballotta.incoming');/*DESK*/ if (window.desk) try { desk.say(t); } catch (e) {}/*/DESK*/\n"
      "}\n"
      "async function handleIncoming(inc, fresh) {")
# The laptop layout calls them
sw(T, "    else if (a === 'hidefriend') { if ($('f-hide')) $('f-hide').click(); render(); if (WIDE.matches) P().focus({ preventScroll: true }); }\n    else if (a === 'print') $('print').click();\n",
      "    else if (a === 'hidefriend') { hideFriend(); if (WIDE.matches) P().focus({ preventScroll: true }); }\n    else if (a === 'print') printCrib();\n")
sw(T, "    if (a === 'feedback') $('feedback').click();\n", "    if (a === 'feedback') sendFeedback();\n")
sw(T, "    else if (a === 'clear') { $('reset').click(); render(); }\n    else if (a === 'clearall') $('reset-all').click();\n",
      "    else if (a === 'clear') { clearPicks(); render(); }\n    else if (a === 'clearall') clearEverything();\n")
sw(T, "  $('friend').addEventListener('click', (e) => { if (e.target.closest('#f-hide')) render(); });  // runs after the button's own handler (it's on the container)\n", "")
sw(T, "  $('dk-share').addEventListener('click', () => $('a-share').click());\n  $('dk-keep').addEventListener('click', () => $('a-keep').click());\n",
      "  $('dk-share').addEventListener('click', openShare);\n  $('dk-keep').addEventListener('click', openKeep);\n")
sw(T, "      // Same words as the phone layout, copied from the page so the two never drift apart.\n",
      "      // Same words as the phone layout, copied from the page so the two never drift apart: static text, the one\n"
      "      // deliberate copy left after #38 (behaviour goes through shared functions).\n")

# README
sw(RM, "If the county can't match it, the browser places it with the U.S. Census geocoder and uses the nearest registered addresses.",
       "If the county can't match it, the browser places it with the U.S. Census geocoder and uses the nearest registered addresses. The Census answers only as a script, so it runs in a sandboxed frame (`census.html`) that can't read the page or its storage and can pass back only a map point.")
sw(RM, "\n## Rebuilding\n",
       "\nThe page is locked down: a Content-Security-Policy (built by `build_site.py` from the hashes of the page's own scripts) lets only its own scripts and files from this site run, lets it talk only to the county map server and the counting service, and allows frames only from this site. It sends no referrer to any site it asks or links to.\n\n## Rebuilding\n")
sw(RM, "python3 source/build_site.py                        # writes index.html\n",
       "python3 source/build_site.py                        # writes index.html and census.html\n")
sw(RM, "python3 tests/mutate_desk.py 0 89                   # mutation check of the laptop tests (slow; restores every file it touches)\n",
       "python3 tests/mutate_desk.py                        # mutation check of the tests (slow; restores every file it touches, even when stopped)\n")

for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
print('fixes B applied to', ', '.join(files))
```

## Script: edits_mutants_B.py

```python
"""Issues round, commit B: mutants for #36 and #38, and anchors the refactor moved. Run from the repo root after
edits_page_B.py:  python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
MD = ROOT / 'tests/mutate_desk.py'
m = MD.read_text(encoding='utf-8')
def sw(a, z):
    global m
    if m.count(a) != 1: sys.exit(f'mutate_desk.py: FIND occurs {m.count(a)} times: {a[:70]!r}')
    m = m.replace(a, z)
sw("MD_SELF = ROOT / 'tests/mutate_desk.py'", "LEARN = ROOT / 'source/learn.json'\nMD_SELF = ROOT / 'tests/mutate_desk.py'")
# anchors the refactor moved (#38)
for pre in ("('M29 ", "('V40 ", "('F11 "):
    hits = [l for l in m.split('\n') if l.startswith(' ' + pre)]
    assert len(hits) == 1, pre
    m = m.replace(hits[0] + '\n', '')
NEW = [
 ('M29 hiding a friend leaves the landing broken', 'PREV', "friend = null;/*DESK*/ if (window.desk) try { desk.render(); } catch (e) {}/*/DESK*/\n}\nfunction friendName", "friend = null;\n}\nfunction friendName", ['desk_friend_hide_on_landing']),
 ('V40 clear everything missing from the menu', 'PREV', "    else if (a === 'clearall') clearEverything();\n", '', ['desk_counts_laptop_features']),
 ('F11 old warning survives a good link', 'PREV', "  notify('');\n", '', ['desk_launch_audit_fixes']),
 ('B1 no Content-Security-Policy', 'BLD', 'return html.replace("<!--CSP-->", csp_meta(html), 1)', 'return html', ['page_is_locked_down']),
 ('B2 inline scripts allowed', 'BLD', "script-src 'self' {hashes};", "script-src 'self' 'unsafe-inline';", ['page_is_locked_down']),
 ('B3 referrer sent', 'TPL', '<meta name="referrer" content="no-referrer">\n', '', ['page_is_locked_down']),
 ('B4 data may go anywhere', 'BLD', 'connect-src https://taxmaps.traviscountytx.gov https://gateway.umami.is;', 'connect-src *;', ['page_is_locked_down']),
 ('B5 Census frame not sandboxed', 'PREV', "f.setAttribute('sandbox', 'allow-scripts');", "f.setAttribute('sandbox', 'allow-scripts allow-same-origin');", ['census_runs_in_a_sandbox']),
 ('B6 any point accepted', 'PREV', ' && d.x > -107 && d.x < -93 && d.y > 25 && d.y < 37', '', ['census_runs_in_a_sandbox']),
 ('B7 any window may answer', 'PREV', '      if (e.source !== f.contentWindow) return;\n', '', ['census_runs_in_a_sandbox']),
 ('B8 frame left behind', 'PREV', "window.removeEventListener('message', on); f.remove(); resolve(v);", "window.removeEventListener('message', on); resolve(v);", ['census_runs_in_a_sandbox']),
 ('B9 census.html out of date', 'BLD', "if (e.source !== parent || typeof e.data", "if (typeof e.data", ['census_runs_in_a_sandbox']),
 ('B10 a campaign site back on http', 'LEARN', '"https://cuero4rrisd.com"', '"http://cuero4rrisd.com"', ['campaign_links_use_https_where_they_work']),
 ('C1 laptop Share clicks the phone button', 'PREV', "  $('dk-share').addEventListener('click', openShare);", "  $('dk-share').addEventListener('click', () => $('a-share').click());", ['desk_works_without_phone_buttons']),
 ('C2 laptop hours copied from the phone page', 'PREV', "<div class=\"sub\">' + hoursHTML() + '</div>'", "<div class=\"sub\">' + $('hours').innerHTML + '</div>'", ['desk_works_without_phone_buttons']),
 ('C3 laptop crib copied from the phone page', 'PREV', "'\" id=\"dk-page\">' + cribHTML() + '</div>';", "'\" id=\"dk-page\">' + $('crib').innerHTML + '</div>';", ['desk_works_without_phone_buttons']),
 ('C4 laptop print clicks the phone button', 'PREV', "    else if (a === 'print') printCrib();", "    else if (a === 'print') $('print').click();", ['desk_works_without_phone_buttons']),
 ('C5 laptop clear clicks the phone button', 'PREV', "    else if (a === 'clear') { clearPicks(); render(); }", "    else if (a === 'clear') { $('reset').click(); render(); }", ['desk_works_without_phone_buttons']),
]
k = m.index('\n]\n')
m = m[:k] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in NEW).rstrip('\n') + '\n]\n' + m[k + 3:]
MD.write_text(m, encoding='utf-8')
print('mutants B added:', len(NEW) - 3, '(and 3 re-anchored)')
```

## Script: rework_B1.py

```python
"""Issues round, commit B: rework after remediation-audit Pass 1. Run from the repo root after edits_mutants_B.py:
    python3 <this file> && python3 source/build_site.py"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
T, B, TS, MD = 'source/template-travis.html', 'source/build_site.py', 'tests/test_site.py', 'tests/mutate_desk.py'
files = {}
def sw(path, a, z):
    s = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
    if s.count(a) != 1: sys.exit(f'{path}: FIND occurs {s.count(a)} times: {a[:80]!r}')
    files[path] = s.replace(a, z)

# ---- P1-1: census.html runs only sandboxed, and builds the Census address itself (fixed callback); the page sends
# only the address text
sw(B, "    \"window.addEventListener('message', function on(e) {\\n\"\n"
      "    \"  if (e.source !== parent || typeof e.data !== 'string' || e.data.indexOf('https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?') !== 0) return;\\n\"\n",
      "    \"window.addEventListener('message', function on(e) {\\n\"\n"
      "    \"  // Only inside Ballotta's sandbox (an opaque origin), only for its own page, only an address (Pass 1).\\n\"\n"
      "    \"  if (self.origin !== 'null' || e.source !== parent || typeof e.data !== 'string' || e.data.length > 200) return;\\n\"\n")
sw(B, "    \"  s.src = e.data; s.onerror = function () { parent.postMessage(null, '*'); };\\n\"\n",
      "    \"  s.src = 'https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?' + new URLSearchParams({ address: e.data, benchmark: 'Public_AR_Current', format: 'jsonp', callback: 'cb' });\\n\"\n"
      "    \"  s.onerror = function () { parent.postMessage(null, '*'); };\\n\"\n")
sw(B, "    \"// Built by source/build_site.py; don't edit census.html. Ballotta's page sends one Census geocoder address;\\n\"\n",
      "    \"// Built by source/build_site.py; don't edit census.html. Ballotta's page sends one address;\\n\"\n")
# ---- P1-2: the page answers the frame's first load only (a reloading frame can't loop requests)
sw(T, "    f.addEventListener('load', () => f.contentWindow.postMessage('https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?' + new URLSearchParams({ address: street + ', TX ' + zip, benchmark: 'Public_AR_Current', format: 'jsonp', callback: 'cb' }), '*'));",
      "    f.addEventListener('load', () => f.contentWindow.postMessage((street + ', TX ' + zip).slice(0, 200), '*'), { once: true });  // once: a reloading frame can't loop (Pass 1)")
# ---- P1-3: the preview (one folder down) finds census.html at the root
sw(B, "        for a, b in [(\"url('fonts/\", \"url('../fonts/\"), ('href=\"favicon.svg\"', 'href=\"../favicon.svg\"'),\n",
      "        for a, b in [(\"url('fonts/\", \"url('../fonts/\"), ('href=\"favicon.svg\"', 'href=\"../favicon.svg\"'), (\"f.src = 'census.html'\", \"f.src = '../census.html'\"),\n")

# ---- tests
sw(TS, "    deskjs = src[src.index('const desk = (() => {'):src.index('window.desk = desk;')]",
       "    page = (ROOT / PAGE).read_text(encoding='utf-8')                     # the page under test (mutants change it)\n"
       "    deskjs = page[page.index('const desk = (() => {'):page.index('window.desk = desk;')]")
sw(TS, "    assert (ROOT / 'census.html').read_text(encoding='utf-8') == m.census_page(), 'census.html on disk is not what the build writes'\n",
       "    assert (ROOT / 'census.html').read_text(encoding='utf-8') == m.census_page(), 'census.html on disk is not what the build writes'\n"
       "    assert \"f.src = '../census.html'\" in m.build(preview=True), 'the preview (one folder down) finds census.html at the root (Pass 1)'\n"
       "    # Embedded by another page without a sandbox, census.html does nothing (it would run as this site) (Pass 1).\n"
       "    ctx, pg = new_page(b, csp=True); hits = []\n"
       "    ctx.route(re.compile(r'https://geocoding\\.geo\\.census\\.gov/.*'), lambda r: (hits.append(r.request.url), r.abort()))\n"
       "    pg.goto(BASE)\n"
       "    pg.evaluate(\"() => new Promise(ok => { const f = document.createElement('iframe'); f.src = 'census.html'; f.onload = () => { f.contentWindow.postMessage('1 Main St, TX 78701', '*'); setTimeout(ok, 800); }; document.body.appendChild(f); })\")\n"
       "    assert hits == [], ('census.html ran outside its sandbox', hits)\n"
       "    ctx.close()\n")
sw(TS, "    for body, reason in ((hostile, 'no_voters_nearby'),                                                  # a point came back\n",
       "    looper = \"location.href = 'census.html?again';\"                                                       # reloads the frame (Pass 1)\n"
       "    for body, reason in ((hostile, 'no_voters_nearby'),                                                  # a point came back\n"
       "                         (looper, 'not_found'),\n")
sw(TS, "        assert refs == [None], ('the Census request carries no referrer', refs)\n",
       "        assert refs == [None], ('one Census request, with no referrer: a reloading frame does not loop', len(refs), refs[:2])\n")

# ---- mutants
m = files.setdefault(MD, (ROOT / MD).read_text(encoding='utf-8'))
hits = [l for l in m.split('\n') if l.startswith(" ('B9 ")]
assert len(hits) == 1; m = m.replace(hits[0] + '\n', '')
NEW = [
 ('B9 census.html out of date', 'BLD', " || e.source !== parent || ", " || ", ['census_runs_in_a_sandbox']),
 ('B11 census.html runs unsandboxed', 'BLD', "if (self.origin !== 'null' || ", 'if (', ['census_runs_in_a_sandbox']),
 ('B12 a reloading frame loops', 'PREV', ", '*'), { once: true });  // once", ", '*'));  // once", ['census_runs_in_a_sandbox']),
 ('B13 preview looks for census.html in its own folder', 'BLD', ", (\"f.src = 'census.html'\", \"f.src = '../census.html'\")", '', ['census_runs_in_a_sandbox']),
]
k = m.index('\n]\n')
m = m[:k] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in NEW).rstrip('\n') + '\n]\n' + m[k + 3:]
files[MD] = m
for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
print('rework B1 applied to', ', '.join(files))
```
