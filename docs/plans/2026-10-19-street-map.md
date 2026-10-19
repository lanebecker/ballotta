# Ballotta: the street map — build plan

*Written Oct 19, 2026 for Lane. Status: **approved by Lane (Oct 19, 1:25 pm): every recommendation below, and the
build tonight, Oct 19**, with the preview (1.2.1) pushed late in the evening. (He had first said to hold implementation
until early-voting traffic died down; on reading the plan he chose tonight.) Every script and code change below was dry-run on throwaway copies of the repo
on Oct 19 (results in "Dry run"); the find/replace edits in the tasks were generated from those copies and checked to
rebuild them byte for byte from today's files (`22ff484`, v1.2.0).*

## The request (verbatim)

> "What would it take to add actual map tiles to the mapping page?"

Three routes were offered (a hosted tile service, self-hosted tiles, or real streets drawn into today's map). Lane:

> "Option 3 makes sense to me and seems simplest and least privacy-invasive. Am I right about that? If so, yes please
> mock it up"

The mockup ("Ballotta Street Map Mockup", https://claude.ai/artifact/K3f5g6TLAYnLbCyL5cuDJb) drew Census streets and
water under the dots for five sample spots. Lane:

> "This looks perfect, but I'd like to work on this prior to wave 2. Can we build an implementation plan, in
> anticipation of publishing at /next/ before we move it onto the main site? I think the planning can happen now,
> yes, even though we want to hold off on implementation until site activity has died down?"

## Decisions for Lane (before Task 1)

**Lane's answers (Oct 19, 1:25 pm):** 1, data in the page; 2, ship the preview late in the evening; 3, keep all the
differences from the mockup; 4, yes; 5, the credit as written; 6, tonight, Oct 19.

1. **Page weight (recommended: data in the page).** The street data covers every view any Travis County address can
   produce, including the widened maps of far-out addresses, so it is bigger than the mockup's: **160 KB, 57 KB
   compressed**. Inside the page, the compressed page goes from about 109 KB to about 172 KB (measured), and the map
   works offline with no new moving parts. The alternative is a separate `streets.json` fetched from ballotta.org only when the map is
   drawn: the page stays as it is for people who never open the map, but the map then has a loading state, a fallback
   (today's grid) when the fetch fails, a redraw when it arrives, and one more file for the offline copy to keep. The
   plan below is written for **data in the page**; say if you want the other.
2. **The "newer Ballotta" bar (recommended: ship the preview in a quiet hour).** The preview is a release (1.2.1)
   because `next/` is a published file, and every release makes pages left open show "A newer Ballotta is available",
   even though ballotta.org itself doesn't change in 1.2.1. Promotion (1.3.0) shows it again, that time for a real
   change. Shipping 1.2.1 late in the evening keeps the reload prompt away from most voters.
3. **Differences from the mockup** (the mockup was the look; these came out of the dry run):
   1. **Coverage:** major streets from Travis, Williamson and Hays counties near Travis; water from twelve counties
      (Travis, Williamson, Hays, Bastrop, Burnet, Blanco, Caldwell, Llano, Lee, Comal, Guadalupe, Fayette), so a
      widened map never ends at the county line.
   2. **Major streets** are the 160 longest-running named streets near the county plus in-town streets the mockup
      missed (Oltorf, Koenig, 38th, 45th, Cesar Chavez, Riverside, MLK, 7th, 11th, 12th, Manor, Rundberg, Stassney…):
      186 names, an east and a west half counted separately. The longest-running ones include about 30 Williamson and
      Hays county roads and about 40 farm-to-market and ranch roads, which is what the outskirts have. A widened map
      (more than 0.6° across, only far-out addresses in early voting) shows highways only.
   3. **Highway labels** (I-35, MoPac, 183, 290, 71, Ben White, 45, 130, 360, Lamar, Congress, in that order of
      priority) never touch you, a vote center, a town name or each other, and always sit wholly on the map; a highway
      with no such place in view gets no label. They are 12 px on a phone and 10 px on a laptop, a little smaller than
      the town names (13 and 11).
   4. **Town names** that a vote center would cover move just above or below it, or are left out. Today's map has
      this problem too ("UT campus", "Lakeway" under dots); the fix reaches ballotta.org at promotion.
   5. **Search engines:** the preview carries `noindex`, so only ballotta.org is listed.
   6. **A preview left open** asks the root `version.json` for newer releases (the old preview asked `next/version.json`,
      which doesn't exist; it never mattered while the preview was short-lived).
4. **The main page's offline copy and `next/`.** Today the offline copy on every phone fetches `next/` (the 1 KB
   hand-off page) when it installs, so Home Screen apps from the old preview open offline. While `next/` is the
   600 KB preview, that would cost every new phone visitor 172 KB they never use, in the middle of early voting. So
   while the street map is in preview, the main copy doesn't fetch `next/`, and drops the hand-off page it kept before
   (otherwise a Home Screen app from the old preview, opened offline, would show that page and be sent on); promotion
   puts it back, byte for byte today's `sw.js`. Changing `sw.js`
   makes each phone's offline copy update itself once at 1.2.1 and once at 1.3.0, quietly (the offline copy is
   network first, so nobody sees it).
5. **Wording** (visitor-facing words go to Lane before they ship): the credit added under About this test, "Streets
   and water on the map: U.S. Census Bureau TIGER/Line, 2024."; the map's caption stays as it is today ("Drawn on your
   device from the county’s list; no map company sees where you live. …"), which stays true.
6. **When.** About half a day of work plus about an hour and a half of test runs, then your look at the preview on
   your phone and laptop, then promotion (an hour). Pick a quiet day before Oct 26.

## What "done" looks like

1. **ballotta.org/next/** shows the street map on laptops and phones (Where to vote, and the map fold on a phone), and
   is otherwise the main page exactly: same picks, same storage, `[Preview]` in the title, counting nothing.
2. **ballotta.org is unchanged** until promotion: before the version bump, the rebuilt `index.html` is byte-for-byte
   the one live today (Task 5), and no street code or data is in it (a test).
3. **Nothing new leaves the phone:** drawing the map makes no request at all (a test counts them), the caption's
   promise stands as written, and the map works offline (the data is part of the page).
4. **Credited:** "Streets and water on the map: U.S. Census Bureau TIGER/Line, 2024." in About this test (preview, then
   live); README data sources.
5. **Tested:** a browser test and a build test in `tests/test_site.py`, a pipeline test, 28 mutants all killed; the full browser suite green against both
   `index.html` and `next/index.html`.
6. **After Lane's OK:** promotion (Task 9) puts it on ballotta.org as 1.3.0, and `next/` sends people on again.

## How it's built (and why ballotta.org can't change by accident)

- **Markers, as the two layouts had.** Everything new is inside `/*STREETS*/ … /*/STREETS*/` (CSS, JS) or
  `<!--STREETS--> … <!--/STREETS-->` (HTML): whole-line blocks, or a pair inside one line. `source/build_site.py` gets
  `STREETS_LIVE = False` and a `streets` switch on `build()` (default: on for the preview, or once `STREETS_LIVE`;
  never without the laptop layout, whose code draws the map). The main build strips every STREETS block with the same
  stripper (and the same refusals for malformed markers) as DESK and PHONE. The strip runs **before** the phone
  layout's `if/else`, never between them: the dry run's first draft put it between, and the main page silently lost
  its `next/` clean-up line (mutant S21 now guards this).
- **`next/` becomes a preview again.** Since the phone layout's promotion (Oct 17), the main build writes `next/` as a
  page that sends people on. With `STREETS_LIVE = False` it writes the preview instead, as it did before Oct 17:
  `next/index.html` is `build(preview=True)` (the main page with the street map on, `[Preview]` title, a tracker that
  never sends, `../` paths, and now `noindex`) and `next/sw.js` is the preview's own offline copy (`ballotta-next-1`).
  Promotion flips it back with no new code: the existing hand-off page and self-removing worker, already tested by
  `promotion_hands_the_preview_on`. Home Screen apps added from the Oct 15–17 preview open the preview again until
  then.
- **The main page's offline copy** fetches `./`, `next/` and `picks/` when it installs. While `next/` is the preview
  (600 KB) it fetches only `./` and `picks/`, so no phone downloads the preview unasked (decision 4), and its install
  first deletes a kept `next/` (the old hand-off page); promotion restores `next/`, which Home Screen apps from a
  preview need offline, and today's `sw.js` exactly. Mutant W3f in `tests/mutate_desk.py` is re-anchored so it
  holds in both states.
- **The data.** `source/fetch_streets.py` (new; needs `pyshp` and `shapely`, pinned in `requirements.txt`, used by
  nothing else) downloads the Census Bureau's TIGER/Line 2024 shapefiles (public domain: no license terms, no
  attribution required, credited anyway), joins, clips and simplifies the lines for a map about 560 px across, and
  writes `source/data/streets.json`: freeways, highways, major streets and lake outlines as integer deltas in 1/10000
  degree, plus label places along each named highway. The same files and the same shapely give the same bytes (checked
  twice in the dry run); it stops rather than write a partial or oversized file (cap 180,000 bytes). The build and CI
  never need shapely: they read the committed JSON.
- **Into the page.** The build replaces `__STREETS__` (inside a STREETS block, so it exists only when the street map is
  on) with the JSON, compact (spaces would add a third), before the main `__DATA__`. The page decodes the lines once,
  then at each draw keeps only lines whose box reaches the view and draws water, major streets (unless widened),
  highways and freeways under everything else, in place of the grid lines.
- **Labels.** Boxes in map pixels: you, every vote center, the town names' final positions, then each highway label in
  priority order at its place nearest your address whose box is wholly on the map and touches nothing already placed.
  Town names get a halo (a stroke in the background colour) so they read over streets.
- **Speed.** On a phone-speed CPU (Chromium at 6x slowdown) the first Where to vote view takes about 100 ms instead of
  50 ms (the one-time decode); later views about 55 ms instead of 20 ms.

## Dry run (Oct 19)

On throwaway copies of the repo at `22ff484` (never the real clone), Oct 19:

- **The data:** `fetch_streets.py` ran twice from the same downloaded files and wrote the same bytes (160 KB, 57 KB
  compressed, sha256 `24366d86…cd51fa`). The first try stopped, as it should, on three hand-picked names that aren't
  local streets in the Census files ("W Oltorf St" is spelled "Oltorf St W"; "E Koenig Ln" and "S Lamar Blvd" are
  highways there) and then on its size cap (236 KB, from full-detail lakes in all twelve counties); far-away water is
  now big lakes only, at a coarser outline.
- **ballotta.org unchanged:** with every change in and `VERSION` still 1.2.0, the rebuilt `index.html` was
  byte-for-byte the live one. The first draft wasn't: it put the STREETS strip between the phone layout's `if` and its
  `else`, which dropped the main page's `next/` clean-up line. Caught by comparing the bytes; fixed; mutant S21 guards
  it.
- **Drawn:** the preview's map at South Austin, downtown, Mueller, the Domain, Oak Hill and a far-northwest address,
  laptop and phone: streets, water, labels, no grid, and **no request at all** while drawing.
- **Tests:** the pipeline tests `22/22 passed` in both the preview's state and the promoted state; the whole browser suite `170/170 passed (next/index.html)` against the preview and `169/169 passed, 1 skipped (index.html)` against the main page (the skip is the street map's browser test, which needs a page with the street map); in the promoted copy, the whole suite against `index.html` passed 169 of 170: the pixel test that compares the old phone page with and without the laptop code (`desk_phone_layout_matches_live_page`) now saw the street map's credit in one of its two builds; it builds both with the street map off now, and passes in both states.
- **Mutants:** the first run killed 20 of 24. The four survivors were real gaps, now closed: no test spot crowded two
  highway labels (Oak Hill does, so it's a test spot now); one mutant was a no-op; a long label could hang off a
  phone's map edge (fixed in the code: a label must sit wholly on the map); and the "needs the laptop layout" test
  accepted any refusal. Later runs added mutants for the preview's `noindex` and `version.json` (S25, S26) and for the main offline copy (S27, S28); one more survivor (S22) showed the test matched the phone layout's refusal, which also names the laptop layout (fixed: the phone layout is off in that call). The final run on the final code: **28 of 28 killed**, and the two existing mutants whose lines moved (D64, W3f) killed too.
- **The whole suite against the preview** found three tests that assumed the site root: a preview left open asked
  `next/version.json` (a real bug in the preview build, now `../version.json`); the offline copy's cache is
  `ballotta-next-1` on the preview; share links open on the main site, so their offline test doesn't apply to the
  preview. And a pipeline test of the phone layout's rollback assumed `next/` is always the hand-off page; it now sets
  that up itself. All four are in the edits below.
- **The offline copy:** a browser reproduction installed today's offline copy on a phone-sized page, then deployed the
  preview release: the kept hand-off page at `next/` is deleted at the update, and `next/` then opens the preview
  offline; after promotion `sw.js`, `next/sw.js` and `next/index.html` are byte-for-byte today's.
- **Existing mutants:** an anchor check of `mutate_desk.py` (493) and `mutate_phone.py` (155) found one collision
  (I3, the data-escaping mutant: a second copy of its line); the street data now goes through the page's own
  `script_json`, and every anchor is found once.
- **Promotion and the release notes** (Tasks 7 and 9) were applied to a copy too: both builds, `--check`, the bump
  check, and the hand-off page at `next/` after promotion.
- **Speed:** Chromium at 6x CPU slowdown, phone size: the first Where to vote view 104 ms (51 ms today), later views
  about 55 ms (about 20 ms today); the page's load time the same.

## Verification pass (Oct 19)

An independent agent checked this plan against the repo and the dry-run copies: it applied every edit to `22ff484`
and got the dry-run files byte for byte, recomputed the numbers, and ran the cheap commands. What it caught, all fixed
above:

1. The main page's offline copy would have fetched the 600 KB preview on every new phone during early voting: now
   decision 4, with the fix in the code (Task 3), a test and mutant S27.
2. Task 9 ran the tests and pushed in one block, so red tests would still have deployed; it skipped the bump check and
   the remediation audit. Now separate, with both.
3. Task 6 let an executor leave "pre-existing" failures on `next/`; there are none (170/170). Removed.
4. The 1.2.1 CHANGELOG said 25 mutants; the count is now 28.
5. Task 0 expected a clean tree while this plan sat uncommitted, and Task 8 would have folded the plan into the
   release commit: the plan is now committed on its own in Task 0.
6. ~~The compressed page grows to about 166 KB~~: measured, about 172 KB.
7. Task 10's "revert the preview's commit" would have put VERSION back to 1.2.0, which the bump check refuses: now
   the RUNBOOK's steps.
8. Task 1 pointed at the street-name snippet in the wrong section.
9. Task 1 used `sha256sum` (not on a Mac) and `curl` without `-f` (an HTTP error page would be saved as a .zip).
10. Task 5 said `git diff --stat`, which doesn't show new files: now `git status --short`.
11. Wording: label sizes against the town names', "about 190" streets (186, with what they are), "two browser tests"
    (one browser test and one build test), and a stale comment about `next/manifest.webmanifest` (fixed in Task 3).
12. The suite results were rerun on the final code (above).

Then a narrow second pass over that rework (the remediation audit's Pass 2) found, all fixed above:

13. A phone whose offline copy already kept the old hand-off page would still hold it after 1.2.1 (same cache name, so
    nothing was deleted): reproduced in a browser. The install now deletes it; reproduced again, gone (mutant S28).
14. The build test would break on a phone-layout rollback or with `OFFLINE = False`: it now sets the phone layout on and
    checks the offline copy's lists only when there is one.
15. Nothing pinned the preview's own worker's list (`['./']`): now asserted.
16. A comment about the main page asking `next/sw.js` to update was untrue while a preview is up: reworded.
17. The promoted copy's full suite: the pixel-parity test for the old phone page saw the street map's credit (it is
    on by default once promoted); that test now builds both pages with the street map off.
18. On the promoted copy the street-map mutants killed 22 of 28. Five survivors (S17, S18, S20, S27, S28) mutate code
    that runs only while the street map is in preview; the runner leaves them out once it is live.

A third narrow pass over that last rework (the audit's stopping rule: the second pass forced a real code change) found:

19. ~~S21 is preview-only~~: it still matters after promotion, for a phone-layout rollback built with the street map on
    (reproduced: that build fails under S21), and the parity-test change had removed its only check. The build test now
    builds that page in the promoted state, kills S21 there, and S21 stays in the list: Task 9 expects 23 of 23.
20. The runner read `STREETS_LIVE` with a fragile string match; it now parses the one assignment and stops if there
    isn't exactly one.
21. Accepted, not changed: the parity test no longer compares a phone-layout rollback page with the street map's
    credit on (the credit is the one intended difference; the real promoted page at phone width is covered by the
    street-map test); and a Home Screen app from the Oct 15–17 preview whose worker already removed itself opens
    `next/` offline only after one online visit.

## Base and preflight

The plan was generated against `22ff484` (v1.2.0). If `main` has moved on (Wave 2 fixes, say), every edit's "Find"
text must still occur exactly once; if one doesn't, that file changed since Oct 19: stop, re-derive that one edit by
hand from its "Replace it with" text (which shows the intended result), and say so in the commit message.

## Task 0: preflight

From the repo root:

```
git fetch origin --tags && git status -sb && git log --oneline -1 && git log --oneline -1 origin/main && git tag -l 'v1.2.*'
```

Expected: `## main...origin/main`, the two `git log` lines identical, the tags `v1.2.0` (and any later ones; the
bump check needs them), and nothing listed except, if this plan isn't
committed yet, `?? docs/plans/2026-10-19-street-map.md`. In that case commit it on its own first (docs aren't
published, so no VERSION bump; the bump check passes):

```
git add docs/plans/2026-10-19-street-map.md && git commit -m "Plan: the street map (preview at next/, then promotion)" && git push origin main
```

Then the baseline, which later tasks compare with:

```
cp index.html /tmp/index.before.html && python3 source/build_site.py --check && python3 tests/test_pipeline.py | tail -1
```

Expected: `build check: every output matches the build, and both rollback builds pass` and `21/21 passed (pipeline)`
(more if tests were added since Oct 19: note the number). Done when both say so.

## Task 1: the street data

**Files:** `requirements.txt` (edit), `source/fetch_streets.py` (new), `source/data/streets.json` (new, generated).

**Edit R1** (`requirements.txt`). Find, exactly once:

````text
pypdf==5.9.0             # tests/test_site.py: the crib sheet's printed PDF
````

Replace it with:

````text
pypdf==5.9.0             # tests/test_site.py: the crib sheet's printed PDF
pyshp==3.1.6             # source/fetch_streets.py only: reads the Census TIGER/Line shapefiles for the street map
shapely==2.2.0           # source/fetch_streets.py only: joins, cuts and simplifies their lines (same version, same bytes)
````


Create `source/fetch_streets.py` with exactly this content:

````python
"""The street layer under the vote-center map (Lane, Oct 19): freeways, highways, major streets and water, from the
U.S. Census Bureau's TIGER/Line 2024 shapefiles (public domain), simplified for a map about 560 px across.

    python3 source/fetch_streets.py              # downloads the shapefiles, writes source/data/streets.json
    python3 source/fetch_streets.py --raw DIR    # the same from zips already in DIR (named as the Census names them)
    python3 source/fetch_streets.py --out FILE   # writes FILE instead (to compare a rerun with the committed file)

Only this script needs pyshp and shapely (requirements.txt); the site build and CI read the committed JSON. The same
files and the same shapely (GEOS) give the same bytes. It stops rather than write a partial or oversized answer.

Format of streets.json (read by the page's streetLayer(), template-travis.html):
  {"v": 1, "q": 10000,
   "fwy": [line, …], "hwy": [line, …], "art": [line, …], "water": [ring, …],
   "tags": [[label, x, y], …], "order": [label, …]}
  line / ring: [x0, y0, dx1, dy1, dx2, dy2, …] in 1/10000 degree: x = round(longitude * 10000), y = round(latitude *
  10000); each later point is the one before plus (dx, dy). A ring is a water body's outline (islands not cut out).
  tags: places along each named highway, about 3 km apart, where the page may put that highway's label.
  order: the highway labels, most useful first: the page places them in this order, so I-35 wins a crowded corner.
"""
import collections, io, json, pathlib, re, sys, urllib.request, zipfile

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "data/streets.json"
TIGER = "https://www2.census.gov/geo/tiger/TIGER2024/"
Q = 10000
# Every map view a Travis County address can produce (measured Oct 19 over a 41 x 41 grid of the county's bounding box,
# both voting periods: lon -98.624 … -96.924, lat 29.661 … 30.985), with a margin.
VIEW = (-98.70, 29.60, -96.85, 31.05)
# Major streets: the county and its two neighbours' streets near the county, where close-in views (0.12° across) reach.
NEAR = (-98.30, 29.90, -97.25, 30.75)
ROAD_COUNTIES = ("48453", "48491", "48209")                       # Travis, Williamson, Hays
WATER_COUNTIES = ("48453", "48491", "48209", "48021", "48053", "48031", "48055", "48299", "48287", "48091", "48187", "48149")
# Travis, Williamson, Hays, Bastrop, Burnet, Blanco, Caldwell, Llano, Lee, Comal, Guadalupe, Fayette
LONGEST = 160                                                     # the longest-running named streets near the county …
ALSO = ("E Oltorf St", "Oltorf St W", "W Koenig Ln", "W 38th St", "E 38th St", "W 45th St", "E 45th St",
        "W Cesar Chavez St", "E Cesar Chavez St", "Barton Springs Rd", "E Riverside Dr", "W Riverside Dr", "Enfield Rd",
        "E Martin Luther King Jr Blvd", "W Martin Luther King Jr Blvd", "E 7th St", "E 11th St", "E 12th St",
        "Manor Rd", "Springdale Rd", "Montopolis Dr", "Duval St", "W Anderson Ln", "E Rundberg Ln", "W Rundberg Ln",
        "E Stassney Ln", "W Stassney Ln", "S Congress Ave", "Congress Ave", "N Lamar Blvd")   # … and these in town
TOL = 0.00012                    # simplification, in degrees: about half a pixel at the usual 0.12° view
MIN_LEN = 0.002                  # pieces shorter than this (about 200 m) are dropped
MIN_WATER = 150000               # square metres: in Travis County, lakes and the river, not ponds;
MIN_WATER_AWAY = 1000000          # beyond it, where only widened views reach, the big lakes only
WATER_TOL = 0.00025              # lake outlines: about one pixel at the usual view
TAGS = [("I-35", r"^(N |S )?I- ?35\b"), ("MoPac", r"Mo-? ?[Pp]ac|^State Loop 1$"), ("183", r"US Hwy 183|^Research Blvd|^S Hwy 183"),
        ("290", r"US Hwy 290|^W Hwy 290"), ("71", r"State Hwy 71|^Bastrop Hwy|^Hwy 71|^W Hwy 71"), ("Ben White", r"Ben White Blvd"),
        ("45", r"^State Hwy 45\b"), ("130", r"^State Hwy 130\b"), ("360", r"Capital of Texas Hwy|Loop 360"),
        ("Lamar", r"^(N|S) Lamar Blvd$"), ("Congress", r"Congress Ave")]
TAG_EVERY = 0.03                 # degrees between a highway's tag places
MAX_BYTES = 180_000


def need():
    try:
        import shapefile, shapely  # noqa: F401
    except ImportError:
        sys.exit("needs pyshp and shapely: pip install -r requirements.txt")


def zips(raw):
    names = (["PRISECROADS/tl_2024_48_prisecroads.zip"] + [f"ROADS/tl_2024_{c}_roads.zip" for c in ROAD_COUNTIES]
             + [f"AREAWATER/tl_2024_{c}_areawater.zip" for c in WATER_COUNTIES])
    out = {}
    for n in names:
        base = n.split("/")[1]
        if raw:
            p = pathlib.Path(raw) / base
            if not p.is_file(): sys.exit(f"{p} is missing: nothing written")
            out[base] = p.read_bytes()
        else:
            with urllib.request.urlopen(TIGER + n, timeout=300) as r:
                out[base] = r.read()
        zipfile.ZipFile(io.BytesIO(out[base])).testzip()          # a cut-off download stops here
    return out


def records(data, base):
    import shapefile
    r = shapefile.Reader(**{k: io.BytesIO(zipfile.ZipFile(io.BytesIO(data[base])).read(base[:-4] + "." + k))
                                      for k in ("shp", "shx", "dbf")})
    for sr in r.iterShapeRecords():
        yield sr.record.as_dict(), sr.shape


def lines_of(g):
    if g.is_empty: return []
    if g.geom_type == "LineString": return [g]
    return [x for part in getattr(g, "geoms", []) for x in lines_of(part)]


def polygons_of(g):
    if g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [x for part in getattr(g, "geoms", []) for x in polygons_of(part)]


def merged(segments, box):
    from shapely.geometry import LineString
    from shapely.ops import linemerge, unary_union
    if not segments: return []
    g = linemerge(unary_union([LineString(s) for s in segments if len(s) > 1]).intersection(box))
    return [l.simplify(TOL) for l in lines_of(g) if l.length >= MIN_LEN]


def encode(coords):
    """[(lon, lat), …] -> [x0, y0, dx, dy, …] in 1/Q degree, dropping points that round onto the one before."""
    pts = [(round(x * Q), round(y * Q)) for x, y in coords]
    out = list(pts[0])
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if (x1, y1) != (x0, y0): out += [x1 - x0, y1 - y0]
    return out if len(out) >= 4 else None


def layer(geoms):
    enc = [e for e in (encode(list(g.coords)) for g in geoms) if e]
    return sorted(enc, key=lambda a: (a[0], a[1], len(a), a))   # a fixed order: the same input gives the same bytes


def build(data):
    from shapely.geometry import LineString, Polygon, box
    from shapely.ops import unary_union
    view, near = box(*VIEW), box(*NEAR)
    tiers, named = collections.defaultdict(list), collections.defaultdict(list)
    for rec, sh in records(data, "tl_2024_48_prisecroads.zip"):
        if sh.points and view.intersects(box(*sh.bbox)):
            tiers[rec["MTFCC"]].append(sh.points); named[rec["FULLNAME"] or ""].append(sh.points)
    if not tiers["S1100"] or not tiers["S1200"]: sys.exit("no freeways or highways in the view: nothing written")
    streets, length = collections.defaultdict(list), collections.Counter()
    for c in ROAD_COUNTIES:
        for rec, sh in records(data, f"tl_2024_{c}_roads.zip"):
            if rec["MTFCC"] != "S1400" or not rec["FULLNAME"] or len(sh.points) < 2 or not near.intersects(box(*sh.bbox)): continue
            streets[rec["FULLNAME"]].append(sh.points); length[rec["FULLNAME"]] += LineString(sh.points).intersection(near).length
    missing = [n for n in ALSO if n not in streets]
    if missing: sys.exit(f"streets not in the Census files: {missing}: nothing written")
    picked = sorted({n for n, _ in sorted(length.items(), key=lambda kv: (-kv[1], kv[0]))[:LONGEST]} | set(ALSO))
    water = []
    for c in WATER_COUNTIES:
        for rec, sh in records(data, f"tl_2024_{c}_areawater.zip"):
            if rec["AWATER"] < (MIN_WATER if c == "48453" else MIN_WATER_AWAY): continue
            ends = list(sh.parts) + [len(sh.points)]
            rings = [sh.points[a:b] for a, b in zip(ends, ends[1:])]
            water.append(Polygon(rings[0], rings[1:]).buffer(0))
    w = unary_union(water).intersection(view)
    polys = [p for p in polygons_of(w) if p.area > 1e-5]
    if not polys: sys.exit("no water in the view: nothing written")
    rings = [LineString(p.simplify(WATER_TOL).exterior.coords) for p in polys]
    tags = []
    for label, rx in TAGS:
        segs = [s for n, ss in named.items() if re.search(rx, n) for s in ss]
        for l in merged(segs, view):
            k = 0.0
            while k < l.length:
                p = l.interpolate(k); tags.append([label, round(p.x * Q), round(p.y * Q)]); k += TAG_EVERY
    if {t[0] for t in tags} != {t[0] for t in TAGS}: sys.exit(f"highways with no tag place: {sorted({t[0] for t in TAGS} - {t[0] for t in tags})}")
    return {"v": 1, "q": Q, "fwy": layer(merged(tiers["S1100"], view)), "hwy": layer(merged(tiers["S1200"], view)),
            "art": layer(merged([s for n in picked for s in streets[n]], near)), "water": layer(rings), "tags": sorted(tags),
            "order": [label for label, _ in TAGS]}


def main():
    need()
    raw = sys.argv[sys.argv.index("--raw") + 1] if "--raw" in sys.argv[1:] else None
    out = OUT
    if "--out" in sys.argv[1:]: out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
    text = json.dumps(build(zips(raw)), separators=(",", ":")) + "\n"
    if len(text) > MAX_BYTES: sys.exit(f"{len(text)} bytes is more than MAX_BYTES ({MAX_BYTES}): nothing written")
    out.parent.mkdir(exist_ok=True)
    out.write_text(text, encoding="utf-8")
    d = json.loads(text)
    print(out, len(text) // 1024, "KB:", ", ".join(f"{k} {len(d[k])}" for k in ("fwy", "hwy", "art", "water", "tags")))


if __name__ == "__main__":
    main()
````

Install the two libraries (the versions pinned above; another shapely can give different bytes, which is harmless but
makes the fingerprint below differ), download the Census files once, and run the script twice from them:

```
python3 -m pip install --break-system-packages pyshp==3.1.6 shapely==2.2.0
mkdir -p /tmp/tiger && cd /tmp/tiger && for f in PRISECROADS/tl_2024_48_prisecroads ROADS/tl_2024_48453_roads ROADS/tl_2024_48491_roads ROADS/tl_2024_48209_roads AREAWATER/tl_2024_48453_areawater AREAWATER/tl_2024_48491_areawater AREAWATER/tl_2024_48209_areawater AREAWATER/tl_2024_48021_areawater AREAWATER/tl_2024_48053_areawater AREAWATER/tl_2024_48031_areawater AREAWATER/tl_2024_48055_areawater AREAWATER/tl_2024_48299_areawater AREAWATER/tl_2024_48287_areawater AREAWATER/tl_2024_48091_areawater AREAWATER/tl_2024_48187_areawater AREAWATER/tl_2024_48149_areawater; do curl -fsS -m 300 -O "https://www2.census.gov/geo/tiger/TIGER2024/$f.zip" || echo "FAILED $f"; done; cd -
python3 source/fetch_streets.py --raw /tmp/tiger && python3 source/fetch_streets.py --raw /tmp/tiger --out /tmp/streets.again.json && cmp source/data/streets.json /tmp/streets.again.json && shasum -a 256 source/data/streets.json
```

Expected: no `FAILED` line (`-f` makes curl fail on an HTTP error instead of saving the error page); then

```
…/source/data/streets.json 160 KB: fwy 126, hwy 339, art 772, water 12, tags 657
/tmp/streets.again.json 160 KB: fwy 126, hwy 339, art 772, water 12, tags 657
24366d86854b252d27be43c784d5b72d5900f434664c8af6bbb1223df9cd51fa  source/data/streets.json
```

`cmp` prints nothing (the two runs agree). A different fingerprint with the same counts means a different shapely
build: fine, carry on. Different counts mean the Census changed its 2024 files: look at a map (Task 4's check) before
going on. If the script stops with "streets not in the Census files", a name in `ALSO` changed spelling: find the new
spelling with the snippet in "Appendix: checking a street name" and fix `ALSO`.

## Task 2: the tests (written before the code)

**Files:** `tests/test_site.py`, `tests/test_pipeline.py`, `tests/mutate_desk.py` (edits), `tests/mutate_streets.py` (new).

**Edit TS1** (`tests/test_site.py`). Find, exactly once:

````python
HAS_PHONE = 'id="ph-bar"' in (ROOT / PAGE).read_text(encoding='utf-8')
if not HAS_DESK and "location.replace(new URL('../'" in (ROOT / PAGE).read_text(encoding='utf-8'):   # promotion audit #5
````

Replace it with:

````python
HAS_PHONE = 'id="ph-bar"' in (ROOT / PAGE).read_text(encoding='utf-8')
HAS_STREETS = '.dk-map .st-wat{' in (ROOT / PAGE).read_text(encoding='utf-8')   # the street map (next/ until STREETS_LIVE)
if not HAS_DESK and "location.replace(new URL('../'" in (ROOT / PAGE).read_text(encoding='utf-8'):   # promotion audit #5
````

**Edit TS2** (`tests/test_site.py`). Find, exactly once:

````python
def phone_test(fn): TESTS.append(fn); PHONE_TESTS.add(fn.__name__); return fn

````

Replace it with:

````python
def phone_test(fn): TESTS.append(fn); PHONE_TESTS.add(fn.__name__); return fn
STREETS_TESTS = set()                                          # run only where the page has the street map (Lane, Oct 19)
def streets_test(fn): TESTS.append(fn); STREETS_TESTS.add(fn.__name__); return fn

````

**Edit TS3** (`tests/test_site.py`). Find, exactly once:

````python
    for name, desk in (('_parity_plain.html', False), ('_parity_desk.html', True)):              # served from memory: nothing is written (Pass 1)
        html = m.build(desk=desk, phone=False)                                                  # the old phone page, as a rollback would bring it back
        ctx, pg = new_page(b); ctx.route(f'**/{name}', (lambda h: lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=h))(html))
````

Replace it with:

````python
    for name, desk in (('_parity_plain.html', False), ('_parity_desk.html', True)):              # served from memory: nothing is written (Pass 1)
        html = m.build(desk=desk, phone=False, streets=False)                                   # the old phone page, as a rollback would bring it back
                                                                                                # (the street map, Oct 19, has its own credit: off in both)
        ctx, pg = new_page(b); ctx.route(f'**/{name}', (lambda h: lambda r: r.fulfill(status=200, content_type='text/html; charset=utf-8', body=h))(html))
````

**Edit TS4** (`tests/test_site.py`). Find, exactly once:

````python
    # 1.1.7 link (to the page itself) opened from the copy. The copy now keeps picks/ from the start, as it does the page.
    Flip.swap, Flip.gone, Flip.fail, Flip.slow, Flip.gzip = {}, set(), {}, {}, False; srv, url = own_server()
````

Replace it with:

````python
    # 1.1.7 link (to the page itself) opened from the copy. The copy now keeps picks/ from the start, as it does the page.
    if PAGE.startswith('next/'):                                         # a share link goes to the main site's picks/, which only
        return print('  (not on the preview: share links open on the main site)')   # the main page's offline copy keeps (Oct 19)
    Flip.swap, Flip.gone, Flip.fail, Flip.slow, Flip.gzip = {}, set(), {}, {}, False; srv, url = own_server()
````

**Edit TS5** (`tests/test_site.py`). Find, exactly once:

````python
    assert "'ballotta-next-1'" in on and "'ballotta-1'" in m.sw_js(False) and "startsWith('ballotta-next-')" in off and "startsWith('ballotta-')" in m.sw_off_js(False)
    m.PHONE_LIVE = True; out = m.outputs(False); m.PHONE_LIVE = False
    assert out['next/sw.js'] == m.sw_off_js(True) and out['sw.js'] == m.sw_js(False) and out['next/index.html'] == m.moved_page(), sorted(out)
    Flip.swap = {}; srv, url = own_server()
````

Replace it with:

````python
    assert "'ballotta-next-1'" in on and "'ballotta-1'" in m.sw_js(False) and "startsWith('ballotta-next-')" in off and "startsWith('ballotta-')" in m.sw_off_js(False)
    was = m.STREETS_LIVE; m.PHONE_LIVE = m.STREETS_LIVE = True; out = m.outputs(False); main_sw = m.sw_js(False); m.PHONE_LIVE, m.STREETS_LIVE = False, was   # nothing in preview (Oct 19)
    assert out['next/sw.js'] == m.sw_off_js(True) and out['sw.js'] == main_sw and out['next/index.html'] == m.moved_page(), sorted(out)
    Flip.swap = {}; srv, url = own_server()
````

**Edit TS6** (`tests/test_site.py`). Find, exactly once:

````python
    pre = m.outputs(True)
    m.PHONE_LIVE = True
    try: post = m.outputs(False)
    finally: m.PHONE_LIVE = False
    assert post['next/index.html'] == m.moved_page() and post['next/sw.js'] == m.sw_off_js(True), sorted(post)
````

Replace it with:

````python
    pre = m.outputs(True)
    was = m.STREETS_LIVE; m.PHONE_LIVE = m.STREETS_LIVE = True                              # nothing else in preview at next/ (Oct 19)
    try: post = m.outputs(False)
    finally: m.PHONE_LIVE, m.STREETS_LIVE = False, was
    assert post['next/index.html'] == m.moved_page() and post['next/sw.js'] == m.sw_off_js(True), sorted(post)
````

**Edit TS7** (`tests/test_site.py`). Find, exactly once:

````python
        pg.goto(base + 'index.html'); poll(pg, '!!navigator.serviceWorker.controller', 15); pg.reload(); pg.wait_for_timeout(500)
        keys = pg.evaluate("caches.open('ballotta-1').then(c => c.keys()).then(ks => ks.map(r => r.url))")
        assert base in keys and base + 'index.html' not in keys, keys
````

Replace it with:

````python
        pg.goto(base + 'index.html'); poll(pg, '!!navigator.serviceWorker.controller', 15); pg.reload(); pg.wait_for_timeout(500)
        mine = 'ballotta-next-1' if PAGE.startswith('next/') else 'ballotta-1'                 # the preview keeps its own (Oct 19)
        keys = pg.evaluate(f"caches.open('{mine}').then(c => c.keys()).then(ks => ks.map(r => r.url))")
        assert base in keys and base + 'index.html' not in keys, keys
````

**Edit TS8** (`tests/test_site.py`). Find, exactly once:

````python
            assert pg.evaluate("[...document.querySelectorAll('#dk-map > circle')].length") <= 15, 'downtown: the usual close-in map, not one widened to most of the county'
        ctx.close()

@phone_test
````

Replace it with:

````python
            assert pg.evaluate("[...document.querySelectorAll('#dk-map > circle')].length") <= 15, 'downtown: the usual close-in map, not one widened to most of the county'
        ctx.close()


# ---------------------------------------------------------------- the street map (Lane, Oct 19; next/ until STREETS_LIVE)
STREET_SPOTS = {'south': [-97.7745, 30.2235], 'downtown': [-97.7431, 30.2747], 'mueller': [-97.7050, 30.2980],
                'domain': [-97.7195, 30.3885], 'oakhill': [-97.84, 30.235], 'far': [-98.17, 30.62]}
# Mueller: the town name sits on you; Oak Hill: highway labels compete for one corner; far: a widened map
MAP_PROBLEMS = """(() => {
  const m = document.getElementById('dk-map'), W = 560, H = 520, bb = e => { const r = e.getBBox(); return [r.x, r.y, r.x + r.width, r.y + r.height]; };
  const hit = (a, b) => a[0] < b[2] - 0.5 && b[0] < a[2] - 0.5 && a[1] < b[3] - 0.5 && b[1] < a[3] - 0.5, out = [];
  const tags = [...m.querySelectorAll('.st-tag')].map(g => ({ n: g.textContent, r: bb(g.querySelector('rect')), t: bb(g.querySelector('text')) }));
  const dots = [...m.querySelectorAll(':scope > circle, .top circle')].map(bb), you = bb(m.querySelector(':scope > g:not(.top):not(.st-tag) rect'));
  const names = [...m.querySelectorAll(':scope > text')].map(e => ({ n: e.textContent, b: bb(e) }));
  tags.forEach((g, i) => {
    if (!(g.t[0] >= g.r[0] - 0.5 && g.t[2] <= g.r[2] + 0.5 && g.t[1] >= g.r[1] - 1.5 && g.t[3] <= g.r[3] + 1.5)) out.push('label sticks out of its tag: ' + g.n);
    if (!(g.r[0] >= 0 && g.r[2] <= W && g.r[1] >= 0 && g.r[3] <= H)) out.push('tag off the edge of the map: ' + g.n);
    if (hit(g.r, you)) out.push('tag on you: ' + g.n);
    dots.forEach(d => { if (hit(g.r, d)) out.push('tag on a vote center: ' + g.n); });
    names.forEach(t => { if (hit(g.r, t.b)) out.push('tag on a town name: ' + g.n + ' / ' + t.n); });
    tags.slice(i + 1).forEach(h => { if (hit(g.r, h.r)) out.push('two tags overlap: ' + g.n + ' / ' + h.n); });
  });
  names.forEach(t => { if (hit(t.b, you)) out.push('town name on you: ' + t.n); dots.forEach(d => { if (hit(t.b, d)) out.push('town name under a vote center: ' + t.n); }); });
  m.querySelectorAll('.st-wat, .st-rd').forEach(p => (p.getAttribute('d') || '').split('M').filter(Boolean).forEach(sub => {
    const n = sub.split(/[ L]/).map(Number), xs = n.filter((_, i) => i % 2 === 0), ys = n.filter((_, i) => i % 2 === 1);
    if (Math.max(...xs) < 0 || Math.min(...xs) > W || Math.max(...ys) < 0 || Math.min(...ys) > H) out.push('a line drawn wholly outside the map: ' + p.getAttribute('class'));
  }));
  return [...new Set(out)];
})()"""

@test
def street_map_waits_for_promotion(b):
    # Lane, Oct 19: the street map is built into the preview (next/) only, until STREETS_LIVE: the main page carries none
    # of its code or data. The preview has the data compact and the credit; promotion puts it on the main page and sends
    # next/ on again; with streets off the page is exactly the main page; the street map needs the laptop layout.
    m = build_module(); was = m.STREETS_LIVE; m.PHONE_LIVE = True                           # as promoted (a phone rollback has no next/ to check)
    live, prev = m.build(), m.build(preview=True)
    data = json.loads((ROOT / 'source/data/streets.json').read_text(encoding='utf-8'))
    assert m.strip_streets('a\n/*STREETS*/\nb\n/*/STREETS*/\nc;/*STREETS*/ d;/*/STREETS*/\n') == 'a\nc;\n'
    for bad in ('/*STREETS*/ x', 'a\n/*STREETS*/\nb\n/*/STREETS*/ }\n', 'x /*STREETS*/ y\n/*/STREETS*/\n'):
        try: m.strip_streets(bad); refused = False
        except AssertionError: refused = True
        assert refused, f'malformed STREETS markers must stop the build: {bad!r}'
    assert '.dk-map .st-wat{' in prev and 'const STREETS = ' + json.dumps(data, separators=(',', ':')) + ';' in prev, 'the preview carries the street data, compact'
    assert 'Streets and water on the map: U.S. Census Bureau TIGER/Line, 2024.' in prev, 'the credit'
    assert prev.count('<meta name="robots" content="noindex">') == 1 and 'noindex' not in live, 'search engines list the main page, never the preview'
    assert "fetch('../version.json?'" in prev and "fetch('version.json?'" in live, 'a preview left open asks the one version.json, at the root'
    assert m.build(streets=False) == (live if not was else m.build(streets=False)) and '.dk-map .st-wat{' not in m.build(streets=False) and '"fwy":' not in m.build(streets=False)
    if not was:
        assert '.dk-map .st-wat{' not in live and 'TIGER/Line' not in live and '"fwy":' not in live, 'the street map leaked into the main page'
        out = m.outputs(False)
        assert out['next/index.html'] == prev and out['next/sw.js'] == (m.sw_js(True) if m.OFFLINE else m.sw_off_js(True)), 'next/ is the preview, with its own offline copy'
        if m.OFFLINE:
            assert "['./', 'picks/'].map" in out['sw.js'], "the main page's offline copy fetches the 600 KB preview at install"
            assert "c.delete(new URL('next/', location.href).href)" in out['sw.js'], 'a hand-off page kept before would be shown for the preview'
    assert "['./'].map" in m.sw_js(True) and 'c.delete(' not in m.sw_js(True), "the preview's own copy keeps only its page"
    m.STREETS_LIVE = True
    try: post = m.outputs(False); rolled = m.build(desk=True, phone=False)        # promoted, then a phone-layout rollback: it builds, street map and all
    finally: m.STREETS_LIVE = was
    assert '.dk-map .st-wat{' in rolled and 'id="ph-bar"' not in rolled, 'a phone-layout rollback after promotion'
    assert '.dk-map .st-wat{' in post['index.html'] and post['next/index.html'] == m.moved_page() and post['next/sw.js'] == m.sw_off_js(True), 'promoted: on the main page, and next/ sends people on'
    if m.OFFLINE:
        assert "['./', 'next/', 'picks/'].map" in post['sw.js'] and 'c.delete(' not in post['sw.js'], 'promoted: the offline copy keeps the hand-off page again, for Home Screen apps from a preview'
    try: m.build(desk=False, phone=False, streets=True); refused = False                   # phone off: its own refusal names the laptop layout too
    except AssertionError as e: refused = 'street map' in str(e) and 'laptop layout' in str(e)
    assert refused, 'the street map without the laptop layout that draws it: refused, saying why'

@streets_test
def street_map_draws_streets_and_asks_nobody(b):
    # Lane, Oct 19: streets, highways and water under the dots, from data in the page: drawing the map asks nothing of
    # anyone. Labels (highway tags, town names) keep off you, the vote centers and each other; a town name a dot would
    # cover moves above or below it; a widened map shows highways only; only lines that reach the view are drawn.
    for spot, pt in STREET_SPOTS.items():
        for period in ('early', 'eday'):
            ctx, pg = new_page(b, wide=True); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.goto(BASE); saved_ballot(pg, [1, 70], pt=pt); pg.wait_for_selector('body.dk-app-on')
            asked = []; pg.on('request', lambda r: asked.append(r.url))
            pg.evaluate("desk.ph.setView('vote')"); pg.click(f'[data-period="{period}"]'); pg.wait_for_selector('#dk-map')
            assert asked == [], (spot, 'drawing the map asked for', asked)
            m = pg.evaluate("""(() => { const m = document.getElementById('dk-map'), d = c => m.querySelector(c).getAttribute('d');
              return {grid: m.querySelectorAll(':scope > line').length, wat: d('.st-wat'), art: d('.st-art'), fw: d('.st-fw'), hw: d('.st-hw'),
                      tags: [...m.querySelectorAll('.st-tag text')].map(t => t.textContent), size: [...m.querySelectorAll('.st-tag text')].map(t => getComputedStyle(t).fontSize),
                      halo: [...m.querySelectorAll(':scope > text')].map(t => getComputedStyle(t).paintOrder)}; })()""")
            assert m['grid'] == 0 and (m['fw'] or m['hw']), (spot, period, 'streets in place of the grid', m['tags'])
            assert bool(m['art']) == (spot != 'far' or period == 'eday'), (spot, period, 'major streets close in; highways only on a widened map (far out, early voting: 45 centers)')
            assert m['tags'] and set(m['size']) == {'10px'} and all(h.startswith('stroke') for h in m['halo']), (spot, period, m['tags'], m['size'], m['halo'])
            if spot in ('south', 'downtown'): assert 'I-35' in m['tags'] and 'MoPac' in m['tags'] and m['wat'], (spot, period, m['tags'])
            problems = pg.evaluate(MAP_PROBLEMS)
            assert problems == [], (spot, period, problems)
            assert errs == [], errs
            ctx.close()
    ctx, pg = phone_page(b); pg.goto(BASE); saved_ballot(pg, [1, 70], pt=STREET_SPOTS['south']); pg.wait_for_selector('body.dk-app-on')
    pg.evaluate("desk.ph.setView('vote')"); pg.click('.ph-mapfold summary'); expect(pg.locator('#dk-map')).to_be_visible()
    assert set(pg.evaluate("[...document.querySelectorAll('#dk-map .st-tag text')].map(t => getComputedStyle(t).fontSize)")) == {'12px'}, 'phone: bigger tags, as its town names are'
    problems = pg.evaluate(MAP_PROBLEMS)
    assert problems == [] and sideways(pg) <= 0 and pg.errs == [], (problems, pg.errs)
    ctx.close()

@phone_test
````

**Edit TS9** (`tests/test_site.py`). Find, exactly once:

````python
                skipped += 1; print('SKIP', fn.__name__, '- no phone layout in', PAGE); continue
            try:
````

Replace it with:

````python
                skipped += 1; print('SKIP', fn.__name__, '- no phone layout in', PAGE); continue
            if fn.__name__ in STREETS_TESTS and not HAS_STREETS:
                skipped += 1; print('SKIP', fn.__name__, '- no street map in', PAGE, '(it is in next/index.html until STREETS_LIVE)'); continue
            try:
````


**Edit TP1** (`tests/test_pipeline.py`). Find, exactly once:

````python
        r = run(); assert r.returncode == 0, r.stderr[-300:]
        r = run('--site', str(d / 'stale'))                                                           # the rollback without --preview: next/ is still the hand-off page
````

Replace it with:

````python
        r = run(); assert r.returncode == 0, r.stderr[-300:]
        (repo / 'next/index.html').write_text(build_site.moved_page(), encoding='utf-8')              # next/ as it is when nothing is in preview (Oct 19)
        r = run('--site', str(d / 'stale'))                                                           # the rollback without --preview: next/ is still the hand-off page
````

**Edit TP2** (`tests/test_pipeline.py`). Find, exactly once:

````python

if __name__ == '__main__':
````

Replace it with:

````python

def street_problems(d):
    """What is wrong with the street map's data d (source/data/streets.json, parsed), as a list; [] when nothing is."""
    import fetch_streets as F
    out, q = [], d.get('q')
    if set(d) != {'v', 'q', 'fwy', 'hwy', 'art', 'water', 'tags', 'order'} or d['v'] != 1 or q != F.Q: return ['keys or version: ' + str(sorted(d))]
    for layer, box, least in (('fwy', F.VIEW, 50), ('hwy', F.VIEW, 150), ('art', F.NEAR, 300), ('water', F.VIEW, 5)):
        if len(d[layer]) < least: out.append(f'{layer}: only {len(d[layer])}')
        for a in d[layer]:
            if len(a) < 4 or len(a) % 2 or not all(type(v) is int for v in a): out.append(f'{layer}: malformed {a[:6]}'); continue
            x, y, pts = a[0], a[1], [(a[0], a[1])]
            for i in range(2, len(a), 2): x += a[i]; y += a[i + 1]; pts.append((x, y))
            if not all(box[0] - 1 / q <= px / q <= box[2] + 1 / q and box[1] - 1 / q <= py / q <= box[3] + 1 / q for px, py in pts): out.append(f'{layer}: a point outside {box}')
            if layer == 'water' and pts[0] != pts[-1]: out.append('water: an outline not closed')
    if d['order'] != [label for label, _ in F.TAGS] or {t[0] for t in d['tags']} != set(d['order']): out.append('tags: a label with no place, or a place with no label')
    if not all(len(t) == 3 and type(t[1]) is int and type(t[2]) is int and F.VIEW[0] <= t[1] / q <= F.VIEW[2] and F.VIEW[1] <= t[2] / q <= F.VIEW[3] for t in d['tags']): out.append('tags: a malformed place, or one outside the view')
    near = lambda lab, x, y: any(t[0] == lab and abs(t[1] / q - x) < 0.03 and abs(t[2] / q - y) < 0.03 for t in d['tags'])
    if not (near('I-35', -97.7357, 30.2672) and near('MoPac', -97.7700, 30.2950)): out.append('tags: I-35 or MoPac not near downtown')
    return out


@test
def street_data_is_whole_and_in_view():
    """source/data/streets.json, the street map's data (Lane, Oct 19), as source/fetch_streets.py writes it and the page
    reads it: compact, within its size cap, every layer there, every point inside the area the maps can show, every
    lake outline closed, a place for every highway label and the labels in the script's order. The check is shown to
    catch each kind of damage on a copy."""
    import copy, fetch_streets as F
    raw = (ROOT / 'source/data/streets.json').read_bytes()
    d = json.loads(raw)
    assert raw == (json.dumps(d, separators=(',', ':')) + '\n').encode('utf-8'), 'not as fetch_streets.py writes it (compact, one line)'
    assert len(raw) <= F.MAX_BYTES, (len(raw), F.MAX_BYTES)
    assert street_problems(d) == [], street_problems(d)
    for damage in (lambda e: e['water'][0].extend([1, 1]),                 # an outline left open
                   lambda e: e['art'][0].__setitem__(0, e['art'][0][0] - 20000),   # a street moved 2 degrees west
                   lambda e: e['tags'].__setitem__(slice(None), [t for t in e['tags'] if t[0] != '71']),   # a highway with no label place
                   lambda e: e['order'].reverse(),
                   lambda e: e['fwy'].__setitem__(slice(10, None), []),
                   lambda e: e['hwy'][0].append(5)):
        e = copy.deepcopy(d); damage(e)
        assert street_problems(e), 'the check missed a damaged copy'


if __name__ == '__main__':
````


**Edit MD1** (`tests/mutate_desk.py`). Find, exactly once:

````python
 ('W3e a share link titled as the site', ROOT / 'picks/index.html', '<title>My picks for Nov 3 · Ballotta</title>', '<title>Ballotta</title>', ['a_share_link_has_its_own_card']),
 ('W3f the offline copy does not keep picks/', ROOT / 'sw.js', "['./', 'next/', 'picks/'].map", "['./', 'next/'].map", ['a_share_link_opens_from_the_offline_copy']),
 ('W3g the share page points unfurlers at the site', ROOT / 'picks/index.html', '<meta property="og:url" content="https://ballotta.org/picks/">', '<link rel="canonical" href="https://ballotta.org/">', ['a_share_link_has_its_own_card']),
````

Replace it with:

````python
 ('W3e a share link titled as the site', ROOT / 'picks/index.html', '<title>My picks for Nov 3 · Ballotta</title>', '<title>Ballotta</title>', ['a_share_link_has_its_own_card']),
 ('W3f the offline copy does not keep picks/', ROOT / 'sw.js', ", 'picks/'].map", "].map", ['a_share_link_opens_from_the_offline_copy']),   # with or without next/ (Oct 19)
 ('W3g the share page points unfurlers at the site', ROOT / 'picks/index.html', '<meta property="og:url" content="https://ballotta.org/picks/">', '<link rel="canonical" href="https://ballotta.org/">', ['a_share_link_has_its_own_card']),
````


Create `tests/mutate_streets.py` with exactly this content:

````python
"""Mutation-kill check for the street map's tests (Lane, Oct 19): every mutant must turn at least one named test RED.
The same runner as mutate_desk.py (files restored from an in-memory copy, even when stopped), against the page with the
street map: next/index.html until promotion, index.html after. Run from the repo root after the build:
    python3 tests/mutate_streets.py [first last]   (a slice of the list, e.g. 0 10)"""
import os, re, sys, pathlib
ROOT = pathlib.Path.cwd()
_set = re.findall(r'^STREETS_LIVE\s*=\s*(True|False)\b', (ROOT / 'source/build_site.py').read_text(encoding='utf-8'), re.M)
assert len(_set) == 1, ('STREETS_LIVE set', len(_set), 'times in build_site.py')
LIVE = _set[0] == 'True'                                                                    # the setting's own line
os.environ['BALLOTTA_MUTATE_PAGE'] = 'index.html' if LIVE else 'next/index.html'
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mutate_desk as R

PREV, TPL, BLD = R.PREV, R.TPL, R.BLD
D, B = 'street_map_draws_streets_and_asks_nobody', 'street_map_waits_for_promotion'
M = [
 ('S1 the grid stays', PREV, '    g = streetLayer(all, X, Y, W, H, sx, sy);   // streets and water in place of the grid\n', '', [D]),
 ('S2 a widened map keeps every street', PREV, "(sx <= 0.6 ? d(L.art) : '')", 'd(L.art)', [D]),
 ('S3 lines above and below the view drawn', PREV, 'f.b[2] >= w && f.b[0] <= e && f.b[3] >= s && f.b[1] <= n', 'f.b[2] >= w && f.b[0] <= e', [D]),
 ('S4 lines left and right of the view drawn', PREV, 'f.b[2] >= w && f.b[0] <= e && f.b[3] >= s && f.b[1] <= n', 'f.b[3] >= s && f.b[1] <= n', [D]),
 ('S5 a tag lands on whatever is there', PREV, 'inside(x, y) && !taken.some(t => overlaps(box(x, y), t)));', 'inside(x, y));', [D]),
 ('S6 tags pile on each other', PREV, '      taken.push(box(x, y));\n', '', [D]),
 ('S7 tags ignore the town names', PREV, "const taken = mapMarks(all, X, Y, W, H).concat(PLACES", "const taken = mapMarks(all, X, Y, W, H).concat(PLACES.slice(0, 0)", [D]),
 ('S8 town names stay under the dots', PREV, '/*STREETS*/.map(p => placeClear(p, all, X, Y, W, H, sy)).filter(Boolean)/*/STREETS*/', '', [D]),
 ('S9 a town name may sit on you', PREV, '    return [[W / 2 - 18, H / 2 - 18, W / 2 + 18, H / 2 + 18]].concat(all.map', '    return [].concat(all.map', [D]),
 ('S10 a moved town name moves the wrong way', PREV, "return [p[0], p[1], p[2] - dy * sy / H];", "return [p[0], p[1], p[2] + dy * sy / H];", [D]),
 ('S11 phone tags at laptop size', PREV, "const fs = matchMedia('(max-width: 1023.98px)').matches ? 12 : 10, best = {};", 'const fs = 10, best = {};', [D]),
 ('S12 the tag box ignores the label', PREV, 'bw = name.length * fs * 0.64 + fs, bh', 'bw = 30, bh', [D]),
 ('S13 a tag hangs off the edge', PREV, '.find(([, x, y]) => inside(x, y) && !taken.some(', '.find(([, x, y]) => !taken.some(', [D]),
 ('S14 no halo on the town names', PREV, '  .dk-map .st-wat ~ text{font-weight:600;fill:var(--ink2);paint-order:stroke;stroke:var(--ground);stroke-width:3px;stroke-linejoin:round}\n  .dk-map .st-tag rect{fill:#fff;stroke:#CDBFAE;stroke-width:1}\n  .dk-map .st-tag text{font-weight:700;fill:var(--muted)}\n/*/STREETS*/\n  /* crib sheet preview', '  .dk-map .st-tag rect{fill:#fff;stroke:#CDBFAE;stroke-width:1}\n  .dk-map .st-tag text{font-weight:700;fill:var(--muted)}\n/*/STREETS*/\n  /* crib sheet preview', [D]),
 ('S15 no water drawn', PREV, "let out = '<path class=\"st-wat\" d=\"' + d(L.water) + '\"></path>'", "let out = '<path class=\"st-wat\" d=\"\"></path>'", [D]),
 ('S16 freeways only', PREV, "const fw = d(L.fwy), hw = d(L.hwy);", "const fw = d(L.fwy), hw = '';", [D]),
 ('S17 the main page gets the street map', BLD, 'streets = streets if streets is not None else bool((preview or STREETS_LIVE) and desk)', 'streets = streets if streets is not None else bool(desk)', [B]),
 ('S18 the preview has no street map', BLD, 'streets = streets if streets is not None else bool((preview or STREETS_LIVE) and desk)', 'streets = streets if streets is not None else bool(STREETS_LIVE and desk)', [B]),
 ('S19 the street data spaced out', BLD, 'script_json(json.load(open(HERE / "data/streets.json", encoding="utf-8")), compact=True)', 'script_json(json.load(open(HERE / "data/streets.json", encoding="utf-8")))', [B]),
 ('S20 the preview without its offline copy', BLD, '"next/sw.js": sw_js(True) if OFFLINE else sw_off_js(True), "next/index.html": build(True)', '"next/sw.js": sw_off_js(True), "next/index.html": build(True)', [B]),
 ('S21 the street strip between the phone if and its else', BLD, '    if not streets:   # before the phone layout\'s if/else below, never between them\n        html = strip_streets(html)\n    if not phone:\n        html = strip_phone(html)\n', '    if not phone:\n        html = strip_phone(html)\n    if not streets:\n        html = strip_streets(html)\n', ['live_build_is_unchanged_until_promotion', B]),
 ('S22 the street map drawn without the laptop layout', BLD, '    assert desk or not streets, "the street map is drawn by the laptop layout\'s code"\n', '', [B]),
 ('S23 no credit', TPL, '<!--STREETS--> Streets and water on the map: U.S. Census Bureau TIGER/Line, 2024.<!--/STREETS-->', '', [B]),
 ('S25 search engines may list the preview', BLD, "html.replace('<meta name=\"referrer\" content=\"no-referrer\">', '<meta name=\"referrer\" content=\"no-referrer\">\\n<meta name=\"robots\" content=\"noindex\">', 1)", "html", [B]),
 ("S26 the preview asks for a version.json that isn't there", BLD, """("fetch('version.json?'", "fetch('../version.json?'")""", """("fetch('version.json?'", "fetch('version.json?'")""", [B]),
 ('S27 the main copy fetches the preview at install', BLD, "    if not preview and not STREETS_LIVE:   # next/ is the street map's preview", "    if False:   # next/ is the street map's preview", [B]),
 ('S28 a kept hand-off page outlives the preview', BLD, "        js = js.replace(STALE_NEXT[0], STALE_NEXT[1], 1)\n        assert STALE_NEXT[1] in js\n", '', [B]),
 ('S24 a malformed STREETS marker passes', BLD, "def strip_streets(html):\n    return strip_marked(html, 'STREETS')", "def strip_streets(html):\n    return html.replace('/*STREETS*/', '').replace('/*/STREETS*/', '')", [B]),
]
# Only while the street map is in preview: their code runs only with STREETS_LIVE = False, so once it is live they
# change nothing and can't be killed (measured on a promoted copy, Oct 19; checked again by a third review pass). The
# runner leaves them out then.
PREVIEW_ONLY = {'S17', 'S18', 'S20', 'S27', 'S28'}   # (S21 still matters: a phone-layout rollback after promotion)
if LIVE:
    M = [m for m in M if m[0].split()[0] not in PREVIEW_ONLY]
if __name__ == '__main__':
    R.main(M)
````

Red first:

```
python3 tests/test_pipeline.py | tail -2
python3 -c "import sys; sys.argv=['x']; sys.path.insert(0, 'tests'); import test_site as T; T.street_map_waits_for_promotion(None)" 2>&1 | tail -1
```

Expected: `street_data_is_whole_and_in_view` passes already (the data is there: `22/22 passed (pipeline)`), and the
build test fails with `AttributeError: module 'build_site' has no attribute 'STREETS_LIVE'`. The browser test can't
run yet: `next/` is still the hand-off page.

## Task 3: the build

**File:** `source/build_site.py`.

**Edit B1** (`source/build_site.py`). Find, exactly once:

````python
    python3 source/build_site.py --site DIR  # the Pages workflow: after --check passes, copies only the site's files to DIR (#83)
    python3 source/build_site.py --preview   # next/: the same page with the phone layout on (and its Home Screen files); counts nothing

````

Replace it with:

````python
    python3 source/build_site.py --site DIR  # the Pages workflow: after --check passes, copies only the site's files to DIR (#83)
    python3 source/build_site.py --preview   # next/, while the phone layout isn't live: the page with it on; counts nothing
                                             # (once it is, the main build writes next/: the street map's preview until
                                             # STREETS_LIVE, then a page that sends people on)

````

**Edit B2** (`source/build_site.py`). Find, exactly once:

````python
OFFLINE = True

````

Replace it with:

````python
OFFLINE = True
# The street map (Lane, Oct 19): freeways, highways, major streets and water under the vote-center dots, drawn on the
# device from source/data/streets.json (written by source/fetch_streets.py from the U.S. Census Bureau's TIGER/Line
# files, public domain), so drawing it asks nothing of anyone. Marked /*STREETS*/ ... /*/STREETS*/ and <!--STREETS-->
# ... <!--/STREETS-->, like the two layouts were. Until Lane approves it at ballotta.org/next/, the main build removes
# every marked block, so index.html stays as it was (the street data too), and next/ is a preview again: the main
# page with the street map on, with its own Home Screen app and offline copy, counting nothing. Promotion: set
# STREETS_LIVE = True; next/ then goes back to sending people on (docs/plans/2026-10-19-street-map.md, Task 9).
STREETS_LIVE = False

````

**Edit B3** (`source/build_site.py`). Find, exactly once:

````python

# ---- Content-Security-Policy (#36). Only the page's own inline scripts (by hash) and files from this site run; data
````

Replace it with:

````python

def strip_streets(html):
    return strip_marked(html, 'STREETS')


# ---- Content-Security-Policy (#36). Only the page's own inline scripts (by hash) and files from this site run; data
````

**Edit B4** (`source/build_site.py`). Find, exactly once:

````python

def script_json(obj):
    """obj as a JavaScript literal that can sit inside an inline <script> (#85): no "</" (ends the script), no "<!--"
    (changes how the script is parsed), no U+2028/U+2029 (line ends in older JavaScript). Every "<" is written \\u003c,
    which reads back as the same text."""
    return (json.dumps(obj, ensure_ascii=False).replace("<", "\\u003c")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
````

Replace it with:

````python

def script_json(obj, compact=False):
    """obj as a JavaScript literal that can sit inside an inline <script> (#85): no "</" (ends the script), no "<!--"
    (changes how the script is parsed), no U+2028/U+2029 (line ends in older JavaScript). Every "<" is written \\u003c,
    which reads back as the same text. compact: no spaces after "," and ":" (the street map's data: a third smaller)."""
    return (json.dumps(obj, ensure_ascii=False, separators=(",", ":") if compact else None).replace("<", "\\u003c")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))
````

**Edit B5** (`source/build_site.py`). Find, exactly once:

````python
    keep = "['./']" if preview else "['./', 'next/', 'picks/']"   # picks/: where share links go, so the first one opens offline too (1.2.0, Pass 1)
    return SW_JS.replace("'ballotta-1'", "'" + cache_prefix(preview) + "1'").replace("PREFIX", cache_prefix(preview)).replace("KEEP.map", keep + ".map")

````

Replace it with:

````python
    keep = "['./']" if preview else "['./', 'next/', 'picks/']"   # picks/: where share links go, so the first one opens offline too (1.2.0, Pass 1)
    js = SW_JS
    if not preview and not STREETS_LIVE:   # next/ is the street map's preview (600 KB), not the hand-off page: no phone fetches it unasked,
        keep = "['./', 'picks/']"           # and a hand-off page kept before is dropped, so it is never shown for the preview (Oct 19, Pass 2)
        js = js.replace(STALE_NEXT[0], STALE_NEXT[1], 1)
        assert STALE_NEXT[1] in js
    return js.replace("'ballotta-1'", "'" + cache_prefix(preview) + "1'").replace("PREFIX", cache_prefix(preview)).replace("KEEP.map", keep + ".map")


# While a preview is at next/, the main copy's install also deletes a kept next/ (the old hand-off page) before keeping the rest.
STALE_NEXT = ("e.waitUntil(caches.open(CACHE).then((c) => Promise.all(",
              "e.waitUntil(caches.open(CACHE).then((c) => c.delete(new URL('next/', location.href).href).catch(() => {}).then(() => c)).then((c) => Promise.all(")

````

**Edit B6** (`source/build_site.py`). Find, exactly once:

````python
    "  } catch (e) { go(); } })();\n")
# The main page does the same for a phone that installed the preview but only ever opens ballotta.org/ now: it asks for
````

Replace it with:

````python
    "  } catch (e) { go(); } })();\n")
