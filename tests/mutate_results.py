"""Mutation-kill check for the results tests (Lane, Oct 20; docs/plans/2026-10-20-results.md): every mutant must turn at
least one named test RED. The same runner as mutate_desk.py (files restored from an in-memory copy, even when stopped),
against index.html. Run from the repo root after the build:
    python3 tests/mutate_results.py [first last]   (a slice of the list, e.g. 0 10)"""
import os, re, sys, pathlib
ROOT = pathlib.Path.cwd()
_set = re.findall(r'^RESULTS_LIVE\s*=\s*(True|False)\b', (ROOT / 'source/build_site.py').read_text(encoding='utf-8'), re.M)
assert _set == ['True'], ('the results tests need RESULTS_LIVE = True', _set)
os.environ['BALLOTTA_MUTATE_PAGE'] = 'index.html'
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mutate_desk as R

PREV, BLD, SW = R.PREV, R.BLD, ROOT / 'sw.js'
L, P, S = 'results_show_on_the_laptop_ballot', 'results_show_on_the_phone_ballot', 'results_say_what_changed_since_you_last_looked'
W, X, O = 'withdrawn_results_hide_everything', 'a_bad_results_file_breaks_nothing', 'the_date_override_works_only_on_this_computer'
A, C, N, E = 'all_travis_county_results_need_no_address', 'a_saved_copy_says_so', 'results_wait_for_nov_4', 'the_canvass_is_explained_from_the_results_and_the_menu'
T = 'results_turn_the_ballot_into_a_record'
M = [
 ('R1 results before Nov 4', PREV, 'const live = () => day() >= FROM;', 'const live = () => true;', [N]),
 ('R2 ?today= works on ballotta.org', PREV, "const LOCAL = ['localhost', '127.0.0.1'].includes(location.hostname);", 'const LOCAL = true;', [O]),
 ('R3 choices out of ballot order accepted', PREV, "    if (names.filter((n, i) => !e.choices[i][3]).join('\\u0000') !== own.join('\\u0000')) return false;   // the ballot's own choices, in its order\n", '', [X]),
 ('R4 a source label as HTML', PREV, "e.sources.map((s, i) => esc(s[0]) + (i ? ', ' : ', posted ') + esc(when(s[1])))", "e.sources.map((s, i) => s[0] + (i ? ', ' : ', posted ') + esc(when(s[1])))", [X]),
 ('R5 a one-seat pick reads backwards', PREV, "      if (n === 1) return mineIn ? 'Your pick is leading.' : 'Your pick is behind.';", "      if (n === 1) return mineIn ? 'Your pick is behind.' : 'Your pick is leading.';", [L]),
 ('R6 a measure pick reads backwards', PREV, "((V === 'passing') === (v[0] === 'FOR') ? 'is leading.' : 'is behind.')", "((V === 'passing') === (v[0] === 'FOR') ? 'is behind.' : 'is leading.')", [L]),
 ('R7 official, unofficial numbers unsaid', PREV, "(e.official_numbers ? '' : ' · numbers are the last unofficial count')", "''", [S]),
 ('R8 late ballots forever', PREV, '    if (day() <= R.late_until) h +=', '    if (true) h +=', [S]),
 ('R9 a missing county unsaid', PREV, "    if (e.state === 'partial') h += ", "    if (false) h += ", [L]),
 ('R10 nothing becomes official since', PREV, "      else if (isOfficial(e) && was[id] && !/^(official|recount)\\|/.test(was[id])) since.official++;\n", '', [S]),
 ('R11 what was seen is never kept', PREV, "    LS.set('ballotta.resultsSeen', { seq: R.seq, v: now });\n", '', [S]),
 ('R12 withdrawn ignored', PREV, 'const entry = (cid) => (R && !R.withdrawn && live() ?', 'const entry = (cid) => (R && live() ?', [W]),
 ('R13 a Result column with nothing in it', PREV, "  function glance(paper) {\n    if (!on()) return;\n", "  function glance(paper) {\n", [W]),
 ('R14 a pick line on nobody\'s ballot', PREV, "    if (withPick !== false) {   // your pick", "    if (true) {   // your pick", [A, P]),
 ('R15 results counted at every redraw', PREV, "    if (!counted) { counted = true; track('results_seen'); }\n  }\n  function landing() {", "    track('results_seen');\n  }\n  function landing() {", [L, P]),
 ('R16 a saved copy unsaid', PREV, "r.headers.get('x-ballotta-copy') === 'saved'", 'false', [C]),
 ('R17 the offline copy marks nothing', SW, "u.pathname.endsWith('/results.json') ? savedCopy(kept) : kept", "u.pathname.endsWith('/results.json') ? kept : kept", [C]),   # the built file; a stale build is the pipeline's catch
 ('R18 a correction never fades', PREV, '+e.corrected.slice(8, 10) + 7)', '+e.corrected.slice(8, 10) + 700)', [S]),
 ('R19 no votes yet reads as unofficial', PREV, "    if (e.state === 'counting') return '<p class=\"rs-st\">No votes reported yet</p>';", '', [L]),
 ('R20 declared write-ins unexplained', PREV, "    if (e.write_ins) h +=", "    if (false) h +=", [L]),
 ('R21 no Travis breakdown', PREV, '    if (e.travis) h +=', '    if (false) h +=', [L]),
 ('R22 the menu item opens nothing', PREV, "    if (item) item.addEventListener('click', why);\n", '', [E]),
 ('R23 no landing card', PREV, "    if (box) box.classList.toggle('hidden', !on());", "    if (box) box.classList.add('hidden');", [A]),
 ('R24 ?results ignored', PREV, '    if (wantAll && on()) { wantAll = false; openAll(); }', '    if (false) { wantAll = false; openAll(); }', [A]),
 ('R25 the Legislature called the state', PREV, "    else if (cv.kind === 'legislature') h +=", "    else if (false) h +=", [L]),
 ('R26 parties colored', PREV, '.rs-tr i{display:block;height:100%;background:var(--lc)}', '.rs-tr i{display:block;height:100%;background:var(--lc)}.rs-b:nth-child(2) .rs-tr i{background:#007BBD}', [L]),
 ('R27 a level button filters nothing', PREV, "(ui.level === 'all' || c.level === ui.level)", 'true', [A]),
 ('R28 search finds nothing new', PREV, "(!q || (c.title + ' ' + optionsOf(c).join(' ')", "(!q || ('' + ' ' + ''", [A]),
 ('R29 a bad file breaks the page', PREV, '    Object.keys(j.contests).forEach(cid => { if (entryOK(cid, j.contests[cid])) contests[cid] = j.contests[cid]; });', '    Object.keys(j.contests).forEach(cid => { contests[cid] = j.contests[cid]; });', [X]),
 ('R30 asked before the gate', PREV, "    if (!live() || document.visibilityState === 'hidden' ||", "    if (document.visibilityState === 'hidden' ||", [N]),
 ('R31 a two-thirds measure unsaid', PREV, "    if (e.needs === 'two_thirds') h +=", "    if (false) h +=", [A]),
 # after the election (docs/plans/2026-10-21-after-the-election.md)
 ('R32 never after the election', PREV, "  const after = () => !!(R && live() && (R.withdrawn || Object.keys(R.contests).length));", "  const after = () => false;", [T]),
 ('R33 picks editable after', PREV, "    if (after()) return viewResult();\n", '', [T]),
 ('R34 picking keys after', PREV, "    if (after() && (/^[1-9]$/.test(k) || k === 's' || k === 'r')) return;", '', [T]),
 ('R35 decided counted as official', PREV, "done = ballot.filter(b => A ? results.official(b.c) : decided(b.c.id)).length;", "done = ballot.filter(b => decided(b.c.id)).length;", [T, L, S]),
 ('R36 everything too close', PREV, "['too_close', 'may_runoff', 'tied', 'tied_second'].includes(e.verdict)", 'true', [T]),
 ('R37 behind counted as leading', PREV, "    if (V === 'leading') return hit ? 'up' : 'behind';", "    if (V === 'leading') return 'up';", [T]),
 ('R38 the timeline stuck at the start', PREV, "    const now = steps.findIndex(s => d <= s[2]);", "    const now = 0;", [T]),
 ('R39 an official runoff unsaid', PREV, "!!e.runoff_on && day() <= e.runoff_on;", "!!e.runoff_on && day() > e.runoff_on;", [T]),
 ('R40 Next skips to the undecided', PREV, "  function upNext() { if (after()) return null; ", "  function upNext() { ", [T]),
 ('R41 the reason left out', PREV, "(w ? '<p><q>'", "(false ? '<p><q>'", [T]),
 ('R42 the whole summary on a phone', PREV, ".rs-band .rs-sum,.rs-band .rs-tl{display:none}", ".rs-band .rs-x{display:none}", [P]),
]
if __name__ == '__main__':
    R.main(M)
