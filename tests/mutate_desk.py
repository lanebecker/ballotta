"""Mutation-kill check for the laptop-layout tests: every mutant must turn at least one named test RED.
Files are restored from an in-memory copy in a finally block (never git).
Run from the repo root after both builds:  python3 <this file> [first last]   (a slice of the list, e.g. 0 10)"""
import os, sys, pathlib, signal
SIGS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)
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
ROOT = pathlib.Path.cwd()
LIVE = '\nDESK_LIVE = True\n' in (ROOT / 'source/build_site.py').read_text(encoding='utf-8')     # the setting's own line, not the comment
os.environ['BALLOTTA_PAGE'] = os.environ.get('BALLOTTA_MUTATE_PAGE') or ('index.html' if LIVE else 'next/index.html')   # mutate_phone.py sets its own page
sys.path.insert(0, str(ROOT / 'tests'))
import test_site as T
from playwright.sync_api import sync_playwright

PREV, TPL, BLD = ROOT / os.environ['BALLOTTA_PAGE'], ROOT / 'source/template-travis.html', ROOT / 'source/build_site.py'
README = ROOT / 'README.md'
LEARN = ROOT / 'source/learn.json'
MD_SELF = ROOT / 'tests/mutate_desk.py'                    # the runner's own signal handling (#41), tested in a child process
# Retired at promotion (Oct 17), each verified equivalent on the promoted page: M34, M38, M42 sit behind
# `/*PHONE*/false && /*/PHONE*/` (print options now survive a narrow window by design); M16b's redraw on resize is
# redundant now that one DOM and one render serve both widths; M31's string check is redundant because every
# path that writes a reason keeps text only (the load filter, restore and the two reason boxes).
# Also retired then: A30-A33 and R6 (the old phone page's footer button, now inside the hidden legacy page) and R5
# (the paper is redrawn from the picks, so a cleared limit note can't linger). The laptop half of the retired
# extra_pick_is_explained, the build half of page_is_locked_down and #40's notice came back as their own tests.
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
 ('M10 crib hide ignored', PREV, "cribSkip: (c) => ui.hideCrib && isUnopp(c),", "cribSkip: (c) => false,", ['laptop_crib_options_and_print_go_to_the_phone']),
 ('M11 app shown in print', PREV, ".dk-hdr,.dk-app,.dk-steps,.dk-fcta,.dk-back,.dk-hero,.dk-faq{display:none}", ".dk-steps,.dk-fcta,.dk-back,.dk-hero,.dk-faq{display:none}", ['laptop_crib_options_and_print_go_to_the_phone']),
 ('M12 menu Escape loses focus', PREV, "{ e.preventDefault(); menu(false); $('dk-help').focus(); }", "{ e.preventDefault(); menu(false); }", ['desk_help_menu_info_address_and_clear']),
 ('M13 privacy text missing', PREV, "priv.append(document.querySelector('#lookup > p.note').cloneNode(true), ", "priv.append(", ['desk_help_menu_info_address_and_clear']),
 ('M14 compare not counted on phones (counted at any width since promotion)', PREV, "if (app && friend && /*PHONE*/(true || /*/PHONE*/WIDE.matches/*PHONE*/)/*/PHONE*/ && ui.cmpFor", "if (app && friend && WIDE.matches && ui.cmpFor", ['phone_share_friend_compare_and_events']),
 ('M15 compare counted per screen', PREV, "/*/PHONE*/ && ui.cmpFor !== friend)", "/*/PHONE*/)", ['desk_compare_counted_once_per_link']),
 ('M15b compare counted per reload', PREV, "if (!(k && list.includes(k))) {", "if (true) {", ['desk_compare_counted_once_per_link']),
 ('M16 refresh hook gone', PREV, "renderCompare();/*DESK*/ if (window.desk) try { desk.refresh(); } catch (e) {}/*/DESK*/", "renderCompare();", ['desk_glance_selects_and_filters', 'desk_decide_pick_keys_and_sync']),
 ('M17 friend reason unescaped', PREV, "' · “' + esc(friend.W[c.id]) + '”'", "' · “' + friend.W[c.id] + '”'", ['desk_hostile_friend_is_escaped']),
 ('M18 dialogs stay bottom sheets', PREV, "  dialog.sheet{max-width:520px;margin:auto;border-radius:16px;padding:24px 28px}\n", '', ['desk_share_and_keep_open_as_centered_windows']),
 ('M19 ballot hook gone', PREV, "renderVote();/*DESK*/ if (window.desk) try { desk.ballot(meta); } catch (e) {}/*/DESK*/", "renderVote();", ['desk_layout_header_and_rail', 'desk_restore_link_on_laptop']),
 ('M20 street saved', PREV, "      if (idx(ui.cur) < 0) ui.cur = (nextUndecided('') || ballot[0]).c.id;", "      LS.set('ballotta.addr', ui.addr); if (idx(ui.cur) < 0) ui.cur = (nextUndecided('') || ballot[0]).c.id;", ['desk_layout_header_and_rail']),
 ('M21 friend hook gone', PREV, "  }/*DESK*/ if (window.desk) try { desk.render(); } catch (e) {}/*/DESK*/\n}\nlet wantCompare", "  }\n}\nlet wantCompare", ['desk_friend_link_landing_and_inline']),
 ('M25 compare counted before open', PREV, "  f.classList.remove('hidden');\n", "  f.classList.remove('hidden'); if (window.desk) desk.render();\n", ['desk_friend_link_with_saved_ballot_counts_in_order']),
 ('M26 focus lost after Help window', PREV, "menu(false); $('dk-help').focus();  //", "menu(false);  //", ['desk_help_menu_info_address_and_clear']),
 ('M27 menu stays open after Tab', PREV, "    if (a && a !== document.body && !a.closest('.dk-menuwrap')) menu(false);", "", ['desk_help_menu_info_address_and_clear']),
 ('M30 Escape only inside the list', PREV, "    if (e.key === 'Escape' && !$('dk-menu').classList.contains('hidden')) { e.preventDefault(); menu(false); $('dk-help').focus(); }", "", ['desk_help_menu_info_address_and_clear']),
 ('M22 phone takes laptop shortcuts', PREV, "if (!WIDE.matches || !ballot.length || ui.landing", "if (!ballot.length || ui.landing", ['phone_takes_no_laptop_shortcuts']),
 ('M24 phone spacing lost', TPL, "#start{display:flex;flex-direction:column;gap:18px}", '', ['desk_phone_layout_matches_live_page']),
 ('M32 hook unguarded', PREV, "if (window.desk) try { desk.ballot(meta); } catch (e) {}", "if (window.desk) desk.ballot(meta);", ['phone_junk_and_hook_failures_never_break_the_lookup']),
 ('M33 compare without a shared race', PREV, "      if (Object.keys(friend.P).some(id => mine.has(id))) {\n        ui.cmpFor = friend;", "      if (true) {\n        ui.cmpFor = friend;", ['desk_compare_counted_once_per_link']),
 ('M35 held key flickers', PREV, "    if (e.repeat && (/^[1-9]$/.test(k) || k === 's')) return;  // a held key picks once (pick() toggles)\n", '', ['desk_decide_pick_keys_and_sync']),
 ('M36 J drops focus', PREV, "go(ballot[i + 1].c.id, true); used('move'); }", "go(ballot[i + 1].c.id); used('move'); }", ['desk_decide_pick_keys_and_sync']),
 ('M37 odd whitespace after a close accepted', BLD, "        elif ALONE_CLOSE.fullmatch(line):", "        elif re.fullmatch(CLOSE, line.strip()):", ['live_build_is_unchanged_until_promotion']),
 ('M39 a first no-overlap view blocks the count', PREV, "      const mine = new Set(ballot.map(b => b.c.id)), k = friend.code", "      ui.cmpFor = friend; const mine = new Set(ballot.map(b => b.c.id)), k = friend.code", ['desk_compare_counted_once_per_link']),
 ('M40 laptop compare counted twice', PREV, "track('share_compare');", "track('share_compare'); track('share_compare');", ['desk_compare_counted_once_per_link']),
 ('M41 stray marker inside a block accepted', BLD, "            assert not re.search(OPEN + '|' + CLOSE, line), f\"line {n}: a {tag} marker inside a block isn't alone on its line\"", "            pass", ['live_build_is_unchanged_until_promotion']),
 ('M43 laptop box does not grow', PREV, "      fit(ta);\n      whys[c.id] = ta.value;", "      whys[c.id] = ta.value;", ['laptop_and_phone_why_box_grows_with_the_reason']),
 ('M23 card and notes drift apart', PREV, "column-gap:clamp(24px,calc((100% - 992px) / 3),32px);", "column-gap:calc((100% - 992px) / 3);", ['desk_layout_header_and_rail']),
 ('M28 no gutters at 1280', PREV, "justify-content:center;gap:24px;column-gap:clamp(24px,calc((100% - 992px) / 3),32px);align-items:start;min-width:0;padding:28px 24px 64px}", "justify-content:center;align-items:start;min-width:0;padding:28px 0 64px}", ['desk_layout_header_and_rail']),
 ('M44 long saved reason opens squashed', PREV, "    fit(ta);\n    ta.addEventListener('input', () => {", "    ta.addEventListener('input', () => {", ['laptop_and_phone_why_box_grows_with_the_reason']),
 ('M45 typing at the bottom jumps the page', PREV, "    card.style.minHeight = card.offsetHeight + 'px';\n", "", ['laptop_and_phone_why_box_grows_with_the_reason']),
 ('M46 reason card not a card', PREV, "gap:10px;background:var(--ground);border:1px solid var(--line);border-radius:12px;padding:14px 16px 16px;margin-top:6px}", "gap:8px}", ['laptop_and_phone_why_box_grows_with_the_reason']),
 ('L1 band not plum', PREV, ".dk-hero{flex-direction:column;align-items:center;gap:14px;background:var(--plum);", ".dk-hero{flex-direction:column;align-items:center;gap:14px;", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L2 plum corner box stays', PREV, "  body:not(.dk-app-on) .dk-hdr::before,body:not(.dk-app-on) .dk-brand{display:none}\n", "", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L3 top bar lilac on the landing', PREV, "  body:not(.dk-app-on) .dk-hdr{background:var(--plum);padding-left:24px}\n", "", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L4 no gold strip', PREV, "padding:9px 24px;background:var(--gold);color:var(--ink)", "padding:9px 24px;color:var(--ink)", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L5 small logo', PREV, "font-size:80px;line-height:1;color:var(--ground)}", "font-size:40px;line-height:1;color:var(--ground)}", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L6 paper does not overlap the band', PREV, "  body:not(.dk-app-on) .wrap{margin-top:-96px;padding-top:0}\n", "", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L7 side column on the plum', PREV, ".dk-steps,body.dk-friend #start{margin-top:112px}", ".dk-steps,body.dk-friend #start{margin-top:0}", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L8 FAQ hidden', PREV, "  body:not(.dk-app-on) .dk-faq{display:flex}\n", "", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L9 FAQ on phones', PREV, ".dk-back,.dk-hero,.dk-faq{display:none}", ".dk-back,.dk-hero{display:none}", ['laptop_and_phone_landing_plum_band_and_faq', 'desk_phone_layout_matches_live_page']),
 ('L10 band shown in the app', PREV, "on the plum bar */\n  body:not(.dk-app-on) .dk-hero{display:flex}", "on the plum bar */\n  .dk-hero{display:flex}", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L11 Share my picks vanishes on plum', PREV, "  body:not(.dk-app-on) .dk-btn.pri{background:var(--gold);border-color:var(--gold);color:var(--ink)}", "", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L12 address dark on plum', PREV, "  body:not(.dk-app-on) .dk-loc,body:not(.dk-app-on) .dk-loc b{color:var(--ground)}\n", "", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L13 date dark on plum', PREV, "  body:not(.dk-app-on) .dk-when{color:var(--lilac)}\n", "", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L14 description too faint', PREV, ".dk-sub{font-size:17px;max-width:680px;color:var(--lilac)}", ".dk-sub{font-size:17px;max-width:680px;color:var(--lc)}", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L15 FAQ link without noopener', PREV, 'target="_blank" rel="noopener">VoteTravis.gov</a> before you vote.', 'target="_blank">VoteTravis.gov</a> before you vote.', ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L16 tagline not Lane\'s', PREV, '<p class="dk-tagline">Don’t wait to meet your ballot in the booth.</p>', '<p class="dk-tagline">Your ballot, considered together.</p>', ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L17 a FAQ answer dropped', PREV, '<div class="dk-q"><h3>Is this official?</h3>', '<div class="dk-q" style="display:none"><h3>Is this official?</h3>', ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L18 band too tall for short windows', PREV, "@media screen and (min-width:1024px) and (max-height:880px){", "@media screen and (min-width:1024px) and (max-height:1px){", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L19 privacy answer skips the Census', PREV, "Travis County’s map server (and, if the county can’t match it, the U.S. Census geocoder); we never receive it.", "the county’s map server; we never receive it.", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L20 description overclaims', PREV, "learn about the races from neutral sources, make your picks", "learn about every race from neutral sources, make your picks", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L21 see-through description', PREV, ".dk-sub{font-size:17px;max-width:680px;color:var(--lilac)}", ".dk-sub{font-size:17px;max-width:680px;color:rgba(234,220,245,.18)}", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L22 compact cutoff too low for Change address', PREV, "(min-width:1024px) and (max-height:880px){", "(min-width:1024px) and (max-height:820px){", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('L23 faded band', PREV, ".dk-hero{flex-direction:column;align-items:center;", ".dk-hero{opacity:.5;flex-direction:column;align-items:center;", ['laptop_and_phone_landing_plum_band_and_faq']),
 ('F1 rail titles cut off', PREV, '.dk-rt b{font-size:13px;font-weight:600;line-height:1.3;color:#fff;overflow-wrap:anywhere}', '.dk-rt b{font-size:13px;font-weight:600;line-height:1.3;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}', ['desk_launch_audit_fixes']),
 ('F3 damaged-link notice not wired', PREV, '/*DESK*/ if (window.desk) try { desk.say(t); } catch (e) {}/*/DESK*/', '', ['desk_launch_audit_fixes']),
 ('F4 shortcuts fire on any button', PREV, "    if (t && t !== document.body && !t.closest('#dk-paper')) return;", '', ['desk_launch_audit_fixes']),
 ('F5 picks by key not announced', PREV, 'if (pick(b.c.id, o) !== false) announce(b.c);', 'pick(b.c.id, o);', ['desk_launch_audit_fixes']),
 ('F6 no main landmark', PREV, 'id="dk-desk" role="main"', 'id="dk-desk"', ['desk_launch_audit_fixes']),
 ('F7 paper focus invisible', PREV, '  .dk-paper:focus-visible{outline:3px solid var(--plum);outline-offset:4px}', '', ['desk_launch_audit_fixes']),
 ('F8 key hints on touch screens', PREV, '  .kbd,.dk-keysec{display:none}  /* touch screens', '  .dk-keysec{display:none}  /* touch screens', ['desk_launch_audit_fixes']),
 ('F9 notice cannot be dismissed', PREV, "\n  $('dk-say').querySelector('button').addEventListener('click', () => $('dk-say').classList.add('hidden'));", '', ['desk_launch_audit_fixes']),
 ('F12 keys dead after switching views', PREV, "if (v === 'decide' && toPaper) P().focus({ preventScroll: true });", "", ['desk_launch_audit_fixes']),
 ('F13 slash fires off the paper', PREV, "    if (t && t !== document.body && !t.closest('#dk-paper')) return;  // single-key shortcuts only on the ballot paper (WCAG 2.1.4, audit #30)\n    const used = (kind) => countOnce('k:' + kind, 'shortcut_used', { kind });\n    if (k === '/') { e.preventDefault(); $('dk-q').focus(); used('search'); return; }", "    const used = (kind) => countOnce('k:' + kind, 'shortcut_used', { kind });\n    if (k === '/') { e.preventDefault(); $('dk-q').focus(); used('search'); return; }\n    if (t && t !== document.body && !t.closest('#dk-paper')) return;  // single-key shortcuts only on the ballot paper (WCAG 2.1.4, audit #30)", ['desk_launch_audit_fixes']),
 ('F17 warning kept through Change address', PREV, "ui.landing = true; $('dk-say').classList.add('hidden'); render();", "ui.landing = true; render();", ['desk_launch_audit_fixes']),
 ('F18 keyboard Decide jumps to the paper', PREV, "setView(btn.dataset.view, e.detail > 0)", "setView(btn.dataset.view, true)", ['desk_launch_audit_fixes']),
 ('F19 warning off screen when scrolled', PREV, "      if (WIDE.matches && box.getBoundingClientRect().top < 56) window.scrollTo(0, 0);", "", ['desk_launch_audit_fixes']),
 ('F14 notice floats over the paper', PREV, ".dk-say{grid-column:1/-1;display:flex;", ".dk-say{position:fixed;top:68px;left:400px;z-index:25;display:flex;", ['desk_launch_audit_fixes']),
 ('F15 warning shown under the landing', PREV, "if (!t || !document.body.classList.contains('dk-app-on')) return;", "if (!t) return;", ['desk_launch_audit_fixes']),
 ('F16 focus ring on mouse clicks', PREV, ".dk-paper:focus-visible{outline", ".dk-paper:focus{outline", ['desk_launch_audit_fixes']),
 ('F10 skip not announced', PREV, "pick(b.c.id, '__skip'); announce(b.c);", "pick(b.c.id, '__skip');", ['desk_launch_audit_fixes']),
 ('V1 unlisted events let through', PREV, "if (typeof name !== 'string' || !has(EVENTS, name)) { dropped.push(String(name)); return null; }", "if (typeof name !== 'string') return null;", ['privacy_firewall_drops_anything_unlisted']),
 ('V2 unlisted details kept', PREV, "if (ok) out[k] = v; else dropped.push(name + '.' + k);", 'out[k] = v;', ['privacy_firewall_drops_anything_unlisted']),
 ('V3 values not checked', PREV, 'has(spec, k) && spec[k](String(v))', 'has(spec, k)', ['privacy_firewall_drops_anything_unlisted']),
 ('V4 objects allowed as values', PREV, "(typeof v === 'string' || typeof v === 'number') && ", '', ['privacy_firewall_drops_anything_unlisted']),
 ('V5 Global Privacy Control ignored', PREV, 'navigator.globalPrivacyControl === true || ', '', ['privacy_firewall_drops_anything_unlisted']),
 ('V6 Do Not Track ignored', PREV, "navigator.doNotTrack === '1' || ", '', ['privacy_firewall_drops_anything_unlisted']),
 ('V7 before-send ignores the off switch', PREV, "  if (NO_COUNT || !p || typeof p !== 'object' || (type", "  if (!p || typeof p !== 'object' || (type", ['privacy_firewall_drops_anything_unlisted']),
 ('V8 extra fields kept', PREV, "  TOP.forEach(k => { if (typeof p[k] === 'string') out[k] = k === 'url' ? p[k].split(/[?#]/)[0] : k === 'referrer' ? siteOf(p[k]) : p[k]; });", '  Object.assign(out, p);', ['privacy_firewall_drops_anything_unlisted', 'real_tracker_sends_only_listed_events']),
 ('V9 before-send skips the list', PREV, '  if (out.name !== undefined) { const d = clean(out.name, p.data); if (!d) return null; out.data = d; }', '  if (out.name !== undefined) out.data = p.data;', ['privacy_firewall_drops_anything_unlisted']),
 ('V10 track ignores the off switch', PREV, '  if (NO_COUNT) return;\n  const d = clean(name', '  const d = clean(name', ['privacy_firewall_drops_anything_unlisted']),
 ('V11 no layout on events', PREV, "{ layout: window.desk && matchMedia('(min-width: 1024px)').matches ? 'laptop' : 'phone' }", '{}', ['phone_counts_where_people_drop_off']),
 ('V12 tracker tag without the firewall', PREV, 'data-before-send="ballottaBeforeSend" ', '', ['privacy_firewall_drops_anything_unlisted', 'real_tracker_sends_only_listed_events']),
 ('V13 missing street not counted', PREV, "track('lookup_failed', { reason: 'no_street' }); ", '', ['phone_counts_where_people_drop_off']),
 ('V14 bad ZIP not counted', PREV, "track('lookup_failed', { reason: 'bad_zip' }); ", '', ['phone_counts_where_people_drop_off']),
 ('V15 lookup start not counted', PREV, "  track('lookup_started');\n", '', ['phone_counts_where_people_drop_off']),
 ('V17 not found not counted', PREV, " track('lookup_failed', { reason: 'not_found' });", '', ['phone_counts_where_people_drop_off']),
 ('V18 county outage not counted', PREV, "    track('lookup_failed', { reason: 'county_unreachable' });\n", '', ['phone_counts_where_people_drop_off']),
 ('V19 nobody nearby not counted', PREV, " track('lookup_failed', { reason: 'no_voters_nearby' });", '', ['phone_counts_where_people_drop_off']),
 ('V20 unit picker not counted', PREV, "  track('units_asked');\n", '', ['phone_counts_where_people_drop_off']),
 ('V21 damaged link not counted', PREV, "{ track('link_damaged', { kind: 'damaged' }); return damaged(); }", 'return damaged();', ['phone_counts_where_people_drop_off']),
 ('V23 milestone one race late', PREV, 'done * 100 >= p * n && !progressSeen.at.includes(p)', 'done * 100 >= p * n + 100 && !progressSeen.at.includes(p)', ['phone_counts_progress_sources_and_clearing']),
 ('V24 skips miscounted', PREV, "const skipped = few(ids.filter(id => current(id)[0] === '__skip').length);", "const skipped = few(ids.filter(id => current(id)[0] === 'x').length);", ['phone_counts_progress_sources_and_clearing']),
 ('V25 milestones never checked', PREV, '  milestones();\n}', '}', ['phone_counts_progress_sources_and_clearing']),
 ('V26 campaign sites not told apart', PREV, "a.textContent.trim() === 'Campaign site' ? 'campaign_site' : ", '', ['phone_counts_progress_sources_and_clearing']),
 ('V27 race level dropped', PREV, "track('source_opened', level ? { kind, level } : { kind });", "track('source_opened', { kind });", ['phone_counts_progress_sources_and_clearing']),
 ('V28 laptop paper level unknown', PREV, "    P().dataset.c = ui.view === 'decide' ? curB().c.id : '';", '', ['desk_counts_laptop_features']),
 ('V29 directions counted as a source', PREV, "  if (host === 'www.google.com' && a.pathname.startsWith('/maps/dir')) return track('directions_opened', { period });\n", '', ['phone_counts_progress_sources_and_clearing']),
 ('V30 wrong voting period', PREV, "return track('directions_opened', { period });", "return track('directions_opened', { period: period === 'early' ? 'eday' : 'early' });", ['phone_counts_progress_sources_and_clearing']),
 ('V31 wait times counted as a source', PREV, "  if (host === 'updates.electionlink.net') return track('wait_times_opened', { period });\n", '', ['phone_counts_progress_sources_and_clearing']),
 ('V32 clearing picks not counted', PREV, "track('cleared', { what: 'picks' }); ", '', ['phone_counts_progress_sources_and_clearing']),
 ('V33 clear everything keeps data', PREV, "Object.keys(s).filter(k => k.startsWith('ballotta.')).forEach(k => s.removeItem(k));", "Object.keys(s).filter(k => k.startsWith('nothing.')).forEach(k => s.removeItem(k));", ['phone_counts_progress_sources_and_clearing', 'desk_counts_laptop_features']),
 ('V34 clear everything without asking', PREV, "  if (!confirm('Clear everything Ballotta saved in this browser: your ballot, picks, reasons, map location and share name?')) return;\n", '', ['phone_counts_progress_sources_and_clearing']),
 ('V35 print options not counted', PREV, "two_col: ui.two ? 'yes' : 'no'", "two_col: 'no'", ['desk_counts_laptop_features']),
 ('V36 menu items not counted', PREV, "    track('help_opened', { item: a });\n", '', ['desk_counts_laptop_features']),
 ('V37 views not counted', PREV, " track('view_opened', { view: btn.dataset.view });", '', ['desk_counts_laptop_features']),
 ('V38 busy keyboards counted every time', PREV, 'const countOnce = (key, name, data) => { if (!once.has(key)) { once.add(key); track(name, data); } };', 'const countOnce = (key, name, data) => track(name, data);', ['desk_counts_laptop_features']),
 ('V39 FAQ never counted', PREV, "countOnce('faq', 'faq_seen');", '', ['desk_counts_laptop_features']),
 ('V41 README misses an event', README, '`faq_seen` (after the visitor scrolls); ', '', ['readme_lists_every_counted_event']),
 ('V42 other payload types pass', PREV, "(type !== 'event' && type !== 'performance')", 'false', ['privacy_firewall_drops_anything_unlisted']),
 ('V43 page views keep details', PREV, '  if (out.name !== undefined) { const d = clean(out.name, p.data); if (!d) return null; out.data = d; }', '  out.data = p.data;\n  if (out.name !== undefined) { const d = clean(out.name, p.data); if (!d) return null; out.data = d; }', ['privacy_firewall_drops_anything_unlisted', 'real_tracker_sends_only_listed_events']),
 ('V44 page-speed numbers dropped', PREV, "  if (type === 'performance') SPEED.forEach(k => { if (typeof p[k] === 'number') out[k] = p[k]; });\n", '', ['privacy_firewall_drops_anything_unlisted', 'real_tracker_sends_only_listed_events']),
 ('V45 link codes unchecked', PREV, 'CODE = (v) => /^[a-z0-9]{1,8}$/.test(v)', 'CODE = (v) => true', ['privacy_firewall_drops_anything_unlisted']),
 ('V46 generations unchecked', PREV, 'GEN = (v) => /^[1-9][0-9]?$/.test(v)', 'GEN = (v) => true', ['privacy_firewall_drops_anything_unlisted']),
 ('V47 share sections unchecked', PREV, "sections: (v) => v === '' || v.split(',').every(k => SECTION_KEYS.includes(k))", 'sections: (v) => true', ['privacy_firewall_drops_anything_unlisted']),
 ('V48 layout unchecked', PREV, "k === 'layout' ? LAYOUT(String(v))", "k === 'layout' ? true", ['privacy_firewall_drops_anything_unlisted']),
 ('V49 laptops counted as phones', PREV, "window.desk && matchMedia('(min-width: 1024px)').matches ? 'laptop' : 'phone'", "'phone'", ['desk_counts_laptop_features', 'desk_compare_counted_once_per_link']),
 ('V50 rolled-back wide screens counted as laptops', TPL, '{ layout: window.desk && matchMedia', '{ layout: matchMedia', ['privacy_firewall_drops_anything_unlisted']),
 ('V51 outage after the Census fallback hangs', PREV, '      return await nearby(pt, pt.label);', '      return nearby(pt, pt.label);', ['phone_counts_where_people_drop_off']),
 ('V52 same ballot counted as a new address', PREV, "  if (before && before !== after) track('address_changed');", "  if (before) track('address_changed');", ['phone_counts_where_people_drop_off']),
 ('V54 laptop level leaks into other views', PREV, "    P().dataset.c = ui.view === 'decide' ? curB().c.id : '';", "    if (ui.view === 'decide') P().dataset.c = curB().c.id;", ['desk_counts_laptop_features']),
 ('V55 middle clicks not counted', PREV, "document.addEventListener('auxclick', outbound, true);", '', ['phone_counts_progress_sources_and_clearing']),
 ('V56 too-old links not counted', PREV, "{ track('link_damaged', { kind: 'too_old' }); return say(", '{ return say(', ['phone_counts_where_people_drop_off']),
 ('V57 news counted as other', PREV, "votebeat\\.org)$/, 'news']", "votebeat\\.org)$/, 'other']", ['phone_counts_progress_sources_and_clearing']),
 ('V58 FAQ promise missing', PREV, ' If your browser sends Do Not Track or Global Privacy Control, we count nothing at all.</p></div>', '</p></div>', ['privacy_firewall_drops_anything_unlisted']),
 ('V59 privacy note promise missing', PREV, 'pages load, never your address or your picks. If your browser sends Do Not Track or Global Privacy Control, we count nothing at all.</p>', 'pages load, never your address or your picks.</p>', ['privacy_firewall_drops_anything_unlisted']),
 ('V60 non-text fields kept', PREV, "if (typeof p[k] === 'string') out[k] = k === 'url'", "if (p[k] !== undefined) out[k] = k === 'url'", ['privacy_firewall_drops_anything_unlisted']),
 ('V61 query and fragment kept', PREV, "k === 'url' ? p[k].split(/[?#]/)[0] :", "k === 'url' ? p[k] :", ['privacy_firewall_drops_anything_unlisted']),
 ('V62 firewall fails open', PREV, '<script>window.ballottaBeforeSend = () => null;</script>', '', ['privacy_firewall_drops_anything_unlisted']),
 ('V63 returning voters counted again', PREV, '  if (quietProgress) return;  // the ballot was just shown: nothing was decided just now\n', '', ['phone_counts_progress_sources_and_clearing']),
 ('V64 showing a ballot counted as progress', PREV, '  quietProgress = true; try { refresh(); } finally { quietProgress = false; }', '  refresh();', ['phone_counts_progress_sources_and_clearing']),
 ('V65 progress forgets within a visit', PREV, '  if (progressSeen.sig !== sig) progressSeen = { sig, at: [] };', '  progressSeen = { sig, at: [] };', ['phone_counts_progress_sources_and_clearing']),
 ('V66 FAQ counted without a scroll', PREV, "io.observe($('dk-faq'));\n    };\n    window.addEventListener('scroll', arm, { passive: true });", "io.observe($('dk-faq'));\n    };\n    arm();", ['desk_counts_laptop_features']),
 ('V67 referrer path kept', PREV, "k === 'referrer' ? siteOf(p[k]) :", '', ['privacy_firewall_drops_anything_unlisted']),
 ('V68 blocked storage stops Clear everything', PREV, "['localStorage', 'sessionStorage'].forEach(n => { try { const s = window[n];", '[localStorage, sessionStorage].forEach(s => { try {', ['phone_counts_progress_sources_and_clearing']),
 ('V69 another tab writes it back', PREV, "window.addEventListener('storage', (e) => { if (e.key === 'ballotta.ballot' && e.newValue === null && e.oldValue !== null) location.replace(location.pathname); });", '', ['phone_counts_progress_sources_and_clearing']),
 ('V70 Clear everything clears other sites too', PREV, "Object.keys(s).filter(k => k.startsWith('ballotta.')).forEach(k => s.removeItem(k));", 's.clear();', ['phone_counts_progress_sources_and_clearing']),
 ('V71 glance rows lose their race', PREV, "box.matches('tr[data-tr]') ? box.dataset.tr : ", '', ['desk_counts_laptop_features']),
 ('V72 app referrers become "null"', PREV, "return u.host ? u.protocol + '//' + u.host : '';", 'return u.origin;', ['privacy_firewall_drops_anything_unlisted']),
 ('V73 shown ballot not noted', PREV, '  progressSeen.at.push(...now);\n  if (quietProgress) return;', '  if (quietProgress) return;\n  progressSeen.at.push(...now);', ['phone_counts_progress_sources_and_clearing']),
 ('V74 any ballot write reloads other tabs', PREV, "if (e.key === 'ballotta.ballot' && e.newValue === null && e.oldValue !== null)", "if (e.key === 'ballotta.ballot')", ['phone_counts_progress_sources_and_clearing']),
 ('V75 app scrolls arm the FAQ count', PREV, "      if (document.body.classList.contains('dk-app-on')) return;  // a scroll in the app doesn't count: only one on the landing page\n", '', ['desk_counts_laptop_features']),
 ('A1 non-text reasons kept', PREV, "Object.entries(plain(LS.get('ballotta.whys', {}))).filter(([, v]) => typeof v === 'string')", "Object.entries(plain(LS.get('ballotta.whys', {})))", ['phone_stored_junk_never_breaks_keep_or_share']),
 ('A3 look-alike letters ignored', PREV, '.map(ch => LOOKALIKE[ch] || ch)', '.map(ch => ch)', ['share_names_block_lookalikes_and_nicknames']),
 ('A7 focus ring clipped again', PREV, 'text-overflow:ellipsis;min-width:0;padding:4px;margin:-4px}', 'text-overflow:ellipsis;min-width:0}', ['desk_change_link_focus_ring_is_whole']),
 ('A8 long names push the phone page sideways', PREV, '#friend h2,#friend .note,#friend .fp,#compare h2,#compare .note,#compare .cmp,#compare .lead{overflow-wrap:anywhere}', '', ['phone_friend_card_long_names_and_honest_copy', 'desk_friend_card_long_names_and_honest_copy']),
 ('A9 long names push the laptop page sideways', PREV, 'white-space:nowrap;min-width:0}\n  .dk-fcta,.dk-fchip,.dk-fbox,.dk-fp{overflow-wrap:anywhere;min-width:0}  /* #23 */\n', 'white-space:nowrap;min-width:0}\n', ['phone_friend_card_long_names_and_honest_copy', 'desk_friend_card_long_names_and_honest_copy']),
 ('A10 friend card overclaims', PREV, 'Most races on your ballot link to neutral sources.', 'Each race on your ballot links to neutral sources.', ['phone_friend_card_long_names_and_honest_copy', 'desk_friend_card_long_names_and_honest_copy']),
 ('A11 friend pick unnamed in the rail', PREV, '<span class="dk-vh">\' + esc(friendName()) + \' picked \' + fp + \'</span>', '', ['desk_friend_pick_in_rail_has_a_name']),
 ('A12 rail initial read out', PREV, ' aria-hidden="true" title="\' + possessive() + \' pick: \' + fp', ' title="\' + possessive() + \' pick: \' + fp', ['desk_friend_pick_in_rail_has_a_name']),
 ('A13 extra pick accepted', PREV, '    if (!cur.includes(val) && cur.length >= n) { limitNote(cid, n); return false; }  // already N picks: say why nothing changed (#33)\n', '', ['phone_extra_pick_is_explained']),
 ('A14 extra pick refused silently', PREV, '{ limitNote(cid, n); return false; }', '{ return false; }', ['phone_extra_pick_is_explained']),
 ('A15 limit note never clears', PREV, '  limitNote(cid, 0);\n  picks[cid] = cur;', '  picks[cid] = cur;', ['phone_extra_pick_is_explained']),
 ('A16 refused key pick announced', PREV, 'if (pick(b.c.id, o) !== false) announce(b.c);', 'pick(b.c.id, o); announce(b.c);', ['desk_extra_pick_is_explained', 'phone_extra_pick_is_explained']),
 ('A17 limit note not a status', PREV, 'data-limit="\' + c.id + \'" role="status"></span>\' : \'\') + \'</p>\';', 'data-limit="\' + c.id + \'"></span>\' : \'\') + \'</p>\';', ['desk_extra_pick_is_explained', 'phone_extra_pick_is_explained']),
 ('A18 no check for a new day', PREV, 'setInterval(dayCheck, 60000);\n', '', ['dates_move_on_in_a_tab_left_open']),
 ('A19 chosen period overridden', PREV, '  if (!periodChosen) period = defaultPeriod();\n', '  period = defaultPeriod();\n', ['dates_move_on_in_a_tab_left_open']),
 ('A20 tab choice forgotten', PREV, "period = 'early'; periodChosen = true; renderVote();", "period = 'early'; renderVote();", ['dates_move_on_in_a_tab_left_open']),
 ('A22 date frozen at load', PREV, 'const today = () => new Date();', 'const FROZEN = new Date(), today = () => FROZEN;', ['dates_move_on_in_a_tab_left_open']),
 ('A23 data inserted first', BLD, '        html = strip_desk(html)\n', '        html = strip_desk(html)\n    html = html.replace("__DATA__", data)\n', ['build_inserts_data_last']),
 ('A24 moves not announced', PREV, 'where(curB()); }', '}', ['desk_moves_are_announced']),
 ('A26 old link notice survives a new ballot', PREV, "      $('dk-say').classList.add('hidden');  // a new ballot: an older link's notice no longer applies (#40)\n", '', ['a_good_link_clears_a_damaged_links_notice']),
 ('A27 a stop signal leaves the mutant', MD_SELF, '    for f_, t_ in PENDING: put(f_, t_)\n', '', ['mutation_runner_restores_on_any_signal']),
 ('A28 Ctrl-C not handled', MD_SELF, 'SIGS = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)\nPENDING', 'SIGS = (signal.SIGTERM, signal.SIGHUP)\nPENDING', ['mutation_runner_restores_on_any_signal']),
 ('A29 importing the runner starts a run', MD_SELF, "\nif __name__ == '__main__':", '\nif True:', ['mutation_runner_restores_on_any_signal']),
 ('R2 hyphen-joined words get through', PREV, "const w = t.replace(/[\\p{P}\\p{S}]/gu, ' ')", "const w = t.replace(/[\\p{P}\\p{S}]/gu, '')", ['share_names_block_lookalikes_and_nicknames']),
 ('R8 runs of spaces not collapsed', PREV, " ' ').replace(/\\s+/g, ' ').trim();", " ' ');", ['share_names_block_lookalikes_and_nicknames']),
 ('R11 Print… counted twice', PREV, "    if (ui.view !== 'crib') { setView('crib'); track('view_opened', { view: 'crib' }); }", "    setView('crib'); track('view_opened', { view: 'crib' });", ['desk_print_button_opens_the_crib_sheet']),
 ('P1 laptop Print… prints straight away', PREV, "    if (ui.view !== 'crib') { setView('crib'); track('view_opened', { view: 'crib' }); }\n    const pr", "    $('print').click(); return;\n    const pr", ['desk_print_button_opens_the_crib_sheet']),
 ('P2 laptop Print… not counted as a view', PREV, "{ setView('crib'); track('view_opened', { view: 'crib' }); }", "{ setView('crib'); }", ['desk_print_button_opens_the_crib_sheet']),
 ('R14 focused Print button left off screen', PREV, " pr.scrollIntoView({ block: 'nearest' }); }", ' }', ['desk_print_button_opens_the_crib_sheet']),
 ('R16 short words matched across spaces', PREV, "['league', 'lwv', 'vote411', 'county',", "['league', 'lwv', 'voter', 'cityof', 'vote411', 'county',", ['share_names_block_lookalikes_and_nicknames']),
 ('R18 voter not a reserved word', PREV, "'dnc', 'voters?', 'clerks?',", "'dnc', 'clerks?',", ['share_names_block_lookalikes_and_nicknames']),
 ('R1 a new day redraws the whole laptop page', PREV, 'desk.today(period !== was); } catch (e) {}/*/DESK*/', 'desk.render(); } catch (e) {}/*/DESK*/', ['dates_move_on_in_a_tab_left_open']),
 ('A5 party nicknames allowed', PREV, "'gop', 'dems?', 'repubs?', 'rnc', 'dnc', ", "'gop', ", ['share_names_block_lookalikes_and_nicknames']),
 ('A6 symbols read only as letters', PREV, "[fold(low), fold(low.replace(/[|!$@]/g, '')), ", '[fold(low), ', ['share_names_block_lookalikes_and_nicknames']),
 ('R7 reserved words not folded', PREV, "'villageof'].map(fold).join('|'));", "'villageof'].join('|'));", ['share_names_block_lookalikes_and_nicknames', 'audit_a5_a8_a12_hostile_share']),
 ('A21 laptop header keeps the old day', PREV, "      $('dk-when').textContent = whenLine();\n      if (!periodChanged", '      if (!periodChanged', ['dates_move_on_in_a_tab_left_open']),
 ('R12 new list leaves focus nowhere', PREV, '      if (inside) P().focus({ preventScroll: true });\n', '', ['dates_move_on_in_a_tab_left_open']),
 ('R15 every new day re-draws the vote view', PREV, "      if (!periodChanged || ui.view !== 'vote'", "      if (ui.view !== 'vote'", ['dates_move_on_in_a_tab_left_open']),
 ('R20 glued handles get through', PREV, ' || RESERVED_GLUED.test(x)', '', ['share_names_block_lookalikes_and_nicknames']),
 ('R21 leading acronyms not split', PREV, "n.replace(/(\\p{Lu})(?=\\p{Lu}\\p{Ll})/gu, '$1 ').replace(", 'n.replace(', ['share_names_block_lookalikes_and_nicknames']),
 ('R22 glued words need fewer letters', PREV, "')\\\\S{4,}|\\\\S{4,}('", "')\\\\S{1,}|\\\\S{1,}('", ['share_names_block_lookalikes_and_nicknames']),
 ('R23 holding Enter prints', PREV, '    N().querySelectorAll(\'[data-act="print"]\').forEach(btn => btn.addEventListener(\'keydown\', (e) => { if (e.repeat) e.preventDefault(); }));  // Pass 4\n', '', ['desk_print_button_opens_the_crib_sheet']),
 ('M29 hiding a friend leaves the landing broken', PREV, 'friend = null;/*DESK*/ if (window.desk) try { desk.render(); } catch (e) {}/*/DESK*/\n}\nfunction friendName', 'friend = null;\n}\nfunction friendName', ['desk_friend_hide_on_landing']),
 ('V40 clear everything missing from the menu', PREV, "    else if (a === 'clearall') clearEverything();\n", '', ['desk_counts_laptop_features']),
 ('F11 old warning survives a good link', PREV, "  notify('');\n", '', ['desk_launch_audit_fixes']),
 ('B1 no Content-Security-Policy', BLD, 'return html.replace("<!--CSP-->", csp_meta(html, phone), 1)', 'return html', ['page_is_built_locked_down']),
 ('B2 inline scripts allowed', BLD, "script-src 'self' {hashes};", "script-src 'self' 'unsafe-inline';", ['page_is_built_locked_down']),
 ('B3 referrer sent', TPL, '<meta name="referrer" content="no-referrer">\n', '', ['page_is_built_locked_down']),
 ('B4 data may go anywhere', BLD, 'connect-src https://taxmaps.traviscountytx.gov https://gateway.umami.is;', 'connect-src *;', ['page_is_built_locked_down']),
 ('B5 Census frame not sandboxed', PREV, "f.setAttribute('sandbox', 'allow-scripts');", "f.setAttribute('sandbox', 'allow-scripts allow-same-origin');", ['census_runs_in_a_sandbox']),
 ('B6 any point accepted', PREV, ' && d.x > -107 && d.x < -93 && d.y > 25 && d.y < 37', '', ['census_runs_in_a_sandbox']),
 ('B7 any window may answer', PREV, '      if (e.source !== f.contentWindow) return;\n', '', ['census_runs_in_a_sandbox']),
 ('B8 frame left behind', PREV, "window.removeEventListener('message', on); f.remove(); resolve(v);", "window.removeEventListener('message', on); resolve(v);", ['census_runs_in_a_sandbox']),
 ('B10 a campaign site back on http', LEARN, '"https://cuero4rrisd.com"', '"http://cuero4rrisd.com"', ['campaign_links_use_https_where_they_work']),
 ('C1 laptop Share clicks the phone button', PREV, "  $('dk-share').addEventListener('click', openShare);", "  $('dk-share').addEventListener('click', () => $('a-share').click());", ['desk_works_without_phone_buttons']),
 ('C2 laptop hours copied from the phone page', PREV, '<div class="sub">\' + hoursHTML() + \'</div>\'', '<div class="sub">\' + $(\'hours\').innerHTML + \'</div>\'', ['desk_works_without_phone_buttons']),
 ('C3 laptop crib copied from the phone page', PREV, '\'" id="dk-page">\' + cribHTML() + \'</div>\';', '\'" id="dk-page">\' + $(\'crib\').innerHTML + \'</div>\';', ['desk_works_without_phone_buttons']),
 ('C4 laptop print clicks the phone button', PREV, "    else if (a === 'print') printCrib();", "    else if (a === 'print') $('print').click();", ['desk_works_without_phone_buttons']),
 ('C5 laptop clear clicks the phone button', PREV, "    else if (a === 'clear') { clearPicks(); render(); }", "    else if (a === 'clear') { $('reset').click(); render(); }", ['desk_works_without_phone_buttons']),
 ('B9 census.html out of date', BLD, ' || e.source !== parent || ', ' || ', ['census_runs_in_a_sandbox']),
 ('B11 census.html runs unsandboxed', BLD, "if (self.origin !== 'null' || ", 'if (', ['census_runs_in_a_sandbox']),
 ('B12 a reloading frame loops', PREV, ", '*'), { once: true });  // once", ", '*'));  // once", ['census_runs_in_a_sandbox']),
 ('B13 preview looks for census.html in its own folder', BLD, ', ("f.src = \'census.html\'", "f.src = \'../census.html\'")', '', ['census_runs_in_a_sandbox']),
 ('R19 9 not read as g', PREV, ", '8': 'b', '9': 'g',\n", ", '8': 'b',\n", ['share_names_close_remaining_gaps']),
 ('A4 stand-ins not folded', PREV, 'const fold = (t) => t.replace(/[1i|!0345@$6789€©¢]/g, ch => FOLD[ch]);', 'const fold = (t) => t;', ['share_names_block_lookalikes_and_nicknames']),
 ('A2 stored picks not checked', PREV, "let picks = cleanPicks(LS.get('ballotta.picks', {}))", "let picks = LS.get('ballotta.picks', {})", ['phone_stored_junk_never_breaks_keep_or_share']),
 ('R10 Print… leaves keyboard focus behind', PREV, "    if (pr && (e.detail === 0 || e.pointerType === 'touch' || e.pointerType === 'pen')) { pr.focus({ preventScroll: true }); pr.scrollIntoView({ block: 'nearest' }); }\n", '', ['desk_print_button_opens_the_crib_sheet']),
 ('R13 Print… moves focus on a mouse click', PREV, "if (pr && (e.detail === 0 || e.pointerType === 'touch' || e.pointerType === 'pen')) {", 'if (pr) {', ['desk_print_button_opens_the_crib_sheet']),
 ('D1 Unicode table not applied', PREV, 'for (const [k, chars] of Object.entries(LOOKALIKE_TABLE)) for (const ch of chars) if (!LOOKALIKE[ch]) LOOKALIKE[ch] = k;\n', '', ['share_names_close_remaining_gaps']),
 ('D2 lower-case look-alikes missed', PREV, 'for (const [k, chars] of Object.entries(LOOKALIKE_TABLE)) for (const ch of chars) { const lc = ch.toLowerCase();', 'for (const [k, chars] of Object.entries({})) for (const ch of chars) { const lc = ch.toLowerCase();', ['share_names_close_remaining_gaps']),
 ('D3 flag letters not read', PREV, 'for (let i = 0; i < 26; i++) LOOKALIKE[String.fromCodePoint(0x1F1E6 + i)] = String.fromCharCode(97 + i);\n', '', ['share_names_close_remaining_gaps']),
 ('D4 symbol stand-ins not folded', PREV, "  '€': 'e', '©': 'c', '¢': 'c' };", "  '€': '€', '©': '©', '¢': '¢' };", ['share_names_close_remaining_gaps']),
 ('D5 short glued handles pass', PREV, "+ '|\\\\S{2,}(' + ['voters?', 'cityof']", "+ '|\\\\S{9,}(' + ['voters?', 'cityof']", ['share_names_close_remaining_gaps']),
 ('D7 non-text picks counted', PREV, ".filter(x => typeof x === 'string')]).filter(([, v]) => v.length));", '.filter(x => x != null)]).filter(([, v]) => v.length));', ['phone_stored_junk_in_share_fields']),
 ('D8 odd generation sent', PREV, 'gen = Number.isInteger(g0) ? Math.max(1, Math.min(99, g0)) : 1,', 'gen = Math.max(1, Math.min(99, g0 || 1)),', ['phone_stored_junk_in_share_fields']),
 ('D9 odd share name shown', PREV, "$('sharename').value = typeof nm === 'string' ? nm.slice(0, 30) : '';", "$('sharename').value = nm || '';", ['phone_stored_junk_in_share_fields']),
 ('D12 a touch leaves focus on Print…', PREV, " || e.pointerType === 'touch' || e.pointerType === 'pen'", '', ['desk_print_by_touch_and_announced']),
 ('D14 a new day rebuilds the phone list', PREV, '  if (period !== was) renderVote(); else waitsNote();', '  renderVote();', ['phone_new_day_keeps_the_vote_list_and_focus', 'phone_wait_times_note_says_when_it_fills_in']),
 ('D15 a new day forgets the dated note', PREV, 'renderVote(); else waitsNote();', 'renderVote();', ['phone_new_day_keeps_the_vote_list_and_focus', 'phone_wait_times_note_says_when_it_fills_in']),
 ('D17 no second card at 25', PREV, 'n >= 25 && !st.d25 ? 25 : ', '', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D19 a kept link ignored', PREV, "if (via) { track('keep_created', { via }); nudgeKept(); } });", "if (via) { track('keep_created', { via }); } });", ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D20 card not counted', PREV, "  track('backup_nudge', { at: String(at), action: 'shown' });\n", '', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D21 Send myself a link opens nothing', PREV, "  if (action === 'keep') openKeep();\n", '', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D22 browser never asked to keep data', PREV, 's.persisted().then(p => p || s.persist())', 's.persisted()', ['phone_persistent_storage_asked_at_first_pick']),
 ('D23 asked at every pick', PREV, '  if (persistAsked) return;\n', '', ['phone_persistent_storage_asked_at_first_pick']),
 ('D24 asked even when already kept', PREV, 'p => p || s.persist()', 'p => s.persist()', ['phone_persistent_storage_asked_at_first_pick']),
 ('R17 glued words not split', PREV, "fold(low.replace(/[|!$@]/g, '')), fold(split), ", "fold(low.replace(/[|!$@]/g, '')), ", ['share_names_block_lookalikes_and_nicknames']),
 ('D6 uneven splits pass', PREV, ', fold(split), fold(latin(uneven))];', ', fold(split)];', ['share_names_close_remaining_gaps']),
 ('D16 backup card never shown', PREV, "if (val !== '__skip' && current(cid).includes(val)) nudgeCheck();", '', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D28 a skip shows the card', PREV, "if (val !== '__skip' && current(cid).includes(val)) nudgeCheck();", 'nudgeCheck();', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D18 an ignored card comes back', PREV, "  st['d' + at] = 1; if (at === 25) st.d5 = 1; LS.set('ballotta.nudge', st);\n", '', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D29 Not now at 25+ brings the 25 card', PREV, "  if (countPicks(ballot.map(b => b.c.id)) >= 25) { const st = nudgeState(); st.d25 = 1; LS.set('ballotta.nudge', st); }\n", '', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D30 focus left on a hidden button', PREV, '  if (home) home.focus({ preventScroll: true });\n', '', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D31 Clear my picks leaves the card', PREV, "track('cleared', { what: 'picks' }); nudgeAt = 0; nudgeBoxes(false);", "track('cleared', { what: 'picks' });", ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D32 the phone card pushes the page', PREV, '.nudge{position:fixed;left:12px;right:12px;', '.nudge{left:12px;right:12px;', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D33 the laptop card pushes the paper', PREV, '  .dk-nudge{position:fixed;right:24px;bottom:24px;', '  .dk-nudge{grid-column:1/-1;', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D25 a capitalised word glued to an initial', PREV, '\\s(?!\\p{Lu}\\p{Ll}{2,})|(?<!(^|\\s)\\p{Lu}\\p{Ll}{2,})\\s(?=', '\\s|\\s(?=', ['share_names_close_remaining_gaps']),
 ('D26 б not read as b', PREV, "LOOKALIKE['б'] = LOOKALIKE['Б'] = 'b';", "delete LOOKALIKE['б']; delete LOOKALIKE['Б'];", ['share_names_close_remaining_gaps']),
 ('D34 two-letter words count as names', PREV, '(?!\\p{Lu}\\p{Ll}{2,})|(?<!(^|\\s)\\p{Lu}\\p{Ll}{2,})', '(?!\\p{Lu}\\p{Ll})|(?<!(^|\\s)\\p{Lu}\\p{Ll}+)', ['share_names_close_remaining_gaps']),
 ('D36 the card covers the page end', PREV, " document.documentElement.classList.toggle('nudging', show); };", ' };', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D37 Not now throws focus to the top', PREV, '  const home = was || /*PHONE*/(', '  const home = /*PHONE*/(', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('A25 contest number off by one', PREV, "'Contest ' + (idx(c.id) + 1)", "'Contest ' + idx(c.id)", ['desk_moves_are_announced']),
 ('D10 a quick move cuts off the pick', PREV, '    [...q].reverse().forEach(x => { if (x.pick && x.pick.id !== to && !done.has(x.pick.id)) { done.add(x.pick.id); parts.unshift(pickWords(x.pick)); } });\n', '', ['desk_quick_pick_then_move_keeps_both_announcements']),
 ('D11 a pick is said at once', PREV, 'liveQ.some(x => x.pick) ? 300 : 50);', '50);', ['desk_quick_pick_then_move_keeps_both_announcements']),
 ('D27 a pick already said is said again', PREV, '    const q = liveQ; liveQ = [];\n', '    const q = liveQ;\n', ['desk_quick_pick_then_move_keeps_both_announcements']),
 ('D38 a move worded too early', PREV, 'function where(b) { say({ move: b.c }); }', 'function where(b) { say({ text: moveWords(b.c) }); }', ['desk_quick_pick_then_move_keeps_both_announcements']),
 ('D39 the moved-to contest said twice', PREV, 'x.pick && x.pick.id !== to && ', 'x.pick && ', ['desk_quick_pick_then_move_keeps_both_announcements']),
 ('D13 Print… says nothing', PREV, "    say({ text: 'Crib sheet: print options, then the Print button.' });\n", '', ['desk_print_by_touch_and_announced']),
 ('D35 small capitals read as lower case', PREV, 'const uneven = caps.replace(', 'const uneven = n.replace(', ['share_names_close_remaining_gaps']),
 ('D40 Cyrillic small capitals missed', PREV, 'тмнквп]/gu, ch =>', ']/gu, ch =>', ['share_names_close_remaining_gaps']),
 ('D41 focus lost in a closed race', PREV, "  if (document.activeElement !== home) { const f = $(wide ? 'dk-paper' : 'a-keep'); if (f) f.focus({ preventScroll: true }); }", '', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D42 room under the card on paper', PREV, '@media screen{html.nudging{', '@media all{html.nudging{', ['phone_backup_nudge_after_fifth_pick', 'desk_backup_nudge_after_fifth_pick']),
 ('D43 the pick column takes what is left', PREV, '  .dk-tbl td:nth-child(2){width:240px}', '  .dk-tbl td:nth-child(2){width:auto}', ['desk_glance_picks_fit_their_names']),
 ('D44 the contest column keeps a third', PREV, '  .dk-tbl tbody th{width:24%}\n', '  .dk-tbl tbody th{width:34%}\n', ['desk_glance_picks_fit_their_names']),
 ('D45 Learn more wraps on a wide laptop', PREV, '@media (max-width:1199.98px){.dk-tbl td a{white-space:normal}}', '@media all{.dk-tbl td a{white-space:normal}}', ['desk_glance_picks_fit_their_names']),
 ('D46 the tab still says Crib sheet', PREV, 'Print your choices</button>', 'Crib sheet</button>', ['laptop_crib_options_and_print_go_to_the_phone']),
 ('D47 the old headings', PREV, '<span class="ov">Print your choices</span><h1>Crib sheet</h1>', '<span class="ov">Crib sheet</span><h1>Print your notes</h1>', ['laptop_crib_options_and_print_go_to_the_phone']),
 ('D48 At a glance title hugs its line', PREV, '  .dk-gh > div{display:flex;flex-direction:column;gap:18px}', '  .dk-gh > div{}', ['view_titles_sit_the_same_distance_below_their_line']),
 ('D49 At a glance title smaller than the rest', PREV, '  .dk-gh{display:flex;align-items:flex-end;gap:16px;justify-content:space-between}\n', '  .dk-gh{display:flex;align-items:flex-end;gap:16px;justify-content:space-between}\n  .dk-gh h1{font-size:36px}\n', ['view_titles_sit_the_same_distance_below_their_line']),
 ('D50 links read in the new order', PREV, 'const was = REORDERED[id], at', 'const was = false, at', ['links_keep_the_old_order_for_the_ten_reordered_lists']),
 ('D51 links written in the new order', PREV, "back = REORDERED[id], ix", "back = false, ix", ['links_keep_the_old_order_for_the_ten_reordered_lists']),
 ('D52 Share links marked for new pages only', PREV, "packFrag('s', { v: 1, n: name,", "packFrag('s', { v: 1, r: 2, n: name,", ['links_keep_the_old_order_for_the_ten_reordered_lists']),
 ('D53 Keep links marked for new pages only', PREV, "packFrag('k', { v: 1, at:", "packFrag('k', { v: 1, r: 2, at:", ['links_keep_the_old_order_for_the_ten_reordered_lists']),
 ('D54 one list\'s table wrong (c179)', PREV, 'c179: [2, 3, 0, 1]', 'c179: [3, 2, 1, 0]', ['links_keep_the_old_order_for_the_ten_reordered_lists']),
 ('D55 links written through the table the wrong way round', PREV, "back && back.indexOf(i) >= 0 ? back.indexOf(i) : i", "back && back[i] !== undefined ? back[i] : i", ['links_keep_the_old_order_for_the_ten_reordered_lists']),
 ('D56 promotion leaves the preview page at next/', BLD, '"next/sw.js": sw_off_js(True), "next/index.html": moved_page()})', '"next/sw.js": sw_off_js(True)})', ['promotion_hands_the_preview_on']),
 ('D57 next/ drops a link made on the preview', BLD, "location.replace(new URL('../', location.href).href + location.hash)", "location.replace(new URL('../', location.href).href)", ['promotion_hands_the_preview_on']),
 ('D58 the promoted page leaves the preview copy', BLD, "        if not preview:   # the main page with the phone layout", "        if False:   # the main page with the phone layout", ['promotion_hands_the_preview_on']),
 ('D59 the promoted page updates its own worker instead', BLD, "sw.getRegistration('next/').then((g) => g && g.scope === new URL('next/', location.href)", "sw.getRegistration('./').then((g) => g && g.scope === new URL('./', location.href)", ['promotion_hands_the_preview_on']),
 ('D60 MUD 41 routed to nobody', PREV, '"c193": {"clauses": [{"MUD": ["M41"]}, {"Temp": ["M41"]}], "conf": "medium"', '"c193": {"clauses": null, "conf": "unrouted"', ['mud_41_reaches_its_addresses_marked_double_check']),
 ('D61 MUD 41 shown as certain', PREV, '"c194": {"clauses": [{"MUD": ["M41"]}, {"Temp": ["M41"]}], "conf": "medium"', '"c194": {"clauses": [{"MUD": ["M41"]}, {"Temp": ["M41"]}], "conf": "high"', ['mud_41_reaches_its_addresses_marked_double_check']),
 ('D62 next/ updates whatever worker it finds', BLD, "g && g.scope === new URL('./', location.href).href && g.update()),", "g && g.update()),", ['promotion_hands_the_preview_on']),
 ('D63 the main page updates its own worker for next/', BLD, "g && g.scope === new URL('next/', location.href).href && g.update()", "g && g.update()", ['promotion_hands_the_preview_on']),
 ('D64 the worker keeps nothing at install', BLD, "keep = \"['./']\" if preview else \"['./', 'next/']\"", "keep = \"[]\"", ['promotion_hands_the_preview_on']),
 ('D65 the install waits as long as the line', BLD, "setTimeout(() => stop.abort(), 8000)", "setTimeout(() => {}, 8000)", ['offline_copy_install_never_waits_on_a_slow_line']),
 ('D66 a rollback leaves the offline copy on phones', BLD, '        out["sw.js"] = sw_off_js(False)', '        pass', ['promotion_hands_the_preview_on']),
 ('D67 the shared link vanishes once shared', PREV, "  prepShare(true);  // a fresh link code", "  prepShare();  // a fresh link code", ['shared_link_stays_on_screen_after_sharing']),
 ('D68 an older link stays next to new choices', PREV, "  if (!keepShown) $('share-out').classList.add('hidden');", "  if (false) $('share-out').classList.add('hidden');", ['shared_link_stays_on_screen_after_sharing']),
]
def main(M):
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
