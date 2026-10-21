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
