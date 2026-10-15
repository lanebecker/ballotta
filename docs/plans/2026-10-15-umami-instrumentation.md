# Umami instrumentation: fine-grained, privacy-first counting

**Status:** written Oct 15, 2026 after Lane approved the event map ("Yes plan it"), chose "Clear everything on this device" next to "Clear my picks", and turned on page-speed measurements. Revised twice the same day after two verification passes (record at the end). Not yet approved for execution.

**Goal.** Count how people use and share Ballotta in much more detail, while making sure the page can't send anything personal. Every request to Umami passes through one checkpoint (the *privacy firewall*) that only lets listed events, listed details and listed values through. Do Not Track or Global Privacy Control turns counting off entirely.

**Also in this round:**
- "Clear everything on this device" (issue #29).
- Page-speed measurements.
- One sentence about Do Not Track and Global Privacy Control, in the form's privacy note and in the FAQ answer "What happens to my address and picks?". The FAQ wording Lane approved gains this sentence: flag it to him.
- A fix for a pre-existing hang: a county outage after the Census fallback left the page on "Finding your address…" forever.
- An up-to-date README.

**Base:** `main` at `4c4510a` ("Turn on the laptop layout"), where the laptop layout is live (`DESK_LIVE = True`) and `python3 tests/test_site.py` passes 41/41 against `index.html`.

## Rules for whoever executes this (human or agent)

- Work in `/home/claude/ballotta` (a sandbox clone, not a mounted folder). Every subagent dispatch includes, verbatim: "Do not run any git command (not even status/diff) against /home/claude/ballotta; work on a copy." Give agents a tarball copy.
- No destructive git: never `reset --hard`, `checkout --`, `stash`, `clean -f` or force-push. Mutants are reverted in memory by `tests/mutate_desk.py`, never with git.
- Never send Lane's email address to any service. It only exists as two halves joined at runtime in the feedback link.
- Commit as `git -c user.name="Lane Becker" -c user.email="3211673+lanebecker@users.noreply.github.com" commit`, with the trailers `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and `Claude-Session: https://claude.ai/code/session_01ESRbqS3dGWHQThLF6J7gxN`. Push straight to `main` (Lane's rule until Nov 3).
- Run the test suite and the mutation runner one at a time: both use port 8765. Before Tasks 0, 1, 4 and 6, check that `ps -eo pid,args | grep "mutate_desk.py" | grep -v grep` prints nothing.
- The mutation runner rewrites `index.html`, `source/*` and `README.md` in place while it runs (restoring them from memory afterwards). Never copy, edit, build or commit while it is running.
- Find processes by their full argument list (`ps -eo pid,args | grep "mutate_desk.py 0 1"`), never with `pgrep -f`/`pkill -f` on a pattern that also appears in your own command line (that kills your own shell).

## The event map (what gets counted)

Every event also carries `layout`: `laptop` when the laptop layout is on screen (a wide window, with the laptop code present), otherwise `phone`. After a rollback (`DESK_LIVE = False`), every visitor counts as `phone`.

| Event | Details (the only allowed values) | When |
|---|---|---|
| `lookup_started` | none | the address form passes its checks |
| `lookup_failed` | `reason`: `no_street`, `bad_zip`, `not_found`, `no_voters_nearby`, `county_unreachable` | each failure message |
| `units_asked` | none | the "which unit is yours?" picker appears |
| `ballot_found` | `match`: `exact`, `nearby`, `near a line` | unchanged |
| `address_changed` | none | a lookup brings up a different ballot from the one already showing (this visit or saved earlier). Retyping the same address doesn't count, and a different address with an identical ballot can't be told apart |
| `link_damaged` | `kind`: `damaged`, `too_old` | a share or keep link can't be read |
| `progress` | `at`: `25`, `50`, `75`, `100`; `reasons`, `skipped`: `0`, `1-5`, `6+` | once per ballot, as each share of races is decided (skips count); the last 5 ballots on a device are remembered |
| `source_opened` | `kind`: `league_guide`, `campaign_site`, `official`, `news`, `reference`, `other`; `level`: `federal`, `state`, `courts`, `county`, `city`, `school`, `special`, `measure` (omitted outside a race) | an outbound link is clicked or middle-clicked |
| `directions_opened`, `wait_times_opened` | `period`: `early`, `eday` | the directions or live-wait links |
| `view_opened` | `view`: `decide`, `glance`, `vote`, `crib` | laptop view tabs |
| `shortcut_used` | `kind`: `pick`, `skip`, `move`, `reason`, `search` | laptop keys, once per kind per visit |
| `search_used`, `filter_used` | `filter`: `all`, `und`, `why` | laptop rail, once per visit (per filter) |
| `faq_seen` | none | the laptop FAQ scrolls into view, once per visit |
| `help_opened` | `item`: `feedback`, `privacy`, `about`, `address`, `clear`, `clearall` | laptop Feedback & Info items |
| `cleared` | `what`: `picks`, `everything` | after the confirm |
| `crib_printed` | `two_col`, `hide_unopposed`: `yes`, `no` | Print (phones always `no`, `no`) |
| `keep_created` | `via`: `share`, `copy`, `shown`, `email` | unchanged |
| `keep_restored`, `share_sheet_open` | none | unchanged |
| `share_created` | `sections` (share-sheet keys), `reasons` yes/no, `picks` `1-5`/`6-15`/`16+`, `via` `share`/`copy`/`shown`, `generation` 1–99, `link` (random code) | unchanged |
| `share_opened` | `generation`, `has_picks` yes/no, `link` | unchanged |
| `share_own_ballot` | `generation` | unchanged |
| `share_compare` | none | unchanged (the laptop's `layout: laptop` now comes from `track()` for every event) |

**Never sent:** addresses, precincts, districts, which race, candidate names, parties, picks, reasons or names. The firewall enforces this:
- values are checked against fixed lists or tight patterns;
- objects and arrays are never values;
- every outgoing payload is rebuilt from a fixed set of fields.

**Known, accepted effects:**
- On the first visit after this ships, a returning voter who already decided races will send the milestones they had reached (once per ballot).
- A keep link opened on a new device sends the milestones it already reached, all at once.
- "Clear everything" forgets which milestones were counted, so they count again afterwards.
- A sixth ballot pushes the oldest out of `ballotta.progress`, so going back to it counts its milestones again.
- Because both `nearby()` calls are now awaited, an unexpected page error while drawing a ballot on the Census or nearby path would show the county-outage message and count `county_unreachable`, as the exact-match path already did. Since `ballot_found` is now counted before the ballot is drawn, such an error would also leave a `ballot_found` behind. On the unit-picker path, the error isn't caught at all, so no message is shown. (HYPOTHESIS: no such error is known.)
- `generation` stays a number, as today, so Umami's existing property type doesn't change.
- Page-speed payloads (load time, largest paint, layout shift, responsiveness) pass the firewall unchanged; they carry no personal data.

## How it works (read before the tasks)

- **`EVENTS` in `source/template-travis.html`** lists every event and, per detail, a check function (`ONE_OF(...)`, `GEN`, `CODE`, or the share-section check).
- **`clean(name, data)`** returns only the details that pass. It drops unlisted events (returns `null`) and records what it removed in `window.ballottaDropped`, for the tests only; that array is never sent anywhere.
- **`track(name, data)`** adds `layout`, then runs `clean()`, then hands the result to Umami.
- **`window.ballottaBeforeSend(type, payload)`** is named in the tracker tag (`data-before-send`), so the real tracker calls it with every payload it is about to send, including page views. It:
  - returns `null` (send nothing) under Do Not Track or Global Privacy Control, and for any payload type other than `event` and `performance`, so `umami.identify` session data is never sent;
  - rebuilds the payload from a fixed set of *text* fields (`website, hostname, screen, language, title, url, referrer, tag, name`), cutting any `?query` or `#fragment` from `url` and `referrer`, plus the numeric `ttfb, fcp, lcp, cls, inp, duration` on page-speed reports. So a distinct `id`, an object, an array or any new field is dropped;
  - gives only named events a `data`, run through `clean()` again. Page views and speed reports carry no details.
- **The build puts a stand-in before the tracker tag:** `<script>window.ballottaBeforeSend = () => null;</script>`. If the page's own script failed before defining the real check, the tracker would send nothing; without the stand-in it would send everything unfiltered (it only calls the hook when one exists). Umami still groups a visit's requests into a session with its own cache header, as it does on any site; no distinct id or `identify` data is sent.
- **The tracker tag** gains `data-do-not-track="true" data-before-send="ballottaBeforeSend" data-performance="true"`.
- **Outbound links** are counted by one capturing click listener (plus `auxclick` for middle clicks). It classifies the link:
  - by hostname, through `KIND_BY_HOST`;
  - by its "Campaign site" label, which marks campaign sites;
  - as `directions_opened` or `wait_times_opened` when it's a directions or wait-times link.

  It reads the race's level from the enclosing phone race card, or, on a laptop, from `#dk-paper`'s `data-c`. The laptop's `render()` sets that to the current race in Decide and clears it in every other view.
- **Progress milestones** are checked at the end of `refresh()`, which runs after every pick and every ballot render. Which ones were counted is kept in `localStorage` under `ballotta.progress`: a list of `{sig, at}` records for the last 5 ballots, keyed by each ballot's contest list.
- **`ballot_found` and `address_changed`** are sent from `render()` (fresh lookups only) *before* the ballot is shown. That way a progress milestone the new ballot triggers (picks are kept by contest, so a shared race may already be decided) comes after `ballot_found`, and funnels stay in order. `address_changed` is sent when the new contest list differs from the one that was showing.
- **Both `nearby(...)` calls in `lookup()` are now awaited**, so a county failure after the Census fallback reaches the `catch`. It then shows the "couldn't reach Travis County's map server" message and counts `county_unreachable`. Before, the page hung.
- **Clear everything** removes every `ballotta.*` key from `localStorage` and `sessionStorage`, counts `cleared {what: everything}` first, and reloads the page without its fragment. It asks before doing anything.

## Task 0: baseline

```
ps -eo pid,args | grep "mutate_desk.py" | grep -v grep; (echo > /dev/tcp/127.0.0.1/8765) 2>/dev/null && echo "PORT 8765 BUSY" || echo "port 8765 free"
cd /home/claude/ballotta && git log --oneline -1 && git status --short
python3 source/build_site.py && git status --short && timeout 590 python3 tests/test_site.py | tail -1
```

Expected: `4c4510a Turn on the laptop layout` (or a later commit that only touched docs), an empty status both times, and `41/41 passed (index.html)`. If the base differs, stop and re-check every FIND below with a dry run (Task 1 and Task 2 scripts refuse to apply when a FIND doesn't match exactly once, and change nothing in that case).

## Task 1: the tests first (RED)

Save this as `/tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/umami/edits_tests.py` and run it from the repo root. It updates three existing payload checks (every event now carries `layout`) and one older test (T4: a failing laptop hook must not show up as a county outage), and adds six tests.

```python
"""Umami round, test edits.  Run from the repo root:  python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
TS = 'tests/test_site.py'

NEW_TESTS = r'''
# ---------------------------------------------------------------- anonymous counts: the privacy firewall (Umami round)
def event_names_in_page():
    src = (ROOT / 'source/template-travis.html').read_text(encoding='utf-8')
    block = src[src.index('const EVENTS = {'):src.index('};', src.index('const EVENTS = {'))]
    return re.findall(r'^  ([a-z_]+): \{', block, re.M)

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
    odd = {'url': '/?addr=1000+Guadalupe#k=x', 'referrer': 'https://a.example/p?q=1', 'title': {'street': 'x'}, 'tag': ['78701'], 'website': 'w'}
    assert bs(odd) == {'url': '/', 'referrer': 'https://a.example/p', 'website': 'w'}, 'only text fields, and never a query or fragment'
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
    for b_ in ('[1, 2, 3, 4]', '[5, 6, 7, 8]', '[1, 2, 3, 4]'):                                    # ballot A, then B, then A again
        pg.evaluate(f"renderStored({{ pr: '9', b: {b_}, mode: 'saved' }}, 'test'); ballot.forEach(x => {{ if (!current(x.c.id).length) pick(x.c.id, '__skip'); }})")
    assert len(prog()) == 12, ('A and B count 4 milestones each; A again counts none', prog())
    pg.evaluate("renderStored(JSON.parse(localStorage.getItem('ballotta.ballot')), 'test')")
    pg.reload(); pg.wait_for_selector('#result:not(.hidden)'); pg.wait_for_timeout(500)
    assert names(pg).count('progress') == 0, 'counted once per ballot, not per visit'
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
    pg.evaluate("umami.track = (n, d) => sessionStorage.setItem('__last', JSON.stringify([n, d]))")   # survives the reload
    pg.once('dialog', lambda d: d.accept()); pg.click('#reset-all')
    pg.wait_for_function("!document.getElementById('result') || document.getElementById('result').classList.contains('hidden')")
    pg.wait_for_load_state()
    assert pg.evaluate(LS_KEYS) == [], pg.evaluate(LS_KEYS)
    assert pg.evaluate("JSON.parse(sessionStorage.getItem('__last'))") == ['cleared', {'what': 'everything', 'layout': 'phone'}]
    assert pg.is_hidden('#result') and pg.evaluate('location.hash') == ''
    ctx.close()
    ctx, pg = new_page(b); pg.goto(BASE); lookup(pg)                                             # asking first: Cancel keeps everything
    pg.once('dialog', lambda d: d.dismiss()); pg.click('#reset-all')
    assert pg.evaluate("localStorage.getItem('ballotta.ballot')") and pg.is_visible('#result')
    ctx.close()

@desk_test
def desk_counts_laptop_features(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
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
    pg.click('#dk-c2'); pg.evaluate('window.print = () => {}'); pg.click('#dk-print')
    assert events(pg)[-1] == ['crib_printed', {'two_col': 'yes', 'hide_unopposed': 'no', 'layout': 'laptop'}], events(pg)[-1]
    pg.click('#dk-views [data-view="decide"]'); pg.click('.dk-row[data-row="c001"]')
    pg.locator('#dk-paper a', has_text='League guide answers').first.click()
    pg.locator('#dk-notes a', has_text='League of Women Voters guide').first.click()
    assert [e[1] for e in events(pg) if e[0] == 'source_opened'] == [{'kind': 'league_guide', 'level': 'federal', 'layout': 'laptop'}] * 2
    assert [e[1]['view'] for e in events(pg) if e[0] == 'view_opened'] == ['glance', 'vote', 'crib', 'decide']
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
    assert 'Global Privacy Control' in readme and 'ballotta.progress' in readme
'''

EDITS = [
 ('T1 keep payload carries the layout', TS, "    assert ['keep_created', {'via': 'copy'}] in events(pg)",
  "    assert ['keep_created', {'via': 'copy', 'layout': 'phone'}] in events(pg)"),
 ('T2 share_opened payload carries the layout', TS, "    assert op == {'generation': 1, 'has_picks': 'no', 'link': ev['link']}, op",
  "    assert op == {'generation': 1, 'has_picks': 'no', 'link': ev['link'], 'layout': 'phone'}, op"),
 ('T0 ballot_found carries the layout', TS, "    assert ['ballot_found', {'match': 'exact'}] in ev, ev",
  "    assert ['ballot_found', {'match': 'exact', 'layout': 'phone'}] in ev and ['lookup_started', {'layout': 'phone'}] in ev, ev"),
 ('T4 a failing laptop hook is not an outage', TS,
  "    assert 'United States Senator' in pg.inner_text('#crib') and not errs, errs                          # the crib sheet still renders\n",
  "    assert 'United States Senator' in pg.inner_text('#crib') and not errs, errs                          # the crib sheet still renders\n"
  "    assert 'lookup_failed' not in names(pg) and pg.locator('#status.bad').count() == 0, 'a laptop-code failure is not reported as a county outage'\n"),
 ('T3 new tests', TS, "\ndef main():\n", NEW_TESTS + "\ndef main():\n"),
]

if __name__ == '__main__':
    files = {}
    for name, path, find, repl in EDITS:
        f = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
        n = f.count(find)
        if n != 1: sys.exit(f'{name}: FIND occurs {n} times in {path}')
        files[path] = f.replace(find, repl)
    for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
    print('applied', len(EDITS), 'test edits')
```

```
cd /home/claude/ballotta && python3 /tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/umami/edits_tests.py
```

Expected: `applied 5 test edits`. Then run just the new tests against today's page:

```
cd /home/claude/ballotta && BALLOTTA_PAGE=index.html timeout 590 python3 /tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/land/one.py privacy_firewall_drops_anything_unlisted real_tracker_sends_only_listed_events counts_where_people_drop_off counts_progress_sources_and_clearing desk_counts_laptop_features readme_lists_every_counted_event
```

`one.py` imports `tests/test_site.py`, starts its server, runs the named tests and prints PASS or FAIL for each. If it isn't at that path, save this as `/tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/land/one.py`:

```python
"""Run named tests against the preview:  python3 one.py name [name ...]   (from the repo root)"""
import os, sys
os.environ.setdefault('BALLOTTA_PAGE', 'index.html'); sys.path.insert(0, 'tests')
import test_site as T
from playwright.sync_api import sync_playwright
srv = T.serve(); bad = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for n in sys.argv[1:]:
        try: getattr(T, n)(b); print('PASS', n)
        except Exception as e: bad += 1; print('FAIL', n, '-', (str(e) or type(e).__name__)[:600])
    b.close()
srv.shutdown(); sys.exit(1 if bad else 0)
```

Expected: all six `FAIL`:
- `window.ballottaBeforeSend is not a function`;
- `substring not found`, twice (the `EVENTS` list doesn't exist yet);
- an `AssertionError`;
- `[]`;
- a `Timeout` waiting for `faq_seen`.

## Task 2: the page and the tracker tag

Save this as `/tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/umami/edits_page.py` and run it from the repo root. Each edit names what it does (U1 to U7).

```python
"""Umami round, page and build edits.  Run from the repo root:  python3 <this file>
Each FIND must occur exactly once; the script stops on the first one that doesn't (nothing is half-applied per file)."""
import pathlib, sys
ROOT = pathlib.Path.cwd()
T, B = 'source/template-travis.html', 'source/build_site.py'

EDITS = [
# ---------------------------------------------------------------- U1: the privacy firewall and track()
('U1 firewall', T,
"""/* ---------- anonymous counts (Umami; no-op when not configured) ---------- */
const TQ = [];
function track(name, data) {
  try { if (window.umami && typeof umami.track === 'function') umami.track(name, data || {}); else if (TQ.length < 20) TQ.push([name, data || {}]); } catch (e) {}
}
""",
"""/* ---------- anonymous counts (Umami) ----------
   The privacy firewall. Every event Ballotta may count is listed in EVENTS, with the only values each property may
   take. track() and the tracker's before-send hook (window.ballottaBeforeSend, named in the tracker tag) both pass
   everything through clean(), which drops any event or property not listed here. So a new feature or a bug can't send
   an address, precinct, district, race, candidate, pick, reason or name. A browser sending Do Not Track or Global
   Privacy Control turns counting off entirely, page views included. README.md lists the same events. */
const ONE_OF = (...vals) => (v) => vals.includes(v);
const YN = ONE_OF('yes', 'no'), FEW = ONE_OF('0', '1-5', '6+');
const GEN = (v) => /^[1-9][0-9]?$/.test(v), CODE = (v) => /^[a-z0-9]{1,8}$/.test(v);
const SECTION_KEYS = ['federal', 'state', 'county', 'city', 'school', 'special'];  // the share sheet's sections
const EVENTS = {
  lookup_started: {},
  lookup_failed: { reason: ONE_OF('no_street', 'bad_zip', 'not_found', 'no_voters_nearby', 'county_unreachable') },
  units_asked: {},
  ballot_found: { match: ONE_OF('exact', 'nearby', 'near a line') },
  address_changed: {},
  link_damaged: { kind: ONE_OF('damaged', 'too_old') },
  progress: { at: ONE_OF('25', '50', '75', '100'), reasons: FEW, skipped: FEW },
  source_opened: { kind: ONE_OF('league_guide', 'campaign_site', 'official', 'news', 'reference', 'other'), level: ONE_OF('federal', 'state', 'courts', 'county', 'city', 'school', 'special', 'measure') },
  directions_opened: { period: ONE_OF('early', 'eday') },
  wait_times_opened: { period: ONE_OF('early', 'eday') },
  view_opened: { view: ONE_OF('decide', 'glance', 'vote', 'crib') },
  shortcut_used: { kind: ONE_OF('pick', 'skip', 'move', 'reason', 'search') },
  search_used: {},
  filter_used: { filter: ONE_OF('all', 'und', 'why') },
  faq_seen: {},
  help_opened: { item: ONE_OF('feedback', 'privacy', 'about', 'address', 'clear', 'clearall') },
  cleared: { what: ONE_OF('picks', 'everything') },
  crib_printed: { two_col: YN, hide_unopposed: YN },
  keep_created: { via: ONE_OF('share', 'copy', 'shown', 'email') },
  keep_restored: {},
  share_sheet_open: {},
  share_created: { sections: (v) => v === '' || v.split(',').every(k => SECTION_KEYS.includes(k)), reasons: YN, picks: ONE_OF('1-5', '6-15', '16+'), via: ONE_OF('share', 'copy', 'shown'), generation: GEN, link: CODE },
  share_opened: { generation: GEN, has_picks: YN, link: CODE },
  share_own_ballot: { generation: GEN },
  share_compare: {},
};
const LAYOUT = ONE_OF('phone', 'laptop');
const dropped = [];  // what clean() removed: kept in this page only, so the tests can prove our own calls never trip it
window.ballottaDropped = dropped;
function clean(name, data) {
  const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
  if (typeof name !== 'string' || !has(EVENTS, name)) { dropped.push(String(name)); return null; }
  const spec = EVENTS[name], out = {}, d = data && typeof data === 'object' ? data : {};
  Object.keys(d).forEach(k => {
    const v = d[k], ok = (typeof v === 'string' || typeof v === 'number') && (k === 'layout' ? LAYOUT(String(v)) : has(spec, k) && spec[k](String(v)));
    if (ok) out[k] = v; else dropped.push(name + '.' + k);
  });
  return out;
}
const NO_COUNT = (() => { try { return navigator.globalPrivacyControl === true || navigator.doNotTrack === '1' || window.doNotTrack === '1'; } catch (e) { return false; } })();
// The tracker calls this with every payload it is about to send. Only page views, events and page-speed reports
// pass, rebuilt from a fixed list of text fields (any ?query or #fragment cut from addresses): no distinct id, no
// identify data, nothing a future tracker might add. A stand-in defined before the tracker tag drops everything
// until this one exists, so if this script failed to run, nothing would be sent (build_site.py).
const TOP = ['website', 'hostname', 'screen', 'language', 'title', 'url', 'referrer', 'tag', 'name'];
const SPEED = ['ttfb', 'fcp', 'lcp', 'cls', 'inp', 'duration'];
window.ballottaBeforeSend = (type, p) => {
  if (NO_COUNT || !p || typeof p !== 'object' || (type !== 'event' && type !== 'performance')) return null;
  const out = {};
  TOP.forEach(k => { if (typeof p[k] === 'string') out[k] = k === 'url' || k === 'referrer' ? p[k].split(/[?#]/)[0] : p[k]; });
  if (type === 'performance') SPEED.forEach(k => { if (typeof p[k] === 'number') out[k] = p[k]; });
  if (out.name !== undefined) { const d = clean(out.name, p.data); if (!d) return null; out.data = d; }  // page views carry no details
  return out;
};
const TQ = [];
function track(name, data) {
  if (NO_COUNT) return;
  const d = clean(name, Object.assign({}, data, { layout: window.desk && matchMedia('(min-width: 1024px)').matches ? 'laptop' : 'phone' }));
  if (!d) return;
  try { if (window.umami && typeof umami.track === 'function') umami.track(name, d); else if (TQ.length < 20) TQ.push([name, d]); } catch (e) {}
}
"""),
# ---------------------------------------------------------------- U2: where people drop off
('U2a no street', T,
"""  if (!street) { show('bad', 'Enter your street address.'); return; }
  if (!/^\\d{5}$/.test(zip)) { show('bad', 'Enter your 5-digit ZIP code.'); return; }
  show('warn', 'Finding your address in Travis County’s records…');
""",
"""  if (!street) { show('bad', 'Enter your street address.'); track('lookup_failed', { reason: 'no_street' }); return; }
  if (!/^\\d{5}$/.test(zip)) { show('bad', 'Enter your 5-digit ZIP code.'); track('lookup_failed', { reason: 'bad_zip' }); return; }
  track('lookup_started');
  show('warn', 'Finding your address in Travis County’s records…');
"""),
('U2b not found', T,
"""      if (!pt) { show('bad', 'We couldn’t find that address. Check the spelling and ZIP. Only Travis County addresses are supported.'); return; }""",
"""      if (!pt) { show('bad', 'We couldn’t find that address. Check the spelling and ZIP. Only Travis County addresses are supported.'); track('lookup_failed', { reason: 'not_found' }); return; }"""),
('U2c county down', T,
"""    show('bad', 'We couldn’t reach Travis County’s map server just now (' + e.message + '). Check your connection and try again in a minute.');
""",
"""    show('bad', 'We couldn’t reach Travis County’s map server just now (' + e.message + '). Check your connection and try again in a minute.');
    track('lookup_failed', { reason: 'county_unreachable' });
"""),
('U2d nobody nearby', T,
"""  if (!near.length) { show('bad', 'We placed that address on the map, but there are no registered voting addresses near it. Check with the Travis County Tax Office.'); return; }""",
"""  if (!near.length) { show('bad', 'We placed that address on the map, but there are no registered voting addresses near it. Check with the Travis County Tax Office.'); track('lookup_failed', { reason: 'no_voters_nearby' }); return; }"""),
('U2e unit picker', T,
"""  box.className = 'unit';
  box.querySelectorAll('button').forEach(b => b.addEventListener('click', () => { box.className = 'unit hidden'; render(groups[+b.dataset.i][0], 'exact', label, null, pt); }));
""",
"""  box.className = 'unit';
  box.querySelectorAll('button').forEach(b => b.addEventListener('click', () => { box.className = 'unit hidden'; render(groups[+b.dataset.i][0], 'exact', label, null, pt); }));
  track('units_asked');
"""),
('U2f nearby failures reach the catch', T,
"""      return nearby(pt, pt.label);""",
"""      return await nearby(pt, pt.label);  // awaited, so a county outage here shows its message (it used to hang)"""),
('U2g nearby failures reach the catch (2)', T,
"""    return nearby(cand.location, cand.address);
  } catch (e) {""",
"""    return await nearby(cand.location, cand.address);
  } catch (e) {"""),
('U2h another address', T,
"""  here = pt ? [Math.round(pt.x * 1000) / 1000, Math.round(pt.y * 1000) / 1000] : null;""",
"""  const before = ballot.map(b => b.c.id).join(','), after = list.map(b => b.c.id).join(',');
  here = pt ? [Math.round(pt.x * 1000) / 1000, Math.round(pt.y * 1000) / 1000] : null;"""),
('U2i another address counted', T,
"""  showBallot(list, { mode, precinct: rec.Precinct, where });
  track('ballot_found', { match: { exact: 'exact', nearby: 'nearby', 'nearby-mixed': 'near a line' }[mode] || mode });
""",
"""  // Counted before the ballot shows, so a progress milestone the new ballot triggers comes after ballot_found.
  track('ballot_found', { match: { exact: 'exact', nearby: 'nearby', 'nearby-mixed': 'near a line' }[mode] || mode });
  if (before && before !== after) track('address_changed');  // came back and looked up an address with a different ballot
  showBallot(list, { mode, precinct: rec.Precinct, where });
"""),
# ---------------------------------------------------------------- U3: how far people get (progress milestones)
('U3 milestones', T,
"""  renderCrib();
  if (!$('compare').classList.contains('hidden')) renderCompare();/*DESK*/ if (window.desk) try { desk.refresh(); } catch (e) {}/*/DESK*/
}
""",
"""  renderCrib();
  if (!$('compare').classList.contains('hidden')) renderCompare();/*DESK*/ if (window.desk) try { desk.refresh(); } catch (e) {}/*/DESK*/
  milestones();
}
// Counted once per ballot (the last 5 ballots on this device are remembered), at 25, 50, 75 and 100% decided (a skip counts as decided), with rough
// counts of reasons written and races skipped. Never which races.
function milestones() {
  const ids = ballot.map(b => b.c.id), n = ids.length;
  if (!n) return;
  const sig = ids.join(','), saved = LS.get('ballotta.progress', []);
  const list = Array.isArray(saved) ? saved.filter(r => r && typeof r.sig === 'string' && Array.isArray(r.at)) : [];
  const rec = list.find(r => r.sig === sig), sent = rec ? rec.at : [];
  const done = ids.filter(id => current(id).length).length;
  const now = [25, 50, 75, 100].filter(p => done * 100 >= p * n && !sent.includes(p));
  if (!now.length) return;
  const few = (k) => k === 0 ? '0' : k <= 5 ? '1-5' : '6+';
  const reasons = few(ids.filter(id => typeof whys[id] === 'string' && whys[id].trim() !== '').length);
  const skipped = few(ids.filter(id => current(id)[0] === '__skip').length);
  LS.set('ballotta.progress', [{ sig, at: sent.concat(now) }].concat(list.filter(r => r.sig !== sig)).slice(0, 5));  // the last 5 ballots
  now.forEach(p => track('progress', { at: String(p), reasons, skipped }));
}
"""),
# ---------------------------------------------------------------- U4: what helps people decide (outbound links)
('U4 outbound links', T,
"""$('t-early').addEventListener('click', () => { period = 'early'; renderVote(); });
""",
"""// Outbound links: count the kind of link and the race's level, never which race or which candidate.
const KIND_BY_HOST = [[/(^|\\.)austinvotersguide\\.org$/, 'league_guide'], [/\\.gov$/, 'official'],
  [/(^|\\.)(texastribune\\.org|kut\\.org|statesman\\.com|apnews\\.com|votebeat\\.org)$/, 'news'], [/(^|\\.)(ballotpedia\\.org|wikipedia\\.org)$/, 'reference']];
function raceLevel(a) {
  const box = a.closest('details.race, #dk-paper, #dk-notes'), p = $('dk-paper');
  const id = !box ? '' : box.matches('details.race') ? box.id.slice(1) : (p && p.dataset.c) || '';
  const c = BYID[id];
  return !c ? '' : c.type === 'measure' ? 'measure' : c.level === 'Special district' ? 'special' : c.level.toLowerCase();
}
function outbound(e) {
  if (e.type === 'auxclick' && e.button !== 1) return;  // a middle click opens a link too
  const a = e.target && e.target.closest ? e.target.closest('a[href^="http"]') : null;
  if (!a) return;
  let host = '';
  try { host = new URL(a.href).hostname; } catch (err) { return; }
  if (host === 'www.google.com' && a.pathname.startsWith('/maps/dir')) return track('directions_opened', { period });
  if (host === 'updates.electionlink.net') return track('wait_times_opened', { period });
  const kind = a.textContent.trim() === 'Campaign site' ? 'campaign_site' : (KIND_BY_HOST.find(([re]) => re.test(host)) || [null, 'other'])[1];
  const level = raceLevel(a);
  track('source_opened', level ? { kind, level } : { kind });
}
document.addEventListener('click', outbound, true);
document.addEventListener('auxclick', outbound, true);
$('t-early').addEventListener('click', () => { period = 'early'; renderVote(); });
"""),
# ---------------------------------------------------------------- U5: damaged links, clearing, printing
('U5a damaged links', T,
"""  if (o === TOO_OLD) return say('This browser is too old to open that link. Update your phone’s software, or open the link in a current browser such as Chrome, Firefox or Safari.');
  if (!o || typeof o !== 'object' || o.v !== 1) return damaged();
""",
"""  if (o === TOO_OLD) { track('link_damaged', { kind: 'too_old' }); return say('This browser is too old to open that link. Update your phone’s software, or open the link in a current browser such as Chrome, Firefox or Safari.'); }
  if (!o || typeof o !== 'object' || o.v !== 1) { track('link_damaged', { kind: 'damaged' }); return damaged(); }
"""),
('U5b damaged after decoding', T,
"""  } catch (e) { damaged(); }
}""",
"""  } catch (e) { track('link_damaged', { kind: 'damaged' }); damaged(); }
}"""),
('U5c print and clear', T,
"""$('print').addEventListener('click', () => { track('crib_printed', {}); window.print(); });
$('reset').addEventListener('click', () => { if (confirm('Clear all your picks and reasons?')) { picks = {}; whys = {};""",
"""$('print').addEventListener('click', () => { track('crib_printed', /*DESK*/ window.desk ? desk.cribOpts() : /*/DESK*/ { two_col: 'no', hide_unopposed: 'no' }); window.print(); });
// Clear everything on this device (#29): every ballotta.* key in this browser, then a fresh page. Asks first.
$('reset-all').addEventListener('click', () => {
  if (!confirm('Clear everything Ballotta saved in this browser: your ballot, picks, reasons, map location and share name?')) return;
  track('cleared', { what: 'everything' });
  [localStorage, sessionStorage].forEach(s => { try { Object.keys(s).filter(k => k.startsWith('ballotta.')).forEach(k => s.removeItem(k)); } catch (e) {} });
  location.replace(location.pathname);
});
$('reset').addEventListener('click', () => { if (confirm('Clear all your picks and reasons?')) { track('cleared', { what: 'picks' }); picks = {}; whys = {};"""),
('U5d clear-everything button', T,
"""        <button class="btn secondary" id="reset" type="button">Clear my picks</button>
      </div>
""",
"""        <button class="btn secondary" id="reset" type="button">Clear my picks</button>
      </div>
      <button type="button" class="x" id="reset-all" style="align-self:flex-start">Clear everything on this device</button>
"""),
('U5e privacy note', T,
"""We count anonymous taps, like “a share link was opened”, never your address or your picks.</p>""",
"""We count anonymous taps, like “a share link was opened”, and how quickly pages load, never your address or your picks. If your browser sends Do Not Track or Global Privacy Control, we count nothing at all.</p>"""),
('U5f FAQ promise', T,
"""Picks and reasons stay in your browser unless you send yourself or a friend a link.</p></div>""",
"""Picks and reasons stay in your browser unless you send yourself or a friend a link. If your browser sends Do Not Track or Global Privacy Control, we count nothing at all.</p></div>"""),
# ---------------------------------------------------------------- U6: laptop features (inside the laptop-only code)
('U6a crib options and paper contest', T,
"""    cribSkip: (c) => ui.hideCrib && isUnopp(c),
""",
"""    cribSkip: (c) => ui.hideCrib && isUnopp(c),
    cribOpts: () => ({ two_col: ui.two ? 'yes' : 'no', hide_unopposed: ui.hideCrib ? 'yes' : 'no' }),
"""),
('U6b paper knows its contest', T,
"""    rail();
    $('dk-desk').className = 'dk-desk' + (ui.view === 'glance'""",
"""    rail();
    P().dataset.c = ui.view === 'decide' ? curB().c.id : '';  // an outbound link in the paper or notes is counted by the race's level, only in Decide
    $('dk-desk').className = 'dk-desk' + (ui.view === 'glance'"""),
('U6c compare layout', T,
"""track('share_compare', { layout: 'laptop' });""",
"""track('share_compare');"""),
('U6d menu items', T,
"""    const a = btn.dataset.help;
    if (a === 'feedback') $('feedback').click();""",
"""    const a = btn.dataset.help;
    track('help_opened', { item: a });
    if (a === 'feedback') $('feedback').click();"""),
('U6e clear everything in the menu', T,
"""    else if (a === 'clear') { $('reset').click(); render(); }
""",
"""    else if (a === 'clear') { $('reset').click(); render(); }
    else if (a === 'clearall') $('reset-all').click();
"""),
('U6f clear everything menu item', T,
"""      <button type="button" role="menuitem" data-help="clear" class="bad"><b>Clear my picks…</b><small>Asks before deleting anything</small></button>
""",
"""      <button type="button" role="menuitem" data-help="clear" class="bad"><b>Clear my picks…</b><small>Asks before deleting anything</small></button>
      <button type="button" role="menuitem" data-help="clearall" class="bad"><b>Clear everything on this device…</b><small>Ballot, picks, reasons, location and share name</small></button>
"""),
('U6g views, filters, search', T,
"""  document.querySelectorAll('#dk-views button').forEach(btn => btn.addEventListener('click', (e) => setView(btn.dataset.view, e.detail > 0)));
  document.querySelectorAll('#dk-filt button').forEach(btn => btn.addEventListener('click', () => { ui.filter = btn.dataset.f; rail(); }));
  $('dk-q').addEventListener('input', () => { ui.q = $('dk-q').value.trim(); rail(); });
""",
"""  const once = new Set();  // counted once per visit (page load), so a busy keyboard doesn't count 63 times
  const countOnce = (key, name, data) => { if (!once.has(key)) { once.add(key); track(name, data); } };
  document.querySelectorAll('#dk-views button').forEach(btn => btn.addEventListener('click', (e) => { setView(btn.dataset.view, e.detail > 0); track('view_opened', { view: btn.dataset.view }); }));
  document.querySelectorAll('#dk-filt button').forEach(btn => btn.addEventListener('click', () => { ui.filter = btn.dataset.f; rail(); countOnce('f:' + btn.dataset.f, 'filter_used', { filter: btn.dataset.f }); }));
  $('dk-q').addEventListener('input', () => { ui.q = $('dk-q').value.trim(); rail(); countOnce('search', 'search_used'); });
  if ('IntersectionObserver' in window) {  // did the FAQ scroll into view? once per visit
    const io = new IntersectionObserver((es) => { if (es.some(x => x.isIntersecting)) { countOnce('faq', 'faq_seen'); io.disconnect(); } }, { threshold: 0.25 });
    io.observe($('dk-faq'));
  }
"""),
('U6h shortcuts', T,
"""    if (k === '/') { e.preventDefault(); $('dk-q').focus(); return; }
    if (ui.view !== 'decide') return;
    if (e.repeat && (/^[1-9]$/.test(k) || k === 's')) return;  // a held key picks once (pick() toggles)
    const b = curB();
    if (/^[1-9]$/.test(k)) { const o = optionsOf(b.c)[+k - 1]; if (o !== undefined) { e.preventDefault(); pick(b.c.id, o); announce(b.c); } }
    else if (k === 's') { e.preventDefault(); pick(b.c.id, '__skip'); announce(b.c); }
    else if (k === 'n') { e.preventDefault(); act('next', true); }
    else if (k === 'j') { e.preventDefault(); const i = idx(b.c.id); if (i < ballot.length - 1) go(ballot[i + 1].c.id, true); }
    else if (k === 'k') { e.preventDefault(); act('prev', true); }
    else if (k === 'r') { e.preventDefault(); $('dk-w').focus(); }
""",
"""    const used = (kind) => countOnce('k:' + kind, 'shortcut_used', { kind });
    if (k === '/') { e.preventDefault(); $('dk-q').focus(); used('search'); return; }
    if (ui.view !== 'decide') return;
    if (e.repeat && (/^[1-9]$/.test(k) || k === 's')) return;  // a held key picks once (pick() toggles)
    const b = curB();
    if (/^[1-9]$/.test(k)) { const o = optionsOf(b.c)[+k - 1]; if (o !== undefined) { e.preventDefault(); pick(b.c.id, o); announce(b.c); used('pick'); } }
    else if (k === 's') { e.preventDefault(); pick(b.c.id, '__skip'); announce(b.c); used('skip'); }
    else if (k === 'n') { e.preventDefault(); act('next', true); used('move'); }
    else if (k === 'j') { e.preventDefault(); const i = idx(b.c.id); if (i < ballot.length - 1) go(ballot[i + 1].c.id, true); used('move'); }
    else if (k === 'k') { e.preventDefault(); act('prev', true); used('move'); }
    else if (k === 'r') { e.preventDefault(); $('dk-w').focus(); used('reason'); }
"""),
# ---------------------------------------------------------------- U7: the tracker tag
('U7 tracker tag', B,
"""                 f'data-domains="{UMAMI_DOMAINS}" data-exclude-search="true" data-exclude-hash="true"></script>') if UMAMI_ID else \"\"""",
"""                 f'data-domains="{UMAMI_DOMAINS}" data-exclude-search="true" data-exclude-hash="true" '
                 # The privacy firewall in the page checks every payload; Do Not Track is honoured twice (here and there);
                 # page-speed measurements (load time, responsiveness) carry no personal data (Lane, Oct 15).
                 f'data-do-not-track="true" data-before-send="ballottaBeforeSend" data-performance="true"></script>') if UMAMI_ID else \"\"
    # Fail closed: until the page's own check is defined, the tracker's before-send drops everything.
    if analytics: analytics = '<script>window.ballottaBeforeSend = () => null;</script>' + analytics"""),
]

if __name__ == '__main__':
    files = {}
    for name, path, find, repl in EDITS:
        f = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
        n = f.count(find)
        if n != 1: sys.exit(f'{name}: FIND occurs {n} times in {path}')
        files[path] = f.replace(find, repl)
    for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
    print('applied', len(EDITS), 'edits to', ', '.join(files))
```

```
cd /home/claude/ballotta && python3 /tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/umami/edits_page.py && python3 source/build_site.py
node -e "const s=require('fs').readFileSync('index.html','utf8'); for (const m of s.matchAll(/<script>([\s\S]*?)<\/script>/g)) new Function(m[1]); console.log('scripts parse')"
python3 -c "import sys; sys.path.insert(0,'source'); import build_site as m; open('/tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/plain.html','w').write(m.build(desk=False))" && node -e "const s=require('fs').readFileSync('/tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/plain.html','utf8'); for (const m of s.matchAll(/<script>([\s\S]*?)<\/script>/g)) new Function(m[1]); console.log('phone-only build parses')"
```

Expected: `applied 27 edits to source/template-travis.html, source/build_site.py`, `index.html 336 KB`, `scripts parse` and `phone-only build parses`. The last check matters because `crib_printed`'s laptop options sit inside an inline `/*DESK*/` block, and rollback strips it.

## Task 3: the README

Save this as `/tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/umami/edits_readme.py` and run it from the repo root.

```python
"""Umami round, README edits.  Run from the repo root:  python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
R = 'README.md'
OLD_COUNTS = R_OLD = None

EDITS = [
 ('R1 what the browser stores', R,
  "3. Picks and reasons are saved only in your browser (`localStorage`), along with your ballot's contest list and a rounded location for sorting vote centers.",
  "3. Picks and reasons are saved only in your browser (`localStorage`), along with your ballot's contest list and a rounded location for sorting vote centers. Everything Ballotta keeps is under `ballotta.*` keys: `ballotta.ballot` (precinct, contest list, rounded location), `ballotta.picks`, `ballotta.whys`, `ballotta.name` (your share name), `ballotta.gen` (your place in a share chain), `ballotta.opened` and `ballotta.compared` (codes of friend links already counted), `ballotta.progress` (which progress milestones were counted, for the last 5 ballots), `ballotta.desk` (laptop view), and in `sessionStorage` a link being opened (`ballotta.incoming`) and which friend links already counted an own-ballot lookup (`ballotta.ownTracked`). **Clear everything on this device** (under the crib sheet; Feedback & Info on a laptop) removes them all."),
 ('R2 anonymous counts', R, None, None),   # filled in below: the whole paragraph is replaced
]

NEW_COUNTS = """### Anonymous counts

[Umami](https://umami.is) (cookieless) counts page views, page speed (load time and responsiveness) and the events below, each with only the details listed. Every event also carries `layout` (`phone` or `laptop`).

- Where people drop off: `lookup_started`; `lookup_failed` (reason: no street, bad ZIP, not found, no voters nearby, county server unreachable); `units_asked` (the "which unit is yours?" picker); `ballot_found` (match type); `address_changed` (a lookup that brings up a different ballot from the one already showing, whether from this visit or saved earlier); `link_damaged` (damaged or too old).
- How far people get: `progress` at 25, 50, 75 and 100% decided, once per ballot (the last 5 ballots on a device are remembered; Clear everything forgets them), with reasons written and races skipped as 0, 1–5 or 6+. A keep link opened on a new device counts the milestones it already reached, at once.
- What helps: `source_opened` (kind of link: League guide, campaign site, official, news, reference or other; and the race's level: federal, state, courts, county, city, school, special district or measure; never which race or candidate); `directions_opened` and `wait_times_opened` (early voting or Election Day).
- Laptop features: `view_opened` (decide, at a glance, where to vote, crib sheet); `shortcut_used` (pick, skip, move, reason or search; once per kind per visit); `search_used` and `filter_used` (once per visit); `faq_seen`; `help_opened` (which Feedback & Info item).
- Keeping and sharing: `keep_created` (how), `keep_restored`, `share_sheet_open`, `share_created` (section keys, reasons yes/no, picks 1–5/6–15/16+, how, generation, link code), `share_opened` (generation, already had picks, link code; once per browser per link), `share_own_ballot` (generation), `share_compare` (phone: each Compare tap; laptop: once per friend link when one of their races is first shown beside your ballot), `crib_printed` (two columns and hide-unopposed, yes or no), `cleared` (picks, or everything).

**The privacy firewall.** `source/template-travis.html` lists every event and the only values each detail may take (`EVENTS`). The page's `track()` and the tracker's before-send hook (`ballottaBeforeSend`) both drop anything not on that list, so a new feature or a bug can't send something unlisted. The hook also rebuilds every payload from a fixed set of text fields, with any `?query` or `#fragment` cut from addresses: only page views, events and page-speed reports pass, page views and speed reports carry no details, and no distinct id or `identify` data is ever sent. (Umami still groups one visit's requests into a session, as it does on any site.) A stand-in placed before the tracker tag drops everything until the page's check exists, so if the page's script failed, nothing would be sent. Never sent: addresses, precincts, districts, which race, candidate names, parties, picks, reasons or names. If the browser sends **Do Not Track** or **Global Privacy Control**, nothing is counted, not even page views. Tests run real journeys on both layouts, and the real tracker against a stand-in Umami server, and the test suite fails if anything off the list would be sent; another test fails if this README misses an event. The tracker is a pinned copy (`umami.js`, fetched 2026-10-14) so it can't change underneath the page; it reports to gateway.umami.is, and only on the hostnames in `UMAMI_DOMAINS`.
"""

if __name__ == '__main__':
    p = ROOT / R; s = p.read_text(encoding='utf-8')
    a, z = EDITS[0][2], EDITS[0][3]
    if s.count(a) != 1: sys.exit('R1: FIND occurs %d times' % s.count(a))
    s = s.replace(a, z)
    i = s.index('### Anonymous counts\n'); j = s.index('Contests marked **Double-check**', i)
    if s.count('### Anonymous counts\n') != 1: sys.exit('R2: heading not unique')
    s = s[:i] + NEW_COUNTS + '\n' + s[j:]
    p.write_text(s, encoding='utf-8'); print('applied 2 README edits')
```

Expected: `applied 2 README edits`.

## Task 4: GREEN, then the whole suite

Run the same six tests as in Task 1: expect six `PASS`. Then:

```
cd /home/claude/ballotta && timeout 598 python3 tests/test_site.py | tail -1
```

Expected: `47/47 passed (index.html)`. The phone-parity test is among them. It builds the page with and without the laptop code and compares pixels at phone width, and it still passes, because the shared changes (the new button, the privacy sentence) are in both builds.

## Task 5: mutation check

Save this as `/tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/umami/edits_mutants.py` and run it from the repo root. It:
- adds 61 mutants, V1 to V62 (V16 was retired in the first revision), one per protection;
- rewrites three older mutants whose anchors sit on lines this round changes (M36, M40, F13).

```python
"""Umami round, mutants appended to tests/mutate_desk.py.  Run from the repo root:  python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
FW, DROP, PROG, LAP = (['privacy_firewall_drops_anything_unlisted'], ['counts_where_people_drop_off'],
                       ['counts_progress_sources_and_clearing'], ['desk_counts_laptop_features'])
MUTANTS = [
 ('V1 unlisted events let through', 'PREV', "if (typeof name !== 'string' || !has(EVENTS, name)) { dropped.push(String(name)); return null; }", "if (typeof name !== 'string') return null;", FW),
 ('V2 unlisted details kept', 'PREV', "if (ok) out[k] = v; else dropped.push(name + '.' + k);", "out[k] = v;", FW),
 ('V3 values not checked', 'PREV', "has(spec, k) && spec[k](String(v))", "has(spec, k)", FW),
 ('V4 objects allowed as values', 'PREV', "(typeof v === 'string' || typeof v === 'number') && ", "", FW),
 ('V5 Global Privacy Control ignored', 'PREV', "navigator.globalPrivacyControl === true || ", "", FW),
 ('V6 Do Not Track ignored', 'PREV', "navigator.doNotTrack === '1' || ", "", FW),
 ('V7 before-send ignores the off switch', 'PREV', "  if (NO_COUNT || !p || typeof p !== 'object' || (type", "  if (!p || typeof p !== 'object' || (type", FW),
 ('V8 extra fields kept', 'PREV', "  TOP.forEach(k => { if (typeof p[k] === 'string') out[k] = k === 'url' || k === 'referrer' ? p[k].split(/[?#]/)[0] : p[k]; });", '  Object.assign(out, p);', FW + ['real_tracker_sends_only_listed_events']),
 ('V9 before-send skips the list', 'PREV', '  if (out.name !== undefined) { const d = clean(out.name, p.data); if (!d) return null; out.data = d; }', '  if (out.name !== undefined) out.data = p.data;', FW),
 ('V10 track ignores the off switch', 'PREV', "  if (NO_COUNT) return;\n  const d = clean(name", "  const d = clean(name", FW),
 ('V11 no layout on events', 'PREV', "{ layout: window.desk && matchMedia('(min-width: 1024px)').matches ? 'laptop' : 'phone' }", "{}", DROP),
 ('V12 tracker tag without the firewall', 'PREV', 'data-before-send="ballottaBeforeSend" ', '', FW + ['real_tracker_sends_only_listed_events']),
 ('V13 missing street not counted', 'PREV', "track('lookup_failed', { reason: 'no_street' }); ", "", DROP),
 ('V14 bad ZIP not counted', 'PREV', "track('lookup_failed', { reason: 'bad_zip' }); ", "", DROP),
 ('V15 lookup start not counted', 'PREV', "  track('lookup_started');\n", "", DROP),
 ('V17 not found not counted', 'PREV', " track('lookup_failed', { reason: 'not_found' });", "", DROP),
 ('V18 county outage not counted', 'PREV', "    track('lookup_failed', { reason: 'county_unreachable' });\n", "", DROP),
 ('V19 nobody nearby not counted', 'PREV', " track('lookup_failed', { reason: 'no_voters_nearby' });", "", DROP),
 ('V20 unit picker not counted', 'PREV', "  track('units_asked');\n", "", DROP),
 ('V21 damaged link not counted', 'PREV', "{ track('link_damaged', { kind: 'damaged' }); return damaged(); }", "return damaged();", DROP),
 ('V22 milestones counted every visit', 'PREV', "const rec = list.find(r => r.sig === sig), sent = rec ? rec.at : [];", "const rec = null, sent = [];", PROG),
 ('V23 milestone one race late', 'PREV', "done * 100 >= p * n && !sent.includes(p)", "done * 100 >= p * n + 100 && !sent.includes(p)", PROG),
 ('V24 skips miscounted', 'PREV', "const skipped = few(ids.filter(id => current(id)[0] === '__skip').length);", "const skipped = few(ids.filter(id => current(id)[0] === 'x').length);", PROG),
 ('V25 milestones never checked', 'PREV', "  milestones();\n}", "}", PROG),
 ('V26 campaign sites not told apart', 'PREV', "a.textContent.trim() === 'Campaign site' ? 'campaign_site' : ", "", PROG),
 ('V27 race level dropped', 'PREV', "track('source_opened', level ? { kind, level } : { kind });", "track('source_opened', { kind });", PROG),
 ('V28 laptop paper level unknown', 'PREV', "    P().dataset.c = ui.view === 'decide' ? curB().c.id : '';", "", LAP),
 ('V29 directions counted as a source', 'PREV', "  if (host === 'www.google.com' && a.pathname.startsWith('/maps/dir')) return track('directions_opened', { period });\n", "", PROG),
 ('V30 wrong voting period', 'PREV', "return track('directions_opened', { period });", "return track('directions_opened', { period: period === 'early' ? 'eday' : 'early' });", PROG),
 ('V31 wait times counted as a source', 'PREV', "  if (host === 'updates.electionlink.net') return track('wait_times_opened', { period });\n", "", PROG),
 ('V32 clearing picks not counted', 'PREV', "track('cleared', { what: 'picks' }); ", "", PROG),
 ('V33 clear everything keeps data', 'PREV', "Object.keys(s).filter(k => k.startsWith('ballotta.')).forEach(k => s.removeItem(k));", "Object.keys(s).filter(k => k.startsWith('nothing.')).forEach(k => s.removeItem(k));", PROG + LAP),
 ('V34 clear everything without asking', 'PREV', "  if (!confirm('Clear everything Ballotta saved in this browser: your ballot, picks, reasons, map location and share name?')) return;\n", "", PROG),
 ('V35 print options not counted', 'PREV', "two_col: ui.two ? 'yes' : 'no'", "two_col: 'no'", LAP),
 ('V36 menu items not counted', 'PREV', "    track('help_opened', { item: a });\n", "", LAP),
 ('V37 views not counted', 'PREV', " track('view_opened', { view: btn.dataset.view });", "", LAP),
 ('V38 busy keyboards counted every time', 'PREV', "const countOnce = (key, name, data) => { if (!once.has(key)) { once.add(key); track(name, data); } };", "const countOnce = (key, name, data) => track(name, data);", LAP),
 ('V39 FAQ never counted', 'PREV', "countOnce('faq', 'faq_seen');", "", LAP),
 ('V40 clear everything missing from the menu', 'PREV', "    else if (a === 'clearall') $('reset-all').click();\n", "", LAP),
 ('V41 README misses an event', 'README', "`faq_seen`; ", "", ['readme_lists_every_counted_event']),
 ('V42 other payload types pass', 'PREV', "(type !== 'event' && type !== 'performance')", "false", FW),
 ('V43 page views keep details', 'PREV', '  if (out.name !== undefined) { const d = clean(out.name, p.data); if (!d) return null; out.data = d; }', '  out.data = p.data;\n  if (out.name !== undefined) { const d = clean(out.name, p.data); if (!d) return null; out.data = d; }', FW + ['real_tracker_sends_only_listed_events']),
 ('V44 page-speed numbers dropped', 'PREV', "  if (type === 'performance') SPEED.forEach(k => { if (typeof p[k] === 'number') out[k] = p[k]; });\n", "", FW + ['real_tracker_sends_only_listed_events']),
 ('V45 link codes unchecked', 'PREV', "CODE = (v) => /^[a-z0-9]{1,8}$/.test(v)", "CODE = (v) => true", FW),
 ('V46 generations unchecked', 'PREV', "GEN = (v) => /^[1-9][0-9]?$/.test(v)", "GEN = (v) => true", FW),
 ('V47 share sections unchecked', 'PREV', "sections: (v) => v === '' || v.split(',').every(k => SECTION_KEYS.includes(k))", "sections: (v) => true", FW),
 ('V48 layout unchecked', 'PREV', "k === 'layout' ? LAYOUT(String(v))", "k === 'layout' ? true", FW),
 ('V49 laptops counted as phones', 'PREV', "window.desk && matchMedia('(min-width: 1024px)').matches ? 'laptop' : 'phone'", "'phone'", LAP + ['desk_compare_counted_once_per_link']),
 ('V50 rolled-back wide screens counted as laptops', 'TPL', '{ layout: window.desk && matchMedia', '{ layout: matchMedia', FW),
 ('V51 outage after the Census fallback hangs', 'PREV', "      return await nearby(pt, pt.label);", "      return nearby(pt, pt.label);", DROP),
 ('V52 same ballot counted as a new address', 'PREV', "  if (before && before !== after) track('address_changed');", "  if (before) track('address_changed');", DROP),
 ('V53 progress remembers one ballot only', 'PREV', ".concat(list.filter(r => r.sig !== sig)).slice(0, 5));", ".concat(list.filter(r => r.sig !== sig)).slice(0, 1));", PROG),
 ('V54 laptop level leaks into other views', 'PREV', "    P().dataset.c = ui.view === 'decide' ? curB().c.id : '';", "    if (ui.view === 'decide') P().dataset.c = curB().c.id;", LAP),
 ('V55 middle clicks not counted', 'PREV', "document.addEventListener('auxclick', outbound, true);", "", PROG),
 ('V56 too-old links not counted', 'PREV', "{ track('link_damaged', { kind: 'too_old' }); return say(", "{ return say(", DROP),
 ('V57 news counted as other', 'PREV', "votebeat\\.org)$/, 'news']", "votebeat\\.org)$/, 'other']", PROG),
 ('V58 FAQ promise missing', 'PREV', " If your browser sends Do Not Track or Global Privacy Control, we count nothing at all.</p></div>", "</p></div>", FW),
 ('V59 privacy note promise missing', 'PREV', 'pages load, never your address or your picks. If your browser sends Do Not Track or Global Privacy Control, we count nothing at all.</p>', 'pages load, never your address or your picks.</p>', FW),
 ('V60 non-text fields kept', 'PREV', "if (typeof p[k] === 'string') out[k] = k === 'url'", "if (p[k] !== undefined) out[k] = k === 'url'", FW),
 ('V61 query and fragment kept', 'PREV', '? p[k].split(/[?#]/)[0] : p[k]; });', '? p[k] : p[k]; });', FW),
 ('V62 firewall fails open', 'PREV', '<script>window.ballottaBeforeSend = () => null;</script>', '', FW),
]

# Three older mutants whose anchors sit on lines this round changes (the runner checks every anchor up front).
UPDATES = [
 ("""('M36 J drops focus', PREV, "go(ballot[i + 1].c.id, true); }", "go(ballot[i + 1].c.id); }",""",
  """('M36 J drops focus', PREV, "go(ballot[i + 1].c.id, true); used('move'); }", "go(ballot[i + 1].c.id); used('move'); }","""),
 ("""('M40 laptop compare looks like a phone tap', PREV, "track('share_compare', { layout: 'laptop' })", "track('share_compare', {})",""",
  """('M40 laptop compare counted twice', PREV, "track('share_compare');", "track('share_compare'); track('share_compare');","""),
]
# F13 swaps two lines that this round separates with a new one, so its whole definition is rewritten.
_G = "    if (t && t !== document.body && !t.closest('#dk-paper')) return;  // single-key shortcuts only on the ballot paper (WCAG 2.1.4, audit #30)"
_U = "    const used = (kind) => countOnce('k:' + kind, 'shortcut_used', { kind });"
_S = "    if (k === '/') { e.preventDefault(); $('dk-q').focus(); used('search'); return; }"
F13 = " ('F13 slash fires off the paper', PREV, " + repr(_G + '\n' + _U + '\n' + _S) + ', ' + repr(_U + '\n' + _S + '\n' + _G) + ", ['desk_launch_audit_fixes']),"

if __name__ == '__main__':
    p = ROOT / 'tests/mutate_desk.py'; s = p.read_text(encoding='utf-8')
    for old, new in UPDATES:
        if s.count(old) != 1: sys.exit('mutant update not found once: ' + old[:40])
        s = s.replace(old, new)
    k = s.index(" ('F13 slash fires off the paper'"); s = s[:k] + F13 + s[s.index('\n', k):]
    a = "PREV, TPL, BLD = ROOT / os.environ['BALLOTTA_PAGE'], ROOT / 'source/template-travis.html', ROOT / 'source/build_site.py'"
    if s.count(a) != 1: sys.exit('runner header changed')
    s = s.replace(a, a + "\nREADME = ROOT / 'README.md'")
    rows = ''.join(f" ({n!r}, {f}, {x!r}, {y!r}, {t!r}),\n" for n, f, x, y, t in MUTANTS)
    i = s.index('\n]\n'); s = s[:i] + '\n' + rows.rstrip('\n') + '\n]\n' + s[i + 3:]
    p.write_text(s, encoding='utf-8'); print('added', len(MUTANTS), 'mutants')
```

```
cd /home/claude/ballotta && python3 /tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/umami/edits_mutants.py
nohup python3 tests/mutate_desk.py 0 150 > /tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/umami/mut.log 2>&1 &
```

The runner checks all 150 anchors before starting the browser. A stale anchor stops it within a second, with the mutant's name. It takes about 60 minutes on this two-core machine; `tail -3 /tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/umami/mut.log` shows progress.

Expected last line: `150 of 150 mutants killed`. **Gate:** don't start Task 6 until that line is in the log and `ps -eo pid,args | grep "mutate_desk.py" | grep -v grep` prints nothing. A SURVIVED line means a test doesn't actually guard that protection: fix the test RED-first, never the mutant.

## Task 6: adversarial audit (remediation-audit)

1. **Pass 1:** dispatch one no-context agent with a tarball copy and the diff, with the instruction "break this". Require executed reproductions, and labels for PRE-EXISTING vs INTRODUCED. Attack surfaces to name in the prompt:
   - Can anything personal leave the browser through any path? Check page views, page-speed payloads, a crafted share link, an `href` with odd characters, and the referrer.
   - Is Do Not Track or Global Privacy Control honoured everywhere, including page views and page speed?
   - Do the counts lie: double counting, missed counts, milestone keys across ballots, the address-change definition?
   - Does "Clear everything" really clear everything, and could it clear anything that isn't Ballotta's?
   - Can the click listener break links, keyboard activation or middle clicks?
   - Phone parity, and that the stripped (rollback) build still works.
2. Argue the findings down. Fix the survivors RED-first, and file pre-existing ones as GitHub issues (`gh api repos/lanebecker/ballotta/issues`, milestone 2).
3. **Pass 2:** a narrow pass over only the rework, capped at about 20 tool calls. **Pass 3** only if Pass 2 needed non-trivial code.

## Task 7: commit, push, verify live

This plan is committed to `docs/plans/2026-10-15-umami-instrumentation.md` when it goes to Lane for approval, so the file already exists. Task 7 has two blocks with a manual step between them.

**7a. Start the execution log.**

```
cd /home/claude/ballotta && test -f docs/plans/2026-10-15-umami-instrumentation.md || { echo 'STOP: the plan file is missing'; exit 1; }
printf '\n## Execution log\n\n- %s: executed Tasks 0 to 6.\n' "$(date +%F)" >> docs/plans/2026-10-15-umami-instrumentation.md && tail -3 docs/plans/2026-10-15-umami-instrumentation.md
```

**Then, by hand:** add to that log line the actual results:
- the six RED failures;
- `47/47 passed (index.html)`;
- the mutation line, e.g. `150 of 150 mutants killed`;
- what each audit pass found and changed.

Don't run 7b until the log line holds real results.

**7b. Build, commit and push.**

```
cd /home/claude/ballotta && python3 source/build_site.py && git status --short
git add README.md index.html source/build_site.py source/template-travis.html tests/test_site.py tests/mutate_desk.py docs/plans/2026-10-15-umami-instrumentation.md
git diff --cached --stat
git -c user.name="Lane Becker" -c user.email="3211673+lanebecker@users.noreply.github.com" commit -q -F - <<'MSG'
Fine-grained, privacy-first Umami counting

Every event and detail the page may send is listed in EVENTS, and both
track() and the tracker's before-send hook drop anything else. Do Not
Track or Global Privacy Control turns counting off entirely. New
events cover where people drop off, how far they get, which kinds of
sources help, voting logistics and laptop features. Page-speed
measurements are on. Adds Clear everything on this device. README
lists every event and stored key.

Closes #29

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01ESRbqS3dGWHQThLF6J7gxN
MSG
git push -q origin main
```

After GitHub Pages deploys (poll up to 8 minutes):

```
curl -s "https://ballotta.org/?v=$RANDOM" | grep -c 'data-before-send="ballottaBeforeSend"'
```

Expected after the deploy: `1`. Before committing, `git diff --cached --stat` must list all seven files. After the deploy, compare `curl -s "https://ballotta.org/?v=$RANDOM" | sha256sum` with `sha256sum index.html`: they must be identical.

## Task 8: check the real pipeline

- **If an Umami connector is attached to the session:** open ballotta.org once in a headless browser without the test stub, look up 1000 Guadalupe St 78701, and make one pick. That's one real visit in Lane's numbers: tell him. Then confirm through the connector that `lookup_started`, `ballot_found` and a `layout: phone` detail arrived. Do Not Track and Global Privacy Control are proven by `real_tracker_sends_only_listed_events` against the real tracker; live aggregate counts can't prove an absence, so don't try.
- **Otherwise:** ask Lane to open ballotta.org, look up his address, and check Umami's Events tab within a few minutes. Every event in the README should show only the listed details. The `layout` detail should be on each one.

## Task 9: Umami reports (dashboard)

Umami's report types are Insights, Funnel, Retention, UTM, Goals and Journey. Create them under **Reports → Create report** (through the connector if there is one, otherwise as Lane's click guide):

1. **Funnel "From landing to a ballot"**
   - Window: 60 minutes.
   - Steps: URL `/` → event `lookup_started` → event `ballot_found` → event `progress` → event `crib_printed`.
   - Funnel steps match event names, not details, so the `progress` step means "reached 25%".
2. **Funnel "Sharing" (the sharer's side)**
   - Window: 1440 minutes.
   - Steps: event `share_sheet_open` → event `share_created`.
   - A friend's `share_opened` happens in *their* visit, so the chain across people is read in Insights instead: filter events by the detail `link` and compare `share_created` with `share_opened` for the same code.
3. **Funnel "A friend's link" (the recipient's side)**
   - Window: 1440 minutes.
   - Steps: event `share_opened` → event `share_own_ballot` → event `ballot_found` → event `share_created`.
4. **Goals:** `ballot_found`, `progress`, `crib_printed`, `keep_created`, `share_created`.
5. **Journey:** starting at `/`, 5 steps.
6. **Insights:** one view filtered by `layout = laptop` and one by `layout = phone`.
7. **Retention:** default settings.

Not yet checked against Umami Cloud (HYPOTHESIS until Task 9 is done): whether Insights can filter by an event detail such as `link`. If it can't, the Events page's Properties tab shows each detail's values.

Page-speed numbers appear in Umami's performance view, where the plan offers one.

## Self-review (write-plan)

- **Spec coverage.** Each item maps to tasks:
  - firewall: U1, U7; mutants V1 to V12, V42 to V50, V60 to V62;
  - drop-off events: U2a to U2i; V13 to V15, V17 to V20, V51 and V52;
  - damaged links: U5a and U5b; V21 and V56;
  - progress: U3; V22 to V25 and V53;
  - sources and logistics: U4 and U6b; V26 to V31, V54, V55 and V57;
  - laptop features: U6; V35 to V39;
  - clear everything (#29): U5c, U5d, U6e and U6f; V32 to V34 and V40;
  - page speed: U7; V44, plus the page-speed assertion in `real_tracker_sends_only_listed_events`;
  - privacy note and FAQ sentence: U5e and U5f; V59 and V58;
  - README: Task 3; V41;
  - dashboard: Task 9.
- **Left uncovered on purpose** (no mutant):
  - the `catch` path in `handleIncoming` (a link object that decodes, then throws);
  - `track()`'s `if (!d) return` (`clean()` returning null is covered by V1);
  - the order of `ballot_found` before `progress` (a funnel nicety, not a privacy protection).
  - the `auxclick` button check (a right click never opens a link).
- **Placeholder scan.** `grep -nE 'TBD|appropriate error handling|write tests for the above|similar to Task|149 of 150 in the full run on the second revision. The one survivor, M32 (an unguarded laptop hook), showed that sending `ballot_found` before the ballot is drawn had weakened an older test: the failure now surfaced as a false county-outage message, which that test didn't check. Test edit T4 now checks it, and M32 is then killed, so all 150 die. Suite: 47/47.'` on this file finds only this line.
- **Names.** Event names are identical across `EVENTS`, the tests, the mutants and the README; the README test enforces that. Element ids (`reset-all`, `dk-faq`, `dk-paper`), `ballotta.progress`, `ballottaBeforeSend` and `ballottaDropped` are consistent across Tasks 1 to 5.
- **Dry run.** The four scripts above were applied in this order to a fresh copy of `4c4510a`:
  - Task 1 (tests only): the six new tests failed as listed, and T4's older test still passed on the base.
  - Tasks 2 and 3: the six passed, and the suite passed 47/47.
  - Task 5: 149 of 150 in the full run on the second revision. The one survivor, M32 (an unguarded laptop hook), showed that sending `ballot_found` before the ballot is drawn had weakened an older test: the failure now surfaced as a false county-outage message, which that test didn't check. Test edit T4 now checks it, and M32 is then killed, so all 150 die. Suite: 47/47.

## Verification pass (Oct 15): what it caught

An independent agent checked this plan against Lane's request and the proposal, applied the scripts literally, recomputed every count and probed the privacy claims. Its findings, and what changed:

1. ~~The firewall only checked payloads with a `name`. A page view could carry `data`, an `identify` payload passed, and extra top-level fields passed.~~ Fixed: only `event` and `performance` pass, payloads are rebuilt from a fixed field list, and page views lose `data`. New assertions; mutants V42 to V44.
2. ~~Task 7's `git add` named a plan file no step creates, so the commit would fail and nothing would be pushed.~~ Fixed: Task 7 copies the plan into `docs/plans/` first and checks `git diff --cached --stat`.
3. ~~No gate between the mutation run (which rewrites files in place) and Tasks 6 and 7; port 8765 was busy.~~ Fixed: a gate in Task 5, and a port and process check in Task 0 and the rules.
4. ~~On a laptop, links in other views inherited the last Decide race's level.~~ Fixed: `render()` clears `data-c` outside Decide. Test plus V54.
5. ~~"The mutation result is recorded in the verification section below", but there was no such section.~~ Fixed: this section, plus the result line under Dry run.
6. ~~A county outage after the Census fallback was never counted, and the page hung (a pre-existing hang).~~ Fixed: both `nearby()` calls are awaited. Test plus V51.
7. ~~"Once per ballot per device" was overstated: A, then B, then A again resent A's milestones.~~ Fixed: the last 5 ballots are remembered (V53). The remaining effects are listed under "Known, accepted effects".
8. ~~`address_changed` counted the same address retyped, and the first lookup on a return visit.~~ Fixed: it counts only when the new ballot differs from the one showing (V52). The table states exactly that.
9. ~~Coverage gaps:~~
   - ~~the link-code, generation, section and layout checks;~~
   - ~~too-old links, middle clicks, and the official, news and reference kinds;~~
   - ~~laptop wait times;~~
   - ~~Do Not Track with the real tracker, and a real page-speed payload;~~
   - ~~a stub-test message that claimed page views were checked;~~
   - ~~the old laptop-label mutant M40 had been repurposed.~~

   Fixed: assertions plus V45 to V50 and V55 to V57. The real-tracker test now covers Do Not Track and a real page-speed report, and the laptop label is back as V49. What's left uncovered on purpose is in the self-review.
10. ~~After a rollback, wide screens were counted as `laptop`.~~ Fixed: `laptop` requires the laptop code (`window.desk`). Test plus V50.
11. ~~`one.py` defaulted to the old preview page.~~ Fixed: it defaults to `index.html`, and Task 1 sets it explicitly.
12. ~~The self-review's mapping was wrong (V21, V32, V40, page speed).~~ Fixed above.
13. ~~The dashboard missed the recipient's side of the sharing chain.~~ Fixed: funnel 3 in Task 9. The Insights filter is marked HYPOTHESIS.
14. ~~Small hazards: a `/tmp` path, a curl without a cache-buster, and a live check of Global Privacy Control that can't work.~~ Fixed in Tasks 2, 7 and 8.
15. ~~The new button overrode the 44px touch target; the README missed `ballotta.ownTracked`; the privacy note didn't mention page speed; the FAQ lacked the Do Not Track sentence.~~ Fixed (U5d, Task 3, U5e, U5f).

### Second verification pass (on the revision)

1. ~~V50 could never be killed: it mutated `index.html`, where the laptop code is always present, while the only test that can see it builds from the template.~~ Fixed: V50 targets the template (`TPL`); the verifier confirmed it is then killed.
2. ~~A date bomb: the phone test expected `period: early`, but from Oct 31 the page opens on Election Day, so the test would fail and V30 would survive.~~ Fixed: the test picks Early voting first, and V30 swaps to the opposite period.
3. ~~The privacy note read "never your address or your picks, and how quickly pages load", which says the opposite.~~ Fixed: "and how quickly pages load, never your address or your picks". V59 guards the note's Do Not Track sentence.
4. ~~The firewall kept objects and arrays in fixed top-level fields, and kept `?query` or `#fragment` in `url` and `referrer`.~~ Fixed: only text values pass, and addresses are cut at `?` or `#`. Test plus V60 and V61.
5. ~~Task 7 copied a plan file that no step creates.~~ Fixed: the plan is committed with the approval request, and Task 7 checks it exists and appends an execution log.
6. ~~The README said "never a distinct id or session data", but Umami's own session cache header is outside the hook's reach.~~ Fixed: the README says no distinct id or `identify` data, and that Umami still groups a visit into a session.
7. ~~The Dry run line was still a placeholder.~~ Fixed: it holds the result of the final mutation run, and the placeholder scan now includes `149 of 150 in the full run on the second revision. The one survivor, M32 (an unguarded laptop hook), showed that sending `ballot_found` before the ballot is drawn had weakened an older test: the failure now surfaced as a false county-outage message, which that test didn't check. Test edit T4 now checks it, and M32 is then killed, so all 150 die. Suite: 47/47.`.

### Third verification pass (on the second revision)

Converged on the code. It applied the four scripts literally and every count matched. It confirmed that the real tracker's page views (`screen` and `referrer` are strings) pass the stricter firewall, and that the fail-closed stand-in is placed and replaced correctly. It caught:
1. ~~Task 7's log-append snippet was a Python syntax error, and its `test -f` guard didn't stop anything.~~ Fixed: Task 7 is split into 7a (append with `printf`, and stop if the file is missing) and 7b (commit), with the results filled in by hand between them.
2. ~~Record item 7 claimed the placeholder was fixed while it wasn't.~~ Fixed: filled in.
3. ~~The accepted-effects bullet didn't mention that `ballot_found` is now counted before the ballot is drawn.~~ Fixed: the bullet says so, including the unit-picker path.
8. ~~The self-review mapped the privacy-note sentence to V58, which only covers the FAQ.~~ Fixed: V59 added and mapped.
9. HYPOTHESIS, accepted and listed under "Known, accepted effects": a page error while drawing a ballot now counts `ballot_found` and then `county_unreachable` (exact-match and Census paths), or `ballot_found` alone with no message (the unit picker, whose click handler is outside `lookup()`'s `try`).
10. ~~A new ballot sharing already-decided races sent `progress` before `ballot_found`.~~ Fixed: `ballot_found` and `address_changed` are sent before the ballot is shown.
11. ~~The firewall failed open if the page's script broke before defining the hook.~~ Fixed: a stand-in before the tracker tag drops everything until the real check exists. Test plus V62.

Checked and confirmed by the first verifier:
- the edit counts;
- the six RED failure messages, and 47/47 after the edits;
- 25 events, identical in the table and in `EVENTS`;
- the allowed values match the page's own sections, menu items, filters and views;
- the real tracker sends nothing under Do Not Track or Global Privacy Control;
- page-speed payloads hold only timing numbers;
- the phone-only (rollback) build parses and its tests pass;
- links outside a race carry no level on phones;
- page titles and URLs are static.
