# Ballotta after-election page code: cold audit (deep-page)

Scope: the RESULTS blocks in `source/template-travis.html`, every `after()` branch in the laptop (`desk`) and phone code, the runoff, how results.json is fetched, checked and kept, storage, printing, and the demo build and lock. Also whether the results tests check what they claim.

How I checked: I read all of the code above. I also copied the repo to the scratchpad. `build_site.py --check` passed there, so the shipped index.html matches the template. Then I ran Playwright probes using the suite's own helpers (`rs_page`, `rs_go`, `RS_BALLOT`, the fixtures) on port 8791. Probe scripts are `p1.py` to `p7.py` in `/tmp/claude-0/-home-claude/83046943-1852-502f-a4b7-3e94315f60c5/scratchpad/deep-page/`. Nothing under /home/claude/ballotta was changed. Line numbers refer to `source/template-travis.html` unless another file is named.

Severity: **High** means voter-visible wrong behavior or data loss that is likely to happen. **Medium** means real, but needs a specific situation. **Low** means polish, hardening or a refactor.

---

## A. Bugs

### 1. [Medium-High] Runoff picks and reasons are lost when two tabs are open (the #92 bug again)
- **Where:** 2811–2821 (`RP`/`RW` are cached once, in `rstore()`, and `rpick`/`rwhy` write the whole cached object back); 2265–2275 (the storage listener handles only `ballotta.picks`/`ballotta.whys`).
- **Scenario:** Two runoffs are on the ballot (c069 and c121) and two tabs are open on Nov 14.
  - Tab 1 picks Bowen in c069.
  - Tab 2, whose cache is stale, then picks Bradley in c121.
  - Result: `ballotta.runoffPicks` becomes `{"c121":["Cheryl Bradley"]}`. Tab 1's pick is gone.
  - Tab 2's rail still says "Bowen or Xie · Undecided".
  - Reasons (`RW`) behave the same way. Typing a runoff reason in one tab erases another contest's reason written in the other tab.
- **Confirmed:** ran it (`p1.py two_tabs_runoff_picks_ui`).
- **Fix:**
  - Re-read storage before each write: `rstore()` should always reload, or reload on a `storage` event for these two keys.
  - Add the two keys to the #92 listener: set `RP = RW = null` (`results.runoff.reset()`, which exists and is never called), then redraw the runoff rail, paper and ovals.
  - Better: run runoff picks through the same machinery as Nov 3's picks (`cleanPicks`, the listener, the debounce, the cleared-in-another-tab guard).

### 2. [Medium] After midnight on the runoff day, an open runoff page goes stale and throws
- **Where:**
  - 1745–1752: `dayCheck()` only calls `desk.today()`.
  - 3605–3611: `desk.today` only updates the header line.
  - 3525–3526 and 3157–3158: `results.runoff.list().find(...).c`.
- **Scenario:** Runoff Decide is open at 11:59 pm on Dec 12 (Austin), and the clock passes midnight.
  - The page still shows the plum band "Saturday, Dec 12 · Today" and the runoff group.
  - Pressing 1, or clicking an oval, throws `Cannot read properties of undefined (reading 'c')`.
  - The click had already saved the pick first (`runoffPicks` gets written after the runoff was held).
  - Other date-driven text also stays stale until the next results file or click: the timeline's current step, "Runoff held", the 7-day correction note, the late-ballots line and W5.
- **Confirmed:** ran it (`p1.py midnight_after_runoff`). `pg.errs` held two TypeErrors.
- **Fix:**
  - In `desk.today()`, when `after()`, call `desk.reflow('')`. That redraws and keeps focus (Pass 1's concern was the Nov 3 reason box, which doesn't exist after the election).
  - In `rrefresh` and the rdecide key handler, guard against an empty `find()` and fall back to `render()`.