# (While a preview is up again, the street map's since Oct 19, this only asks the preview's own worker to update: harmless.)
# The main page does the same for a phone that installed the preview but only ever opens ballotta.org/ now: it asks for
````

**Edit B7** (`source/build_site.py`). Find, exactly once:

````python

# next/manifest.webmanifest is left as it is: once no page links it, nothing can install from it, and a Home Screen
# app installed from the preview opens next/, which sends it on. Rewriting its start_url or scope could merge the two
````

Replace it with:

````python

# next/manifest.webmanifest is left as it is (a preview, the street map's since Oct 19, links it again while it is up;
# it installs as "Ballotta (preview)"): once no page links it, nothing can install from it, and a Home Screen
# app installed from the preview opens next/, which sends it on. Rewriting its start_url or scope could merge the two
````

**Edit B8** (`source/build_site.py`). Find, exactly once:

````python
    if PHONE_LIVE:
        out.update({"manifest.webmanifest": manifest(False), "sw.js": sw_js(False) if OFFLINE else sw_off_js(False),
                    "next/sw.js": sw_off_js(True), "next/index.html": moved_page()})
    else:   # a rollback after promotion: phones keep a worker until its sw.js says otherwise, so it removes itself (Pass 2)
````

Replace it with:

````python
    if PHONE_LIVE:
        out.update({"manifest.webmanifest": manifest(False), "sw.js": sw_js(False) if OFFLINE else sw_off_js(False)})
        if STREETS_LIVE:   # nothing in preview: next/ sends people on, and its worker removes itself
            out.update({"next/sw.js": sw_off_js(True), "next/index.html": moved_page()})
        else:              # the street map's preview (Lane, Oct 19), with its own offline copy, as the layouts' was
            out.update({"next/sw.js": sw_js(True) if OFFLINE else sw_off_js(True), "next/index.html": build(True)})
    else:   # a rollback after promotion: phones keep a worker until its sw.js says otherwise, so it removes itself (Pass 2)
