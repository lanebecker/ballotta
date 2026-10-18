# Ballotta cold audit, round 2 — Oct 18, 2026 (eve of launch)

Scope: the whole repo at commit 3de4641 (v1.1.4, origin/main as of 16:40 CT), one day after the first cold audit and 41 commits of remediation. Four independent auditors with no inherited context (shared page code; laptop and phone layers and the offline copy; the Python pipeline and its data; tests, workflows and security posture) formed their own findings first, then graded every round-1 remediation on SPEC (does the fix do what the finding said) and QUALITY. Findings were argued down against the code, the ballot PDF, the county's map server and the county's published election orders, then a separate no-context agent verified this document.

The site goes public on Oct 19, the first day of early voting. So the waves below are ordered by one question: what would a voter see wrong, or lose, in the next fifteen days? Everything else waits.

Line numbers: `source/template-travis.html` (T), `source/build_site.py` (B), `tests/test_site.py` (S), `source/build_rules.py` (R), at 3de4641.

Counts (computed from the files): 154 browser tests (60 common, 29 laptop, 65 phone; none skipped on the live page), 16 pipeline tests (offline, pass), 453 laptop mutants, 126 phone mutants; 214 contests (93 measures, 121 candidate contests); 45 early and 201 Election Day vote centers. `build_site.py --check` passes; the live page's sha256 (6738bfe5…) equals the committed `index.html`; the repo's tests, docs and sources are no longer served (404 at ballotta.org).

