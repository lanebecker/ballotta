# Ballotta after the election: building the design

*Written Oct 21, 2026 for Lane. The design is the canvas "Ballotta after the election" (claude.ai artifact
9rWDWLLpWybw4gDBc8RcWE), agreed Oct 20–21 ("This design has nailed it"). This plan turns it into the page on
`results-build`, in phases, each one visible in the locked demo (ballotta.org/demo/) as soon as it lands. The results
back end, `results.json` and the wording cells (W1–W70) are unchanged: this is the page.*

## What changes, in one sentence

From Nov 4, once results are in, the page stops being a ballot you fill in and becomes a record of how your ballot did:
the same frame (header, plum rail, paper and notes), with the rail's menu, the paper and At a glance turned to results,
All Travis County results as its own page instead of a pop-up, and, when a runoff is official, a small "decide" section
for it alone.

## Decisions taken here (say if any is wrong)

1. **The switch.** The page is in "after" mode when `results.on()`: from Nov 4 (Austin time), with a results file the
   page accepts, not withdrawn. Before that, nothing changes. If results are withdrawn (the kill switch), the page
   shows the pause message in the summary's place and stays in after mode.
2. **Picks become a record.** In after mode the ballot paper's lines are read-only ("Your choice"); picking keys
   (1–9, S, R) do nothing. Picks and reasons stay on the device as before, and Keep my picks still works.
3. **The menu.** Results · At a glance · All Travis County results · Print your results; then, only while a runoff on
   your ballot is official and not yet held, a "Runoff · <date>" group with Decide · Where to vote · Print your choices.
   Where to vote (Nov 3's) leaves the menu after the election.
4. **No address yet.** All Travis County results works without an address (from the landing page's "or see all Travis
   County results"). Its menu still lists Results and At a glance; choosing either goes to the address form. (Your open
   question from Oct 20; this is the "ask for the address" answer. Hiding them is a one-line change if you prefer.)
5. **The summary band** is option A as last styled (Your ballot · Your N picks · What's next), with the labels sharing a
   first line. You said you'd think more about it: it's built so its contents can change without touching the rest.
6. **New words** come only from the canvas (which you've reviewed) and the approved wording cells. Anything new that the
   build needs goes into the wording doc as W71+, marked "new, not yet approved", and is listed for you before release.

## Phases

Each phase ends with: tests passing (the site suite, the results suite, the mutation runner for what changed), a demo
deploy, and a short note to Lane of what to look at.

### Phase 1: the laptop, contest by contest (target Oct 23)
1. **After mode switch** in the laptop layout (`desk`): `after()`; views relabeled from the static buttons (Decide →
   Results, Where to vote hidden, All Travis County results added, Print your choices → Print your results).
2. **Rail:** "N of M official" and the bar by official results; filters All · Too close · My picks; each row's second
   line is the result ("Runoff: Ortega and Price · Official"); the gold dot keeps its meaning (you picked).
3. **Top of the desk:** "Since you last looked" line, the summary band, and "Where things stand" (the timeline, its
   current step from the date and the canvass dates), replacing today's one-line results strip.
4. **The results paper:** where · contest i of n; title; meta; the result (status, verdict, neutral bars, How Travis
   County voted); your pick and your reason inside it; What's next for a runoff; Your choice (read-only lines);
   "What you read before voting" folded. Previous / Next stay (J / K).
5. **Notes:** About this result (who canvasses, when; How results become official), Where the numbers come from
   (sources and times), Calling races, Something look wrong? Tell us.
6. **Header:** "Results updated <date, time>" in place of the voting-dates line.

### Phase 2: All Travis County results, the landing page, the phone (target Oct 27)
1. **All Travis County results as a page** (the `all` view): wide paper, title and note, contest cards in two columns
   grouped by level; the rail keeps the main menu, then search, filters (All · Too close · Runoffs) and the levels as
   its list (Everything, Federal … Special districts, with counts and how many are official). Works without an address.
   The pop-up goes; `?results` links open the page.
2. **Landing in after mode:** "The results of the Nov 3, 2026 election, as they come in", the subline, the three steps,
   one address card ("See how your ballot did", "Show my ballot's results", "or see all Travis County results"), Where
   things stand, and the results FAQ.
3. **The phone:** the top bar's list button ("Your ballot · N of M official"), the plum list with the same menu, the
   results paper, the summary folded small, the bottom bar's Previous / Next; All Travis County results with the level
   picker. Mostly the laptop's code, as today.

### Phase 3: At a glance, Print, and the full check (target Oct 30)
*Built Oct 21 (items 1–2, the state check and the Dec 8 demo scene). Cold audit Oct 21
(`docs/audits/2026-10-21-results-cold-audit.md`): 17 issues filed (#134–#150) and fixed the same day. New words W82–W96
in the wording doc, for Lane. Still to come: Lane's word review and the release candidate.*
1. **At a glance:** Contest · Result · Your pick · Your reason; "Only contests I picked in"; read-only picks.
2. **Print your results:** the crib sheet's layout with each contest's result beside your pick.
3. **Lining figures, focus order, screen reader labels, every state on the "Pieces" board** (pause, partial, tie,
   recount, correction, two-thirds, no call) checked in the page; the cold audit (agents that haven't seen the work).
4. **Release candidate:** `results-build` merged to main behind the date gate (nothing shows before Nov 4), version
   1.4.0, by Oct 31. Dry run of the pipeline Nov 1.

### Phase 4: the runoff (after Nov 3; target the city's canvass, about Nov 12)
1. A runoff ballot from `results.json` (`verdict: runoff`, `runoff`, `runoff_on`) for contests on your ballot.
2. The Runoff group in the menu; Decide for runoff contests (Nov 3 pick as context, never pre-filled; picks kept apart
   from Nov 3's); Where to vote in the runoff (from the county's runoff list, or the "not posted yet" state); Print.
3. The plum runoff band on each runoff screen.
4. After the runoff, its results through the same pipeline.

## The demo, phase by phase

Each deploy rebuilds ballotta.org/demo/ from `results-build`. Scenes grow with the phases: Nov 4 and Nov 13 now; Dec 8
(state canvass done) in Phase 3; the runoff (Dec 12 and after) in Phase 4.

## Tests

- `tests/test_site.py`: the results tests move to the new layout (rail count and rows, summary, timeline, results
  paper, read-only lines, notes, At a glance columns, All Travis County results page with and without an address, the
  phone's list and bar). Every verdict, state and the kill switch, as now.
- `tests/mutate_results.py`: mutants for the new code (after-mode switch, filters, counts, read-only lines, the
  summary's arithmetic, the timeline's current step).
- `tests/test_demo.py`: unchanged rules (no real names, never the real results, the lock holds).

## Risks

- **Size of the change, 13 days out.** Everything is behind the Nov 4 date gate, so a mistake can't reach voters before
  then, and the kill switch withdraws results (and with them after mode) without a release.
- **The pre-election page must not change.** Every after-mode path is behind `after()`, and the site suite's 170
  before-Nov-4 tests are the guard: they run unchanged after each phase.
- **Phone layout regressions.** The phone reuses the laptop's paper and rail; Phase 2 has its own pass at 390px.