````

**Edit B9** (`source/build_site.py`). Find, exactly once:

````python

def build(preview=False, desk=None, phone=None):
    """desk: include the laptop layout (default: on for the preview, or once DESK_LIVE). phone: include the phone layout
    (default: on for the preview, or once PHONE_LIVE). The laptop-parity test builds with and without it."""
    key = json.load(open(HERE / "answer_key.json", encoding="utf-8"))
````

Replace it with:

````python

def build(preview=False, desk=None, phone=None, streets=None):
    """desk: include the laptop layout (default: on for the preview, or once DESK_LIVE). phone: include the phone layout
    (default: on for the preview, or once PHONE_LIVE). The laptop-parity test builds with and without it. streets: the
    street map (default: on for the preview, or once STREETS_LIVE; never without the laptop layout, which draws it)."""
    desk = desk if desk is not None else (preview or DESK_LIVE)
    phone = phone if phone is not None else (preview or PHONE_LIVE)
    streets = streets if streets is not None else bool((preview or STREETS_LIVE) and desk)
    assert desk or not phone, "the phone layout is built on the laptop layout's code"
    assert desk or not streets, "the street map is drawn by the laptop layout's code"
    key = json.load(open(HERE / "answer_key.json", encoding="utf-8"))
````

**Edit B10** (`source/build_site.py`). Find, exactly once:

