# Election results: the inputs

How results reach the ballot is in `docs/plans/2026-10-20-results.md`; the daily steps are in `docs/RUNBOOK.md`
("Results days"). This folder holds every input, on the branch `results/next`:

- `inbox/travis/`, `inbox/bastrop/`: Lane's downloads (Clarity's `detailxml.zip`, as downloaded). Upload into the
  county's own folder: the build reads the county from inside the file and refuses one in the wrong folder.
  `inbox/williamson/` and `inbox/hays/` are only for a hand download if their fetch fails.
- `rejected/<county>/`: a file the build couldn't use (not a results file, the wrong county, another election), with
  a `.why.txt` beside it. The pull request lists each one until it's deleted.
- `raw/<source>/<posted time>-<hash>/`: every file, as fetched or downloaded, filed by the time posted inside it.
  Never edited or deleted; a bad file goes in `excluded.json`.
- `excluded.json`: `[{"path": "raw/...", "reason": "...", "date": "YYYY-MM-DD", "contests": ["c071"]}]`. A
  published contest that read from it, and reads differently without it, is marked corrected on that date.
- `official.json`: the canvasses, written by hand as each body canvasses:
  - `"canvasses": {"city-of-austin": {"canvassed": "2026-11-12", "link": "https://..."}}`: the slug is the map's
    canvasser; `"expected": "YYYY-MM-DD"` before the meeting (the "official by" line); `"recount": {"link": "https://..."}`.
  - `"runoffs": {"c069": "2026-12-12"}`: a runoff's date, once set.
  - `"withdrawn": true`: the kill switch. Hides every result at once.
  - `"counted": {"c117": {"lee": {"at": "2026-11-18T10:00", "votes": {"Jane Doe": 120, ...}}}}`: a county that
    posts no file Ballotta reads (ACC's Caldwell and Lee), counted from the canvass record, with the canvass's date
    and time; used once that contest is canvassed.
  - `"final": {"travis": "YYYY-MM-DD"}`: the date of a county's final file, when it's posted before the canvass.
  - `"late_until"`: the last day late ballots are counted, if it ever differs from the map's `meta.late_until`
    (2026-11-17).
