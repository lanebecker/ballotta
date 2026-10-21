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
V = 'every_state_reads_in_at_a_glance_and_the_printout'
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
 ('R14 a pick line on nobody\'s ballot', PREV, "    if (withPick !== false) {   // your pick", "    if (true) {   // your pick", [A, P]),
 ('R15 results counted at every redraw', PREV, "    if (!counted) { counted = true; track('results_seen'); }\n  }\n  function landing() {", "    track('results_seen');\n  }\n  function landing() {", [L, P]),
 ('R16 a saved copy unsaid', PREV, "r.headers.get('x-ballotta-copy') === 'saved'", 'false', [C]),
 ('R17 the offline copy marks nothing', SW, "u.pathname.endsWith('/results.json') ? savedCopy(kept) : kept", "u.pathname.endsWith('/results.json') ? kept : kept", [C]),   # the built file; a stale build is the pipeline's catch
 ('R18 a correction never fades', PREV, '+e.corrected.slice(8, 10) + 7)', '+e.corrected.slice(8, 10) + 700)', [S]),
 ('R19 no votes yet reads as unofficial', PREV, "    if (e.state === 'counting') return '<p class=\"rs-st\">No votes reported yet</p>';", '', [L]),
 ('R20 declared write-ins unexplained', PREV, "    if (e.write_ins) h +=", "    if (false) h +=", [L]),
 ('R21 no Travis breakdown', PREV, '    if (e.travis) h +=', '    if (false) h +=', [L]),
 ('R22 the menu item opens nothing', PREV, "    if (item) item.addEventListener('click', why);\n", '', [E]),
 ('R23 no way to all results from the landing', PREV, "    if (or) or.classList.toggle('hidden', !A);", "    if (or) or.classList.add('hidden');", [A]),
 ('R24 ?results ignored', PREV, '    if (wantAll && on()) { wantAll = false; openAll(); }', '    if (false) { wantAll = false; openAll(); }', [A]),
 ('R25 the Legislature called the state', PREV, "    else if (cv.kind === 'legislature') h +=", "    else if (false) h +=", [L]),
 ('R26 parties colored', PREV, '.rs-tr i{display:block;height:100%;background:var(--lc)}', '.rs-tr i{display:block;height:100%;background:var(--lc)}.rs-b:nth-child(2) .rs-tr i{background:#007BBD}', [L]),
 ('R27 a level button filters nothing', PREV, "(st.level === 'all' || c.level === st.level)", 'true', [A]),
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
 ('R43 the landing unchanged after', PREV, "      .forEach(([el, h]) => A ? swapIn(el, h) : swapOut(el));", "      .forEach(() => {});", [A]),
 ('R44 no address, no page', PREV, "(ballot.length > 0 || (after() && ui.allNow && ui.view === 'all'))", "(ballot.length > 0)", [A]),
 ('R45 a level row does nothing', PREV, "r.addEventListener('click', () => { ui.level = r.dataset.lv; render();", "r.addEventListener('click', () => { render();", [A]),
 ('R46 no summary in the phone list', PREV, "    if (A && html) html = results.listSum() + html;", '', [P]),
 ('R47 the filter ignored on the page', PREV, "&& (st.filter === 'all' || (st.filter === 'und' ? close(c) : RUNOFFISH.includes(entry(c.id).verdict)))", '', [A]),
 # Phase 3: At a glance and Print your results after the election
 ('R13 At a glance editable after', PREV, "    if (after()) {   // after the election: the results beside your picks", "    if (false) {   // after the election: the results beside your picks", [T]),
 ('R48 the pick filter ignored', PREV, "      if (mine && !picked(c)) return;\n", '', [T]),
 ('R49 the picks printed, not the results', PREV, "  if (window.results && results.after()) return results.crib(withWhy);", '', [T]),
 ('R50 the printout never redrawn', PREV, "    try { renderCrib(); } catch (e) {}   // the printout", '', [T]),
 ('R51 a measure share misread', PREV, "f[2].toFixed(1) + '% '", "'50.0% '", [L]),
 ('R52 no canvass date in At a glance', PREV, "    return s + (cv.on ? ' · canvass ' + md(cv.on) : cv.by ? ' · canvass by ' + md(cv.by) : '');", "    return s;", [L]),
 ('R53 the runoff date left off', PREV, "    if (['runoff', 'tied_runoff'].includes(e.verdict) && e.runoff_on && day() <= e.runoff_on) return s + ' · runoff ' + dayLong(e.runoff_on) + rc;", '', [T]),
 ('R54 a recount unsaid in At a glance', PREV, "rc = e.state === 'recount' ? ' · recount requested' : '';", "rc = '';", [V]),
 ('R55 two-thirds unsaid in At a glance', PREV, "(e.needs === 'two_thirds' ? ' · needs two-thirds' : '')", "''", [V]),
 ('R56 a tie at full length in At a glance', PREV, "    return e.verdict === 'tied' ? 'Tied' : verdict(c, e);", "    return verdict(c, e);", [V]),
 # the cold audit's fixes (Oct 21, #135-#150)
 ('R58 a new leader is only new numbers', PREV, "else if (!same(w.slice(0, 4), n.slice(0, 4))) since.changed++;", "else if (!same(w.slice(0, 2), n.slice(0, 2))) since.changed++;", [S]),
 ('R59 every race has new numbers', PREV, "else if (w[4] !== n[4]) since.numbers++;", "else since.numbers++;", [S]),
 ('R60 an old correction is news again', PREV, "(e.corrected > at || (e.corrected === at && e.changed > seen.seq))", "true", [S]),
 ('R61 what is seen while open is forgotten', PREV, "if (txt !== seenText) { seenText = txt;", "if (!seenText) { seenText = txt;", [S]),
 ('R62 new results wipe the reader\'s place', PREV, "if (news) desk.reflow(updated()); else desk.render();", "desk.render();", [S]),
 ('R63 the header loses the results time at midnight', PREV, "(after() && results.updated()) || whenLine();   // after the election, the results' time, as header() (#141)", "whenLine();", [T]),
 ('R64 a canvassed tie is too close to call', PREV, "!!e && !isOfficial(e) && ['too_close'", "!!e && ['too_close'", [V]),
 ('R65 a recount reads as lost', PREV, "    if (e.state === 'recount') return 'open';", "", [V]),
 ('R66 the rail hides a recount', PREV, "(isOfficial(e) ? 'Official' : 'Unofficial') + (e.state === 'recount' ? ' · recount requested' : '');", "(isOfficial(e) ? 'Official' : 'Unofficial');", [V]),
 ('R67 two close counts read alike', PREV, "seen[k] = x[1]; return false; }) ? 2 : 1;", "seen[k] = x[1]; return false; }) ? 1 : 1;", [V]),
 ('R68 a tie that goes to a runoff is not next', PREV, "['runoff', 'tied_runoff'].includes(e.verdict) && isOfficial(e) && !!e.runoff_on && day() <= e.runoff_on;", "e.verdict === 'runoff' && isOfficial(e) && !!e.runoff_on && day() <= e.runoff_on;", [V]),
 ('R69 the county\'s runoffs on your timeline', PREV, "summary() + timeline(true);", "summary() + timeline();", [V]),
 ('R70 a split several-seat race counts once', PREV, "seats(c) > 1 && v.length > 1 && v[0] !== '__skip' ? v.map(x => outcome(c, x))", "false ? v.map(x => outcome(c, x))", [T]),
 ('R71 zeros while paused', PREV, "$('dk-count').textContent = paused ? 'Results paused' : done", "$('dk-count').textContent = done", [W]),
 ('R72 a record opens on the first without a pick', PREV, "if (ui.curAuto && after() && ballot.length)", "if (false)", [T]),
 ('R73 no What\'s next on the phone', PREV, "    if (runs.length) h += '<button type=\"button\" class=\"rs-lnext\"", "    if (false) h += '<button type=\"button\" class=\"rs-lnext\"", [P]),
 ('R74 the phone list stays open', PREV, "e.target.closest('.dk-row, .rs-lnext')", "e.target.closest('.dk-row')", [P]),
 ('R75 a move says only the pick', PREV, "    if (after()) return 'Contest ' + (idx(c.id) + 1)", "    if (false) return 'Contest ' + (idx(c.id) + 1)", [T]),
 ('R76 picked rows silent to screen readers', PREV, "(A && v.length && v[0] !== '__skip' ? '<span class=\"dk-vh\"> · you picked here</span>' : '')", "''", [T]),
 ('R77 small targets on the phone', PREV, "  .dk-app .dk-link[data-rs],.rs .rs-key a{display:inline-flex;align-items:center;min-height:44px}", "", [P]),
 ('R78 no time on a narrow laptop', PREV, "  .rs-upd{display:block;margin:0;", "  .rs-upd{display:none;margin:0;", [T]),
 ('R79 skipped said twice', PREV, "v[0] === '__skip' && !(window.results && results.entry(c.id))", "v[0] === '__skip'", [T]),
 ('R80 the rest when none are official', PREV, ": off ? 'The rest are still being counted or canvassed' : 'Still being counted or canvassed')", ": 'The rest are still being counted or canvassed')", [T]),
 ('R81 W5 and W8 together', PREV, "if (cv.kind === 'state' && day() <= R.late_until)", "if (cv.kind === 'state')", [V]),
 ('R82 the printout\'s pick unlabeled', PREV, "      + '<div class=\"ln rs-prh\"><span>Contest and result</span><span>Your pick</span></div>', last = '';", "      , last = '';", [T]),
 ('R83 official without a canvass day', PREV, "    if ((e.state === 'official' || e.state === 'recount') && !cv.done) return false;", "", [X]),
 ('R84 any verdict in any state', PREV, " || !ALLOWED[e.state].includes(e.verdict)) return false;", ") return false;", [X]),
 ('R85 leading no one', PREV, "    if (['leading', 'won', 'elected', 'unopposed'].includes(e.verdict) && !e.leaders.length) return false;", "", [X]),
 ('R86 month 13', PREV, "TIME.test(x) && realDay(x) &&", "TIME.test(x) &&", [X]),
 ('R87 constructor is a contest', PREV, "Object.prototype.hasOwnProperty.call(BYID, cid) ? BYID[cid] : null", "BYID[cid]", [X]),
 ('R88 the phone count on All results', PREV, "    if (D.ui.view !== 'all') $('ph-count')", "    $('ph-count')", [P]),
]
if __name__ == '__main__':
    R.main(M)