````python
    html = (HERE / "template-travis.html").read_text(encoding="utf-8")
    desk = desk if desk is not None else (preview or DESK_LIVE)
    phone = phone if phone is not None else (preview or PHONE_LIVE)
    assert desk or not phone, "the phone layout is built on the laptop layout's code"
    if not desk:
        html = strip_desk(html)
    if not phone:
````

Replace it with:

````python
    html = (HERE / "template-travis.html").read_text(encoding="utf-8")
    if not desk:
        html = strip_desk(html)
    if not streets:   # before the phone layout's if/else below, never between them
        html = strip_streets(html)
    if not phone:
````

**Edit B11** (`source/build_site.py`). Find, exactly once:

````python
        html = html.replace("<title>Ballotta ·", "<title>[Preview] Ballotta ·", 1)
        for a, b in [("url('fonts/", "url('../fonts/"), ('href="favicon.svg"', 'href="../favicon.svg"'), ("f.src = 'census.html'", "f.src = '../census.html'"),
                     ('href="apple-touch-icon.png"', 'href="../apple-touch-icon.png"')]:
            assert a in html, a
            html = html.replace(a, b)
    html = html.replace("<!--ANALYTICS-->", analytics)
    # The data goes in last, so nothing in it can be mistaken for one of the placeholders above (#37).
    html = html.replace("__DATA__", data, 1)
