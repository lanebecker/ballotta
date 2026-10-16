# Issues round, commit A (Oct 15, 2026): #20 #21 #22 #23 #24 #32 #33 #34 #37 #39 #40 #41 #42, plus the laptop Print… change

**Goal.** Clear the contained GitHub issues from the laptop-layout audit milestone in one commit, test-first, before
commit B (#36 security hardening and #38 the laptop/phone untangling).

**Lane's decisions (Oct 15).**
- #33: a pick past "vote for up to N" changes nothing and says "You can pick up to N. Unpick one first." under the
  race's "Vote for up to N" line, on both layouts.
- #24: the friend card says "Most races on your ballot link to neutral sources."
- #21: catch look-alike letters and party nicknames (Dems, GOP, Repubs, RNC, DNC…).
- #42: a "Clear everything on this device" button in the phone footer, shown only while this browser holds anything.
- All 15 issues in this round (#36 and #38 in commit B).
- Mid-round request: the laptop's left-column Print opens the Crib sheet view (where the print options are) instead of
  printing straight away. It is now labelled "Print…".

**What each fix does**

| Issue | Fix | Test |
|---|---|---|
| #20 | Saved picks must be an object and saved reasons text, checked when read | `stored_junk_never_breaks_keep_or_share` |
| #21 | `safeName` folds look-alike letters and stand-in digits/symbols in the name and the reserved words alike; long reserved words match anywhere, short ones as words (or glued to 4+ letters), with punctuation/symbols as spaces, spaced initials joined, and case/digit splits | `share_names_block_lookalikes_and_nicknames`, `audit_a5_a8_a12_hostile_share` |
| #22 | `.dk-loc` gets 4px of padding (and -4px margin) so the "change" focus ring isn't clipped | `desk_change_link_focus_ring_is_whole` |
| #23 | `overflow-wrap:anywhere` on friend, compare and laptop friend text | `friend_card_long_names_and_honest_copy` |
| #24 | Copy change | same |
| #32 | Rail chip is `aria-hidden`; visually hidden "Maya picked …" text | `desk_friend_pick_in_rail_has_a_name` |
| #33 | `pick()` refuses and returns false; `limitNote()` fills a `role="status"` span; a refused key pick isn't announced; Clear my picks clears the note | `extra_pick_is_explained` |
| #34 | `today()` read when drawing; `periodChosen`; `dayCheck()` every minute and on tab return; on a new day only the header line changes, and the laptop vote view re-draws only if the period changed (focus then goes to the paper) | `dates_move_on_in_a_tab_left_open` |
| #37 | `build_site.py` inserts the data last | `build_inserts_data_last` |
| #39 | `where()` announces "Contest i of n: title. …" on a keyboard or rail move | `desk_moves_are_announced` |
| #40 | `desk.ballot()` hides an older link's notice | `desk_old_link_warning_gone_after_new_lookup` |
| #41 | `mutate_desk.py`: TERM/HUP/INT restore the original first (`PENDING`), writes block signals, `main()` guard | `mutation_runner_restores_on_any_signal` |
| #42 | Footer button, `footClear()` on every storage write, on start and on another tab's write | `phone_can_clear_everything_from_the_footer` |
| Print… | Opens the crib view once; a keyboard press focuses the real Print button and scrolls it on screen; a held Enter can't print | `desk_print_button_opens_the_crib_sheet` |

**How to apply (from the repo root, in order).** Each script refuses to run if an anchor it edits isn't found exactly once.

```
python3 <scripts>/edits_tests_A.py      # 12 tests (RED first: all 12 failed on the unfixed page, for the reason in each issue)
python3 <scripts>/edits_page_A.py       # the fixes
python3 <scripts>/edits_mutants_A.py    # 33 mutants
python3 <scripts>/rework_A1.py          # remediation audit Pass 1 + Lane's Print change
python3 <scripts>/rework_A2.py          # Pass 2
python3 <scripts>/rework_A3.py          # Pass 3
python3 <scripts>/rework_A4.py          # Pass 4
python3 source/build_site.py
python3 tests/test_site.py              # expected: 60/60 passed (index.html)
python3 tests/mutate_desk.py 161 217    # expected: 56 of 56 mutants killed (the full list is 217)
```

## Execution log

- RED: the 12 new tests failed on the unfixed page, each for its issue's reason. GREEN after `edits_page_A.py`, except
  `audit_a5_a8_a12_hostile_share` ("Vote411" slipped through once digits were read as letters); fixed by checking both
  ways, then 59/59.
- 33 of 33 first-round mutants killed.
- **Remediation audit Pass 1** (independent agent, executed reproductions). Fixed: a new-day redraw on the laptop took
  focus from a reason being typed, so the rest of the sentence ran as shortcuts (picks, skips); hyphen-joined reserved
  words ("Travis-GOP") passed; Clear my picks left the limit note; another tab's write left the footer button stale.
  Logged, not fixed: a move announcement can replace a pick announcement within ~10ms (HYPOTHESIS, not confirmed with a
  screen reader). Pre-existing, filed: `ballotta.gen` / `ballotta.name` read from storage unchecked.
- Lane (18:12): the laptop Print button should open the Crib sheet view. Done in rework_A1; one existing test updated
  to press the crib view's own Print button.
- **Pass 2** (rework only). Fixed: digit 1 standing for both i and l in one name, dotted initials, symbols between
  letters (one fold replaced the combination passes); Print… gave keyboard and screen-reader users no feedback (now
  "Print…", focus moves to the real button, no double count). Accepted: "Mo-Dem" style hyphenated names are blocked.
- **Pass 3** (rework 2 only). Fixed: real names were blocked across a space ("Gustavo Terrazas" holds "voter",
  "Felicity Ofori" "cityof"), a pre-existing fault: short reserved words now match as words; glued camel-case and
  digit forms ("TravisGOP", "GOP2026"); 8/9 stand-ins; Print… focus off screen at 1024–1279px; focus moved on a mouse
  click (Space then printed).
- **Pass 4** (rework 3 only). Fixed: the vote view's "same position" focus restore landed on a different vote center's
  Directions link when the list changed (now: re-draw only when the period changes, focus the paper); glued lowercase
  handles ("voterguide", "cityofaustin", "travisclerk") were blocked before Pass 3 and passed after it (restored: a
  reserved word at the start or end of one word with 4+ more letters); leading acronyms ("GOPTravis"); holding Enter on
  Print… printed. Accepted as best effort and filed: a stray space inside a word ("V oter"), uneven splits ("G OP"),
  very short glued forms ("TXVOTERS"), Armenian/Cherokee look-alikes and flag-emoji letters.
- Mutant R9 (symbols read as spaces in the word check) survived: a regex word boundary already treats a symbol as a
  break and the joined form strips symbols, so it is an equivalent mutant; retired like V16, V22 and V53.
- **Final:** 60/60 tests; 56 of 56 new mutants killed (161 earlier ones unchanged).
- Convergence: Pass 4's fixes removed code (the focus heuristic) or added narrowly tested rules; the remaining findings
  are all on the name block's best-effort edge and are filed rather than chased further.

## Script: edits_tests_A.py

```python
"""Issues round, commit A: the tests (written first; each must fail before the fixes). Run from the repo root:
    python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
TS = ROOT / 'tests/test_site.py'
s = TS.read_text(encoding='utf-8')
def sw(a, z):
    global s
    if s.count(a) != 1: sys.exit(f'test_site.py: FIND occurs {s.count(a)} times: {a[:70]!r}')
    s = s.replace(a, z)

# A working copy can run its own server next to a live job (the default stays 8765).
sw("PORT = 8765\n", "PORT = int(os.environ.get('BALLOTTA_PORT', '8765'))\n")

NEW = r'''
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
                'RNC', 'DNC Texas', 'L3ague', 'C0unty Clerk', 'ΟFFICIAL', 'Тravis Сounty Еlections', 'ᴠᴏᴛᴇʀ ɪɴꜰᴏ', 'Ballοtta']:
        assert sn(bad) == '', bad
    for good in ['Maya', 'Ana', 'José', "O'Brien", 'Dempsey', 'Ελένη', 'Ольга', '李明', 'Demetria', 'Gopal']:
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
    pg.keyboard.press('1'); pg.keyboard.press('k'); said(f'Contest 1 of {n}: {t(0)}. No pick yet.')
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
    lookup(pg); expect(foot).to_be_visible()                                   # shown as soon as a lookup saves the ballot
    pg.reload(); pg.wait_for_selector('#result:not(.hidden)'); expect(foot).to_be_visible()   # and on a later visit
    ctx.close()

def main():'''
sw("\ndef main():", NEW)
TS.write_text(s, encoding='utf-8')
print('tests A added')
```

## Script: edits_page_A.py

```python
"""Issues round, commit A: the fixes for #20 #21 #22 #23 #24 #32 #33 #34 #37 #39 #40 #41 #42. Run from the repo root:
    python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
T, B, MD, RM = 'source/template-travis.html', 'source/build_site.py', 'tests/mutate_desk.py', 'README.md'
files = {}
def sw(path, a, z):
    s = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
    if s.count(a) != 1: sys.exit(f'{path}: FIND occurs {s.count(a)} times: {a[:80]!r}')
    files[path] = s.replace(a, z)

# ---------- #20: saved state is checked when it's read
sw(T, "let picks = LS.get('ballotta.picks', {}), whys = LS.get('ballotta.whys', {});",
      "// Saved state is checked when read: an old format or tampering (a reason that isn't text, picks that aren't an\n"
      "// object) can't make the page, Keep or Share throw (#20).\n"
      "const plain = (o) => o && typeof o === 'object' && !Array.isArray(o) ? o : {};\n"
      "let picks = plain(LS.get('ballotta.picks', {})), whys = Object.fromEntries(Object.entries(plain(LS.get('ballotta.whys', {}))).filter(([, v]) => typeof v === 'string'));")

# ---------- #42: the footer's Clear everything shows whenever this browser holds something from Ballotta
sw(T, "const LS = { get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} } };\n"
      "const SS = { get(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { sessionStorage.setItem(k, v); } catch (e) {} }, del(k) { try { sessionStorage.removeItem(k); } catch (e) {} } };",
      "const LS = { get(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } }, set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} footClear(); } };\n"
      "const SS = { get(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { sessionStorage.setItem(k, v); } catch (e) {} footClear(); }, del(k) { try { sessionStorage.removeItem(k); } catch (e) {} footClear(); } };")
sw(T, "    <p class=\"note\">Opens your email app with a few details filled in (your precinct and how the lookup went, never your address).</p>\n",
      "    <p class=\"note\">Opens your email app with a few details filled in (your precinct and how the lookup went, never your address).</p>\n"
      "    <button type=\"button\" class=\"x hidden\" id=\"reset-all-foot\" style=\"align-self:flex-start\">Clear everything on this device</button>\n")
sw(T, "// Clear everything on this device (#29): every ballotta.* key in this browser, then a fresh page. Asks first.\n"
      "$('reset-all').addEventListener('click', () => {\n",
      "// Clear everything on this device (#29): every ballotta.* key in this browser, then a fresh page. Asks first.\n"
      "function clearEverything() {\n")
sw(T, "  location.replace(location.pathname);\n});\n",
      "  location.replace(location.pathname);\n}\n"
      "$('reset-all').addEventListener('click', clearEverything);\n"
      "$('reset-all-foot').addEventListener('click', clearEverything);  // reachable without a ballot of your own, e.g. after only a friend's link (#42)\n"
      "// The footer's button shows only while this browser holds something from Ballotta (storage writes call this).\n"
      "function footClear() {\n"
      "  let has = false;\n"
      "  ['localStorage', 'sessionStorage'].forEach(n => { try { if (Object.keys(window[n]).some(k => k.startsWith('ballotta.'))) has = true; } catch (e) {} });\n"
      "  const f = $('reset-all-foot'); if (f) f.classList.toggle('hidden', !has);\n"
      "}\n")
sw(T, "(function start() {\n  const st = LS.get('ballotta.ballot', null);",
      "(function start() {\n  footClear();  // a link opened before this script ran is already in sessionStorage\n  const st = LS.get('ballotta.ballot', null);")
sw(RM, "**Clear everything on this device** (under the crib sheet; Feedback & Info on a laptop) removes them all.",
       "**Clear everything on this device** (under the crib sheet and, on a phone, at the bottom of the page whenever anything is stored; Feedback & Info on a laptop) removes them all.")

# ---------- #21: look-alike letters, digits for letters, and party nicknames
sw(T, """// A share link is made by anyone, so a name can't claim to be an organization or Ballotta itself.
// Best effort only (look-alike letters from other alphabets can still slip through); the "Ballotta doesn't endorse
// anyone" copy is the real guard. Tested on a skeleton with spaces, punctuation, marks and invisible characters removed.
const RESERVED = /league|lwv|voter|vote411|county|clerk|official|ballotta|cityof|villageof|election|government|democrat|republican|libertarian|greenparty|taxoffice|campaign|secretaryofstate/;
const RESERVED_WORDS = /\\b(state|party|admin|gop)\\b/;
function safeName(n) {
  if (typeof n !== 'string') return '';
  n = n.normalize('NFKC').replace(/[\\p{Cc}\\p{Cf}\\p{Default_Ignorable_Code_Point}]/gu, '').replace(/\\s+/g, ' ').trim().slice(0, 30);
  const low = n.normalize('NFKD').replace(/\\p{M}/gu, '').toLowerCase();
  const skel = low.replace(/[\\s\\p{P}\\p{S}]/gu, '');
  return RESERVED.test(skel) || RESERVED_WORDS.test(low) ? '' : n;
}""",
"""// A share link is made by anyone, so a name can't claim to be an organization, a party or Ballotta itself.
// Best effort only; the "Ballotta doesn't endorse anyone" copy is the real guard. Before the check, look-alike letters
// from other alphabets (Cyrillic а, Greek ο, small-capital ʟ…) and digits or symbols standing in for letters become
// the Latin letters they imitate (#21); the name shown is never changed. Tested on a skeleton with spaces,
// punctuation, marks and invisible characters removed, and word by word for short names like GOP or Dems.
const RESERVED = /league|lwv|voter|vote411|county|clerk|official|ballotta|cityof|villageof|election|government|democrat|republican|libertarian|greenparty|taxoffice|campaign|secretaryofstate/;
const RESERVED_WORDS = /\\b(state|party|admin|gop|dems?|repubs?|rnc|dnc)\\b/;
const LOOKALIKE = { 'а': 'a', 'в': 'b', 'с': 'c', 'ԁ': 'd', 'е': 'e', 'ё': 'e', 'һ': 'h', 'н': 'h', 'і': 'i', 'ї': 'i', 'ј': 'j', 'к': 'k', 'ӏ': 'l',
  'м': 'm', 'о': 'o', 'р': 'p', 'ԛ': 'q', 'г': 'r', 'ѕ': 's', 'т': 't', 'у': 'y', 'ү': 'y', 'х': 'x', 'ԝ': 'w',
  'α': 'a', 'β': 'b', 'ε': 'e', 'η': 'n', 'ι': 'i', 'κ': 'k', 'ν': 'v', 'ο': 'o', 'ρ': 'p', 'τ': 't', 'υ': 'u', 'χ': 'x', 'γ': 'y',
  'ᴀ': 'a', 'ʙ': 'b', 'ᴄ': 'c', 'ᴅ': 'd', 'ᴇ': 'e', 'ɢ': 'g', 'ʜ': 'h', 'ɪ': 'i', 'ᴊ': 'j', 'ᴋ': 'k', 'ʟ': 'l', 'ᴍ': 'm', 'ɴ': 'n',
  'ᴏ': 'o', 'ᴘ': 'p', 'ʀ': 'r', 'ꜱ': 's', 'ᴛ': 't', 'ᴜ': 'u', 'ᴠ': 'v', 'ᴡ': 'w', 'ʏ': 'y', 'ᴢ': 'z' };
const LEET = { '0': 'o', '1': 'l', '3': 'e', '4': 'a', '5': 's', '7': 't', '$': 's', '@': 'a', '|': 'l' };  // checked both ways: "Vote411" stays blocked
function safeName(n) {
  if (typeof n !== 'string') return '';
  n = n.normalize('NFKC').replace(/[\\p{Cc}\\p{Cf}\\p{Default_Ignorable_Code_Point}]/gu, '').replace(/\\s+/g, ' ').trim().slice(0, 30);
  const low = [...n.normalize('NFKD').replace(/\\p{M}/gu, '').toLowerCase()].map(ch => LOOKALIKE[ch] || ch).join('');
  const hit = (t) => RESERVED.test(t.replace(/[\\s\\p{P}\\p{S}]/gu, '')) || RESERVED_WORDS.test(t.replace(/\\p{P}/gu, ''));
  return hit(low) || hit(low.replace(/[013457$@|]/g, ch => LEET[ch])) ? '' : n;
}""")

# ---------- #22: the "change" link's focus ring fits inside the header's ellipsis box
sw(T, ".dk-loc{font-size:14px;color:var(--ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}",
      ".dk-loc{font-size:14px;color:var(--ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;padding:4px;margin:-4px}  /* room for the focus ring on \"change\" (#22) */")

# ---------- #23: a long name with no spaces wraps (phone friend card and compare; laptop chip, call to action, notes)
sw(T, ".who{display:flex;gap:12px;align-items:center;padding:14px 16px;border-radius:12px;background:var(--lilac)}",
      ".who{display:flex;gap:12px;align-items:center;padding:14px 16px;border-radius:12px;background:var(--lilac)}\n"
      "#friend h2,#friend .note,#friend .fp,#compare h2,#compare .note,#compare .cmp,#compare .lead{overflow-wrap:anywhere}  /* a 30-letter name with no spaces (#23) */\n"
      ".limit:not(:empty){display:block;margin-top:4px;font-weight:600;color:var(--plum)}  /* \"You can pick up to 2…\" (#33) */")
sw(T, "  .dk-fchip{align-self:flex-start;display:inline-flex;",
      "  .dk-fcta,.dk-fchip,.dk-fbox,.dk-fp{overflow-wrap:anywhere;min-width:0}  /* #23 */\n  .dk-fchip{align-self:flex-start;display:inline-flex;")

# ---------- #24: the friend card doesn't overclaim
sw(T, "Ballotta doesn’t endorse anyone. Each race on your ballot links to neutral sources. <button",
      "Ballotta doesn’t endorse anyone. Most races on your ballot link to neutral sources. <button")

# ---------- #32: a friend's pick in a rail row is read out, not only shown as an initial with a hover title
sw(T, "        const fa = friend && friend.P[id] ? '<span class=\"dk-fa' + (samePick(id) ? '' : ' diff') + '\" title=\"' + possessive() + ' pick: ' + esc(friend.P[id].map(x => optLabel(b.c, x)).join(', ')) + '\">' + initial() + '</span>' : '';",
      "        const fp = friend && friend.P[id] ? esc(friend.P[id].map(x => optLabel(b.c, x)).join(', ')) : '';  // read out as \"Maya picked …\" (#32)\n"
      "        const fa = fp ? '<span class=\"dk-fa' + (samePick(id) ? '' : ' diff') + '\" aria-hidden=\"true\" title=\"' + possessive() + ' pick: ' + fp + '\">' + initial() + '</span><span class=\"dk-vh\">' + esc(friendName()) + ' picked ' + fp + '</span>' : '';")

# ---------- #33: a pick past "vote for up to N" changes nothing and says why
sw(T, "    body += '<p class=\"note\">' + (opts.length === 1 ? 'Unopposed' : (n > 1 ? 'Vote for up to ' + n : 'Vote for 1')) + (c.choices.includes('Write-in') ? ' · write-in allowed' : '') + '</p>';",
      "    body += '<p class=\"note\">' + (opts.length === 1 ? 'Unopposed' : (n > 1 ? 'Vote for up to ' + n : 'Vote for 1')) + (c.choices.includes('Write-in') ? ' · write-in allowed' : '') + (n > 1 ? '<span class=\"limit\" data-limit=\"' + c.id + '\" role=\"status\"></span>' : '') + '</p>';")
sw(T, "    if (!isM) h += '<div class=\"dk-meta\">' + (opts.length === 1 ? 'Unopposed' : (n > 1 ? 'Vote for up to ' + n : 'Vote for 1')) + (c.choices.includes('Write-in') ? ' · write-in allowed' : '') + '</div>';",
      "    if (!isM) h += '<div class=\"dk-meta\">' + (opts.length === 1 ? 'Unopposed' : (n > 1 ? 'Vote for up to ' + n : 'Vote for 1')) + (c.choices.includes('Write-in') ? ' · write-in allowed' : '') + (n > 1 ? '<span class=\"limit\" data-limit=\"' + c.id + '\" role=\"status\"></span>' : '') + '</div>';")
sw(T, """  else if (n > 1) { cur = cur.includes(val) ? cur.filter(x => x !== val) : (cur.length < n ? cur.concat(val) : cur); }
  else cur = current(cid)[0] === val ? [] : [val];
  picks[cid] = cur; LS.set('ballotta.picks', picks);""",
"""  else if (n > 1) {
    if (!cur.includes(val) && cur.length >= n) { limitNote(cid, n); return false; }  // already N picks: say why nothing changed (#33)
    cur = cur.includes(val) ? cur.filter(x => x !== val) : cur.concat(val);
  }
  else cur = current(cid)[0] === val ? [] : [val];
  limitNote(cid, 0);
  picks[cid] = cur; LS.set('ballotta.picks', picks);""")
sw(T, "  $('s' + cid).innerHTML = summaryHTML(cid);\n  refresh();\n}\n",
      "  $('s' + cid).innerHTML = summaryHTML(cid);\n  refresh();\n  return true;\n}\n"
      "// Under the race's \"Vote for up to N\" line, on both layouts; a status region, so screen readers say it too. 0 clears it.\n"
      "function limitNote(cid, n) {\n"
      "  document.querySelectorAll('[data-limit=\"' + cid + '\"]').forEach(s => { s.textContent = n ? 'You can pick up to ' + n + '. Unpick one first.' : ''; });\n"
      "}\n")
sw(T, "e.preventDefault(); pick(b.c.id, o); announce(b.c); used('pick');",
      "e.preventDefault(); if (pick(b.c.id, o) !== false) announce(b.c); used('pick');")

# ---------- #34: today's date is read when drawing; a tab left open past midnight moves on
sw(T, "const NOW = new Date();\nlet period = (NOW.getFullYear() > 2026 || (NOW.getMonth() === 9 && NOW.getDate() > 30) || NOW.getMonth() > 9) ? 'eday' : 'early';",
      "// Today's date is read whenever something is drawn, never once at load: a tab left open past midnight moves on to\n"
      "// the new day (#34). A voting period the visitor picked stays picked.\n"
      "const today = () => new Date();\n"
      "const defaultPeriod = () => { const d = today(); return (d.getFullYear() > 2026 || (d.getMonth() === 9 && d.getDate() > 30) || d.getMonth() > 9) ? 'eday' : 'early'; };\n"
      "let period = defaultPeriod(), periodChosen = false;")
sw(T, "  const started = NOW >= new Date(2026, 9, 19);", "  const started = today() >= new Date(2026, 9, 19);")
sw(T, "    const d = new Date(NOW.getFullYear(), NOW.getMonth(), NOW.getDate()).getTime(), t = (m, day) => new Date(2026, m, day).getTime();",
      "    const now = today(), d = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime(), t = (m, day) => new Date(2026, m, day).getTime();")
sw(T, "$('t-early').addEventListener('click', () => { period = 'early'; renderVote(); });\n$('t-eday').addEventListener('click', () => { period = 'eday'; renderVote(); });\n",
      "$('t-early').addEventListener('click', () => { period = 'early'; periodChosen = true; renderVote(); });\n"
      "$('t-eday').addEventListener('click', () => { period = 'eday'; periodChosen = true; renderVote(); });\n"
      "let shownDay = today().toDateString();\n"
      "function dayCheck() {  // a new day since the page was drawn: redraw what depends on the date\n"
      "  const d = today().toDateString(); if (d === shownDay) return;\n"
      "  shownDay = d;\n"
      "  if (!periodChosen) period = defaultPeriod();\n"
      "  renderVote();/*DESK*/ if (window.desk) try { desk.render(); } catch (e) {}/*/DESK*/\n"
      "}\n"
      "document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') dayCheck(); });\n"
      "setInterval(dayCheck, 60000);\n")
sw(T, "P().querySelectorAll('[data-period]').forEach(btn => btn.addEventListener('click', () => { period = btn.dataset.period; renderVote(); viewVote(); }));",
      "P().querySelectorAll('[data-period]').forEach(btn => btn.addEventListener('click', () => { period = btn.dataset.period; periodChosen = true; renderVote(); viewVote(); }));")

# ---------- #39: J, K and N (and a rail click) say where they landed
sw(T, "    if (focus) P().focus({ preventScroll: true });\n    const r = $('dk-out')",
      "    if (focus) { P().focus({ preventScroll: true }); where(curB()); }\n    const r = $('dk-out')")
sw(T, "  // Decide by mouse puts you back on the paper,",
      "  function where(b) {  // a move to another contest, for screen readers: the paper's own label never changes (#39)\n"
      "    const v = current(b.c.id), l = $('dk-live');\n"
      "    l.textContent = '';\n"
      "    setTimeout(() => { l.textContent = 'Contest ' + (idx(b.c.id) + 1) + ' of ' + ballot.length + ': ' + cleanTitle(b.c) + '. ' + (!v.length ? 'No pick yet.' : v[0] === '__skip' ? 'Skipped.' : 'Picked ' + v.map(x => optLabel(b.c, x)).join(', ') + '.'); }, 50);\n"
      "  }\n"
      "  // Decide by mouse puts you back on the paper,")

# ---------- #40: a new ballot clears an older link's notice, even one stored at phone width
sw(T, "    ballot(meta) {\n      ui.landing = false;\n",
      "    ballot(meta) {\n      ui.landing = false;\n      $('dk-say').classList.add('hidden');  // a new ballot: an older link's notice no longer applies (#40)\n")

# ---------- #37: the data goes in last
sw(B, "        html = strip_desk(html)\n    html = html.replace(\"__DATA__\", data)\n", "        html = strip_desk(html)\n")
sw(B, "    return html.replace(\"<!--ANALYTICS-->\", analytics)\n",
      "    html = html.replace(\"<!--ANALYTICS-->\", analytics)\n"
      "    # The data goes in last, so nothing in it can be mistaken for one of the placeholders above (#37).\n"
      "    return html.replace(\"__DATA__\", data, 1)\n")

# ---------- #41: the mutation runner restores the original on any stop signal, and importing it starts nothing
sw(MD, """def _stop(sig, _frame):                                    # a timeout's kill still runs the restore in `finally` (Pass 1);
    for s_ in (signal.SIGTERM, signal.SIGHUP): signal.signal(s_, signal.SIG_IGN)   # a second signal can't interrupt it (Pass 2)
    sys.exit(128 + sig)
signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGHUP, _stop)
def put(f, text):                                          # write whole or not at all: never a half-written page
    tmp = f.with_name(f.name + '.mutate-tmp'); tmp.write_text(text, encoding='utf-8'); os.replace(tmp, f)
""", """SIGS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)
PENDING = []                                               # (file, original text) while a mutant may be on disk
def _stop(sig, _frame):                                    # Ctrl-C, a kill or a hang-up: put the original back, then exit (#41);
    for s_ in SIGS: signal.signal(s_, signal.SIG_IGN)     # a second signal can't interrupt the restore
    for f_, t_ in PENDING: put(f_, t_)
    sys.exit(128 + sig)
for s_ in SIGS: signal.signal(s_, _stop)
def put(f, text):                                          # write whole or not at all: never a half-written page; a signal
    old = signal.pthread_sigmask(signal.SIG_BLOCK, SIGS)  # arriving meanwhile waits until the file is whole (#41)
    try:
        tmp = f.with_name(f.name + '.mutate-tmp'); tmp.write_text(text, encoding='utf-8'); os.replace(tmp, f)
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old)
""")
sw(MD, """if len(sys.argv) > 2: M = M[int(sys.argv[1]):int(sys.argv[2])]   # run the list in slices if a shell caps how long a command may take
for name, f, a, z, tests in M:                                   # a stale anchor fails in a second, not after the baseline (audit #27)
    assert f.read_text(encoding='utf-8').count(a) == 1, (name, 'anchor found', f.read_text(encoding='utf-8').count(a), 'times in', f.name)
srv = T.serve(); res = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        # A kill only means something if the same tests pass without the mutant (a county outage fails them all).
        for tn in sorted({t for m in M for t in m[4]}):
            getattr(T, tn)(b)
        print('baseline: every target test passes unmutated', flush=True)
        for name, f, a, z, tests in M:
            orig = f.read_text(encoding='utf-8')
            assert orig.count(a) == 1, (name, 'anchor found', orig.count(a), 'times')
            try:
                put(f, orig.replace(a, z))
                killed = []
                for tn in tests:
                    try: getattr(T, tn)(b)
                    except Exception as e: killed.append(tn + ':' + type(e).__name__)   # AssertionError, or a Playwright timeout
                res.append((name, 'KILLED' if killed else 'SURVIVED', ','.join(killed)))
            finally:
                put(f, orig)
            # A kill counts only if the same tests pass again on the restored file (a service hiccup fails both).
            for tn in [k.split(':')[0] for k in killed]:
                try: getattr(T, tn)(b)
                except Exception as e: raise SystemExit(f'INCONCLUSIVE {name}: {tn} also fails unmutated ({type(e).__name__}); rerun later')
            print(*res[-1], flush=True)
        b.close()
finally:
    srv.shutdown()
print(sum(r[1] == 'KILLED' for r in res), 'of', len(res), 'mutants killed')
""", """def main(M):
    if len(sys.argv) > 2: M = M[int(sys.argv[1]):int(sys.argv[2])]   # run the list in slices if a shell caps how long a command may take
    for name, f, a, z, tests in M:                                   # a stale anchor fails in a second, not after the baseline (audit #27)
        assert f.read_text(encoding='utf-8').count(a) == 1, (name, 'anchor found', f.read_text(encoding='utf-8').count(a), 'times in', f.name)
    srv = T.serve(); res = []
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            # A kill only means something if the same tests pass without the mutant (a county outage fails them all).
            for tn in sorted({t for m in M for t in m[4]}):
                getattr(T, tn)(b)
            print('baseline: every target test passes unmutated', flush=True)
            for name, f, a, z, tests in M:
                orig = f.read_text(encoding='utf-8')
                assert orig.count(a) == 1, (name, 'anchor found', orig.count(a), 'times')
                PENDING.append((f, orig))                            # from here until the restore, a stop signal restores first (#41)
                try:
                    put(f, orig.replace(a, z))
                    killed = []
                    for tn in tests:
                        try: getattr(T, tn)(b)
                        except Exception as e: killed.append(tn + ':' + type(e).__name__)   # AssertionError, or a Playwright timeout
                    res.append((name, 'KILLED' if killed else 'SURVIVED', ','.join(killed)))
                finally:
                    put(f, orig); PENDING.clear()
                # A kill counts only if the same tests pass again on the restored file (a service hiccup fails both).
                for tn in [k.split(':')[0] for k in killed]:
                    try: getattr(T, tn)(b)
                    except Exception as e: raise SystemExit(f'INCONCLUSIVE {name}: {tn} also fails unmutated ({type(e).__name__}); rerun later')
                print(*res[-1], flush=True)
            b.close()
    finally:
        srv.shutdown()
    print(sum(r[1] == 'KILLED' for r in res), 'of', len(res), 'mutants killed')

if __name__ == '__main__':                                       # importing the runner (its own test does) starts nothing (#41)
    main(M)
""")

s = files[T]
assert 'NOW' not in s, 'a frozen NOW is left'
for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
print('fixes A applied to', ', '.join(files))
```

## Script: edits_mutants_A.py

```python
"""Issues round, commit A: mutants for every fix (each must turn a named test red). Run from the repo root after the
fixes:  python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
MD = ROOT / 'tests/mutate_desk.py'
m = MD.read_text(encoding='utf-8')
def sw(a, z):
    global m
    if m.count(a) != 1: sys.exit(f'mutate_desk.py: FIND occurs {m.count(a)} times: {a[:70]!r}')
    m = m.replace(a, z)
# F5's anchor moved: a key pick is announced only when it went through (#33).
sw(""" ('F5 picks by key not announced', PREV, 'pick(b.c.id, o); announce(b.c);', 'pick(b.c.id, o);', ['desk_launch_audit_fixes']),""",
   """ ('F5 picks by key not announced', PREV, 'if (pick(b.c.id, o) !== false) announce(b.c);', 'pick(b.c.id, o);', ['desk_launch_audit_fixes']),""")
J = 'MD_SELF'
NEW = [
 ('A1 non-text reasons kept', 'PREV', "Object.entries(plain(LS.get('ballotta.whys', {}))).filter(([, v]) => typeof v === 'string')", "Object.entries(plain(LS.get('ballotta.whys', {})))", ['stored_junk_never_breaks_keep_or_share']),
 ('A2 stored picks not checked', 'PREV', "let picks = plain(LS.get('ballotta.picks', {}))", "let picks = LS.get('ballotta.picks', {})", ['stored_junk_never_breaks_keep_or_share']),
 ('A3 look-alike letters ignored', 'PREV', '.map(ch => LOOKALIKE[ch] || ch)', '.map(ch => ch)', ['share_names_block_lookalikes_and_nicknames']),
 ('A4 digits for letters ignored', 'PREV', ' || hit(low.replace(/[013457$@|]/g, ch => LEET[ch]))', '', ['share_names_block_lookalikes_and_nicknames']),
 ('A5 party nicknames allowed', 'PREV', '|gop|dems?|repubs?|rnc|dnc)', '|gop)', ['share_names_block_lookalikes_and_nicknames']),
 ('A6 names checked only with digits as letters', 'PREV', 'return hit(low) || hit(', 'return hit(', ['audit_a5_a8_a12_hostile_share']),
 ('A7 focus ring clipped again', 'PREV', 'text-overflow:ellipsis;min-width:0;padding:4px;margin:-4px}', 'text-overflow:ellipsis;min-width:0}', ['desk_change_link_focus_ring_is_whole']),
 ('A8 long names push the phone page sideways', 'PREV', '#friend h2,#friend .note,#friend .fp,#compare h2,#compare .note,#compare .cmp,#compare .lead{overflow-wrap:anywhere}', '', ['friend_card_long_names_and_honest_copy']),
 ('A9 long names push the laptop page sideways', 'PREV', '  .dk-fcta,.dk-fchip,.dk-fbox,.dk-fp{overflow-wrap:anywhere;min-width:0}  /* #23 */\n', '', ['friend_card_long_names_and_honest_copy']),
 ('A10 friend card overclaims', 'PREV', 'Most races on your ballot link to neutral sources.', 'Each race on your ballot links to neutral sources.', ['friend_card_long_names_and_honest_copy']),
 ('A11 friend pick unnamed in the rail', 'PREV', """<span class="dk-vh">' + esc(friendName()) + ' picked ' + fp + '</span>""", '', ['desk_friend_pick_in_rail_has_a_name']),
 ('A12 rail initial read out', 'PREV', """ aria-hidden="true" title="' + possessive() + ' pick: ' + fp""", """ title="' + possessive() + ' pick: ' + fp""", ['desk_friend_pick_in_rail_has_a_name']),
 ('A13 extra pick accepted', 'PREV', '    if (!cur.includes(val) && cur.length >= n) { limitNote(cid, n); return false; }  // already N picks: say why nothing changed (#33)\n', '', ['extra_pick_is_explained']),
 ('A14 extra pick refused silently', 'PREV', '{ limitNote(cid, n); return false; }', '{ return false; }', ['extra_pick_is_explained']),
 ('A15 limit note never clears', 'PREV', '  limitNote(cid, 0);\n  picks[cid] = cur;', '  picks[cid] = cur;', ['extra_pick_is_explained']),
 ('A16 refused key pick announced', 'PREV', 'if (pick(b.c.id, o) !== false) announce(b.c);', 'pick(b.c.id, o); announce(b.c);', ['extra_pick_is_explained']),
 ('A17 limit note not a status', 'PREV', """data-limit="' + c.id + '" role="status"></span>' : '') + '</p>';""", """data-limit="' + c.id + '"></span>' : '') + '</p>';""", ['extra_pick_is_explained']),
 ('A18 no check for a new day', 'PREV', 'setInterval(dayCheck, 60000);\n', '', ['dates_move_on_in_a_tab_left_open']),
 ('A19 chosen period overridden', 'PREV', '  if (!periodChosen) period = defaultPeriod();\n', '  period = defaultPeriod();\n', ['dates_move_on_in_a_tab_left_open']),
 ('A20 tab choice forgotten', 'PREV', "period = 'early'; periodChosen = true; renderVote();", "period = 'early'; renderVote();", ['dates_move_on_in_a_tab_left_open']),
 ('A21 laptop header keeps the old day', 'PREV', "  renderVote();/*DESK*/ if (window.desk) try { desk.render(); } catch (e) {}/*/DESK*/\n}\ndocument.addEventListener('visibilitychange'", "  renderVote();\n}\ndocument.addEventListener('visibilitychange'", ['dates_move_on_in_a_tab_left_open']),
 ('A22 date frozen at load', 'PREV', 'const today = () => new Date();', 'const FROZEN = new Date(), today = () => FROZEN;', ['dates_move_on_in_a_tab_left_open']),
 ('A23 data inserted first', 'BLD', '        html = strip_desk(html)\n', '        html = strip_desk(html)\n    html = html.replace("__DATA__", data)\n', ['build_inserts_data_last']),
 ('A24 moves not announced', 'PREV', 'where(curB()); }', '}', ['desk_moves_are_announced']),
 ('A25 contest number off by one', 'PREV', "'Contest ' + (idx(b.c.id) + 1)", "'Contest ' + idx(b.c.id)", ['desk_moves_are_announced']),
 ('A26 old link notice survives a new ballot', 'PREV', "      $('dk-say').classList.add('hidden');  // a new ballot: an older link's notice no longer applies (#40)\n", '', ['desk_old_link_warning_gone_after_new_lookup']),
 ('A27 a stop signal leaves the mutant', J, '    for f_, t_ in PENDING: put(f_, t_)\n', '', ['mutation_runner_restores_on_any_signal']),
 ('A28 Ctrl-C not handled', J, 'SIGS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)\nPENDING', 'SIGS = (signal.SIGTERM, signal.SIGHUP)\nPENDING', ['mutation_runner_restores_on_any_signal']),
 ('A29 importing the runner starts a run', J, "\nif __name__ == '__main__':", '\nif True:', ['mutation_runner_restores_on_any_signal']),
 ('A30 footer button never shown', 'PREV', "  const f = $('reset-all-foot'); if (f) f.classList.toggle('hidden', !has);\n", '', ['phone_can_clear_everything_from_the_footer']),
 ('A31 footer button not wired', 'PREV', "$('reset-all-foot').addEventListener('click', clearEverything);", '', ['phone_can_clear_everything_from_the_footer']),
 ('A32 a lookup does not show the footer button', 'PREV', 'localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} footClear(); }', 'localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }', ['phone_can_clear_everything_from_the_footer']),
 ('A33 a later visit hides the footer button', 'PREV', '  footClear();  // a link opened before this script ran is already in sessionStorage\n', '', ['phone_can_clear_everything_from_the_footer']),
]
i = m.index('\n]\n')
m = m[:i] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in NEW).rstrip('\n') + '\n]\n' + m[i + 3:]
sw("README = ROOT / 'README.md'\n", "README = ROOT / 'README.md'\nMD_SELF = ROOT / 'tests/mutate_desk.py'                    # the runner's own signal handling (#41), tested in a child process\n")
MD.write_text(m, encoding='utf-8')
print('mutants A added:', len(NEW))
```

## Script: rework_A1.py

```python
"""Issues round, commit A: rework after remediation-audit Pass 1. Run from the repo root after edits_tests_A.py,
edits_page_A.py and edits_mutants_A.py:  python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
T, TS, MD = 'source/template-travis.html', 'tests/test_site.py', 'tests/mutate_desk.py'
files = {}
def sw(path, a, z):
    s = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
    if s.count(a) != 1: sys.exit(f'{path}: FIND occurs {s.count(a)} times: {a[:80]!r}')
    files[path] = s.replace(a, z)

# ---- P1-1: a new day redraws only what shows the date; never a redraw that takes focus from the visitor
sw(T, "  renderVote();/*DESK*/ if (window.desk) try { desk.render(); } catch (e) {}/*/DESK*/\n}\ndocument.addEventListener('visibilitychange'",
      "  renderVote();/*DESK*/ if (window.desk) try { desk.today(); } catch (e) {}/*/DESK*/  // only what shows the date: a full redraw would take focus from a reason being typed (Pass 1)\n}\ndocument.addEventListener('visibilitychange'")
sw(T, "    cribOpts: () => ({ two_col: ui.two ? 'yes' : 'no', hide_unopposed: ui.hideCrib ? 'yes' : 'no' }),\n",
      "    cribOpts: () => ({ two_col: ui.two ? 'yes' : 'no', hide_unopposed: ui.hideCrib ? 'yes' : 'no' }),\n"
      "    today() {  // a new day (#34): the header's line, and the vote view's hours if it's open; the paper and its focus stay as they are\n"
      "      $('dk-when').textContent = whenLine();\n"
      "      if (ui.view === 'vote' && document.body.classList.contains('dk-app-on')) viewVote();\n"
      "    },\n")

# ---- P1-2/3: safeName checks words with punctuation removed AND as spaces, spaced-out initials, 1 as l or i,
# and a few more look-alikes
sw(T, "const RESERVED = /league|lwv|voter|vote411|county|", "const RESERVED = /league|lwv|voter|vote411|voteall|voteail|county|")
sw(T, "  'ᴏ': 'o', 'ᴘ': 'p', 'ʀ': 'r', 'ꜱ': 's', 'ᴛ': 't', 'ᴜ': 'u', 'ᴠ': 'v', 'ᴡ': 'w', 'ʏ': 'y', 'ᴢ': 'z' };",
      "  'ᴏ': 'o', 'ᴘ': 'p', 'ʀ': 'r', 'ꜱ': 's', 'ᴛ': 't', 'ᴜ': 'u', 'ᴠ': 'v', 'ᴡ': 'w', 'ʏ': 'y', 'ᴢ': 'z', 'ɡ': 'g', 'ɑ': 'a', 'ı': 'i' };")
sw(T, "const LEET = { '0': 'o', '1': 'l', '3': 'e', '4': 'a', '5': 's', '7': 't', '$': 's', '@': 'a', '|': 'l' };  // checked both ways: \"Vote411\" stays blocked",
      "const LEET = { '0': 'o', '1': 'l', '3': 'e', '4': 'a', '5': 's', '6': 'g', '7': 't', '$': 's', '@': 'a', '|': 'l' };  // checked as written and as letters (1 as l, then as i)")
sw(T, """  const hit = (t) => RESERVED.test(t.replace(/[\\s\\p{P}\\p{S}]/gu, '')) || RESERVED_WORDS.test(t.replace(/\\p{P}/gu, ''));
  return hit(low) || hit(low.replace(/[013457$@|]/g, ch => LEET[ch])) ? '' : n;""",
"""  // Words are tested with punctuation removed ("G.O.P.") and as spaces ("Travis-GOP"), and with spaced-out single
  // letters joined ("G O P") (Pass 1).
  const words = (t) => [t.replace(/\\p{P}/gu, ''), t.replace(/\\p{P}/gu, ' ').replace(/(?<=(^|\\s)\\S)\\s(?=\\S(\\s|$))/gu, '')];
  const hit = (t) => RESERVED.test(t.replace(/[\\s\\p{P}\\p{S}]/gu, '')) || words(t).some(w => RESERVED_WORDS.test(w));
  const leet = low.replace(/[0134567$@|]/g, ch => LEET[ch]);
  return hit(low) || hit(leet) || hit(leet.replace(/l/g, (ch, i) => /[0-9]/.test(low[i]) ? 'i' : ch)) ? '' : n;""")

# ---- P1-4: Clear my picks clears any "You can pick up to N" note too
sw(T, "track('cleared', { what: 'picks' }); picks = {}; whys = {};",
      "track('cleared', { what: 'picks' }); document.querySelectorAll('[data-limit]').forEach(s => { s.textContent = ''; }); picks = {}; whys = {};")

# ---- P1-5: another tab saving or clearing updates the footer button
sw(T, "// Clear everything in another tab: this tab's copy is stale, so start fresh instead of writing it back.\n",
      "window.addEventListener('storage', () => footClear());  // another tab saved something: the footer button follows (Pass 1)\n"
      "// Clear everything in another tab: this tab's copy is stale, so start fresh instead of writing it back.\n")

# ---- tests
sw(TS, """                'RNC', 'DNC Texas', 'L3ague', 'C0unty Clerk', 'ΟFFICIAL', 'Тravis Сounty Еlections', 'ᴠᴏᴛᴇʀ ɪɴꜰᴏ', 'Ballοtta']:""",
       """                'RNC', 'DNC Texas', 'L3ague', 'C0unty Clerk', 'ΟFFICIAL', 'Тravis Сounty Еlections', 'ᴠᴏᴛᴇʀ ɪɴꜰᴏ', 'Ballοtta',
                'Travis-GOP', 'Tea-Party', 'Site-Admin', 'TX.State', 'Austin/Dems', 'G O P', 'D N C', 'V0te411', 'VOTE 4ll',   # Pass 1
                'Off1cial', 'C1ty of Austin', 'L1bertarian', 'ɡop', '6OP']:""")
sw(TS, """    for good in ['Maya', 'Ana', 'José', "O'Brien", 'Dempsey', 'Ελένη', 'Ольга', '李明', 'Demetria', 'Gopal']:""",
       """    for good in ['Maya', 'Ana', 'José', "O'Brien", 'Dempsey', 'Ελένη', 'Ольга', '李明', 'Demetria', 'Gopal', 'Mary-Jane', 'Jean-Paul', 'A J', 'Liz 2']:""")
sw(TS, """        line(0).click(); expect(note).to_have_text('')
        line(2).click(); assert pg.evaluate("current('c113')") == [opts[1], opts[2]]
        ctx.close()""",
       """        line(0).click(); expect(note).to_have_text('')
        line(2).click(); assert pg.evaluate("current('c113')") == [opts[1], opts[2]]
        if not wide:                                                               # Clear my picks clears the note too (Pass 1)
            line(0).click(); expect(note).to_have_text(msg)
            pg.once('dialog', lambda d: d.accept()); pg.click('#reset')
            assert pg.evaluate("current('c113')") == []; expect(note).to_have_text('')
        ctx.close()""")
sw(TS, """        if wide: assert pg.text_content('#dk-when') == 'Election Day is Tue Nov 3 · 7am–7pm', pg.text_content('#dk-when')
        ctx.close()""",
       """        if wide: assert pg.text_content('#dk-when') == 'Election Day is Tue Nov 3 · 7am–7pm', pg.text_content('#dk-when')
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
        ctx.close()""")
sw(TS, """    lookup(pg); expect(foot).to_be_visible()                                   # shown as soon as a lookup saves the ballot""",
       """    other = ctx.new_page(); other.goto(BASE); other.evaluate("localStorage.setItem('ballotta.name', JSON.stringify('Maya'))")
    expect(foot).to_be_visible(); other.close()                                # another tab saved something (Pass 1)
    pg.evaluate("localStorage.removeItem('ballotta.name'); document.getElementById('reset-all-foot').classList.add('hidden')")
    lookup(pg); expect(foot).to_be_visible()                                   # shown as soon as a lookup saves the ballot""")

# ---- Lane (Oct 15, 18:12): the laptop's left-column Print opens the Crib sheet view instead of printing straight away,
# so the print options (reasons, two columns, hide unopposed) aren't skipped
sw(T, "  $('dk-print').addEventListener('click', () => $('print').click());",
      "  $('dk-print').addEventListener('click', () => { setView('crib'); track('view_opened', { view: 'crib' }); });  // the print options live there (Lane, Oct 15)")
sw(TS, "    pg.click('#dk-c2'); pg.evaluate('window.print = () => {}'); pg.click('#dk-print')",
       "    pg.click('#dk-c2'); pg.evaluate('window.print = () => {}'); pg.click('#dk-notes [data-act=\"print\"]')")
sw(TS, "\ndef main():", """
@desk_test
def desk_print_button_opens_the_crib_sheet(b):
    # Lane (Oct 15): the left column's Print opens the Crib sheet view (with its print options); it doesn't print.
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.evaluate('() => { window.__printed = 0; window.print = () => { window.__printed++; }; }')   # a function: a bare assignment string would be called once by evaluate
    pg.click('#dk-print')
    assert pg.get_attribute('#dk-views [data-view="crib"]', 'aria-current') == 'page'
    assert pg.locator('#dk-notes #dk-c2').count() == 1 and pg.evaluate('window.__printed') == 0
    assert 'crib_printed' not in names(pg) and events(pg)[-1] == ['view_opened', {'view': 'crib', 'layout': 'laptop'}], events(pg)[-1]
    pg.click('#dk-notes [data-act="print"]')
    assert pg.evaluate('window.__printed') == 1 and events(pg)[-1][0] == 'crib_printed'
    ctx.close()

def main():""")

# ---- mutants
sw(MD, """ ('A21 laptop header keeps the old day', PREV, "  renderVote();/*DESK*/ if (window.desk) try { desk.render(); } catch (e) {}/*/DESK*/\\n}\\ndocument.addEventListener('visibilitychange'", "  renderVote();\\n}\\ndocument.addEventListener('visibilitychange'", ['dates_move_on_in_a_tab_left_open']),""",
       """ ('A21 laptop header keeps the old day', PREV, "      $('dk-when').textContent = whenLine();\\n      if (ui.view === 'vote'", "      if (ui.view === 'vote'", ['dates_move_on_in_a_tab_left_open']),""")
m = files[MD]; i = m.index('\n]\n')
NEW = [
 ('R1 a new day redraws the whole laptop page', 'PREV', 'desk.today(); } catch (e) {}/*/DESK*/  // only what shows the date', 'desk.render(); } catch (e) {}/*/DESK*/  // only what shows the date', ['dates_move_on_in_a_tab_left_open']),
 ('R2 hyphen-joined words get through', 'PREV', "t.replace(/\\p{P}/gu, ' ').replace(/(?<=", "t.replace(/\\p{P}/gu, '').replace(/(?<=", ['share_names_block_lookalikes_and_nicknames']),
 ('R3b spaced-out initials not joined', 'PREV', ".replace(/(?<=(^|\\s)\\S)\\s(?=\\S(\\s|$))/gu, '')]", ']', ['share_names_block_lookalikes_and_nicknames']),
 ('P1 laptop Print prints straight away', 'PREV', "$('dk-print').addEventListener('click', () => { setView('crib'); track('view_opened', { view: 'crib' }); });", "$('dk-print').addEventListener('click', () => $('print').click());", ['desk_print_button_opens_the_crib_sheet']),
 ('P2 laptop Print not counted as a view', 'PREV', "setView('crib'); track('view_opened', { view: 'crib' }); });", "setView('crib'); });", ['desk_print_button_opens_the_crib_sheet']),
 ('R4 1 never read as i', 'PREV', " || hit(leet.replace(/l/g, (ch, i) => /[0-9]/.test(low[i]) ? 'i' : ch))", '', ['share_names_block_lookalikes_and_nicknames']),
 ('R5 Clear my picks leaves the limit note', 'PREV', " document.querySelectorAll('[data-limit]').forEach(s => { s.textContent = ''; }); picks = {};", ' picks = {};', ['extra_pick_is_explained']),
 ('R6 another tab leaves the footer button stale', 'PREV', "window.addEventListener('storage', () => footClear());", '', ['phone_can_clear_everything_from_the_footer']),
]
m = m[:i] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in NEW).rstrip('\n') + '\n]\n' + m[i + 3:]
files[MD] = m
for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
print('rework A1 applied to', ', '.join(files))
```

## Script: rework_A2.py

```python
"""Issues round, commit A: rework after remediation-audit Pass 2. Run from the repo root after rework_A1.py:
    python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
T, TS, MD = 'source/template-travis.html', 'tests/test_site.py', 'tests/mutate_desk.py'
files = {}
def sw(path, a, z):
    s = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
    if s.count(a) != 1: sys.exit(f'{path}: FIND occurs {s.count(a)} times: {a[:80]!r}')
    files[path] = s.replace(a, z)

# ---- P2-F1/F2/F3: one fold for every group of characters that stand in for one another, applied to the name and the
# reserved words alike; words checked with punctuation AND symbols as spaces (runs of spaces collapsed)
s = files.setdefault(T, (ROOT / T).read_text(encoding='utf-8'))
a, z = '// A share link is made by anyone', '\nfunction friendName()'
assert s.count(a) == 1 and s.count(z) == 1
i, j = s.index(a), s.index(z)
old = s[i:j]
look = old[old.index('const LOOKALIKE = {'):old.index('};', old.index('const LOOKALIKE = {')) + 2]
NEW = r"""// A share link is made by anyone, so a name can't claim to be an organization, a party or Ballotta itself.
// Best effort only; the "Ballotta doesn't endorse anyone" copy is the real guard. The name shown is never changed:
// only a folded copy is checked (#21). Look-alike letters from other alphabets (Cyrillic а, Greek ο, small-capital ʟ…)
// become the Latin letters they imitate; then each group of characters that stand in for one another (1 l i | !,
// 0 o, 3 e, 4 @ a, 5 $ s, 6 g, 7 t) becomes one letter, in the name and in the reserved words alike, so any mix
// matches ("E1ect1on", "Vote41I"). Checked as one run of letters (spaces, punctuation and symbols removed) and word by
// word (punctuation and symbols as spaces; spaced-out single letters like "G. O. P." joined), with | ! $ @ read both as
// letters and as nothing. A hyphenated part that is a reserved word ("Mo-Dem") is blocked too: rare, accepted (Pass 2).
""" + look + r"""
const FOLD = { '1': 'l', 'i': 'l', '|': 'l', '!': 'l', '0': 'o', '3': 'e', '4': 'a', '@': 'a', '5': 's', '$': 's', '6': 'g', '7': 't' };
const fold = (t) => t.replace(/[1i|!03456@$7]/g, ch => FOLD[ch]);
const RESERVED = new RegExp(['league', 'lwv', 'voter', 'vote411', 'county', 'clerk', 'official', 'ballotta', 'cityof', 'villageof', 'election',
  'government', 'democrat', 'republican', 'libertarian', 'greenparty', 'taxoffice', 'campaign', 'secretaryofstate'].map(fold).join('|'));
const RESERVED_WORDS = new RegExp('\\b(' + ['state', 'party', 'admin', 'gop', 'dems?', 'repubs?', 'rnc', 'dnc'].map(fold).join('|') + ')\\b');
function safeName(n) {
  if (typeof n !== 'string') return '';
  n = n.normalize('NFKC').replace(/[\p{Cc}\p{Cf}\p{Default_Ignorable_Code_Point}]/gu, '').replace(/\s+/g, ' ').trim().slice(0, 30);
  const low = [...n.normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase()].map(ch => LOOKALIKE[ch] || ch).join('');
  const run = (t) => t.replace(/[\s\p{P}\p{S}]/gu, '');
  const words = (t) => {
    const w = t.replace(/[\p{P}\p{S}]/gu, ' ').replace(/\s+/g, ' ').trim();
    return [t.replace(/[\p{P}\p{S}]/gu, ''), w, w.replace(/(?<=(^|\s)\S)\s(?=\S(\s|$))/gu, '')];
  };
  const forms = [fold(low), fold(low.replace(/[|!$@]/g, ''))];
  return forms.some(t => RESERVED.test(run(t)) || words(t).some(x => RESERVED_WORDS.test(x))) ? '' : n;
}"""
files[T] = s[:i] + NEW + s[j:]

# ---- P2-F5: the laptop's Print… opens the crib view once, and puts keyboard focus on the real Print button
sw(T, '<button type="button" id="dk-print">Print</button>', '<button type="button" id="dk-print">Print…</button>')
sw(T, "  $('dk-print').addEventListener('click', () => { setView('crib'); track('view_opened', { view: 'crib' }); });  // the print options live there (Lane, Oct 15)",
      "  $('dk-print').addEventListener('click', () => {  // opens the crib view, where the print options are (Lane, Oct 15)\n"
      "    if (ui.view !== 'crib') { setView('crib'); track('view_opened', { view: 'crib' }); }\n"
      "    const pr = N().querySelector('[data-act=\"print\"]'); if (pr) pr.focus({ preventScroll: true });  // keyboard users land on the real Print button (Pass 2)\n"
      "  });")

# ---- P2-F6: a new day re-draws an open vote view but keeps the visitor's place in it
sw(T, "      $('dk-when').textContent = whenLine();\n      if (ui.view === 'vote' && document.body.classList.contains('dk-app-on')) viewVote();\n",
      "      $('dk-when').textContent = whenLine();\n"
      "      if (ui.view !== 'vote' || !document.body.classList.contains('dk-app-on')) return;\n"
      "      const a = document.activeElement, sel = a && P().contains(a) ? (a.dataset.period ? '[data-period=\"' + a.dataset.period + '\"]' : a.id ? '#' + a.id : '') : '';\n"
      "      viewVote();\n"
      "      const back = sel && P().querySelector(sel); if (back) back.focus({ preventScroll: true });  // keep the visitor's place (Pass 2)\n")

# ---- tests
sw(TS, """                'Off1cial', 'C1ty of Austin', 'L1bertarian', 'ɡop', '6OP']:""",
       """                'Off1cial', 'C1ty of Austin', 'L1bertarian', 'ɡop', '6OP',
                'E1ect1on Info', 'Off1c1a1', 'Vote41I', 'VOTE4II', 'G. O. P.', 'D. N. C.', 'G+O+P', 'G~O~P', 'D^E^M^S', 'Off!cial', 'Ad|min']:   # Pass 2""")
sw(TS, """'Gopal', 'Mary-Jane', 'Jean-Paul', 'A J', 'Liz 2']:""",
       """'Gopal', 'Mary-Jane', 'Jean-Paul', 'A J', 'Liz 2',
                 'J R R Tolkien', 'A.J.', 'D J', 'R2-D2', "D'Angelo", 'Estate Jones', 'G O Pal', 'Işıl Yılmaz', 'Partyka', 'Admina']:""")
sw(TS, """    pg.evaluate('() => { window.__printed = 0; window.print = () => { window.__printed++; }; }')   # a function: a bare assignment string would be called once by evaluate
    pg.click('#dk-print')
    assert pg.get_attribute('#dk-views [data-view="crib"]', 'aria-current') == 'page'
    assert pg.locator('#dk-notes #dk-c2').count() == 1 and pg.evaluate('window.__printed') == 0
    assert 'crib_printed' not in names(pg) and events(pg)[-1] == ['view_opened', {'view': 'crib', 'layout': 'laptop'}], events(pg)[-1]""",
       """    pg.evaluate('() => { window.__printed = 0; window.print = () => { window.__printed++; }; }')   # a function: a bare assignment string would be called once by evaluate
    assert pg.text_content('#dk-print') == 'Print…'                                # it opens options: an ellipsis (Pass 2)
    pg.focus('#dk-print'); pg.keyboard.press('Enter')
    assert pg.get_attribute('#dk-views [data-view="crib"]', 'aria-current') == 'page'
    assert pg.locator('#dk-notes #dk-c2').count() == 1 and pg.evaluate('window.__printed') == 0
    assert pg.evaluate('document.activeElement.dataset.act') == 'print', 'keyboard users land on the real Print button (Pass 2)'
    assert 'crib_printed' not in names(pg) and events(pg)[-1] == ['view_opened', {'view': 'crib', 'layout': 'laptop'}], events(pg)[-1]
    pg.focus('#dk-print'); pg.keyboard.press('Enter')                              # already there: not counted again (Pass 2)
    assert [e[1].get('view') for e in events(pg) if e[0] == 'view_opened'] == ['crib'], events(pg)""")
sw(TS, """        assert pg.evaluate('JSON.stringify(picks)') == '{}', pg.evaluate('JSON.stringify(picks)')
        ctx.close()""",
       """        assert pg.evaluate('JSON.stringify(picks)') == '{}', pg.evaluate('JSON.stringify(picks)')
        ctx.close()
        # In the vote view, the new day re-draws the hours but keeps the visitor's place (Pass 2).
        ctx, pg = new_page(b, wide=True); pg.clock.install(time=dt.datetime(2026, 10, 30, 23, 58)); pg.goto(BASE)
        pg.evaluate('s => localStorage.setItem("ballotta.ballot", s)', st); pg.reload(); pg.wait_for_selector('body.dk-app-on')
        pg.click('#dk-views [data-view="vote"]'); pg.focus('#dk-paper [data-period="early"]')
        pg.clock.run_for(5 * 60 * 1000)
        assert pg.get_attribute('#dk-paper [data-period="eday"]', 'aria-pressed') == 'true', 'the vote view moved on to Election Day'
        assert pg.evaluate('document.activeElement.dataset.period') == 'early', pg.evaluate('document.activeElement.tagName')
        ctx.close()""")

# ---- mutants: the name block was rewritten, so its mutants are re-anchored; new ones for this pass
m = files.setdefault(MD, (ROOT / MD).read_text(encoding='utf-8'))
for pre in ("('A4 ", "('A5 ", "('A6 ", "('R2 ", "('R3b ", "('R4 "):
    hits = [l for l in m.split('\n') if l.startswith(' ' + pre)]
    assert len(hits) == 1, pre
    m = m.replace(hits[0] + '\n', '')
NEWM = [
 ('A4 stand-ins not folded', 'PREV', "const fold = (t) => t.replace(/[1i|!03456@$7]/g, ch => FOLD[ch]);", "const fold = (t) => t;", ['share_names_block_lookalikes_and_nicknames']),
 ('A5 party nicknames allowed', 'PREV', "'gop', 'dems?', 'repubs?', 'rnc', 'dnc']", "'gop']", ['share_names_block_lookalikes_and_nicknames']),
 ('A6 symbols read only as letters', 'PREV', ", fold(low.replace(/[|!$@]/g, ''))]", "]", ['share_names_block_lookalikes_and_nicknames']),
 ('R2 hyphen-joined words get through', 'PREV', "const w = t.replace(/[\\p{P}\\p{S}]/gu, ' ')", "const w = t.replace(/[\\p{P}\\p{S}]/gu, '')", ['share_names_block_lookalikes_and_nicknames']),
 ('R3b spaced-out initials not joined', 'PREV', ", w.replace(/(?<=(^|\\s)\\S)\\s(?=\\S(\\s|$))/gu, '')]", ']', ['share_names_block_lookalikes_and_nicknames']),
 ('R7 reserved words not folded', 'PREV', "'secretaryofstate'].map(fold).join('|'));", "'secretaryofstate'].join('|'));", ['share_names_block_lookalikes_and_nicknames', 'audit_a5_a8_a12_hostile_share']),
 ('R8 runs of spaces not collapsed', 'PREV', " ' ').replace(/\\s+/g, ' ').trim();", " ' ');", ['share_names_block_lookalikes_and_nicknames']),
 ('R9 symbols between letters ignored', 'PREV', "const w = t.replace(/[\\p{P}\\p{S}]/gu, ' ')", "const w = t.replace(/\\p{P}/gu, ' ')", ['share_names_block_lookalikes_and_nicknames']),
 ('R10 Print… leaves focus behind', 'PREV', "    const pr = N().querySelector('[data-act=\"print\"]'); if (pr) pr.focus({ preventScroll: true });", '', ['desk_print_button_opens_the_crib_sheet']),
 ('R11 Print… counted twice', 'PREV', "    if (ui.view !== 'crib') { setView('crib'); track('view_opened', { view: 'crib' }); }", "    setView('crib'); track('view_opened', { view: 'crib' });", ['desk_print_button_opens_the_crib_sheet']),
 ('R12 new day loses the vote-view place', 'PREV', "      const back = sel && P().querySelector(sel); if (back) back.focus({ preventScroll: true });", '', ['dates_move_on_in_a_tab_left_open']),
]
k = m.index('\n]\n')
m = m[:k] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in NEWM).rstrip('\n') + '\n]\n' + m[k + 3:]
for pre in ("('P1 ", "('P2 "):   # Lane's Print change: the handler is now several lines
    hits = [l for l in m.split('\n') if l.startswith(' ' + pre)]
    assert len(hits) == 1, pre
    m = m.replace(hits[0] + '\n', '')
k = m.index('\n]\n')
m = m[:k] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in [
 ('P1 laptop Print… prints straight away', 'PREV', "    if (ui.view !== 'crib') { setView('crib'); track('view_opened', { view: 'crib' }); }\n    const pr", "    $('print').click(); return;\n    const pr", ['desk_print_button_opens_the_crib_sheet']),
 ('P2 laptop Print… not counted as a view', 'PREV', "{ setView('crib'); track('view_opened', { view: 'crib' }); }", "{ setView('crib'); }", ['desk_print_button_opens_the_crib_sheet']),
]).rstrip('\n') + '\n]\n' + m[k + 3:]
files[MD] = m
for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
print('rework A2 applied to', ', '.join(files))
```

## Script: rework_A3.py

```python
"""Issues round, commit A: rework after remediation-audit Pass 3. Run from the repo root after rework_A2.py:
    python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
T, TS, MD = 'source/template-travis.html', 'tests/test_site.py', 'tests/mutate_desk.py'
files = {}
def sw(path, a, z):
    s = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
    if s.count(a) != 1: sys.exit(f'{path}: FIND occurs {s.count(a)} times: {a[:80]!r}')
    files[path] = s.replace(a, z)

# ---- P3-F9: short reserved words match whole words only, so real names across a space aren't blocked
#      ("Gustavo Terrazas" holds "voter", "Felicity Ofori" holds "cityof"); long distinctive ones still match anywhere
# ---- P3-F5: a copy split at case and letter/digit changes ("TravisGOP", "GOP2026", "Dems4Travis")
# ---- P3-F7: 9 and 8 stand in for g and b
sw(T, "// matches (\"E1ect1on\", \"Vote41I\"). Checked as one run of letters (spaces, punctuation and symbols removed) and word by\n"
      "// word (punctuation and symbols as spaces; spaced-out single letters like \"G. O. P.\" joined), with | ! $ @ read both as\n"
      "// letters and as nothing. A hyphenated part that is a reserved word (\"Mo-Dem\") is blocked too: rare, accepted (Pass 2).\n",
      "// matches (\"E1ect1on\", \"Vote41I\"). Long, distinctive words are found anywhere, even across spaces (RESERVED); short\n"
      "// ones only as whole words (RESERVED_WORDS), so a real name like \"Gustavo Terrazas\" (\"voter\") isn't blocked (Pass 3).\n"
      "// Words are read with punctuation and symbols as spaces, spaced-out single letters joined (\"G. O. P.\"), and in a copy\n"
      "// split where case or letters/digits change (\"TravisGOP\", \"GOP2026\"); | ! $ @ are read both as letters and as nothing.\n"
      "// A hyphenated part that is a reserved word (\"Mo-Dem\") is blocked too: rare, accepted (Pass 2).\n")
sw(T, "const FOLD = { '1': 'l', 'i': 'l', '|': 'l', '!': 'l', '0': 'o', '3': 'e', '4': 'a', '@': 'a', '5': 's', '$': 's', '6': 'g', '7': 't' };\n"
      "const fold = (t) => t.replace(/[1i|!03456@$7]/g, ch => FOLD[ch]);\n"
      "const RESERVED = new RegExp(['league', 'lwv', 'voter', 'vote411', 'county', 'clerk', 'official', 'ballotta', 'cityof', 'villageof', 'election',\n"
      "  'government', 'democrat', 'republican', 'libertarian', 'greenparty', 'taxoffice', 'campaign', 'secretaryofstate'].map(fold).join('|'));\n"
      "const RESERVED_WORDS = new RegExp('\\\\b(' + ['state', 'party', 'admin', 'gop', 'dems?', 'repubs?', 'rnc', 'dnc'].map(fold).join('|') + ')\\\\b');\n",
      "const FOLD = { '1': 'l', 'i': 'l', '|': 'l', '!': 'l', '0': 'o', '3': 'e', '4': 'a', '@': 'a', '5': 's', '$': 's', '6': 'g', '7': 't', '8': 'b', '9': 'g' };\n"
      "const fold = (t) => t.replace(/[1i|!0345@$6789]/g, ch => FOLD[ch]);\n"
      "const RESERVED = new RegExp(['league', 'lwv', 'vote411', 'county', 'official', 'ballotta', 'election', 'government', 'democrat', 'republican',\n"
      "  'libertarian', 'greenparty', 'campaign', 'secretaryofstate'].map(fold).join('|'));\n"
      "const RESERVED_WORDS = new RegExp('\\\\b(' + ['state', 'party', 'admin', 'gop', 'dems?', 'repubs?', 'rnc', 'dnc', 'voters?', 'clerks?', 'city ?of', 'village ?of',\n"
      "  'tax ?office'].map(fold).join('|') + ')\\\\b');\n")
sw(T, "  const low = [...n.normalize('NFKD').replace(/\\p{M}/gu, '').toLowerCase()].map(ch => LOOKALIKE[ch] || ch).join('');\n",
      "  const latin = (t) => [...t.normalize('NFKD').replace(/\\p{M}/gu, '').toLowerCase()].map(ch => LOOKALIKE[ch] || ch).join('');\n"
      "  const low = latin(n), split = latin(n.replace(/(\\p{Ll})(?=\\p{Lu})/gu, '$1 ').replace(/(\\p{L})(?=\\p{N})|(\\p{N})(?=\\p{L})/gu, '$1$2 '));\n")
sw(T, "  const forms = [fold(low), fold(low.replace(/[|!$@]/g, ''))];\n",
      "  const forms = [fold(low), fold(low.replace(/[|!$@]/g, '')), fold(split)];\n")

# ---- P3-F3/F4: Print… moves focus only for a keyboard press, and brings the real Print button on screen
sw(T, "  $('dk-print').addEventListener('click', () => {  // opens the crib view, where the print options are (Lane, Oct 15)\n",
      "  $('dk-print').addEventListener('click', (e) => {  // opens the crib view, where the print options are (Lane, Oct 15)\n")
sw(T, "    const pr = N().querySelector('[data-act=\"print\"]'); if (pr) pr.focus({ preventScroll: true });  // keyboard users land on the real Print button (Pass 2)\n",
      "    const pr = N().querySelector('[data-act=\"print\"]');\n"
      "    // A keyboard press lands on the real Print button, scrolled on screen (below the paper at 1024–1279px); a mouse click\n"
      "    // leaves focus alone, so Space still scrolls instead of printing (Pass 2, Pass 3).\n"
      "    if (pr && e.detail === 0) { pr.focus({ preventScroll: true }); pr.scrollIntoView({ block: 'nearest' }); }\n")

# ---- P3-F1/F2: a new day keeps the visitor's place in the vote view even on a link (by position), without selectors
sw(T, "      const a = document.activeElement, sel = a && P().contains(a) ? (a.dataset.period ? '[data-period=\"' + a.dataset.period + '\"]' : a.id ? '#' + a.id : '') : '';\n"
      "      viewVote();\n"
      "      const back = sel && P().querySelector(sel); if (back) back.focus({ preventScroll: true });  // keep the visitor's place (Pass 2)\n",
      "      const items = () => [...P().querySelectorAll('a,button')], a = document.activeElement;\n"
      "      const was = a && a !== P() && P().contains(a) ? { p: a.dataset.period, id: a.id, i: items().indexOf(a) } : null;\n"
      "      viewVote();\n"
      "      if (!was) return;  // keep the visitor's place: same period button or id, else the same position, else the paper (Pass 2, Pass 3)\n"
      "      (items().find(e => (was.p && e.dataset.period === was.p) || (was.id && e.id === was.id)) || items()[was.i] || P()).focus({ preventScroll: true });\n")

# ---- tests
sw(TS, """'G+O+P', 'G~O~P', 'D^E^M^S', 'Off!cial', 'Ad|min']:   # Pass 2""",
       """'G+O+P', 'G~O~P', 'D^E^M^S', 'Off!cial', 'Ad|min',   # Pass 2
                'TravisGOP', 'AustinDems', 'GOP2026', 'Dems4Travis', 'TeaParty', 'SiteAdmin', '9OP', '8allotta', 'VoterGuide',
                'Cityof Austin', 'Travis Co. Tax Office', 'Travis County Clerk']:   # Pass 3""")
sw(TS, """'G O Pal', 'Işıl Yılmaz', 'Partyka', 'Admina']:""",
       """'G O Pal', 'Işıl Yılmaz', 'Partyka', 'Admina',
                 'Gustavo Terrazas', 'Ivo Terzić', 'Felicity Ofori', 'Clerkin', 'DeMarco', 'DeShawn', 'McDonald', 'LaToya']:   # Pass 3""")
sw(TS, """    pg.focus('#dk-print'); pg.keyboard.press('Enter')                              # already there: not counted again (Pass 2)
    assert [e[1].get('view') for e in events(pg) if e[0] == 'view_opened'] == ['crib'], events(pg)""",
       """    pg.focus('#dk-print'); pg.keyboard.press('Enter')                              # already there: not counted again (Pass 2)
    assert [e[1].get('view') for e in events(pg) if e[0] == 'view_opened'] == ['crib'], events(pg)
    pg.click('#dk-views [data-view="decide"]'); pg.click('#dk-print')               # a mouse click doesn't move focus: Space won't print (Pass 3)
    assert pg.evaluate('document.activeElement.dataset.act') != 'print'
    pg.set_viewport_size({'width': 1100, 'height': 800})                            # the notes sit below the paper at 1024–1279px (Pass 3)
    pg.click('#dk-views [data-view="decide"]'); pg.focus('#dk-print'); pg.keyboard.press('Enter')
    r = pg.evaluate('(() => { const r = document.activeElement.getBoundingClientRect(); return [document.activeElement.dataset.act, r.top, r.bottom, innerHeight]; })()')
    assert r[0] == 'print' and r[1] >= 0 and r[2] <= r[3], ('the focused Print button is off screen', r)""")
sw(TS, """        assert pg.evaluate('document.activeElement.dataset.period') == 'early', pg.evaluate('document.activeElement.tagName')
        ctx.close()""",
       """        assert pg.evaluate('document.activeElement.dataset.period') == 'early', pg.evaluate('document.activeElement.tagName')
        ctx.close()
        # ...and on a Directions link, by its position in the list (Pass 3)
        ctx, pg = new_page(b, wide=True); pg.clock.install(time=dt.datetime(2026, 10, 18, 23, 58)); pg.goto(BASE)
        pg.evaluate('s => localStorage.setItem("ballotta.ballot", s)', st); pg.reload(); pg.wait_for_selector('body.dk-app-on')
        pg.click('#dk-views [data-view="vote"]'); link3 = pg.locator('#dk-paper a', has_text='Directions').nth(2); link3.focus()
        href = link3.get_attribute('href'); pg.clock.run_for(5 * 60 * 1000)
        assert pg.text_content('#dk-when') == 'Early voting through Fri Oct 30 · 7am–7pm', pg.text_content('#dk-when')
        assert pg.evaluate('document.activeElement.getAttribute("href")') == href, pg.evaluate('document.activeElement.outerHTML.slice(0, 120)')
        ctx.close()""")

# ---- mutants
m = files.setdefault(MD, (ROOT / MD).read_text(encoding='utf-8'))
for pre in ("('A21 ", "('R10 ", "('R12 "):
    hits = [l for l in m.split('\n') if l.startswith(' ' + pre)]
    assert len(hits) == 1, pre
    m = m.replace(hits[0] + '\n', '')
NEWM = [
 ('A21 laptop header keeps the old day', 'PREV', "      $('dk-when').textContent = whenLine();\n      if (ui.view !== 'vote'", "      if (ui.view !== 'vote'", ['dates_move_on_in_a_tab_left_open']),
 ('R10 Print… leaves keyboard focus behind', 'PREV', "    if (pr && e.detail === 0) { pr.focus({ preventScroll: true }); pr.scrollIntoView({ block: 'nearest' }); }\n", '', ['desk_print_button_opens_the_crib_sheet']),
 ('R12 new day loses the vote-view place', 'PREV', "      (items().find(e => (was.p && e.dataset.period === was.p) || (was.id && e.id === was.id)) || items()[was.i] || P()).focus({ preventScroll: true });\n", '', ['dates_move_on_in_a_tab_left_open']),
 ('R13 Print… moves focus on a mouse click', 'PREV', 'if (pr && e.detail === 0) {', 'if (pr) {', ['desk_print_button_opens_the_crib_sheet']),
 ('R14 focused Print button left off screen', 'PREV', " pr.scrollIntoView({ block: 'nearest' }); }", ' }', ['desk_print_button_opens_the_crib_sheet']),
 ('R15 place on a link not kept', 'PREV', ' || items()[was.i] || P()).focus', ' || P()).focus', ['dates_move_on_in_a_tab_left_open']),
 ('R16 short words matched across spaces', 'PREV', "['league', 'lwv', 'vote411', 'county',", "['league', 'lwv', 'voter', 'cityof', 'vote411', 'county',", ['share_names_block_lookalikes_and_nicknames']),
 ('R17 glued words not split', 'PREV', ", fold(low.replace(/[|!$@]/g, '')), fold(split)];", ", fold(low.replace(/[|!$@]/g, ''))];", ['share_names_block_lookalikes_and_nicknames']),
 ('R18 voter not a reserved word', 'PREV', "'dnc', 'voters?', 'clerks?',", "'dnc', 'clerks?',", ['share_names_block_lookalikes_and_nicknames']),
 ('R19 9 not read as g', 'PREV', ", '8': 'b', '9': 'g' };", " };", ['share_names_block_lookalikes_and_nicknames']),
]
k = m.index('\n]\n')
m = m[:k] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in NEWM).rstrip('\n') + '\n]\n' + m[k + 3:]
files[MD] = m
for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
print('rework A3 applied to', ', '.join(files))
```

## Script: rework_A4.py

```python
"""Issues round, commit A: rework after remediation-audit Pass 4. Run from the repo root after rework_A3.py:
    python3 <this file>"""
import pathlib, sys
ROOT = pathlib.Path.cwd()
T, TS, MD = 'source/template-travis.html', 'tests/test_site.py', 'tests/mutate_desk.py'
files = {}
def sw(path, a, z):
    s = files.setdefault(path, (ROOT / path).read_text(encoding='utf-8'))
    if s.count(a) != 1: sys.exit(f'{path}: FIND occurs {s.count(a)} times: {a[:80]!r}')
    files[path] = s.replace(a, z)

# ---- P4-F4: the vote view re-draws only when the voting period changed; then the old place is gone, so focus goes to
# the paper (never to a different vote center's link). Other days leave it, and the visitor's focus, alone.
sw(T, "  shownDay = d;\n  if (!periodChosen) period = defaultPeriod();\n  renderVote();/*DESK*/ if (window.desk) try { desk.today(); } catch (e) {}/*/DESK*/",
      "  shownDay = d;\n  const was = period;\n  if (!periodChosen) period = defaultPeriod();\n  renderVote();/*DESK*/ if (window.desk) try { desk.today(period !== was); } catch (e) {}/*/DESK*/")
sw(T, "    today() {  // a new day (#34): the header's line, and the vote view's hours if it's open; the paper and its focus stay as they are\n",
      "    today(periodChanged) {  // a new day (#34): the header's line; the vote view only if the voting period changed\n")
sw(T, "      if (ui.view !== 'vote' || !document.body.classList.contains('dk-app-on')) return;\n"
      "      const items = () => [...P().querySelectorAll('a,button')], a = document.activeElement;\n"
      "      const was = a && a !== P() && P().contains(a) ? { p: a.dataset.period, id: a.id, i: items().indexOf(a) } : null;\n"
      "      viewVote();\n"
      "      if (!was) return;  // keep the visitor's place: same period button or id, else the same position, else the paper (Pass 2, Pass 3)\n"
      "      (items().find(e => (was.p && e.dataset.period === was.p) || (was.id && e.id === was.id)) || items()[was.i] || P()).focus({ preventScroll: true });\n",
      "      if (!periodChanged || ui.view !== 'vote' || !document.body.classList.contains('dk-app-on')) return;\n"
      "      const inside = P().contains(document.activeElement);\n"
      "      viewVote();  // a new list of vote centers: the old place in it is gone, so focus goes to the paper, never to another center's link (Pass 4)\n"
      "      if (inside) P().focus({ preventScroll: true });\n")

# ---- P4-F1/F2: glued handles ("voterguide", "cityofaustin", "travisclerk") and leading acronyms ("GOPTravis")
sw(T, "const RESERVED = new RegExp(['league', 'lwv', 'vote411', 'county', 'official', 'ballotta', 'election', 'government', 'democrat', 'republican',\n"
      "  'libertarian', 'greenparty', 'campaign', 'secretaryofstate'].map(fold).join('|'));\n",
      "const RESERVED = new RegExp(['league', 'lwv', 'vote411', 'county', 'official', 'ballotta', 'election', 'government', 'democrat', 'republican',\n"
      "  'libertarian', 'greenparty', 'campaign', 'secretaryofstate', 'taxoffice', 'villageof'].map(fold).join('|'));\n"
      "// voter, clerk and city-of also count at the start or end of one word with 4+ more letters (\"voterguide\", \"travisclerk\"),\n"
      "// never across a space, so \"Clerkson\" and \"Gustavo Terrazas\" are fine (Pass 4).\n"
      "const RESERVED_GLUED = new RegExp('(^|\\\\s)(' + ['voters?', 'clerks?', 'cityof'].map(fold).join('|') + ')\\\\S{4,}|\\\\S{4,}(' + ['voters?', 'clerks?', 'cityof'].map(fold).join('|') + ')(\\\\s|$)');\n")
sw(T, "  const low = latin(n), split = latin(n.replace(/(\\p{Ll})(?=\\p{Lu})/gu, '$1 ').replace(",
      "  const low = latin(n), split = latin(n.replace(/(\\p{Lu})(?=\\p{Lu}\\p{Ll})/gu, '$1 ').replace(/(\\p{Ll})(?=\\p{Lu})/gu, '$1 ').replace(")
sw(T, "  return forms.some(t => RESERVED.test(run(t)) || words(t).some(x => RESERVED_WORDS.test(x))) ? '' : n;",
      "  return forms.some(t => RESERVED.test(run(t)) || words(t).some(x => RESERVED_WORDS.test(x) || RESERVED_GLUED.test(x))) ? '' : n;")

# ---- P4-F5/F6: holding Enter on Print… can't print; the comment says what a later Space does
sw(T, "    // A keyboard press lands on the real Print button, scrolled on screen (below the paper at 1024–1279px); a mouse click\n"
      "    // leaves focus alone, so Space still scrolls instead of printing (Pass 2, Pass 3).\n",
      "    // A keyboard press lands on the real Print button, scrolled on screen (below the paper at 1024–1279px); a mouse click\n"
      "    // leaves focus on Print… (a later Space or Enter just moves it to the real button). A held key's repeats are ignored\n"
      "    // there, so holding Enter on Print… never prints (Pass 2, 3, 4).\n")
sw(T, "    N().querySelectorAll('[data-act]').forEach(btn => btn.addEventListener('click', () => act(btn.dataset.act)));\n  }\n\n  /* ----- actions ----- */",
      "    N().querySelectorAll('[data-act]').forEach(btn => btn.addEventListener('click', () => act(btn.dataset.act)));\n"
      "    N().querySelectorAll('[data-act=\"print\"]').forEach(btn => btn.addEventListener('keydown', (e) => { if (e.repeat) e.preventDefault(); }));  // Pass 4\n"
      "  }\n\n  /* ----- actions ----- */")

# ---- tests
sw(TS, """                'Cityof Austin', 'Travis Co. Tax Office', 'Travis County Clerk']:   # Pass 3""",
       """                'Cityof Austin', 'Travis Co. Tax Office', 'Travis County Clerk',   # Pass 3
                'voterguide', 'VOTERGUIDE', 'cityofaustin', 'travisclerk', 'texasvoters', 'travistaxoffice', 'villageofx',
                'GOPTravis', 'DNCTexas', 'VOTERInfo', 'STATEParty']:   # Pass 4""")
sw(TS, """'Felicity Ofori', 'Clerkin', 'DeMarco', 'DeShawn', 'McDonald', 'LaToya']:   # Pass 3""",
       """'Felicity Ofori', 'Clerkin', 'DeMarco', 'DeShawn', 'McDonald', 'LaToya',   # Pass 3
                 'Clerkson', 'DeClerck', 'JRRTolkien', 'DJ Khaled', 'MacArthur', 'Gopinath', 'Rajagopal', 'Staten']:   # Pass 4""")
sw(TS, """        assert pg.get_attribute('#dk-paper [data-period="eday"]', 'aria-pressed') == 'true', 'the vote view moved on to Election Day'
        assert pg.evaluate('document.activeElement.dataset.period') == 'early', pg.evaluate('document.activeElement.tagName')""",
       """        assert pg.get_attribute('#dk-paper [data-period="eday"]', 'aria-pressed') == 'true', 'the vote view moved on to Election Day'
        assert pg.evaluate('document.activeElement.id') == 'dk-paper', 'a new list: focus on the paper, not on another center (Pass 4)'""")
sw(TS, """    r = pg.evaluate('(() => { const r = document.activeElement.getBoundingClientRect(); return [document.activeElement.dataset.act, r.top, r.bottom, innerHeight]; })()')
    assert r[0] == 'print' and r[1] >= 0 and r[2] <= r[3], ('the focused Print button is off screen', r)""",
       """    r = pg.evaluate('(() => { const r = document.activeElement.getBoundingClientRect(); return [document.activeElement.dataset.act, r.top, r.bottom, innerHeight]; })()')
    assert r[0] == 'print' and r[1] >= 0 and r[2] <= r[3], ('the focused Print button is off screen', r)
    pg.click('#dk-views [data-view="decide"]'); pg.focus('#dk-print'); before = pg.evaluate('window.__printed')
    for _ in range(3): pg.keyboard.down('Enter')                                    # a held Enter: its repeats don't print (Pass 4)
    pg.keyboard.up('Enter'); assert pg.evaluate('window.__printed') == before, 'holding Enter on Print… printed'""")

# ---- mutants
m = files.setdefault(MD, (ROOT / MD).read_text(encoding='utf-8'))
# R9 is retired: a regex word boundary already treats a symbol as a break, and the joined form strips symbols, so
# reading symbols as spaces adds nothing the tests can see (an equivalent mutant, like V16, V22 and V53).
for pre in ("('R12 ", "('R15 ", "('A4 ", "('R1 ", "('A5 ", "('A6 ", "('R7 ", "('A21 ", "('R9 "):
    hits = [l for l in m.split('\n') if l.startswith(' ' + pre)]
    assert len(hits) == 1, pre
    m = m.replace(hits[0] + '\n', '')
NEWM = [
 ('R1 a new day redraws the whole laptop page', 'PREV', 'desk.today(period !== was); } catch (e) {}/*/DESK*/', 'desk.render(); } catch (e) {}/*/DESK*/', ['dates_move_on_in_a_tab_left_open']),
 ('A5 party nicknames allowed', 'PREV', "'gop', 'dems?', 'repubs?', 'rnc', 'dnc', ", "'gop', ", ['share_names_block_lookalikes_and_nicknames']),
 ('A6 symbols read only as letters', 'PREV', "[fold(low), fold(low.replace(/[|!$@]/g, '')), ", "[fold(low), ", ['share_names_block_lookalikes_and_nicknames']),
 ('R7 reserved words not folded', 'PREV', "'villageof'].map(fold).join('|'));", "'villageof'].join('|'));", ['share_names_block_lookalikes_and_nicknames', 'audit_a5_a8_a12_hostile_share']),
 ('A21 laptop header keeps the old day', 'PREV', "      $('dk-when').textContent = whenLine();\n      if (!periodChanged", "      if (!periodChanged", ['dates_move_on_in_a_tab_left_open']),
 ('A4 stand-ins not folded', 'PREV', "const fold = (t) => t.replace(/[1i|!0345@$6789]/g, ch => FOLD[ch]);", "const fold = (t) => t;", ['share_names_block_lookalikes_and_nicknames']),
 ('R12 new list leaves focus nowhere', 'PREV', '      if (inside) P().focus({ preventScroll: true });\n', '', ['dates_move_on_in_a_tab_left_open']),
 ('R15 every new day re-draws the vote view', 'PREV', "      if (!periodChanged || ui.view !== 'vote'", "      if (ui.view !== 'vote'", ['dates_move_on_in_a_tab_left_open']),
 ('R20 glued handles get through', 'PREV', ' || RESERVED_GLUED.test(x)', '', ['share_names_block_lookalikes_and_nicknames']),
 ('R21 leading acronyms not split', 'PREV', "n.replace(/(\\p{Lu})(?=\\p{Lu}\\p{Ll})/gu, '$1 ').replace(", "n.replace(", ['share_names_block_lookalikes_and_nicknames']),
 ('R22 glued words need fewer letters', 'PREV', "')\\\\S{4,}|\\\\S{4,}('", "')\\\\S{1,}|\\\\S{1,}('", ['share_names_block_lookalikes_and_nicknames']),
 ('R23 holding Enter prints', 'PREV', "    N().querySelectorAll('[data-act=\"print\"]').forEach(btn => btn.addEventListener('keydown', (e) => { if (e.repeat) e.preventDefault(); }));  // Pass 4\n", '', ['desk_print_button_opens_the_crib_sheet']),
]
k = m.index('\n]\n')
m = m[:k] + '\n' + ''.join(f" ({n!r}, {f}, {a!r}, {z!r}, {t!r}),\n" for n, f, a, z, t in NEWM).rstrip('\n') + '\n]\n' + m[k + 3:]
files[MD] = m
for path, text in files.items(): (ROOT / path).write_text(text, encoding='utf-8')
print('rework A4 applied to', ', '.join(files))
```
