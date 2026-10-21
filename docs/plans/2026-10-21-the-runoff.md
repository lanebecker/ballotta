# Ballotta's runoff (Phase 4): building the design

*Written Oct 21, 2026 for Lane. The design is on the canvas "Ballotta after the election", on the boards LaptopRunoff,
LaptopRunoffVote, PhoneRunoff, PhoneRunoffVote and RunoffStates. Lane reviewed them Oct 20–21. This is Phase 4 of
`docs/plans/2026-10-21-after-the-election.md`. It is built on `results-build`, after 1.4.0, so it shows in the locked
demo as it lands. It must be live before the city's canvass (about Nov 12), when a runoff can first become official.
Until then, What's next says "See the runoff" (Lane, Oct 21).*

## What it is

When a contest on your ballot is headed to an official runoff that hasn't been held yet (`verdict: runoff`, official,
`runoff_on` in the future), the page helps you vote in it, the way it helped before Nov 3:
- The menu keeps its four results items. Under them, a group labeled "Runoff · Sat, Dec 12" holds Decide, Where to vote
  and Print your choices.
- The rail gets a "Runoff · Sat, Dec 12" group at the top with the runoff contests ("Ortega or Price · Undecided").
- **Decide** shows the plum runoff band: the date, days to go, early voting, who can vote, and what's on your runoff
  ballot. Below it is a ballot paper for the runoff contest:
  - the Nov 3 result as context;
  - "On Nov 3 you picked …", where the pick is never carried over and the ovals start empty;
  - the two candidates with their links;
  - Skip;
  - your reason.

  The notes beside it: About this runoff, Where the candidate links come from, and Your Nov 3 picks ("kept as they were").
- **Where to vote** is the runoff's own list of vote centers once Travis County posts it. Until then it says "Travis County
  hasn't posted runoff vote centers yet", with a link to Travis County Elections, and never shows the Nov 3 list.
- **Print your choices** is the crib sheet for the runoff contests only.
- After the runoff is held, the group goes away and the contest goes back to results. W30 ("Runoff held · result not
  shown here") holds until the runoff's own results come through the pipeline (item 4 below).
- With no runoff on your ballot, there's no group, and nothing else changes.

## Decisions taken here (say if any is wrong)

1. **Runoff picks are kept apart** from Nov 3's: `ballotta.runoffPicks` and `ballotta.runoffWhys`, cleared by Clear
   everything like the rest and never sent anywhere. Your Nov 3 record never changes.
2. **Keys and keyboard:** in runoff Decide the picking keys work again (1, 2, S, R), as before Nov 3.
3. **Early voting dates and vote centers are data, not code.** They go in a small file the page reads, which is
   empty until the county posts. The page shows the "not posted yet" state until then. The canvas's
   "[RUNOFF EARLY VOTING DATES]" stays out of the page until there are real dates.
4. **Share and Keep links** carry Nov 3 picks only. Sharing runoff picks would be new, so it's out of scope.
5. **Words** come from the canvas boards Lane reviewed. Anything else goes in the wording doc as W98 and up, for Lane.

## Steps

1. Runoff contests from `results.json`. The menu group and the rail group, on laptop and phone.
2. Runoff Decide: the band, the paper (context, the Nov 3 pick line, ovals, Skip, reason, keys), and the notes.
3. Runoff Where to vote ("not posted yet", then the list) and Print your choices for the runoff.
4. The demo: a Nov 14 scene (runoff official, centers not posted) and a Dec 1 scene (centers posted, early voting).
5. Tests for every state on the RunoffStates board, mutants, the cold check, and words for Lane.
6. After Dec 12: the runoff's results through the same pipeline (official.json's runoffs and the runoff's own source
   files). This is a later step, before the runoff count.