Round-1 status in one line: of the 47 findings, 38 are remediated and verified here (SPEC met or exceeded; 11 with residue listed at the end, and one of them, round-1 #4's MUD 41, remediated in the wrong direction, below), 2 became moot when the phone layout was promoted (#17, #22), 6 are deferred by Lane to after the election (#86–#90, #97), and 1 was dropped by choice (a LICENSE). 38 + 2 + 6 + 1 = 47. The remediation held up well; the exceptions are what this report is for.

Already open and not re-listed: #56 (confirm MUD/MMD codes with the Tax Office), #86–#90 (post-election refactors), #97 (rebuild the key from the corrected PDF), #98 (old share link stays on screen).

Filing: each numbered heading is the issue title; the bullets are the body. #28 and #29 are grab-bags and file as one issue per bullet or as two checklists. Labels: `P0`–`P3` plus `data`, `page`, `phone`, `tests`, `process`, `cleanup`.

Priorities: **P0** a voter sees something wrong, or the ability to fix what a voter sees this week is at risk; fix before the site is public · **P1** a voter can lose something or be misled; fix during early voting · **P2** correctness of the checks that guard the above · **P3** after Nov 3.

---

## P0 — before going public

### 1. Travis County MUD No. 41 is very likely routed to the wrong 1,217 addresses
- Where: R:78–80 (routes the seven MUD 41 contests, c193–c199, to `MUD = M41` or `Temp = M41` at medium confidence), R:99 (`UNREACHED_OK` emptied), `source/data/district_combos.json` (two rows, precinct 142: 1,215 addresses in Manor's ETJ, Muni `MEJ`, plus 2 inside Manor city limits, `C03`).
- What the county's own order says (`TC-MUD-41_Order-of-Election.pdf`, p. 1): the district "was duly created by order of the Texas Commission on Environmental Quality … dated May 4, 2026", and Nov 3 is its **confirmation** election (the order's title: "Order Calling a Confirmation Election, an Operation and Maintenance Tax Election, a System Facilities Bond Election, a Road Bond Election, Refunding Bond Elections and a Permanent Directors Election"), with five permanent directors and six propositions, five of them "THIS IS A TAX INCREASE". Its engineering budget is for facilities "to be purchased, acquired and constructed": $37.6M of water, wastewater and drainage including a treatment plant, land acquisition and impact fees. That is raw land. 1,217 registered voting addresses do not sit on land whose water system is yet to be built.
- Why M41 was chosen, and why that was wrong: the code string exists in the county data. But the county's M-codes are sequential, not district numbers. The project's own confirmed mappings (R:69–72) are North Austin MUD **No. 1** = M20, Northtown = M23, Vista = M14, Sunfield **No. 2** = M93, Williamson-Travis **No. 1** = M50; and every district with a 2026 creation in this election sits in the M118–M128 run (Eastwood M123, Kennedy Hill M126, Hidden Lakes M127, all with confirmation propositions; Travis County MMD No. 1, created Aug 17, 2026, M125). M41 sits between M40 (300 addresses, Austin) and M42 (2), in the block of long-established districts; precinct 142's Manor ETJ already carries two other established MUD codes (M77: 980 addresses, M78: 2), and M41 is plausibly a third. "M41 = MUD No. 41" was a coincidence of digits. **The round-1 report (Oct 17, #4) called M41 "the obvious candidate"; that was the auditor's error, and the remediation (f02b029, CHANGELOG 0.6.3) acted on it.** The new-sequence codes no rule uses are `Temp = M128` (2 addresses, precinct 361, west Austin ETJ), `MUD = M119` (1), `M120` (68, Lago Vista), `M121` (2), `M122` (4).
- Effect tomorrow if unchanged: the voters at about 1,217 Manor-area addresses see seven contests, five of them tax and bond measures, that are not on their ballot, flagged only "Double-check · Matched to the county's district code M41, which the Tax Office hasn't confirmed is MUD No. 41": truthful, far too mild for a probable wrong district. The district's real voters see nothing either way.
- Confidence: the data facts are verified by running and the PDF quotes are verbatim; the identification "M41 ≠ MUD No. 41" is a strong inference (nothing in the repo or the county's PDFs names the district's location), not proof. Only the Tax Office (#56) settles which code is right.
- Fix (tonight, as release 1.1.5): drop the M41 clauses; MUD No. 41 goes back to unrouted. That touches more than `build_rules.py`: `rule_for` needs its `return None, "unrouted", …` path back and `UNREACHED_OK` its entry with the reason; the page's "can't be placed on a map yet" data note was removed with f02b029 and needs re-adding; the browser test `mud_41_reaches_its_addresses_marked_double_check` (S:539–552) asserts the M41 routing and must be rewritten to assert the opposite; mutants D60/D61 (`mutate_desk.py` 338–339) target that test and must be retargeted or retired (the runner's target check fails otherwise); README line 111 and the CHANGELOG 0.6.3 entry describe the M41 routing and need a 1.1.5 entry that says why it went back. Then a build-time guard: a contest whose text says "Confirmation" or "Confirming" may not route to more than 300 addresses without an allow-list entry (Hidden Lakes, 207, passes; a 50-address threshold would fail the build on it). When the Tax Office answers, route it, still medium until confirmed. Add M119, M120, M121, M122 and M128 to the question in #56.

### 2. The broken-link rule from 1.1.3 was never applied to the shipped data: a dead campaign site is still linked
- Where: `source/data/lwv_candidates.json` (no entry has the `curl` key the current `check_sites.py` writes; the data was last produced Oct 14), `source/build_learn.py` 118–123 (`broken(http, curl)` treats `000` as dead only when `curl` is 6/35/60), `source/learn.json` and `index.html` (Okey Anyiam's `https://okeyanyiamforjudge.com`, which fails TLS, is linked).
- What: fa9bf47 fixed the code (#85) and the CHANGELOG reads as if the Anyiam case were handled; it is handled only in the unit test's synthetic data. The shipped page still offers the dead link under a candidate's name.
- Fix: run `python3 source/check_sites.py` from an ordinary connection, then `build_learn.py`, `build_site.py`, commit with the 1.1.5 release. Add a pipeline test that every entry with `http == '000'` carries a `curl` key (proof the data came from the current checker), and a build assert that `check_sites.py` has run since `lwv_candidates.json` last changed (a recorded hash or date).

### 3. The Pages deploy is not gated by the pipeline tests
- Where: `.github/workflows/pages.yml` 31–32 (runs `build_site.py --site`, which re-runs `check()`: build equals disk, release bookkeeping, rollback builds), `build-check.yml` 33–34 (the only place `tests/test_pipeline.py` runs). The 154 browser tests run in no workflow at all: a template hotfix during early voting deploys with zero automated page checks. Both start on the same push and run in parallel (1.1.4: Pages green in 18 s, Build check in 27 s).
- What: `check()` proves the committed `index.html` is what the build writes from the committed sources; it does not prove the sources are right. A hand edit to `answer_key.json`, `vote_sites.json` or `rules.json` followed by a faithful rebuild passes `--site`, deploys, and turns Build check red about ten seconds later, with only an Actions e-mail to say so. During a week of possible data hotfixes, that is the wrong order.
- Fix: in `pages.yml`, install the two pinned PDF libraries and run `python3 tests/test_pipeline.py` before `--site` (≈30 s), or trigger Pages with `workflow_run` on Build check success. Either way, `gh run watch` after every push this week, and run the browser suite locally before any template push (there is no CI for it; a Playwright job is a post-election item).

### 4. `ubuntu-latest` migrates to Ubuntu 26 starting Oct 19, launch day
- Where: all four workflows, `runs-on: ubuntu-latest`, using the image's system `python3`; every current run carries GitHub's annotation about the migration.
- What: `check()` byte-compares `json.dumps` output with the committed build. A Python version change on the new image that alters any serialization, or breaks the pinned `pdfminer.six`/`pdfplumber` install, turns Build check red and, worse, makes `--site` refuse, so a hotfix would not deploy. Suspected (the migration is announced; the breakage is not certain), and the cheapest insurance in this report.
- Fix: `runs-on: ubuntu-24.04` in all four workflows, or a SHA-pinned `actions/setup-python` with the Python the committed build was made with.

### 5. The midnight rollback has no runbook, and three of its steps bite
- Where: `source/check_release.py` 38–76 (date format: em dash and ISO date; a hyphen or "Oct 20" is refused), B:351–354 (the build refuses while `.mutate-lock` exists, and the lock is git-ignored so `git status` will not show it), `pages.yml` (red means nothing deployed and the bad page is still live), the CDN (`cache-control: max-age=600` on `version.json`; `curl "https://ballotta.org/version.json?$(date +%s)"` to see the truth), the Actions-down fallback (Settings → Pages → Source → branch re-serves the whole repo; documented in the README by this pass).
- What: a rollback is a forward release (new CHANGELOG section, `VERSION` bump) because reverting a release commit also deletes its CHANGELOG entry and re-pins the old `version.json`. Nothing says so. The service worker needs nothing (network-first; an online phone takes the new page on its next load).
- Fix: a `docs/RUNBOOK.md` (or a README section) with the exact eight steps, written and rehearsed once before Oct 19: revert → CHANGELOG + VERSION → build (clear a stale lock first) → `--check` + `test_pipeline` → one commit → push → `gh run watch` → verify with a cache-busting curl. Wave 0 itself is the first rehearsal: 1.1.5 needs its CHANGELOG section, `VERSION` and `version.json` or `check_release.py` refuses the build.

### 6. Two launch-day decisions that need a conscious yes
- `<meta name="robots" content="noindex">` (T:34) is still on the page the day before it goes public. Probably intentional for a county-only test; decide, and say so in the README either way.
- "Print your choices" inside an iPhone Home Screen app: `printCrib()` (T:1947) calls `window.print()` unconditionally, and WebKit has long made `window.print()` a no-op in standalone (Home Screen) mode. The phone layout pushes voters toward the Home Screen and offers Print in the sheet and the crib view. If the no-op holds on iOS 26, the button silently does nothing. **Test it on a device tonight.** If confirmed: when `standalone() && iOS()`, replace the button's help with "Printing isn't available from a Home Screen app: open ballotta.org in Safari and print there (your picks link carries them over)". Suspected (platform behaviour, not reproduced here).

---

## P1 — during early voting

### 7. A phone or tab left open never learns a newer page exists
- Where: `version.json` is written by the build (B:234) and read by nothing on the page or in `sw.js`; the worker only ever acts on a request the page makes, and a resumed page makes none.
- What: Lane fixes a candidate list on Oct 20. A voter who opened the Home Screen app on Oct 19 and only *resumes* it (iOS keeps the page alive in the background for hours or days; the same for a laptop tab left open or restored from the back-forward cache) stays on the Oct 19 page indefinitely. No reload ever happens, so neither the worker nor the CDN matters. Nothing prompts.
- Fix: inject the build's version into the page; on `visibilitychange` → visible (throttled to ≥10 min) `fetch('version.json', { cache: 'no-store' })`, and when it differs reuse the existing bar / `dk-say` with "A newer Ballotta is available · Reload". Never auto-reload (the same rule as the saved-copy bar). With #1 and #2 shipping as 1.1.5, this is what gets them to phones already in use.

### 8. An unknown precinct silently drops the twelve federal and state contests
- Where: T:1076–1079 (`enrich()` merges `DATA.tlc[precinct] || {}` into the record, so an unknown precinct leaves CD/HD/SD absent), T:1080–1093 (`applies()`: the twelve rules keyed on CD/HD/SD then fail quietly), R (`no_tlc` guards only the snapshot). Round-1 #4 asked for a runtime fallback; it was not built.
- What: the voter sees a complete-looking ballot, marked "Matched your exact address", with no US Rep, State Senator or State Rep. Today all 308 precincts in the Oct 18 county snapshot are in the table, and the county's own `Congressional`/`Legislative`/`Senate` fields agree with it for all 1,316 district combinations, so the trigger is a precinct the county adds or renumbers before Nov 3, or a null `Precinct`. Rare; silent.
- Fix: in `enrich()`, when the precinct is unknown, derive CD/HD/SD from `rec.Congressional`, `rec.Legislative`, `rec.Senate` (already fetched in `FIELDS`) and mark those contests medium with a note.

### 9. A refused or empty share name wipes the saved good name
- Where: T:1777 (`LS.set('ballotta.name', name)` after every share, including when `safeName` refused the typed name and `name` is `''`).
- What: CHANGELOG 1.1.4 says a refused name "is neither sent nor kept"; it is also destructive to the previously kept name. Verified by reading.
- Fix: when the typed name was refused, leave the stored name alone; a box the voter emptied on purpose still clears it.

### 10. Dismissing the restore dialog by backdrop tap or Escape counts as "Not now", for good
- Where: T:1584–1589 (any dialog closes on a backdrop tap), T:1692 (`close` deletes `ballotta.incoming` for a Keep link).
- What: an accidental tap outside the sheet on a phone drops the Keep link silently; a reload no longer re-asks (the #25 fix made the dialog return on reload, but only while the link is still stored).
- Fix: delete the stored link only on the two buttons; or on an unanswered close, `notify()` "Your saved-picks link was set aside; open it again to load it."

### 11. A Keep link the page itself cannot open is still offered for sending
- Where: T:1604–1631 (`keepTooLong()` detects a body over 40,000 characters, which `unpackFrag` refuses; the sheet shows "This link is too long to open", but "Text or email it to myself" and "Copy link" stay enabled).
- Fix: disable the two send buttons while `keepTooLong(u)` until "Leave my reasons out" is pressed.

### 13. The frame guard shows a blank page to anyone who is not the top window, with no words
- Where: T:16 (`<style id="frame-guard">body>:not(noscript){display:none!important}`), T:18 (removed only when `top === self`).
- What: the round-1 #16 fix is sound against a hostile framer (`top` is unforgeable). But a legitimate embed (a browser extension side panel; a civic site that iframes Ballotta in good faith) and, more importantly, any environment where the first inline script does not run (an extension or proxy that breaks the CSP hash) show a blank page: JavaScript is on, so the `<noscript>` note never appears either. Home Screen apps, in-app browsers and Safari Reader are top-level and unaffected.
- Fix: keep the guard; add one visible line the guard CSS exempts: "Open ballotta.org directly."

### 14. An iPad Home Screen app in landscape has no way to bring picks in
- Where: T:2492 and T:2587 (the paste box and the menu's "Paste my picks link" are gated on `NARROW.matches`); at ≥1024px the laptop menu shows, which has no paste item, and a standalone app cannot open a `#k2…` link.
- Fix: add the paste item to the laptop menu when `standalone() && iOS()`, or drop the width gate on the card.

### 15. A second Keep link while the restore dialog is open is reported as "damaged" on older browsers
- Where: T:2798–2804 → `openRestore` → `showModal()` on an already-open dialog throws `InvalidStateError` in Chrome < 114 and Safari < 17; the catch at T:2795 says "That link looks incomplete or damaged" and counts `link_damaged`.
- Fix: `if (!d.open) d.showModal()`.

---

## P2 — the checks that guard the above

### 17. Six midnight-rollover tests pass only on a machine in US Central time
- Where: S:1696, 1709, 1721, 1729, 3609, 3626 (`pg.clock.install(time=dt.datetime(2026, 10, 30, 23, 58))`, naive datetimes; Playwright converts them with `.timestamp()`, i.e. the runner's local zone, while the page computes "today" in America/Chicago).
- What: on a UTC machine 23:58Z is 18:58 CDT, still Oct 30 after the five-minute advance, and "Election Day is Tue Nov 3" is not shown → FAIL. Latent today (Lane runs in Austin; the browser suite is not in CI); bites on any other machine or a travelling laptop.
- Fix: one helper that builds these with `tzinfo=ZoneInfo('America/Chicago')`; pass `tz='America/Chicago'` to the context too.

### 18. In stub mode an unrecorded county request silently goes to the live server
- Where: S:43–64 (`route.fallback()` on a miss, with a stderr note only), `tests/county_answers.json` (two recorded URLs: the courthouse geocode and its voter-address query).
- What: "the suite runs when the county is down" holds only while no test adds a second real address; a miss then fails as a county outage with only a stderr line to explain it. The mutation runner already handles the `KILLED-LIVE` case.
- Fix: print a summary line of `COUNTY_MISSES` in `main()`, and fail the stubbed run when it is non-empty.

### 19. Nothing enforces "live content equals tag v<version>"
- Where: `source/check_release.py` (internal consistency only: VERSION ↔ CHANGELOG ↔ version.json), `release-check.yml`, `release-tag.yml` 19–23.
- What: a hotfix pushed without a bump deploys under the old number; `/version.json` keeps saying 1.1.4 while the page differs from tag v1.1.4, and the README's claim that version.json says which release is live becomes wrong, silently. History: 14 commits since versioning changed `index.html` without a bump, each pushed in a batch with its release commit; that is discipline, not a check.
- Fix: in release-check (`fetch-depth: 0` plus tags), fail when tag `v$VERSION` exists on origin and `git diff --quiet v$VERSION HEAD -- <site files>` is non-empty: "published files changed: bump VERSION".

### 20. `tests/test_pipeline.py` gaps
- Write-in presence per contest is never compared to the PDF (the choice-order test strips `Write-in`; the English-line test ignores the mixed-font "Write-in / Voto Escrito" line). All five write-ins were verified by hand here.
- `every_english_line_on_the_ballot_is_in_the_key` accepts any short English line that is a *substring* of any measure text, so a dropped candidate name that happens to appear inside a measure would pass.
- Measure ↔ title pairing is by sequence and letter only; all 93 agree today, verified by hand.
- Contest order within a level (#26) and `vote_sites.json` against the Clerk's lists (count, bus flags, starred late sites) are not tested; both verified by hand here and match the Clerk's current flyers exactly.
- Fix: a write-in test; whole-line matching with an explicit allow-list for the unopposed notices; a title-block check; a frozen copy of the Clerk's two lists to diff against.

### 21. Two-tab sync: the simultaneous-write race remains, and the debounce tracks one box
- Where: T:1333–1350 (`pick` writes the whole `ballotta.picks` object), T:1970–1980 (the storage listener re-reads after the other tab's event), T:1398–1399 (`whyTyping = [cid, box]`, a single entry), S:555–612 (the test waits for each cross-tab write to land before the next action).
- What: two picks or two reason saves inside the event-delivery window (milliseconds) and the second whole-object write erases the first; if a storage event lands while two different contests' reasons were edited inside one 150 ms window, the first box's text is reloaded stale. Both need two tabs acting at the same instant; moderately sure from event ordering, not reproduced.
- Fix: merge per key (read storage, apply this tab's changed key only, write); a `Map` of pending boxes; a test that acts in both tabs within one tick.

### 12. "Clear my picks" does not cancel a pending reason save
- Where: T:1981 (`clearPicks`) vs T:1952 (`clearEverything` does `clearTimeout(whyTimer); whyTyping = null;`) and T:1693 (`restore-go`, same gap).
- What: `storage` events fire only in other tabs, so this needs a second tab to write picks or reasons within the ≤150 ms before the pending `whySave` timer clears `whyTyping`; then the just-cleared reason comes back into memory and is saved. A two-tab, sub-150 ms race (hygiene, not a loss a voter would meet alone); verified by reading. P2, filed with #21.
- Fix: the same two statements in `clearPicks` and `restore-go`.

### 16. The saved-copy bar's first re-probe is up to 20 seconds after load
- Where: T:2749 (`visibilitychange`, `online`, `setInterval(check, 20000)`; no immediate check).
- What: a copy marked `slow` whose line is fine now shows "Slow connection… Try again" for up to 20 s before "Ballotta is back · Reload".
- Fix: `setTimeout(check, 1000)` after the listeners are wired.
- Cosmetic: nobody loses anything. P2.

### 22. ~~A test's own `pg.clock.install` on top of `BALLOTTA_TODAY`'s~~ (not a defect)
- Struck by the verification pass: Playwright 1.56's `clock.install()` on an installed clock replays and sets the new time (`install(time){ this._replayLogOnce(); this._innerSetTime(…) }`); it does not throw. S:85's comment "a test's own clock still wins" is right. Six tests, nine call sites. Kept here so it is not re-found.

### 23. `check_sites.py` records the requested URL, not the final one after redirects
- Where: `source/check_sites.py` (`url` is `'https://' + s`). A site that moved hosts is linked by the old name. Unchanged from round 1 (#38).

### 24. Workflow and repo hygiene
- `pages.yml` 6–7 and its `type != 'workflow'` branch still describe the pre-switch world; keep the branch as the emergency fallback but say so.
- `pages.yml` checkout lacks `persist-credentials: false` and the job has no `timeout-minutes`; `release-tag.yml` has no timeout; `build-check.yml` installs from PyPI without `--require-hashes` (no deploy follows; low stakes).
- `_site/` is not in `.gitignore`: a local `--site _site` leaves a 20-file tree that a midnight `git add -A` commits (it would not be published, but it bloats the repo and `test_pipeline`'s `copytree`).
- `test_pipeline`'s `copytree` (150–168) ignores `.git`, `tests`, `__pycache__`, `*.pdf` but not `.mutate-lock`/`*.mutate-tmp`, so a killed runner makes `build_check_catches_drift_and_broken_markers` fail confusingly.
- S:3982–3983 and S:4105–4106 say two laptop-half tests are "skipped wherever the phone layout exists"; nothing skips now. Comments only.
- README says "Python 3.10 or newer"; `requirements.txt` says "3.9+".
- The timeout-only kill now needs two timeouts (`mutate_desk.py` 531–542): accepted cost of round-1 #27; print the attempt count.

---

## P3 — after Nov 3

### 25. Dead legacy UI is still built, rendered and kept in step on every pick
- Where: T:1255–1270 (`showBallot` renders all 214 `<details>` into `#groups`), T:1437–1453 (`renderVote` legacy list), `#compare`, `#friend`, `#nudge`, `#reset-all-foot` and `footClear()` on every `LS.set`; both live layouts hide `.wrap` (CSS 232, 483). Covered by #86; listed because it also carries round-1's residue: duplicate `<meta name="viewport">` (T:5, T:9) is now in the live page, phone CSS `.dk-loc` rules (CSS 453–455) are dead, `desk.say()`'s comment is false, B:25–33 and the module docstring still say "until Lane approves the preview", `WIDE`'s change handler body is unreachable.

### 26. (wave 1) "County Judge" is shown after "Judge, County Court at Law No. 1"; the ballot prints it before
- Where: `source/answer_key.json` c042/c044 vs ballot p.2 col 1; the page sorts within a level by key index (T:959, T:1265). c003–c005 (US Rep 37, 11, 27) are also out of ballot order, but no voter sees more than one. Every other contest within every level follows the ballot.
- Fix: a ballot-position sort key per contest (ids must not change: they are in Keep links). Moved to wave 1 by the verification pass: every voter in the county sees this contest.

### 27. A new two-pair marker line, the shape #87 asked to stop adding
- Where: T:2076 `if (!ballot.length) /*PHONE*/{ if (window.phone) try { phone.after(); } catch (e) {}/*/PHONE*/return;/*PHONE*/ }/*/PHONE*/`. Strips correctly in all three builds (verified); one half edited breaks exactly one build.
- Fix: `if (!ballot.length) { /*PHONE*/if (window.phone) try { phone.after(); } catch (e) {}/*/PHONE*/ return; }`.

### 28. Small page items
- #53's fix ping-pongs: with one undecided contest left and open, "Next" goes on in order, and from the next contest "Next undecided" points back; N alternates forever. Let "Next" keep going in order while the only undecided one is the one deliberately left.
- `lookup_started` still double-counts on a double Enter (T:1110 fires before the sequence guard; `#go` is not disabled, which round-1 #7 asked for).
- `nudgeDone()`'s fallback focus on a phone is the hidden `a-keep` (T:1661); fall back to `dk-paper` at both widths.
- Reason text is unbounded in the glance table and the crib (links slice to 600; a pasted essay makes a many-page printout). Still open from round-1 #47.
- `safeName` gaps, for the record: "lanegop" (all-lowercase glued; only shouted/camel glued forms are caught) and enclosed alphanumerics ("🅖🅞🅟") pass; the round-1 gaps and the #93 examples are all refused; Łukasz, Søren, Đặng, GOPAL, ERDEM pass. Known false positives (Elections Lane, Campaigner, Village Ofelia, "Lane, Republican", Colleague) remain blocked. Tuning.
- `prepShare()` runs on every `#sharename` keystroke (T:1743): two `safeName` passes, `packPicks`, an async `CompressionStream` of the whole link. Cheap; debounce with the name check.
- `whySave()` rebuilds the whole rail and crib per pause (round-1 #44's "only the affected row" was not done). Cheap.
- A tampered `ballotta.picks` key of `__proto__`/`constructor` makes `BYID[k]` resolve to an inherited object and both `openRestore` and `openFriend` fall to "damaged". Self-inflicted only (links cannot produce such keys). `Object.hasOwn(BYID, k)` in `cleanPicks`.
- "Ballotta is back" trusts any HEAD 200 (T:2747); behind a captive portal that answers 200 for the real host (rare over HTTPS) Reload lands on the portal. Nothing is lost. Check `content-type` or compare `ETag` if wanted.
- A tester who kept the "Ballotta (preview)" Home Screen icon gets the live page in an in-app Safari view with a third storage bucket (the hand-off page navigates out of the preview app's `/next/` scope). The README says to re-add the icon; the hand-off page could say it too when `navigator.standalone`.
- At viewport widths in (1023.98, 1024) neither layout's media query applies and the legacy page shows; one layout unit in 64 at exactly the boundary, under zoom. `@media (width < 1024px)` / `(width >= 1024px)` closes it. Suspected, not reproduced.
- Keep/Share links made in the ~7-minute window on Oct 17 between 663feec (`r: 2`, new order) and 1789fae (old order for all links) decode the ten reordered contests wrongly. Negligible population; a CHANGELOG line.
- Shops at Arbor Walk carries "On a bus route" in the early list and not in the Election Day list: faithful to the Clerk's two flyers (Yes / No), so not an error, but the chip disappears when the voter switches periods.

### 29. Documentation currency (fixed in this pass where marked ✓)
- README: "37 measures … to be fixed" ✓; "`next/` now holds the phone-layout preview" ✓; "Phones keep the existing layout, pixel for pixel" ✓; the laptop rollback instruction (setting `DESK_LIVE = False` alone asserts out at B:291 while `PHONE_LIVE` is true, and the page that comes back is the pre-Oct-15 phone page) ✓; "Clear everything … at the bottom of the page" (the footer button is never visible on either live layout; it lives in Feedback & Info on both) ✓; "Until Settings → Pages → Source is set…" (the switch happened Oct 18; the live site confirms) ✓ with the branch fallback noted; CHANGELOG 1.1.3's "waits for the Pages setting" ✓.
- Still owed: `requirements.txt`'s "3.9+" vs README's "3.10" (#24); the plans' execution logs stop at Oct 17 and the 41 commits of waves 2–6 live only in the CHANGELOG (acceptable if the CHANGELOG is the log from here on; say so at the top of the phone plan); the Oct 17 audit doc has no per-finding done/deferred status (this report's "round-1 status" line and the CHANGELOG's issue numbers are the map); the robots decision (#6); the runbook (#5).

---

## Waves, launch-first

**Wave 0 — tonight, before the site is public (release 1.1.5).** #1 (drop M41; MUD 41 back to unrouted with the reason; the confirmation-election guard), #2 (rerun `check_sites.py`, rebuild `learn.json`, the "data came from the current checker" test), #4 (pin `ubuntu-24.04`), #3 (pipeline tests before `--site`), #5 (the runbook, rehearsed once), #6 (decide `noindex`; test Print from a Home Screen app on an iPhone). One commit for the data and the workflows, one release; `gh run watch`; verify with a cache-busting curl. Order inside the wave: #4 first (so the workflows are pinned before anything else runs on them), then #1 and #2 together, then #3, then #5 and #6.

**Wave 1 — early voting week 1 (Oct 19–23; release 1.1.6).** #7 (newer-page notice; ship this first so later fixes reach phones in use), #8 (precinct fallback), #26 (County Judge in ballot order: every Travis voter sees that contest, and the fix is a sort key), #9, #10, #11 (three small shared-code fixes, one to five lines each), #13 (one visible line under the frame guard), #15 (`showModal` guard), #14 (iPad paste item). Test-first; one remediation-audit pass on the diff; mutants over #7 and #8.

**Wave 2 — early voting week 2 (Oct 26–30; no page change except where noted).** #17 (zoned datetimes), #18 (stub misses), #19 (tag-vs-content check), #20 (pipeline test gaps), #21 with #12 (per-key merge, the pending-save cancel and the two-tab race test; a page change), #16 (probe at load; a page change), #23, #24 (hygiene, all small), and from #28 the Next ping-pong and the unbounded reason text in the printout (both visible on laptops now; small). These make a hotfix on Oct 30 or Nov 2 safer; none change what a voter sees except #21.

**Wave 3 — after Nov 3.** #25 (with #86–#90 and #97), #27, the rest of #28 (stated plainly: won't-fix for this election), the rest of #29, and a Playwright job in CI; then the next cold audit, of the post-election cleanup.

Dependencies: #4 before anything else runs in Actions; #22 is struck and in no wave; #1 and #2 before public; #7 before any later data fix matters to phones already in use; #86 (remove the legacy page) only after Nov 3, and #25's residue goes with it; #56 (Tax Office) can land in any wave and re-routes MUD 41 when it does.

---

## Argued down (not filed)

- ~~"Sunday early-voting hours may differ."~~ The data auditor compared `vote_sites.json` row by row with the Clerk's current early and Election Day flyers (fetched Oct 18): 45/201 sites, bus flags, the seven 10 pm sites and TCC "Fri Oct 30 only" match exactly; the flyers say 7 am–7 pm daily, weekends included.
- ~~The county stub masks real failures.~~ Only one address (the courthouse) is ever looked up live, and `county_is_live` is a real canary; the residue is #18's visibility, not a mask.
- ~~Retired mutants lost teeth.~~ Spot-checked M31, D14, A17, D32, D41: each targets dead legacy DOM or an equivalent path on the live page. Honest retirements, though they underline #25.
- ~~`said()` could silently stop marking.~~ The regex path handles doctype-less, commented, BOM'd and multi-line `<html` openers, verified fast and correct here.
- ~~The service worker serves a stale `version.json`.~~ The page never fetches it (which is #7's problem, not the worker's).
- ~~A framer can bypass the frame guard.~~ `top` is unforgeable; a sandboxed frame stays hidden. The residue is #13 (blank for legitimate non-top contexts).
- ~~The analytics firewall can be made to leak.~~ Two auditors again tried (url, referrer, title, data keys, `__proto__`, `layout`, numbers, `pushState`) and could not; the `x-umami-cache` session header is outside the hook; the README says Umami still groups a visit's requests into a session, without naming the header.
- ~~`profileKey` (CodeCat|Temp) merges units with different ballots.~~ Re-verified: CodeCat is the concatenation of every district code on the row; Temp (e.g. `ACCX`) is not in it, so appending it is right.
- ~~The phone's `.dk-paper .links a` tap targets.~~ 44 px `min-height` is in (#51).

## Round-1 remediation residue (SPEC met, with notes)

#7: `#go` not disabled, `lookup_started` double-counts (→ #28). #11: stores `ln` in the ballot record and Keep links where the finding said "store nothing extra"; justified (the line reason cannot be derived) and the most intricate new code in the shared slice; verified against `rules.json`. #12: `'0300'` passes `/^\d{1,4}$/` and prints "Precinct 0300" (cosmetic). #19: Lane chose "Ballotta is back · Reload" over auto-hide; documented deviation. #20: narrowed to 5xx/408/429 after Pass 1 found `!ok` masked a real 404; correct narrowing. #21: `next/manifest.webmanifest` kept on purpose (identity-merging risk on Android) rather than removed; defensible. #24: the warning exists but the send buttons stay live (→ #11 here). #25: the dialog returns on reload but a dismissal is final (→ #10 here). #17 and #22 (round 1) are moot after promotion. #27: a timeout counts only when repeated, any other exception counts (looser than "AssertionError only"; reasonable). #38: `.impeccable` ignore documented instead of narrowed (reasoned). #44: debounce yes, "only the affected row" no. #47: viewport duplicate now live; unbounded reason text still open.

## Documentation

Fixed in this pass: README lines on measures, phone layout, laptop rollback, Clear everything, the Pages source and its fallback; CHANGELOG 1.1.3's Pages sentence. The project note "Ballotta: where things live" is updated separately. Owed by wave: see #29.

## Verification pass on this document (Oct 18)

An independent no-context agent recomputed every count, read the county's Order of Election and the Clerk's flyers itself, spot-checked every P0/P1 line, and was told to make the strongest case that #1 is wrong. What it caught, corrected above and kept here struck through:

- ~~#1 rested partly on "the other 2026 confirmation districts … a handful of resident electors", listing six districts.~~ Only Eastwood, Hidden Lakes, Kennedy Hill (and MUD 41) have confirmation propositions; Hero Way West and Sunfield 2 are bond/tax elections of existing districts, MMD 1 was created Aug 2026 without a confirmation proposition, and Hidden Lakes has 207 addresses, MMD 1 125. The inference now rests on the code sequencing and the raw-land construction budget, and the title says "very likely", matching the Confidence line. ~~"every 2026 creation sits in M118–M128" while listing Sunfield 2 = M93 as one~~: Sunfield 2 is pre-existing; removed from that list. ~~Unassigned new codes M128/M119/M121/M122~~: M120 (68 addresses, Lago Vista) was missing. ~~"households" / "voters"~~ → addresses (the layer counts voting addresses).
- ~~#1's 50-address guard~~ would fail the build on Hidden Lakes (207); now 300 with the allow-list. ~~#1's fix list~~ omitted the browser test (S:539–552), mutants D60/D61, README line 111, CHANGELOG 0.6.3, the removed "can't be placed" note and `rule_for`'s unrouted path; all added.
- ~~"38 remediated, 5 deferred (#86–#90, #97), 1 dropped, 1 wrong direction" = 45~~ → 38 + 2 moot + 6 deferred + 1 dropped = 47, with the wrong-direction one inside the 38.
- ~~"44 commits"~~ → 41 (`d4d589e..HEAD`).
- ~~The README rollback sentence this pass wrote, "`next/` keeps its hand-off page"~~: after a phone rollback `next/` must be the preview build again (B:379, `site_files()` docstring); corrected in the README.
- ~~#22 (double `pg.clock.install`)~~: not a defect; struck.
- ~~#12 "one-turn window" at P1~~: a two-tab sub-150 ms race; P2 with #21. ~~#16 at P1~~: cosmetic; P2.
- ~~#3, #4, #5 as P0 under "a voter sees something wrong"~~: the P0 definition now includes "the ability to fix what a voter sees this week is at risk".
- #26 (County Judge order) was in wave 3 ("after Nov 3", i.e. never for this election) though every voter sees it; moved to wave 1. The ping-pong and unbounded-reason items from #28 moved to wave 2; the rest of #28 is now stated as won't-fix for this election.
- Wording: `enrich()` merges `|| {}` rather than "returns `{}`"; `sw.js` is network-first for every same-origin GET, not navigations only; #5's "undocumented" fallback is documented by this pass; the `x-umami-cache` sentence overstated the README; line cites for `pages.yml`, `build-check.yml` and B:351–354.
- Added: the 154 browser tests run in no workflow (#3); Wave 0 needs 1.1.5's CHANGELOG/VERSION/version.json (#5); the #9 fix must not make a deliberately emptied name un-removable.

Confirmed correct by the pass: every count in the opening paragraph after the mutant fix; all M-code address counts; the Order of Election quotes and the confirmation-election characterisation; the flyers match (45/201, "Monday–Sunday 7am–7pm", seven starred 10 pm sites, TCC Fri Oct 30 only, bus flags 26/97); every "claimed missing" item is missing (version.json unread, no runbook, pipeline tests absent from pages.yml, no precinct fallback, `#go` never disabled, whole-rail redraw, `_site/` unignored, no write-in test, no `curl` keys, dead link shipped, send buttons live, workflow hygiene items, `ubuntu-latest` everywhere with GitHub's migration annotation on the live runs); the argued-down and residue sections; the other README/CHANGELOG edits. Not covered by either round: accessibility (beyond #51's tap targets) and a fresh look at `census.html` (its round-1 fixes were verified in the remediation check only).
