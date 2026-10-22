# Deep cold audit of the after-election code, Oct 21, 2026

Lane asked for a deep audit of everything that runs after Election Day, with plenty of time before Nov 3. Three fresh
agents, with no context, each took one part:
- `page.md`: the page code (results, after mode, the runoff, the demo). 25 items.
- `backend.md`: the results pipeline and how it's operated (fetch, build, rules, checks, workflows, runbook, law).
  25 items.
- `voters.md`: what voters see, in a browser, on laptop and phone. 28 items.

## Filed (survived arguing down)

Each issue groups related findings and names the report items it covers.

| Milestone | Issues |
|---|---|
| **Election night readiness** (14): before Nov 3 | #152–#164 |
| **The runoff** (15): before the city's canvass (~Nov 12); #175 before Dec 12 | #165–#176 |
| **After-election polish** (16) | #177–#179 |

## Argued down (not filed)

- **The demo's password in sessionStorage** (page 22). Same reasoning as Oct 21's first audit: only ballotta.org's own
  scripts run there, under a strict CSP, and closing the tab clears it.
- **"won or are leading" when nothing is leading** (voters 24). It's W71's approved wording, and the number beside it
  says how many.
- **The phone has no "Where things stand" in the app** (page 19). The canvas's phone boards don't have it there either.
  The landing page shows it.
- **The canvass window's lower bound is loose** (backend 25). It's harmless, since a real canvass can't come earlier.
- **Manor's and Pflugerville's majority rules are unverified** (backend, legal). This isn't a code defect; the map
  already flags them. It's listed in #155's follow-ups for Lane.

## Status (Oct 21, evening)

Fixed on `results-build`, each with a test that fails without the fix (checked against the code before it) and,
for the back end, a mutant in `tests/mutate_backend.py`:

| Issue | Fix | Commits |
|---|---|---|
| #152 Nothing posted before the polls close is a result | `POLLS_CLOSE` cutoff in the workflow's build | 3ea9994 |
| #153 One bad input stops everything | per-file and per-contest holds listed in the PR; `rejected/`; the kill switch read first; a pause ledger | 297a277, 12bc6f0 |
| #154 Exclusions and corrections | roll back quietly; "Corrected" only when the published numbers came from the excluded file and now differ | c010cba, eebd25d |
| #155 Counties with no file (ACC) | `official.json` `counted`, with the canvass's own time (W106) | 899d3a0, 2276962 |
| #156 "Last unofficial count" never cleared | per county: Hays's "Official" PDF, or `official.json` `final` | 899d3a0 |
| #157 County Clerk write-in | declared write-in, and the unopposed rule both ways | 8dd8402 |
| #158 Wrong keys, wrong-election files | `suggest` ranked by title; county keys carry their names; files dated other than Nov 3 refused | 899d3a0, 8130ff7 |
| #159 Workflows | `--match-head-commit`; main-moved check; results-only patch; publish recomputes the verdict check; hashed pins; Pages copies only the demo page | 2276962 |
| #160 Numbers held behind a verdict | Lane: one PR stays; the PR says when numbers wait | da7b4bd |
| #161 Fetching | retries; never fails the run; "Sources this run" in the PR; the SOS clock check; election date | 2276962 |
| #162 Hand edits to the map; runbook | map compared as JSON, registrations kept; runbook steps 3, 9, 10, 11, 12, 13; schedule to Dec 20 | 2276962 |
| #163 Parsers | Hays's columns; empty Williamson contests; the canvass report's own label (W107); a general election's canvass report, which found the SOS's Green codes | 2276962, 3e5791d |
| #164 A page left open past midnight | redraws what's dated | fa1a0cc |
| #165–#174, #176 The runoff's pages | two tabs; several runoffs; Clear (W110); printing (W109, W116); no date (W111); after and near the day (W113, W114); the phone; accessibility; layout; analytics; the rollback build | 12bc6f0, da7b4bd, 9ad56a1, f67c655 |
| #177 Small fixes | the caret; timeline order; "Since you last looked"; no call on an unofficial count (W112); past canvass dates; friend initials; rail lines; the phone's line gap | 12bc6f0, da7b4bd, 3e5791d |

