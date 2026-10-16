# Ballotta: phone layout — build plan

*Written Oct 15, 2026 for Lane. Status: **approved by Lane (Oct 16, 8:19am: all 15 differences, including the 4-second offline rule) and being executed.** Every script below was dry-run on a throwaway copy first (results in "Dry run"). Early voting starts **Mon Oct 19**, and most voters are on phones, so the plan is sized for a preview the same day Lane says go, and a promotion before Monday if he's happy.*

## The request (verbatim)

> "Great! Let's get started on the phone interface plan."

Lane's answers to the four open questions (Oct 15):

| Question | Lane's answer |
|---|---|
| Phone landing page | **The laptop's band, compact**: plum band, gold strip, tagline, the form's paper overlapping the band; steps and the FAQ (as tap-to-open questions) below |
| Moving between races | **Add "← Previous · Next →" under the paper**; the bottom bar keeps "Next undecided" |
| Add to Home Screen | **In the menu, plus once on the 25-pick backup card** |
| Offline | **Yes: fresh online, the saved copy offline** (network first) |

The design is the canvas page **"All screens, 2d (web + phone)"** (https://claude.ai/artifact/6oAiCKqH36pboTcREAzuxh), the 13 boards marked "phone 390", Option B: plum top and bottom bars, the white ballot "paper" on lilac, "Your ballot" as a full-screen plum sheet.

## What "done" looks like

1. https://ballotta.org/next/ shows the phone layout to anyone on a screen narrower than 1024px, with every feature today's phone page has: look up, decide (race and measure, with the League and campaign links and the office notes), at a glance, where to vote (list, map, wait times, photo ID), crib sheet (with print options), keep link, share link, a friend's picks, feedback & info, clear picks / everything.
2. Plus **Add to Home Screen** (Android: the browser's own prompt; iPhone: the steps, and a way to carry picks over, because an iPhone Home Screen app has its own storage) and an **offline copy** of the page.
3. https://ballotta.org/ is **byte-for-byte unchanged** until Lane says "promote" (a fingerprint test, and a fetch of the live page after the push).
4. Laptops (1024px and wider) see **exactly** what they see today, on both addresses (a pixel test: landing, ballot, a pick, at a glance, where to vote, crib sheet, the menu, at 1440 and 1024 wide).
5. After Lane's OK on his own phone: a short promotion plan (Task 13) moves the phone layout live.

## Differences from the canvas mocks (Lane: please confirm each)

The mocks predate some of your laptop decisions, so where they disagree the phone follows the laptop as shipped:

1. **Where to vote**: no "Calendar" button (not built on the laptop either); "Check live wait times" plus the full photo-ID box and notes, instead of "Wait times / Calendar / ID rules" buttons. The map sits behind a "Map of vote centers" fold, as the mock's "Map ▾".
2. **Crib sheet** offers all three print options (reasons, two columns, hide unopposed), like the laptop; the mock showed two.
3. **A friend's link, no ballot yet**: their picks on a paper, then "See Maya's picks beside yours" and the address form, as the laptop does, instead of the mock's "See my own ballot" / "Compare with my picks" buttons. After the lookup, her picks show inline ("Maya picked this") automatically, and `share_compare` is counted then (once per link), as on a laptop.
4. **"You and Maya" tally** (same / different / not picked) lives inside the fold under the paper, whose label then starts "You and Maya · …".
5. **Bottom bar** says "Next undecided →" in every view (the mock said "Next →" outside Decide); once everything is decided it says "Crib sheet →", and it hides on the crib sheet.
6. **"Your ballot" sheet**: the four views in a 2×2 grid of 44px buttons (mock: smaller chips that wrap), and "Done" as a filled button (mock: underlined text). A search you typed stays when you jump to a contest, as on a laptop.
7. **Feedback & Info** (your laptop name; the mock said "Help & info") opens as a sheet with all the laptop's items, including "Clear everything on this device…", plus "Add to your Home Screen" (or, inside the Home Screen app, "Paste my picks link"). Today's "About this test" card and feedback footer move into it.
8. **Sheets** keep today's phone style: a handle and a "Close" text button (the mock drew a round ×).
9. **Privacy note under the address form** keeps the full sentence (Census fallback, anonymous counts, Do Not Track). The mock's shorter one leaves those out, so it would be wrong.
10. **Measure header** reads "CITY OF AUSTIN · CONTEST 50 OF 63" without "· BOND", and races read "Vote for 1" without "Nonpartisan" (the data doesn't say either; same as the laptop). "Saved on this device" sits at the top right of the paper, as on the laptop.
11. **Tablets** (an iPad held upright, 768–1023px) get the phone layout, centred, at most 640px wide.
12. **No keyboard shortcuts** below 1024px (and no key hints).
13. **Landing**: the band has no big logo (the top bar carries it), so the form starts higher on a small screen. The form keeps today's words: the long lead ("…from Travis County's own voter-district data"), "Apt / unit", and no "Nov 3, 2026 · Travis County" overline (the gold strip and tagline say it).
14. **Top bar order**: menu (☰), then Share; the mock drew Share first. The laptop's buttons come in that order, and swapping them on screen only would make the keyboard order differ from what you see.
15. **Offline, on one bar of signal** (please look at this one: it bends your answer a little). "Fresh online" holds whenever the network answers; but if a phone that has visited before gets **no answer within 4 seconds**, it shows the kept copy at once, and the fresh page replaces the kept one for next time. Without that, a voter in a line with one bar can stare at a blank screen for a minute. The alternative is to wait for the network however long it takes, and use the kept copy only when there is no network at all. Your call; it's one number in `sw.js`.

## How it's built (and why the live page and laptops can't change by accident)

- **The laptop app, folded up.** The phone mock is the laptop layout on a small screen: "Your ballot" is the plum rail, the paper is the same paper, the notes column becomes a fold. So the phone layout *is* the laptop app (`#dk-app`) at phone widths, restyled by one CSS block for `max-width: 1023px`, plus a small controller (`phone`) for the bottom bar, the list sheet, the menu sheet, the fold and Add to Home Screen. Every move goes through the laptop's own `go()`, `setView()` and `act()` (exposed to the phone code as `desk.ph`), every pick through the shared `pick()`. Today's phone page (`.wrap`'s accordion list) stays in the file, hidden once a ballot shows, because the printout and a few shared texts still live in it; deleting it is promotion-time cleanup.
- **Markers, like the laptop round.** Everything new is inside `/*PHONE*/ … /*/PHONE*/` (CSS, JS) or `<!--PHONE--> … <!--/PHONE-->` (HTML): whole-line blocks, or a pair inside one line. `source/build_site.py` gets `PHONE_LIVE = False`, and the live build strips every PHONE block, giving back today's `index.html` byte for byte (pinned by sha256). The stripper is the laptop's, generalised to take a tag, with the same refusals (unpaired or misplaced markers stop the build).
- **Laptops untouched.** The phone CSS sits inside `@media screen and (max-width:1023.98px)` (the .98 leaves no gap below 1024px at odd zoom levels); the phone's own elements are `display:none` outside it; at laptop widths the phone code only builds hidden pieces: it doesn't install the offline copy and leaves Chrome's own install offer alone (a test checks both). A second test builds the page with and without the phone code and compares laptop screenshots pixel for pixel.
- **The preview.** `python3 source/build_site.py --preview` writes `next/index.html` (phone layout on, counts nothing, as before) plus `next/manifest.webmanifest` and `next/sw.js`. Today `next/index.html` is a redirect (left from the laptop promotion); the preview replaces it, and promotion puts the redirect back.
- **Add to Home Screen.** A manifest (name, icons, `display: standalone`; the preview's copy is called "Ballotta (preview)", a separate app on a phone), three icons drawn from the logo by `source/make_icons.py`, iPhone meta tags, and `viewport-fit=cover` so the bars reach the screen's edges on notched phones (this also fixes the logged "`env(safe-area-inset-bottom)` is 0" issue). The page's CSP gains `manifest-src 'self'` and `worker-src 'self'` **in phone builds only**.
- **The offline copy (`sw.js`).** Network first, as Lane chose: online, every request of this site's own files goes to the network as if the copy didn't exist, and the answer is kept; offline, or with no answer after 4 seconds (difference 15), the kept copy of that file is used (and a late answer still refreshes it). Lookups (the county, the Census) and counting never go through it, and a link's `#picks` never reach a service worker. Phones only. **Kill switch:** `OFFLINE = False` in `build_site.py` writes a `sw.js` that deletes its copies and unregisters itself, and the page itself, instead of installing it, unregisters it and deletes the copies.
- **iPhone Home Screen storage.** A Home Screen web app on an iPhone keeps its own storage, apart from Safari's, and isn't subject to Safari's 7-day clean-up (WebKit's 2020 statement, as reported by [Search Engine Land](https://searchengineland.com/what-safaris-7-day-cap-on-script-writeable-storage-means-for-pwa-developers-332519); Task 11 checks it on a real iPhone). Good for keeping picks; but the app starts empty. So on an iPhone the install sheet first offers **Copy my picks link** (a normal keep link), and the Home Screen app shows **Paste my picks link** (landing page and menu), which opens the usual "Load your saved picks?" window. The link never leaves the phone. Android's installed app shares the browser's storage, so it gets none of this (no paste box there). "Paste from clipboard" only ever shows clipboard text that is a Ballotta link.
- **Counting.** One new event, `home_screen` (`opened` from `menu` or `card`, `prompted`, `added`, `copied`, `pasted`); `backup_nudge` gains the action `home`; events from a Home Screen app carry `app: yes` (and nothing new otherwise, so every existing payload is unchanged). All are added to the firewall's list inside PHONE markers. The phone FAQ is counted as `faq_seen`, like the laptop's (once a visit, when a scroll brings it into view).

## Base and baseline (measured Oct 15)

- `main` at **06b7030** ("Issues round C"), clean tree, issue list empty.
- `python3 source/build_site.py` rewrites `index.html` with sha256 **8e6eaf368729c6b9f9fb5e43c2285d477bb77397e82ee080dfddf2e7b2de5a2e** (357 KB); `census.html` unchanged.
- `python3 tests/test_site.py`: 71/71 pass.

## Dry run (done on a throwaway copy, Oct 15)

Every script in the appendix was applied, in order, to a copy of the repo at 06b7030:

- `index.html` rebuilt byte-identical (sha above) with all the phone code in the template; `next/index.html` 396 KB; all three inline scripts and `sw.js` pass `node --check`.
- Live suite (`index.html`): **71/71 passed, 17 skipped** (the phone tests), the same 71 that pass today.
- Preview suite (`next/index.html`): **57/57 passed, 31 skipped** (the old-phone tests). Then, after the last two small fixes (a 44px "See all" and a wait in the paste test), the four tests they touch passed again. With no phone layout (`index.html`), 15 of the 17 phone tests fail, as they should, and 2 pass by design (Task 4).
- Mutation kill: **53 of 53** phone mutants killed (one run hit a race in the paste test, which is now fixed, so the last 32 were rerun), and **17 of 17** laptop mutants on the files this round changes. Every file was restored afterwards: `index.html` 8e6eaf36…5a2e.
- Screenshots at 390×844 looked as intended (landing, decide, fold, measure, list sheet, at a glance, where to vote, crib sheet, menu, install sheet, share).

## Task 0 — Re-check the base, file this plan, unpack the scripts

```
cd /home/claude/ballotta
git log --oneline -1          # expect: 06b7030 Issues round C: name-block gaps, stored-data checks, backup nudge
git status --short            # expect: nothing
python3 source/build_site.py && git status --short && sha256sum index.html
# expect: "index.html 357 KB", "census.html", no status lines, then 8e6eaf36…5a2e
```

If the sha differs, a data rebuild happened since this plan: re-pin `LIVE_SHA` in the test edit script (Task 4) to the new value before continuing.

Save this plan, as Lane approved it, to `docs/plans/2026-10-15-phone-layout.md` (it is committed with the preview in Task 10). Then unpack the appendix's files into an empty folder outside the repo:

```
P=/tmp/claude-0/-home-claude/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/phone-P   # the scripts unpacked in Task 0 (each block sets it: shells don't keep it)
mkdir -p $P
python3 - "$P" <<'EOF'
import re, sys, pathlib
plan = pathlib.Path('docs/plans/2026-10-15-phone-layout.md').read_text(encoding='utf-8')
files = re.findall(r'^```\w+ file=(\S+)\n(.*?)^```$', plan, re.S | re.M)
for name, body in files: (pathlib.Path(sys.argv[1]) / name).write_text(body, encoding='utf-8')
print(len(files), 'files:', ' '.join(n for n, _ in files))
EOF
# expect: 10 files: edits_build_P.py make_icons.py phone.css phone.js edits_template_P.py phone_tests.py edits_tests_P.py mutate_phone.py edits_mutate_P.py edits_readme_P.py
```

Every edit script checks each anchor occurs exactly once and writes nothing if one doesn't, so a second run, or a run on a changed file, stops with an `AssertionError` naming the anchor.

## Task 1 — `source/build_site.py` (edit P1)

```
P=/tmp/claude-0/-home-claude/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/phone-P   # the scripts unpacked in Task 0 (each block sets it: shells don't keep it)
python3 $P/edits_build_P.py      # expect: build_site.py: PHONE markers, Home Screen files, preview CSP
python3 source/build_site.py && sha256sum index.html     # expect: the same 8e6eaf36…5a2e (nothing marked yet)
```

What it does: `PHONE_LIVE = False` and `OFFLINE = True`; `strip_marked(html, tag)` (the old `strip_desk` body, naming its tag in every message) with `strip_desk` and `strip_phone` as one-liners; `build(preview, desk, phone)` strips PHONE unless the preview or `PHONE_LIVE`, refuses `phone` without `desk`, and with `OFFLINE = False` swaps the page's `register('sw.js')` for an unregister; `csp_meta(html, phone)` adds `manifest-src 'self'; worker-src 'self'` to phone builds; `manifest(preview)`, `SW_JS` and `SW_OFF_JS`; `--preview` now refuses only once `PHONE_LIVE`, and writes `manifest.webmanifest` and `sw.js` next to the page it builds.

## Task 2 — Home Screen icons

```
P=/tmp/claude-0/-home-claude/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/phone-P   # the scripts unpacked in Task 0 (each block sets it: shells don't keep it)
cp $P/make_icons.py source/make_icons.py
python3 source/make_icons.py     # expect: icon-192.png, icon-512.png, icon-maskable-512.png
file icon-*.png                  # expect: 192 x 192 and two 512 x 512 PNGs
```

Plum square, gold sun, porch-light bowl; the maskable one keeps the logo inside the middle 70% so a round or squircle mask never clips it. Open `icon-maskable-512.png` and look at it before moving on.

## Task 3 — The template (edit P2: `phone.css`, `phone.js`, markup and hooks)

```
P=/tmp/claude-0/-home-claude/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/phone-P   # the scripts unpacked in Task 0 (each block sets it: shells don't keep it)
python3 $P/edits_template_P.py   # expect: template: phone layout added inside PHONE markers
python3 source/build_site.py && sha256sum index.html     # expect: still 8e6eaf36…5a2e: every addition is marked
python3 source/build_site.py --preview                   # expect: next/index.html 396 KB, next/manifest.webmanifest next/sw.js
python3 - <<'EOF'
import re, subprocess, pathlib
h = pathlib.Path('next/index.html').read_text(encoding='utf-8')
for i, js in enumerate(re.findall(r'<script>(.*?)</script>', h, re.S)):
    p = pathlib.Path('/tmp/_ballotta_check.js'); p.write_text(js, encoding='utf-8')
    print('inline script', i, subprocess.run(['node', '--check', str(p)], capture_output=True, text=True).stderr or 'ok')
print('sw.js', subprocess.run(['node', '--check', 'next/sw.js'], capture_output=True, text=True).stderr or 'ok')
EOF
# expect: inline script 0 ok / inline script 1 ok / inline script 2 ok / sw.js ok
```

The edit adds, all inside PHONE markers:

- **Head**: a second viewport tag with `viewport-fit=cover` (the later one wins), the manifest link, the iPhone and Android "web app" tags.
- **Styles** (`phone.css`, after the laptop's): the whole phone layout, inside `@media screen and (max-width:1023px)`, plus `.ph-only, .ph-faq {display:none}` outside it.
- **Markup**: a "Done" button in the rail's header; a Home Screen line in the laptop's backup card (shown only at 25 picks, on a phone); the fold button and the Previous / Next row around the notes; the bottom bar after the landing band; the "Paste my picks link" box above the address form; the FAQ's fold container after the laptop FAQ; three sheets (`#ph-menu`, `#ph-install`, `#ph-paste-d`) after the laptop's info window.
- **Counting**: `EVENTS.home_screen`, `backup_nudge`'s `home`, the `app` detail in `clean()` and `track()`.
- **Phones only for the extras**: the offline copy is installed, and Chrome's install offer held for our button, only below 1024px.
- **Hooks in shared and laptop code** (each an inline pair that strips back to today's line): the backup card tells the phone it's showing; "Not now" on a phone returns focus to the paper; the laptop's `render()` calls `phone.after()` at its end (and on its no-ballot early return); a friend's picks count `share_compare` on a phone too; narrowing a window no longer resets the print options (a phone shows them now); `desk.ph` exposes `ui, go, setView, act, nextUndecided, idx, curB, decided`.
- **The controller** (`phone.js`), after the laptop block and before `start()`.

## Task 4 — Tests (edit P3), RED first

```
P=/tmp/claude-0/-home-claude/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/phone-P   # the scripts unpacked in Task 0 (each block sets it: shells don't keep it)
python3 $P/edits_tests_P.py      # expect: tests: phone layout tests added
```

It adds `HAS_PHONE`, re-pins `LIVE_SHA` to 8e6eaf36…5a2e (from 06b7030), `phone_test` and `PHONE_TESTS`, `OLD_PHONE_TESTS` (the 31 tests that drive today's phone page: they run on `index.html` only; promotion moves them, Task 13), `size`/`sw`/`ua` options for `new_page` (and service workers blocked unless a test asks), PHONE checks in `live_build_is_unchanged_until_promotion`, `EVENTS.x` lines in `event_names_in_page()`, and the 17 phone tests in `phone_tests.py`. `phone_whole_visit_counts_only_listed_events` covers, on the new layout, what the 31 skipped tests cover on today's page (sources, directions, wait times, photo ID, keep there and back, share, clearing, the firewall).

**RED first.** The phone tests must fail where there is no phone layout. Run all 17 against the live page, which has none (the runner below calls tests directly, so nothing is skipped). Two are built to pass there, and their RED comes from mutants in Task 8: `laptop_unchanged_by_the_phone_code` (P35) and `laptops_get_no_offline_copy_or_install_prompt` (P46, P47). The code was written before these tests (Task 3), so the behavioural RED, test by test, is the mutation kill in Task 8.

```
P=/tmp/claude-0/-home-claude/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/phone-P   # the scripts unpacked in Task 0 (each block sets it: shells don't keep it)
cat > $P/one.py <<'EOF'
"""Run named tests:  python3 one.py name [name ...]   (from the repo root; BALLOTTA_PAGE picks the page)"""
import os, sys
os.environ.setdefault('BALLOTTA_PAGE', 'index.html'); sys.path.insert(0, 'tests')
import test_site as T
from playwright.sync_api import sync_playwright
srv = T.serve(); bad = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for n in sys.argv[1:]:
        try: getattr(T, n)(b); print('PASS', n)
        except Exception as e: bad += 1; print('FAIL', n, '-', (str(e) or type(e).__name__)[:300])
    b.close()
srv.shutdown(); sys.exit(1 if bad else 0)
EOF
BALLOTTA_PORT=8790 python3 $P/one.py $(python3 -c "import sys; sys.path.insert(0, 'tests'); import test_site as T; print(' '.join(f.__name__ for f in T.TESTS if f.__name__ in T.PHONE_TESTS))")
# expect: 15 FAILs, and PASS for laptops_get_no_offline_copy_or_install_prompt and laptop_unchanged_by_the_phone_code (several minutes: failures wait for their timeouts)
```

Then GREEN on the preview, a few at a time (each takes 10–40 seconds; the county lookup is live):

```
P=/tmp/claude-0/-home-claude/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/phone-P   # the scripts unpacked in Task 0 (each block sets it: shells don't keep it)
BALLOTTA_PORT=8790 BALLOTTA_PAGE=next/index.html python3 $P/one.py phone_landing_band_form_and_faq phone_lookup_opens_the_app_at_its_top phone_pick_reason_fold_and_steps phone_next_undecided_then_the_crib_sheet
BALLOTTA_PORT=8790 BALLOTTA_PAGE=next/index.html python3 $P/one.py phone_ballot_list_sheet phone_glance_vote_and_crib_fit_the_screen phone_menu_is_a_sheet phone_friend_link_landing_then_inline
BALLOTTA_PORT=8790 BALLOTTA_PAGE=next/index.html python3 $P/one.py phone_backup_card_sits_above_the_bar phone_add_to_home_screen_three_ways phone_home_screen_app_pastes_picks phone_offline_copy_after_one_visit
BALLOTTA_PORT=8790 BALLOTTA_PAGE=next/index.html python3 $P/one.py laptops_get_no_offline_copy_or_install_prompt phone_whole_visit_counts_only_listed_events phone_runs_under_the_page_lock phone_resize_keeps_things_in_step
BALLOTTA_PORT=8790 BALLOTTA_PAGE=next/index.html python3 $P/one.py laptop_unchanged_by_the_phone_code live_build_is_unchanged_until_promotion
# expect: PASS for all 18
```

What the phone tests check (all at 390×844 unless said):

| Test | Checks |
|---|---|
| `phone_landing_band_form_and_faq` | plum bar and band, the paper overlapping it, steps, six FAQ folds with the laptop's exact words, `faq_seen` counted once after a scroll, old brand/About/footer hidden, a 44px menu button named "Feedback & Info", nothing sideways at 390 or 320px |
| `phone_lookup_opens_the_app_at_its_top` | after a lookup from mid-page: the app, the bar ("0 of 63 decided", "Next undecided →"), contest 1, scrolled to the top, focus on its heading; precinct and a 44px Share button in the bar; `ballot_found` counted as phone |
| `phone_pick_reason_fold_and_steps` | through the list's search to District 9; a pick (bar count follows), a reason saved; the fold closed, then open with the office note, staying open to the next contest (a measure: "Sources"); Previous / Next, Previous disabled at contest 1; no shortcuts; the browser asked once to keep data (#49) |
| `phone_next_undecided_then_the_crib_sheet` | a ballot saved on the phone opens without moving focus; Next undecided skips decided ones; "Crib sheet →" once all are decided; it opens the crib view and hides there; counted |
| `phone_ballot_list_sheet` | full screen, the page behind `inert`, focus on the current row; Escape and Done close it and return focus; search kept; filters; Keep from the sheet; a view tap closes it on that view's heading; Print… lands on the real Print button |
| `phone_glance_vote_and_crib_fit_the_screen` | 16px fields (no iPhone zoom); a pick from a dropdown; a contest's name opens it at the top; no Learn-more column; 5 vote centres, the map folded (once, even after switching period); print options, printing counted as phone; the printout is the crib sheet alone; options survive widening and narrowing; nothing sideways at 320px |
| `phone_menu_is_a_sheet` | the laptop menu's items in a sheet (+ Home Screen), `aria-haspopup="dialog"`; privacy opens the info window, counted; Change address and Back; at 1440px the laptop dropdown again |
| `phone_friend_link_landing_then_inline` | their picks first, then "See Maya's picks beside yours" and the form; inline "Maya picked this" after the lookup; fold label "You and Maya · …"; `share_compare` once; Hide |
| `phone_backup_card_sits_above_the_bar` | the card above the bar, not over it; no Home Screen line at 5, one at 25; it opens the install sheet; `backup_nudge` `home` and `home_screen` `opened`/`card` counted; nothing dropped |
| `phone_add_to_home_screen_three_ways` | Android: the browser's prompt, `opened`/`prompted`/`added`; afterwards "where to look"; iPhone: no carry step without picks, then the steps and Copy my picks link (a real `#k2…` link on the clipboard, counted as `copied` and `keep_created`) |
| `phone_home_screen_app_pastes_picks` | Android's Home Screen app: no paste box or item; an iPhone's: the paste box and menu item (no install item); junk and a friend's link refused with a reason; a keep link inside other words loads the picks and reasons; `pasted`, `keep_restored` with `app: yes`; the clipboard button, which never shows clipboard text that isn't a link |
| `phone_offline_copy_after_one_visit` | on a server of its own, with the page's CSP on: the offline copy installs and takes charge (scope `/next/`); the manifest and icons are right; a changed page shows at once online (network first); the page and its fonts are kept, nothing from elsewhere; with the server stopped (no network for the offline copy either) the page and its fonts still load; no CSP violations |
| `laptops_get_no_offline_copy_or_install_prompt` | at 1440px: no offline copy installed, and Chrome's install offer not held back |
| `phone_whole_visit_counts_only_listed_events` | sources and their counts, photo ID and notes, wait times and directions, a keep link (then opened elsewhere: picks and reasons back), a share link, Clear my picks and Clear everything from the menu sheet; everything counted is listed and says "phone" |
| `phone_runs_under_the_page_lock` | a whole phone visit with the CSP on (friend link, lookup, pick, fold, every view, the map, menu, install, share): no violations; an injected script still can't run |
| `phone_resize_keeps_things_in_step` | an open list closes and the page is reachable again when the window widens; the laptop rail shows; back at phone width, the bar |
| `laptop_unchanged_by_the_phone_code` | at 1440×900 and 1024×640, built with and without the phone code: landing, ballot, a pick with a reason, at a glance, where to vote, crib sheet and the open menu are identical, pixel for pixel |

## Task 5 — Mutation runner (edit P5) and the phone mutants

```
P=/tmp/claude-0/-home-claude/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/phone-P   # the scripts unpacked in Task 0 (each block sets it: shells don't keep it)
python3 $P/edits_mutate_P.py     # expect: mutate_desk.py: page override; M41 and B1 re-anchored
cp $P/mutate_phone.py tests/mutate_phone.py
```

## Task 6 — README (edit P4)

```
P=/tmp/claude-0/-home-claude/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/phone-P   # the scripts unpacked in Task 0 (each block sets it: shells don't keep it)
python3 $P/edits_readme_P.py     # expect: README: phone layout, Home Screen, counts
```

Adds a "Phone layout (preview at ballotta.org/next/)" section (what it is, Add to Home Screen, the offline copy and its kill switch, how the live page is protected), the `app` detail, `home_screen`, `backup_nudge`'s `home`, `share_compare` on the phone preview, and the new commands.

## Task 7 — Build and run both suites

```
python3 source/build_site.py && python3 source/build_site.py --preview && sha256sum index.html
# expect: index.html 357 KB, census.html, next/index.html 396 KB, next/manifest.webmanifest next/sw.js, 8e6eaf36…5a2e
git status --short
# expect: M README.md, M next/index.html, M source/build_site.py, M source/template-travis.html, M tests/mutate_desk.py,
#         M tests/test_site.py, ?? docs/plans/2026-10-15-phone-layout.md, ?? icon-192.png, ?? icon-512.png,
#         ?? icon-maskable-512.png, ?? next/manifest.webmanifest, ?? next/sw.js, ?? source/make_icons.py,
#         ?? tests/mutate_phone.py        (index.html and census.html unchanged)
BALLOTTA_PORT=8790 python3 tests/test_site.py                                   # expect: 71/71 passed, 17 skipped (index.html)
BALLOTTA_PORT=8791 BALLOTTA_PAGE=next/index.html python3 tests/test_site.py      # expect: 57/57 passed, 31 skipped (next/index.html)
```

Each suite takes 10–15 minutes (live county lookups). They can run side by side on different ports.

## Task 8 — Mutation kill (RED-first)

Run in slices (a shell may cap one command's time); don't edit, build or commit while it runs.

```
BALLOTTA_PORT=8790 python3 tests/mutate_phone.py 0 14      # expect: "baseline: every target test passes unmutated", then 14 of 14 mutants killed
BALLOTTA_PORT=8790 python3 tests/mutate_phone.py 14 28     # expect: 14 of 14 mutants killed
BALLOTTA_PORT=8790 python3 tests/mutate_phone.py 28 42     # expect: 14 of 14 mutants killed
BALLOTTA_PORT=8790 python3 tests/mutate_phone.py 42 53     # expect: 11 of 11 mutants killed      (53 in all; about 40 minutes)
BALLOTTA_PORT=8790 python3 - <<'PY'
import sys; sys.argv = ['mutate_desk.py']; sys.path.insert(0, 'tests')
import mutate_desk as R
R.main([m for m in R.M if m[1] in (R.BLD, R.MD_SELF, R.TPL)])   # the laptop mutants on the build script, the runner and the template (the README's still pass: its anchors are untouched)
PY
# expect: 17 of 17 mutants killed (M1, M2, M24, M37, M41, V50, A23, A27–A29, B1–B4, B9, B11, B13)
git status --short && sha256sum index.html   # expect: the same list as Task 7 (docs/plans line included) and 8e6eaf36…5a2e: every file restored
```

A survivor means a test doesn't really check what it claims: strengthen the test (never weaken the mutant), rerun that slice, and log it in "Execution log".

## Task 9 — Adversarial audit before any commit (remediation-audit)

Pass 1: three independent agents, each on a tarball copy with its own port (never 8765), each told *"Do not run any git command (not even status/diff) against /home/claude/ballotta; work on a copy."*:

1. **Phone UX and accessibility** at 320, 390 and 430px and an iPad upright (810px): VoiceOver-style focus order, every target ≥ 44px or justified, the sheets' focus traps and returns, zoom-on-focus, landscape phones (844×390), the iPhone notch and home indicator with `viewport-fit=cover`.
2. **Security and privacy**: the CSP additions, `sw.js` (what it caches, a #fragment can never reach it, cross-origin never cached, the kill switch), the paste flow (only `k` links, the text never leaves the phone), the manifest, the `app` detail and new events against the firewall.
3. **Laptop and live-page regressions**: the strip guarantees (`index.html` sha), laptop behaviour with the phone code present (not just pixels: events, focus, keys), resize in both directions, printing from a phone and from a laptop.

Fix each real finding test-first; then narrow passes on the changed code until a pass finds nothing new. File anything that predates this round as a GitHub issue (milestone 2).

## Task 10 — Commit and push the preview

```
git add README.md next/index.html next/manifest.webmanifest next/sw.js source/build_site.py source/make_icons.py source/template-travis.html \
        tests/mutate_desk.py tests/mutate_phone.py tests/test_site.py icon-192.png icon-512.png icon-maskable-512.png docs/plans/2026-10-15-phone-layout.md
git -c user.name="Lane Becker" -c user.email="3211673+lanebecker@users.noreply.github.com" commit -F - <<'EOF'
Phone layout preview at /next/: the laptop app folded up, Add to Home Screen, offline copy

The live page is unchanged (PHONE_LIVE = False strips every PHONE block; sha pinned) and laptops see the same pixels
(tested with and without the phone code). Plan: docs/plans/2026-10-15-phone-layout.md.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01ESRbqS3dGWHQThLF6J7gxN
EOF
git push origin main
```

Then, once GitHub Pages has deployed (the preview check first, so the live check isn't run against the old deploy):

```
until curl -s https://ballotta.org/next/ | grep -q 'id="ph-bar"'; do sleep 15; done; echo preview up   # expect: preview up (a minute or two)
curl -s https://ballotta.org/ | sha256sum              # expect: 8e6eaf36…5a2e (the live page, after the deploy, unchanged)
curl -s https://ballotta.org/next/manifest.webmanifest | python3 -m json.tool | grep '"name"'   # expect: "Ballotta (preview)"
```

## Task 11 — Lane's review on a real phone

The tests run in Chromium; an iPhone's Safari is the real audience. Lane, on your iPhone:

1. Open https://ballotta.org/next/ in Safari, look up your address, make a few picks, write a reason.
2. Menu (☰) → **Add to your Home Screen** → **Copy my picks link** → Share → **Add to Home Screen** (it will be called "Ballotta (preview)").
3. Open it from the Home Screen: it should start empty and offer **Paste my picks link**; paste, load, check your picks and reasons came along.
4. Turn on Airplane Mode, close and reopen the Home Screen app: it should still open (lookups won't work offline).
5. Anything that looks off, tell me; a screenshot helps. Review rounds follow the usual ritual (test first, audit).

If you have an Android phone handy, step 2 there should show Chrome's own install prompt.

## Task 12 — Cold audit before promotion

An agent that hasn't seen this work reads the plan, the diff and the preview, and tries to break it (the cold-audit skill). Findings are fixed test-first before Task 13.

## Task 13 — Promote (a short plan of its own, after Lane's "go")

Written after the review rounds, because they change the code it would test. It will: set `PHONE_LIVE = True`; put `next/index.html` back to the redirect, keep `next/sw.js` as the self-removing `SW_OFF_JS` (deleting it would leave a phone's preview copy running; a 404 doesn't remove a service worker) and drop `next/manifest.webmanifest` (the root ones take over; the preview's Home Screen app then opens the redirect); move the 31 `OLD_PHONE_TESTS` to the new layout (most by switching their helpers to the app's elements); turn `desk_phone_layout_matches_live_page` into a rollback test; and run the full ritual. Rollback after promotion: `PHONE_LIVE = False`, rebuild, push.

What the audits taught this task (Oct 16):
- `outputs()` already writes `next/sw.js` as the self-removing worker once `PHONE_LIVE = True`; keep it deployed for good (a 404 never removes a service worker). One visit to `/next/` then clears a phone's preview copy (measured: 2.6 s).
- If the `/next/` redirect page also unregisters, it must check the scope first: `getRegistration('./')` on a `/next/` page returns the *root* registration when there is no `/next/` one. Unregister only when `g.scope === new URL('./', location.href).href`.
- Tests that swap `sw.js` must let the browser's own update check (a few seconds after load) settle first, or they pass for the wrong reason.

## Risks and unknowns

- **iPhone behaviours the tests can't reproduce**: separate Home Screen storage, the paste callout for "Paste from clipboard", the share sheet's "Add to Home Screen" place, `black-translucent` status bar. Task 11 checks them on a real phone; the paste box also works by hand if the clipboard button doesn't.
- **A stuck offline copy.** Network-first means an online phone gets the newest page whenever the network answers within 4 seconds (difference 15); the kill switch exists for the unexpected.
- **Android's automatic install banner**: on phones, Chrome's own "Add to Home screen" banner is held back so our menu item and card show the prompt instead; Chrome may still offer installing from its own menu.
- **Mixed tap-target sizes**: every phone control is at least 44px tall except links set in a line of text: the campaign and League links under each name and Directions (about 26px, as on today's phone page; WCAG 2.2's minimum is 24px).
- **`text-wrap: balance`** (the voting-period buttons) needs Safari 17.5+; older phones just wrap normally.
- **iPad held sideways** (1024px+) gets the laptop layout as today, with no offline copy (laptop widths don't install it); with `viewport-fit=cover`, a Home Screen app there could tuck the laptop's last line under the home indicator. Low impact; noted for the audit.

## Self-review (write-plan)

1. **Spec coverage**: every "done" item and every one of Lane's four answers maps to a task: layout (Task 3), landing band and FAQ folds (Task 3, tested in `phone_landing…`), Previous / Next (`phone_pick…`), install in menu and at 25 (`phone_menu…`, `phone_backup…`, `phone_add…`), offline network-first (`sw.js`, `phone_offline…`, which really cuts the network), live unchanged (`live_build…`), laptops unchanged (`laptop_unchanged…`, `laptops_get_no…`), "every feature" (`phone_whole_visit…`).
2. **Placeholder scan**: no "TBD", no "add appropriate error handling", no "write tests for the above", no "similar to Task N". Task 13 is deliberately a separate plan, and says why.
3. **Names**: `PHONE_LIVE`, `OFFLINE`, `strip_phone`, `csp_meta(html, phone)`, `manifest()`, `SW_JS`, `desk.ph`, `phone.after/nudge`, the ids `ph-*` are the same in every script, test and this text.

## Verification pass

An independent agent with no part in writing this plan got Lane's request and answers verbatim, extracted the repo at 06b7030, ran Tasks 0–7 exactly as written, recomputed every count, read the code against the 13 phone mocks, and hunted for overstatements and understatements (Oct 15–16). Every "expect:" line in Tasks 1–6 matched, `index.html` stayed byte-identical, both suites passed with the stated counts, and all 45 mutant anchors were found once. It also found the following problems. All of them are fixed in this version, and the dry-run numbers above are from after the fixes.

1. **Critical: the offline test couldn't fail.** Playwright's "offline" doesn't cut a service worker's own network, so a copy that was never used, a cache-first copy (the opposite of "fresh online"), and one that kept only the page all passed. My own mutation run agreed: P33 survived. *Fixed:* the test now runs on a server of its own and stops it before the offline reload. It also checks that a changed page shows at once while online, and that the kept files are the page and its fonts from this site only. New mutants P51 (page only) and P52 (cache first) are killed, and P33 is killed now.
2. **Major: Task 0 read a plan file that didn't exist in the repo yet**, and Task 7's expected `git status` was missing it. *Fixed:* Task 0 saves the plan first, and both status lists include it.
3. **Major: `$P` was set once but used in later blocks.** Shells don't keep it between commands. *Fixed:* every block that uses it sets it.
4. **Major: laptops did change.** The offline copy was installed at every width, and Chrome's install offer was held back everywhere, while the pixel test couldn't see either. *Fixed:* both happen on phones only. A new test, `laptops_get_no_offline_copy_or_install_prompt`, checks this, with mutants P46 and P47.
5. **Major: the 4-second fallback bends Lane's "always the newest page when there's signal"** and wasn't put to him. *Fixed:* it is now difference 15, for Lane to decide.
6. **Major: Task 8's commands would have used port 8765.** *Fixed:* every command sets `BALLOTTA_PORT`.
7. **Major: "done" item 1 wasn't tested on the phone layout.** The 31 skipped tests covered clearing, source counts, wait times, photo ID, a keep round trip, sharing and the firewall only on today's page. *Fixed:* `phone_whole_visit_counts_only_listed_events` covers them on the new layout. Mutant P53 checks the menu's Clear my picks.
8. **Minor: RED-first was shown for 4 of the tests.** *Fixed:* Task 4 runs all 17. Two pass by design, and the plan names the mutants that give them their RED.
9. **Minor: the differences list was off.** The mock's views are wrapping chips, not "a list", and a CSS comment contradicted difference 8. Four differences were missing: the header order, the "Done" style, the landing's words, and the uncounted phone FAQ. *Fixed:* differences 6, 13 and 14 are corrected or added, the comment is fixed, and the phone FAQ is now counted as `faq_seen` (mutant P50).
10. **Minor: the kill switch could leave the copies behind.** The page unregistered the offline copy before it could clean up, and Task 13 would have deleted `next/sw.js`, which leaves the old copy running. *Fixed:* the page now deletes the copies itself, and Task 13 keeps a self-removing `next/sw.js`.
11. **Minor: an installed Android app showed "Made picks in Safari?"**, and "Paste from clipboard" put any clipboard text on screen. *Fixed:* the paste box appears on iPhones only, and only a Ballotta link is ever shown. The test checks both, with mutants P48 and P49.
12. **Minor: wrong numbers in comments.** Comments said "Task 14" where they meant 13, the dry run said "both inline scripts" when there are three, and Task 8's comment about the 17 laptop mutants was imprecise. *Fixed:* all three are corrected, and Task 3 now checks all three scripts.
13. **Minor: some phone targets were 32–36px, there was a zoom gap between 1023 and 1024px, and the band ignored a landscape notch.** *Fixed:* prompts, filters, the friend's Hide link, the reason links and "See all" are 44px. The phone query ends at 1023.98px. The band and the landing pad for the notch. The links set inside text (about 26px, as today) are listed under Risks.
14. **Minor: `'manifest' not in live` would trip on any League text containing "manifesto".** *Fixed:* the check is now `'rel="manifest"' not in live`.
15. **Minor: Task 10's live check could run before Pages deployed**, and the "WebKit, 2020" citation linked to Search Engine Land. *Fixed:* Task 10 waits for the preview before checking the live page, and the citation now names its real source.

Found while acting on these: the paste test had a race. The clipboard is read in the background, so the test now waits for the message. One mutation run reported it as INCONCLUSIVE.

## Execution log

**Oct 16, 8:19am.** Lane approved all 15 differences (including the 4-second offline rule) and said "Let's build this."

**Tasks 0–8, as written.** Every "expect" line matched: the 10 scripts unpacked byte-identical to the dry run; `index.html` 8e6eaf36…5a2e after every step; `71/71 passed, 17 skipped (index.html)`; `57/57 passed, 31 skipped (next/index.html)`; phone mutants 0–21 killed on the repo (21 of 21), the rest already killed on byte-identical files in the dry run (32 of 32), laptop mutants 17 of 17.

**Task 9, Pass 1** (three independent agents, executed reproductions only). 23 findings; the introduced ones were fixed test-first in round D (`edits_round_D.py`, `reanchor_D.py`, `readme_D.py`), each new test RED on the old code first:

| Finding | Fix |
|---|---|
| A1 HIGH: "Your ballot" showed no contests on a phone on its side | the whole sheet scrolls below 560px tall |
| A2: a 30-letter friend name pushed the page sideways (the fold label) | wraps |
| A3: Tab left controls under the sticky top bar (WCAG 2.4.11) | `scroll-padding-top`, plus a scroll for Tab focus (reworked in E–G) |
| A4: the backup card filled a landscape screen | a compact one-line card there |
| A5: Escape only worked with focus inside the sheet | Escape closes it from anywhere (a search's first Escape still clears it) |
| A6: widening with the sheet open dropped focus | focus returns to the same row |
| A7/C5: the menu button's `aria-expanded` lied after a resize | read from the menu; narrowing puts the laptop menu away |
| A8: the backup card came before the paper in Tab order on a phone | moved after it on phones, back on laptops |
| A9: At-a-glance contest names were 24px targets | 44px |
| B1: "Paste from clipboard" showed text around a link | only the link is ever shown; the box empties on close |
| B2: the kill switch could leave a cache behind | reworked in E–F |
| B3: promotion would leave the preview's offline copy running | `outputs()` writes a self-removing `next/sw.js`; separate cache names |
| C1: a narrow laptop window installed the offline copy | phones and tablets only (coarse pointer) |
| C2: a laptop-wide Home Screen window added `app` to every event | phone widths only |
| C3: phone sheets stayed open after widening (and blocked the laptop's keys) | widening closes them |
| C7: the live-page check couldn't see changed line endings | compares bytes and hashes the file on disk |
| hardening: `/*PHONE*/ … <!--/PHONE-->` was accepted | refused |
| nit: a damaged pasted link was counted as pasted | decoded first, refused with a reason |

Accepted and documented (README): C4, laptop print options now survive a narrow-and-back resize (a phone shows them); C6, `share_compare` counts when a friend's picks first show beside a ballot at any width. Pre-existing, filed: **#50** (the counting firewall passes `title`/`tag` as free text), **#51** (26px campaign/League links). B4 (no "saved copy" notice when the 4-second rule serves the kept page) is a design question for Lane, not a defect.

**Pass 2** (narrow, on round D): two reproduced bugs, fixed in round E: the offline copy answered from any cache on the site (now only its own), and the focus scroll moved buttons out from under a click; also the kill switch's width gate, focus kept in the card when it moves, an escaped focus key. **Pass 3** (on round E) reproduced that round E's "update every other copy" loop could remove the *live* copy over a captive portal or one 503, and that tapped text fields still jumped. Round F removed the loop (retiring the preview's copy is Task 13's job), made the kill switch remove a copy only through the self-removing `sw.js` (never on a failed fetch), and made the focus scroll follow the Tab key itself. **Pass 4** (on round F): nothing above LOW; round G makes the Tab flag last only for its own Tab (a Tab out of the page had left it set) and proves the kill-switch's 503 case actually asked for `sw.js`. Converged.

**Mutants retired as equivalent:** P63 (the menu button's state after a resize: narrowing now always closes the menu, so it is always "false"), P79 (view buttons never lose focus on widening: the laptop doesn't redraw them), P80 (the kill switch's width gate: Chromium's own update check on reload removes the copy anyway; the explicit call is for Safari), P83 and P84 (the Tab flag's other two resets: the timer clears it first). Final list: 79 phone mutants.

**Final numbers** (on the repo, after round G): `71/71 passed, 25 skipped (index.html)`; `65/65 passed, 31 skipped (next/index.html)`; phone mutants: all 79 killed (the whole list ran on round F's code, 79 of 81 killed with P80 and P83 the two retired above; round G changes only the Tab flag, so the 13 mutants nearest it, P56, P77, P78 and the last ten through P85, ran again on the final code: 13 of 13), laptop mutants 17 of 17. `index.html` is still 8e6eaf36…5a2e and `next/index.html` is 401 KB. Changed expectations since the plan was written: the build prints one line per file written (`next/index.html 401 KB`, `next/manifest.webmanifest`, `next/sw.js`); there are now 25 phone tests, so the suites print `71/71 passed, 25 skipped` and `65/65 passed, 31 skipped`.

**Oct 16, round H (Lane's first look on his iPhone).** Lane: step 2 of Add to Home Screen was unclear ("How does one get the share button? Is it the button at the top of the main Ballotta page?"), and on his iPhone Share is followed by "View More" before Add to Home Screen. Also yes to B4 (say when the kept copy is showing). Approved wording, with his View More addition, then built test-first:

- The steps name and draw the browser's own buttons: "Add the icon with Safari's buttons, not Ballotta's. At the bottom right of your screen, tap Safari's [•••], then [Share] Share. If you already see Safari's [Share] in its bar, tap that instead. Scroll down and tap Add to Home Screen. Don't see it? Tap View More first…". Chrome on iOS, other iOS browsers, iPad and apps' own browsers (Instagram, Facebook, the Google app: "Open this page in Safari first") each get their own wording; an app's Safari view sends Safari's own UA, so Safari's steps end with "If another app opened this page, tap its compass or Open in Safari first." Step 1 says the copied link is the private Keep my picks link, not the Share my picks link for friends; after a copy it shows "✓ Copied" and marks step 2 as the one to do now (a new look starts at step 1). The paste screens say the same.
- The saved-copy bar: `sw.js` marks a page it answers from its kept copy (`<html data-copy="offline">` or `"slow"`, HTML navigations only), and a bar under the top bar says "No connection" / "Slow connection, so this is the copy saved on your phone." plus "Your picks are all here." or "Looking up an address needs a connection.", with Try again; it goes when the network comes back, never prints, and on the laptop layout (a tablet held sideways) it is one sticky line under the top bar with the rail moved down to make room.
- Design checker: its five "cramped padding" warnings on `template-travis.html` were measured in a browser (text sits 10–33px from every edge; the checker reads base rules, not the phone overrides) and ignored for that file in `.impeccable/config.json`. The bar uses the page's warning colours, not gold: the landing page's gold Travis County strip sits right under it.

Audits: Pass 1 (4 findings, all fixed test-first: the bar pushed the laptop rail off screen; in-app browsers were told to use Safari's buttons; a stored ballot the page can't show was promised as picks; the rewrite broke non-page files opened directly). Pass 2 on that rework (the fix had hidden the bar on a sideways tablet, now shown there instead; the bar printed; Safari-view and Opera OPX wording; the second sentence now follows the ballot). Pass 3 on that rework: nothing above LOW; fixed the clipped Try again focus ring and tested the stored-ballot sentence at boot. Left as is: Chromium ignores the copied content-encoding/length headers either way (the deletes are for WebKit, untestable here); "your phone" also shows on a tablet; a back/forward-cache restore can miss an `online` event (hypothesis).

Numbers: `71/71 passed, 27 skipped (index.html)`; `67/67 passed, 31 skipped (next/index.html)`; phone mutants: all 112 killed (P86–P118 new, P22/P33/P52/P76/P89/P91/P99/P109 re-anchored and re-run); laptop mutant anchors all present. `index.html` still 8e6eaf36…5a2e. One laptop test (`desk_launch_audit_fixes`) timed out once while both suites ran side by side on the 2-core sandbox; it passed alone and in a full rerun of the live suite (71/71), on a page byte-identical to the one it has always passed on.

## Appendix: the scripts

Each block is one file; Task 0 unpacks them by the `file=` name after the language.

```python file=edits_build_P.py
"""Phone round, edit P1: source/build_site.py. Run from the repo root:  python3 <this file>
Adds the PHONE markers (stripped from the live build until Lane promotes), the preview's Home Screen files
(next/manifest.webmanifest, next/sw.js) and the two CSP sources they need (preview only)."""
import pathlib
ROOT = pathlib.Path.cwd()
F = ROOT / 'source/build_site.py'
s = F.read_text(encoding='utf-8')

def rep(a, z, n=1):
    global s
    assert s.count(a) == n, (a[:70], s.count(a))
    s = s.replace(a, z)

rep('''    python3 source/build_site.py --preview   # next/index.html: the same page with the laptop layout on; counts nothing
''', '''    python3 source/build_site.py --preview   # next/: the same page with the phone layout on (and its Home Screen files); counts nothing
''')

rep('''DESK_LIVE = True

OPEN, CLOSE = r'(?:/\\*DESK\\*/|<!--DESK-->)', r'(?:/\\*/DESK\\*/|<!--/DESK-->)'


ALONE_OPEN, ALONE_CLOSE = re.compile(r'[ \\t]*' + OPEN + r'[ \\t]*'), re.compile(r'[ \\t]*' + CLOSE + r'[ \\t]*')


def strip_desk(html):
    """Remove every laptop-layout block. A marker alone on its line (spaces or tabs around it, nothing else) opens or
    closes a block of whole lines; a marker pair inside a line removes just the text between and including them.
    One loop both checks and removes; a marker that is neither alone nor in a one-line pair stops the build."""
    opens, closes = len(re.findall(OPEN, html)), len(re.findall(CLOSE, html))
    assert opens == closes, f"DESK markers unpaired: {opens} open, {closes} close"
''', '''DESK_LIVE = True
# The phone layout (narrower than 1024px: the laptop app folded up, plus Add to Home Screen and an offline copy) is
# marked the same way: /*PHONE*/ ... /*/PHONE*/ and <!--PHONE--> ... <!--/PHONE-->. Until Lane approves the preview at
# ballotta.org/next/, the live build removes every marked block, so index.html stays byte-for-byte what it was.
# Promotion: set PHONE_LIVE = True (docs/plans/2026-10-15-phone-layout.md, Task 13).
PHONE_LIVE = False
# The offline copy (sw.js). False writes a sw.js that removes itself and its copies from every phone that has it, and
# the page stops installing it: the switch to pull if offline copies ever cause trouble. Rebuild and push to apply.
OFFLINE = True


def marks(tag):
    return r'(?:/\\*' + tag + r'\\*/|<!--' + tag + r'-->)', r'(?:/\\*/' + tag + r'\\*/|<!--/' + tag + r'-->)'


def strip_marked(html, tag):
    """Remove every block marked with tag (DESK or PHONE). A marker alone on its line (spaces or tabs around it,
    nothing else) opens or closes a block of whole lines; a marker pair inside a line removes just the text between
    and including them. One loop both checks and removes; a marker that is neither alone nor in a one-line pair
    stops the build."""
    OPEN, CLOSE = marks(tag)
    ALONE_OPEN, ALONE_CLOSE = re.compile(r'[ \\t]*' + OPEN + r'[ \\t]*'), re.compile(r'[ \\t]*' + CLOSE + r'[ \\t]*')
    opens, closes = len(re.findall(OPEN, html)), len(re.findall(CLOSE, html))
    assert opens == closes, f"{tag} markers unpaired: {opens} open, {closes} close"
''')
rep('''            assert not in_block, f"line {n}: a DESK block opens inside another (is a closing marker sharing its line?)"''',
    '''            assert not in_block, f"line {n}: a {tag} block opens inside another (is a closing marker sharing its line?)"''')
rep('''            assert in_block, f"line {n}: a DESK block closes without opening"''',
    '''            assert in_block, f"line {n}: a {tag} block closes without opening"''')
rep('''            assert not re.search(OPEN + '|' + CLOSE, line), f"line {n}: a DESK marker inside a block isn't alone on its line"''',
    '''            assert not re.search(OPEN + '|' + CLOSE, line), f"line {n}: a {tag} marker inside a block isn't alone on its line"''')
rep('''    assert not in_block, "a DESK block is never closed (is its closing marker sharing its line with other characters?)"
    html = re.sub(OPEN + r'[^\\n]*?' + CLOSE, '', '\\n'.join(out))
    assert not re.search(OPEN + '|' + CLOSE, html), "a DESK marker survived stripping"
    return html
''', '''    assert not in_block, f"a {tag} block is never closed (is its closing marker sharing its line with other characters?)"
    html = re.sub(OPEN + r'[^\\n]*?' + CLOSE, '', '\\n'.join(out))
    assert not re.search(OPEN + '|' + CLOSE, html), f"a {tag} marker survived stripping"
    return html


def strip_desk(html):
    return strip_marked(html, 'DESK')


def strip_phone(html):
    return strip_marked(html, 'PHONE')
''')

rep('''def csp_meta(html):
    hashes = " ".join(sha(s) for s in re.findall(r"<script>(.*?)</script>", html, re.S))
    return '<meta http-equiv="Content-Security-Policy" content="' + PAGE_CSP.format(hashes=hashes) + '">'
''', '''# The phone layout adds two: its Home Screen description (manifest.webmanifest) and its offline copy (sw.js), both
# from this site only.
PHONE_CSP = "; manifest-src 'self'; worker-src 'self'"


def csp_meta(html, phone=False):
    hashes = " ".join(sha(s) for s in re.findall(r"<script>(.*?)</script>", html, re.S))
    return '<meta http-equiv="Content-Security-Policy" content="' + PAGE_CSP.format(hashes=hashes) + (PHONE_CSP if phone else '') + '">'


# ---- Add to Home Screen (phone layout). The manifest names the app and its icons; paths are relative to it, so the
# preview's copy (next/) and the live one (/) are two different apps on a phone: "Ballotta (preview)" and "Ballotta".
def manifest(preview=False):
    up = '../' if preview else ''
    return json.dumps({
        "id": "./", "start_url": "./", "scope": "./", "display": "standalone",
        "name": "Ballotta (preview)" if preview else "Ballotta", "short_name": "Ballotta",
        "description": "Your Travis County ballot for Nov 3, 2026, with private picks and a printable crib sheet.",
        "background_color": "#4B2A6B", "theme_color": "#4B2A6B",
        "icons": [{"src": up + "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                  {"src": up + "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
                  {"src": up + "icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}],
    }, indent=1, ensure_ascii=False) + "\\n"


# ---- The offline copy. Network first: online, every request goes to the network as if this file didn't exist, and
# the answer is kept; offline, or with no answer after 4 seconds, the kept copy of that same file is used. Only this
# site's own files are kept (the page, its fonts, icons, the pinned tracker); lookups (the county, the Census) and
# counting always need the network. A #fragment (saved or shared picks) never reaches a service worker.
SW_JS = (
    "// Built by source/build_site.py; don't edit sw.js. Ballotta's offline copy: network first, kept copy as a fallback.\\n"
    "const CACHE = 'ballotta-1';\\n"
    "self.addEventListener('install', () => self.skipWaiting());\\n"
    "self.addEventListener('activate', (e) => e.waitUntil(caches.keys()\\n"
    "  .then((ks) => Promise.all(ks.filter((k) => k !== CACHE).map((k) => caches.delete(k)))).then(() => self.clients.claim())));\\n"
    "self.addEventListener('fetch', (e) => {\\n"
    "  const r = e.request, u = new URL(r.url);\\n"
    "  if (r.method !== 'GET' || u.origin !== location.origin || r.headers.has('range')) return;  // the browser handles it, as if there were no copy\\n"
    "  const key = u.origin + u.pathname;  // one copy per file, whatever ?query a link adds\\n"
    "  const net = fetch(r).then((res) => {\\n"
    "    if (res.ok && res.type === 'basic') { const copy = res.clone(); e.waitUntil(caches.open(CACHE).then((c) => c.put(key, copy)).catch(() => {})); }\\n"
    "    return res;\\n"
    "  });\\n"
    "  e.waitUntil(net.catch(() => {}));  // a late answer still refreshes the kept copy\\n"
    "  e.respondWith(Promise.race([net.catch(() => null), new Promise((ok) => setTimeout(ok, 4000, null))])\\n"
    "    .then(async (first) => first || (await caches.match(key)) || net));  // nothing kept: wait for the network after all\\n"
    "});\\n")
SW_OFF_JS = (
    "// Built by source/build_site.py with OFFLINE = False: removes Ballotta's offline copy from this browser.\\n"
    "self.addEventListener('install', () => self.skipWaiting());\\n"
    "self.addEventListener('activate', (e) => e.waitUntil(caches.keys().then((ks) => Promise.all(ks.map((k) => caches.delete(k))))\\n"
    "  .then(() => self.registration.unregister())));\\n")
SW_REGISTER = "navigator.serviceWorker.register('sw.js')"
SW_REMOVE = ("navigator.serviceWorker.getRegistrations().then((rs) => Promise.all(rs.map((g) => g.unregister())))"
             ".then(() => window.caches && caches.keys()).then((ks) => ks && Promise.all(ks.map((k) => caches.delete(k))))")  # the page clears the copies too
''')

rep('''def build(preview=False, desk=None):
    """desk: include the laptop layout (default: on for the preview, or once DESK_LIVE). The phone-parity test builds both."""''',
    '''def build(preview=False, desk=None, phone=None):
    """desk: include the laptop layout (default: on for the preview, or once DESK_LIVE). phone: include the phone layout
    (default: on for the preview, or once PHONE_LIVE). The laptop-parity test builds with and without it."""''')
rep('''    if not (desk if desk is not None else (preview or DESK_LIVE)):
        html = strip_desk(html)
''', '''    desk = desk if desk is not None else (preview or DESK_LIVE)
    phone = phone if phone is not None else (preview or PHONE_LIVE)
    assert desk or not phone, "the phone layout is built on the laptop layout's code"
    if not desk:
        html = strip_desk(html)
    if not phone:
        html = strip_phone(html)
    elif not OFFLINE:
        assert html.count(SW_REGISTER) == 1, SW_REGISTER
        html = html.replace(SW_REGISTER, SW_REMOVE)
''')
rep('''    return html.replace("<!--CSP-->", csp_meta(html), 1)  # last of all: it hashes the finished scripts (#36)
''', '''    return html.replace("<!--CSP-->", csp_meta(html, phone), 1)  # last of all: it hashes the finished scripts (#36)
''')
rep('''if __name__ == "__main__":
    preview = "--preview" in sys.argv[1:]
    if preview and DESK_LIVE:
        print("The laptop layout is live, and next/index.html is a redirect to the main page: not overwriting it.")
        sys.exit(0)  # not an error, so `--preview && build_site.py` still builds the live page (Pass 2)
    html = build(preview)
    out = ROOT / ("next/index.html" if preview else "index.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out.relative_to(ROOT).as_posix(), len(html) // 1024, "KB")
    if not preview:
        (ROOT / "census.html").write_text(census_page(), encoding="utf-8")  # the Census lookup's sandbox (#36)
        print("census.html")
''', '''if __name__ == "__main__":
    preview = "--preview" in sys.argv[1:]
    if preview and PHONE_LIVE:
        print("The phone layout is live, and next/index.html is a redirect to the main page: not overwriting it.")
        sys.exit(0)  # not an error, so `--preview && build_site.py` still builds the live page (Pass 2)
    html = build(preview)
    out = ROOT / ("next/index.html" if preview else "index.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out.relative_to(ROOT).as_posix(), len(html) // 1024, "KB")
    if preview or PHONE_LIVE:  # the Home Screen files sit next to the page they belong to
        d = out.parent
        (d / "manifest.webmanifest").write_text(manifest(preview), encoding="utf-8")
        (d / "sw.js").write_text(SW_JS if OFFLINE else SW_OFF_JS, encoding="utf-8")
        print((d / "manifest.webmanifest").relative_to(ROOT).as_posix(), (d / "sw.js").relative_to(ROOT).as_posix())
    if not preview:
        (ROOT / "census.html").write_text(census_page(), encoding="utf-8")  # the Census lookup's sandbox (#36)
        print("census.html")
''')
F.write_text(s, encoding='utf-8')
print('build_site.py: PHONE markers, Home Screen files, preview CSP')
```

```python file=make_icons.py
"""Draw the Home Screen icons from the Ballotta logo (favicon.svg's shapes), with Chromium. Run from the repo root:
    python3 source/make_icons.py
Writes icon-192.png, icon-512.png (logo at 62% of the height) and icon-maskable-512.png (logo inside the middle 70%,
so a phone's round or squircle mask never clips it): a plum square, the gold sun, the porch-light bowl."""
import pathlib
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
LOGO = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 86 104" width="{w}" height="{h}">'
        '<circle cx="43" cy="22" r="18" fill="#E9A92A"/>'
        '<path d="M8 52 C8 86 26 98 43 98 C60 98 78 86 78 52" fill="none" stroke="#FFF9F1" stroke-width="8" stroke-linecap="round"/>'
        '<path d="M2 52 H84" stroke="#FFF9F1" stroke-width="8" stroke-linecap="round"/></svg>')


def page(size, share):
    h = round(size * share); w = round(h * 86 / 104)
    return ('<!doctype html><html><body style="margin:0;width:%dpx;height:%dpx;background:#4B2A6B;display:flex;'
            'align-items:center;justify-content:center">%s</body></html>') % (size, size, LOGO.format(w=w, h=h))


with sync_playwright() as p:
    b = p.chromium.launch()
    for name, size, share in (('icon-192.png', 192, .62), ('icon-512.png', 512, .62), ('icon-maskable-512.png', 512, .5)):
        pg = b.new_page(viewport={'width': size, 'height': size})
        pg.set_content(page(size, share))
        pg.screenshot(path=str(ROOT / name), clip={'x': 0, 'y': 0, 'width': size, 'height': size})
        pg.close()
        print(name)
    b.close()
```

```css file=phone.css
/*PHONE*/
/* ---------- phone layout (narrower than 1024px): the laptop app folded up for a small screen ---------- */
.ph-only,.ph-faq{display:none}
@media screen and (max-width:1023.98px){  /* .98: no gap below 1024px at odd zoom levels */
  body{background:var(--lilac)}
  .kbd,.dk-keysec{display:none}
  .dk-link{border:none;background:none;padding:0;font:inherit;color:inherit;text-decoration:underline;text-underline-offset:3px;cursor:pointer}
  .dk-link.muted{color:var(--muted)}
  input[type=search],select{font-size:16px}  /* under 16px, iPhones zoom the page when a field gets focus */
  /* plum top bar: logo, precinct, Share (icon), Feedback & Info (icon); under the status bar on a Home Screen app */
  .dk-hdr{display:flex;align-items:center;gap:8px;height:calc(56px + env(safe-area-inset-top));padding:env(safe-area-inset-top) max(12px,env(safe-area-inset-right)) 0 max(14px,env(safe-area-inset-left));position:sticky;top:0;z-index:20;background:var(--plum)}
  .dk-brand{display:flex;align-items:center;gap:8px;flex-shrink:0}
  .dk-brand b{font-family:'Zilla Slab',Rockwell,Georgia,serif;font-size:21px;font-weight:600;color:var(--ground)}
  .dk-loc{font-size:0;color:var(--ground);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;padding-left:4px}  /* the precinct only: the street and "change" are in the menu */
  .dk-loc b{font-size:13px;font-weight:600}
  .dk-loc .dk-link,body:not(.dk-app-on) .dk-loc{display:none}
  .dk-sp{flex:1}
  .dk-when,.dk-menu{display:none !important}  /* the phone's menu is a sheet (#ph-menu) */
  .dk-btn{width:44px;height:44px;border-radius:10px;border:1px solid rgba(255,249,241,.45);background:transparent no-repeat center/22px;font-size:0;color:transparent;cursor:pointer;flex-shrink:0;padding:0}
  #dk-help{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23FFF9F1' stroke-width='2' stroke-linecap='round'%3E%3Cpath d='M4 7h16M4 12h16M4 17h16'/%3E%3C/svg%3E")}
  #dk-share{background-color:var(--ground);border-color:var(--ground);background-size:20px;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%234B2A6B' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M12 15V3'/%3E%3Cpath d='M7 8l5-5 5 5'/%3E%3Cpath d='M5 13v6a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-6'/%3E%3C/svg%3E")}
  .dk-btn:focus-visible{box-shadow:0 0 0 2px var(--plum),0 0 0 4px var(--ground);outline:none}
  /* landing: the laptop's plum band, compact; the form's paper overlaps its foot */
  body:not(.dk-app-on) .dk-hero{display:flex}
  .dk-hero{flex-direction:column;align-items:flex-start;gap:10px;background:var(--plum);padding:0 max(20px,env(safe-area-inset-right)) 84px max(20px,env(safe-area-inset-left))}
  .dk-only{align-self:stretch;margin:0 -20px 8px;padding:8px 20px;background:var(--gold);color:var(--ink);font-size:14px;font-weight:600}
  .dk-logo{display:none}  /* the bar above carries the logo */
  .dk-tagline{font-family:'Zilla Slab',Rockwell,Georgia,serif;font-size:31px;font-weight:700;line-height:1.08;color:var(--ground)}
  .dk-sub{font-size:15px;color:var(--lilac)}
  body:not(.dk-app-on) .wrap{margin-top:-64px;padding-top:0;max-width:560px;padding-left:max(16px,env(safe-area-inset-left));padding-right:max(16px,env(safe-area-inset-right))}
  .wrap > .brand{display:none}
  body:not(.dk-app-on) .wrap > section.card,body:not(.dk-app-on) .wrap > footer,body:not(.dk-app-on) #result,body.dk-app-on .wrap{display:none !important}
  #start,body.dk-friend #friend{background:#fff;border-radius:4px;box-shadow:0 1px 0 var(--line2),0 12px 32px rgba(36,26,46,.08);padding:22px 18px;gap:16px}
  #start h1{font-size:32px}
  #lookup{border:none;padding:0;background:transparent}
  body.dk-has .dk-back{display:inline-flex;align-self:flex-start;min-height:44px;padding:0}
  .dk-steps{display:flex;flex-direction:column;gap:14px;padding:8px 6px 0}
  .dk-steps .lead{font-size:15px}
  body:not(.dk-app-on) .ph-faq{display:flex}
  .ph-faq{flex-direction:column;gap:8px;padding-top:12px}
  .ph-faq h2{font-size:26px;padding:0 6px 4px}
  .ph-faq details{background:#fff;border-radius:12px;box-shadow:0 1px 0 var(--line2)}
  .ph-faq summary{list-style:none;display:flex;justify-content:space-between;align-items:center;gap:12px;min-height:52px;padding:10px 16px;cursor:pointer}
  .ph-faq summary::-webkit-details-marker{display:none}
  .ph-faq summary::after{content:'';width:9px;height:9px;border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);transform:rotate(45deg);margin-top:-4px;flex-shrink:0;transition:transform .15s}
  .ph-faq details[open] summary::after{transform:rotate(225deg);margin-top:4px}
  .ph-faq h3{text-transform:none;letter-spacing:0;font-size:16px;color:var(--ink);font-weight:700}
  .ph-faq p{padding:0 16px 14px;font-size:15px;color:var(--ink2)}
  /* a friend's link, no ballot yet: their picks on a paper, then the form (as on a laptop) */
  body.dk-friend #start > div:has(> h1){display:none !important}
  body.dk-friend .dk-fcta{display:flex;flex-direction:column;gap:10px}
  body.dk-friend .dk-steps,body.dk-friend #f-own,body.dk-friend #f-cmp{display:none}
  .dk-fcta,.dk-fchip,.dk-fbox,.dk-fp{overflow-wrap:anywhere;min-width:0}  /* #23 */
  /* Home Screen app, no ballot yet: bring picks over from Safari */
  .ph-paste.ph-show{display:flex;flex-direction:column;gap:10px;padding:14px 16px;border-radius:12px;background:var(--lilac);color:var(--plum)}
  .ph-paste p{font-size:15px}
  /* the app: paper on lilac, a plum bar at the bottom */
  body.dk-app-on .dk-app{display:block}
  .dk-rail{display:none}
  .dk-desk{display:flex;flex-direction:column;max-width:640px;margin:0 auto;padding:10px max(8px,env(safe-area-inset-right)) calc(100px + env(safe-area-inset-bottom)) max(8px,env(safe-area-inset-left))}
  .dk-paper{background:#fff;border-radius:4px;box-shadow:0 1px 0 var(--line2),0 12px 32px rgba(36,26,46,.08);padding:22px 18px;display:flex;flex-direction:column;gap:16px;min-width:0;outline:none}
  .dk-paper h1{font-size:30px}
  .dk-paper h1:focus{outline:none}  /* focused only to tell a screen reader where a move landed */
  .dk-say{display:flex;gap:12px;align-items:center;justify-content:space-between;margin-bottom:10px;padding:12px 14px;border-radius:10px;background:var(--warnsoft);color:var(--warn);font-size:14px;font-weight:600}
  .dk-say button{min-height:44px;flex-shrink:0}
  .dk-top{display:flex;justify-content:space-between;align-items:baseline;gap:4px 10px;flex-wrap:wrap}
  .dk-meta{font-size:14px;font-weight:600;color:var(--ink2);margin-top:-8px}
  .dk-lines{display:flex;flex-direction:column}
  .dk-lw{border-top:1px solid var(--divider);padding:2px 0}
  .dk-lines .dk-lw:first-child{border-top:2px solid var(--ink)}
  .dk-lw:has(.dk-line[aria-pressed=true]){background:linear-gradient(90deg,var(--warnsoft),#fff 70%);margin:0 -10px;padding:2px 10px;border-radius:6px}
  .dk-line{display:flex;align-items:center;gap:14px;width:100%;min-height:52px;padding:8px 0;border:none;background:transparent;font:inherit;color:var(--ink);text-align:left;cursor:pointer}
  .dk-oval{width:30px;height:20px;border-radius:50%;border:2px solid var(--lc);flex-shrink:0}
  .dk-line[aria-pressed=true] .dk-oval{border:none;background:var(--ink)}
  .dk-nm{flex:1;font-size:18px;font-weight:600;line-height:1.25;overflow-wrap:anywhere}
  .dk-nm small{display:block;font-size:13px;font-weight:400;color:var(--muted)}
  .dk-paper .links{padding:0 0 10px 44px;margin:-6px 0 0}
  .dk-fp{display:flex;gap:8px;align-items:center;padding:0 0 10px 44px;font-size:13px;color:var(--plum)}
  .dk-two{display:flex;flex-direction:column;gap:12px}
  .dk-why{display:flex;flex-direction:column;gap:10px;background:var(--ground);border:1px solid var(--line);border-radius:12px;padding:12px 14px 14px}
  .dk-why label{display:flex;gap:2px 8px;align-items:baseline;flex-wrap:wrap;font-size:15px;font-weight:600}
  .dk-why label span:not(.kbd){flex:1;color:var(--muted);font-weight:400;font-size:13px}
  .dk-why textarea{background:#fff;border:1px solid var(--lc);border-radius:10px;font-family:Georgia,'Times New Roman',serif;font-size:17px;padding:10px 12px;min-height:64px;resize:none;overflow:hidden}
  .dk-prompts{display:flex;gap:6px;flex-wrap:wrap}
  .dk-prompts button{min-height:44px;padding:4px 12px;border-radius:999px;background:#fff;border:1px solid var(--line);font:inherit;font-size:13px;color:var(--ink2);cursor:pointer}
  .dk-nav{display:none}  /* the bottom bar and the Previous / Next row below do this on a phone */
  .dk-fchip{align-self:flex-start;display:inline-flex;gap:8px;align-items:center;flex-wrap:wrap;padding:4px 12px 4px 4px;border-radius:999px;background:var(--lilac);color:var(--plum);font-size:13px;font-weight:600}
  .dk-fchip .dk-link{min-height:44px}
  .dk-fa{width:18px;height:18px;border-radius:50%;background:var(--gold);color:var(--ink);font-size:10px;font-weight:800;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0}
  /* Decide: the paper, its "Learn more" fold and a Previous / Next row read as one sheet */
  body.ph-decide .dk-paper{border-radius:4px 4px 0 0;box-shadow:none;padding-bottom:12px}
  body.ph-decide .ph-fold{display:flex}
  .ph-fold{justify-content:space-between;align-items:center;gap:12px;width:100%;min-height:52px;padding:0 18px;background:#fff;border:none;border-top:1px solid var(--line);font:inherit;font-size:15px;font-weight:600;color:var(--ink);text-align:left;cursor:pointer}
  .ph-fold::after{content:'';width:9px;height:9px;border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);transform:rotate(45deg);margin-top:-4px;flex-shrink:0}
  .ph-fold[aria-expanded=true]::after{transform:rotate(225deg);margin-top:4px}
  .dk-notes{display:flex;flex-direction:column;gap:18px;min-width:0}
  .dk-notes:empty{display:none}
  body.ph-decide .dk-notes{background:#fff;padding:2px 18px 16px}
  body.ph-decide .dk-notes:not(.ph-open){display:none}
  body:not(.ph-decide) .dk-notes{background:#fff;border-radius:4px;margin-top:10px;padding:18px}
  .dk-notes h3{margin-bottom:6px;font-size:11px;letter-spacing:.09em}
  .dk-notes section > p{font-size:14px;color:var(--ink2)}
  .dk-notes .lnk{border-top:none;border-bottom:1px dotted var(--lc);min-height:44px}
  .dk-fbox{background:var(--lilac);border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:8px}
  .dk-kv{display:grid;grid-template-columns:repeat(3,1fr);text-align:center;gap:6px}
  .dk-kv b{display:block;font-family:'Zilla Slab',Rockwell,Georgia,serif;font-size:26px;line-height:1.1}
  .dk-kv span{font-size:12px;color:var(--muted)}
  body.ph-decide .ph-step{display:flex}
  .ph-step{justify-content:space-between;background:#fff;border-top:1px solid var(--divider);border-radius:0 0 4px 4px;box-shadow:0 12px 32px rgba(36,26,46,.08);padding:2px 8px}
  .ph-step button{min-height:48px;padding:0 10px;border:none;background:none;font:inherit;font-size:15px;font-weight:600;color:var(--ink);text-decoration:underline;text-underline-offset:3px;cursor:pointer}
  .ph-step button:disabled{color:var(--lc);text-decoration:none;cursor:default}
  /* At a glance: one contest per row, the pick under its name */
  .dk-gh{display:flex;flex-direction:column;gap:10px}
  .dk-gh h1{font-size:30px}
  .dk-tog{display:inline-flex;gap:8px;align-items:center;min-height:44px;font-size:15px;font-weight:600}
  .dk-tbl,.dk-tbl tbody,.dk-tbl tr,.dk-tbl th,.dk-tbl td{display:block;text-align:left}
  .dk-tbl thead,.dk-tbl td:nth-child(4){display:none}  /* Learn more lives in Decide on a phone */
  .dk-tbl tr[data-tr]{padding:12px 0;border-bottom:1px solid var(--divider)}
  .dk-tbl tbody th,.dk-tbl td{padding:0;font-weight:400}
  .dk-tbl tbody th{margin-bottom:6px}
  .dk-tbl tbody th .dk-link{font-weight:600;text-decoration:none;text-align:left;font-size:16px}
  .dk-tbl small{display:block;font-size:12px;color:var(--muted)}
  .dk-tbl small.dk-chk{color:var(--warn)}
  .dk-tbl tr.dk-tg th{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding:16px 0 0}
  .dk-tbl td:nth-child(3){margin-top:6px;font-size:14px}
  .dk-tbl td:nth-child(3) .dk-link{display:inline-flex;align-items:center;min-height:44px}
  .dk-sel{width:100%;height:44px;padding:0 8px;border:1px solid var(--lc);border-radius:8px;background:#fff;font:inherit;font-size:16px;color:var(--ink)}
  .dk-wt{color:var(--ink2);font-style:italic}
  /* Where to vote: the list, then the map behind a fold */
  .dk-vote,.dk-vote > div{display:flex;flex-direction:column;gap:12px;min-width:0}
  .dk-vote{gap:18px}
  .dk-vote .seg button{min-height:44px;padding:4px 8px;line-height:1.25;text-wrap:balance}  /* "Early voting · / Oct 19–30", not "…Oct 19– / 30" */
  .dk-sites{list-style:none;margin:0;padding:0}
  .dk-site{display:flex;gap:12px;padding:11px 0;border-top:1px solid var(--divider)}
  .dk-site .site{flex:1;border:none;padding:0}
  .dk-site .chips a{display:inline-block;padding:6px 0}
  #dk-all{min-height:44px}
  .dk-num{width:24px;height:24px;border-radius:50%;background:var(--plum);color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}
  .dk-num.blank{background:transparent}
  .ph-mapfold{border-top:1px solid var(--line)}
  .ph-mapfold summary{list-style:none;display:flex;justify-content:space-between;align-items:center;min-height:52px;font-weight:600;cursor:pointer}
  .ph-mapfold summary::-webkit-details-marker{display:none}
  .ph-mapfold summary::after{content:'';width:9px;height:9px;border-right:2px solid var(--muted);border-bottom:2px solid var(--muted);transform:rotate(45deg);margin-top:-4px}
  .ph-mapfold[open] summary::after{transform:rotate(225deg);margin-top:4px}
  .dk-map{width:100%;height:auto;background:var(--ground);border-radius:8px;display:block}
  .dk-map line{stroke:var(--divider)}
  .dk-map text{font:13px 'Public Sans',system-ui,sans-serif;fill:var(--muted);text-anchor:middle}
  .dk-map circle{fill:var(--lc);stroke:#fff;stroke-width:1.5}
  .dk-map circle.late{fill:var(--gold)}
  .dk-map .top circle{fill:var(--plum)}
  .dk-map .top text{fill:#fff;font-weight:700}
  /* Crib sheet: the printout's look, then its options and the Print button */
  .dk-page{background:#fff;border:1px solid var(--line2);box-shadow:0 2px 12px rgba(36,26,46,.12);padding:18px 16px}
  .dk-page.two{column-count:2;column-gap:16px}
  .dk-page .ch{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid #000;padding-bottom:8px;margin-bottom:4px;column-span:all}
  .dk-page .ln{display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px solid #DDD;font-size:12px;break-inside:avoid}
  .dk-page .ln span:last-child{font-weight:800;text-align:right}
  .dk-page .why{font-size:11px;color:#333;padding:0 0 4px}
  .dk-page .grp{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;margin-top:10px;break-after:avoid}
  /* the backup card floats above the bottom bar (#48) */
  .dk-nudge{position:fixed;left:max(12px,env(safe-area-inset-left));right:max(12px,env(safe-area-inset-right));bottom:calc(84px + env(safe-area-inset-bottom));z-index:40;max-width:496px;margin:0 auto;display:flex;flex-direction:column;align-items:flex-start;gap:10px;padding:14px 16px;border-radius:12px;background:#fff;color:var(--plum);font-size:15px;font-weight:600;box-shadow:0 12px 32px rgba(36,26,46,.28)}
  .dk-nudge .row{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
  .dk-nudge .dk-link{min-height:44px}
  .ph-home.ph-show{display:block;text-align:left;font-size:14px;font-weight:600}
  html.nudging body{padding-bottom:0}
  html.nudging .dk-desk{padding-bottom:calc(290px + env(safe-area-inset-bottom))}
  html.nudging{scroll-padding-bottom:calc(290px + env(safe-area-inset-bottom))}
  html{scroll-padding-bottom:calc(84px + env(safe-area-inset-bottom))}
  /* the bottom bar: your ballot (the list) and the next undecided contest */
  body.dk-app-on:not(.ph-list) .ph-bar{display:flex}
  .ph-bar{position:fixed;left:0;right:0;bottom:0;z-index:30;align-items:center;gap:10px;min-height:72px;padding:10px max(12px,env(safe-area-inset-right)) calc(10px + env(safe-area-inset-bottom)) max(12px,env(safe-area-inset-left));background:var(--plum)}
  .ph-bar button{font:inherit;cursor:pointer;border:none}
  #ph-list{flex:1;min-width:0;display:flex;align-items:center;gap:10px;min-height:48px;padding:0 4px;background:transparent;color:#fff;text-align:left;border-radius:10px}
  #ph-list b{display:block;font-size:15px;font-weight:600}
  #ph-list small{display:block;font-size:13px;color:rgba(255,249,241,.8)}
  #ph-list svg{flex-shrink:0}
  #ph-next{min-height:48px;padding:0 16px;border-radius:12px;background:var(--ground);color:var(--plum);font-weight:700;font-size:15px;white-space:nowrap}
  .ph-bar button:focus-visible{box-shadow:0 0 0 2px var(--plum),0 0 0 4px var(--ground);outline:none}
  /* "Your ballot": the laptop's plum rail, full screen */
  body.ph-list{overflow:hidden}
  body.ph-list .dk-rail{display:flex}
  .dk-rail{position:fixed;inset:0;z-index:60;flex-direction:column;min-height:0;background:var(--plum);color:var(--ground);padding:env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left)}
  .dk-rhd{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:6px 12px;padding:12px 16px}
  .dk-rhd h2{font-size:26px;color:#fff}
  .dk-rhd > span{grid-column:1/-1}
  #dk-count{font-size:14px;color:rgba(255,249,241,.85)}
  .ph-done{display:block;grid-column:2;grid-row:1;min-height:44px;padding:0 16px;border-radius:10px;border:none;background:var(--ground);color:var(--plum);font:inherit;font-weight:700;cursor:pointer}
  .dk-rbar{display:block;height:6px;border-radius:999px;background:rgba(255,249,241,.18);overflow:hidden}
  .dk-rbar i{display:block;height:6px;background:var(--gold);width:0}
  .dk-views{display:grid;grid-template-columns:1fr 1fr;gap:4px;padding:4px 10px 10px;border-bottom:1px solid rgba(255,249,241,.14)}
  .dk-views button{display:flex;align-items:center;gap:10px;min-height:44px;padding:0 10px;border-radius:8px;border:none;background:transparent;color:rgba(255,249,241,.85);font:inherit;font-size:15px;font-weight:600;cursor:pointer;text-align:left}
  .dk-views button[aria-current=page]{background:rgba(255,249,241,.14);color:#fff}
  .dk-search{margin:10px 14px 6px;height:44px;border-radius:8px;background:rgba(255,249,241,.10);display:flex;align-items:center;gap:8px;padding:0 10px}
  .dk-search input{flex:1;min-width:0;height:42px;border:none;background:transparent;color:#fff;font:inherit;font-size:16px;padding:0}
  .dk-search input::placeholder{color:#CBB6DE}
  .dk-filt{display:flex;gap:6px;padding:4px 14px 10px;flex-wrap:wrap}
  .dk-filt button{min-height:44px;padding:0 12px;border-radius:8px;border:none;background:transparent;color:#fff;font:inherit;font-size:13px;font-weight:600;box-shadow:inset 0 0 0 1px rgba(255,249,241,.35);cursor:pointer;white-space:nowrap}
  .dk-filt button[aria-pressed=true]{background:var(--ground);color:var(--plum);box-shadow:none}
  .dk-out{flex:1;overflow:auto;overscroll-behavior:contain;padding-bottom:8px}
  .dk-g{display:flex;justify-content:space-between;padding:12px 16px 3px;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,249,241,.65)}
  .dk-row{display:flex;align-items:center;gap:10px;width:100%;min-height:48px;padding:6px 16px;border:none;background:transparent;color:inherit;font:inherit;text-align:left;cursor:pointer}
  .dk-row[aria-current=true]{background:rgba(255,249,241,.14);box-shadow:inset 3px 0 0 var(--gold)}
  .dk-d{width:9px;height:9px;border-radius:50%;box-shadow:inset 0 0 0 2px rgba(255,249,241,.55);flex-shrink:0}
  .dk-d.on{background:var(--gold);box-shadow:none}
  .dk-rt{min-width:0;flex:1;display:flex;flex-direction:column}
  .dk-rt b{font-size:14px;font-weight:600;line-height:1.3;color:#fff;overflow-wrap:anywhere}
  .dk-rt small{font-size:13px;color:rgba(255,249,241,.75);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .dk-rail .dk-fa.diff{background:transparent;color:var(--ground);box-shadow:inset 0 0 0 2px var(--gold)}
  .dk-empty{padding:12px 16px;font-size:14px;color:rgba(255,249,241,.8)}
  .dk-foot{padding:10px 14px;border-top:1px solid rgba(255,249,241,.14);display:flex;gap:8px}
  .dk-foot button{flex:1;min-height:44px;border-radius:8px;border:none;background:transparent;color:#fff;font:inherit;font-size:14px;font-weight:600;box-shadow:inset 0 0 0 1px rgba(255,249,241,.35);cursor:pointer}
  .dk-rail button:focus-visible,.dk-rail input:focus-visible{box-shadow:0 0 0 2px var(--plum),0 0 0 4px var(--ground);outline:none}
  /* sheets: room for the home indicator */
  dialog.sheet{padding-bottom:calc(30px + env(safe-area-inset-bottom))}
  .ph-menu{display:flex;flex-direction:column;margin:0 -10px}
  .ph-menu button{display:flex;flex-direction:column;align-items:flex-start;gap:1px;min-height:52px;justify-content:center;text-align:left;padding:8px 10px;border:none;border-radius:8px;background:transparent;font:inherit;color:var(--ink);cursor:pointer}
  .ph-menu b{font-size:16px;font-weight:600}
  .ph-menu small{font-size:13px;color:var(--muted)}
  .ph-menu .bad b{color:var(--bad)}
  .ph-menu hr{border:none;border-top:1px solid var(--divider);margin:4px 10px;width:auto;align-self:stretch}
  .ph-steps{margin:0;padding-left:22px;display:flex;flex-direction:column;gap:14px;font-size:15px}
  .ph-steps li{padding-left:4px}
  .ph-steps .btn{margin-top:8px}
  .dk-info{display:flex;flex-direction:column;gap:22px}
  .dk-info section{display:flex;flex-direction:column;gap:10px}
}
/*/PHONE*/
```

```js file=phone.js
/*PHONE*/
/* ---------- phone layout (narrower than 1024px) ----------
   The phone shows the laptop's app folded up: the plum rail becomes the "Your ballot" sheet, the notes column a fold
   under the paper, and a bottom bar carries the list and "Next undecided". Moves and picks go through the laptop
   code (desk.ph) and pick(), so the two widths never disagree. Also here: Add to Home Screen, the offline copy, and
   bringing picks into a Home Screen app (an iPhone gives it its own storage, apart from Safari's). */
const phone = (() => {
  const NARROW = window.matchMedia('(max-width: 1023.98px)'), D = desk.ph, cls = document.body.classList;
  const standalone = () => matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  const iOS = () => /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  let foldOpen = false, lastKey = '', booting = true, listFrom = null, bip = null;
  setTimeout(() => { booting = false; });  // a ballot already saved on this phone opens where the browser left the page

  /* ----- after every laptop render: the bar, the fold, the Previous / Next row, the map fold ----- */
  function bar() {
    if (!ballot.length) return;
    const n = ballot.length, done = ballot.filter(b => D.decided(b.c.id)).length, nx = D.nextUndecided(D.ui.cur);
    $('ph-count').textContent = done + ' of ' + n + ' decided';
    $('ph-next').textContent = nx ? 'Next undecided →' : 'Crib sheet →';
    $('ph-next').classList.toggle('hidden', !nx && D.ui.view === 'crib');
  }
  function after() {
    const app = cls.contains('dk-app-on'), dec = app && D.ui.view === 'decide';
    cls.toggle('ph-decide', dec);
    bar();
    if (dec) {
      const c = D.curB().c, L = DATA.learn[c.id] || {}, i = D.idx(c.id);
      const what = c.type === 'measure' ? 'Sources' : L.office ? 'About this office · Learn more' : 'Learn more';
      $('ph-fold').textContent = (friend ? 'You and ' + friendName() + ' · ' : '') + what;
      $('ph-fold').setAttribute('aria-expanded', foldOpen ? 'true' : 'false');
      $('dk-notes').classList.toggle('ph-open', foldOpen);
      $('ph-prev').disabled = i <= 0; $('ph-step-next').disabled = i >= ballot.length - 1;
    }
    // A new contest or view, however it came (the bar, the list, a name in At a glance, a new ballot): start at its top.
    const key = app ? D.ui.view + ':' + D.ui.cur : '';
    if (key && key !== lastKey && NARROW.matches && !booting) moved();
    lastKey = key;
    $('ph-paste').classList.toggle('ph-show', NARROW.matches && standalone() && iOS() && !ballot.length);  // Android's app shares the browser's storage
  }
  // A move on a phone lands at the top of the paper, and a screen reader hears the new contest's heading.
  function moved() {
    window.scrollTo(0, 0);
    const h = $('dk-paper').querySelector('h1');
    if (h) { h.tabIndex = -1; h.focus({ preventScroll: true }); }
  }
  function next() {
    const nx = D.nextUndecided(D.ui.cur);
    if (nx) D.go(nx.c.id);
    else { D.setView('crib'); track('view_opened', { view: 'crib' }); }
  }

  /* ----- "Your ballot": the rail as a full-screen sheet ----- */
  const behind = () => ['dk-hdr', 'dk-desk', 'ph-bar'].map($);
  function openList() {
    listFrom = document.activeElement;
    cls.add('ph-list'); $('ph-list').setAttribute('aria-expanded', 'true');
    behind().forEach(e => { e.inert = true; });
    const row = $('dk-out').querySelector('[aria-current="true"]');
    if (row) { row.scrollIntoView({ block: 'center' }); row.focus({ preventScroll: true }); } else $('ph-done').focus();
  }
  function closeList(then) {
    if (!cls.contains('ph-list')) return;
    cls.remove('ph-list'); $('ph-list').setAttribute('aria-expanded', 'false');
    behind().forEach(e => { e.inert = false; });
    if (then === 'paper') moved();  // the move itself happened while the page behind was out of reach
    else if (then === 'print') { const pr = $('dk-notes').querySelector('[data-act="print"]'); if (pr) { pr.scrollIntoView({ block: 'center' }); pr.focus({ preventScroll: true }); } }
    else (listFrom && listFrom.isConnected && listFrom.getClientRects().length ? listFrom : $('ph-list')).focus({ preventScroll: true });
  }
  $('ph-list').addEventListener('click', openList);
  $('ph-done').addEventListener('click', () => closeList());
  $('ph-next').addEventListener('click', next);
  // The laptop's own listeners run first (they move, or change the view); then the sheet gets out of the way.
  $('dk-out').addEventListener('click', (e) => { if (NARROW.matches && e.target.closest('.dk-row')) closeList('paper'); });
  $('dk-views').addEventListener('click', (e) => { if (NARROW.matches && e.target.closest('button')) closeList('paper'); });
  $('dk-print').addEventListener('click', () => { if (NARROW.matches) closeList('print'); });
  document.querySelector('.dk-rail').addEventListener('keydown', (e) => { if (e.key === 'Escape' && cls.contains('ph-list') && e.target.id !== 'dk-q') { e.preventDefault(); closeList(); } });
  $('ph-fold').addEventListener('click', () => { foldOpen = !foldOpen; after(); });
  $('ph-prev').addEventListener('click', () => D.act('prev'));
  $('ph-step-next').addEventListener('click', () => { const i = D.idx(D.ui.cur); if (i < ballot.length - 1) D.go(ballot[i + 1].c.id); });
  new MutationObserver(bar).observe($('dk-count'), { childList: true });  // a pick changes the count: the bar follows
  // The map waits behind a fold on a phone, however the vote view was drawn (a view change, the period, "See all", a new day).
  function mapFold() {
    const map = $('dk-map');
    if (!NARROW.matches || !map || map.closest('details')) return;
    const box = map.parentNode, d = document.createElement('details');
    d.className = 'ph-mapfold'; d.innerHTML = '<summary>Map of vote centers</summary>';
    box.before(d); d.append(box);
  }
  new MutationObserver(mapFold).observe($('dk-paper'), { childList: true, subtree: true });

  /* ----- Feedback & Info as a sheet: the laptop menu's own items, plus Home Screen ones ----- */
  function menuItems() {
    const box = $('ph-mitems'); box.textContent = '';
    const item = (key, html, bad) => { const b = document.createElement('button'); b.type = 'button'; b.dataset.ph = key; b.innerHTML = html; if (bad) b.className = 'bad'; box.append(b); };
    [...$('dk-menu').children].forEach(el => {
      if (el.tagName === 'HR') { box.append(document.createElement('hr')); return; }
      item(el.dataset.help, el.innerHTML, el.classList.contains('bad'));
      if (el.dataset.help !== 'address') return;
      if (standalone() && iOS()) item('paste', '<b>Paste my picks link</b><small>Bring picks from Safari or another device</small>');
      else if (!standalone()) item('home', '<b>Add to your Home Screen</b><small>Opens like an app, and keeps your picks longer</small>');
    });
  }
  menuItems();
  $('ph-mitems').addEventListener('click', (e) => {
    const b = e.target.closest('button'); if (!b) return;
    $('ph-menu').close();
    if (b.dataset.ph === 'home') install('menu');
    else if (b.dataset.ph === 'paste') paste();
    else $('dk-menu').querySelector('[data-help="' + b.dataset.ph + '"]').click();  // the laptop's handler: counts it, then acts
  });
  document.addEventListener('click', (e) => {  // before the laptop's listeners: on a phone the menu button opens the sheet
    if (!NARROW.matches || !e.target.closest || !e.target.closest('#dk-help')) return;
    e.stopPropagation(); e.preventDefault(); $('ph-menu').showModal();
  }, true);
  function helpButton() {
    const h = $('dk-help');
    if (NARROW.matches) { h.setAttribute('aria-haspopup', 'dialog'); h.removeAttribute('aria-expanded'); h.removeAttribute('aria-controls'); }
    else { h.setAttribute('aria-haspopup', 'menu'); h.setAttribute('aria-expanded', 'false'); h.setAttribute('aria-controls', 'dk-menu'); }
  }

  /* ----- the landing's questions, as folds (copied from the laptop's, so the words never drift apart) ----- */
  (function faq() {
    const box = $('ph-faq');
    box.innerHTML = '<h2 id="ph-faqh">' + $('dk-faqh').innerHTML + '</h2>';
    $('dk-faq').querySelectorAll('.dk-q').forEach(q => {
      const d = document.createElement('details'), s = document.createElement('summary');
      s.append(q.querySelector('h3').cloneNode(true)); d.append(s, q.querySelector('p').cloneNode(true)); box.append(d);
    });
    // Counted like the laptop's FAQ (faq_seen): once a visit, when a scroll brings it into view.
    if (!('IntersectionObserver' in window)) return;
    let seen = false;
    const arm = () => {
      if (cls.contains('dk-app-on') || !NARROW.matches) return;
      window.removeEventListener('scroll', arm);
      const io = new IntersectionObserver((es) => { if (!seen && es.some(x => x.isIntersecting)) { seen = true; track('faq_seen'); io.disconnect(); } }, { threshold: 0.25 });
      io.observe(box);
    };
    window.addEventListener('scroll', arm, { passive: true });
  })();

  /* ----- Add to Home Screen ----- */
  // Android: on a phone, our button shows the browser's own prompt (so Chrome's automatic banner waits for it); laptops are left alone.
  window.addEventListener('beforeinstallprompt', (e) => { if (!NARROW.matches) return; e.preventDefault(); bip = e; });
  window.addEventListener('appinstalled', () => { bip = null; track('home_screen', { action: 'added' }); });
  function install(from) {
    track('home_screen', { action: 'opened', from });
    const ios = !bip && iOS(), picked = countPicks(ballot.map(b => b.c.id)) > 0;
    $('ph-i-add').classList.toggle('hidden', !bip);
    $('ph-i-ios').classList.toggle('hidden', !ios);
    $('ph-i-carry').classList.toggle('hidden', !ios || !picked);
    $('ph-i-other').classList.toggle('hidden', !!bip || ios);
    $('ph-i-out').classList.add('hidden');
    if (ios && picked) prepKeep();  // packed now: Safari only lets the copy happen right after the tap
    $('ph-install').showModal();
  }
  $('ph-i-add').addEventListener('click', async () => {
    const ev = bip; if (!ev) return;
    bip = null; track('home_screen', { action: 'prompted' });
    try { await ev.prompt(); await ev.userChoice; } catch (e) {}
    $('ph-install').close();
  });
  $('ph-i-copy').addEventListener('click', async () => {
    const k = keepPrep || prepKeep(), via = await copyLink(k.url || await k.p, $('ph-i-out'), $('ph-i-copy'));
    if (via) { track('home_screen', { action: 'copied' }); track('keep_created', { via }); nudgeKept(); }
  });
  $('ph-home-nudge').addEventListener('click', () => { nudgeDone('home'); install('card'); });

  /* ----- a Home Screen app starts empty on an iPhone: paste a saved-picks link to bring them in ----- */
  function paste() { $('ph-p-in').value = ''; $('ph-p-msg').classList.add('hidden'); $('ph-paste-d').showModal(); }
  async function load(text) {
    const m = String(text || '').match(/#([ks][=2][A-Za-z0-9_-]+)/), say = (t) => { $('ph-p-msg').textContent = t; $('ph-p-msg').classList.remove('hidden'); };
    if (!m) return say('That doesn’t look like a Ballotta link. Copy the whole link, starting with https.');
    if (m[1][0] !== 'k') return say('That’s a link a friend shared. To bring your own picks, use the link from Keep my picks.');
    $('ph-paste-d').close();
    track('home_screen', { action: 'pasted' });
    SS.set('ballotta.incoming', m[1]);
    handleIncoming(m[1], true);  // the usual "Load your saved picks?" window, from here on
  }
  $('ph-paste-open').addEventListener('click', paste);
  $('ph-p-go').addEventListener('click', () => load($('ph-p-in').value));
  $('ph-p-clip').addEventListener('click', async () => {
    try { const t = await navigator.clipboard.readText(); if (/#[ks][=2]/.test(t)) $('ph-p-in').value = t; load(t); }  // never shows other clipboard text
    catch (e) { $('ph-p-in').focus(); }  // no clipboard access: paste into the box by hand
  });

  /* ----- width changes, and the first look ----- */
  function width() {
    helpButton();
    if (!NARROW.matches) { closeList(); if ($('ph-menu').open) $('ph-menu').close(); }
    after(); mapFold();
  }
  NARROW.addEventListener('change', width);
  width();
  try { if (NARROW.matches && 'serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {}); } catch (e) {}  // the offline copy, for phones (laptops unchanged)
  return {
    after,
    nudge(at) { $('ph-home-nudge').classList.toggle('ph-show', at === 25 && NARROW.matches && !standalone()); },
  };
})();
window.phone = phone;
/*/PHONE*/
```

```python file=edits_template_P.py
"""Phone round, edit P2: source/template-travis.html. Run from the repo root, with phone.css and phone.js next to this
script:  python3 <this file>
Every addition sits inside PHONE markers (whole-line blocks, or a pair inside one line), so stripping them gives back
today's template byte for byte (the live page can't change until Lane promotes)."""
import pathlib
ROOT, HERE = pathlib.Path.cwd(), pathlib.Path(__file__).resolve().parent
F = ROOT / 'source/template-travis.html'
s = F.read_text(encoding='utf-8')
CSS = (HERE / 'phone.css').read_text(encoding='utf-8')
JS = (HERE / 'phone.js').read_text(encoding='utf-8')
assert CSS.startswith('/*PHONE*/\n') and CSS.endswith('/*/PHONE*/\n') and JS.startswith('/*PHONE*/\n') and JS.endswith('/*/PHONE*/\n')

def rep(a, z):
    global s
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, z)

# --- head: Home Screen description, safe areas (the second viewport tag wins)
rep('<!--CSP-->\n', '''<!--CSP-->
<!--PHONE-->
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="manifest" href="manifest.webmanifest">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Ballotta">
<!--/PHONE-->
''')
# --- styles, after the laptop's
rep('/*/DESK*/\n</style>\n', '/*/DESK*/\n' + CSS + '</style>\n')

# --- markup
rep('<span class="dk-rbar"><i id="dk-bar"></i></span></div>\n',
    '<span class="dk-rbar"><i id="dk-bar"></i></span><!--PHONE--><button type="button" class="ph-done ph-only" id="ph-done">Done</button><!--/PHONE--></div>\n')
rep('<button class="dk-link" type="button" data-nudge="dismiss">Not now</button></span></div>\n',
    '<button class="dk-link" type="button" data-nudge="dismiss">Not now</button></span><!--PHONE--><button class="dk-link ph-home ph-only" type="button" id="ph-home-nudge">Or add Ballotta to your Home Screen: it keeps your picks longer</button><!--/PHONE--></div>\n')
rep('''    <article class="dk-paper" id="dk-paper" tabindex="-1" aria-label="Ballot paper"></article>
    <aside class="dk-notes" id="dk-notes" aria-label="Notes"></aside>
''', '''    <article class="dk-paper" id="dk-paper" tabindex="-1" aria-label="Ballot paper"></article>
<!--PHONE-->
    <button type="button" class="ph-fold ph-only" id="ph-fold" aria-expanded="false" aria-controls="dk-notes"></button>
<!--/PHONE-->
    <aside class="dk-notes" id="dk-notes" aria-label="Notes"></aside>
<!--PHONE-->
    <div class="ph-step ph-only" id="ph-step"><button type="button" id="ph-prev">← Previous</button><button type="button" id="ph-step-next">Next →</button></div>
<!--/PHONE-->
''')
rep('''  <p class="dk-sub">See exactly what’s on your Travis County ballot for Nov 3, learn about the races from neutral sources, make your picks at your own pace, and share them with friends.</p>
</section>
''', '''  <p class="dk-sub">See exactly what’s on your Travis County ballot for Nov 3, learn about the races from neutral sources, make your picks at your own pace, and share them with friends.</p>
</section>
<!--PHONE-->
<nav class="ph-bar ph-only" id="ph-bar" aria-label="Your ballot">
  <button type="button" id="ph-list" aria-expanded="false"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFF9F1" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg><span><b>Your ballot</b><small id="ph-count"></small></span></button>
  <button type="button" id="ph-next"></button>
</nav>
<!--/PHONE-->
''')
rep('''  <section class="card" id="lookup" aria-labelledby="lk">
''', '''<!--PHONE-->
  <div class="ph-paste ph-only" id="ph-paste"><p><b>Made picks in Safari?</b> This Home Screen app keeps its own copy, so bring them over with the link from Keep my picks.</p><button class="btn secondary" type="button" id="ph-paste-open">Paste my picks link</button></div>
<!--/PHONE-->
  <section class="card" id="lookup" aria-labelledby="lk">
''')
rep('''    </div>
  </section>
<!--/DESK-->

  <div id="result" class="hidden"''', '''    </div>
  </section>
<!--PHONE-->
  <section class="ph-faq" id="ph-faq" aria-labelledby="ph-faqh"></section>
<!--/PHONE-->
<!--/DESK-->

  <div id="result" class="hidden"''')
rep('''  <div class="dk-info" id="dk-info"></div>
</dialog>
<!--/DESK-->
''', '''  <div class="dk-info" id="dk-info"></div>
</dialog>
<!--/DESK-->
<!--PHONE-->

<dialog class="sheet" id="ph-menu" aria-labelledby="ph-mh">
  <div class="handle" aria-hidden="true"></div>
  <div class="sheethead"><h2 id="ph-mh" style="font-size:26px">Feedback &amp; Info</h2><button type="button" class="x" data-close>Close</button></div>
  <div class="ph-menu" id="ph-mitems"></div>
</dialog>

<dialog class="sheet" id="ph-install" aria-labelledby="ph-ih">
  <div class="handle" aria-hidden="true"></div>
  <div class="sheethead"><h2 id="ph-ih" style="font-size:26px">Add Ballotta to your Home Screen</h2><button type="button" class="x" data-close>Close</button></div>
  <p class="lead">It opens like an app, and your phone is less likely to clear your picks.</p>
  <button class="btn" type="button" id="ph-i-add">Add to Home Screen</button>
  <ol class="ph-steps" id="ph-i-ios">
    <li id="ph-i-carry"><b>Take your picks along.</b> On an iPhone, the Home Screen app keeps its own copy, and it starts empty. Copy a private link to your picks first.<br><button class="btn secondary small" type="button" id="ph-i-copy">Copy my picks link</button><span class="linkout hidden" id="ph-i-out" style="display:block"></span><span class="note" style="display:block;margin-top:6px">Anyone with this link can see your picks and reasons. Paste it only into your own Ballotta.</span></li>
    <li>Tap the <b>Share</b> button (a square with an arrow), scroll down, and tap <b>Add to Home Screen</b>.</li>
    <li>Open Ballotta from your Home Screen. If you copied your picks, tap <b>Paste my picks link</b>.</li>
  </ol>
  <p id="ph-i-other">Open your browser’s menu and look for <b>Add to Home Screen</b> or <b>Install</b>.</p>
</dialog>

<dialog class="sheet" id="ph-paste-d" aria-labelledby="ph-ph">
  <div class="handle" aria-hidden="true"></div>
  <div class="sheethead"><h2 id="ph-ph" style="font-size:26px">Paste my picks link</h2><button type="button" class="x" data-close>Close</button></div>
  <p class="lead">The link from <b>Keep my picks</b> holds your picks and reasons. It stays on this phone.</p>
  <button class="btn" type="button" id="ph-p-clip">Paste from clipboard</button>
  <div class="field"><label for="ph-p-in">Or paste it here</label><input id="ph-p-in" type="text" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="https://ballotta.org/#k2…"></div>
  <button class="btn secondary" type="button" id="ph-p-go">Load my picks</button>
  <p class="status warn hidden" id="ph-p-msg" role="status"></p>
</dialog>
<!--/PHONE-->
''')

# --- counting: two new details, both listed (the firewall drops anything else)
rep('''  share_compare: {},
};
''', '''  share_compare: {},
};
/*PHONE*/
EVENTS.home_screen = { action: ONE_OF('opened', 'prompted', 'added', 'copied', 'pasted'), from: ONE_OF('menu', 'card') };
EVENTS.backup_nudge.action = ONE_OF('shown', 'keep', 'dismiss', 'home');
/*/PHONE*/
''')
rep("(k === 'layout' ? LAYOUT(String(v)) : has(spec, k)",
    "(k === 'layout' ? LAYOUT(String(v)) : /*PHONE*/k === 'app' ? v === 'yes' : /*/PHONE*/has(spec, k)")
rep("matchMedia('(min-width: 1024px)').matches ? 'laptop' : 'phone' }));",
    "matchMedia('(min-width: 1024px)').matches ? 'laptop' : 'phone' }/*PHONE*/, matchMedia('(display-mode: standalone)').matches || navigator.standalone === true ? { app: 'yes' } : {}/*/PHONE*/));")

# --- backup card: the Home Screen line at 25; focus home on a phone
rep("  nudgeAt = at; nudgeFrom = document.activeElement; nudgeBoxes(true);\n",
    "  nudgeAt = at; nudgeFrom = document.activeElement; nudgeBoxes(true);/*PHONE*/ if (window.phone) try { phone.nudge(at); } catch (e) {}/*/PHONE*/\n")
rep("  const home = was || (action === 'keep' || !wide ?",
    "  const home = was || /*PHONE*/(!wide && document.body.classList.contains('dk-app-on') ? $(action === 'keep' ? 'ph-list' : 'dk-paper') : null) || /*/PHONE*/(action === 'keep' || !wide ?")

# --- hooks in the laptop code
rep("    if (!ballot.length) return;\n    if (idx(ui.cur) < 0) ui.cur = ballot[0].c.id;\n",
    "    if (!ballot.length) /*PHONE*/{ if (window.phone) try { phone.after(); } catch (e) {}/*/PHONE*/return;/*PHONE*/ }/*/PHONE*/\n    if (idx(ui.cur) < 0) ui.cur = ballot[0].c.id;\n")
rep("    if (app && friend && WIDE.matches && ui.cmpFor !== friend) {",
    "    if (app && friend && /*PHONE*/(true || /*/PHONE*/WIDE.matches/*PHONE*/)/*/PHONE*/ && ui.cmpFor !== friend) {")
rep('''        if (!(k && list.includes(k))) { track('share_compare'); if (k) LS.set('ballotta.compared', list.concat(k).slice(-50)); }
      }
    }
  }
''', '''        if (!(k && list.includes(k))) { track('share_compare'); if (k) LS.set('ballotta.compared', list.concat(k).slice(-50)); }
      }
    }
    /*PHONE*/
    if (window.phone) try { phone.after(); } catch (e) {}
    /*/PHONE*/
  }
''')
rep("    if (!WIDE.matches && !printing && !matchMedia('print').matches && (ui.two || ui.hideCrib))",
    "    if (/*PHONE*/false && /*/PHONE*/!WIDE.matches && !printing && !matchMedia('print').matches && (ui.two || ui.hideCrib))")
rep("  return {\n    render,\n", "  return {\n    render,/*PHONE*/ ph: { ui, go, setView, act, nextUndecided, idx, curB, decided },/*/PHONE*/\n")
rep("window.desk = desk;\ndesk.render();\n/*/DESK*/\n", "window.desk = desk;\ndesk.render();\n/*/DESK*/\n" + JS)
F.write_text(s, encoding='utf-8')
print('template: phone layout added inside PHONE markers')
```

```python file=phone_tests.py
# ---------------------------------------------------------------- phone layout (preview build only until promotion)
import urllib.request
PHONE = {'width': 390, 'height': 844}                      # an iPhone 13/14/15's screen in CSS pixels

def phone_page(b, sent=None, csp=False, sw=False, size=None, init=None, ua=None):
    ctx, pg = new_page(b, sent, csp=csp, touch=True, size=size or PHONE, sw=sw, ua=ua)
    if init: pg.add_init_script(init)
    errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.__dict__['errs'] = errs
    return ctx, pg

def lookup_phone(pg):
    pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '78701'); pg.click('#go')
    pg.wait_for_selector('body.dk-app-on', timeout=30000)
    pg.wait_for_function("/ of \\d+ decided$/.test(document.getElementById('ph-count').textContent)", timeout=30000)

def h1(pg): return pg.inner_text('#dk-paper h1')
def focused(pg): return pg.evaluate("(() => { const a = document.activeElement; return a ? (a.id || a.tagName) : null; })()")
def sideways(pg): return pg.evaluate('document.scrollingElement.scrollWidth - document.scrollingElement.clientWidth')
def to_contest(pg, title):                                  # through the "Your ballot" sheet, as a voter would
    pg.click('#ph-list'); pg.fill('#dk-q', title); pg.locator('.dk-row', has_text=title).first.click()
    expect(pg.locator('.dk-rail')).to_be_hidden()

@phone_test
def phone_landing_band_form_and_faq(b):
    ctx, pg = phone_page(b); pg.goto(BASE)
    for sel in ('#dk-hdr', '#dk-hero', '#start', '#lookup', '.dk-steps', '#ph-faq', '#dk-help'):
        expect(pg.locator(sel)).to_be_visible()
    for sel in ('.wrap > .brand', '#dk-faq', '#ph-bar', '#dk-share', '.dk-logo', '#dk-loc', '#ph-paste'):
        expect(pg.locator(sel).first).to_be_hidden()
    assert pg.locator('.wrap > section.card:visible, .wrap > footer:visible').count() == 0, 'About and Feedback live in the menu'
    assert pg.text_content('.dk-tagline') == 'Don’t wait to meet your ballot in the booth.'
    assert css(pg, '#dk-hdr', 'backgroundColor') == PLUM and css(pg, '#dk-hero', 'backgroundColor') == PLUM
    hero, paper = box(pg, '#dk-hero'), box(pg, '#start')
    assert paper['y'] < hero['y'] + hero['height'] - 40, ('the paper overlaps the band', hero, paper)
    qs = pg.locator('#ph-faq details')
    assert qs.count() == pg.locator('#dk-faq .dk-q').count() == 6 and pg.locator('#ph-faq details[open]').count() == 0
    pg.mouse.wheel(0, 3000); pg.wait_for_function("(window.__events || []).some(e => e[0] === 'faq_seen')", timeout=5000)
    assert [e for e in events(pg) if e[0] == 'faq_seen'] == [['faq_seen', {'layout': 'phone'}]]
    qs.nth(3).locator('summary').click()
    assert pg.inner_text('#ph-faq details[open] p') == pg.locator('#dk-faq .dk-q p').nth(3).inner_text()   # the same words
    hb = box(pg, '#dk-help')
    assert hb['width'] >= 44 and hb['height'] >= 44 and pg.get_by_role('button', name='Feedback & Info').count() == 1
    assert sideways(pg) <= 0
    pg.set_viewport_size({'width': 320, 'height': 640}); pg.wait_for_timeout(100)
    assert sideways(pg) <= 0, 'nothing sideways on a 320px phone'
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def phone_lookup_opens_the_app_at_its_top(b):
    ctx, pg = phone_page(b); pg.goto(BASE); pg.evaluate('window.scrollTo(0, 400)'); lookup_phone(pg)
    expect(pg.locator('#ph-bar')).to_be_visible(); expect(pg.locator('.wrap')).to_be_hidden(); expect(pg.locator('.dk-rail')).to_be_hidden()
    assert pg.text_content('#ph-count') == '0 of 63 decided' and pg.text_content('#ph-next') == 'Next undecided →'
    assert h1(pg) == 'United States Senator' and focused(pg) == 'H1' and pg.evaluate('scrollY') == 0
    assert 'Precinct 300' in pg.inner_text('#dk-loc') and pg.is_visible('#dk-share')
    sb = box(pg, '#dk-share'); assert sb['width'] >= 44 and pg.get_by_role('button', name='Share my picks').count() == 1
    assert ['ballot_found', {'match': 'exact', 'layout': 'phone'}] in events(pg)
    paper, bar = box(pg, '#dk-paper'), box(pg, '#ph-bar')
    assert abs(bar['y'] + bar['height'] - PHONE['height']) < 1 and paper['x'] >= 8, (paper, bar)
    assert sideways(pg) <= 0 and pg.errs == [], pg.errs
    ctx.close()

PERSIST = ("window.__persist = 0; Object.defineProperty(navigator, 'storage', { configurable: true, value: {"
           " persisted: () => Promise.resolve(false), persist: () => { window.__persist++; return Promise.resolve(true); } } });")

@phone_test
def phone_pick_reason_fold_and_steps(b):
    ctx, pg = phone_page(b, init=PERSIST); pg.goto(BASE); lookup_phone(pg)
    to_contest(pg, 'District 9')
    assert h1(pg) == 'City Council Member, District 9' and focused(pg) == 'H1'
    pg.locator('.dk-line', has_text='Qadri').click()
    assert pg.locator('.dk-line', has_text='Qadri').get_attribute('aria-pressed') == 'true' and cur(pg, 'c070') == ['Zohaib “Zo” Qadri']
    pg.wait_for_function("document.getElementById('ph-count').textContent === '1 of 63 decided'")
    pg.fill('#dk-w', 'Knows the district')
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.whys')).c070") == 'Knows the district'
    assert pg.evaluate('window.__persist') == 1, 'the browser is asked to keep the picks at the first one (#49)'
    fold = pg.locator('#ph-fold')
    assert fold.inner_text() == 'About this office · Learn more' and fold.get_attribute('aria-expanded') == 'false'
    expect(pg.locator('#dk-notes')).to_be_hidden()
    fold.click()
    expect(pg.locator('#dk-notes')).to_be_visible(); assert 'One of 10 district council members' in pg.inner_text('#dk-notes')
    assert fold.get_attribute('aria-expanded') == 'true' and not pg.is_visible('.dk-keysec'), 'no keyboard shortcuts on a phone'
    pg.click('#ph-step-next')
    assert h1(pg) == 'Austin Proposition A' or h1(pg).endswith('Proposition A'), h1(pg)
    assert fold.inner_text() == 'Sources' and fold.get_attribute('aria-expanded') == 'true', 'the fold stays open from contest to contest'
    assert focused(pg) == 'H1'
    pg.click('#ph-prev'); assert h1(pg) == 'City Council Member, District 9'
    to_contest(pg, 'United States Senator')
    assert pg.is_disabled('#ph-prev') and not pg.is_disabled('#ph-step-next')
    expect(pg.locator('.dk-nav')).to_be_hidden()
    assert pg.errs == [], pg.errs
    ctx.close()

@phone_test
def phone_next_undecided_then_the_crib_sheet(b):
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
    assert h1(pg) == 'United States Senator' and pg.text_content('#ph-count') == '0 of 3 decided'
    assert focused(pg) == 'BODY', 'a ballot saved on this phone opens without moving focus'
    pg.locator('.dk-line', has_text='Ted Brown').click(); pg.click('#ph-next')
    assert h1(pg) == 'City Council Member, District 9' and focused(pg) == 'H1'
    pg.click('.skip'); pg.click('#ph-next'); assert h1(pg).endswith('Proposition A'), h1(pg)
    pg.locator('.dk-line', has_text='For').first.click()
    pg.wait_for_function("document.getElementById('ph-next').textContent === 'Crib sheet →'")
    pg.click('#ph-next')
    assert h1(pg) == 'Print your notes' and pg.is_hidden('#ph-next') and ['view_opened', {'view': 'crib', 'layout': 'phone'}] in events(pg)
    ctx.close()

@phone_test
def phone_ballot_list_sheet(b):
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); to_contest(pg, 'District 9')
    pg.click('#ph-list')
    rail = box(pg, '.dk-rail'); assert rail['x'] == 0 and rail['y'] == 0 and rail['width'] == PHONE['width'] and rail['height'] == PHONE['height'], rail
    assert pg.evaluate("['dk-hdr', 'dk-desk', 'ph-bar'].every(id => document.getElementById(id).inert)"), 'the page behind is out of reach'
    assert pg.evaluate("document.activeElement.getAttribute('aria-current')") == 'true' and 'District 9' in pg.evaluate('document.activeElement.textContent')
    assert pg.get_attribute('#ph-list', 'aria-expanded') == 'true'
    pg.keyboard.press('Escape'); expect(pg.locator('.dk-rail')).to_be_hidden(); assert focused(pg) == 'ph-list'
    assert not pg.evaluate("document.getElementById('dk-desk').inert")
    pg.click('#ph-list'); pg.click('#ph-done'); expect(pg.locator('.dk-rail')).to_be_hidden(); assert focused(pg) == 'ph-list'
    pg.click('#ph-list'); assert pg.input_value('#dk-q') == 'District 9' and pg.locator('.dk-row').count() == 1   # the search stays, as on a laptop
    pg.fill('#dk-q', ''); pg.click('#dk-filt [data-f="und"]'); expect(pg.locator('.dk-rail')).to_be_visible()
    assert pg.locator('.dk-row').count() == 63
    pg.click('#dk-keep'); pg.wait_for_selector('#d-keep[open]'); pg.click('#d-keep [data-close]'); expect(pg.locator('.dk-rail')).to_be_visible()
    pg.click('#dk-views [data-view="glance"]'); expect(pg.locator('.dk-rail')).to_be_hidden()
    assert h1(pg) == 'Your whole ballot' and focused(pg) == 'H1' and ['view_opened', {'view': 'glance', 'layout': 'phone'}] in events(pg)
    pg.click('#ph-list'); pg.click('#dk-print'); expect(pg.locator('.dk-rail')).to_be_hidden()
    assert h1(pg) == 'Print your notes' and pg.evaluate('document.activeElement.dataset.act') == 'print'
    ctx.close()

@phone_test
def phone_glance_vote_and_crib_fit_the_screen(b):
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg)
    pg.click('#ph-list'); pg.click('#dk-views [data-view="glance"]')
    assert css(pg, '[data-sel="c006"]', 'fontSize') == '16px' and css(pg, '#dk-q', 'fontSize') == '16px', 'iPhones zoom into smaller fields'
    pg.locator('[data-sel="c006"]').select_option(index=1); assert cur(pg, 'c006') == [pg.evaluate("optionsOf(BYID.c006)[0]")]
    pg.evaluate('window.scrollTo(0, 2000)'); pg.locator('[data-go="c070"]').first.click()
    assert h1(pg) == 'City Council Member, District 9' and pg.evaluate('scrollY') == 0 and focused(pg) == 'H1', 'a name in At a glance opens its contest at the top'
    pg.click('#ph-list'); pg.click('#dk-views [data-view="glance"]')
    expect(pg.locator('.dk-tbl thead')).to_be_hidden(); expect(pg.locator('.dk-tbl td:nth-child(4)').first).to_be_hidden()
    assert sideways(pg) <= 0
    pg.click('#ph-list'); pg.click('#dk-views [data-view="vote"]')
    assert pg.locator('.dk-site').count() == 5 and pg.locator('.ph-mapfold:not([open])').count() == 1
    expect(pg.locator('#dk-map')).to_be_hidden(); pg.click('.ph-mapfold summary'); expect(pg.locator('#dk-map')).to_be_visible()
    pg.click('[data-period="eday"]'); assert pg.locator('.ph-mapfold').count() == 1, 'redrawn: one fold, never two'
    assert sideways(pg) <= 0
    pg.click('#ph-list'); pg.click('#dk-views [data-view="crib"]')
    for t in ('#dk-cw', '#dk-c2', '#dk-cu'): expect(pg.locator(t)).to_be_visible()
    pg.click('#dk-c2'); pg.click('#dk-cu'); assert pg.get_attribute('#dk-page', 'class') == 'dk-page two'
    pg.evaluate("() => { window.print = () => { window.__printed = (window.__printed || 0) + 1; }; }")
    pg.click('#dk-notes [data-act="print"]')
    assert pg.evaluate('window.__printed') == 1 and events(pg)[-1] == ['crib_printed', {'two_col': 'yes', 'hide_unopposed': 'yes', 'layout': 'phone'}], events(pg)[-1]
    pg.emulate_media(media='print')                                                  # what the printer gets: the crib sheet alone
    assert pg.is_visible('#crib') and 'two' in pg.get_attribute('#crib', 'class') and not pg.is_visible('#dk-app') and not pg.is_visible('#ph-bar') and not pg.is_visible('#dk-hdr')
    pg.emulate_media(media='screen')
    pg.set_viewport_size({'width': 320, 'height': 640}); pg.wait_for_timeout(100); assert sideways(pg) <= 0
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(100); assert pg.is_checked('#dk-c2') and pg.is_checked('#dk-cu')
    pg.set_viewport_size(PHONE); pg.wait_for_timeout(100)
    assert pg.is_checked('#dk-c2') and pg.is_checked('#dk-cu') and 'two' in pg.get_attribute('#crib', 'class'), 'print options survive a narrower window: a phone shows them now'
    ctx.close()

@phone_test
def phone_menu_is_a_sheet(b):
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg)
    assert pg.get_attribute('#dk-help', 'aria-haspopup') == 'dialog' and pg.get_attribute('#dk-help', 'aria-controls') is None
    pg.click('#dk-help'); pg.wait_for_selector('#ph-menu[open]'); expect(pg.locator('#dk-menu')).to_be_hidden()
    got = pg.locator('#ph-mitems button b').all_inner_texts(); want = pg.locator('#dk-menu button b').all_text_contents()   # the laptop menu's own items
    assert got == want[:4] + ['Add to your Home Screen'] + want[4:] and pg.locator('#ph-mitems hr').count() == 1, (got, want)
    pg.locator('#ph-mitems button', has_text='How your privacy works').click()
    pg.wait_for_selector('#d-info[open]'); assert not pg.evaluate("document.getElementById('ph-menu').open")
    assert ['help_opened', {'item': 'privacy', 'layout': 'phone'}] in events(pg)
    pg.click('#d-info [data-close]')
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Change address').click()
    expect(pg.locator('#start')).to_be_visible(); expect(pg.locator('#dk-back')).to_be_visible(); expect(pg.locator('#ph-bar')).to_be_hidden()
    pg.click('#dk-back'); expect(pg.locator('#ph-bar')).to_be_visible()
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(100)
    assert pg.get_attribute('#dk-help', 'aria-haspopup') == 'menu'
    pg.click('#dk-help'); expect(pg.locator('#dk-menu')).to_be_visible(); assert not pg.evaluate("document.getElementById('ph-menu').open")
    ctx.close()

@phone_test
def phone_friend_link_landing_then_inline(b):
    o = {'v': 1, 'n': 'Maya', 'c': 'abcd1234', 'g': 1, 'p': {'70': 2, '71': 0}, 'w': {'70': 'Knows the district.'}}
    ctx, pg = phone_page(b); pg.goto(BASE); fresh_goto(pg, link('s', o))
    expect(pg.locator('#friend')).to_be_visible(); assert 'Maya shared 2 picks' in pg.inner_text('#friend')
    expect(pg.locator('#f-own')).to_be_hidden(); expect(pg.locator('#f-cmp')).to_be_hidden()
    expect(pg.locator('.dk-fcta')).to_be_visible(); assert 'See Maya’s picks beside yours' in pg.inner_text('.dk-fcta')
    assert box(pg, '#friend')['y'] < box(pg, '#start')['y'], 'their picks first, then the form'
    lookup_phone(pg); to_contest(pg, 'District 9')
    expect(pg.locator('.dk-fchip')).to_be_visible(); assert 'Maya picked this' in pg.inner_text('.dk-fp')
    assert pg.inner_text('#ph-fold').startswith('You and Maya · ')
    assert [e for e in events(pg) if e[0] == 'share_compare'] == [['share_compare', {'layout': 'phone'}]], events(pg)
    pg.click('#ph-next'); assert [e for e in events(pg) if e[0] == 'share_compare'] == [['share_compare', {'layout': 'phone'}]], 'once'
    pg.locator('.dk-fchip [data-act="hidefriend"]').click(); expect(pg.locator('.dk-fchip')).to_be_hidden()
    assert not pg.inner_text('#ph-fold').startswith('You and')
    ctx.close()

@phone_test
def phone_backup_card_sits_above_the_bar(b):
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, list(range(1, 41))); pg.wait_for_selector('body.dk-app-on')
    ids = pg.evaluate('ballot.filter(x => optionsOf(x.c).length).map(x => x.c.id)')
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[:5])
    card = pg.locator('#dk-nudge'); expect(card).to_be_visible(); expect(pg.locator('#ph-home-nudge')).to_be_hidden()
    c, bar = box(pg, '#dk-nudge'), box(pg, '#ph-bar'); assert c['y'] + c['height'] <= bar['y'], ('the card covers the bar', c, bar)
    card.locator('[data-nudge="dismiss"]').click(); expect(card).to_be_hidden()
    assert focused(pg) in ('dk-paper',) or pg.evaluate("document.activeElement.closest('#dk-paper') !== null"), focused(pg)
    pg.evaluate('ids => ids.forEach(id => pick(id, optionsOf(BYID[id])[0]))', ids[5:25])
    expect(card).to_be_visible(); expect(pg.locator('#ph-home-nudge')).to_be_visible()
    pg.click('#ph-home-nudge'); pg.wait_for_selector('#ph-install[open]'); expect(card).to_be_hidden()
    ev = events(pg)
    assert ['backup_nudge', {'at': '25', 'action': 'home', 'layout': 'phone'}] in ev and ['home_screen', {'action': 'opened', 'from': 'card', 'layout': 'phone'}] in ev, ev
    assert pg.evaluate('window.ballottaDropped') == []
    ctx.close()

IPHONE_UA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1'
FAKE_BIP = ("() => { const e = new Event('beforeinstallprompt', { cancelable: true }); e.prompt = () => { window.__prompted = (window.__prompted || 0) + 1; return Promise.resolve(); };"
            " e.userChoice = Promise.resolve({ outcome: 'accepted' }); window.dispatchEvent(e); }")

@phone_test
def phone_add_to_home_screen_three_ways(b):
    # Android (the browser's own prompt), iPhone (steps, and a copy of the picks to carry over), anything else (where to look).
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pg.evaluate(FAKE_BIP)
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click(); pg.wait_for_selector('#ph-install[open]')
    expect(pg.locator('#ph-i-add')).to_be_visible(); expect(pg.locator('#ph-i-ios')).to_be_hidden(); expect(pg.locator('#ph-i-other')).to_be_hidden()
    pg.click('#ph-i-add'); pg.wait_for_function("!document.getElementById('ph-install').open")
    pg.evaluate("window.dispatchEvent(new Event('appinstalled'))")
    assert pg.evaluate('window.__prompted') == 1
    hs = [e[1] for e in events(pg) if e[0] == 'home_screen']
    assert hs == [{'action': 'opened', 'from': 'menu', 'layout': 'phone'}, {'action': 'prompted', 'layout': 'phone'}, {'action': 'added', 'layout': 'phone'}], hs
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click()
    expect(pg.locator('#ph-i-other')).to_be_visible(); expect(pg.locator('#ph-i-add')).to_be_hidden()   # the prompt is used up: say where to look
    ctx.close()
    ctx, pg = phone_page(b, ua=IPHONE_UA); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click()
    expect(pg.locator('#ph-i-carry')).to_be_hidden(), 'no picks yet: nothing to carry'
    pg.click('#ph-install [data-close]'); pg.locator('.dk-line').first.click()
    pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click()
    expect(pg.locator('#ph-i-ios')).to_be_visible(); expect(pg.locator('#ph-i-carry')).to_be_visible(); expect(pg.locator('#ph-i-add')).to_be_hidden()
    pg.click('#ph-i-copy'); pg.wait_for_function("(window.__events || []).some(e => e[0] === 'keep_created')")
    clip = pg.evaluate('navigator.clipboard.readText()')
    assert re.fullmatch(re.escape(BASE) + r'#k2[A-Za-z0-9_-]{16,}', clip), clip
    assert ['home_screen', {'action': 'copied', 'layout': 'phone'}] in events(pg) and ['keep_created', {'via': 'copy', 'layout': 'phone'}] in events(pg)
    ctx.close()

STANDALONE = "Object.defineProperty(navigator, 'standalone', { configurable: true, get: () => true });"

@phone_test
def phone_home_screen_app_pastes_picks(b):
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, [70, 71, 1]); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("pick('c070', 'Zohaib “Zo” Qadri'); whys.c070 = 'Knows the district'; LS.set('ballotta.whys', whys)")
    keep = pg.evaluate('keepURL()'); share = pg.evaluate("packFrag('s', { v: 1, n: 'Maya', p: { '70': 1 } })")
    ctx.close()
    ctx, pg = phone_page(b, init=STANDALONE); pg.goto(BASE)                                # Android's Home Screen app shares Chrome's storage
    expect(pg.locator('#ph-paste')).to_be_hidden(); pg.click('#dk-help'); t = pg.inner_text('#ph-mitems')
    assert 'Paste my picks link' not in t and 'Add to your Home Screen' not in t, t
    ctx.close()
    ctx, pg = phone_page(b, init=STANDALONE, ua=IPHONE_UA); pg.goto(BASE)
    expect(pg.locator('#ph-paste')).to_be_visible()
    pg.click('#dk-help'); t = pg.inner_text('#ph-mitems')
    assert 'Paste my picks link' in t and 'Add to your Home Screen' not in t, t
    pg.click('#ph-menu [data-close]'); pg.click('#ph-paste-open'); pg.wait_for_selector('#ph-paste-d[open]')
    pg.fill('#ph-p-in', 'hello'); pg.click('#ph-p-go'); assert 'doesn’t look like a Ballotta link' in pg.inner_text('#ph-p-msg')
    pg.fill('#ph-p-in', BASE + '#' + share); pg.click('#ph-p-go'); assert 'a friend shared' in pg.inner_text('#ph-p-msg')
    pg.fill('#ph-p-in', 'My picks: ' + keep + '.'); pg.click('#ph-p-go')               # extra words around it, as in a note
    pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go'); pg.wait_for_selector('body.dk-app-on')
    assert cur(pg, 'c070') == ['Zohaib “Zo” Qadri'] and pg.evaluate('whys.c070') == 'Knows the district'
    ev = events(pg)
    assert ['home_screen', {'action': 'pasted', 'layout': 'phone', 'app': 'yes'}] in ev and ['keep_restored', {'layout': 'phone', 'app': 'yes'}] in ev, ev
    expect(pg.locator('#ph-paste')).to_be_hidden()
    assert pg.evaluate('window.ballottaDropped') == []
    ctx.close()
    ctx, pg = phone_page(b, init=STANDALONE, ua=IPHONE_UA); pg.goto(BASE)                 # straight from the clipboard
    pg.evaluate("navigator.clipboard.writeText('my bank PIN is 1234')"); pg.click('#ph-paste-open'); pg.click('#ph-p-clip')
    pg.wait_for_selector('#ph-p-msg:not(.hidden)')                                     # the clipboard is read in the background
    assert pg.input_value('#ph-p-in') == '' and 'doesn’t look like a Ballotta link' in pg.inner_text('#ph-p-msg'), 'other clipboard text is never shown'
    pg.evaluate('u => navigator.clipboard.writeText(u)', keep)
    pg.click('#ph-p-clip'); pg.wait_for_selector('#d-restore[open]')
    ctx.close()

class Flip(http.server.SimpleHTTPRequestHandler):           # the repo's files, except any path in swap (served as given)
    swap = {}
    def log_message(self, *a): pass
    def do_GET(self):
        body = Flip.swap.get(self.path.split('?')[0])
        if body is None: return super().do_GET()
        self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8'); self.send_header('Content-Length', str(len(body)))
        self.end_headers(); self.wfile.write(body)

def own_server():                                           # a spare port of the system's choosing, never 8765
    s = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Flip, directory=str(ROOT)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, f'http://127.0.0.1:{s.server_address[1]}/{PAGE}'

@phone_test
def phone_offline_copy_after_one_visit(b):
    # Network first (Lane): online, a changed page shows at once; the page, its fonts and icons are kept; with the server
    # gone (the offline copy's own network included), the kept copy opens. The page's CSP stays on throughout.
    Flip.swap = {}; srv, url = own_server(); up = True
    ctx, pg = phone_page(b, csp=True, sw=True); pg.add_init_script(CSP_WATCH)
    try:
        pg.goto(url)
        assert pg.evaluate('Promise.race([navigator.serviceWorker.ready.then(() => true), new Promise(ok => setTimeout(ok, 15000, false))])'), 'no offline copy installed'
        poll(pg, '!!navigator.serviceWorker.controller', 15)                             # and in charge of this page
        meta = pg.get_attribute('meta[http-equiv="Content-Security-Policy"]', 'content')
        assert "manifest-src 'self'" in meta and "worker-src 'self'" in meta, meta
        scope = pg.evaluate("navigator.serviceWorker.getRegistration().then(r => r && r.scope)")
        assert scope == url.rsplit('/', 1)[0] + '/', scope
        murl = pg.evaluate("document.querySelector('link[rel=manifest]').href")    # read from here: the page itself may only fetch from the county
        m = json.loads(urllib.request.urlopen(murl).read())
        assert m['display'] == 'standalone' and m['start_url'] == './' and {i['purpose'] for i in m['icons']} == {'any', 'maskable'}, m
        for i in m['icons']:
            r = urllib.request.urlopen(urllib.parse.urljoin(murl, i['src'])); assert r.headers['Content-Type'] == 'image/png' and r.read(8) == b'\x89PNG\r\n\x1a\n', i
        pg.reload(); poll(pg, "document.fonts.status === 'loaded'")
        Flip.swap['/' + PAGE] = (ROOT / PAGE).read_bytes().replace(b"<h1>What's on your ballot?</h1>", b"<h1>A newer page</h1>", 1)
        pg.reload(); assert pg.inner_text('#start h1') == 'A newer page', 'online, the newest page wins (network first)'
        Flip.swap = {}; pg.reload(); assert pg.inner_text('#start h1') == "What's on your ballot?"
        kept = pg.evaluate("caches.open('ballotta-1').then(c => c.keys()).then(ks => ks.map(r => r.url))")
        origin = url.split('/' + PAGE)[0]
        assert url in kept and any(k.endswith('.woff2') for k in kept) and all(k.startswith(origin + '/') for k in kept), kept
        srv.shutdown(); srv.server_close(); up = False                                   # now there is no network at all
        pg.reload(); poll(pg, "document.fonts.status === 'loaded'")
        assert pg.inner_text('#start h1') == "What's on your ballot?" and pg.evaluate("document.fonts.check('16px \"Public Sans\"')")
        assert pg.evaluate('window.__csp') == [], pg.evaluate('window.__csp')
    finally:
        ctx.close()
        if up: srv.shutdown(); srv.server_close()

@phone_test
def laptops_get_no_offline_copy_or_install_prompt(b):
    # Laptops stay as they are: no offline copy, and Chrome's own install offer is left alone.
    ctx, pg = new_page(b, wide=True, sw=True); pg.goto(BASE); pg.wait_for_timeout(1500)
    assert pg.evaluate("navigator.serviceWorker.getRegistration().then(r => !r)"), 'a laptop got the offline copy'
    assert not pg.evaluate("() => { const e = new Event('beforeinstallprompt', { cancelable: true }); window.dispatchEvent(e); return e.defaultPrevented; }")
    ctx.close()

@phone_test
def phone_whole_visit_counts_only_listed_events(b):
    # Today's phone page has journey tests; this is the phone layout's: sources, directions, wait times, photo ID, a keep
    # link there and back, a share link, clearing picks and everything. Everything counted is listed and says "phone".
    ctx, pg = phone_page(b); pg.goto(BASE); no_link_opens(pg); lookup_phone(pg); to_contest(pg, 'District 9')
    pg.locator('.dk-line', has_text='Qadri').click(); pg.fill('#dk-w', 'Knows the district')
    pg.locator('.dk-paper .links a', has_text='Campaign site').first.click()
    pg.click('#ph-fold'); pg.locator('#dk-notes a', has_text='League').first.click()
    pg.click('#ph-list'); pg.click('#dk-views [data-view="vote"]')
    vote = pg.text_content('#dk-paper'); assert 'Bring a photo ID' in vote and 'Moved here from another Texas county' in vote, 'photo ID and notes, as on today\'s phone page'
    pg.locator('#dk-paper a', has_text='Check live wait times').click(); pg.locator('#dk-paper a', has_text='Directions').first.click()
    ev = events(pg)
    for want in (['source_opened', {'kind': 'campaign_site', 'level': 'city', 'layout': 'phone'}], ['source_opened', {'kind': 'league_guide', 'level': 'city', 'layout': 'phone'}],
                 ['wait_times_opened', {'period': pg.evaluate('period'), 'layout': 'phone'}], ['directions_opened', {'period': pg.evaluate('period'), 'layout': 'phone'}]):
        assert want in ev, (want, ev)
    pg.click('#ph-list'); pg.click('#dk-keep'); pg.click('#keep-copy'); pg.wait_for_selector('#keep-out:not(.hidden)')
    keep = pg.inner_text('#keep-out'); pg.click('#d-keep [data-close]'); pg.click('#ph-done')   # Keep opened over the list; the list is still there
    pg.click('#dk-share'); pg.fill('#sharename', 'Lane'); pg.click('#share-go'); pg.wait_for_selector('#share-out:not(.hidden)')
    assert '#s2' in pg.inner_text('#share-out'); pg.click('#d-share [data-close]')
    pg.once('dialog', lambda d: d.accept()); pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Clear my picks').click()
    assert cur(pg, 'c070') == [] and pg.text_content('#ph-count') == '0 of 63 decided'
    names_ = names(pg)
    assert {'keep_created', 'share_sheet_open', 'share_created', 'cleared', 'help_opened'} <= set(names_), names_
    journey_check(pg, 'phone')
    ctx.close()
    ctx, pg = phone_page(b); pg.goto(keep); pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go')
    pg.wait_for_selector('body.dk-app-on'); assert cur(pg, 'c070') == ['Zohaib “Zo” Qadri'] and pg.evaluate('whys.c070') == 'Knows the district'
    pg.once('dialog', lambda d: d.accept()); pg.click('#dk-help'); pg.locator('#ph-mitems button', has_text='Clear everything').click()
    pg.wait_for_function("!Object.keys(localStorage).some(k => k.startsWith('ballotta.'))", timeout=5000)
    pg.wait_for_load_state(); expect(pg.locator('#start')).to_be_visible(); expect(pg.locator('#ph-bar')).to_be_hidden()
    journey_check(pg, 'phone')
    ctx.close()

@phone_test
def phone_runs_under_the_page_lock(b):
    # The phone layout keeps the page's Content-Security-Policy (#36): a whole visit, a friend's link to the Home Screen
    # steps, trips nothing (its icons are data: images, which the policy allows); an injected script still can't run.
    ctx, pg = phone_page(b, csp=True); pg.add_init_script(CSP_WATCH); pg.goto(BASE)
    fresh_goto(pg, link('s', {'v': 1, 'n': 'Maya', 'c': 'abcd2350', 'g': 1, 'p': {'70': 0}}))
    poll(pg, "!document.getElementById('friend').classList.contains('hidden')")
    pg.fill('#street', '1000 Guadalupe St'); pg.fill('#zip', '78701'); pg.click('#go')
    poll(pg, "document.body.classList.contains('dk-app-on') && / of \\d+ decided$/.test(document.getElementById('ph-count').textContent)")
    pg.locator('.dk-line').first.click(); pg.click('#ph-fold'); pg.click('#ph-next')
    for v in ('glance', 'vote', 'crib'):
        pg.click('#ph-list'); pg.click(f'#dk-views [data-view="{v}"]')
        if v == 'vote': pg.click('.ph-mapfold summary')
    pg.click('#dk-help'); poll(pg, "document.getElementById('ph-menu').open")
    pg.locator('#ph-mitems button', has_text='Add to your Home Screen').click(); poll(pg, "document.getElementById('ph-install').open")
    pg.click('#ph-install [data-close]'); pg.click('#dk-share'); poll(pg, "document.getElementById('d-share').open"); pg.click('#d-share [data-close]')
    pg.wait_for_timeout(500)
    assert pg.evaluate('window.__csp') == [], pg.evaluate('window.__csp')
    pg.evaluate("() => { const s = document.createElement('script'); s.textContent = 'window.__pwned = 1'; document.body.appendChild(s); }")
    pg.wait_for_timeout(200)
    assert pg.evaluate('window.__pwned') is None and any(v.startswith('script-src') for v in pg.evaluate('window.__csp')), 'an injected script ran'
    ctx.close()

@phone_test
def phone_resize_keeps_things_in_step(b):
    ctx, pg = phone_page(b); pg.goto(BASE); lookup_phone(pg); pg.click('#ph-list')
    pg.set_viewport_size({'width': 1440, 'height': 900}); pg.wait_for_timeout(100)
    assert not pg.evaluate("document.body.classList.contains('ph-list') || document.getElementById('dk-desk').inert")
    expect(pg.locator('.dk-rail')).to_be_visible(); expect(pg.locator('#ph-bar')).to_be_hidden(); expect(pg.locator('#ph-fold')).to_be_hidden()
    pg.set_viewport_size(PHONE); pg.wait_for_timeout(100)
    expect(pg.locator('#ph-bar')).to_be_visible(); expect(pg.locator('.dk-rail')).to_be_hidden()
    ctx.close()

@phone_test
def laptop_unchanged_by_the_phone_code(b):
    # Laptops must not change: at laptop widths the page with the phone code is pixel-for-pixel the page without it,
    # on the landing page and in each view. Both are built in memory from the template (as the phone-parity test does).
    m = build_module(); shots = {}
    for name, ph in (('_lp_plain.html', False), ('_lp_phone.html', True)):
        html = m.build(phone=ph)
        for size in ({'width': 1440, 'height': 900}, {'width': 1024, 'height': 640}):
            ctx, pg = new_page(b, wide=True); ctx.route(f'**/{name}', (lambda h: lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=h))(html))
            pg.set_viewport_size(size); pg.goto(f'http://127.0.0.1:{PORT}/{name}'); pg.wait_for_timeout(500)
            assert pg.evaluate('!!document.getElementById("ph-bar")') == ph, (name, 'built the wrong flavour')
            got = [pg.screenshot(full_page=True)]
            lookup_wide(pg); pg.wait_for_timeout(300); got.append(pg.screenshot(full_page=True))
            pg.click('[data-row="c070"]'); pg.locator('.dk-line', has_text='Qadri').click(); pg.fill('#dk-w', 'Knows the district'); pg.wait_for_timeout(200)
            got.append(pg.screenshot(full_page=True))
            for v in ('glance', 'vote', 'crib'):
                pg.click(f'#dk-views [data-view="{v}"]'); pg.wait_for_timeout(300); got.append(pg.screenshot(full_page=True))
            pg.click('#dk-help'); pg.wait_for_timeout(100); got.append(pg.screenshot())
            shots[(name, size['width'])] = got; ctx.close()
    for w in (1440, 1024):
        for k, (a, z) in enumerate(zip(shots[('_lp_plain.html', w)], shots[('_lp_phone.html', w)])):
            assert a == z, f'laptop differs with the phone code in: width {w}, shot {k} (landing, ballot, pick, glance, vote, crib, menu)'
```

```python file=edits_tests_P.py
"""Phone round, edit P3: tests/test_site.py. Run from the repo root, with phone_tests.py next to this script:
    python3 <this file>"""
import pathlib
ROOT, HERE = pathlib.Path.cwd(), pathlib.Path(__file__).resolve().parent
F = ROOT / 'tests/test_site.py'
s = F.read_text(encoding='utf-8')
NEW = (HERE / 'phone_tests.py').read_text(encoding='utf-8')

def rep(a, z):
    global s
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, z)

rep('''    BALLOTTA_PAGE=next/index.html python3 tests/test_site.py      # checks the preview, laptop layout included
''', '''    BALLOTTA_PAGE=next/index.html python3 tests/test_site.py      # checks the preview, phone layout included
''')
rep('''HAS_DESK = 'id="dk-app"' in (ROOT / PAGE).read_text(encoding='utf-8')
# sha256 of the live index.html as built from commit 0ae877c (Oct 14). The laptop layout must not change it until
# Lane promotes the preview. A data rebuild (ballot or League data) changes it legitimately: re-pin it in that commit.
LIVE_SHA = 'fcbf41e3792c67b0efedc81f5e12c6c3519437fa62a5be0640d222c7d7a0a7f5'
''', '''HAS_DESK = 'id="dk-app"' in (ROOT / PAGE).read_text(encoding='utf-8')
HAS_PHONE = 'id="ph-bar"' in (ROOT / PAGE).read_text(encoding='utf-8')
# sha256 of the live index.html as built from commit 06b7030 (Oct 15). The phone layout must not change it until
# Lane promotes the preview. A data rebuild (ballot or League data) changes it legitimately: re-pin it in that commit.
LIVE_SHA = '8e6eaf368729c6b9f9fb5e43c2285d477bb77397e82ee080dfddf2e7b2de5a2e'
''')
rep('''def new_page(browser, sent=None, wide=False, csp=False, touch=False):
    # The page's Content-Security-Policy (#36) forbids eval, which Playwright's wait_for_function polls with: tests run
    # with it bypassed unless they ask (csp=True), and those poll from Python instead (see poll()).
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900} if wide else {'width': 400, 'height': 900}, permissions=['clipboard-read', 'clipboard-write'], bypass_csp=not csp, has_touch=touch)
''', '''def new_page(browser, sent=None, wide=False, csp=False, touch=False, size=None, sw=False, ua=None):
    # The page's Content-Security-Policy (#36) forbids eval, which Playwright's wait_for_function polls with: tests run
    # with it bypassed unless they ask (csp=True), and those poll from Python instead (see poll()). The offline copy
    # (sw.js) is blocked unless a test asks (sw=True): a service worker would answer requests the stubs below expect.
    ctx = browser.new_context(viewport=size or ({'width': 1440, 'height': 900} if wide else {'width': 400, 'height': 900}), permissions=['clipboard-read', 'clipboard-write'],
                              bypass_csp=not csp, has_touch=touch, service_workers='allow' if sw else 'block', **({'user_agent': ua} if ua else {}))
''')
rep('''DESK_TESTS = set()
def desk_test(fn): TESTS.append(fn); DESK_TESTS.add(fn.__name__); return fn
''', '''DESK_TESTS = set()
def desk_test(fn): TESTS.append(fn); DESK_TESTS.add(fn.__name__); return fn
PHONE_TESTS = set()                                            # run only where the page has the phone layout (the preview)
def phone_test(fn): TESTS.append(fn); PHONE_TESTS.add(fn.__name__); return fn
# These drive the phone page as it is live today (the accordion list, its cards and buttons). On the preview a phone
# gets the new layout instead, so they run on index.html only; promotion moves them to the new layout (plan, Task 13).
OLD_PHONE_TESTS = {
    'audit_a10_a11_generation_and_own_ballot', 'audit_a14_a15_tracker_and_targets', 'audit_a1_a2_a3_guide_data',
    'audit_a4_a9_keep_link_limits', 'audit_a6_sheet_padding_tap_keeps_it_open', 'audit_b3_b4_counts_and_dedupe',
    'backup_nudge_after_fifth_pick', 'counts_progress_sources_and_clearing', 'counts_where_people_drop_off',
    'desk_crib_options_and_print', 'desk_failures_never_break_the_phone_flow', 'desk_landing_plum_band_and_faq',
    'desk_old_link_warning_gone_after_new_lookup', 'desk_resize_keeps_layouts_in_step', 'desk_stays_quiet_on_phones',
    'desk_why_box_grows_with_the_reason', 'double_tap_share_counts_once', 'extra_pick_is_explained',
    'friend_card_long_names_and_honest_copy', 'keep_link_round_trip', 'lookup_courthouse_and_ballot_found',
    'measure_card_prop_a', 'page_is_locked_down', 'persistent_storage_asked_at_first_pick',
    'phone_can_clear_everything_from_the_footer', 'phone_new_day_keeps_focus_on_a_directions_link',
    'race_learn_more_is_symmetric_and_attributed', 'share_friend_compare_and_events', 'stored_junk_in_share_fields',
    'stored_junk_never_breaks_keep_or_share', 'where_to_vote_sorted_by_distance'
}
''')
rep('''    live, prev = m.build(preview=False), m.build(preview=True)
    if m.DESK_LIVE:
        assert 'id="dk-app"' in live, 'promoted: the live page carries the laptop layout'
    else:
        assert 'id="dk-app"' not in live and 'DESK' not in live, 'laptop layout leaked into the live build'
        got = hashlib.sha256(live.encode('utf-8')).hexdigest()
        assert got == LIVE_SHA, f'live index.html changed ({got}). Expected only after a data rebuild: re-pin LIVE_SHA in that commit.'
    assert 'id="dk-app"' in prev and 'data-domains="preview.invalid"' in prev and 'src="../umami.js"' in prev
    assert (ROOT / 'index.html').read_text(encoding='utf-8') == live, 'index.html on disk is not what the build writes (stale, or left mutated)'
    if not m.DESK_LIVE: assert (ROOT / 'next/index.html').read_text(encoding='utf-8') == prev, 'next/index.html on disk is not what the build writes'
''', '''    assert m.strip_phone('a\\n<!--PHONE-->\\nb\\n<!--/PHONE-->\\nc;/*PHONE*/ d;/*/PHONE*/\\n') == 'a\\nc;\\n'      # the same rules, for PHONE
    for bad in ('/*PHONE*/ x', 'a\\n/*PHONE*/\\nb\\n/*/PHONE*/ }\\n', 'x /*PHONE*/ y\\n/*/PHONE*/\\n'):
        try:
            m.strip_phone(bad); refused = False
        except AssertionError:
            refused = True
        assert refused, f'malformed PHONE markers must stop the build: {bad!r}'
    live, prev = m.build(preview=False), m.build(preview=True)
    if m.DESK_LIVE:
        assert 'id="dk-app"' in live, 'promoted: the live page carries the laptop layout'
    else:
        assert 'id="dk-app"' not in live and 'DESK' not in live, 'laptop layout leaked into the live build'
    if m.PHONE_LIVE:
        assert 'id="ph-bar"' in live and "worker-src 'self'" in live, 'promoted: the live page carries the phone layout'
    else:
        assert 'id="ph-bar"' not in live and 'PHONE' not in live and 'rel="manifest"' not in live and "worker-src" not in live, 'phone layout leaked into the live build'
        got = hashlib.sha256(live.encode('utf-8')).hexdigest()
        assert got == LIVE_SHA, f'live index.html changed ({got}). Expected only after a data rebuild: re-pin LIVE_SHA in that commit.'
        assert (ROOT / 'next/index.html').read_text(encoding='utf-8') == prev, 'next/index.html on disk is not what the build writes'
        assert (ROOT / 'next/manifest.webmanifest').read_text(encoding='utf-8') == m.manifest(True) and (ROOT / 'next/sw.js').read_text(encoding='utf-8') == (m.SW_JS if m.OFFLINE else m.SW_OFF_JS)
        assert not (ROOT / 'sw.js').exists() and not (ROOT / 'manifest.webmanifest').exists(), 'no offline copy on the live site before promotion'
    assert 'id="ph-bar"' in prev and "manifest-src 'self'; worker-src 'self'" in prev and '"name": "Ballotta (preview)"' in m.manifest(True)
    assert 'id="dk-app"' in prev and 'data-domains="preview.invalid"' in prev and 'src="../umami.js"' in prev
    assert (ROOT / 'index.html').read_text(encoding='utf-8') == live, 'index.html on disk is not what the build writes (stale, or left mutated)'
''')
rep('''    block = src[src.index('const EVENTS = {'):src.index('};', src.index('const EVENTS = {'))]
    return re.findall(r'^  ([a-z_]+): \\{', block, re.M)
''', '''    block = src[src.index('const EVENTS = {'):src.index('};', src.index('const EVENTS = {'))]
    return re.findall(r'^  ([a-z_]+): \\{', block, re.M) + re.findall(r'^EVENTS\\.([a-z_]+) = \\{', src, re.M)   # the phone layout adds its own (PHONE)
''')
rep('''def main():
    srv = serve()''', NEW + '''
def main():
    srv = serve()''')
rep('''            if fn.__name__ in DESK_TESTS and not HAS_DESK:
                skipped += 1; print('SKIP', fn.__name__, '- no laptop layout in', PAGE); continue
''', '''            if fn.__name__ in DESK_TESTS and not HAS_DESK:
                skipped += 1; print('SKIP', fn.__name__, '- no laptop layout in', PAGE); continue
            if fn.__name__ in PHONE_TESTS and not HAS_PHONE:
                skipped += 1; print('SKIP', fn.__name__, '- no phone layout in', PAGE); continue
            if fn.__name__ in OLD_PHONE_TESTS and HAS_PHONE:
                skipped += 1; print('SKIP', fn.__name__, '- drives today\\'s phone page: runs on index.html'); continue
''')
F.write_text(s, encoding='utf-8')
print('tests: phone layout tests added')
```

```python file=mutate_phone.py
"""Mutation-kill check for the phone-layout tests: every mutant must turn at least one named test RED. The same runner
as mutate_desk.py (files restored from an in-memory copy, even when stopped), against the page with the phone layout:
next/index.html until promotion, index.html after. Run from the repo root after both builds:
    python3 tests/mutate_phone.py [first last]   (a slice of the list, e.g. 0 10)"""
import os, sys, pathlib
ROOT = pathlib.Path.cwd()
LIVE = '\nPHONE_LIVE = True\n' in (ROOT / 'source/build_site.py').read_text(encoding='utf-8')     # the setting's own line
os.environ['BALLOTTA_MUTATE_PAGE'] = 'index.html' if LIVE else 'next/index.html'
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mutate_desk as R

PREV, TPL, BLD = R.PREV, R.TPL, R.BLD
SW = PREV.parent / 'sw.js'
L, P, G = 'phone_ballot_list_sheet', 'phone_pick_reason_fold_and_steps', 'phone_glance_vote_and_crib_fit_the_screen'
M = [
 ('P1 the bar misses picks', PREV, "  new MutationObserver(bar).observe($('dk-count'), { childList: true });", '', [P]),
 ('P2 the page behind the list stays reachable', PREV, "    behind().forEach(e => { e.inert = true; });\n", '', [L]),
 ('P3 tapping a contest leaves the list open', PREV, "if (NARROW.matches && e.target.closest('.dk-row')) closeList('paper');", '', [P]),
 ('P4 Escape leaves the list open', PREV, "if (e.key === 'Escape' && cls.contains('ph-list') && e.target.id !== 'dk-q') { e.preventDefault(); closeList(); }", '', [L]),
 ('P5 Done drops focus', PREV, "    else (listFrom && listFrom.isConnected && listFrom.getClientRects().length ? listFrom : $('ph-list')).focus({ preventScroll: true });\n", '', [L]),
 ('P6 a move says nothing to a screen reader', PREV, "    if (h) { h.tabIndex = -1; h.focus({ preventScroll: true }); }\n", '', ['phone_lookup_opens_the_app_at_its_top']),
 ('P7 a move keeps the old scroll', PREV, "  function moved() {\n    window.scrollTo(0, 0);\n", '  function moved() {\n', ['phone_lookup_opens_the_app_at_its_top']),
 ('P8 the fold never folds', PREV, "$('dk-notes').classList.toggle('ph-open', foldOpen);", "$('dk-notes').classList.toggle('ph-open', true);", [P]),
 ('P9 a measure\'s fold says "office"', PREV, "c.type === 'measure' ? 'Sources' : ", '', [P]),
 ('P10 the fold forgets the friend', PREV, "(friend ? 'You and ' + friendName() + ' · ' : '') + what", 'what', ['phone_friend_link_landing_then_inline']),
 ('P11 Previous never disabled', PREV, "$('ph-prev').disabled = i <= 0;", "$('ph-prev').disabled = false;", [P]),
 ('P12 Next undecided with nothing left', PREV, "nx ? 'Next undecided →' : 'Crib sheet →'", "'Next undecided →'", ['phone_next_undecided_then_the_crib_sheet']),
 ('P13 the bar button stays on the crib sheet', PREV, "$('ph-next').classList.toggle('hidden', !nx && D.ui.view === 'crib');", "$('ph-next').classList.toggle('hidden', false);", ['phone_next_undecided_then_the_crib_sheet']),
 ('P14 the menu button opens the laptop dropdown', PREV, "    e.stopPropagation(); e.preventDefault(); $('ph-menu').showModal();\n", '', ['phone_menu_is_a_sheet']),
 ('P15 no Home Screen item', PREV, "      else if (!standalone()) item('home', '<b>Add to your Home Screen</b><small>Opens like an app, and keeps your picks longer</small>');\n", '', ['phone_menu_is_a_sheet']),
 ('P16 the menu button still says "menu"', PREV, "    if (NARROW.matches) { h.setAttribute('aria-haspopup', 'dialog');", "    if (false) { h.setAttribute('aria-haspopup', 'dialog');", ['phone_menu_is_a_sheet']),
 ('P17 the FAQ folds are empty', PREV, "d.append(s, q.querySelector('p').cloneNode(true));", 'd.append(s);', ['phone_landing_band_form_and_faq']),
 ('P18 Android never gets its button', PREV, "$('ph-i-add').classList.toggle('hidden', !bip);", "$('ph-i-add').classList.toggle('hidden', true);", ['phone_add_to_home_screen_three_ways']),
 ('P19 carry step without picks', PREV, "$('ph-i-carry').classList.toggle('hidden', !ios || !picked);", "$('ph-i-carry').classList.toggle('hidden', !ios);", ['phone_add_to_home_screen_three_ways']),
 ('P20 the copied link isn\'t a kept link', PREV, "if (via) { track('home_screen', { action: 'copied' }); track('keep_created', { via }); nudgeKept(); }", "if (via) { track('home_screen', { action: 'copied' }); }", ['phone_add_to_home_screen_three_ways']),
 ('P21 the browser\'s prompt is lost', PREV, "e.preventDefault(); bip = e; });", 'e.preventDefault(); });', ['phone_add_to_home_screen_three_ways']),
 ('P22 a friend\'s link pasted as mine', PREV, "    if (m[1][0] !== 'k') return say('That’s a link a friend shared. To bring your own picks, use the link from Keep my picks.');\n", '', ['phone_home_screen_app_pastes_picks']),
 ('P23 no paste box in a Home Screen app', PREV, "$('ph-paste').classList.toggle('ph-show', NARROW.matches && standalone() && iOS() && !ballot.length);", "$('ph-paste').classList.toggle('ph-show', false);", ['phone_home_screen_app_pastes_picks']),
 ('P24 Home Screen line on the 5-pick card', PREV, "toggle('ph-show', at === 25 && NARROW.matches", "toggle('ph-show', NARROW.matches", ['phone_backup_card_sits_above_the_bar']),
 ('P25 the card covers the bar', PREV, 'bottom:calc(84px + env(safe-area-inset-bottom));z-index:40', 'bottom:calc(12px + env(safe-area-inset-bottom));z-index:40', ['phone_backup_card_sits_above_the_bar']),
 ('P26 "home" not on the list', PREV, "EVENTS.backup_nudge.action = ONE_OF('shown', 'keep', 'dismiss', 'home');\n", '', ['phone_backup_card_sits_above_the_bar']),
 ('P27 Home Screen visits not marked', PREV, "? { app: 'yes' } : {}", '? {} : {}', ['phone_home_screen_app_pastes_picks']),
 ('P28 fields small enough to zoom', PREV, 'font:inherit;font-size:16px;color:var(--ink)}', 'font:inherit;font-size:14px;color:var(--ink)}', [G]),
 ('P29 the map unfolded', PREV, "  new MutationObserver(mapFold).observe($('dk-paper'), { childList: true, subtree: true });\n", '', [G]),
 ('P30 a friend\'s picks not counted on a phone', PREV, '/*PHONE*/(true || /*/PHONE*/WIDE.matches/*PHONE*/)/*/PHONE*/', 'WIDE.matches', ['phone_friend_link_landing_then_inline']),
 ('P31 print options reset on a phone', PREV, 'if (/*PHONE*/false && /*/PHONE*/!WIDE.matches', 'if (!WIDE.matches', [G]),
 ('P32 no offline copy', PREV, "navigator.serviceWorker.register('sw.js')", 'Promise.resolve()', ['phone_offline_copy_after_one_visit']),
 ('P33 the offline copy is never used', SW, '.then(async (first) => first || (await caches.match(key)) || net)', '.then(async (first) => first || net)', ['phone_offline_copy_after_one_visit']),
 ('P34 no manifest', PREV, '<link rel="manifest" href="manifest.webmanifest">\n', '', ['phone_offline_copy_after_one_visit']),
 ('P35 phone code on laptops', TPL, '.ph-only,.ph-faq{display:none}', '.ph-faq{display:none}', ['laptop_unchanged_by_the_phone_code']),
 ('P36 phone layout in the live build', BLD, '    if not phone:\n        html = strip_phone(html)\n', '', ['live_build_is_unchanged_until_promotion']),
 ('P37 preview CSP blocks the manifest', BLD, 'PHONE_CSP = "; manifest-src \'self\'; worker-src \'self\'"', 'PHONE_CSP = ""', ['live_build_is_unchanged_until_promotion']),
 ('P38 the paper sits below the band', PREV, 'body:not(.dk-app-on) .wrap{margin-top:-64px', 'body:not(.dk-app-on) .wrap{margin-top:0', ['phone_landing_band_form_and_faq']),
 ('P39 header buttons too small to tap', PREV, '.dk-btn{width:44px;height:44px', '.dk-btn{width:32px;height:32px', ['phone_landing_band_form_and_faq']),
 ('P40 a wide window keeps the list open', PREV, '    if (!NARROW.matches) { closeList();', '    if (!NARROW.matches) {', ['phone_resize_keeps_things_in_step']),
 ('P41 a move from At a glance lands mid-page', PREV, '    if (key && key !== lastKey && NARROW.matches && !booting) moved();\n', '', ['phone_glance_vote_and_crib_fit_the_screen']),
 ('P42 the search field zooms', PREV, 'background:transparent;color:#fff;font:inherit;font-size:16px;padding:0}', 'background:transparent;color:#fff;font:inherit;font-size:13px;padding:0}', [G]),
 ('P43 the friend landing keeps today\'s two buttons', PREV, 'body.dk-friend #f-cmp{display:none}\n  .dk-fcta,.dk-fchip', 'body.dk-friend #f-cmp{display:block}\n  .dk-fcta,.dk-fchip', ['phone_friend_link_landing_then_inline']),
 ('P44 Print… leaves the list over the crib sheet', PREV, "$('dk-print').addEventListener('click', () => { if (NARROW.matches) closeList('print'); });", '', [L]),
 ('P45 a saved ballot grabs focus on opening', PREV, "    if (key && key !== lastKey && NARROW.matches && !booting) moved();", "    if (key && key !== lastKey && NARROW.matches) moved();", ['phone_next_undecided_then_the_crib_sheet']),
 ('P46 laptops get the offline copy', PREV, "if (NARROW.matches && 'serviceWorker' in navigator)", "if ('serviceWorker' in navigator)", ['laptops_get_no_offline_copy_or_install_prompt']),
 ('P47 laptops lose Chrome\'s install offer', PREV, "(e) => { if (!NARROW.matches) return; e.preventDefault(); bip = e; }", "(e) => { e.preventDefault(); bip = e; }", ['laptops_get_no_offline_copy_or_install_prompt']),
 ('P48 Android\'s Home Screen app asks for a paste', PREV, "standalone() && iOS() && !ballot.length);", "standalone() && !ballot.length);", ['phone_home_screen_app_pastes_picks']),
 ('P49 any clipboard text shown', PREV, "if (/#[ks][=2]/.test(t)) $('ph-p-in').value = t;", "$('ph-p-in').value = t;", ['phone_home_screen_app_pastes_picks']),
 ('P50 the phone FAQ never counted', PREV, "seen = true; track('faq_seen'); io.disconnect();", "seen = true; io.disconnect();", ['phone_landing_band_form_and_faq']),
 ('P51 the offline copy keeps only the page', SW, "if (res.ok && res.type === 'basic')", "if (res.ok && res.type === 'basic' && r.mode === 'navigate')", ['phone_offline_copy_after_one_visit']),
 ('P52 the offline copy wins while online', SW, "  e.respondWith(Promise.race([net.catch(() => null), new Promise((ok) => setTimeout(ok, 4000, null))])", "  e.respondWith(caches.match(key).then((hit) => hit || net).then((first) => first)", ['phone_offline_copy_after_one_visit']),
 ('P53 Clear my picks missing from the phone menu', PREV, "    else $('dk-menu').querySelector('[data-help=\"' + b.dataset.ph + '\"]').click();", "    else if (b.dataset.ph !== 'clear') $('dk-menu').querySelector('[data-help=\"' + b.dataset.ph + '\"]').click();", ['phone_whole_visit_counts_only_listed_events']),
]
if __name__ == '__main__':
    R.main(M)
```

```python file=edits_mutate_P.py
"""Phone round, edit P5: let tests/mutate_phone.py reuse tests/mutate_desk.py's runner on the phone page, and re-anchor
the two build-script mutants whose lines this round changes (M41: the stripper names its tag; B1: csp_meta takes the
phone flag). Run from the repo root:  python3 <this file>"""
import pathlib
F = pathlib.Path.cwd() / 'tests/mutate_desk.py'
s = F.read_text(encoding='utf-8')

def rep(a, z):
    global s
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, z)

rep("os.environ['BALLOTTA_PAGE'] = 'index.html' if LIVE else 'next/index.html'   # after promotion the laptop layout is the live page",
    "os.environ['BALLOTTA_PAGE'] = os.environ.get('BALLOTTA_MUTATE_PAGE') or ('index.html' if LIVE else 'next/index.html')   # mutate_phone.py sets its own page")
rep('''"            assert not re.search(OPEN + '|' + CLOSE, line), f\\"line {n}: a DESK marker inside a block isn't alone on its line\\""''',
    '''"            assert not re.search(OPEN + '|' + CLOSE, line), f\\"line {n}: a {tag} marker inside a block isn't alone on its line\\""''')
rep('''('B1 no Content-Security-Policy', BLD, 'return html.replace("<!--CSP-->", csp_meta(html), 1)', 'return html',''',
    '''('B1 no Content-Security-Policy', BLD, 'return html.replace("<!--CSP-->", csp_meta(html, phone), 1)', 'return html',''')
F.write_text(s, encoding='utf-8')
print('mutate_desk.py: page override; M41 and B1 re-anchored')
```

```python file=edits_readme_P.py
"""Phone round, edit P4: README.md. Run from the repo root:  python3 <this file>"""
import pathlib
F = pathlib.Path.cwd() / 'README.md'
s = F.read_text(encoding='utf-8')

def rep(a, z):
    global s
    assert s.count(a) == 1, (a[:80], s.count(a))
    s = s.replace(a, z)

rep('''### Anonymous counts
''', '''### Phone layout (preview at ballotta.org/next/)

Narrower than 1024px, the preview shows the laptop's app folded up for a phone: a plum top bar (logo, precinct, Share, Feedback & Info), one contest at a time on the white paper, its office note and neutral sources behind an "About this office · Learn more" fold, a quiet "← Previous · Next →" row under the paper, and a plum bottom bar with **Your ballot** (the laptop's outline, search and filters as a full-screen sheet, with At a glance, Where to vote, Crib sheet, Keep my picks and Print) and **Next undecided**. Feedback & Info opens as a sheet; the landing page gets the laptop's plum band, tagline, gold "Travis County only" strip and FAQ (as folds). Every pick goes through the same code on both widths, so resizing never loses anything.

It also adds **Add to Home Screen**: `manifest.webmanifest`, three icons (`icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, drawn by `source/make_icons.py`) and an offline copy (`sw.js`, network first: online, every request goes to the network and the answer is kept; offline, or with no answer after 4 seconds, the kept copy of that file is used; lookups always need the network, and a link's #picks never reach it). On Android the menu's "Add to your Home Screen" shows the browser's own prompt. On an iPhone it explains the steps; a Home Screen app there keeps its own storage, apart from Safari's (and Safari's 7-day clean-up), so it starts empty: the steps offer to copy a private picks link first, and the Home Screen app offers "Paste my picks link". The 25-pick backup card mentions it once. The page's Content-Security-Policy gains `manifest-src 'self'` and `worker-src 'self'` for these.

Until Lane promotes it, the phone layout is marked in `source/template-travis.html` (`/*PHONE*/ … /*/PHONE*/`, `<!--PHONE--> … <!--/PHONE-->`) and `PHONE_LIVE = False` in `source/build_site.py` strips it from `index.html`, so the live page stays byte-for-byte what it was (a test pins its fingerprint). A second test builds the page with and without the phone code and checks that laptops see exactly the same pixels. **Offline kill switch:** set `OFFLINE = False` in `source/build_site.py`, rebuild and push: `sw.js` then removes itself and its copies from every phone that has it, and the page stops installing it.

### Anonymous counts
''')
rep('''Every event also carries `layout` (`phone` or `laptop`).''',
    '''Every event also carries `layout` (`phone` or `laptop`), and, from a Home Screen app only, `app` (`yes`).''')
rep('''`backup_nudge` (the backup-link card at 5 or 25 picks: shown, keep or dismiss),''',
    '''`backup_nudge` (the backup-link card at 5 or 25 picks: shown, keep, dismiss, or home for its Home Screen line), `home_screen` (Add to Home Screen: the steps opened, from the menu or the card; the browser's prompt shown; added; a picks link copied to carry over; one pasted into a Home Screen app),''')
rep('''`share_compare` (phone: each Compare tap; laptop: once per friend link when one of their races is first shown beside your ballot)''',
    '''`share_compare` (today's phone page: each Compare tap; laptop, and the phone preview: once per friend link when one of their races is first shown beside your ballot)''')
rep('''python3 source/build_site.py                        # writes index.html and census.html
''', '''python3 source/build_site.py                        # writes index.html and census.html
python3 source/build_site.py --preview              # writes next/ (the phone preview, its manifest.webmanifest and sw.js)
python3 source/make_icons.py                        # only if the logo changes: the Home Screen icons
''')
rep('''python3 tests/mutate_desk.py                        # mutation check of the tests (slow; restores every file it touches, even when stopped)
''', '''python3 tests/mutate_desk.py                        # mutation check of the tests (slow; restores every file it touches, even when stopped)
python3 tests/mutate_phone.py                       # the same for the phone layout's tests, against the preview
''')
F.write_text(s, encoding='utf-8')
print('README: phone layout, Home Screen, counts')
```