### 3. [Medium] A results file older than the one shown replaces it, and "Since you last looked" repeats itself
- **Where:** 2353 (`changed = !R || next.seq !== R.seq || …`). Any different seq is accepted, including a lower one.
- **Scenario:**
  - The page shows seq 5 (4 of 11 official).
  - The next poll gets seq 2. Possible causes: a lagging CDN edge right after a deploy, or the phone's kept copy if the cache write had failed.
  - The rail drops to "0 of 11 official", and `resultsSeen.seq` is written as 2.
  - On the next visit with seq 5, the page says "Since you last looked: 4 results became official." again.
- **Confirmed:** ran it (`p1.py seq_goes_backwards`).
- **Fix:** ignore `next.seq < R.seq` unless the current R is the saved copy (`saved`). Never lower `resultsSeen.seq`: write `max(seen.seq, R.seq)`.

### 4. [Medium] On every visit from Nov 4, the page first opens as the editable pre-election ballot and only becomes the record when results.json arrives
- **Where:**
  - 3998–4007: `renderStored()` renders before `results.start()`.
  - 2749: the first `load(true)` is asynchronous.
  - 3203: `after()` stays false until `R` is set.
- **Scenario:** Nov 5, with results.json delayed 3 s (a slow phone; the service worker waits up to 4 s before using its copy). Until the file arrives:
  - The menu reads Decide · At a glance · Where to vote · Print your choices.
  - The header says "Election Day was Nov 3".
  - The paper has live ovals on c006, the first contest without a pick.
  - A tap changed the Nov 3 record: `current('c006')` became `['Greg Abbott']`.
  - When results arrive, the page jumps to c001, and on a phone `moved()` scrolls to the top and moves focus.
