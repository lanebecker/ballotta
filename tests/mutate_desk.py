"""Mutation-kill check for the laptop-layout tests: every mutant must turn at least one named test RED.
Files are restored from an in-memory copy in a finally block (never git).
Run from the repo root after both builds:  python3 <this file> [first last]   (a slice of the list, e.g. 0 10)"""
import os, sys, pathlib, signal
def _stop(sig, _frame):                                    # a timeout's kill still runs the restore in `finally` (Pass 1);
    for s_ in (signal.SIGTERM, signal.SIGHUP): signal.signal(s_, signal.SIG_IGN)   # a second signal can't interrupt it (Pass 2)
    sys.exit(128 + sig)
signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGHUP, _stop)
def put(f, text):                                          # write whole or not at all: never a half-written page
    tmp = f.with_name(f.name + '.mutate-tmp'); tmp.write_text(text, encoding='utf-8'); os.replace(tmp, f)
ROOT = pathlib.Path.cwd()
LIVE = '\nDESK_LIVE = True\n' in (ROOT / 'source/build_site.py').read_text(encoding='utf-8')     # the setting's own line, not the comment
os.environ['BALLOTTA_PAGE'] = 'index.html' if LIVE else 'next/index.html'   # after promotion the laptop layout is the live page
sys.path.insert(0, str(ROOT / 'tests'))
import test_site as T
from playwright.sync_api import sync_playwright

