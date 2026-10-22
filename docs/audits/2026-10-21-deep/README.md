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
