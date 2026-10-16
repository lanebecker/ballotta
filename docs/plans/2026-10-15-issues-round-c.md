# Issues round C (Oct 15, 2026): #43–#49

**Goal.** Clear the follow-ups from rounds A and B (#43–#47) and two new robustness issues Lane asked for (#48, #49).

**Lane's decisions (Oct 15).**
- #48 backup nudge: a one-time card after the 5th pick ("Your picks live only in this browser, and phones can clear
  them. Send yourself a backup link." / Send myself a link / Not now), once more at 25 if no link was ever kept.
  After the first audit showed the card pushed the page (the laptop paper jumped ~90px mid-click): **it floats** (phone:
  bottom of the screen; laptop: bottom-right, since the notes column is below the paper at 1024–1279px and hidden in
  the wide views).
- #49 persistent storage: ask at the first pick (Firefox shows a one-time prompt then).

**What changed**

| Issue | Change | Test |
|---|---|---|
| #43 | Unicode's look-alike table (1,310 characters, ~5 KB, built by `make_lookalike_table.py`) after the hand-made map, plus lower-case forms and flag letters; € © ¢ fold; an "uneven" join from the name as typed (a single letter joins its neighbour unless that's a capitalised word of 3+ letters; small capitals, Cherokee small letters and Cyrillic т м н к в п count as capitals); voter(s)/city-of at the end of a word after 2+ letters; Unicode-aware word edges; б reads as b | `share_names_close_remaining_gaps` (and the earlier name tests) |
| #44 | Stored picks keep only text values; stored share generation must be a whole number; stored share name must be text | `stored_junk_in_share_fields` |
| #45 | Laptop announcements: an ordered queue worded when spoken (each contest's newest pick, then the last move); a pick waits 300 ms so a move at typing speed joins it; nothing is said twice | `desk_quick_pick_then_move_keeps_both_announcements` |
| #46 | Print… moves focus to the real Print button on touch/pen too, and always says "Crib sheet: print options, then the Print button." | `desk_print_by_touch_and_announced` |
| #47 | Phones: a new day re-draws the vote-center list only if the period changed (else just the dated note) | `phone_new_day_keeps_focus_on_a_directions_link` |
| #48 | The floating backup card; once per browser (remembered when shown); only when a pick is added; Clear my picks hides it; the page keeps room under it while it's up (screen only); focus returns where the visitor was; counted as `backup_nudge` (at 5/25; shown, keep, dismiss) | `backup_nudge_after_fifth_pick` |
| #49 | First pick of a visit: `navigator.storage.persisted()`, then `persist()` if not | `persistent_storage_asked_at_first_pick` |

**How to apply (from the repo root, after commit ef29f61).**

```
python3 <scripts>/edits_tests_C.py     # 7 tests (RED first: all seven failed on the old page)
python3 <scripts>/edits_page_C.py      # needs lookalike_table.js beside it (make_lookalike_table.py)
python3 <scripts>/edits_mutants_C.py
python3 <scripts>/rework_C1.py         # audit Pass 1 + Lane: the card floats
python3 <scripts>/rework_C2.py         # Pass 2
python3 <scripts>/rework_C3.py         # Pass 3 (+ Pass 4's test gap)
python3 source/build_site.py
python3 tests/test_site.py             # expected: 71/71 passed (index.html)
python3 tests/mutate_desk.py 231 276   # expected: 45 of 45 mutants killed
```

## Execution log

- RED: the 7 new tests failed on the old page for their issues' reasons. GREEN after the fixes, except "ϹOUNTY": the
  page's display normalization (NFKC) already turns the lunate sigma into Σ, so the name shows as "ΣOUNTY", no longer
  a look-alike; the test asserts that instead. A wide real-name screen (177 names in many scripts) then found "Борис"
  blocked: `\b` is ASCII-only, so the word check got Unicode-aware edges.
- **Pass 1** (independent agent): fixed: spaced acronyms next to a word ("G O P Texas") passed again; "S Tate" and
  "Бор" (б listed by Unicode as a look-alike of 6) were blocked; the card pushed the page (Lane: float it); Not now at
  25+ picks brought the 25 card straight back; Clear my picks left the card; focus fell to the page; an ignored card
  came back every visit and was counted every time; a skip or unpick could show it; a pick could be announced twice.
- **Pass 2**: fixed: the floating card could cover the footer's Clear everything and a focused Print button on short
  laptops (now the page keeps room under it); Not now on a phone threw focus to the top (now back to the pick just
  made); small capitals ("G Oᴘ") and two-letter words ("Go P Texas", "Dn C") got past the capitalised-word rule;
  "Бallotta" passed (б now reads b); announcements: joining only within 50 ms rarely helped at typing speed, and two
  quick moves dropped a pick.
- **Pass 3**: fixed: pick, move, pick at typing speed lost the first pick and said "No pick yet" after a pick (now an
  ordered queue worded when spoken); focus returned into a race closed since went nowhere (now falls back); Cherokee
  small letters and Cyrillic т м н к в п acting as small capitals; the reserved room applied when printing and
  ignored the iPhone home-bar inset.
- **Pass 4**: no product bugs. Its one test gap (D39 survived) was closed with an assertion. Logged, not changed (low):
  the focus fallback is tried once and ignores which button was used; on very narrow phones (≤ 320px) the fixed
  180px reserve can leave a little of the page end under a taller card; `env(safe-area-inset-bottom)` is 0 until the
  viewport meta has `viewport-fit=cover`.
- Accepted trade-offs (Lane to confirm): "Maria De M", "De M", "Go P" are blocked (a 2-letter word plus an initial is
  read as an acronym, so "Go P Texas" is caught); "Ngọc Dem", "Clerkenwell" stay blocked; "De ms"-style 2+2 splits and
  "Elec+ion" still pass.
- Mutants retired as equivalent: R3b (the uneven join covers spaced initials).
- **Final:** 71/71 tests; 45 of 45 round-C mutants killed.

## Script: make_lookalike_table.py

```python
"""Build lookalike_table.js from Unicode's confusables data (via the confusable_homoglyphs 3.3.1 wheel):
    pip download --no-deps confusable-homoglyphs==3.3.1   then extract confusable_homoglyphs/confusables.json
    python3 -I make_lookalike_table.py confusables.json lookalike_table.js
Every non-ASCII single character listed as a homoglyph of an ASCII letter or digit, grouped by that letter (lower case);
marks, controls and spaces left out (marks are stripped before the check anyway)."""
import json, sys, unicodedata, collections
d = json.load(open(sys.argv[1], encoding='utf-8'))
m = {}
for key, lst in d.items():
    if len(key) == 1 and key.isascii() and key.isalnum():
        for e in lst:
            c = e['c']
            if len(c) != 1 or c.isascii() or unicodedata.category(c).startswith(('M', 'C', 'Z')): continue
            m[c] = key.lower()
g = collections.defaultdict(str)
for c, k in sorted(m.items()): g[k] += c
open(sys.argv[2], 'w', encoding='utf-8').write('const LOOKALIKE_TABLE = {' + ', '.join(f'{k}: {json.dumps(v, ensure_ascii=False)}' for k, v in sorted(g.items())) + '};')
print(len(m), 'characters')
```

## Script: edits_tests_C.py

```python
"""Issues round C: tests for #43–#49 (written first; each must fail before the fixes). Run from the repo root:
    python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
TS = ROOT / 'tests/test_site.py'
s = TS.read_text(encoding='utf-8')
def sw(a, z):
    global s
    if s.count(a) != 1: sys.exit(f'test_site.py: FIND occurs {s.count(a)} times: {a[:70]!r}')
    s = s.replace(a, z)

# a touch-screen page for #46
sw("def new_page(browser, sent=None, wide=False, csp=False):", "def new_page(browser, sent=None, wide=False, csp=False, touch=False):")
sw("permissions=['clipboard-read', 'clipboard-write'], bypass_csp=not csp)", "permissions=['clipboard-read', 'clipboard-write'], bypass_csp=not csp, has_touch=touch)")
# #45: a pick and a move within a second are now announced together, so this test waits between them
sw("    pg.keyboard.press('1'); pg.keyboard.press('k'); said(f'Contest 1 of {n}: {t(0)}. No pick yet.')",
   "    pg.keyboard.press('1'); pg.wait_for_timeout(1200); pg.keyboard.press('k'); said(f'Contest 1 of {n}: {t(0)}. No pick yet.')   # apart: see #45")

NEW = r'''
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
                '🇬🇴🇵', '🇩🇳🇨', '€lection Office', 'Travis ©ounty', 'Travis ¢ounty', 'ᏞWV', 'Ꮩoter guide', 'ℒeague']:
        assert sn(bad) == '', bad
    assert sn('ϹOUNTY') == 'ΣOUNTY', 'display normalization turns a lunate sigma into Σ: no longer a look-alike'
    for good in ['Mary J Blige', 'J Smith', 'Νίκος', 'Ηλέκτρα', 'Γιώργος', 'Георгий', 'Борис', 'Ольга Петрова', 'Արամ', 'Անի', 'ᏣᎳᎩ',
                 'ანა', 'Ελένη', 'Đặng Thu', 'Nguyễn Văn An', 'محمد', 'דוד', 'Priya', 'Gustavo Terrazas', 'Clerkson', 'DeClerck', 'Le Clerc',
                 'José', 'Dempsey', 'Gopinath', 'Statham', 'Partridge', 'Ivo Terzić', 'A J', 'J R R Tolkien']:
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
        decide(4, 5); expect(card).to_be_visible(); expect(card.locator('[role="status"]')).to_have_text(msg)
        assert ['backup_nudge', {'at': '5', 'action': 'shown', 'layout': 'laptop' if wide else 'phone'}] in events(pg), events(pg)
        card.locator('[data-nudge="dismiss"]').click(); expect(card).to_be_hidden()
        decide(5, 24); expect(card).to_be_hidden()
        decide(24, 25); expect(card).to_be_visible()
        card.locator('[data-nudge="keep"]').click(); pg.wait_for_selector('#d-keep[open]'); expect(card).to_be_hidden()
        assert [e[1]['action'] for e in events(pg) if e[0] == 'backup_nudge'] == ['shown', 'dismiss', 'shown', 'keep'], events(pg)
        pg.keyboard.press('Escape'); pg.reload(); pg.wait_for_selector('body.dk-app-on' if wide else '#result:not(.hidden)')
        decide(25, 30); expect(backup_card(pg, wide)).to_be_hidden()                      # each card once per browser
        ctx.close()
    ctx, pg = new_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('#result:not(.hidden)')
    ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:2])
    pg.click('#a-keep'); pg.click('#keep-copy'); pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'keep_created')"); pg.click('#d-keep [data-close]')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[2:30]); expect(backup_card(pg, False)).to_be_hidden()   # already kept a link
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

def main():'''
sw('\ndef main():', NEW)
TS.write_text(s, encoding='utf-8')
print('tests C added')
```

## Script: edits_page_C.py

```python
"""Issues round C: fixes for #43 #44 #45 #46 #47 #48 #49. Run from the repo root after edits_tests_C.py:
    python3 <this file> && python3 source/build_site.py
Needs lookalike_table.js (generated from Unicode's confusables data) next to this script."""
import pathlib, sys
HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path.cwd()
T, RM = 'source/template-travis.html', 'README.md'
files = {}
def sw(path, a, z):
    s = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
    if s.count(a) != 1: sys.exit(f'{path}: FIND occurs {s.count(a)} times: {a[:80]!r}')
    files[path] = s.replace(a, z)
TABLE = (HERE / 'lookalike_table.js').read_text(encoding='utf-8').strip()
assert TABLE.startswith('const LOOKALIKE_TABLE = {') and TABLE.endswith('};') and '<' not in TABLE

# ======================= #43 share-name gaps =======================
sw(T, "  'ᴏ': 'o', 'ᴘ': 'p', 'ʀ': 'r', 'ꜱ': 's', 'ᴛ': 't', 'ᴜ': 'u', 'ᴠ': 'v', 'ᴡ': 'w', 'ʏ': 'y', 'ᴢ': 'z', 'ɡ': 'g', 'ɑ': 'a', 'ı': 'i' };\n",
      "  'ᴏ': 'o', 'ᴘ': 'p', 'ʀ': 'r', 'ꜱ': 's', 'ᴛ': 't', 'ᴜ': 'u', 'ᴠ': 'v', 'ᴡ': 'w', 'ʏ': 'y', 'ᴢ': 'z', 'ɡ': 'g', 'ɑ': 'a', 'ı': 'i' };\n"
      "// Unicode's look-alike table (confusables.txt, via confusable_homoglyphs 3.3.1): every character that imitates a Latin\n"
      "// letter or digit, grouped by the one it imitates (#43). It fills in after the hand-made entries above, then their\n"
      "// lower-case forms (Cherokee and Greek capitals lower-case to other code points); flag letters 🇦–🇿 read as a–z.\n"
      + TABLE + "\n"
      "for (const [k, chars] of Object.entries(LOOKALIKE_TABLE)) for (const ch of chars) if (!LOOKALIKE[ch]) LOOKALIKE[ch] = k;\n"
      "for (const [k, chars] of Object.entries(LOOKALIKE_TABLE)) for (const ch of chars) { const lc = ch.toLowerCase(); if (lc !== ch && !LOOKALIKE[lc] && !/[a-z0-9]/.test(lc)) LOOKALIKE[lc] = k; }\n"
      "for (let i = 0; i < 26; i++) LOOKALIKE[String.fromCodePoint(0x1F1E6 + i)] = String.fromCharCode(97 + i);\n")
sw(T, "const FOLD = { '1': 'l', 'i': 'l', '|': 'l', '!': 'l', '0': 'o', '3': 'e', '4': 'a', '@': 'a', '5': 's', '$': 's', '6': 'g', '7': 't', '8': 'b', '9': 'g' };\n"
      "const fold = (t) => t.replace(/[1i|!0345@$6789]/g, ch => FOLD[ch]);\n",
      "const FOLD = { '1': 'l', 'i': 'l', '|': 'l', '!': 'l', '0': 'o', '3': 'e', '4': 'a', '@': 'a', '5': 's', '$': 's', '6': 'g', '7': 't', '8': 'b', '9': 'g',\n"
      "  '€': 'e', '©': 'c', '¢': 'c' };  // symbols Unicode's table doesn't list as letters (#43)\n"
      "const fold = (t) => t.replace(/[1i|!0345@$6789€©¢]/g, ch => FOLD[ch]);\n")
sw(T, "// voter, clerk and city-of also count at the start or end of one word with 4+ more letters (\"voterguide\", \"travisclerk\"),\n"
      "// never across a space, so \"Clerkson\" and \"Gustavo Terrazas\" are fine (Pass 4).\n"
      "const RESERVED_GLUED = new RegExp('(^|\\\\s)(' + ['voters?', 'clerks?', 'cityof'].map(fold).join('|') + ')\\\\S{4,}|\\\\S{4,}(' + ['voters?', 'clerks?', 'cityof'].map(fold).join('|') + ')(\\\\s|$)');\n",
      "// voter, clerk and city-of also count at the start or end of one word with 4+ more letters (\"voterguide\", \"travisclerk\"),\n"
      "// never across a space, so \"Clerkson\" and \"Gustavo Terrazas\" are fine (Pass 4); voter(s) and city-of also at the end\n"
      "// after just 2 (\"TXVOTERS\"): no real name ends that way (#43).\n"
      "const RESERVED_GLUED = new RegExp('(^|\\\\s)(' + ['voters?', 'clerks?', 'cityof'].map(fold).join('|') + ')\\\\S{4,}|\\\\S{4,}(' + ['voters?', 'clerks?', 'cityof'].map(fold).join('|') + ')(\\\\s|$)'\n"
      "  + '|\\\\S{2,}(' + ['voters?', 'cityof'].map(fold).join('|') + ')(\\\\s|$)');\n")
sw(T, "    return [t.replace(/[\\p{P}\\p{S}]/gu, ''), w, w.replace(/(?<=(^|\\s)\\S)\\s(?=\\S(\\s|$))/gu, '')];\n",
      "    // a space next to a single letter is dropped: \"G O P\", \"G OP\", \"V oter\" (#43)\n"
      "    return [t.replace(/[\\p{P}\\p{S}]/gu, ''), w, w.replace(/(?<=(^|\\s)\\S)\\s|\\s(?=\\S(\\s|$))/gu, '')];\n")

# Words are matched with Unicode-aware edges: \b is ASCII-only, so "Борис" folded to "gop" + a Cyrillic letter matched (#43)
sw(T, "const RESERVED_WORDS = new RegExp('\\\\b(' + ['state',", "const RESERVED_WORDS = new RegExp('(?<![\\\\p{L}\\\\p{N}])(' + ['state',")
sw(T, "  'tax ?office'].map(fold).join('|') + ')\\\\b');", "  'tax ?office'].map(fold).join('|') + ')(?![\\\\p{L}\\\\p{N}])', 'u');")

# ======================= #44 stored share fields and pick values =======================
sw(T, "let picks = plain(LS.get('ballotta.picks', {})), whys =",
      "const cleanPicks = (o) => Object.fromEntries(Object.entries(plain(o)).map(([k, v]) => [k, (Array.isArray(v) ? v : [v]).filter(x => typeof x === 'string')]).filter(([, v]) => v.length));  // option names only (#44)\n"
      "let picks = cleanPicks(LS.get('ballotta.picks', {})), whys =")
sw(T, "gen = Math.max(1, Math.min(99, LS.get('ballotta.gen', 1) || 1)), code = rand8();",
      "g0 = LS.get('ballotta.gen', 1), gen = Number.isInteger(g0) ? Math.max(1, Math.min(99, g0)) : 1, code = rand8();  // a whole number or 1 (#44)")
sw(T, "  $('sharename').value = LS.get('ballotta.name', '') || '';",
      "  const nm = LS.get('ballotta.name', ''); $('sharename').value = typeof nm === 'string' ? nm.slice(0, 30) : '';  // text only (#44)")

# ======================= #45 one region, one timer =======================
sw(T, """  function announce(c) {  // what a key just did, for screen readers (audit #30)
    const v = current(c.id), l = $('dk-live');
    l.textContent = '';
    setTimeout(() => { l.textContent = cleanTitle(c) + ': ' + (!v.length ? 'no pick' : v[0] === '__skip' ? 'skipped' : 'picked ' + v.map(x => optLabel(c, x)).join(', ')); }, 50);
  }
  function where(b) {  // a move to another contest, for screen readers: the paper's own label never changes (#39)
    const v = current(b.c.id), l = $('dk-live');
    l.textContent = '';
    setTimeout(() => { l.textContent = 'Contest ' + (idx(b.c.id) + 1) + ' of ' + ballot.length + ': ' + cleanTitle(b.c) + '. ' + (!v.length ? 'No pick yet.' : v[0] === '__skip' ? 'Skipped.' : 'Picked ' + v.map(x => optLabel(b.c, x)).join(', ') + '.'); }, 50);
  }""", """  // One polite region and one timer for what the keys did (#45). A move within a second of a pick keeps the pick's words
  // ahead of its own, so the pick isn't cut off; moves alone, or picks alone, simply replace each other.
  let liveT = 0, livePick = null;
  function say(text, isPick) {
    const l = $('dk-live'), keep = !isPick && livePick && Date.now() - livePick.at < 1000 ? livePick.text + '. ' : '';
    livePick = isPick ? { text, at: Date.now() } : null;
    clearTimeout(liveT); l.textContent = '';
    liveT = setTimeout(() => { l.textContent = keep + text; }, 50);
  }
  function announce(c) {  // what a key just did, for screen readers (audit #30)
    const v = current(c.id);
    say(cleanTitle(c) + ': ' + (!v.length ? 'no pick' : v[0] === '__skip' ? 'skipped' : 'picked ' + v.map(x => optLabel(c, x)).join(', ')), true);
  }
  function where(b) {  // a move to another contest, for screen readers: the paper's own label never changes (#39)
    const v = current(b.c.id);
    say('Contest ' + (idx(b.c.id) + 1) + ' of ' + ballot.length + ': ' + cleanTitle(b.c) + '. ' + (!v.length ? 'No pick yet.' : v[0] === '__skip' ? 'Skipped.' : 'Picked ' + v.map(x => optLabel(b.c, x)).join(', ') + '.'), false);
  }""")

# ======================= #46 Print… by touch, and said aloud =======================
sw(T, """    // A keyboard press lands on the real Print button, scrolled on screen (below the paper at 1024–1279px); a mouse click
    // leaves focus on Print… (a later Space or Enter just moves it to the real button). A held key's repeats are ignored
    // there, so holding Enter on Print… never prints (Pass 2, 3, 4).
    if (pr && e.detail === 0) { pr.focus({ preventScroll: true }); pr.scrollIntoView({ block: 'nearest' }); }""",
"""    // A keyboard press or a touch (a screen reader's double-tap on a tablet is a touch) lands on the real Print button,
    // scrolled on screen (below the paper at 1024–1279px); a mouse click leaves focus on Print… (a later Space or Enter
    // just moves it to the real button). A held key's repeats are ignored there, so holding Enter on Print… never prints
    // (Pass 2, 3, 4). Every activation says where it went (#46).
    say('Crib sheet: print options, then the Print button.', false);
    if (pr && (e.detail === 0 || e.pointerType === 'touch' || e.pointerType === 'pen')) { pr.focus({ preventScroll: true }); pr.scrollIntoView({ block: 'nearest' }); }""")

# ======================= #47 a new day keeps a phone's vote-center list =======================
sw(T, "  const started = today() >= new Date(2026, 9, 19);\n", "")
sw(T, "  $('waitsnote').textContent = 'Travis County map' + (started ? '' : ' · fills in once voting starts Oct 19');\n}\n",
      "  waitsNote();\n}\n"
      "function waitsNote() { $('waitsnote').textContent = 'Travis County map' + (today() >= new Date(2026, 9, 19) ? '' : ' · fills in once voting starts Oct 19'); }\n")
sw(T, "  renderVote();/*DESK*/ if (window.desk) try { desk.today(period !== was); } catch (e) {}/*/DESK*/  // only what shows the date: a full redraw would take focus from a reason being typed (Pass 1)\n",
      "  if (period !== was) renderVote(); else waitsNote();  // a new list only when the period changed, so a focused link keeps its place (#47)\n"
      "  /*DESK*/if (window.desk) try { desk.today(period !== was); } catch (e) {}/*/DESK*/  // only what shows the date: a full redraw would take focus from a reason being typed (Pass 1)\n")

# ======================= #48 backup nudge, #49 persistent storage =======================
sw(T, "  keep_restored: {},\n", "  keep_restored: {},\n  backup_nudge: { at: ONE_OF('5', '25'), action: ONE_OF('shown', 'keep', 'dismiss') },\n")
sw(T, '      <div class="meter" role="img" id="meterlabel" aria-label="Progress"><div id="meter"></div></div>\n',
      '      <div class="meter" role="img" id="meterlabel" aria-label="Progress"><div id="meter"></div></div>\n'
      '      <div class="nudge hidden" id="nudge" data-nudge-box><p role="status"></p><div class="row"><button class="btn small" type="button" data-nudge="keep">Send myself a link</button><button class="btn text small" type="button" data-nudge="dismiss">Not now</button></div></div>\n')
sw(T, '    <div class="dk-say hidden" id="dk-say" role="status"><span></span><button type="button" class="dk-link" aria-label="Dismiss this message">Dismiss</button></div>\n',
      '    <div class="dk-say hidden" id="dk-say" role="status"><span></span><button type="button" class="dk-link" aria-label="Dismiss this message">Dismiss</button></div>\n'
      '    <div class="dk-nudge hidden" id="dk-nudge" data-nudge-box><span role="status"></span><span class="row"><button class="btn small" type="button" data-nudge="keep">Send myself a link</button><button class="dk-link" type="button" data-nudge="dismiss">Not now</button></span></div>\n')
sw(T, ".limit:not(:empty){display:block;margin-top:4px;font-weight:600;color:var(--plum)}  /* \"You can pick up to 2…\" (#33) */",
      ".limit:not(:empty){display:block;margin-top:4px;font-weight:600;color:var(--plum)}  /* \"You can pick up to 2…\" (#33) */\n"
      ".nudge{display:flex;flex-direction:column;gap:10px;padding:14px 16px;border-radius:12px;background:var(--lilac);color:var(--ink)}  /* backup nudge (#48) */\n"
      ".nudge p{margin:0;font-size:15px;font-weight:600}.nudge .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}")
sw(T, "  .dk-say{grid-column:1/-1;display:flex;",
      "  .dk-nudge{grid-column:1/-1;display:flex;gap:16px;align-items:center;justify-content:space-between;padding:12px 16px;border-radius:10px;background:#fff;color:var(--plum);font-size:14px;font-weight:600;box-shadow:0 8px 24px rgba(36,26,46,.12)}  /* #48 */\n"
      "  .dk-nudge .row{display:flex;gap:12px;align-items:center;flex-shrink:0}\n"
      "  .dk-say{grid-column:1/-1;display:flex;")
sw(T, "  $('s' + cid).innerHTML = summaryHTML(cid);\n  refresh();\n  return true;\n}\n",
      "  $('s' + cid).innerHTML = summaryHTML(cid);\n  refresh();\n  nudgeCheck(); askPersist();\n  return true;\n}\n")
sw(T, "  if (via) track('keep_created', { via });\n});\n", "  if (via) { track('keep_created', { via }); nudgeKept(); }\n});\n")
sw(T, "if (via) track('keep_created', { via }); });", "if (via) { track('keep_created', { via }); nudgeKept(); } });")
sw(T, "  track('keep_restored', {});\n", "  track('keep_restored', {}); nudgeKept();\n")
sw(T, "/* ---------- restore a keep link ---------- */\n", """/* ---------- backup nudge (#48) and persistent storage (#49) ---------- */
// After the 5th pick, and once more at 25 if no link was ever kept, a card suggests a backup link: picks live only in
// this browser, and phones can clear them. "Send myself a link" opens Keep my picks; either button puts the card away for
// good. Remembered in ballotta.nudge (d5, d25: seen; kept: a link was made or loaded).
const NUDGE_MSG = 'Your picks live only in this browser, and phones can clear them. Send yourself a backup link.';
let nudgeAt = 0;  // the card showing: 5, 25, or 0 for none
const nudgeState = () => plain(LS.get('ballotta.nudge', {}));
const nudgeBoxes = (show) => document.querySelectorAll('[data-nudge-box]').forEach(box => box.classList.toggle('hidden', !show));
function nudgeCheck() {
  const st = nudgeState(); if (st.kept || nudgeAt) return;
  const n = countPicks(ballot.map(b => b.c.id)), at = n >= 25 && !st.d25 ? 25 : n >= 5 && !st.d5 ? 5 : 0;
  if (!at) return;
  nudgeAt = at; nudgeBoxes(true);
  document.querySelectorAll('[data-nudge-box] [role="status"]').forEach(t => { t.textContent = ''; setTimeout(() => { t.textContent = NUDGE_MSG; }, 50); });
  track('backup_nudge', { at: String(at), action: 'shown' });
}
function nudgeDone(action) {
  if (!nudgeAt) return;
  const st = nudgeState(); st['d' + nudgeAt] = 1; if (nudgeAt === 25) st.d5 = 1;
  LS.set('ballotta.nudge', st); track('backup_nudge', { at: String(nudgeAt), action });
  nudgeAt = 0; nudgeBoxes(false);
  if (action === 'keep') openKeep();
}
function nudgeKept() { const st = nudgeState(); if (!st.kept) { st.kept = 1; LS.set('ballotta.nudge', st); } nudgeAt = 0; nudgeBoxes(false); }
document.querySelectorAll('[data-nudge]').forEach(b => b.addEventListener('click', () => nudgeDone(b.dataset.nudge)));
// At the first pick of a visit, ask the browser to keep Ballotta's data under storage pressure (#49): a hint, not a
// promise. Chrome and Safari decide silently; Firefox asks the visitor once. Skipped if it's already kept.
let persistAsked = false;
function askPersist() {
  if (persistAsked) return;
  persistAsked = true;
  try { const s = navigator.storage; if (s && s.persist && s.persisted) s.persisted().then(p => p || s.persist()).catch(() => {}); } catch (e) {}
}

/* ---------- restore a keep link ---------- */
""")

# README
sw(RM, "- Keeping and sharing: `keep_created` (how), `keep_restored`, ",
       "- Keeping and sharing: `keep_created` (how), `keep_restored`, `backup_nudge` (the backup-link card at 5 or 25 picks: shown, keep or dismiss), ")
sw(RM, "`ballotta.desk` (laptop view), ", "`ballotta.desk` (laptop view), `ballotta.nudge` (which backup-link cards were seen, and whether a link was kept), ")

for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
print('fixes C applied to', ', '.join(files))
```

## Script: edits_mutants_C.py

```python
"""Issues round C: mutants for #43–#49, and anchors this round moved. Run from the repo root after edits_page_C.py:
    python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
MD = ROOT / 'tests/mutate_desk.py'
m = MD.read_text(encoding='utf-8')
for pre in ("('A2 ", "('R3b ", "('R10 ", "('R13 ", "('R19 ", "('A4 "):
    hits = [l for l in m.split('\n') if l.startswith(' ' + pre)]
    assert len(hits) == 1, pre
    m = m.replace(hits[0] + '\n', '')
N = 'share_names_close_remaining_gaps'
NEW = [
 ('R19 9 not read as g', 'PREV', ", '8': 'b', '9': 'g',\n", ", '8': 'b',\n", [N]),
 ('A4 stand-ins not folded', 'PREV', "const fold = (t) => t.replace(/[1i|!0345@$6789€©¢]/g, ch => FOLD[ch]);", "const fold = (t) => t;", ['share_names_block_lookalikes_and_nicknames']),
 ('A2 stored picks not checked', 'PREV', r"let picks = cleanPicks(LS.get('ballotta.picks', {}))", r"let picks = LS.get('ballotta.picks', {})", ['stored_junk_never_breaks_keep_or_share']),
 ('R3b spaced-out initials not joined', 'PREV', r", w.replace(/(?<=(^|\s)\S)\s|\s(?=\S(\s|$))/gu, '')]", ']', ['share_names_block_lookalikes_and_nicknames']),
 ('R10 Print… leaves keyboard focus behind', 'PREV', "    if (pr && (e.detail === 0 || e.pointerType === 'touch' || e.pointerType === 'pen')) { pr.focus({ preventScroll: true }); pr.scrollIntoView({ block: 'nearest' }); }\n", '', ['desk_print_button_opens_the_crib_sheet']),
 ('R13 Print… moves focus on a mouse click', 'PREV', "if (pr && (e.detail === 0 || e.pointerType === 'touch' || e.pointerType === 'pen')) {", 'if (pr) {', ['desk_print_button_opens_the_crib_sheet']),
 ('D1 Unicode table not applied', 'PREV', "for (const [k, chars] of Object.entries(LOOKALIKE_TABLE)) for (const ch of chars) if (!LOOKALIKE[ch]) LOOKALIKE[ch] = k;\n", '', [N]),
 ('D2 lower-case look-alikes missed', 'PREV', "for (const [k, chars] of Object.entries(LOOKALIKE_TABLE)) for (const ch of chars) { const lc = ch.toLowerCase();", "for (const [k, chars] of Object.entries({})) for (const ch of chars) { const lc = ch.toLowerCase();", [N]),
 ('D3 flag letters not read', 'PREV', "for (let i = 0; i < 26; i++) LOOKALIKE[String.fromCodePoint(0x1F1E6 + i)] = String.fromCharCode(97 + i);\n", '', [N]),
 ('D4 symbol stand-ins not folded', 'PREV', "  '€': 'e', '©': 'c', '¢': 'c' };", "  '€': '€', '©': '©', '¢': '¢' };", [N]),
 ('D5 short glued handles pass', 'PREV', r"+ '|\\S{2,}(' + ['voters?', 'cityof']", r"+ '|\\S{9,}(' + ['voters?', 'cityof']", [N]),
 ('D6 uneven splits pass', 'PREV', r"w.replace(/(?<=(^|\s)\S)\s|\s(?=\S(\s|$))/gu, '')", r"w.replace(/(?<=(^|\s)\S)\s(?=\S(\s|$))/gu, '')", [N]),
 ('D7 non-text picks counted', 'PREV', ".filter(x => typeof x === 'string')]).filter(([, v]) => v.length));", ".filter(x => x != null)]).filter(([, v]) => v.length));", ['stored_junk_in_share_fields']),
 ('D8 odd generation sent', 'PREV', 'gen = Number.isInteger(g0) ? Math.max(1, Math.min(99, g0)) : 1,', 'gen = Math.max(1, Math.min(99, g0 || 1)),', ['stored_junk_in_share_fields']),
 ('D9 odd share name shown', 'PREV', "$('sharename').value = typeof nm === 'string' ? nm.slice(0, 30) : '';", "$('sharename').value = nm || '';", ['stored_junk_in_share_fields']),
 ('D10 a quick move cuts off the pick', 'PREV', "keep = !isPick && livePick && Date.now() - livePick.at < 1000 ? livePick.text + '. ' : '';", "keep = '';", ['desk_quick_pick_then_move_keeps_both_announcements']),
 ('D11 moves pile up', 'PREV', 'livePick = isPick ? { text, at: Date.now() } : null;', 'livePick = { text, at: Date.now() };', ['desk_quick_pick_then_move_keeps_both_announcements']),
 ('D12 a touch leaves focus on Print…', 'PREV', " || e.pointerType === 'touch' || e.pointerType === 'pen'", '', ['desk_print_by_touch_and_announced']),
 ('D13 Print… says nothing', 'PREV', "    say('Crib sheet: print options, then the Print button.', false);\n", '', ['desk_print_by_touch_and_announced']),
 ('D14 a new day rebuilds the phone list', 'PREV', '  if (period !== was) renderVote(); else waitsNote();', '  renderVote();', ['phone_new_day_keeps_focus_on_a_directions_link']),
 ('D15 a new day forgets the dated note', 'PREV', 'renderVote(); else waitsNote();', 'renderVote();', ['phone_new_day_keeps_focus_on_a_directions_link']),
 ('D16 backup card never shown', 'PREV', '  nudgeCheck(); askPersist();\n', '  askPersist();\n', ['backup_nudge_after_fifth_pick']),
 ('D17 no second card at 25', 'PREV', 'n >= 25 && !st.d25 ? 25 : ', '', ['backup_nudge_after_fifth_pick']),
 ('D18 card back after Not now', 'PREV', "st['d' + nudgeAt] = 1; ", '', ['backup_nudge_after_fifth_pick']),
 ('D19 a kept link ignored', 'PREV', "if (via) { track('keep_created', { via }); nudgeKept(); } });", "if (via) { track('keep_created', { via }); } });", ['backup_nudge_after_fifth_pick']),
 ('D20 card not counted', 'PREV', "  track('backup_nudge', { at: String(at), action: 'shown' });\n", '', ['backup_nudge_after_fifth_pick']),
 ('D21 Send myself a link opens nothing', 'PREV', "  if (action === 'keep') openKeep();\n", '', ['backup_nudge_after_fifth_pick']),
 ('D22 browser never asked to keep data', 'PREV', 's.persisted().then(p => p || s.persist())', 's.persisted()', ['persistent_storage_asked_at_first_pick']),
 ('D23 asked at every pick', 'PREV', '  if (persistAsked) return;\n', '', ['persistent_storage_asked_at_first_pick']),
 ('D24 asked even when already kept', 'PREV', 'p => p || s.persist()', 'p => s.persist()', ['persistent_storage_asked_at_first_pick']),
]
k = m.index('\n]\n')
m = m[:k] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in NEW).rstrip('\n') + '\n]\n' + m[k + 3:]
MD.write_text(m, encoding='utf-8')
print('mutants C added:', len(NEW) - 6, '(and 6 re-anchored)')
```

## Script: rework_C1.py

```python
"""Issues round C: rework after remediation-audit Pass 1 (and Lane: the backup card floats, it never pushes the page).
Run from the repo root after edits_mutants_C.py:  python3 <this file> && python3 source/build_site.py"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
T, TS, MD = 'source/template-travis.html', 'tests/test_site.py', 'tests/mutate_desk.py'
files = {}
def sw(path, a, z):
    s = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
    if s.count(a) != 1: sys.exit(f'{path}: FIND occurs {s.count(a)} times: {a[:80]!r}')
    files[path] = s.replace(a, z)

# ---- P1-1/4 names: the old single-letter join, plus a case-aware uneven join from the name as typed; no Cyrillic б
sw(T, "for (let i = 0; i < 26; i++) LOOKALIKE[String.fromCodePoint(0x1F1E6 + i)] = String.fromCharCode(97 + i);\n",
      "for (let i = 0; i < 26; i++) LOOKALIKE[String.fromCodePoint(0x1F1E6 + i)] = String.fromCharCode(97 + i);\n"
      "delete LOOKALIKE['б']; delete LOOKALIKE['Б'];  // Unicode lists б as a look-alike of 6 (read as g): \"Бор\" isn't \"gop\" (Pass 1)\n")
sw(T, "    // a space next to a single letter is dropped: \"G O P\", \"G OP\", \"V oter\" (#43)\n"
      "    return [t.replace(/[\\p{P}\\p{S}]/gu, ''), w, w.replace(/(?<=(^|\\s)\\S)\\s|\\s(?=\\S(\\s|$))/gu, '')];\n",
      "    return [t.replace(/[\\p{P}\\p{S}]/gu, ''), w, w.replace(/(?<=(^|\\s)\\S)\\s(?=\\S(\\s|$))/gu, '')];\n")
sw(T, "  const forms = [fold(low), fold(low.replace(/[|!$@]/g, '')), fold(split)];\n",
      "  // Uneven splits (\"G OP\", \"V oter\"): from the name as typed, a single letter joins its neighbour, except a\n"
      "  // capitalised word (\"S Tate\" stays a person) (#43, Pass 1).\n"
      "  const uneven = n.replace(/[\\p{P}\\p{S}]/gu, ' ').replace(/\\s+/g, ' ').trim().replace(/(?<=(^|\\s)\\S)\\s(?!\\p{Lu}\\p{Ll})|(?<!(^|\\s)\\p{Lu}\\p{Ll}+)\\s(?=\\S(\\s|$))/gu, '');\n"
      "  const forms = [fold(low), fold(low.replace(/[|!$@]/g, '')), fold(split), fold(latin(uneven))];\n")

# ---- P1-2 (Lane): the card floats over the page, so nothing moves under a finger or pointer
sw(T, ".nudge{display:flex;flex-direction:column;gap:10px;padding:14px 16px;border-radius:12px;background:var(--lilac);color:var(--ink)}  /* backup nudge (#48) */",
      ".nudge{position:fixed;left:12px;right:12px;bottom:calc(12px + env(safe-area-inset-bottom));z-index:40;max-width:496px;margin:0 auto;display:flex;flex-direction:column;gap:10px;padding:14px 16px;border-radius:12px;background:var(--lilac);color:var(--ink);box-shadow:0 12px 32px rgba(36,26,46,.28)}  /* backup nudge (#48): floats, never pushes the page (Lane) */")
sw(T, "  .dk-nudge{grid-column:1/-1;display:flex;gap:16px;align-items:center;justify-content:space-between;padding:12px 16px;border-radius:10px;background:#fff;color:var(--plum);font-size:14px;font-weight:600;box-shadow:0 8px 24px rgba(36,26,46,.12)}  /* #48 */\n"
      "  .dk-nudge .row{display:flex;gap:12px;align-items:center;flex-shrink:0}\n",
      "  .dk-nudge{position:fixed;right:24px;bottom:24px;z-index:40;width:380px;display:flex;flex-direction:column;align-items:flex-start;gap:12px;padding:16px 18px;border-radius:10px;background:#fff;color:var(--plum);font-size:14px;font-weight:600;box-shadow:0 12px 32px rgba(36,26,46,.22)}  /* #48: floats, never pushes the paper (Lane) */\n"
      "  .dk-nudge .row{display:flex;gap:12px;align-items:center}\n")

# ---- P1-3/5/6/7: shown once per browser (remembered when shown), only when a pick is added, gone after Clear my
# picks, and focus lands somewhere sensible
sw(T, "  nudgeCheck(); askPersist();\n  return true;\n}\n",
      "  if (val !== '__skip' && current(cid).includes(val)) nudgeCheck();  // only when a pick was added, not a skip or an unpick (Pass 1)\n"
      "  askPersist();\n  return true;\n}\n")
sw(T, "// good. Remembered in ballotta.nudge (d5, d25: seen; kept: a link was made or loaded).\n",
      "// good. Remembered in ballotta.nudge when shown (d5, d25), so each card shows once per browser; kept: a link was made\n"
      "// or loaded. Putting a card away at 25+ picks also retires the 25 card (Pass 1).\n")
sw(T, "  nudgeAt = at; nudgeBoxes(true);\n",
      "  nudgeAt = at; nudgeBoxes(true);\n  st['d' + at] = 1; if (at === 25) st.d5 = 1; LS.set('ballotta.nudge', st);\n")
sw(T, """  const st = nudgeState(); st['d' + nudgeAt] = 1; if (nudgeAt === 25) st.d5 = 1;
  LS.set('ballotta.nudge', st); track('backup_nudge', { at: String(nudgeAt), action });
  nudgeAt = 0; nudgeBoxes(false);
  if (action === 'keep') openKeep();""",
"""  if (countPicks(ballot.map(b => b.c.id)) >= 25) { const st = nudgeState(); st.d25 = 1; LS.set('ballotta.nudge', st); }
  track('backup_nudge', { at: String(nudgeAt), action });
  // Focus goes where the visitor is working, not to a hidden button: the Keep button (where the Keep window returns it)
  // or, after Not now on a laptop, the ballot paper (Pass 1).
  const wide = /*DESK*/ !!window.desk && matchMedia('(min-width: 1024px)').matches || /*/DESK*/ false;
  const home = action === 'keep' || !wide ? $(wide ? 'dk-keep' : 'a-keep') : $('dk-paper');
  if (home) home.focus({ preventScroll: true });
  nudgeAt = 0; nudgeBoxes(false);
  if (action === 'keep') openKeep();""")
sw(T, "function clearPicks() { if (confirm('Clear all your picks and reasons?')) { track('cleared', { what: 'picks' });",
      "function clearPicks() { if (confirm('Clear all your picks and reasons?')) { track('cleared', { what: 'picks' }); nudgeAt = 0; nudgeBoxes(false);")

# ---- P1-8: a pick and a move are joined only while both are still waiting to be said
sw(T, """  // One polite region and one timer for what the keys did (#45). A move within a second of a pick keeps the pick's words
  // ahead of its own, so the pick isn't cut off; moves alone, or picks alone, simply replace each other.
  let liveT = 0, livePick = null;
  function say(text, isPick) {
    const l = $('dk-live'), keep = !isPick && livePick && Date.now() - livePick.at < 1000 ? livePick.text + '. ' : '';
    livePick = isPick ? { text, at: Date.now() } : null;
    clearTimeout(liveT); l.textContent = '';
    liveT = setTimeout(() => { l.textContent = keep + text; }, 50);
  }""", """  // One polite region and one timer for what the keys did (#45). A move made while a pick's words are still waiting to be
  // said is said with them, so the pick isn't lost; once words are out, the next message simply follows (screen readers
  // queue polite updates), so nothing is read twice (Pass 1). Moves alone, or picks alone, replace each other.
  let liveT = 0, livePick = '';
  function say(text, isPick) {
    const l = $('dk-live'), keep = !isPick && livePick ? livePick + '. ' : '';
    livePick = isPick ? text : '';
    clearTimeout(liveT); l.textContent = '';
    liveT = setTimeout(() => { l.textContent = keep + text; livePick = ''; }, 50);
  }""")

# ---- tests
sw(TS, "                '🇬🇴🇵', '🇩🇳🇨', '€lection Office', 'Travis ©ounty', 'Travis ¢ounty', 'ᏞWV', 'Ꮩoter guide', 'ℒeague']:",
       "                '🇬🇴🇵', '🇩🇳🇨', '€lection Office', 'Travis ©ounty', 'Travis ¢ounty', 'ᏞWV', 'Ꮩoter guide', 'ℒeague',\n"
       "                'G O P Texas', 'Travis G O P', 'D N C Team', 'R N C Chair', 'D E M S Austin', 'A D M I N Team', 'g op', 'v oter guide',\n"
       "                'ꓖꓳꓑ', 'ꓓꓠꓚ Texas']:   # Pass 1 (Lisu letters: caseless, so only the table itself maps them)")
sw(TS, "                 'José', 'Dempsey', 'Gopinath', 'Statham', 'Partridge', 'Ivo Terzić', 'A J', 'J R R Tolkien']:",
       "                 'José', 'Dempsey', 'Gopinath', 'Statham', 'Partridge', 'Ivo Terzić', 'A J', 'J R R Tolkien',\n"
       "                 'S Tate', 'S. Tate', 'P Arty', 'Go P', 'Maria De M', 'Нильс Бор', 'Ольга Бор']:   # Pass 1")
sw(TS, """    assert live.startswith('Contest 4 of ') and live.count('Contest ') == 1, live
    ctx.close()""", """    assert live.startswith('Contest 4 of ') and live.count('Contest ') == 1, live
    pg.keyboard.press('1'); pg.wait_for_timeout(300); pg.keyboard.press('j'); pg.wait_for_timeout(300)   # the pick was already said: not again (Pass 1)
    live = pg.text_content('#dk-live')
    assert live.startswith('Contest 5 of ') and 'picked' not in live, live
    ctx.close()""")
sw(TS, """        decide(0, 4); expect(card).to_be_hidden()
        decide(4, 5); expect(card).to_be_visible(); expect(card.locator('[role="status"]')).to_have_text(msg)""",
"""        decide(0, 4); expect(card).to_be_hidden()
        pg.evaluate('id => pick(id, "__skip")', ids[4]); expect(card).to_be_hidden()            # a skip isn't a pick (Pass 1)
        pg.evaluate('id => pick(id, "__skip")', ids[4])
        below = '#dk-paper' if wide else '#groups'; top = pg.evaluate(f'document.querySelector("{below}").getBoundingClientRect().top')
        decide(4, 5); expect(card).to_be_visible(); expect(card.locator('[role="status"]')).to_have_text(msg)
        assert pg.evaluate(f'document.querySelector("{below}").getBoundingClientRect().top') == top, 'the card pushed the page (Lane: it floats)'
        assert card.evaluate('e => getComputedStyle(e).position') == 'fixed'""")
sw(TS, """        card.locator('[data-nudge="dismiss"]').click(); expect(card).to_be_hidden()
        decide(5, 24); expect(card).to_be_hidden()""",
"""        card.locator('[data-nudge="dismiss"]').click(); expect(card).to_be_hidden()
        if wide: assert pg.evaluate('document.activeElement.id') == 'dk-paper', 'focus back on the paper (Pass 1)'
        decide(5, 24); expect(card).to_be_hidden()""")
sw(TS, """        card.locator('[data-nudge="keep"]').click(); pg.wait_for_selector('#d-keep[open]'); expect(card).to_be_hidden()
        assert [e[1]['action'] for e in events(pg) if e[0] == 'backup_nudge'] == ['shown', 'dismiss', 'shown', 'keep'], events(pg)
        pg.keyboard.press('Escape'); pg.reload()""",
"""        card.locator('[data-nudge="keep"]').click(); pg.wait_for_selector('#d-keep[open]'); expect(card).to_be_hidden()
        assert [e[1]['action'] for e in events(pg) if e[0] == 'backup_nudge'] == ['shown', 'dismiss', 'shown', 'keep'], events(pg)
        pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
        assert pg.evaluate('document.activeElement.id') == ('dk-keep' if wide else 'a-keep'), 'Keep returns focus to a Keep button (Pass 1)'
        pg.reload()""")
sw(TS, """    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[2:30]); expect(backup_card(pg, False)).to_be_hidden()   # already kept a link
    ctx.close()""",
"""    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[2:30]); expect(backup_card(pg, False)).to_be_hidden()   # already kept a link
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
    ctx, pg = new_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('#result:not(.hidden)')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:5]); card = backup_card(pg, False); expect(card).to_be_visible()
    pg.once('dialog', lambda d: d.accept()); pg.click('#reset'); expect(card).to_be_hidden()
    ctx.close()""")

# ---- mutants
m = files.setdefault(MD, (ROOT / MD).read_text(encoding='utf-8'))
for pre in ("('R3b ", "('D6 ", "('D10 ", "('D11 ", "('D16 ", "('D18 ", "('R17 "):
    hits = [l for l in m.split('\n') if l.startswith(' ' + pre)]
    assert len(hits) == 1, pre
    m = m.replace(hits[0] + '\n', '')
N = 'share_names_close_remaining_gaps'
NEW = [
 ('R3b spaced-out initials not joined', 'PREV', r", w.replace(/(?<=(^|\s)\S)\s(?=\S(\s|$))/gu, '')]", ']', ['share_names_block_lookalikes_and_nicknames', N]),
 ('R17 glued words not split', 'PREV', "fold(low.replace(/[|!$@]/g, '')), fold(split), ", "fold(low.replace(/[|!$@]/g, '')), ", ['share_names_block_lookalikes_and_nicknames']),
 ('D6 uneven splits pass', 'PREV', ", fold(split), fold(latin(uneven))];", ", fold(split)];", [N]),
 ('D25 a capitalised word glued to an initial', 'PREV', r"\s(?!\p{Lu}\p{Ll})|(?<!(^|\s)\p{Lu}\p{Ll}+)\s(?=", r"\s|\s(?=", [N]),
 ('D26 б read as g', 'PREV', "delete LOOKALIKE['б']; delete LOOKALIKE['Б'];", '', [N]),
 ('D10 a quick move cuts off the pick', 'PREV', "keep = !isPick && livePick ? livePick + '. ' : '';", "keep = '';", ['desk_quick_pick_then_move_keeps_both_announcements']),
 ('D11 moves pile up', 'PREV', "livePick = isPick ? text : '';", 'livePick = text;', ['desk_quick_pick_then_move_keeps_both_announcements']),
 ('D27 a pick already said is said again', 'PREV', "l.textContent = keep + text; livePick = ''; }, 50);", 'l.textContent = keep + text; }, 50);', ['desk_quick_pick_then_move_keeps_both_announcements']),
 ('D16 backup card never shown', 'PREV', "if (val !== '__skip' && current(cid).includes(val)) nudgeCheck();", '', ['backup_nudge_after_fifth_pick']),
 ('D28 a skip shows the card', 'PREV', "if (val !== '__skip' && current(cid).includes(val)) nudgeCheck();", 'nudgeCheck();', ['backup_nudge_after_fifth_pick']),
 ('D18 an ignored card comes back', 'PREV', "  st['d' + at] = 1; if (at === 25) st.d5 = 1; LS.set('ballotta.nudge', st);\n", '', ['backup_nudge_after_fifth_pick']),
 ('D29 Not now at 25+ brings the 25 card', 'PREV', "  if (countPicks(ballot.map(b => b.c.id)) >= 25) { const st = nudgeState(); st.d25 = 1; LS.set('ballotta.nudge', st); }\n", '', ['backup_nudge_after_fifth_pick']),
 ('D30 focus left on a hidden button', 'PREV', '  if (home) home.focus({ preventScroll: true });\n', '', ['backup_nudge_after_fifth_pick']),
 ('D31 Clear my picks leaves the card', 'PREV', "track('cleared', { what: 'picks' }); nudgeAt = 0; nudgeBoxes(false);", "track('cleared', { what: 'picks' });", ['backup_nudge_after_fifth_pick']),
 ('D32 the phone card pushes the page', 'PREV', '.nudge{position:fixed;left:12px;right:12px;', '.nudge{left:12px;right:12px;', ['backup_nudge_after_fifth_pick']),
 ('D33 the laptop card pushes the paper', 'PREV', '  .dk-nudge{position:fixed;right:24px;bottom:24px;', '  .dk-nudge{grid-column:1/-1;', ['backup_nudge_after_fifth_pick']),
]
k = m.index('\n]\n')
m = m[:k] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in NEW).rstrip('\n') + '\n]\n' + m[k + 3:]
files[MD] = m
for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
print('rework C1 applied to', ', '.join(files))
```

## Script: rework_C2.py

```python
"""Issues round C: rework after remediation-audit Pass 2. Run from the repo root after rework_C1.py:
    python3 <this file> && python3 source/build_site.py"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
T, TS, MD = 'source/template-travis.html', 'tests/test_site.py', 'tests/mutate_desk.py'
files = {}
def sw(path, a, z):
    s = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
    if s.count(a) != 1: sys.exit(f'{path}: FIND occurs {s.count(a)} times: {a[:80]!r}')
    files[path] = s.replace(a, z)

# ---- P2-F1: while a card floats, the page keeps room under it, and scrolling keeps focused things clear of it
sw(T, "const nudgeBoxes = (show) => document.querySelectorAll('[data-nudge-box]').forEach(box => box.classList.toggle('hidden', !show));",
      "const nudgeBoxes = (show) => { document.querySelectorAll('[data-nudge-box]').forEach(box => box.classList.toggle('hidden', !show)); document.documentElement.classList.toggle('nudging', show); };  // room under it (Pass 2)")
sw(T, ".nudge p{margin:0;font-size:15px;font-weight:600}",
      "html.nudging{scroll-padding-bottom:160px}html.nudging body{padding-bottom:150px}  /* nothing ends up under the floating card (Pass 2) */\n"
      ".nudge p{margin:0;font-size:15px;font-weight:600}")
sw(T, "  .dk-nudge .row{display:flex;gap:12px;align-items:center}\n",
      "  .dk-nudge .row{display:flex;gap:12px;align-items:center}\n"
      "  html.nudging{scroll-padding-bottom:190px}html.nudging body{padding-bottom:0}html.nudging .dk-desk{padding-bottom:200px}\n")

# ---- P2-F2: focus returns where the visitor was (usually the pick just made), else a Keep button or the paper
sw(T, "let nudgeAt = 0;  // the card showing: 5, 25, or 0 for none\n",
      "let nudgeAt = 0, nudgeFrom = null;  // the card showing: 5, 25, or 0 for none; where focus was when it appeared\n")
sw(T, "  nudgeAt = at; nudgeBoxes(true);\n", "  nudgeAt = at; nudgeFrom = document.activeElement; nudgeBoxes(true);\n")
sw(T, """  // Focus goes where the visitor is working, not to a hidden button: the Keep button (where the Keep window returns it)
  // or, after Not now on a laptop, the ballot paper (Pass 1).
  const wide = /*DESK*/ !!window.desk && matchMedia('(min-width: 1024px)').matches || /*/DESK*/ false;
  const home = action === 'keep' || !wide ? $(wide ? 'dk-keep' : 'a-keep') : $('dk-paper');""",
"""  // Focus goes back where the visitor was working (usually the pick just made; the Keep window returns it there too),
  // else a Keep button or, after Not now on a laptop, the ballot paper; never a hidden button (Pass 1, Pass 2).
  const wide = /*DESK*/ !!window.desk && matchMedia('(min-width: 1024px)').matches || /*/DESK*/ false;
  const was = nudgeFrom && nudgeFrom.isConnected && nudgeFrom !== document.body && nudgeFrom.getClientRects().length ? nudgeFrom : null;
  const home = was || (action === 'keep' || !wide ? $(wide ? 'dk-keep' : 'a-keep') : $('dk-paper'));""")

# ---- P2-F3/F4/F5 names: small capitals read as capitals; the capitalised-word exception needs 3+ letters; б is b
sw(T, "delete LOOKALIKE['б']; delete LOOKALIKE['Б'];  // Unicode lists б as a look-alike of 6 (read as g): \"Бор\" isn't \"gop\" (Pass 1)\n",
      "LOOKALIKE['б'] = LOOKALIKE['Б'] = 'b';  // Unicode lists б as a look-alike of 6 (read as g): \"Бор\" is \"bop\", not \"gop\" (Pass 1, 2)\n")
sw(T, "  const uneven = n.replace(/[\\p{P}\\p{S}]/gu, ' ').replace(/\\s+/g, ' ').trim().replace(/(?<=(^|\\s)\\S)\\s(?!\\p{Lu}\\p{Ll})|(?<!(^|\\s)\\p{Lu}\\p{Ll}+)\\s(?=\\S(\\s|$))/gu, '');\n",
      "  // Small capitals (ᴘ, ᴛ…) look like capitals, so they count as capitals here; a capitalised word needs 3+ letters (Pass 2).\n"
      "  const caps = n.replace(/[\\u1D00-\\u1D2B\\u0262\\u026A\\u0274\\u0276\\u0280\\u0281\\u028F\\u0299\\u029B\\u029C\\u029F\\uA730\\uA731]/gu, ch => (LOOKALIKE[ch] || ch).toUpperCase());\n"
      "  const uneven = caps.replace(/[\\p{P}\\p{S}]/gu, ' ').replace(/\\s+/g, ' ').trim().replace(/(?<=(^|\\s)\\S)\\s(?!\\p{Lu}\\p{Ll}{2,})|(?<!(^|\\s)\\p{Lu}\\p{Ll}{2,})\\s(?=\\S(\\s|$))/gu, '');\n")

# ---- P2-F6/H1: a pick's words wait a moment; a move in that moment is said with them; nothing is said twice
sw(T, """  // One polite region and one timer for what the keys did (#45). A move made while a pick's words are still waiting to be
  // said is said with them, so the pick isn't lost; once words are out, the next message simply follows (screen readers
  // queue polite updates), so nothing is read twice (Pass 1). Moves alone, or picks alone, replace each other.
  let liveT = 0, livePick = '';
  function say(text, isPick) {
    const l = $('dk-live'), keep = !isPick && livePick ? livePick + '. ' : '';
    livePick = isPick ? text : '';
    clearTimeout(liveT); l.textContent = '';
    liveT = setTimeout(() => { l.textContent = keep + text; livePick = ''; }, 50);
  }""", """  // One polite region and one timer for what the keys did (#45). A pick's words wait 300 ms; a move in that time is said
  // after them in one message, so the pick isn't cut off at typing speed. The newest pick and the newest move win;
  // once a message is out it's never repeated (Pass 1, Pass 2).
  let liveT = 0, livePend = { pick: '', move: '' };
  function say(text, isPick) {
    const l = $('dk-live');
    livePend[isPick ? 'pick' : 'move'] = text;
    clearTimeout(liveT); l.textContent = '';
    liveT = setTimeout(() => { l.textContent = [livePend.pick, livePend.move].filter(Boolean).join('. '); livePend = { pick: '', move: '' }; }, livePend.pick ? 300 : 50);
  }""")

# ---- tests
sw(TS, "                'ꓖꓳꓑ', 'ꓓꓠꓚ Texas']:   # Pass 1 (Lisu letters: caseless, so only the table itself maps them)",
       "                'ꓖꓳꓑ', 'ꓓꓠꓚ Texas',   # Pass 1 (Lisu letters: caseless, so only the table itself maps them)\n"
       "                'G Oᴘ', 'G Oᴘ Texas', 'V Oᴛᴇʀ Guide', 'R Nᴄ', 'D Nᴄ Team', 'Dn C', 'Go P Texas', 'G Op Texas', 'Бallotta', 'БALLOTTA Team']:   # Pass 2")
sw(TS, "                 'S Tate', 'S. Tate', 'P Arty', 'Go P', 'Maria De M', 'Нильс Бор', 'Ольга Бор']:   # Pass 1",
       "                 'S Tate', 'S. Tate', 'P Arty', 'Нильс Бор', 'Ольга Бор', 'Борис Бор']:   # Pass 1, 2")
sw(TS, """    pg.keyboard.press('1'); pg.wait_for_timeout(300); pg.keyboard.press('j'); pg.wait_for_timeout(300)   # the pick was already said: not again (Pass 1)
    live = pg.text_content('#dk-live')
    assert live.startswith('Contest 5 of ') and 'picked' not in live, live""",
"""    pg.keyboard.press('1'); pg.wait_for_timeout(700); pg.keyboard.press('j'); pg.wait_for_timeout(400)   # the pick was already said: not again (Pass 1)
    live = pg.text_content('#dk-live')
    assert live.startswith('Contest 5 of ') and 'picked' not in live, live
    pg.wait_for_timeout(700); pg.keyboard.press('1'); pg.wait_for_timeout(150); pg.keyboard.press('j'); pg.wait_for_timeout(500)   # at typing speed (Pass 2)
    live = pg.text_content('#dk-live'); assert ': picked ' in live and 'Contest 6 of ' in live, live
    pg.wait_for_timeout(700); pg.keyboard.press('1'); pg.keyboard.press('j'); pg.keyboard.press('j'); pg.wait_for_timeout(500)   # two quick moves keep the pick (Pass 2)
    live = pg.text_content('#dk-live'); assert ': picked ' in live and live.count('Contest ') == 1 and 'Contest 8 of ' in live, live""")
sw(TS, """    many(6, 30); expect(card).to_be_visible(); card.locator('[data-nudge="dismiss"]').click(); many(30, 31); expect(card).to_be_hidden()
    ctx.close()""",
"""    many(6, 30); expect(card).to_be_visible(); card.locator('[data-nudge="dismiss"]').click(); many(30, 31); expect(card).to_be_hidden()
    ctx.close()
    # Pass 2: with the card up, nothing at the bottom of the page is stuck under it (phone footer; laptop Print button at
    # 1024x640); after Not now, focus returns to the pick just made, not to the top of the page.
    ctx, pg = new_page(b); pg.goto(BASE); saved_ballot(pg, nums); pg.wait_for_selector('#result:not(.hidden)')
    ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)'); card = backup_card(pg, False)
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:4])
    open_race(pg, ids[4]); fifth = pg.locator(f'#r{ids[4]} .opt').first; fifth.focus(); pg.keyboard.press('Enter'); expect(card).to_be_visible()
    card.locator('[data-nudge="dismiss"]').focus(); pg.keyboard.press('Enter'); expect(card).to_be_hidden()
    assert pg.evaluate('document.activeElement.dataset.c') == ids[4], pg.evaluate('document.activeElement.outerHTML.slice(0, 80)')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[5:25]); expect(card).to_be_visible()
    pg.evaluate('window.scrollTo(0, document.body.scrollHeight)'); pg.wait_for_timeout(200)
    hit = pg.evaluate("() => { const r = document.getElementById('reset-all-foot').getBoundingClientRect(); const e = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2); return e && e.id; }")
    assert hit == 'reset-all-foot', ('the footer button is under the card', hit)
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
        ctx.close()""")

sw(TS, "        assert pg.evaluate('document.activeElement.id') == ('dk-keep' if wide else 'a-keep'), 'Keep returns focus to a Keep button (Pass 1)'",
       "        assert pg.evaluate('document.activeElement.id') == ('dk-paper' if wide else 'a-keep'), 'Keep returns focus where the visitor was (Pass 1, 2)'")
# ---- mutants
m = files.setdefault(MD, (ROOT / MD).read_text(encoding='utf-8'))
# R3b is retired: the uneven form joins spaced-out initials too, so the old join changes nothing the tests can see
# (an equivalent mutant, like R9, V16, V22 and V53).
for pre in ("('D10 ", "('D11 ", "('D25 ", "('D26 ", "('D27 ", "('R3b "):
    hits = [l for l in m.split('\n') if l.startswith(' ' + pre)]
    assert len(hits) == 1, pre
    m = m.replace(hits[0] + '\n', '')
N = 'share_names_close_remaining_gaps'; Q = 'desk_quick_pick_then_move_keeps_both_announcements'; B = 'backup_nudge_after_fifth_pick'
NEW = [
 ('D10 a quick move cuts off the pick', 'PREV', '[livePend.pick, livePend.move].filter(Boolean)', '[livePend.move || livePend.pick].filter(Boolean)', [Q]),
 ('D11 a pick is said at once', 'PREV', ', livePend.pick ? 300 : 50);', ', 50);', [Q]),
 ('D27 a pick already said is said again', 'PREV', " livePend = { pick: '', move: '' }; }, livePend.pick", ' }, livePend.pick', [Q]),
 ('D25 a capitalised word glued to an initial', 'PREV', r"\s(?!\p{Lu}\p{Ll}{2,})|(?<!(^|\s)\p{Lu}\p{Ll}{2,})\s(?=", r"\s|\s(?=", [N]),
 ('D26 б not read as b', 'PREV', "LOOKALIKE['б'] = LOOKALIKE['Б'] = 'b';", "delete LOOKALIKE['б']; delete LOOKALIKE['Б'];", [N]),
 ('D34 two-letter words count as names', 'PREV', r"(?!\p{Lu}\p{Ll}{2,})|(?<!(^|\s)\p{Lu}\p{Ll}{2,})", r"(?!\p{Lu}\p{Ll})|(?<!(^|\s)\p{Lu}\p{Ll}+)", [N]),
 ('D35 small capitals read as lower case', 'PREV', 'const uneven = caps.replace(', 'const uneven = n.replace(', [N]),
 ('D36 the card covers the page end', 'PREV', " document.documentElement.classList.toggle('nudging', show); };", ' };', [B]),
 ('D37 Not now throws focus to the top', 'PREV', '  const home = was || (', '  const home = (', [B]),
]
k = m.index('\n]\n')
m = m[:k] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in NEW).rstrip('\n') + '\n]\n' + m[k + 3:]
files[MD] = m
for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
print('rework C2 applied to', ', '.join(files))
```

## Script: rework_C3.py

```python
"""Issues round C: rework after remediation-audit Pass 3. Run from the repo root after rework_C2.py:
    python3 <this file> && python3 source/build_site.py"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
T, TS, MD = 'source/template-travis.html', 'tests/test_site.py', 'tests/mutate_desk.py'
files = {}
def sw(path, a, z):
    s = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
    if s.count(a) != 1: sys.exit(f'{path}: FIND occurs {s.count(a)} times: {a[:80]!r}')
    files[path] = s.replace(a, z)

# ---- P3-1: an ordered queue, worded when spoken: each contest's newest pick (unless it's the contest moved to), then the
# last move, both describing the picks as they are by then
sw(T, """  // One polite region and one timer for what the keys did (#45). A pick's words wait 300 ms; a move in that time is said
  // after them in one message, so the pick isn't cut off at typing speed. The newest pick and the newest move win;
  // once a message is out it's never repeated (Pass 1, Pass 2).
  let liveT = 0, livePend = { pick: '', move: '' };
  function say(text, isPick) {
    const l = $('dk-live');
    livePend[isPick ? 'pick' : 'move'] = text;
    clearTimeout(liveT); l.textContent = '';
    liveT = setTimeout(() => { l.textContent = [livePend.pick, livePend.move].filter(Boolean).join('. '); livePend = { pick: '', move: '' }; }, livePend.pick ? 300 : 50);
  }
  function announce(c) {  // what a key just did, for screen readers (audit #30)
    const v = current(c.id);
    say(cleanTitle(c) + ': ' + (!v.length ? 'no pick' : v[0] === '__skip' ? 'skipped' : 'picked ' + v.map(x => optLabel(c, x)).join(', ')), true);
  }
  function where(b) {  // a move to another contest, for screen readers: the paper's own label never changes (#39)
    const v = current(b.c.id);
    say('Contest ' + (idx(b.c.id) + 1) + ' of ' + ballot.length + ': ' + cleanTitle(b.c) + '. ' + (!v.length ? 'No pick yet.' : v[0] === '__skip' ? 'Skipped.' : 'Picked ' + v.map(x => optLabel(b.c, x)).join(', ') + '.'), false);
  }""", """  // One polite region and one timer for what the keys did (#45). What happened is queued in order and worded only when it
  // is said, so it describes the picks as they are then: each contest's newest pick (except the contest moved to, whose
  // move says its pick), then the last move or message. A pick waits 300 ms, so a move at typing speed joins it; a
  // message is never repeated (Pass 1, 2, 3).
  let liveT = 0, liveQ = [];
  const pickWords = (c) => { const v = current(c.id); return cleanTitle(c) + ': ' + (!v.length ? 'no pick' : v[0] === '__skip' ? 'skipped' : 'picked ' + v.map(x => optLabel(c, x)).join(', ')); };
  const moveWords = (c) => { const v = current(c.id); return 'Contest ' + (idx(c.id) + 1) + ' of ' + ballot.length + ': ' + cleanTitle(c) + '. ' + (!v.length ? 'No pick yet.' : v[0] === '__skip' ? 'Skipped.' : 'Picked ' + v.map(x => optLabel(c, x)).join(', ') + '.'); };
  function say(item) {  // { pick: contest } | { move: contest } | { text }
    liveQ.push(item);
    clearTimeout(liveT); $('dk-live').textContent = '';
    liveT = setTimeout(sayNow, liveQ.some(x => x.pick) ? 300 : 50);
  }
  function sayNow() {
    const q = liveQ; liveQ = [];
    const last = [...q].reverse().find(x => !x.pick), to = last && last.move ? last.move.id : '', parts = [], done = new Set();
    [...q].reverse().forEach(x => { if (x.pick && x.pick.id !== to && !done.has(x.pick.id)) { done.add(x.pick.id); parts.unshift(pickWords(x.pick)); } });
    if (last) parts.push(last.move ? moveWords(last.move) : last.text);
    $('dk-live').textContent = parts.join('. ');
  }
  function announce(c) { say({ pick: c }); }  // what a key just did, for screen readers (audit #30)
  function where(b) { say({ move: b.c }); }  // a move to another contest: the paper's own label never changes (#39)""")
sw(T, "    say('Crib sheet: print options, then the Print button.', false);\n",
      "    say({ text: 'Crib sheet: print options, then the Print button.' });\n")

# ---- P3-2: focus that didn't land (e.g. inside a race closed since) falls back
sw(T, "  if (home) home.focus({ preventScroll: true });\n",
      "  if (home) home.focus({ preventScroll: true });\n"
      "  if (document.activeElement !== home) { const f = $(wide ? 'dk-paper' : 'a-keep'); if (f) f.focus({ preventScroll: true }); }  // it didn't take: e.g. a closed race (Pass 3)\n")

# ---- P3-3: more letters that look like small capitals: Cherokee small letters, Cyrillic т м н к в п; ᴩ is p
sw(T, "  const caps = n.replace(/[\\u1D00-\\u1D2B\\u0262\\u026A\\u0274\\u0276\\u0280\\u0281\\u028F\\u0299\\u029B\\u029C\\u029F\\uA730\\uA731]/gu, ch => (LOOKALIKE[ch] || ch).toUpperCase());\n",
      "  const caps = n.replace(/[\\u1D00-\\u1D2B\\u0262\\u026A\\u0274\\u0276\\u0280\\u0281\\u028F\\u0299\\u029B\\u029C\\u029F\\uA730\\uA731\\uAB70-\\uABBFтмнквп]/gu, ch => (LOOKALIKE[ch] || LOOKALIKE[ch.toUpperCase()] || ch).toUpperCase());  // + Cherokee small letters, Cyrillic т м н к в п (Pass 3)\n")
sw(T, "LOOKALIKE['б'] = LOOKALIKE['Б'] = 'b';", "LOOKALIKE['б'] = LOOKALIKE['Б'] = 'b'; LOOKALIKE['ᴩ'] = 'p';")

# ---- P3-4/5: the room under the phone card includes the iPhone home-bar inset; none of it applies to printing
sw(T, "html.nudging{scroll-padding-bottom:160px}html.nudging body{padding-bottom:150px}  /* nothing ends up under the floating card (Pass 2) */",
      "@media screen{html.nudging{scroll-padding-bottom:calc(190px + env(safe-area-inset-bottom))}html.nudging body{padding-bottom:calc(180px + env(safe-area-inset-bottom))}}  /* nothing ends up under the floating card (Pass 2, 3) */")

# ---- tests
sw(TS, "                'G Oᴘ', 'G Oᴘ Texas', 'V Oᴛᴇʀ Guide', 'R Nᴄ', 'D Nᴄ Team', 'Dn C', 'Go P Texas', 'G Op Texas', 'Бallotta', 'БALLOTTA Team']:   # Pass 2",
       "                'G Oᴘ', 'G Oᴘ Texas', 'V Oᴛᴇʀ Guide', 'R Nᴄ', 'D Nᴄ Team', 'Dn C', 'Go P Texas', 'G Op Texas', 'Бallotta', 'БALLOTTA Team',   # Pass 2\n"
       "                'V Oꭲꭼꮢ Guide', 'D Eꮇꮪ', 'D Eꮇꮪ Texas', 'D Eмѕ', 'V Oтer Guide', 'G Oᴩ']:   # Pass 3")
sw(TS, """    live = pg.text_content('#dk-live'); assert ': picked ' in live and live.count('Contest ') == 1 and 'Contest 8 of ' in live, live
    ctx.close()""", """    live = pg.text_content('#dk-live'); assert ': picked ' in live and live.count('Contest ') == 1 and 'Contest 8 of ' in live, live
    # Pick, move, pick at typing speed: the first pick is said, and the move describes the contest as it is by then (Pass 3)
    t = lambda i: pg.evaluate(f'cleanTitle(ballot[{i}].c)')
    pg.wait_for_timeout(700); here = pg.evaluate("ballot.findIndex(x => x.c.id === document.getElementById('dk-paper').dataset.c)")
    pg.keyboard.press('1'); pg.wait_for_timeout(120); pg.keyboard.press('j'); pg.wait_for_timeout(120); pg.keyboard.press('1'); pg.wait_for_timeout(600)
    live = pg.text_content('#dk-live')
    assert live.startswith(t(here) + ': picked ') and f'Contest {here + 2} of ' in live and 'No pick yet' not in live, live
    assert live.count(t(here + 1)) == 1, ('the contest moved to is described once', live)   # Pass 4
    ctx.close()""")
sw(TS, """    assert pg.evaluate('document.activeElement.dataset.c') == ids[4], pg.evaluate('document.activeElement.outerHTML.slice(0, 80)')""",
       """    assert pg.evaluate('document.activeElement.dataset.c') == ids[4], pg.evaluate('document.activeElement.outerHTML.slice(0, 80)')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[5:6])   # (not a card moment: 6 picks, the 5 card was seen)""")
sw(TS, """    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[5:25]); expect(card).to_be_visible()
    pg.evaluate('window.scrollTo(0, document.body.scrollHeight)'); pg.wait_for_timeout(200)""",
       """    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[6:24])
    open_race(pg, ids[24]); last = pg.locator(f'#r{ids[24]} .opt').first; last.focus(); pg.keyboard.press('Enter'); expect(card).to_be_visible()
    pg.evaluate(f"document.getElementById('r{ids[24]}').open = false")                     # the race closed since: focus can't go back there (Pass 3)
    card.locator('[data-nudge="dismiss"]').focus(); pg.keyboard.press('Enter'); expect(card).to_be_hidden()
    assert pg.evaluate('document.activeElement.id') == 'a-keep', pg.evaluate('document.activeElement.tagName')
    pg.evaluate("localStorage.removeItem('ballotta.nudge')"); pg.evaluate('id => pick(id, optionsOf(BYID[id])[0])', ids[25]); expect(card).to_be_visible()
    pg.evaluate('window.scrollTo(0, document.body.scrollHeight)'); pg.wait_for_timeout(200)""")
sw(TS, """    assert hit == 'reset-all-foot', ('the footer button is under the card', hit)
    ctx.close()""", """    assert hit == 'reset-all-foot', ('the footer button is under the card', hit)
    pg.emulate_media(media='print'); assert pg.evaluate('getComputedStyle(document.body).paddingBottom') == '0px', 'no room reserved on paper (Pass 3)'
    ctx.close()""")

# ---- mutants
m = files.setdefault(MD, (ROOT / MD).read_text(encoding='utf-8'))
for pre in ("('D10 ", "('D11 ", "('D27 ", "('D13 ", "('D35 ", "('A25 "):
    hits = [l for l in m.split('\n') if l.startswith(' ' + pre)]
    assert len(hits) == 1, pre
    m = m.replace(hits[0] + '\n', '')
N = 'share_names_close_remaining_gaps'; Q = 'desk_quick_pick_then_move_keeps_both_announcements'; B = 'backup_nudge_after_fifth_pick'
NEW = [
 ('A25 contest number off by one', 'PREV', "'Contest ' + (idx(c.id) + 1)", "'Contest ' + idx(c.id)", ['desk_moves_are_announced']),
 ('D10 a quick move cuts off the pick', 'PREV', "    [...q].reverse().forEach(x => { if (x.pick && x.pick.id !== to && !done.has(x.pick.id)) { done.add(x.pick.id); parts.unshift(pickWords(x.pick)); } });\n", '', [Q]),
 ('D11 a pick is said at once', 'PREV', 'liveQ.some(x => x.pick) ? 300 : 50);', '50);', [Q]),
 ('D27 a pick already said is said again', 'PREV', '    const q = liveQ; liveQ = [];\n', '    const q = liveQ;\n', [Q]),
 ('D38 a move worded too early', 'PREV', 'function where(b) { say({ move: b.c }); }', "function where(b) { say({ text: moveWords(b.c) }); }", [Q]),
 ('D39 the moved-to contest said twice', 'PREV', 'x.pick && x.pick.id !== to && ', 'x.pick && ', [Q]),
 ('D13 Print… says nothing', 'PREV', "    say({ text: 'Crib sheet: print options, then the Print button.' });\n", '', ['desk_print_by_touch_and_announced']),
 ('D35 small capitals read as lower case', 'PREV', 'const uneven = caps.replace(', 'const uneven = n.replace(', [N]),
 ('D40 Cyrillic small capitals missed', 'PREV', 'тмнквп]/gu, ch =>', ']/gu, ch =>', [N]),
 ('D41 focus lost in a closed race', 'PREV', "  if (document.activeElement !== home) { const f = $(wide ? 'dk-paper' : 'a-keep'); if (f) f.focus({ preventScroll: true }); }", '', [B]),
 ('D42 room under the card on paper', 'PREV', '@media screen{html.nudging{', '@media all{html.nudging{', [B]),
]
k = m.index('\n]\n')
m = m[:k] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in NEW).rstrip('\n') + '\n]\n' + m[k + 3:]
files[MD] = m
for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
print('rework C3 applied to', ', '.join(files))
```
