"""Mutation-kill check for the laptop-layout tests: every mutant must turn at least one named test RED.
Files are restored from an in-memory copy in a finally block (never git).
Run from the repo root after both builds:  python3 <this file> [first last]   (a slice of the list, e.g. 0 10)"""
import os, sys, pathlib
os.environ['BALLOTTA_PAGE'] = 'next/index.html'
ROOT = pathlib.Path.cwd()
sys.path.insert(0, str(ROOT / 'tests'))
import test_site as T
from playwright.sync_api import sync_playwright

PREV, TPL, BLD = ROOT / 'next/index.html', ROOT / 'source/template-travis.html', ROOT / 'source/build_site.py'
M = [
 ('M1 live page changes', TPL, '<title>Ballotta ·', '<title>Ballotta  ·', ['live_build_is_unchanged_until_promotion']),
 ('M2 block stripping gone', BLD, "        elif not in_block:\n            out.append(line)", "        else:\n            out.append(line)", ['live_build_is_unchanged_until_promotion']),
 ('M3 paper picks not wired', PREV, "P().querySelectorAll('[data-pick]').forEach(btn => btn.addEventListener('click', () => pick(btn.dataset.c, btn.dataset.pick)));", '', ['desk_decide_pick_keys_and_sync']),
 ('M4 shortcuts fire while typing', PREV, "if (typing) { if (e.key === 'Escape') t.blur(); return; }", '', ['desk_decide_pick_keys_and_sync']),
 ('M5 reason not mirrored to phone box', PREV, "const pw = $('w' + c.id); if (pw) pw.value = ta.value;", '', ['desk_decide_pick_keys_and_sync']),
 ('M6 candidate links dropped', PREV, "k, candLinks(L, opts[k]));", "k, '');", ['desk_learn_more_symmetric_and_measure']),
 ('M7 glance cannot clear', PREV, "if (!val) { if (v.length) pick(id, v[0]); }", "if (!val) {}", ['desk_glance_selects_and_filters']),
 ('M8 hide-unopposed ignored', PREV, "      if (ui.hideUnopp && isUnopp(c)) return;\n", '', ['desk_glance_selects_and_filters']),
 ('M9 four numbered dots', PREV, "const top = all.slice(0, 5)", "const top = all.slice(0, 4)", ['desk_where_to_vote_list_and_private_map']),
 ('M10 crib hide ignored', PREV, "cribSkip: (c) => ui.hideCrib && isUnopp(c),", "cribSkip: (c) => false,", ['desk_crib_options_and_print']),
 ('M11 app shown in print', PREV, ".dk-hdr,.dk-app,.dk-steps,.dk-fcta,.dk-back{display:none}", ".dk-steps,.dk-fcta,.dk-back{display:none}", ['desk_crib_options_and_print']),
 ('M12 menu Escape loses focus', PREV, "{ e.preventDefault(); menu(false); $('dk-help').focus(); }", "{ e.preventDefault(); menu(false); }", ['desk_help_menu_info_address_and_clear']),
 ('M13 privacy text missing', PREV, "priv.append(document.querySelector('#lookup > p.note').cloneNode(true), ", "priv.append(", ['desk_help_menu_info_address_and_clear']),
 ('M14 compare counted on phones', PREV, "if (app && friend && WIDE.matches && ui.cmpFor !== friend)", "if (app && friend && ui.cmpFor !== friend)", ['desk_stays_quiet_on_phones']),
 ('M15 compare counted per screen', PREV, "if (app && friend && WIDE.matches && ui.cmpFor !== friend)", "if (app && friend && WIDE.matches)", ['desk_compare_counted_once_per_link']),
 ('M15b compare counted per reload', PREV, "if (!(k && list.includes(k))) {", "if (true) {", ['desk_compare_counted_once_per_link']),
 ('M16 refresh hook gone', PREV, "renderCompare();/*DESK*/ if (window.desk) try { desk.refresh(); } catch (e) {}/*/DESK*/", "renderCompare();", ['desk_glance_selects_and_filters', 'desk_decide_pick_keys_and_sync']),
 ('M16b no redraw on resize', PREV, "  WIDE.addEventListener('change', () => {", "  WIDE.addEventListener('change-never', () => {", ['desk_resize_keeps_layouts_in_step']),
 ('M17 friend reason unescaped', PREV, "' · “' + esc(friend.W[c.id]) + '”'", "' · “' + friend.W[c.id] + '”'", ['desk_hostile_friend_is_escaped']),
 ('M18 dialogs stay bottom sheets', PREV, "  dialog.sheet{max-width:520px;margin:auto;border-radius:16px;padding:24px 28px}\n", '', ['desk_share_and_keep_open_as_centered_windows']),
 ('M19 ballot hook gone', PREV, "renderVote();/*DESK*/ if (window.desk) try { desk.ballot(meta); } catch (e) {}/*/DESK*/", "renderVote();", ['desk_layout_header_and_rail', 'desk_restore_link_on_laptop']),
 ('M20 street saved', PREV, "      if (idx(ui.cur) < 0) ui.cur = (nextUndecided('') || ballot[0]).c.id;", "      LS.set('ballotta.addr', ui.addr); if (idx(ui.cur) < 0) ui.cur = (nextUndecided('') || ballot[0]).c.id;", ['desk_layout_header_and_rail']),
 ('M21 friend hook gone', PREV, "  }/*DESK*/ if (window.desk) try { desk.render(); } catch (e) {}/*/DESK*/\n}\nlet wantCompare", "  }\n}\nlet wantCompare", ['desk_friend_link_landing_and_inline']),
 ('M25 compare counted before open', PREV, "  f.classList.remove('hidden');\n", "  f.classList.remove('hidden'); if (window.desk) desk.render();\n", ['desk_friend_link_with_saved_ballot_counts_in_order']),
 ('M26 focus lost after Help window', PREV, "menu(false); $('dk-help').focus();  //", "menu(false);  //", ['desk_help_menu_info_address_and_clear']),
 ('M27 menu stays open after Tab', PREV, "    if (a && a !== document.body && !a.closest('.dk-menuwrap')) menu(false);", "", ['desk_help_menu_info_address_and_clear']),
 ('M29 hiding a friend leaves the landing broken', PREV, "  $('friend').addEventListener('click', (e) => { if (e.target.closest('#f-hide')) render(); });", "", ['desk_friend_hide_on_landing']),
 ('M30 Escape only inside the list', PREV, "    if (e.key === 'Escape' && !$('dk-menu').classList.contains('hidden')) { e.preventDefault(); menu(false); $('dk-help').focus(); }", "", ['desk_help_menu_info_address_and_clear']),
 ('M22 phone takes laptop shortcuts', PREV, "if (!WIDE.matches || !ballot.length || ui.landing", "if (!ballot.length || ui.landing", ['desk_stays_quiet_on_phones']),
 ('M24 phone spacing lost', PREV, "#start{display:flex;flex-direction:column;gap:18px}", '', ['desk_phone_layout_matches_live_page']),
 ('M31 non-text reason throws', PREV, "typeof whys[cid] === 'string' && whys[cid].trim() !== ''", "!!(whys[cid] && whys[cid].trim())", ['desk_failures_never_break_the_phone_flow']),
 ('M32 hook unguarded', PREV, "if (window.desk) try { desk.ballot(meta); } catch (e) {}", "if (window.desk) desk.ballot(meta);", ['desk_failures_never_break_the_phone_flow']),
 ('M33 compare without a shared race', PREV, "      if (Object.keys(friend.P).some(id => mine.has(id))) {\n        ui.cmpFor = friend;", "      if (true) {\n        ui.cmpFor = friend;", ['desk_compare_counted_once_per_link']),
 ('M34 print options follow to phone', PREV, "ui.two = ui.hideCrib = false; $('crib').classList.remove('two'); renderCrib(); }  // laptop-only", "}  // laptop-only", ['desk_crib_options_and_print']),
 ('M35 held key flickers', PREV, "    if (e.repeat && (/^[1-9]$/.test(k) || k === 's')) return;  // a held key picks once (pick() toggles)\n", '', ['desk_decide_pick_keys_and_sync']),
 ('M36 J drops focus', PREV, "go(ballot[i + 1].c.id, true); }", "go(ballot[i + 1].c.id); }", ['desk_decide_pick_keys_and_sync']),
 ('M37 odd whitespace after a close accepted', BLD, "        elif ALONE_CLOSE.fullmatch(line):", "        elif re.fullmatch(CLOSE, line.strip()):", ['live_build_is_unchanged_until_promotion']),
 ('M38 printing resets the options', PREV, "!printing && !matchMedia('print').matches && ", "", ['desk_crib_options_and_print']),
 ('M39 a first no-overlap view blocks the count', PREV, "      const mine = new Set(ballot.map(b => b.c.id)), k = friend.code", "      ui.cmpFor = friend; const mine = new Set(ballot.map(b => b.c.id)), k = friend.code", ['desk_compare_counted_once_per_link']),
 ('M40 laptop compare looks like a phone tap', PREV, "track('share_compare', { layout: 'laptop' })", "track('share_compare', {})", ['desk_compare_counted_once_per_link']),
 ('M41 stray marker inside a block accepted', BLD, "            assert not re.search(OPEN + '|' + CLOSE, line), f\"line {n}: a DESK marker inside a block isn't alone on its line\"", "            pass", ['live_build_is_unchanged_until_promotion']),
 ('M42 print flag can stick', PREV, "  ['pointerdown', 'keydown'].forEach(ev => window.addEventListener(ev, () => { printing = false; }, true));", "", ['desk_crib_options_and_print']),
 ('M43 laptop box does not grow', PREV, "      fit(ta);\n      whys[c.id] = ta.value;", "      whys[c.id] = ta.value;", ['desk_why_box_grows_with_the_reason']),
 ('M23 card and notes drift apart', PREV, "column-gap:clamp(24px,calc((100% - 992px) / 3),32px);", "column-gap:calc((100% - 992px) / 3);", ['desk_layout_header_and_rail']),
 ('M28 no gutters at 1280', PREV, "justify-content:center;gap:24px;column-gap:clamp(24px,calc((100% - 992px) / 3),32px);align-items:start;min-width:0;padding:28px 24px 64px}", "justify-content:center;align-items:start;min-width:0;padding:28px 0 64px}", ['desk_layout_header_and_rail']),
 ('M44 long saved reason opens squashed', PREV, "    fit(ta);\n    ta.addEventListener('input', () => {", "    ta.addEventListener('input', () => {", ['desk_why_box_grows_with_the_reason']),
 ('M45 typing at the bottom jumps the page', PREV, "    card.style.minHeight = card.offsetHeight + 'px';\n", "", ['desk_why_box_grows_with_the_reason']),
 ('M46 reason card not a card', PREV, "gap:10px;background:var(--ground);border:1px solid var(--line);border-radius:12px;padding:14px 16px 16px;margin-top:6px}", "gap:8px}", ['desk_why_box_grows_with_the_reason']),
]
if len(sys.argv) > 2: M = M[int(sys.argv[1]):int(sys.argv[2])]   # run the list in slices if a shell caps how long a command may take
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
            f.write_text(orig.replace(a, z), encoding='utf-8')
            try:
                killed = []
                for tn in tests:
                    try: getattr(T, tn)(b)
                    except Exception as e: killed.append(tn + ':' + type(e).__name__)   # AssertionError, or a Playwright timeout
                res.append((name, 'KILLED' if killed else 'SURVIVED', ','.join(killed)))
            finally:
                f.write_text(orig, encoding='utf-8')
            # A kill counts only if the same tests pass again on the restored file (a service hiccup fails both).
            for tn in [k.split(':')[0] for k in killed]:
                try: getattr(T, tn)(b)
                except Exception as e: raise SystemExit(f'INCONCLUSIVE {name}: {tn} also fails unmutated ({type(e).__name__}); rerun later')
            print(*res[-1], flush=True)
        b.close()
finally:
    srv.shutdown()
print(sum(r[1] == 'KILLED' for r in res), 'of', len(res), 'mutants killed')