````

Replace it with:

````python
        html = html.replace("<title>Ballotta ·", "<title>[Preview] Ballotta ·", 1)
        # Search engines leave the preview out: the main page is the one to list (README, "noindex"; Oct 19).
        html = html.replace('<meta name="referrer" content="no-referrer">', '<meta name="referrer" content="no-referrer">\n<meta name="robots" content="noindex">', 1)
        assert html.count('<meta name="robots" content="noindex">') == 1
        for a, b in [("url('fonts/", "url('../fonts/"), ('href="favicon.svg"', 'href="../favicon.svg"'), ("f.src = 'census.html'", "f.src = '../census.html'"),
                     ('href="apple-touch-icon.png"', 'href="../apple-touch-icon.png"'),
                     ("fetch('version.json?'", "fetch('../version.json?'")]:   # the one version.json, at the root (Oct 19)
            assert a in html, a
            html = html.replace(a, b)
    html = html.replace("<!--ANALYTICS-->", analytics)
    # The street data, compact (spaces would add a third), then the rest of the data, last, so nothing in either can be
    # mistaken for one of the placeholders above (#37). The street data is numbers and highway names only.
    assert html.count("__STREETS__") == (1 if streets else 0), "__STREETS__ must appear once, inside a STREETS block"
    if streets:
        html = html.replace("__STREETS__", script_json(json.load(open(HERE / "data/streets.json", encoding="utf-8")), compact=True), 1)
    html = html.replace("__DATA__", data, 1)