Not fixed, and why:
- **#163, part:** no Bastrop Clarity fixture (Clarity refuses cloud servers, and Ballotta doesn't work around that) and no
  Nov 2024 Hays or SOS files (the SOS's API keeps only 2025–26 elections; hayscountytx.gov and results.texas-election.com
  refuse scripts). Lane can download them: `https://www.hayscountytx.gov/Archive.aspx?ADID=1601` (Hays, Nov 2024) and
  `https://results.texas-election.com/static/data/Reports/49664/OfficialCanvassReport.pdf` (the state's, Nov 2024).
- **#169, paused results hide the runoff's pages:** argued down. The kill switch hides every result by design, and a
  runoff's pages are built from results that may be the wrong ones; the voter's runoff picks are kept and come back.
- **#172, part:** the paper's screen-reader name on the runoff's pages, and a note that Share and Keep carry Nov 3's
  picks only (with #180, runoff sharing, which Lane chose to build later).
- **#173, part:** the runoff's Nov 3 box differs from the results paper's (lowercase "official", no vote counts).
- **#175** (the Dec 12 runoff's own results), **#178** (tests), **#179** (efficiency): to come; #175 before Dec 12.

## Verification (Oct 22)

A fresh agent checked each fix against its issue's text (report kept with the session's scratch files): 2 FAIL and 9
CONCERN findings. Each is fixed below with a test that fails without it, or listed for Lane.

1. **FAIL #154:** an exclusion that changed nothing kept the excluded file's time in the sources, so a later, ordinary
   update from another county read as a rollback and showed "Corrected". Now the sources say the older file, and
   `check_results` allows a time to go back when it came from an excluded file (`excluded_stamps`, shared by the build
   and the workflow's check). Mutant B59.
2. **#154:** a real correction that moved no verdict said "Numbers only: this merges itself". It now waits for Lane with
   its own line ("marked Corrected …"). Mutant B60.
3. **FAIL #155:** pre-filled `absent` keys and the known small registrations weren't done. Researched Oct 22 (the
   City's district map over the county lines, checked against its Nov 2025 canvass; ACC's order and past results):
   Austin Districts 1, 3, 5 and 9 are Travis alone (their electorate now says so, so they're never "partial,
   Williamson missing"); District 8 is Travis and Hays's precinct 438 (565 registered); ACC's Lee part is Elgin ISD's
   corner (200, an upper bound; was the whole county's 12,262). Caldwell stays the whole county's: since Lockhart ISD
   joined ACC in Nov 2024, most of it is ACC's. Still for Nov 4: ACC's annexation (c120) is held in Travis only per its
   notice, while the map also lists Williamson; set its Williamson key to "absent" if Williamson's file lacks it.
4. **#153:** the runbook's manual restore ("revert") republished a lower seq, which open pages ignore by design, so they
   stayed paused. The runbook now restores at N + 1, and the page redraws when `withdrawn` changes at the same seq. The
   HELD line says "(not shown yet)" for a contest never published.
5. **#158:** a statewide race's Travis key typed as a bare number held the whole race. Now only its Travis breakdown
   waits (HELD), and `suggest` prints those keys too ("Travis breakdown"). Mutant B61.
6. **#162:** a hand-set `registered` on a contest the tables cover failed the run. A hand entry now wins, county by
   county. The plan's Risks section matches the code.
7. **#177:** the summary still counted an unofficial runoff pick outside the pair as "didn't win". Now "behind", as
   W112's "so far".
8. **#157:** the declared write-in's name, LaShawn Nash (from Ballotpedia), was unconfirmed. **Confirmed by Lane, Oct 22:**
   LaShawn Nash, independent (https://lashawnnash.org/).
9. **#161:** the time-zone check caught one direction only. A feed that reads as last updated before the polls closed,
   while the state's server is three or more hours past closing, is now refused and reported. Mutant B58.
10. **#166:** with runoffs on two dates, the band gave each race the first's. On Decide it now gives the open race's own
    date (Where to vote and Print show the soonest).
11. **#164:** the guards for a key or click in the minute before the page notices the new day had no test. Now tested,
    and the test fails with them removed.

Also from the verification: Williamson's page prints no election date, and its vendor restamps old pages, so the
polls-close cutoff doesn't protect it; the name carried in each county key (#158) does.

Correction (Oct 22): the Green codes (GRE, G) left a party code on a candidate's name in the state's canvass report,
but the build's name matching still matched it (one name fits), so that race would not have been held, as first said.
The parser fix stands, and the test now compares names exactly. The mutation runs then found two weak tests (B34, a
canvass with a county's counts not yet in; B57, the Green codes); both are tightened, and every mutant is killed:
back end 61 of 61, page 130 of 130.