PREV, TPL, BLD = ROOT / os.environ['BALLOTTA_PAGE'], ROOT / 'source/template-travis.html', ROOT / 'source/build_site.py'
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
 ('M11 app shown in print', PREV, ".dk-hdr,.dk-app,.dk-steps,.dk-fcta,.dk-back,.dk-hero,.dk-faq{display:none}", ".dk-steps,.dk-fcta,.dk-back,.dk-hero,.dk-faq{display:none}", ['desk_crib_options_and_print']),
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
 ('M24 phone spacing lost', TPL, "#start{display:flex;flex-direction:column;gap:18px}", '', ['desk_phone_layout_matches_live_page']),
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
 ('L1 band not plum', PREV, ".dk-hero{flex-direction:column;align-items:center;gap:14px;background:var(--plum);", ".dk-hero{flex-direction:column;align-items:center;gap:14px;", ['desk_landing_plum_band_and_faq']),
 ('L2 plum corner box stays', PREV, "  body:not(.dk-app-on) .dk-hdr::before,body:not(.dk-app-on) .dk-brand{display:none}\n", "", ['desk_landing_plum_band_and_faq']),
 ('L3 top bar lilac on the landing', PREV, "  body:not(.dk-app-on) .dk-hdr{background:var(--plum);padding-left:24px}\n", "", ['desk_landing_plum_band_and_faq']),
 ('L4 no gold strip', PREV, "padding:9px 24px;background:var(--gold);color:var(--ink)", "padding:9px 24px;color:var(--ink)", ['desk_landing_plum_band_and_faq']),
 ('L5 small logo', PREV, "font-size:80px;line-height:1;color:var(--ground)}", "font-size:40px;line-height:1;color:var(--ground)}", ['desk_landing_plum_band_and_faq']),
 ('L6 paper does not overlap the band', PREV, "  body:not(.dk-app-on) .wrap{margin-top:-96px;padding-top:0}\n", "", ['desk_landing_plum_band_and_faq']),
 ('L7 side column on the plum', PREV, ".dk-steps,body.dk-friend #start{margin-top:112px}", ".dk-steps,body.dk-friend #start{margin-top:0}", ['desk_landing_plum_band_and_faq']),
 ('L8 FAQ hidden', PREV, "  body:not(.dk-app-on) .dk-faq{display:flex}\n", "", ['desk_landing_plum_band_and_faq']),
 ('L9 FAQ on phones', PREV, ".dk-back,.dk-hero,.dk-faq{display:none}", ".dk-back,.dk-hero{display:none}", ['desk_landing_plum_band_and_faq', 'desk_phone_layout_matches_live_page']),
 ('L10 band shown in the app', PREV, "  body:not(.dk-app-on) .dk-hero{display:flex}", "  .dk-hero{display:flex}", ['desk_landing_plum_band_and_faq']),
 ('L11 Share my picks vanishes on plum', PREV, "  body:not(.dk-app-on) .dk-btn.pri{background:var(--gold);border-color:var(--gold);color:var(--ink)}", "", ['desk_landing_plum_band_and_faq']),
 ('L12 address dark on plum', PREV, "  body:not(.dk-app-on) .dk-loc,body:not(.dk-app-on) .dk-loc b{color:var(--ground)}\n", "", ['desk_landing_plum_band_and_faq']),
 ('L13 date dark on plum', PREV, "  body:not(.dk-app-on) .dk-when{color:var(--lilac)}\n", "", ['desk_landing_plum_band_and_faq']),
 ('L14 description too faint', PREV, ".dk-sub{font-size:17px;max-width:680px;color:var(--lilac)}", ".dk-sub{font-size:17px;max-width:680px;color:var(--lc)}", ['desk_landing_plum_band_and_faq']),
 ('L15 FAQ link without noopener', PREV, 'target="_blank" rel="noopener">VoteTravis.gov</a> before you vote.', 'target="_blank">VoteTravis.gov</a> before you vote.', ['desk_landing_plum_band_and_faq']),
 ('L16 tagline not Lane\'s', PREV, '<p class="dk-tagline">Don’t wait to meet your ballot in the booth.</p>', '<p class="dk-tagline">Your ballot, considered together.</p>', ['desk_landing_plum_band_and_faq']),
 ('L17 a FAQ answer dropped', PREV, '<div class="dk-q"><h3>Is this official?</h3>', '<div class="dk-q" style="display:none"><h3>Is this official?</h3>', ['desk_landing_plum_band_and_faq']),
 ('L18 band too tall for short windows', PREV, "@media screen and (min-width:1024px) and (max-height:880px){", "@media screen and (min-width:1024px) and (max-height:1px){", ['desk_landing_plum_band_and_faq']),
 ('L19 privacy answer skips the Census', PREV, "Travis County’s map server (and, if the county can’t match it, the U.S. Census geocoder); we never receive it.", "the county’s map server; we never receive it.", ['desk_landing_plum_band_and_faq']),
 ('L20 description overclaims', PREV, "learn about the races from neutral sources, make your picks", "learn about every race from neutral sources, make your picks", ['desk_landing_plum_band_and_faq']),
 ('L21 see-through description', PREV, ".dk-sub{font-size:17px;max-width:680px;color:var(--lilac)}", ".dk-sub{font-size:17px;max-width:680px;color:rgba(234,220,245,.18)}", ['desk_landing_plum_band_and_faq']),
 ('L22 compact cutoff too low for Change address', PREV, "(min-width:1024px) and (max-height:880px){", "(min-width:1024px) and (max-height:820px){", ['desk_landing_plum_band_and_faq']),
 ('L23 faded band', PREV, ".dk-hero{flex-direction:column;align-items:center;", ".dk-hero{opacity:.5;flex-direction:column;align-items:center;", ['desk_landing_plum_band_and_faq']),
 ('F1 rail titles cut off', PREV, '.dk-rt b{font-size:13px;font-weight:600;line-height:1.3;color:#fff;overflow-wrap:anywhere}', '.dk-rt b{font-size:13px;font-weight:600;line-height:1.3;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}', ['desk_launch_audit_fixes']),
 ('F3 damaged-link notice not wired', PREV, '/*DESK*/ if (window.desk) try { desk.say(t); } catch (e) {}/*/DESK*/', '', ['desk_launch_audit_fixes']),
 ('F4 shortcuts fire on any button', PREV, "    if (t && t !== document.body && !t.closest('#dk-paper')) return;", '', ['desk_launch_audit_fixes']),
 ('F5 picks by key not announced', PREV, 'pick(b.c.id, o); announce(b.c);', 'pick(b.c.id, o);', ['desk_launch_audit_fixes']),
 ('F6 no main landmark', PREV, 'id="dk-desk" role="main"', 'id="dk-desk"', ['desk_launch_audit_fixes']),
 ('F7 paper focus invisible', PREV, '  .dk-paper:focus-visible{outline:3px solid var(--plum);outline-offset:4px}', '', ['desk_launch_audit_fixes']),
 ('F8 key hints on touch screens', PREV, '  .kbd,.dk-keysec{display:none}', '  .dk-keysec{display:none}', ['desk_launch_audit_fixes']),
 ('F9 notice cannot be dismissed', PREV, "\n  $('dk-say').querySelector('button').addEventListener('click', () => $('dk-say').classList.add('hidden'));", '', ['desk_launch_audit_fixes']),
 ('F11 old warning survives a good link', PREV, "$('lookupmsg').classList.add('hidden');/*DESK*/ if (window.desk) try { desk.say(''); } catch (e) {}/*/DESK*/", "$('lookupmsg').classList.add('hidden');", ['desk_launch_audit_fixes']),
 ('F12 keys dead after switching views', PREV, "if (v === 'decide' && toPaper) P().focus({ preventScroll: true });", "", ['desk_launch_audit_fixes']),
 ('F13 slash fires off the paper', PREV, "    if (t && t !== document.body && !t.closest('#dk-paper')) return;  // single-key shortcuts only on the ballot paper (WCAG 2.1.4, audit #30)\n    if (k === '/') { e.preventDefault(); $('dk-q').focus(); return; }", "    if (k === '/') { e.preventDefault(); $('dk-q').focus(); return; }\n    if (t && t !== document.body && !t.closest('#dk-paper')) return;", ['desk_launch_audit_fixes']),
 ('F17 warning kept through Change address', PREV, "ui.landing = true; $('dk-say').classList.add('hidden'); render();", "ui.landing = true; render();", ['desk_launch_audit_fixes']),
 ('F18 keyboard Decide jumps to the paper', PREV, "setView(btn.dataset.view, e.detail > 0)", "setView(btn.dataset.view, true)", ['desk_launch_audit_fixes']),
 ('F19 warning off screen when scrolled', PREV, "      if (WIDE.matches && box.getBoundingClientRect().top < 56) window.scrollTo(0, 0);", "", ['desk_launch_audit_fixes']),
 ('F14 notice floats over the paper', PREV, ".dk-say{grid-column:1/-1;display:flex;", ".dk-say{position:fixed;top:68px;left:400px;z-index:25;display:flex;", ['desk_launch_audit_fixes']),
 ('F15 warning shown under the landing', PREV, "if (!t || !document.body.classList.contains('dk-app-on')) return;", "if (!t) return;", ['desk_launch_audit_fixes']),
 ('F16 focus ring on mouse clicks', PREV, ".dk-paper:focus-visible{outline", ".dk-paper:focus{outline", ['desk_launch_audit_fixes']),
 ('F10 skip not announced', PREV, "pick(b.c.id, '__skip'); announce(b.c);", "pick(b.c.id, '__skip');", ['desk_launch_audit_fixes']),
]
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