````

**Edit B12** (`source/build_site.py`). Find, exactly once:

````python
            bad.append(f"the rollback build (laptop layout {'on' if desk else 'off'}, phone layout off) fails: {e}")
    bad += [f"{f} is published but missing" for f in site_files() if not (ROOT / f).is_file()]
````

Replace it with:

````python
            bad.append(f"the rollback build (laptop layout {'on' if desk else 'off'}, phone layout off) fails: {e}")
    try:
        build(streets=False)          # the street map's rollback (after promotion), which runs every STREETS marker check
    except (AssertionError, SystemExit) as e:
        bad.append(f"the street map's rollback build fails: {e}")
    bad += [f"{f} is published but missing" for f in site_files() if not (ROOT / f).is_file()]
````

**Edit B13** (`source/build_site.py`). Find, exactly once:

````python
    if preview and PHONE_LIVE:
        print("The phone layout is live: the main build writes next/ (a page that sends people on, and the self-removing next/sw.js).")
        sys.exit(0)  # not an error, so `--preview && build_site.py` still builds the live page (Pass 2)
````

Replace it with:

````python
    if preview and PHONE_LIVE:
        print("The phone layout is live: the main build writes next/ (the street map's preview until STREETS_LIVE, then a page that sends people on).")
        sys.exit(0)  # not an error, so `--preview && build_site.py` still builds the live page (Pass 2)
````


## Task 4: the page

**File:** `source/template-travis.html`. T1 and T2 are the laptop and phone CSS (the same lines, in each layout's
block), T3 the credit, T4 the drawing code, T5 the two changes in `dotMap()`.

**Edit T1** (`source/template-travis.html`). Find, exactly once:

````html
  .dk-map .top text{fill:#fff;font-weight:700}
  /* crib sheet preview (same look as the printout) */
````

Replace it with:

````html
  .dk-map .top text{fill:#fff;font-weight:700}
/*STREETS*/
  .dk-map .st-wat{fill:#D8E4EA;stroke:none}
  .dk-map .st-rd{fill:none;stroke-linecap:round;stroke-linejoin:round}
  .dk-map .st-art{stroke:#E7DDD0;stroke-width:1.4}
  .dk-map .st-hwc{stroke:#DED2C3;stroke-width:4}
  .dk-map .st-hw{stroke:#fff;stroke-width:2.2}
  .dk-map .st-fwc{stroke:#CDBFAE;stroke-width:6}
  .dk-map .st-fw{stroke:#fff;stroke-width:3.6}
  .dk-map .st-wat ~ text{font-weight:600;fill:var(--ink2);paint-order:stroke;stroke:var(--ground);stroke-width:3px;stroke-linejoin:round}
  .dk-map .st-tag rect{fill:#fff;stroke:#CDBFAE;stroke-width:1}
  .dk-map .st-tag text{font-weight:700;fill:var(--muted)}
/*/STREETS*/
  /* crib sheet preview (same look as the printout) */
````

**Edit T2** (`source/template-travis.html`). Find, exactly once:

````html
  .dk-map .top text{fill:#fff;font-weight:700}
  /* Crib sheet: the printout's look, then its options and the Print button */
````

Replace it with:

````html
  .dk-map .top text{fill:#fff;font-weight:700}
/*STREETS*/
  .dk-map .st-wat{fill:#D8E4EA;stroke:none}
  .dk-map .st-rd{fill:none;stroke-linecap:round;stroke-linejoin:round}
  .dk-map .st-art{stroke:#E7DDD0;stroke-width:1.4}
  .dk-map .st-hwc{stroke:#DED2C3;stroke-width:4}
  .dk-map .st-hw{stroke:#fff;stroke-width:2.2}
  .dk-map .st-fwc{stroke:#CDBFAE;stroke-width:6}
  .dk-map .st-fw{stroke:#fff;stroke-width:3.6}
  .dk-map .st-wat ~ text{font-weight:600;fill:var(--ink2);paint-order:stroke;stroke:var(--ground);stroke-width:3px;stroke-linejoin:round}
  .dk-map .st-tag rect{fill:#fff;stroke:#CDBFAE;stroke-width:1}
  .dk-map .st-tag text{font-weight:700;fill:var(--muted)}
/*/STREETS*/
  /* Crib sheet: the printout's look, then its options and the Print button */
````

**Edit T3** (`source/template-travis.html`). Find, exactly once:

````html
    <p class="note">Ballotta is an early test for Travis County voters only. It isn't affiliated with Travis County, the League of Women Voters, or any campaign, and it doesn't tell you how to vote.</p>
    <p class="note">Districts: Travis County Tax Office voter registration data (public map server). State and federal districts: Texas Legislative Council, CC BY 4.0. Contests and candidates: Travis County's consolidated ballot for Nov 3, 2026 (corrected Oct 14). Candidate answers and the campaign websites we link: the <a href="https://austinvotersguide.org/LWVAA-VG-EN.pdf" target="_blank" rel="noopener">League of Women Voters of the Austin Area 2026 Voters Guide</a>, linked as published. Voting locations: Travis County Clerk; map positions from the U.S. Census geocoder, Travis County and © OpenStreetMap contributors. Contests marked "Double-check" aren't confirmed yet; one district on the county ballot (Travis County MUD No. 41) can't be placed on a map yet. Always compare with your official ballot using the county’s <a href="https://votetravis.gov/voter-lookup/" target="_blank" rel="noopener">Voter Lookup</a> (search by name and birth date).</p>
  </section>
````

Replace it with:

````html
    <p class="note">Ballotta is an early test for Travis County voters only. It isn't affiliated with Travis County, the League of Women Voters, or any campaign, and it doesn't tell you how to vote.</p>
    <p class="note">Districts: Travis County Tax Office voter registration data (public map server). State and federal districts: Texas Legislative Council, CC BY 4.0. Contests and candidates: Travis County's consolidated ballot for Nov 3, 2026 (corrected Oct 14). Candidate answers and the campaign websites we link: the <a href="https://austinvotersguide.org/LWVAA-VG-EN.pdf" target="_blank" rel="noopener">League of Women Voters of the Austin Area 2026 Voters Guide</a>, linked as published. Voting locations: Travis County Clerk; map positions from the U.S. Census geocoder, Travis County and © OpenStreetMap contributors.<!--STREETS--> Streets and water on the map: U.S. Census Bureau TIGER/Line, 2024.<!--/STREETS--> Contests marked "Double-check" aren't confirmed yet; one district on the county ballot (Travis County MUD No. 41) can't be placed on a map yet. Always compare with your official ballot using the county’s <a href="https://votetravis.gov/voter-lookup/" target="_blank" rel="noopener">Voter Lookup</a> (search by name and birth date).</p>
  </section>
````

**Edit T4** (`source/template-travis.html`). Find, exactly once:

````html
  }
  function dotMap(all) {
````

Replace it with:

````html
  }
/*STREETS*/
  // The street map (Lane, Oct 19): freeways, highways, major streets and water, from the U.S. Census Bureau's
  // TIGER/Line files (public domain), built into the page by source/fetch_streets.py, so drawing it asks nothing of
  // anyone. Its format is described at the top of that script.
  const STREETS = __STREETS__;
  let streetLines = null;
  function streetsDecoded() {   // each line as points in degrees, with its bounding box, worked out once
    if (streetLines) return streetLines;
    const q = STREETS.q, dec = (a) => {
      let x = a[0], y = a[1], w = x, e = x, s = y, n = y;
      const p = [[x / q, y / q]];
      for (let i = 2; i < a.length; i += 2) { x += a[i]; y += a[i + 1]; p.push([x / q, y / q]); if (x < w) w = x; if (x > e) e = x; if (y < s) s = y; if (y > n) n = y; }
      return { p, b: [w / q, s / q, e / q, n / q] };
    };
    streetLines = {};
    for (const k of ['water', 'art', 'hwy', 'fwy']) streetLines[k] = STREETS[k].map(dec);
    return streetLines;
  }
  // Boxes, in map pixels ([left, top, right, bottom]), for keeping labels off each other and off the dots.
  const overlaps = (a, b) => a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
  function placeBox(name, x, y) {   // a town name's box, at the size the page's CSS gives it (13px on a phone, 11px wider)
    const fs = matchMedia('(max-width: 1023.98px)').matches ? 13 : 11, w = name.length * fs * 0.62 + 4;
    return [x - w / 2, y - fs * 0.85, x + w / 2, y + fs * 0.3];
  }
  function mapMarks(all, X, Y, W, H) {   // you, and every vote center (the five closest are bigger)
    return [[W / 2 - 18, H / 2 - 18, W / 2 + 18, H / 2 + 18]].concat(all.map((st, i) => {
      const r = i < 5 ? 13 : 8, x = X(st.pt[0]), y = Y(st.pt[1]);
      return [x - r, y - r, x + r, y + r];
    }));
  }
  // A town name a dot would cover moves just above or below it, or is left out (Lane, Oct 19).
  function placeClear(p, all, X, Y, W, H, sy) {
    const marks = mapMarks(all, X, Y, W, H), x = X(p[1]);
    for (const dy of [0, -16, 16]) {
      const y = Y(p[2]) + dy;
      if (y >= 16 && y <= H - 8 && !marks.some(m => overlaps(placeBox(p[0], x, y), m))) return [p[0], p[1], p[2] - dy * sy / H];
    }
    return null;
  }
  function streetLayer(all, X, Y, W, H, sx, sy) {
    const L = streetsDecoded(), w = here[0] - sx / 2, e = here[0] + sx / 2, s = here[1] - sy / 2, n = here[1] + sy / 2;
    const d = (list) => list.filter(f => f.b[2] >= w && f.b[0] <= e && f.b[3] >= s && f.b[1] <= n)   // only lines that reach the view
      .map(f => f.p.map((pt, i) => (i ? 'L' : 'M') + X(pt[0]).toFixed(1) + ' ' + Y(pt[1]).toFixed(1)).join('')).join('');
    const fw = d(L.fwy), hw = d(L.hwy);
    let out = '<path class="st-wat" d="' + d(L.water) + '"></path>' +                  // always drawn, even empty: the town names' halo follows it
      '<path class="st-rd st-art" d="' + (sx <= 0.6 ? d(L.art) : '') + '"></path>' +  // a widened map shows highways only
      '<path class="st-rd st-hwc" d="' + hw + '"></path><path class="st-rd st-hw" d="' + hw + '"></path>' +
      '<path class="st-rd st-fwc" d="' + fw + '"></path><path class="st-rd st-fw" d="' + fw + '"></path>';
    // One label per highway, in the data's order: its place nearest your address whose label touches nothing already
    // on the map (you, the vote centers, the town names, the labels placed before it); none if no place in view does.
    const fs = matchMedia('(max-width: 1023.98px)').matches ? 12 : 10, best = {};
    const taken = mapMarks(all, X, Y, W, H).concat(PLACES.filter(p => X(p[1]) >= 48 && X(p[1]) <= W - 48 && Y(p[2]) >= 16 && Y(p[2]) <= H - 8)
      .map(p => placeClear(p, all, X, Y, W, H, sy)).filter(Boolean).map(p => placeBox(p[0], X(p[1]), Y(p[2]))));
    STREETS.tags.forEach(([name, tx, ty]) => {
      const x = X(tx / STREETS.q), y = Y(ty / STREETS.q);
      (best[name] = best[name] || []).push([Math.hypot(x - W / 2, y - H / 2), x, y]);
    });
    STREETS.order.filter(name => best[name]).forEach(name => {
      const bw = name.length * fs * 0.64 + fs, bh = fs * 1.5, box = (x, y) => [x - bw / 2 - 2, y - bh / 2 - 2, x + bw / 2 + 2, y + bh / 2 + 2];
      const inside = (x, y) => x - bw / 2 >= 4 && x + bw / 2 <= W - 4 && y - bh / 2 >= 4 && y + bh / 2 <= H - 4;   // the whole tag on the map
      const c = best[name].sort((a, b) => a[0] - b[0]).find(([, x, y]) => inside(x, y) && !taken.some(t => overlaps(box(x, y), t)));
      if (!c) return;
      const [, x, y] = c;
      taken.push(box(x, y));
      out += '<g class="st-tag" aria-hidden="true"><rect x="' + (x - bw / 2).toFixed(1) + '" y="' + (y - bh / 2).toFixed(1) + '" width="' + bw.toFixed(1) + '" height="' + bh.toFixed(1) + '" rx="4"></rect>' +
        '<text x="' + x.toFixed(1) + '" y="' + (y + fs * 0.36).toFixed(1) + '" style="font-size:' + fs + 'px">' + esc(name) + '</text></g>';
    });
    return out;
  }
/*/STREETS*/
  function dotMap(all) {
````

**Edit T5** (`source/template-travis.html`). Find, exactly once:

````html
    for (let k = 50; k < H; k += 50) g += '<line x1="0" y1="' + k + '" x2="' + W + '" y2="' + k + '"></line>';
    const labels = PLACES.filter(p => X(p[1]) >= 48 && X(p[1]) <= W - 48 && Y(p[2]) >= 16 && Y(p[2]) <= H - 8).map(p => '<text x="' + X(p[1]).toFixed(0) + '" y="' + Y(p[2]).toFixed(0) + '">' + esc(p[0]) + '</text>').join('');
    const rest = all.slice(5).filter(s => inView(s.pt)).map(s => '<circle cx="' + X(s.pt[0]).toFixed(1) + '" cy="' + Y(s.pt[1]).toFixed(1) + '" r="6"' + (s.f.includes('L') ? ' class="late"' : '') + '><title>' + esc(s.name) + '</title></circle>').join('');
````

Replace it with:

````html
    for (let k = 50; k < H; k += 50) g += '<line x1="0" y1="' + k + '" x2="' + W + '" y2="' + k + '"></line>';
    /*STREETS*/
    g = streetLayer(all, X, Y, W, H, sx, sy);   // streets and water in place of the grid
    /*/STREETS*/
    const labels = PLACES.filter(p => X(p[1]) >= 48 && X(p[1]) <= W - 48 && Y(p[2]) >= 16 && Y(p[2]) <= H - 8)/*STREETS*/.map(p => placeClear(p, all, X, Y, W, H, sy)).filter(Boolean)/*/STREETS*/.map(p => '<text x="' + X(p[1]).toFixed(0) + '" y="' + Y(p[2]).toFixed(0) + '">' + esc(p[0]) + '</text>').join('');
    const rest = all.slice(5).filter(s => inView(s.pt)).map(s => '<circle cx="' + X(s.pt[0]).toFixed(1) + '" cy="' + Y(s.pt[1]).toFixed(1) + '" r="6"' + (s.f.includes('L') ? ' class="late"' : '') + '><title>' + esc(s.name) + '</title></circle>').join('');
````


## Task 5: build, and prove ballotta.org unchanged

```
python3 source/build_site.py && cmp index.html /tmp/index.before.html && python3 source/build_site.py --check
```

Expected: the build lists its files, among them `index.html 440 KB` and `next/index.html 607 KB` (605–609 is fine);
`cmp` prints **nothing** (the main page is byte-for-byte today's); then `build check: every output matches the build,
and both rollback builds pass`. If `cmp` reports a difference, stop: something outside a STREETS block changed (the
dry run's first draft failed exactly here, Oct 19). `git status --short` should list only the files of Tasks 1–4
(the three new ones as `??`) plus `next/index.html`, `next/sw.js` and `sw.js` (the main offline copy no longer fetches
`next/`).

Then look at it: serve the folder (`cd` to the repo, `python3 -m http.server 8000`), open
`http://localhost:8000/next/`, look up `1000 Guadalupe St, 78701`, open Where to vote, and compare the map with the
mockup: streets, water, a few white highway labels, no grid, no label on a dot. Narrow the window below 1024 px and
open "Map of vote centers".

## Task 6: green, then the mutants

```
python3 tests/test_pipeline.py | tail -1
BALLOTTA_STUB_COUNTY=1 python3 tests/test_site.py > /tmp/suite_index.log 2>&1; tail -1 /tmp/suite_index.log; grep '^FAIL' /tmp/suite_index.log
BALLOTTA_STUB_COUNTY=1 BALLOTTA_PAGE=next/index.html python3 tests/test_site.py > /tmp/suite_next.log 2>&1; tail -1 /tmp/suite_next.log; grep '^FAIL' /tmp/suite_next.log
BALLOTTA_STUB_COUNTY=1 python3 tests/mutate_streets.py | tail -1
```

Expected: `22/22 passed (pipeline)`; on `index.html` every test passes with the street-map browser test skipped
(`169/169 passed, 1 skipped (index.html)` (the skip: `street_map_draws_streets_and_asks_nobody`, which runs only where the page has the street map)); on `next/index.html` `170/170 passed (next/index.html)` (the share-link offline test prints that it doesn't apply to the preview); and `28 of 28 mutants killed`. A test that
fails is a failure: the dry run ended with every test passing on both pages, so fix it before going on. The existing mutation runners
need no full run: the main page is byte-for-byte the same and their anchors are untouched; check the anchors only:

```
python3 -c "
import os, sys; sys.argv = ['x']; sys.path.insert(0, 'tests'); os.environ['BALLOTTA_STUB_COUNTY'] = '1'
import mutate_phone as P, mutate_desk as R
for M in (R.M, P.M):
    bad = [n for n, f, a, z, t in M if f.read_text(encoding='utf-8').count(a) != 1]
    print(len(M), 'mutants;', 'every anchor once' if not bad else bad)"
```

Expected: `493 mutants; every anchor once` and `155 mutants; every anchor once` (or the counts on `main` at the time).
Then run the `remediation-audit` skill, Pass 1, on the whole diff before committing. The attack surfaces to name in
the dispatch: the strip order against the phone layout's `if/else`; `next/` turning from the hand-off page back into
a preview (Home Screen apps from the Oct 15–17 preview; the main page's `next/` worker update; the main worker keeping
`next/` at install); the main page's bytes; street data inside an inline script (escaping, the CSP hash); labels on a
phone after the window crosses 1024 px without a redraw; the label placement's edges; `noindex`; the README and
CHANGELOG claims. Pass 2 on any rework.

## Task 7: the release notes

**Files:** `CHANGELOG.md`, `VERSION`, `README.md`. Use the day's date (`date +%F`) in place of `2026-10-21` below.

**Edit CL1** (`CHANGELOG.md`). Find, exactly once:

````markdown
_Nothing yet._

````

Replace it with:

````markdown
_Nothing yet._

## [1.2.1] — 2026-10-21

### Added
- **A street map, in preview at ballotta.org/next/** (Lane, Oct 19). Where to vote's map draws freeways, highways,
  major streets, the lakes and the river under the vote-center dots, with small labels on the main highways (I-35,
  MoPac, 183…), in place of the graph-paper grid. It is drawn on your device from street data built into the page
  (U.S. Census Bureau TIGER/Line, 2024, public domain, simplified by `source/fetch_streets.py`), so no map company is
  asked anything and it works offline: the caption's promise stands as written. A town name a vote center would cover
  moves just above or below it. Only the preview has it until Lane approves it there (`STREETS_LIVE = False`):
  ballotta.org itself is unchanged.

### Changed
- **ballotta.org/next/ is a preview again**, of the street map: the main page with it on, its own offline copy, a
  "[Preview]" title, nothing counted, and a `noindex` so search engines list only ballotta.org. A Home Screen app added
  from the Oct 15–17 preview opens it again instead of being sent on; after promotion it is sent on again. While
  `next/` is a preview, the main page's offline copy no longer fetches it at install (a 600 KB page most phones would
  never open), and a phone that kept the old hand-off page drops it, so the preview is never shown as the old page;
  promotion puts all that back. Mutant W3f re-anchored to hold either way.

### Tests
- `street_map_waits_for_promotion` and `street_map_draws_streets_and_asks_nobody` (the second runs where the page has
  the street map: `BALLOTTA_PAGE=next/index.html` until promotion), and `street_data_is_whole_and_in_view` in the
  pipeline tests; `tests/mutate_streets.py`, 28 mutants. The two promotion tests set `STREETS_LIVE` as well as
  `PHONE_LIVE`, since next/ sends people on only once nothing is in preview.

````


Set `VERSION` to `1.2.1` (the whole file is that line).

**Edit RM1** (`README.md`). Find, exactly once:

````markdown

### Anonymous counts
````

Replace it with:

````markdown

### Street map (in preview at ballotta.org/next/ since 1.2.1)

Where to vote's map draws freeways, highways, major streets (186 names; an east and a west half count as two), the lakes and the river under the vote-center dots, with small labels on the main highways, instead of a grid. The data is the U.S. Census Bureau's TIGER/Line 2024 shapefiles (public domain), simplified by `source/fetch_streets.py` into `source/data/streets.json` (about 160 KB; its format is described at the top of the script), which the build puts into the page, so drawing the map asks nothing of anyone and works offline. The code is marked in `source/template-travis.html` (`/*STREETS*/ … /*/STREETS*/`, `<!--STREETS--> … <!--/STREETS-->`), and `STREETS_LIVE = False` in `source/build_site.py` leaves it out of `index.html` (with the data) while the main build writes `next/` as the preview: the main page with the street map on, its own offline copy, counting nothing, `noindex`. Promotion: set `STREETS_LIVE = True` and release it; `next/` then sends people on again (`docs/plans/2026-10-19-street-map.md`, Task 9). While `next/` is a preview, the main page's offline copy doesn't fetch it at install (a 600 KB page most phones would never open). The plan's Task 10 is the rollback.

### Anonymous counts
````

**Edit RM2** (`README.md`). Find, exactly once:

````markdown
- Vote centers: Travis County Clerk's early voting and Election Day lists; positions from the U.S. Census geocoder, Travis County's geocoder and © OpenStreetMap contributors (ODbL)
- City of Austin Props A–B money split and tax estimate: City of Austin 2026 bond page and staff memo (May 15, 2026)
````

Replace it with:

````markdown
- Vote centers: Travis County Clerk's early voting and Election Day lists; positions from the U.S. Census geocoder, Travis County's geocoder and © OpenStreetMap contributors (ODbL)
- Streets and water on the vote-center map (in preview at `next/`): U.S. Census Bureau TIGER/Line Shapefiles, 2024 (public domain), simplified by `source/fetch_streets.py`
- City of Austin Props A–B money split and tax estimate: City of Austin 2026 bond page and staff memo (May 15, 2026)
````

**Edit RM3** (`README.md`). Find, exactly once:

````markdown
- `vote_sites.json`: the county's vote center lists, geocoded

````

Replace it with:

````markdown
- `vote_sites.json`: the county's vote center lists, geocoded
- `data/streets.json`: the street map's streets and water (`fetch_streets.py`, from the Census Bureau's TIGER/Line files)

````

**Edit RM4** (`README.md`). Find, exactly once:

````markdown
python3 source/build_learn.py
python3 source/build_site.py                        # writes index.html, census.html, version.json, sw.js, manifest.webmanifest and next/ (checks VERSION and CHANGELOG.md first)
````

Replace it with:

````markdown
python3 source/build_learn.py
python3 source/fetch_streets.py                     # only to rebuild the street map's data (data/streets.json) from the Census files (needs pyshp and shapely)
python3 source/build_site.py                        # writes index.html, census.html, version.json, sw.js, manifest.webmanifest and next/ (checks VERSION and CHANGELOG.md first)
````

**Edit RM5** (`README.md`). Find, exactly once:

````markdown
python3 tests/mutate_phone.py                       # the same for the phone layout's tests
```
````

Replace it with:

````markdown
python3 tests/mutate_phone.py                       # the same for the phone layout's tests
BALLOTTA_PAGE=next/index.html python3 tests/test_site.py   # the suite against the preview (the street map's tests run only where the page has it)
python3 tests/mutate_streets.py                     # the same for the street map's tests (the preview's page until promotion)
```
````

**Edit RM6** (`README.md`). Find, exactly once:

````markdown

Search engines may list the page (Lane, Oct 18, the eve of the public launch): `index.html` has no `noindex`. The old preview address, `next/`, now a page that sends people on, keeps its `noindex`.

````

Replace it with:

````markdown

Search engines may list the page (Lane, Oct 18, the eve of the public launch): `index.html` has no `noindex`. The preview address, `next/`, carries `noindex` whether it is a preview (the street map's, since 1.2.1) or a page that sends people on.

````


```
python3 source/build_site.py && python3 source/build_site.py --check && python3 tests/test_pipeline.py | tail -1 && python3 source/check_bumped.py
```

Expected: the build writes `version.json`; `build check: every output…`; `22/22 passed (pipeline)`; `bump check:
nothing published differs from v1.2.1, or v1.2.1 is a new release not tagged yet`.

## Task 8: ship the preview (1.2.1), then Lane looks

In a quiet hour (decision 2), and only once every expected line of Tasks 5–7 has appeared, one chain from the repo
root:

```
git add -A && git status --short && git commit -m "1.2.1: the street map, in preview at next/" && git push origin main
```

`git status --short` should list exactly:
`CHANGELOG.md`, `README.md`, `VERSION`, `index.html`, `next/index.html`, `next/sw.js`, `requirements.txt`,
`source/build_site.py`, `source/data/streets.json`, `source/fetch_streets.py`, `source/template-travis.html`, `sw.js`,
`tests/mutate_desk.py`, `tests/mutate_streets.py`, `tests/test_pipeline.py`, `tests/test_site.py`, `version.json`. Then watch and verify as
`docs/RUNBOOK.md` steps 7–8 do:

```
gh run list --branch main --limit 4
gh run watch <the Pages run's id> --exit-status
curl -s "https://ballotta.org/version.json?$(date +%s)"
curl -s "https://ballotta.org/?$(date +%s)" | shasum -a 256; shasum -a 256 index.html
curl -s "https://ballotta.org/next/?$(date +%s)" | grep -c 'st-wat'
curl -s "https://ballotta.org/?$(date +%s)" | grep -c 'st-wat'
```

Expected: the Pages run green; `{"version": "1.2.1"}`; the two hashes equal; `5` for `next/`; `0` for the main page.

**Lane's look** (the gate for Task 9): on your phone, open https://ballotta.org/next/ (it says "[Preview]" in the tab
or title), look up your address, open Where to vote → "Map of vote centers"; switch Early voting / Election Day; then
the same on your laptop. Things to judge: the streets and water, the highway labels (too many, too few?), the town
names, and whether it feels slower. Anything you'd change goes back through Tasks 4–8 as 1.2.2.

## Task 9: promotion (1.3.0), after Lane's OK

**Files:** `source/build_site.py`, `CHANGELOG.md`, `README.md`, `VERSION`. Use the day's date in place of
`2026-10-22`.

**Edit UB1** (`source/build_site.py`). Find, exactly once:

````python
# STREETS_LIVE = True; next/ then goes back to sending people on (docs/plans/2026-10-19-street-map.md, Task 9).
STREETS_LIVE = False

````

Replace it with:

````python
# STREETS_LIVE = True; next/ then goes back to sending people on (docs/plans/2026-10-19-street-map.md, Task 9).
# Promoted on 2026-10-22 (Lane): the main page has it, and next/ sends people on.
STREETS_LIVE = True

````


**Edit UCL1** (`CHANGELOG.md`). Find, exactly once:

````markdown
_Nothing yet._

````

Replace it with:

````markdown
_Nothing yet._

## [1.3.0] — 2026-10-22

### Added
- **The street map is live** on ballotta.org (Lane, after trying the preview): Where to vote's map draws freeways,
  highways, major streets, the lakes and the river under the vote-center dots, with labels on the main highways,
  instead of a grid, and a town name a vote center would cover moves just above or below it. Drawn on your device from
  street data built into the page (U.S. Census Bureau TIGER/Line, 2024, public domain): no map company is asked
  anything, and it works offline. Credited under About this test. Previewed at next/ in 1.2.1.

### Changed
- **ballotta.org/next/ sends people on again**, to ballotta.org with any picks link, and its offline copy removes
  itself, as after the phone layout's promotion (`STREETS_LIVE = True`). The main page's offline copy keeps `next/`
  from its first install again.

````


Set `VERSION` to `1.3.0`.

**Edit URM1** (`README.md`). Find, exactly once:

````markdown

### Street map (in preview at ballotta.org/next/ since 1.2.1)

Where to vote's map draws freeways, highways, major streets (186 names; an east and a west half count as two), the lakes and the river under the vote-center dots, with small labels on the main highways, instead of a grid. The data is the U.S. Census Bureau's TIGER/Line 2024 shapefiles (public domain), simplified by `source/fetch_streets.py` into `source/data/streets.json` (about 160 KB; its format is described at the top of the script), which the build puts into the page, so drawing the map asks nothing of anyone and works offline. The code is marked in `source/template-travis.html` (`/*STREETS*/ … /*/STREETS*/`, `<!--STREETS--> … <!--/STREETS-->`), and `STREETS_LIVE = False` in `source/build_site.py` leaves it out of `index.html` (with the data) while the main build writes `next/` as the preview: the main page with the street map on, its own offline copy, counting nothing, `noindex`. Promotion: set `STREETS_LIVE = True` and release it; `next/` then sends people on again (`docs/plans/2026-10-19-street-map.md`, Task 9). While `next/` is a preview, the main page's offline copy doesn't fetch it at install (a 600 KB page most phones would never open). The plan's Task 10 is the rollback.

````

Replace it with:

````markdown

### Street map (live since 1.3.0; it was previewed at ballotta.org/next/ in 1.2.1)

Where to vote's map draws freeways, highways, major streets (186 names; an east and a west half count as two), the lakes and the river under the vote-center dots, with small labels on the main highways, instead of a grid. The data is the U.S. Census Bureau's TIGER/Line 2024 shapefiles (public domain), simplified by `source/fetch_streets.py` into `source/data/streets.json` (about 160 KB; its format is described at the top of the script), which the build puts into the page, so drawing the map asks nothing of anyone and works offline. The code is marked in `source/template-travis.html` (`/*STREETS*/ … /*/STREETS*/`, `<!--STREETS--> … <!--/STREETS-->`), and `STREETS_LIVE = True` in `source/build_site.py` keeps it in `index.html`; `next/` sends people on again, as it did before 1.2.1. **Rollback:** set `STREETS_LIVE = False` and release it as the next PATCH (`docs/RUNBOOK.md`; `docs/plans/2026-10-19-street-map.md`, Task 10): the main page loses the street map and `next/` becomes its preview again.

````

**Edit URM2** (`README.md`). Find, exactly once:

````markdown
- Vote centers: Travis County Clerk's early voting and Election Day lists; positions from the U.S. Census geocoder, Travis County's geocoder and © OpenStreetMap contributors (ODbL)
- Streets and water on the vote-center map (in preview at `next/`): U.S. Census Bureau TIGER/Line Shapefiles, 2024 (public domain), simplified by `source/fetch_streets.py`
- City of Austin Props A–B money split and tax estimate: City of Austin 2026 bond page and staff memo (May 15, 2026)
````

Replace it with:

````markdown
- Vote centers: Travis County Clerk's early voting and Election Day lists; positions from the U.S. Census geocoder, Travis County's geocoder and © OpenStreetMap contributors (ODbL)
- Streets and water on the vote-center map: U.S. Census Bureau TIGER/Line Shapefiles, 2024 (public domain), simplified by `source/fetch_streets.py`
- City of Austin Props A–B money split and tax estimate: City of Austin 2026 bond page and staff memo (May 15, 2026)
````

**Edit URM3** (`README.md`). Find, exactly once:

````markdown
python3 tests/mutate_phone.py                       # the same for the phone layout's tests
BALLOTTA_PAGE=next/index.html python3 tests/test_site.py   # the suite against the preview (the street map's tests run only where the page has it)
python3 tests/mutate_streets.py                     # the same for the street map's tests (the preview's page until promotion)
```
````

Replace it with:

````markdown
python3 tests/mutate_phone.py                       # the same for the phone layout's tests
python3 tests/mutate_streets.py                     # the same for the street map's tests
```
````

**Edit URM4** (`README.md`). Find, exactly once:

````markdown

Search engines may list the page (Lane, Oct 18, the eve of the public launch): `index.html` has no `noindex`. The preview address, `next/`, carries `noindex` whether it is a preview (the street map's, since 1.2.1) or a page that sends people on.

````

Replace it with:

````markdown

Search engines may list the page (Lane, Oct 18, the eve of the public launch): `index.html` has no `noindex`. The old preview address, `next/`, a page that sends people on again since 1.3.0, keeps its `noindex`.

````


```
python3 source/build_site.py && python3 source/build_site.py --check && grep -c 'st-wat' index.html && grep -c 'is now at' next/index.html && grep -c "'next/', 'picks/'" sw.js
python3 tests/test_pipeline.py | tail -1
BALLOTTA_STUB_COUNTY=1 python3 tests/test_site.py > /tmp/suite_live.log 2>&1; tail -1 /tmp/suite_live.log; grep '^FAIL' /tmp/suite_live.log
BALLOTTA_STUB_COUNTY=1 python3 tests/mutate_streets.py | tail -1
python3 source/check_bumped.py
git diff --quiet v1.2.0 -- sw.js next/sw.js next/index.html && echo "offline copies and next/ as in 1.2.0"
```

Expected: `next/index.html 0 KB` among the build's files (the hand-off page); `5`; `1`; `1`; `22/22 passed
(pipeline)`; `170/170 passed (index.html)`, now including `street_map_draws_streets_and_asks_nobody`, no skips;
`23 of 23 mutants killed` (the runner now mutates `index.html`, and leaves out the five mutants of preview-only code,
`PREVIEW_ONLY` in the runner: measured, they can't be killed once the street map is live); `bump check: nothing published differs from v1.3.0,
or v1.3.0 is a new release not tagged yet`; `offline copies and next/ as in 1.2.0`. Run the `remediation-audit` skill's Pass 1 on this diff (it is small:
the switch, the notes). Only when all of that holds, commit and push:

```
git add -A && git status --short && git commit -m "1.3.0: the street map is live" && git push origin main
```

`git status --short` should list `CHANGELOG.md`, `README.md`, `VERSION`, `index.html`, `next/index.html`,
`next/sw.js`, `source/build_site.py`, `sw.js`, `version.json`. Then the RUNBOOK checks again:
`{"version": "1.3.0"}`, `grep -c 'st-wat'` gives `5` for ballotta.org, and `https://ballotta.org/next/` now says
"The new Ballotta is now at ballotta.org."

## Task 10: rollback (only if the street map turns out wrong)

A rollback is a forward release (`docs/RUNBOOK.md`). Set `STREETS_LIVE = False` in `source/build_site.py`, add a
section for the next PATCH (after 1.3.0: `## [1.3.1] — <date>` with "### Fixed — **The street map taken back.**
<what was wrong>. ballotta.org's map is the grid again; the street map is back in preview at next/."), set `VERSION`,
then `python3 source/build_site.py && python3 source/build_site.py --check && python3 tests/test_pipeline.py | tail -1`,
run `python3 source/check_bumped.py`, commit and push in one chain, and verify as in Task 9 (the main page `0`,
`next/` `5`). Nothing else changes: the STREETS blocks stay in the template for the next try. Before promotion the
main page never had the street map; to take the preview down too, follow `docs/RUNBOOK.md` steps 1–8 with the 1.2.1
commit's sha (`git log --oneline -5` shows it): its revert keeps `CHANGELOG.md`, `VERSION` and `version.json` moving
forward, as the bump check requires.

## Appendix: checking a street name

If `fetch_streets.py` stops with "streets not in the Census files", list the spellings it has:

```
python3 -c "
import io, zipfile, shapefile
z = zipfile.ZipFile('/tmp/tiger/tl_2024_48453_roads.zip')
r = shapefile.Reader(**{k: io.BytesIO(z.read('tl_2024_48453_roads.' + k)) for k in ('shp', 'shx', 'dbf')})
print(sorted({(x['FULLNAME'], x['MTFCC']) for x in r.records() if x['FULLNAME'] and 'Oltorf' in x['FULLNAME']}))"
```

(replace `Oltorf` with the street). Only `S1400` names belong in `ALSO`; `S1100`/`S1200` streets are drawn as freeways
or highways already.