- **Confirmed:** ran it (`p2.py load_flash`, with fetch delayed by an init script).
- **Fix:** pick one:
  - (a) From `live()` days, render the ballot read-only (or show a "Loading results…" state) until the first `load()` settles. Fall back to the pre-election ballot only if it fails or the file has nothing usable.
  - (b) Keep the last accepted results.json in localStorage (it's public data). Render from it synchronously on load, labeled as a saved copy until the network answers.

  (b) also removes the jump and focus move.

### 5. [Medium] An official runoff whose date isn't known yet is described as "Nothing else on your ballot"
- **Where:** 2598 (`upcoming` requires `runoff_on`); 2615–2623.
- **Scenario:** c121 is official with verdict `runoff` and `runoff_on: null`. check_results allows this ("runoff_on: date or null, once known"); it's the window between a canvass declaring a runoff and the pipeline getting its date. The summary then says:
  - "What's next: Nothing else on your ballot. We'll keep the results updated until each one is official."
  - Meanwhile the ribbon says "Headed to a runoff: Cheryl Bradley and Candace L. Hunter".
  - There is no runoff group and no timeline step.
- **Confirmed:** ran it (`p2.py runoff_without_date`).
- **Fix:** add a branch for an official runoff with no date, e.g. "A runoff is coming · date to be set" (new words, W106+ for Lane). Or count it in the "A runoff is possible" branch (2619), which today only catches unofficial runoffs.

### 6. [Medium, rollback only] With the results code rolled back, a browser that last showed a runoff page gets a blank paper
- **Where:** 2901 (`ui.view` accepts `rdecide`/`rvote`/`rcrib` outside the RESULTS markers); 3064–3066 (the reset is inside the markers); 3070 (the dispatch table loses those keys).
- **Scenario:**
  - Build with `build(results=False)`.
  - localStorage has `ballotta.desk = {v:'rdecide'}`.
  - `render()` throws "…[ui.view] is not a function". The exception is swallowed by the `try` around `desk.ballot()`.
  - The laptop paper is empty, and the phone's paper is too; `phone.after()` never runs.
  - It recovers only when the user clicks a row or a menu item.
  - The build check (`--check`) builds the rollback but never runs it in a browser.
- **Confirmed:** ran it (`p2.py rollback_build_saved_runoff_view`, `p3.py`).
- **Fix:** move the `'all', 'rdecide', 'rvote', 'rcrib'` part of the list at 2901 into a RESULTS marker. Or make the dispatch fall back: `(views[ui.view] || viewDecide)()`.

### 7. [Medium] A results update while a runoff reason is being typed moves the caret to the start
- **Where:** `reflow()` at 3563–3573. 3570 re-focuses the new `#ro-w` but doesn't restore its selection.
- **Scenario:**
  - The voter is typing in the runoff reason box with the caret mid-text.
  - The 10-minute poll, or coming back to the tab, brings a new seq.
  - The caret goes to position 0, and the next keystroke lands at the start ("XExperience matters…").
- **Confirmed:** ran it (`p1.py caret_on_reflow`).
- **Fix:** in `reflow`, when the focused element is a text field, save `selectionStart`/`selectionEnd`/`scrollTop` and restore them on the replacement. Or skip redrawing the paper while `#ro-w` has focus, as the Nov 3 code avoided full redraws during typing.

### 8. [Medium] Runoff menu items send `view_opened` with its `view` stripped
- **Where:** 1241 (`EVENTS.view_opened.view` allows decide/glance/vote/crib/all only); 3501 (tracks `btn.dataset.view` for rdecide/rvote/rcrib).
- **Scenario:**
  - Clicking Decide, Where to vote or Print in the runoff group sends `view_opened` with only `layout`.
  - The privacy firewall drops `view_opened.view` three times (`window.ballottaDropped`).
  - So these taps are counted as unlabeled view opens, which skews the view counts.
  - No privacy leak; the firewall did its job.
- **Confirmed:** ran it (`p1.py runoff_view_opened_dropped`).
- **Fix:** add `rdecide`, `rvote` and `rcrib` (or one `runoff`) to the RESULTS override at 1241, plus README's event list. Add a `ballottaDropped == []` assertion to the runoff test.

### 9. [Medium] "Clear my picks…" leaves runoff picks and reasons
- **Where:** 2276. `clearPicks()` clears only `ballotta.picks`/`ballotta.whys`, and its confirm says "Clear all your picks and reasons?".
- **Scenario:** A runoff pick and reason are saved, then the voter chooses "Clear my picks…". Nov 3 picks are cleared, but `runoffPicks` and `runoffWhys` stay, and the rail still shows "Cheryl Bradley".
- **Confirmed:** ran it (`p1.py clear_my_picks_keeps_runoff`).
- **Fix:** clear the two runoff keys (and `results.runoff.reset()`), or change the confirm's wording. The plan only mentions Clear everything, so this needs Lane's call.

### 10. [Low-Medium] Ctrl+P from runoff Decide prints the Nov 3 results, not the runoff choices
- **Where:** 1641–1642 (`cribHTML` picks the runoff crib only when `desk.view() === 'rcrib'`); 2239 (`printCrib` re-renders, but the browser's own print doesn't).
- **Scenario:**
  - On runoff Decide, the voter picks, then presses Ctrl+P.
  - `#crib` holds "My ballot's results…", so the printout is the Nov 3 record.
  - Before Nov 3, printing from Decide printed your choices.
- **Confirmed:** ran it (`p1.py print_from_runoff_decide`).
- **Fix:** use `view[0] === 'r'` (any runoff view) to choose the runoff crib. Re-render `#crib` on `beforeprint` (today `whySave` returns early with nothing pending).

### 11. [Low-Medium] Unofficial runoff: a pick outside the pair counts as "didn't win" in the summary
- **Where:** 2584 (`outcome`: `… ? 'open' : 'down'` with no `off` check). Measures use `off ? 'down' : 'behind'` (2580).
- **Scenario:** c070 is unofficial with verdict `runoff`, and the pick is third. The summary says "1 didn't win", and the paper says "Your pick didn't make the runoff.". That reads like a call on an unofficial count, against "Ballotta doesn't call races" and Lane's rule that results are decided only when official. The Nov 4 demo scene has six such contests.
- **Confirmed:** ran it (`p7.py`).
- **Fix:** `return v.some(…) ? 'open' : off ? 'down' : 'behind'`. Ask Lane whether W39's "didn't make the runoff" should stay for an unofficial count.

### 12. [Low] The canvass date stays in the future tense once it has passed
- **Where:** 2384 (W6/W7) and 2786.
- **Scenario:**
  - On Nov 14, with c069's canvass still not done in the file (`on: 2026-11-12`), the ribbon says "Becomes official when the Austin City Council canvasses the vote on Nov 12." At a glance says "canvass Nov 12".
  - The pipeline updates "once or twice a day", and a meeting can be postponed.
  - `by` has the same problem.
- **Confirmed:** ran it (`p6.py`).
- **Fix:** when `day() > cv.on` (or `cv.by`), drop the date or say "was set for Nov 12" (wording for Lane).

### 13. [Low] "Since you last looked" can be used up on a page that never shows it
- **Where:** 2511. `top()` calls `sinceNow()`, which writes `ballotta.resultsSeen`, before checking whether the band is shown: view `all`, landing, or no app.
- **Scenario:** Open `ballotta.org/results/` (→ `?results`) with a saved ballot after new results. The band shows the county's timeline, but the seen record is moved to the new seq. If the voter leaves from that page, the next visit says nothing changed.
- **Confirmed:** ran it (`p5.py since_consumed_on_all`). In the same page load, going to Results still shows it.
- **Fix:** write the record only when the ballot's band is actually drawn: after the `view === 'all'` / runoff / `!app` early returns.

### 14. [Low] The timeline is out of order, and some runoff text uses only the first runoff
- **Where:**
  - 2633–2638: the steps aren't sorted, and Runoffs always comes after the state canvass (Dec 7).
  - 2887, 2991, 3019: the group label and band use `runoffs()[0]` only.
  - 2833: "Any registered voter in …" uses the first contest's area.
- **Scenario:**
  - A runoff before Dec 7 (Texas allows one from about 20 days after the canvass) is drawn after the state canvass.
  - Two runoffs on different dates are both grouped under the first date, and the band's "who can vote" names one district.
- **Confirmed:** read it.
- **Fix:** sort the steps by date. Group runoffs by `runoff_on`, or label each row with its own date.

### 15. [Low] Friend overlay is half-on after the election
- **Where:** 2984–2985 (the rail still draws the friend's initial and the "Maya picked …" text). `viewResult` (3173+) and `results.notes` drop the friend chip, the "Hide" control and "You and Maya".
- **Scenario:**
  - A friend's share link is opened after Nov 4.
  - The rail shows "M" avatars on two rows.
  - There's no way to hide them, and nothing on the paper explains them.
  - Zero `[data-act=hidefriend]` controls are present.
- **Confirmed:** ran it (`p5.py friend_after`).
- **Fix:** either keep the friend chip and Hide in `viewResult`, or don't draw friend marks in the rail when `after()`. Product call.

---

## B. Accessibility

### 16. [Medium] Buttons on the paper that change the view leave focus on `<body>`
- **Where:** 3162 (`ract('back'|'vote')`); 2746 (`data-rs="rvote"` → `desk.rvote()`).
- **Scenario:** These three buttons all leave focus on BODY:
  - Keyboard Enter on "Where to vote in the runoff" (the nextBox on the results paper).
  - "← Back to results" on the runoff paper.
  - "Next: where to vote in the runoff".

  A screen reader user loses their place. By contrast, `rgo(…, true)` focuses the paper.
- **Confirmed:** ran it (`p1.py focus_after_paper_buttons`).
- **Fix:** after these view changes, `P().focus({preventScroll:true})` and `say()` the new view, as `go(..., true)` does.

### 17. [Low-Medium] The runoff menu items aren't grouped for assistive tech, and the paper's label is wrong in the runoff
- **Where:**
  - 934–938 and 3014–3022: `#dk-rl` is a `<p>`, and the buttons read just "Decide Undecided", "Where to vote", "Print your choices". A screen reader user tabbing the menu can't tell them from Nov 3's (only "Where to vote" is hidden after Nov 3).
  - 3054: the paper is labeled "Your ballot's results" even on runoff Decide, which is a ballot to fill in.
- **Confirmed:** read it, and ran it (`p5.py labels_runoff`).
- **Fix:**
  - Wrap the three buttons in `role="group"` with `aria-labelledby="dk-rl"`, or give them `aria-label`s that name the runoff.
  - Label the paper "Runoff ballot" when `ui.view === 'rdecide'`.

### 18. [Low] Invalid markup, and a misleading label
- **Where:**
  - 2618: the summary's What's next is a `<button>` containing `<p>` and `<div>`, which isn't valid inside a button. The phone's `.rs-lnext` (2727) correctly uses spans.
  - 2857: the runoff reason's label says "Private unless you choose to share it", but runoff reasons can never be shared (plan decision 4).
- **Fix:** use spans with `display:block` in the button. Make the label "Only you can see it" (W-cell for Lane).

---

## C. Laptop vs phone

### 19. [Low-Medium] The phone never shows "Where things stand" in the app
- **Where:** 358 (`.rs-band .rs-sum,.rs-band .rs-tl{display:none}`, "the summary and timeline are in the list"); `listSum()` at 2721–2731 has no timeline.
- **Scenario:** On a phone there's no `.rs-tl` visible on Results, in the list, or on All Travis County results. The `#rs-top` box on All is empty (height 0). The timeline appears only on the landing page.
- **Confirmed:** ran it (`p1.py phone_timeline`).
- **Fix:** add `timeline(true)` (or a one-line "Now: Late ballots and local canvasses") to `listSum()`, and `timeline()` to the phone's All view. Or confirm with Lane that it's meant to be dropped.

### 20. [Low] The laptop draws runoff notes on Where to vote that it never shows
- **Where:** 3069 marks `rvote` as `wide`; 446 hides `.dk-notes` there; 3163 still fills them. The phone shows them.
- **Fix:** either don't make `rvote` wide, or don't render notes for it.

---

## D. Privacy and security (no problems found; notes)

### 21. Escaping and leaks: nothing found
- Every free-text field from results.json reaches the page escaped. That covers write-in names (the only names not checked against the ballot), source labels, canvasser and missing-county labels.
- This includes the runoff paper's `data-rpick` attribute and the runoff crib.
- An attack name `<img src=x onerror=…>"'`, made the winner and put in the runoff pair, never ran (`p2.py write_in_names`).
- The recount link is https-only and `rel=noopener`.
- The only thing sent off the device is a plain GET of `results.json` and the bare `results_seen` event (checked by the existing test).
- Storage keys are all `ballotta.*` literals, and the demo rewrites all 56 of them.

### 22. [Low] Demo lock notes
- `demo_lock.mjs` stores the plain password in `sessionStorage['demo:pw']` on the ballotta.org origin. If the visitor then opens the real page in that same tab, the real page's scripts can read it, and Clear everything (which only clears `ballotta.*` keys, or `demo:ballotta.*` in the demo) doesn't remove it.
  - Low risk: same origin, CSP, self-hosted scripts.
  - Storing exported raw AES key bytes instead would avoid keeping a reusable password.
- The real site's service worker (scope `/`) also caches `/demo/` on phones. That's harmless, since the page is encrypted.

---

## E. Efficiency and refactors

### 23. [Low] `entry()` → `live()` → `today()` runs `Intl.formatToParts` thousands of times per draw
- **Measured:** 2,443 calls per All Travis County results render with 214 contests and a 40-contest ballot. Measured render times here were 17.8 ms for All and 10 ms for Results, so expect several times that on a low-end phone.
- Each keystroke in the rail search rebuilds every card on the All page.
- **Fix:** compute `day()` once per render, e.g. `let dayMemo` cleared by `render()`/`load()`, or by a timestamp to the minute. Debounce search on the All page.

### 24. [Low] Refactors worth doing
- `runsAhead` (2600) and `runoffs` (2809) are the same function.
- `viewResult` and `viewDecide` duplicate the heading, meta and double-check block.
- Leftover variables: `at` in `sinceNow` (2493), and `rec.at`, which is written but never read; `k` in `summary` (2605) and `listSum` (2723).
- `pickWords` is two different functions in two scopes (2592 and 3100).
- Give the runoff store the same shape and helpers as Nov 3 picks (see 1, 9). Then the storage listener, debounce, clear and cleared-in-another-tab guard come for free.
- A single "the date changed" hook in after mode (see 2) would replace the scattered `day()` checks that only take effect on the next redraw.
- `entryOK` (2313–2335) is said to be "the checker's own rules", but it skips several of them: the runoff pair is 0 or 2 and only with verdict `runoff`; the verdicts allowed for measures vs races; no leaders for verdicts that name none; `partial` exactly when something is `missing`; Travis rows in ballot order. I found nothing that throws without them, so this is consistency, not a crash risk. Either add them or change the comment.
- The runoff band hard-codes "Early voting · Not posted yet" (2832). On and after the runoff day this is wrong ("Today"). The plan's data file will fix it; until then, hide the line when `daysTo <= 0`.
- The summary's third count reads "0 too close to call" when nothing is open, because `every()` on an empty list is true (2596). Use "not settled yet", or leave the label out at 0.

---

## F. Do the tests test what they claim?

### 25. Mostly yes, but each of the bugs above slipped through a specific gap
- **`the_runoff_is_its_own_ballot`:**
  - It checks "after the runoff" only by setting the clock and reloading, so the in-page rollover (2) isn't covered.
  - The phone section never asserts `pg.errs`.
  - It never checks two tabs (1), Clear my picks (9), `ballottaDropped` (8), Ctrl+P from Decide (10) or focus after the paper's buttons (16).
- **`a_bad_results_file_breaks_nothing`:** its XSS case puts the attack string in a ballot choice's position, so the entry is rejected and nothing is drawn. Write-in names are the free-text names that are accepted, and no test draws one with markup. A mutant that drops `esc()` from `bars()` (2450), `rowLine`'s caller (2986) or `glancePage` (2796) would survive; the only escape mutant is R4, on source labels.
- **`results_say_what_changed_since_you_last_looked`:** never sends an older seq after a newer one (3) and never opens `?results` first (13).
- **No test for:**
  - The load-time gap (4).
  - A runoff with no date (5).
  - The rollback build in a browser (6). `build_site.py --check` builds it but never runs it.
  - The caret on reflow (7).
- **`mutate_results.py`:** its 90 or so mutants are well aimed at the after-mode code that existed before Phase 4. Phase 4 has 10 (R103–R113, no R110). There are none on `rstore`/`rcur` validation, `rwhy`, `rrefresh` or `runoffBand` beyond the day count, or on the `upcoming`/`runsAhead` sort.
- **`tests/test_demo.py`:** it checks the unlocked HTML for names and fetches, and Clear everything on the shared origin, which is good. It never loads the demo's three scenes and checks for page errors. I did that: no errors or "undefined", and both layouts work in all three scenes (`p4.py`). A small loop like `p4.py` would guard it.
- **Fixtures:** `tests/results_fixture.py` covers the main states. It has no scene with two runoffs, a write-in in a runoff pair, or an official runoff with no date. All three exercise different code paths (1, 5, 14).

---

## Pre-Nov-4 page
I found no effect before Nov 4 on the live build:
- `after()` is false, `load()` returns before fetching, and the tracking events are unchanged.
- The `?today=` override is localhost-only and tested.
- The one exception is item 6, which only affects the rollback build.
- `setInterval(load, 60s)` runs before Nov 4, but it only does a date check.
