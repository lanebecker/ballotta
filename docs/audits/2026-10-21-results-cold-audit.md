# Results build: cold audit, Oct 21, 2026

Two fresh agents audited `results-build` after Phase 3. One audited the code and found 14 findings. The other audited what voters see and found 29. The reports are kept with the session's scratch files; this page is the triage record. Each finding was argued down before filing. Survivors are GitHub issues #134–#150 in the milestone "Results 1.4.0: cold audit (Oct 21)".

## Filed (survived)

| Issue | Finding | Source |
|---|---|---|
| #134 | Demo: Clear everything wiped the real page's ballot, picks and reasons. Fixed at once in b1b5980, since the demo is live. | code 1 |
| #135 | A several-seat race names one winner once official. This affects the real pipeline (`results_rules.official`). | code 2 |
| #136 | "Since you last looked" misreports: new leaders, numbers that didn't move, old corrections, updates seen while open. | code 3 |
| #137 | fetch_results: one bad source file stops the whole run. | code 4 |
| #138 | The page's own results check misses cross-field rules its drawing code relies on. | code 5 |
| #139 | Demo Dec 8: every party race is won by the first-listed candidate. | code 6 |
| #140 | New results arriving close folds, jump the page and drop focus. | voter 1 |
| #141 | The header loses "Results updated" at midnight. | voter 2 |
| #142 | Ties and recounts read as settled, or as too close. The official `tied_runoff` gets no What's next. | voter 3, 4, 13; code 7 |
| #143 | The phone has no What's next once a ballot is open. | voter 5 |
| #144 | A split several-seat race counts as "won or are leading". | voter 7 |
| #145 | While paused, zeros look like data. | voter 8 |
| #146 | After the election the page opens on the first contest without a pick. | voter 9 |
| #147 | The timeline's Runoffs step comes from the whole county, not the ballot. | voter 10 |
| #148 | Phone tap targets under 24px, and screen-reader words in after mode. | voter 11, 12 |
| #149 | At laptop widths 1024–1279 there is no update time and the summary is squeezed. | voter 6 |
| #150 | Small fixes: skipped twice, "The rest", "Saved on this device", W5 and W8 together, disabled Previous, the What's next border, the printout's pick label, write-in 0.0%, the phone bar on the All page, demo_lock output path, test_demo write-ins. | voter 14–18, 20, 21, 24; code 8, 9, 12 |

## Argued down (not filed)

- **The read-only "Your choice" ovals look like live ones** (voter 19). This is the canvas's design, and Lane approved it. The paper says "Your choice" over them.
- **The "Runoffs" filter counts "May go to a runoff"** (voter 22). Each card says "May go to a runoff", so nothing is misstated. On election night the possible runoffs are what people look for.
- **The timeline's current step between steps** (voter 23). From Nov 18, "State canvass" is the next thing that happens, which is a fair reading of "where things stand".
- **"Results updated" uses the newest time, not the oldest** (voter 25). The canvas header, which Lane approved, says "Results updated <time>", and every ribbon shows its own sources' times.
- **The demo's password in sessionStorage** (code 9a). Only ballotta.org's own scripts run on that origin, under a strict CSP. Closing the tab clears it.
- **The demo leak check is plain-text only** (code 9c). Today's data is clean. Escaping changes no letters in these names.
- **pages.yml demo job** (code 10):
  - The password is exposed to branch code, but only the repo's collaborators can push.
  - Re-encrypting on each deploy costs seconds.
  - After the merge the job falls back to main once `results-build` is gone. The runbook will say to delete the branch, or to point the job at main.
- **The editable ballot shows until results load, and stays if the fetch fails** (code 11). This is by design: after mode needs results, and without them the page stays the ballot.
- **Refactors** (code 13): fold the verdict functions together, inject check_results' rules at build time, a demo config object, a per-mode table. These are worth doing after the election, not 13 days out; #135 and #142 fix the drift they would prevent.
- **Efficiency** (code 14): unmeasurable at this size.
- **Test-depth notes** (code 12), other than those filed: the in-page unlock script was checked live on ballotta.org/demo on Oct 20, and a_saved_copy_says_so covers the page's side of the service worker's mark.
- **The runoff fixture's 51/49 race sent to a runoff** (voter, note). It's a hand-set fixture and not in the demo. The demo's scenes run through the real rules.

## For Lane (product questions, not defects)

- After the election, should "Share my picks" stay the strongest header button? Should "Clear my picks…" stay in the menu? (voter 26)
- All Travis County results' subline leaves out approved W59's "Unofficial until each canvass. Why unofficial?". Restore it, or keep the canvas's version? (voter 27)
- "What's next · Get ready" leads to a contest page with nothing to get ready with until Phase 4 lands. That's fine if Phase 4 lands before the city's canvass (about Nov 12), when a runoff first becomes official. Otherwise use "See the runoff". (voter 29)
- W82–W88 and the words these fixes add still need approval. (voter 28)
