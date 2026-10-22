# Ballotta after-mode and runoff: deep UX audit (cold)

Built from `results-build` (clean tree; `python3 source/build_site.py` left `index.html` unchanged). Pages loaded with
`tests/test_site.py`'s `rs_page` on port 8791 (stubbed county), scenes from `tests/results_fixture.py` plus states
made with `entry()`. Scripts are in `scratchpad/deep-ux/r*.py` and screenshots in `scratchpad/deep-ux/shots/`.
SHOTS = /tmp/claude-0/-home-claude/83046943-1852-502f-a4b7-3e94315f60c5/scratchpad/deep-ux/shots

Severity: H = a voter can be misled or lose data or can't do the task; M = wrong or confusing, with a workaround;
L = polish.

## Runoff (Phase 4)

1. **H. With more than one runoff contest, there's no way to step through them.**
   - Where: runoff Decide, laptop and phone, from Nov 14. The ballot has c070 (Austin D9), c096 (Pflugerville Pl 4) and c121 (AISD D1), all official runoffs on Dec 12.
   - What the voter sees: the paper says "RUNOFF · CITY OF AUSTIN · CONTEST 1 OF 3". Its only buttons are "← Back to results" and "Next: where to vote in the runoff". J and K do nothing, and N goes to Where to vote. On the phone, the bottom bar's Next is "Where to vote →".
   - Why it matters: a voter who follows Next never sees contests 2 and 3, so they print a runoff sheet with blanks for races they didn't know about. "Undecided" in the menu is the only hint.
   - Confirmed: r4.py. After J, the current row was still c070. The nav buttons were `['← Back to results', 'Next: where to vote in the runoff']`. Screenshot `SHOTS/ro2-decide-first.png`.
   - Fix: give runoff Decide Previous / Next between runoff contests (J/K/N as before Nov 3, and the phone bar's Next). Only the last one should lead to Where to vote.

2. **H. The band's "Who can vote" names only the first runoff's area, on every runoff page.**
   - Where: the plum band, with several runoff contests.
   - What the voter sees: on the Pflugerville Place 4 paper and on the AISD D1 paper, the band still says "Any registered voter in City of Austin District 9, whether or not you voted Nov 3".
   - Why it matters: it's wrong for two of the three contests, and it states eligibility.
   - Confirmed: r4.py BAND96 output. `runoffBand()` uses `area(rs[0].c)`.
   - Fix: on Decide, use the open contest's area. On Where to vote and Print, list each area or drop the line. If dates can differ, take the date from the open contest too.

3. **H. "Clear my picks…" on the runoff pages deletes the Nov 3 record and keeps the runoff picks.**
   - Where: Feedback & Info → "Clear my picks…" (and the phone menu), while on runoff Decide.
   - What the voter sees: a dialog, "Clear all your picks and reasons?". Accepting empties `ballotta.picks` (9 → `{}`) and leaves `ballotta.runoffPicks` `{"c121":["__skip"]}`.
   - Why it matters: the same page says "Your Nov 3 picks: Kept as they were … nothing you choose here changes your Nov 3 record". A voter trying to start the runoff over erases their Nov 3 record, which can't be undone, and the runoff pick they wanted gone stays.
   - Confirmed: r8.py and `SHOTS/after-clear-my-picks.png`.
   - Fix: on runoff views, make it "Clear my runoff picks…" (runoffPicks and runoffWhys only). Elsewhere after the election, say what will go ("your Nov 3 picks and reasons, and runoff picks").

4. **H. The browser's own Print (Cmd/Ctrl+P, or File > Print) prints the wrong sheet.**
   - Where: "Print your choices" (runoff) and "Print your results", laptop and phone.
   - What the voter sees: Cmd+P on "Print your choices" prints "My ballot's results", the whole Nov 3 record. After the runoff sheet's button has been used once, Cmd+P on "Print your results" prints "My runoff choices".
   - Why it matters: the voter brings the wrong paper to the polls. #crib is only redrawn when the on-page button is pressed, and there is no `beforeprint` handler that redraws it.
   - Confirmed: r5.py with `pg.pdf()`. `SHOTS/rcrib-ctrlp.pdf` starts "My ballot's results" and `SHOTS/crib-after-rcrib-ctrlp.pdf` starts "My runoff choices".
   - Fix: call `renderCrib()` on every view change and in a `beforeprint` listener.

5. **H. From an iPhone Home Screen app, "Print your choices" does nothing and says nothing.**
   - Where: runoff Print your choices, iOS standalone.
   - What the voter sees: tapping the button gives no print and no message. "Print your results" shows "Printing doesn't work in a Home Screen app. To print, tap Keep my picks…".
   - Why it matters: `viewRCrib()` has no `#dk-noprint` note, so `printCrib()` writes its warning into the hidden `#noprint`. The Keep-link workaround wouldn't help anyway, because Keep carries Nov 3 picks only (runoff decision 4). Runoff picks made in the Home Screen app can't be printed at all.
   - Confirmed: r15.py. `__printed` stayed 0, the note was unchanged, and `#noprint` was not visible.
   - Fix: give the runoff Print page the same `cantPrint()` note. Tell the voter to write the choices down, or let Keep carry runoff picks.

6. **H. A page left open across midnight goes stale, and after the runoff it throws errors.**
   - Where: runoff pages, open overnight.
   - What the voter sees: at Dec 12 00:03 the band still says "Tomorrow". At Dec 13 00:03 it says "Today" and Decide is still shown. Pressing 2 throws `Cannot read properties of undefined (reading 'c')` and nothing happens. Clicking an oval saves the pick, but the oval doesn't update.
   - Why it matters: `desk.today()` only redraws the header after the election, and `results.json` redraws only when `seq` changes.
   - Confirmed: r9.py and `SHOTS/ro-after-midnight.png`.
   - Fix: after the election, on a new day, call `desk.render()` (or the results `redraw`). Guard `rrefresh` and the rdecide key handler against an empty `runoff.list()`.

7. **M. The kill switch hides the runoff ballot and the voter's runoff picks.**
   - Where: Dec 1, with results withdrawn.
   - What the voter sees: the menu loses the Runoff group (Decide, Where to vote, Print your choices) and a saved runoff view falls back to Results. The band says "Results are paused … Your picks aren't affected."
   - Why it matters: the runoff is already official and doesn't depend on the latest numbers. A voter getting ready loses their runoff picks and printout until results come back.
   - Confirmed: r20.py.
   - Fix: keep the runoff (pair, date, picks) from the last accepted file, or put the official runoffs in the withdrawn file. At least say runoff picks are kept.

8. **M. "Nothing else on your ballot" is wrong when a runoff is coming but not dated, or when a recount decides who goes to it.**
   - Where: the summary's What's next, the timeline and the menu.
   - What the voter sees: an official runoff with `runoff_on: null` (allowed by check_results, "once known") gives "Nothing else on your ballot · We'll keep the results updated…", with no Runoff group and no Runoffs step. Official `tied_second` ("Tie for the runoff spot · a recount decides") gives the same line.
   - Confirmed: r10.py.
   - Fix: for an official runoff with no date, show "Headed to a runoff · date not set yet". For `tied_second`, show "A recount decides who's in the runoff".

9. **M. A tie that went to a runoff still says "goes to a runoff" after the runoff.**
   - Where: rail, paper, At a glance and printout, Dec 14, `verdict: tied_runoff`.
   - What the voter sees: "Tied · goes to a runoff · Official". W30 ("Runoff held Dec 12 · result not shown here") is applied only to `runoff`.
   - Why it matters: future tense about a race already held. The summary also counts the pick as "not settled yet" indefinitely.
   - Confirmed: r10.py Dec 14 output.
   - Fix: treat `tied_runoff` like `runoff` in `verdict()`, `rowLine()` and `glanceRes()` once `day() > runoff_on`.

10. **M. "Who can vote" names a seat as if it were an area.**
    - Where: the band, for Pflugerville and Manor council (Place N, at-large).
    - What the voter sees: "Any registered voter in City of Pflugerville Place 4, whether or not you voted Nov 3".
    - Why it matters: Place 4 is a seat, not a district. The voter may think only part of the city votes. `area()` matches `/District \d+|Place \d+/`, and W100 says "With no district: the place alone ('in City of Austin')". The runoff-capable at-large races in the key are c090 Manor Place 6 and c096 Pflugerville Place 4.
    - Confirmed: r23.py.
    - Fix: match only `District \d+`. Consider "in Austin City Council District 9" rather than "in City of Austin District 9".

11. **M. After the runoff, the Nov 3 bars read as the runoff's result.**
    - Where: the c121 results paper, Dec 13.
    - What the voter sees: "Runoff held Dec 12 · result not shown here", then unlabeled bars "Cheryl Bradley 5,100 · 51.0% / Candace L. Hunter 4,900 · 49.0%". There's no pointer to where the result is.
    - Why it matters: "result not shown here" followed by a result invites misreading.
    - Confirmed: r2.py and `SHOTS/ro-results-c121-2026-12-13.png`.
    - Fix: label the bars "Nov 3 count" once the runoff is held. Add a link to Travis County's results (as the runoff notes link VoteTravis).

12. **M. Early voting and vote centers still say "not posted" on the runoff's eve and day.**
    - Where: the band and Where to vote, Dec 11 ("Tomorrow") and Dec 12 ("Today").
    - What the voter sees: "EARLY VOTING · Not posted yet" and "Travis County hasn't posted runoff vote centers yet. We'll add them as soon as it does." The summary still says "Get ready".
    - Why it matters: by then early voting is over and the county has posted. The plan puts the data in a file still to come, but if it lags the page states something false on the day that matters most.
    - Confirmed: r2.py, `SHOTS/ro-vote-2026-12-12.png`.
    - Fix: from a few days out, with no data, say "Check Travis County Elections for vote centers" (link). Drop the early voting line once early voting must have ended. Show the data file's fetch time.

13. **M. The phone's main view never mentions the runoff.**
    - Where: phone, Nov 14, results view.
    - What the voter sees: "5 of 11 official · 3 of your 9 picks won or are leading / Results updated…" and "Since you last looked: 5 results became official." What's next (Runoff · Sat, Dec 12) is only at the top of the list sheet (W94). When the list opens it scrolls to the current row, so that card is off-screen: only a white sliver shows.
    - Why it matters: the one thing to act on is hidden on the device most voters use. The laptop shows it in the band.
    - Confirmed: r6.py and r17.py, `SHOTS/since-runoff-phone.png`, `SHOTS/ph-ro-list.png` (card scrolled off), `SHOTS/ph-ro-home-full.png`.
    - Fix: add "· Runoff Sat, Dec 12 →" to the phone's compact line, or a small What's next row under it.

14. **M. Two tabs: runoff picks don't sync, and a stale tab overwrites the other's picks.**
    - Where: two tabs on runoff Decide.
    - What the voter sees: tab 1 picks Bradley, and tab 2 still shows "Bradley or Hunter · Undecided". Tab 2's next pick or reason writes its whole stale copy (`RP` is cached once). With several runoff contests, a pick made in the other tab is lost.
    - Why it matters: Nov 3 picks got a storage listener for exactly this (#92). There is none for `ballotta.runoffPicks` / `runoffWhys`.
    - Confirmed: r8.py. Tab 2 showed `false` and "Undecided" after tab 1's pick.
    - Fix: listen for those keys, reset `RP`/`RW` (`runoff.reset()`) and redraw the ovals and the rail.

15. **M. The runoff reason box promises sharing that doesn't exist, and Share / Keep don't say they're Nov 3 only.**
    - Where: runoff Decide, the "Why?" box. Also the header's "Share my picks" and the rail's "Keep my picks" on runoff pages.
    - What the voter sees: "Why? Private unless you choose to share it".
    - Why it matters: runoff reasons can never be shared (runoff decision 4). On the runoff pages, the Share and Keep buttons carry only Nov 3 picks with no hint. A voter keeping a link to move to another device loses their runoff picks.
    - Confirmed: page text (r1.py) and `SHOTS/runoff-decide-1440-full.png`.
    - Fix: label the box "Only you can see it" (as W76). On runoff views, label the buttons "Share my Nov 3 picks" / "Keep my Nov 3 picks", or say so in the dialog.

16. **M. Big empty gap between the band and the paper on short pages.**
    - Where: laptop, runoff Where to vote, runoff Print your choices, and the paused (withdrawn) results view.
    - What the voter sees: about 100–180px of empty lilac under the band. In rvote the paper starts at y=383 though the band ends at 204; in rcrib at 340.
    - Why it matters: `.dk-desk` is a grid with a viewport min-height, and its rows stretch when content is short.
    - Confirmed: r3.py measurements, `SHOTS/ro-vote-2026-12-12.png`, `SHOTS/ro-crib-2026-11-14.png`, `SHOTS/withdrawn-desk.png`.
    - Fix: `align-content: start` on `.dk-desk`.

17. **M. Focus is lost after the runoff's navigation buttons.**
    - Where: laptop. "← Back to results", "Next: where to vote in the runoff", and "Where to vote in the runoff" on the results paper.
    - What the voter sees: after Enter, focus is on `<body>`. "Back to results" also leaves the page scrolled to y=536 rather than at the top.
    - Why it matters: keyboard and screen reader users lose their place. "Get ready…" and N focus the paper, but these buttons don't.
    - Confirmed: r19.py.
    - Fix: after these, `scrollTo(0,0)` and focus the paper (or its h1), as `rgo(…, true)` does.

18. **M. Screen-reader names on the runoff pages are wrong or ambiguous.**
    - Where: runoff Decide, Where to vote and Print; the rail and the menu.
    - What a screen reader user gets:
      - The paper is announced "Your ballot's results", because `render()` sets it from `after()`.
      - The menu's runoff group is a `<p>`, so the buttons read "Decide Undecided", "Where to vote" and "Print your choices" with no "Runoff". These are the same names as Nov 3's views.
      - The rail's runoff row is named "Austin ISD Board of Trustees, District 1 Bradley or Hunter · Undecided", the same title as the results row.
      - Moving to a runoff contest from the rail announces nothing. The live region kept stale text; Nov 3 moves say "Contest 9 of 11: …" (#148).
    - Confirmed: r7.py and r16.py (`aria_snapshot`).
    - Fix: label the paper "Runoff ballot" (and "Where to vote in the runoff" etc.). Wrap the group in `role="group" aria-labelledby="dk-rl"`. Add a visually hidden "Runoff: " to runoff rows. Have `rgo` say "Runoff contest 1 of 3: <title>. <state>."

19. **M. The phone's bottom bar on the runoff pages reads "← Contest 1".**
    - Where: phone, runoff Decide and Where to vote.
    - What the voter sees: "← Contest 1" (aria "Contest 1, go back"). It goes to results contest N, whichever results contest was last open. On runoff Decide, which is "contest 1 of 1" of the runoff, it reads as "this contest". On Where to vote it skips Decide and goes to results.
    - Confirmed: r6.py, `SHOTS/ph-ro-decide-full.png`, `SHOTS/ph-ro-vote.png`.
    - Fix: "← Results" on runoff Decide and "← Decide" on runoff Where to vote and Print.

## Results (after mode)

20. **L–M. Rail lines are cut off with an ellipsis, dropping "Unofficial" (and a name).**
    - Where: laptop rail at 1024, 1280 and 1440.
    - What the voter sees: "Leading for 2 seats: Sarah Ponder, Robe…" — "Robert Johnson · Unofficial" is gone. "Elected: George Morales III (unopposed) · Official" is clipped at 1024–1280.
    - Why it matters: the tone rule is "Unofficial" on every unofficial result.
    - Confirmed: r12.py `clipped()` and `SHOTS/ro-results-c121-2026-11-14.png`.
    - Fix: let the row's second line wrap to two lines, or put the status first ("Unofficial · Leading…").

21. **L. At 1024px the runoff band squeezes into narrow columns.**
    - Where: the band at 1024 wide.
    - What the voter sees: "Who can vote" wraps to 8 lines and "On your ballot" to 5. The band is 236px tall, pushing the ballot below the fold. The summary's What's next wraps "Runoff · Sat, Dec / 12".
    - Confirmed: `SHOTS/ro-decide-1024.png` and `SHOTS/ro-results-1024.png`.
    - Fix: below about 1200px, put the facts in a row under the date. Keep "Sat, Dec 12" together (nbsp).

22. **L. The runoff printout's footnote and the rail's Print… are off.**
    - The runoff printout says "Blank = no vote planned" even for Undecided.
    - The rail's "Print…" on runoff pages opens Print your results, not Print your choices.
    - Confirmed: r2.py CRIB text, and code (`dk-print` handler → `setView('crib')`).
    - Fix: print "Undecided" for no pick (and blank only for Skip), and have Print… open `rcrib` from runoff views.

23. **L. Rail filters and search on runoff Decide hide the runoff group, including the open contest.**
    - What the voter sees: "Too close" or searching "Morales" removes the "RUNOFF · SAT, DEC 12" rows.
    - Confirmed: r25.py.
    - Fix: keep the runoff group pinned whatever the filter.

24. **L. The summary's first pick count always says "won or are leading".**
    - What the voter sees: with every pick official, the cards read "3 won or are leading · 5 didn't win". The second card adapts ("didn't win" with nothing behind), but the first never drops "or are leading".
    - Confirmed: r22.py.
    - Fix: "won" when nothing is leading (mirroring W71).

25. **L. The runoff's Nov 3 context box differs from the results paper.**
    - "Nov 3 · official · canvassed by …" is lowercase "official", where everywhere else it's "Official".
    - The bars show percentages only, while the results paper shows "5,100 · 51.0%".
    - "Saved on this device" sits on the runoff paper before anything is saved (it was removed from results papers, #150).
    - Confirmed: `SHOTS/runoff-decide-1440-full.png`.
    - Fix: "Nov 3 · Official"; the same bars as the results paper; show "Saved" only after a pick.

26. **L. The band's width jumps between runoff pages.**
    - What the voter sees: the band is 1072px on Decide and Print, and 1040px on Where to vote (the `.wide` desk). It visibly jumps as you move through the group.
    - The laptop's Where to vote also hides "About this runoff" (no notes column).
    - Confirmed: r3.py.

27. **L. On the phone, All Travis County results has a gap in its intro paragraph.**
    - What the voter sees: a taller line before "lines. Unofficial until each canvass. Why unofficial?". The inline button sets the line height.
    - Confirmed: `SHOTS/all-noaddr-phone.png`.
    - Fix: `vertical-align: baseline; line-height: inherit` on inline `.dk-link` buttons (keep the hit area with padding or a pseudo-element).

28. **L (fixtures, not the page). The test scenes contradict their own wording.**
    - In the `runoff` scene, c121 shows "No one won a majority" beside "Cheryl Bradley 51.0%": a two-candidate race can't go to a runoff unless tied.
    - In the `official` scene, the Senate shows "Tied" with a 10,000-vote gap (W11 covers this, but it looks wrong).
    - The demo's own data (`tests/results_demo.py`, c070) is realistic. Keep these fixture scenes out of anything Lane or testers review, or give c121 a third candidate.

## Checked and fine

- No horizontal overflow at 320, 390, 1024, 1280 and 1440 in any results or runoff view.
- Phone tap targets are 44px or more (search box 42px).
- Text contrast passes, apart from the disabled Previous.
- Every verdict word matches W1–W105. No "Lost", check marks, "Ahead" or party colors. "Unofficial" is on every unofficial ribbon.
- Recount, two-thirds, partial with two counties, correction, no call, counting, unopposed and the paused rail all read correctly.
- Runoff picks stay apart from Nov 3 picks, and the oval starts empty for a Nov 3 pick that made the runoff.
- W30 on Dec 13 and the Runoff group's disappearance work after a reload.
- Print your results output is correct when started from its button.
