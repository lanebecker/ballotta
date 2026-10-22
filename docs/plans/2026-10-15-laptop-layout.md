# Ballotta: laptop layout — build plan

*Written Oct 15, 2026 for Lane. Status: **approved by Lane (Oct 15, 7:24am), executed, and live since Oct 15 (v0.3.0).** From Oct 17, `CHANGELOG.md` is the log (#128). Original status: **approved by Lane (Oct 15, 7:24am) and executed; preview pushed.** The audits in Task 10 changed the code after this plan was written (see "Execution log" at the end): the repo, not the code blocks below, is now the source of truth.*

## The request (verbatim)

> "So just so I'm clear -- we'll build the web version now, make sure we're happy with it, and once we are, we'll do the phone version next? Both as laid out in design here?"
>
> "Build plan, let's do it. Use this skill for this so we make sure to check the plan as well before we execute."

The design is the canvas page **"All screens, 2d (web + phone)"** (https://claude.ai/artifact/6oAiCKqH36pboTcREAzuxh), Option B: full-height plum column with the logo at its top, header on lilac, beige **Help & info** button left of the plum **Share my picks** button, plain "change" link, lilac field behind a white ballot "paper" and a notes column with equal gutters on both sides of the notes, League links opening in a new tab. This plan builds the **laptop** half (screens 1024px and wider). The **phone** half is the next plan, after Lane is happy with this one.

## What "done" looks like

1. https://ballotta.org/next/ shows the laptop layout to anyone on a laptop, with every feature the phone layout has: look up, decide (race and measure), learn-more links, at a glance, where to vote, crib sheet, keep link, share link, a friend's picks, help & info.
2. https://ballotta.org/ is **byte-for-byte unchanged** until Lane says "promote" (checked by a fingerprint test, and by fetching the live page after the push).
3. Phones see exactly what they see today, on both addresses (checked by a pixel-for-pixel screenshot test).
4. After Lane's OK on the preview: one setting flips and the page is rebuilt, the laptop layout goes live, and `/next/` becomes a redirect to the main page (Task 14).

## Not in this build (Lane: please confirm each, per L5)

These differ from the canvas mocks, or are choices the mocks didn't settle:

1. **"Add to my calendar"** (on the Where-to-vote mock) is left out. It's a new feature (a downloadable calendar file), not part of today's site. Easy follow-up if wanted.
2. **Friend landing button** keeps the label "Show my ballot" (mock: "Show my ballot with Maya's picks"); the heading above it already says "See Maya's picks beside yours".
3. **Measure header line** reads "CITY OF AUSTIN · CONTEST 50 OF 63" (mock added "· BOND"; the data doesn't say which measures are bonds).
4. **Help & info → "How your privacy works" and "About Ballotta & sources"** open one Help & info window with both sections, using the phone layout's exact words (copied from the page at runtime, so the two can't drift apart).
5. **Rail outline** keeps full contest names ("City of Austin, City Council Member, District 9"), because rows for special districts would be ambiguous without them. The paper's big heading drops the name of the government, since it's on the line right above it.
6. **Map** has orientation labels for 12 well-known places (Downtown, UT campus, Zilker, Mueller, …), shown when they fall inside the map's area around your address (5 of them for downtown), and no streets: it's drawn on the page from the county's list, with no map service involved, so no map company ever sees an address.
7. **At a glance, multi-seat contests** ("vote for up to 5") show the picks as text with a "Choose" link to the Decide view, since a dropdown can't hold several picks.
8. **Between 1024 and 1279px wide**, the notes column drops below the paper and the header hides the early-voting note (there isn't room for three columns).
9. **Keyboard shortcuts:** 1–9 pick, S skip, N next undecided, J/K next/previous, R reason, / search. (The mock's legend listed 1–5 and no R, though the mock's "Why?" label showed an R key.)
10. **Counting a "compare":** on a laptop, a friend's picks appear beside your ballot automatically, so `share_compare` is counted once per friend link when that first happens (on phones it's still the "Compare with my picks" button). No new event, no new details.
11. **The preview counts nothing.** It loads the same pinned tracker as the live page (so it behaves the same) but with a domain list no real site matches, so the tracker never sends.
12. **Crib sheet header** is the phone's printout header, "My ballot notes · Nov 3, 2026" (mock: "Precinct 300 · Nov 3, 2026"). Changing it would change the phone printout too.
13. **Contest line** reads "Vote for 1" without "Nonpartisan": the ballot data doesn't mark races as nonpartisan.
14. **League note** under each race uses the phone layout's sentence ("…as listed in the League of Women Voters of the Austin Area 2026 Voters Guide. Links open outside Ballotta. We link to every candidate the same way…"), not the mock's shorter one. The links do open in a new tab, and "Ballotta isn't affiliated with the League" is in Help & info → About.
15. **Where to vote** shows the phone layout's full photo-ID box and notes under the list, where the mock had an "ID rules" button.

## How it's built (and why the live page can't change by accident)

- **One page, two layouts.** The laptop layout is added to the same page, `source/template-travis.html`. It reads the same state as the phone layout (`ballot`, `picks`, `whys`, `friend`) and every pick goes through the existing `pick()`, so the two layouts can never disagree, and resizing a window never loses anything. The phone code is untouched apart from four one-line hooks; the phone markup gains one wrapper, `<div id="start">` around the heading and address card (with the same 18px spacing the page gave those two blocks), plus laptop-only elements that are hidden on phones (the header and app, the landing side column, a Back button, the friend heading, the Help & info window). A pixel test proves phones look identical. The laptop CSS only applies at `@media screen and (min-width:1024px)`, and the laptop parts are `display:none` everywhere else (including printouts).
- **Marked blocks.** Every laptop addition is wrapped in markers: `/*DESK*/ … /*/DESK*/` in CSS and JS, `<!--DESK--> … <!--/DESK-->` in HTML. `build_site.py` strips them for the live build until `DESK_LIVE = True`. The shared code gets only four one-line hooks, each inside markers, so stripping restores the original bytes exactly.
- **Preview.** `python3 source/build_site.py --preview` writes `next/index.html` (asset paths `../`, title "[Preview] …", tracker pointed at a domain that matches nothing). GitHub Pages serves it at https://ballotta.org/next/. Browser storage is per site, so picks made on the main page show up on the preview and vice versa (same keys, same format).
- **New browser storage:** one key, `ballotta.desk` = `{v: view, c: contest id}` (which screen you were on). The street address shown in the header ("1000 Guadalupe St") is held in memory for that visit only, never saved; after a reload the header shows just the precinct, as the phone layout does.

## Base and baseline (measured Oct 14, 11:30pm)

- GitHub `main` = local `main` = `0ae877c` ("Make share and keep links short and safe to paste into chat apps"), plus this plan's own commit, which touches only `docs/plans/`.
- `python3 source/build_site.py` reproduces the committed `index.html` exactly: sha256 `fcbf41e3792c67b0efedc81f5e12c6c3519437fa62a5be0640d222c7d7a0a7f5`, which is also the sha256 of https://ballotta.org/ as served right now (`curl -s https://ballotta.org/ | sha256sum`).
- `python3 tests/test_site.py` → `19/19 passed`.
- Sandbox: 2 cores (`nproc`), so audit agents run one at a time.

## Dry run (already done, on a throwaway copy)

Every code block below was applied to a fresh throwaway clone of `0ae877c` (in the session scratchpad, never the real repo) by a script that reads **this document** and applies each FIND/REPLACE literally (line-break notes included), then run. Results of the final run (after the verification pass's fixes, Oct 15):

- Literal application reproduces the tested files byte-for-byte.
- Live build sha256 after all edits: `fcbf41e3…a7f5`, **unchanged**.
- `python3 tests/test_site.py` → `20/20 passed, 16 skipped (index.html)`.
- `BALLOTTA_PAGE=next/index.html python3 tests/test_site.py` → `36/36 passed (next/index.html)`.
- Mutation check (`mutate_desk.py`, Task 9): **31 of 31 mutants killed**, each kill re-checked against the unmutated file. An earlier run left 3 alive, and each led to a fix that is in this plan: a redundant print rule (removed), a resize test that didn't really test resizing (now checks a reason typed on the phone layout shows up on the laptop paper), and a phone-shortcut test that was typing into the address box (now blurs first).
- The phone screenshot comparison caught one real regression during the dry run (the address form lost its 18px top spacing on phones); fixed in Task 2, and now a test.
- The executor still runs every step below for real: a dry run is evidence about the plan, not a substitute for the steps.

---

## Task 0 — Re-check the base (L3)

```bash
cd /home/claude/ballotta
git fetch origin main && git rev-parse HEAD FETCH_HEAD          # expect the same hash twice (local = GitHub)
git diff --name-only 0ae877c HEAD                                # expect only: docs/plans/2026-10-15-laptop-layout.md (this plan's own commit)
git status --short                                               # expect: nothing
python3 source/build_site.py && git status --short && sha256sum index.html
# expect: "index.html 264 KB", no status lines, then fcbf41e3792c67b0efedc81f5e12c6c3519437fa62a5be0640d222c7d7a0a7f5
timeout 590 python3 tests/test_site.py | tail -1                 # expect: 19/19 passed (under a minute)
```

If any of these differ, stop: the base moved and this plan's FIND strings and fingerprint may no longer apply.

Commands here run in separate shell calls, so nothing (variables, `cd`) carries over between them: every command block starts with its own `cd` and uses absolute paths. Give the shell tool a 10-minute timeout (600000 ms) for test and mutation runs; each `timeout 590` keeps a run under that.

## Task 1 — `source/build_site.py`: preview build and DESK stripping

Replace the whole file with:

```python
"""Build the Ballotta site from template-travis.html and the routing data.

    python3 source/build_site.py             # index.html: the live site
    python3 source/build_site.py --preview   # next/index.html: the same page with the laptop layout on; counts nothing

Rebuild rules first if the answer key or district data change:  python3 source/build_rules.py
"""
import json, re, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
# Public address of the site.
BASE_URL = "https://ballotta.org/"
# Umami Cloud website ID (anonymous, cookieless counts). Empty string = no analytics script at all.
UMAMI_ID = "51b98962-382e-4070-bbd0-f43aba4143ae"
# Hostnames whose visits count; anything else (local test runs, previews) is ignored by the tracker.
UMAMI_DOMAINS = "ballotta.org,www.ballotta.org,lanebecker.github.io"
# The laptop layout (1024px and wider) is marked in the template: /*DESK*/ ... /*/DESK*/ in CSS and JS,
# <!--DESK--> ... <!--/DESK--> in HTML. Until Lane approves the preview at ballotta.org/next/, the live build
# removes every marked block, so index.html stays byte-for-byte what it was. Promotion: set DESK_LIVE = True.
DESK_LIVE = False

OPEN, CLOSE = r'(?:/\*DESK\*/|<!--DESK-->)', r'(?:/\*/DESK\*/|<!--/DESK-->)'


def strip_desk(html):
    """Remove every laptop-layout block. A marker alone on its line removes whole lines (newline included);
    a marker pair inside a line removes just the text between and including the markers."""
    opens, closes = len(re.findall(OPEN, html)), len(re.findall(CLOSE, html))
    assert opens == closes, f"DESK markers unpaired: {opens} open, {closes} close"
    html = re.sub(r'^[ \t]*' + OPEN + r'[ \t]*\n.*?^[ \t]*' + CLOSE + r'[ \t]*\n', '', html, flags=re.S | re.M)
    html = re.sub(OPEN + r'[^\n]*?' + CLOSE, '', html)
    assert not re.search(OPEN + '|' + CLOSE, html), "a DESK marker survived stripping"
    return html


def build(preview=False):
    key = json.load(open(HERE / "answer_key.json", encoding="utf-8"))
    rules = json.load(open(HERE / "rules.json"))
    tlc = json.load(open(HERE / "tlc_precincts.json"))
    contests = [{k: c[k] for k in ("id", "title", "type", "choices", "level", "entity")}
                | ({"text": c.get("text", "")} if c["type"] == "measure" else {})
                for c in key["contests"]]
    learn = json.load(open(HERE / "learn.json", encoding="utf-8"))      # built by build_learn.py
    sites = json.load(open(HERE / "vote_sites.json", encoding="utf-8"))  # Travis County Clerk site lists, geocoded
    data = json.dumps({"contests": contests, "rules": rules, "tlc": tlc, "learn": learn, "sites": sites}, ensure_ascii=False)
    data = data.replace("</", "<\\/")  # never let data close the inline <script>
    html = (HERE / "template-travis.html").read_text(encoding="utf-8")
    if not (preview or DESK_LIVE):
        html = strip_desk(html)
    html = html.replace("__DATA__", data)

    # Self-hosted fonts: the only third-party requests are the county and Census lookups.
    fonts = ("<style>@font-face{font-family:'Zilla Slab';src:url('fonts/ZillaSlab-SemiBold.woff2') format('woff2');font-weight:600;font-display:swap}"
             "@font-face{font-family:'Zilla Slab';src:url('fonts/ZillaSlab-Bold.woff2') format('woff2');font-weight:700;font-display:swap}"
             "@font-face{font-family:'Public Sans';src:url('fonts/PublicSans-wght.woff2') format('woff2');font-weight:100 900;font-display:swap}</style>")
    html = re.sub(r"<!--FONTS-->.*?<!--/FONTS-->", fonts, html, flags=re.S).replace("__OG_IMAGE__", BASE_URL + "og.png")
    # Analytics: no URL search or #fragment is ever sent (the fragment is also stripped before this script loads).
    # The tracker is a pinned copy of https://cloud.umami.is/script.js (umami.js, fetched 2026-10-14) served from this
    # site, so a change on Umami's side can never run new code on this page. It still reports to gateway.umami.is.
    analytics = (f'<script defer src="umami.js" data-website-id="{UMAMI_ID}" '
                 f'data-domains="{UMAMI_DOMAINS}" data-exclude-search="true" data-exclude-hash="true"></script>') if UMAMI_ID else ""
    if preview:
        # The preview lives one folder down (next/index.html). It loads the same pinned tracker, so it behaves like the
        # live page, but with a domain list no real site matches: the tracker then never sends anything.
        if analytics:
            analytics = analytics.replace('src="umami.js"', 'src="../umami.js"').replace(f'data-domains="{UMAMI_DOMAINS}"', 'data-domains="preview.invalid"')
            assert 'preview.invalid' in analytics and '../umami.js' in analytics
        html = html.replace("<title>Ballotta ·", "<title>[Preview] Ballotta ·", 1)
        for a, b in [("url('fonts/", "url('../fonts/"), ('href="favicon.svg"', 'href="../favicon.svg"'),
                     ('href="apple-touch-icon.png"', 'href="../apple-touch-icon.png"')]:
            assert a in html, a
            html = html.replace(a, b)
    return html.replace("<!--ANALYTICS-->", analytics)


if __name__ == "__main__":
    preview = "--preview" in sys.argv[1:]
    if preview and DESK_LIVE:
        sys.exit("The laptop layout is live, and next/index.html is a redirect to the main page: not overwriting it.")
    html = build(preview)
    out = ROOT / ("next/index.html" if preview else "index.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(out.relative_to(ROOT).as_posix(), len(html) // 1024, "KB")
```

Check (the template has no markers yet, so the live build must be unchanged):

```bash
python3 source/build_site.py && sha256sum index.html     # expect fcbf41e3…a7f5 (same as Task 0)
python3 source/build_site.py --preview && ls next/        # expect: "next/index.html 264 KB", then "index.html"
```

## Task 2 — Template styles (edit E1)

All template edits are exact find/replace in `source/template-travis.html`. **How to read a block:** the FIND or REPLACE text is exactly what is between the fences. The line under each fence says whether the text also starts and/or ends with a line break; when it says "No line break at the end", the text stops at the last character shown. Each FIND must occur exactly the stated number of times; if it doesn't, stop. Apply the edits in order.

**E1.** Find (must occur exactly once):

```css
.small{font-size:13px}
</style>
```
↳ No line break at the end: the text stops at the last character shown.

Replace with:

```css
.small{font-size:13px}
/*DESK*/
/* ---------- laptop layout (1024px and wider); phones and printouts never see any of this ---------- */
.dk-hdr,.dk-app,.dk-steps,.dk-fcta,.dk-back{display:none}
#start{display:flex;flex-direction:column;gap:18px}  /* on phones, exactly the spacing .wrap gave these two blocks */
#crib.two{column-count:2;column-gap:24px}
#crib.two .ch{column-span:all}
@media screen and (min-width:1024px){
  body{background:var(--lilac)}
  .kbd{display:inline-flex;align-items:center;justify-content:center;min-width:20px;height:20px;padding:0 5px;border-radius:5px;border:1px solid var(--line2);border-bottom-width:2px;background:#fff;font:700 11px/1 ui-monospace,Menlo,monospace;color:var(--muted);flex-shrink:0}
  .btn .kbd{background:transparent;color:inherit;border-color:currentColor;opacity:.75}
  .dk-link{border:none;background:none;padding:0;font:inherit;color:inherit;text-decoration:underline;text-underline-offset:3px;cursor:pointer}
  .dk-link.muted{color:var(--muted)}
  /* header: plum logo block over the rail, the rest on lilac */
  .dk-hdr{display:flex;align-items:center;gap:14px;height:56px;padding:0 24px 0 312px;position:sticky;top:0;z-index:20;background:var(--lilac)}
  .dk-hdr::before{content:'';position:absolute;left:0;top:0;bottom:0;width:288px;background:var(--plum)}
  .dk-brand{position:absolute;left:18px;top:0;bottom:0;display:flex;align-items:center;gap:9px;z-index:1}
  .dk-brand b{font-family:'Zilla Slab',Rockwell,Georgia,serif;font-size:23px;font-weight:600;color:var(--ground)}
  .dk-loc{font-size:14px;color:var(--ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
  .dk-loc b{font-weight:600;color:var(--ink)}
  .dk-sp{flex:1}
  .dk-when{font-size:13px;color:var(--muted);white-space:nowrap}
  .dk-btn{display:inline-flex;align-items:center;height:40px;padding:0 14px;border-radius:10px;border:1px solid var(--line2);background:var(--ground);color:var(--ink);font:inherit;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap}
  .dk-btn.pri{background:var(--plum);border-color:var(--plum);color:#fff}
  .dk-menuwrap{position:relative}
  .dk-menu{position:absolute;right:0;top:46px;width:310px;background:#fff;border-radius:12px;box-shadow:0 12px 40px rgba(36,26,46,.22);padding:8px;display:flex;flex-direction:column;z-index:30}
  .dk-menu button{display:flex;flex-direction:column;align-items:flex-start;gap:1px;text-align:left;padding:10px 12px;border:none;border-radius:8px;background:transparent;font:inherit;color:var(--ink);cursor:pointer}
  .dk-menu button:hover,.dk-menu button:focus-visible{background:#F5EEFA}
  .dk-menu b{font-size:14px;font-weight:600}
  .dk-menu small{font-size:12px;color:var(--muted)}
  .dk-menu .bad b{color:var(--bad)}
  .dk-menu hr{border:none;border-top:1px solid var(--divider);margin:4px 0}
  /* the app: plum rail | lilac desk (paper + notes) */
  body.dk-app-on .wrap{display:none}
  body.dk-app-on .dk-app{display:grid}
  .dk-app{grid-template-columns:288px minmax(0,1fr);min-height:calc(100vh - 56px);background:linear-gradient(90deg,var(--plum) 288px,transparent 288px)}
  .dk-rail{position:sticky;top:56px;height:calc(100vh - 56px);background:var(--plum);color:var(--ground);display:flex;flex-direction:column;min-height:0}
  .dk-rhd{padding:12px 18px;display:flex;flex-direction:column;gap:8px}
  .dk-rhd h2{font-size:22px;color:#fff}
  .dk-rhd span{font-size:13px;color:rgba(255,249,241,.8)}
  .dk-rbar{display:block;height:6px;border-radius:999px;background:rgba(255,249,241,.18);overflow:hidden}
  .dk-rbar i{display:block;height:6px;background:var(--gold);width:0}
  .dk-views{display:flex;flex-direction:column;padding:4px 10px 10px;border-bottom:1px solid rgba(255,249,241,.14)}
  .dk-views button{display:flex;align-items:center;gap:10px;padding:8px 10px;border-radius:8px;border:none;background:transparent;color:rgba(255,249,241,.85);font:inherit;font-size:14px;font-weight:600;cursor:pointer;text-align:left}
  .dk-views button[aria-current=page]{background:rgba(255,249,241,.14);color:#fff}
  .dk-search{margin:12px 14px 6px;height:36px;border-radius:8px;background:rgba(255,249,241,.10);display:flex;align-items:center;gap:8px;padding:0 10px}
  .dk-search input{flex:1;min-width:0;height:34px;border:none;background:transparent;color:#fff;font:inherit;font-size:13px;padding:0}
  .dk-search input::placeholder{color:rgba(255,249,241,.7)}
  .dk-search .kbd{background:transparent;color:var(--ground);border-color:rgba(255,249,241,.4)}
  .dk-filt{display:flex;gap:6px;padding:4px 14px 10px}
  .dk-filt button{height:30px;padding:0 10px;border-radius:8px;border:none;background:transparent;color:#fff;font:inherit;font-size:12px;font-weight:600;box-shadow:inset 0 0 0 1px rgba(255,249,241,.35);cursor:pointer;white-space:nowrap}
  .dk-filt button[aria-pressed=true]{background:var(--ground);color:var(--plum);box-shadow:none}
  .dk-out{flex:1;overflow:auto;padding-bottom:8px}
  .dk-g{display:flex;justify-content:space-between;padding:10px 18px 3px;font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,249,241,.65)}
  .dk-row{display:flex;align-items:center;gap:10px;width:100%;padding:5px 18px;border:none;background:transparent;color:inherit;font:inherit;text-align:left;cursor:pointer}
  .dk-row:hover{background:rgba(255,249,241,.08)}
  .dk-row[aria-current=true]{background:rgba(255,249,241,.14);box-shadow:inset 3px 0 0 var(--gold)}
  .dk-d{width:9px;height:9px;border-radius:50%;box-shadow:inset 0 0 0 2px rgba(255,249,241,.55);flex-shrink:0}
  .dk-d.on{background:var(--gold);box-shadow:none}
  .dk-rt{min-width:0;flex:1;display:flex;flex-direction:column}
  .dk-rt b{font-size:13px;font-weight:600;color:#fff;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .dk-rt small{font-size:12px;color:rgba(255,249,241,.7);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .dk-fa{width:18px;height:18px;border-radius:50%;background:var(--gold);color:var(--ink);font-size:10px;font-weight:800;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0}
  .dk-rail .dk-fa.diff{background:transparent;color:var(--ground);box-shadow:inset 0 0 0 2px var(--gold)}
  .dk-empty{padding:12px 18px;font-size:13px;color:rgba(255,249,241,.75)}
  .dk-foot{padding:12px 14px;border-top:1px solid rgba(255,249,241,.14);display:flex;gap:8px}
  .dk-foot button{flex:1;height:36px;border-radius:8px;border:none;background:transparent;color:#fff;font:inherit;font-size:13px;font-weight:600;box-shadow:inset 0 0 0 1px rgba(255,249,241,.35);cursor:pointer}
  /* three equal gutters (at least 24px each): before the paper, between paper and notes, after the notes */
  .dk-desk{display:grid;grid-template-columns:minmax(0,720px) 320px;justify-content:space-evenly;gap:24px;align-items:start;min-width:0;padding:28px 24px 64px}
  .dk-desk.wide{grid-template-columns:minmax(0,1040px);padding:28px 32px 64px}
  .dk-desk.wide .dk-notes{display:none}
  .dk-paper{background:#fff;border-radius:4px;box-shadow:0 1px 0 var(--line2),0 12px 32px rgba(36,26,46,.08);padding:36px 44px;display:flex;flex-direction:column;gap:18px;min-width:0;outline:none}
  .dk-paper h1{font-size:40px}
  .dk-top{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
  .dk-meta{font-size:14px;font-weight:600;color:var(--ink2);margin-top:-10px}
  .dk-lines{display:flex;flex-direction:column}
  .dk-lw{border-top:1px solid var(--divider);padding:4px 0}
  .dk-lines .dk-lw:first-child{border-top:2px solid var(--ink)}
  .dk-lw:has(.dk-line[aria-pressed=true]){background:linear-gradient(90deg,var(--warnsoft),#fff 70%);margin:0 -16px;padding:4px 16px;border-radius:6px}
  .dk-line{display:flex;align-items:center;gap:14px;width:100%;min-height:48px;padding:6px 0;border:none;background:transparent;font:inherit;color:var(--ink);text-align:left;cursor:pointer}
  .dk-oval{width:30px;height:20px;border-radius:50%;border:2px solid var(--lc);flex-shrink:0}
  .dk-line[aria-pressed=true] .dk-oval{border:none;background:var(--ink)}
  .dk-nm{flex:1;font-size:18px;font-weight:600;line-height:1.25}
  .dk-nm small{display:block;font-size:13px;font-weight:400;color:var(--muted)}
  .dk-paper .links{padding:0 0 8px 44px;margin:-8px 0 0}
  .dk-fp{display:flex;gap:8px;align-items:center;padding:0 0 8px 44px;font-size:13px;color:var(--plum)}
  .dk-mrow{flex-direction:row;gap:16px}
  .dk-mrow .dk-lw,.dk-mrow .dk-lw:has(.dk-line[aria-pressed=true]){flex:1;border-top:2px solid var(--ink);margin:0;padding:4px 12px}
  .dk-two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  .dk-why{display:flex;flex-direction:column;gap:8px}
  .dk-why label{display:flex;gap:6px;align-items:center;font-size:15px;font-weight:600}
  .dk-why label span:not(.kbd){flex:1;color:var(--muted);font-weight:400}
  .dk-why textarea{border:none;border-bottom:2px solid var(--lc);border-radius:0;font-family:Georgia,'Times New Roman',serif;font-size:17px;padding:6px 0;min-height:48px}
  .dk-prompts{display:flex;gap:6px;flex-wrap:wrap}
  .dk-prompts button{padding:3px 10px;border-radius:999px;background:var(--ground);border:1px solid var(--line);font:inherit;font-size:12px;color:var(--ink2);cursor:pointer}
  .dk-nav{display:flex;justify-content:space-between;align-items:center;gap:12px}
  .dk-nav .btn{max-width:72%;min-width:0}
  .dk-nt{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}
  .dk-fchip{align-self:flex-start;display:inline-flex;gap:8px;align-items:center;padding:4px 12px 4px 4px;border-radius:999px;background:var(--lilac);color:var(--plum);font-size:13px;font-weight:600}
  .dk-notes{display:flex;flex-direction:column;gap:22px;padding:8px 0;min-width:0}
  .dk-notes h3{margin-bottom:6px;font-size:11px;letter-spacing:.09em}
  .dk-notes section > p{font-size:14px;color:var(--ink2)}
  .dk-notes .lnk{border-top:none;border-bottom:1px dotted var(--lc)}
  .dk-fbox{background:#fff;border-radius:10px;padding:14px 16px;display:flex;flex-direction:column;gap:8px}
  .dk-kv{display:grid;grid-template-columns:repeat(3,1fr);text-align:center;gap:6px}
  .dk-kv b{display:block;font-family:'Zilla Slab',Rockwell,Georgia,serif;font-size:26px;line-height:1.1}
  .dk-kv span{font-size:12px;color:var(--muted)}
  .dk-keys{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;color:var(--ink2)}
  .dk-keys span{white-space:nowrap;display:inline-flex;gap:4px;align-items:center}
  /* at a glance */
  .dk-gh{display:flex;align-items:flex-end;gap:16px;justify-content:space-between}
  .dk-gh h1{font-size:36px}
  .dk-tog{display:inline-flex;gap:8px;align-items:center;font-size:14px;font-weight:600;white-space:nowrap}
  .dk-tbl{border-collapse:collapse;width:100%;font-size:14px}
  .dk-tbl thead th{text-align:left;font-size:11px;color:var(--muted);font-weight:700;letter-spacing:.07em;text-transform:uppercase;padding:8px 10px;border-bottom:2px solid var(--ink)}
  .dk-tbl tbody th,.dk-tbl td{text-align:left;font-weight:400;padding:9px 10px;border-bottom:1px solid var(--divider);vertical-align:top}
  .dk-tbl tbody th{width:34%}
  .dk-tbl tbody th .dk-link{font-weight:600;text-decoration:none;text-align:left}
  .dk-tbl small{display:block;font-size:12px;color:var(--muted)}
  .dk-tbl small.dk-chk{color:var(--warn)}
  .dk-tbl tr.dk-tg th{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);padding:14px 10px 4px;border-bottom:none}
  .dk-tbl a{white-space:nowrap}
  .dk-sel{width:100%;max-width:260px;height:36px;padding:0 8px;border:1px solid var(--lc);border-radius:8px;background:#fff;font:inherit;font-size:14px;color:var(--ink)}
  .dk-wt{color:var(--ink2)}
  /* where to vote */
  .dk-vote{display:grid;grid-template-columns:minmax(0,400px) minmax(0,1fr);gap:28px;align-items:start}
  .dk-vote > div{display:flex;flex-direction:column;gap:12px;min-width:0}
  .dk-sites{list-style:none;margin:0;padding:0}
  .dk-site{display:flex;gap:12px;padding:11px 0;border-top:1px solid var(--divider)}
  .dk-site .site{flex:1;border:none;padding:0}
  .dk-num{width:24px;height:24px;border-radius:50%;background:var(--plum);color:#fff;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}
  .dk-num.blank{background:transparent}
  .dk-map{width:100%;height:auto;background:var(--ground);border-radius:8px;display:block}
  .dk-map line{stroke:var(--divider)}
  .dk-map text{font:11px 'Public Sans',system-ui,sans-serif;fill:var(--muted);text-anchor:middle}
  .dk-map circle{fill:var(--lc);stroke:#fff;stroke-width:1.5}
  .dk-map circle.late{fill:var(--gold)}
  .dk-map .top circle{fill:var(--plum)}
  .dk-map .top text{fill:#fff;font-weight:700}
  /* crib sheet preview (same look as the printout) */
  .dk-page{background:#fff;border:1px solid var(--line2);box-shadow:0 2px 12px rgba(36,26,46,.12);padding:28px 32px}
  .dk-page.two{column-count:2;column-gap:24px}
  .dk-page .ch{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid #000;padding-bottom:8px;margin-bottom:4px;column-span:all}
  .dk-page .ln{display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px solid #DDD;font-size:12px;break-inside:avoid}
  .dk-page .ln span:last-child{font-weight:800;text-align:right}
  .dk-page .why{font-size:11px;color:#333;padding:0 0 4px}
  .dk-page .grp{font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;margin-top:10px;break-after:avoid}
  /* dialogs become centered windows */
  dialog.sheet{max-width:520px;margin:auto;border-radius:16px;padding:24px 28px}
  dialog.sheet .handle{display:none}
  .dk-info{display:flex;flex-direction:column;gap:22px}
  .dk-info section{display:flex;flex-direction:column;gap:10px}
  .dk-info h3{font-size:12px}
  /* landing (no ballot yet, or "Change address"): the same form, laid out as a paper plus a side column */
  body:not(.dk-app-on) .wrap{max-width:1248px;padding:56px 48px 80px;display:grid;grid-template-columns:minmax(0,1fr) 400px;column-gap:56px;row-gap:18px;align-items:start}
  .wrap > .brand{display:none}
  body:not(.dk-app-on) .wrap > section.card,body:not(.dk-app-on) .wrap > footer,body:not(.dk-app-on) #result{display:none !important}
  #start{grid-column:1;grid-row:1;background:#fff;border-radius:4px;box-shadow:0 1px 0 var(--line2),0 12px 32px rgba(36,26,46,.08);padding:48px 56px;display:flex;flex-direction:column;gap:22px}
  #start h1{font-size:56px}
  #start .lead{font-size:18px}
  #lookup{border:none;padding:0;display:grid;grid-template-columns:2fr 1fr 1fr;gap:12px}
  #lookup > *{grid-column:1/-1}
  #lookup > .field{grid-column:1}
  #lookup .row{display:contents}
  #lookup .row > .field{grid-column:auto}
  .dk-steps{display:flex;grid-column:2;grid-row:1;flex-direction:column;gap:18px;padding-top:32px}
  body.dk-has .dk-back{display:inline-flex;align-self:flex-start;min-height:0;padding:0}
  body.dk-friend #friend{grid-column:1;grid-row:1;background:#fff;border-radius:4px;box-shadow:0 1px 0 var(--line2),0 12px 32px rgba(36,26,46,.08);padding:36px 44px}
  body.dk-friend #start{grid-column:2;grid-row:1;background:transparent;box-shadow:none;padding:24px 0 0}
  body.dk-friend #start > div:has(> h1){display:none !important}  /* beats the div's inline display:flex */
  body.dk-friend #lookup{background:transparent}
  body.dk-friend .dk-fcta{display:flex;flex-direction:column;gap:10px}
  body.dk-friend .dk-steps,body.dk-friend #f-own,body.dk-friend #f-cmp{display:none}
}
@media screen and (min-width:1024px) and (max-width:1279px){
  .dk-desk{grid-template-columns:minmax(0,720px);padding:28px 32px 64px}
  .dk-notes{max-width:720px}
  .dk-when{display:none}
}
/*/DESK*/
</style>
```
↳ No line break at the end: the text stops at the last character shown.

## Task 3 — Template markup (edits E2–E5)

**E2.** Find (must occur exactly once):

```html
<body>
<main class="wrap">
```
↳ No line break at the end: the text stops at the last character shown.

Replace with:

```html
<body>
<!--DESK-->
<header class="dk-hdr" id="dk-hdr">
  <span class="dk-brand"><svg width="21" height="26" viewBox="0 0 86 104" aria-hidden="true"><circle cx="43" cy="22" r="18" fill="#E9A92A"></circle><path d="M8 52 C8 86 26 98 43 98 C60 98 78 86 78 52" fill="none" stroke="#FFF9F1" stroke-width="8" stroke-linecap="round"></path><path d="M2 52 H84" stroke="#FFF9F1" stroke-width="8" stroke-linecap="round"></path></svg><b>Ballotta</b></span>
  <span class="dk-loc" id="dk-loc">Travis County · Nov 3, 2026 election</span>
  <span class="dk-sp"></span>
  <span class="dk-when" id="dk-when"></span>
  <div class="dk-menuwrap">
    <button type="button" class="dk-btn" id="dk-help" aria-haspopup="menu" aria-expanded="false" aria-controls="dk-menu">Help &amp; info</button>
    <div class="dk-menu hidden" id="dk-menu" role="menu" aria-label="Help and info">
      <button type="button" role="menuitem" data-help="feedback"><b>Send feedback</b><small>Opens an email with your precinct, never your address</small></button>
      <button type="button" role="menuitem" data-help="privacy"><b>How your privacy works</b><small>What goes where, in plain words</small></button>
      <button type="button" role="menuitem" data-help="about"><b>About Ballotta &amp; sources</b><small>Not affiliated with the county, the League or any campaign</small></button>
      <button type="button" role="menuitem" data-help="address"><b>Change address</b><small>Look up a different ballot</small></button>
      <hr>
      <button type="button" role="menuitem" data-help="clear" class="bad"><b>Clear my picks…</b><small>Asks before deleting anything</small></button>
    </div>
  </div>
  <button type="button" class="dk-btn pri hidden" id="dk-share">Share my picks</button>
</header>
<div class="dk-app" id="dk-app">
  <nav class="dk-rail" aria-label="Your ballot">
    <div class="dk-rhd"><h2>Your ballot</h2><span id="dk-count"></span><span class="dk-rbar"><i id="dk-bar"></i></span></div>
    <div class="dk-views" id="dk-views">
      <button type="button" data-view="decide"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-10"/></svg>Decide</button>
      <button type="button" data-view="glance"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg>At a glance</button>
      <button type="button" data-view="vote"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"/><circle cx="12" cy="10" r="2.5"/></svg>Where to vote</button>
      <button type="button" data-view="crib"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M7 14h10v7H7z"/></svg>Crib sheet</button>
    </div>
    <div class="dk-search"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#FFF9F1" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/></svg><input id="dk-q" type="search" placeholder="Find a race or a name" aria-label="Find a race or a name" autocomplete="off"><span class="kbd" aria-hidden="true">/</span></div>
    <div class="dk-filt" id="dk-filt" role="group" aria-label="Show"><button type="button" data-f="all"></button><button type="button" data-f="und"></button><button type="button" data-f="why"></button></div>
    <div class="dk-out" id="dk-out"></div>
    <div class="dk-foot"><button type="button" id="dk-keep">Keep my picks</button><button type="button" id="dk-print">Print</button></div>
  </nav>
  <div class="dk-desk" id="dk-desk">
    <article class="dk-paper" id="dk-paper" tabindex="-1" aria-label="Ballot paper"></article>
    <aside class="dk-notes" id="dk-notes" aria-label="Notes"></aside>
  </div>
</div>
<!--/DESK-->
<main class="wrap">
```
↳ No line break at the end: the text stops at the last character shown.

**E3.** Find (must occur exactly once):

```html
  <div style="display:flex;flex-direction:column;gap:10px">
    <h1>What's on your ballot?</h1>
```
↳ No line break at the end: the text stops at the last character shown.

Replace with:

```html
  <!--DESK--><div id="start"><button type="button" class="btn text dk-back" id="dk-back">← Back to my ballot</button><div class="dk-fcta" id="dk-fcta"></div><!--/DESK--><div style="display:flex;flex-direction:column;gap:10px">
    <h1>What's on your ballot?</h1>
```
↳ No line break at the end: the text stops at the last character shown.

**E4.** Find (must occur exactly once):

```html
  </section>

  <div id="result"
```
↳ No line break at the end: the text stops at the last character shown.

Replace with:

```html
  </section><!--DESK--></div><!--/DESK-->
<!--DESK-->
  <aside class="dk-steps" aria-label="How Ballotta works">
    <div><span class="ov">1 · Your ballot, race by race</span><p class="lead">Every race and proposition for your address, in ballot order, from the county’s own district data.</p></div>
    <div><span class="ov">2 · Neutral sources beside each choice</span><p class="lead">League of Women Voters answers, campaign sites and official measure text, the same way for every candidate.</p></div>
    <div><span class="ov">3 · Print it, keep it, share it</span><p class="lead">A crib sheet for the booth (phones must be off where you vote), a private link to yourself, and a link for friends.</p></div>
  </aside>
<!--/DESK-->

  <div id="result"
```
↳ No line break at the end: the text stops at the last character shown.

**E5.** Find (must occur exactly once):

```html
  <p class="note">Local races can hint at your neighborhood. The link holds only what you chose here; Ballotta never sees it.</p>
</dialog>
```
↳ This text ends with a line break.

Replace with:

```html
  <p class="note">Local races can hint at your neighborhood. The link holds only what you chose here; Ballotta never sees it.</p>
</dialog>
<!--DESK-->

<dialog class="sheet" id="d-info" aria-labelledby="dih">
  <div class="sheethead"><h2 id="dih" style="font-size:26px">Help &amp; info</h2><button type="button" class="x" data-close>Close</button></div>
  <div class="dk-info" id="dk-info"></div>
</dialog>
<!--/DESK-->
```
↳ This text ends with a line break.

## Task 4 — Hooks in the shared code (edits E6–E9)

Each hook is one statement inside inline markers, appended to an existing line, so the live build strips it back to the original line.

**E6.** Find (must occur exactly once):

```js
  refresh();
  renderVote();
}
```
↳ No line break at the end: the text stops at the last character shown.

Replace with:

```js
  refresh();
  renderVote();/*DESK*/ if (window.desk) desk.ballot(meta);/*/DESK*/
}
```
↳ No line break at the end: the text stops at the last character shown.

**E7.** Find (must occur exactly once):

```js
  if (!$('compare').classList.contains('hidden')) renderCompare();
}
```
↳ No line break at the end: the text stops at the last character shown.

Replace with:

```js
  if (!$('compare').classList.contains('hidden')) renderCompare();/*DESK*/ if (window.desk) desk.refresh();/*/DESK*/
}
```
↳ No line break at the end: the text stops at the last character shown.

**E8.** Find (must occur exactly once):

```js
  ballot.forEach(b => {
    if (b.c.level !== last) {
```
↳ No line break at the end: the text stops at the last character shown.

Replace with:

```js
  ballot.forEach(b => {/*DESK*/ if (window.desk && desk.cribSkip(b.c)) return;/*/DESK*/
    if (b.c.level !== last) {
```
↳ No line break at the end: the text stops at the last character shown.

**E9.** Find (must occur exactly once):

```js
    if (!LS.get('ballotta.gen', null)) LS.set('ballotta.gen', friend.gen + 1);
  }
}
```
↳ This text ends with a line break.

Replace with:

```js
    if (!LS.get('ballotta.gen', null)) LS.set('ballotta.gen', friend.gen + 1);
  }/*DESK*/ if (window.desk) desk.render();/*/DESK*/
}
```
↳ This text ends with a line break.

What each hook does: **E6** draws the laptop layout for a new ballot (lookup, saved ballot, restored link). **E7** updates the rail, counts and notes after any pick, skip or clear. **E8** lets the crib sheet's "Hide unopposed races" option drop those lines (it's off unless switched on in the laptop layout, so the phone printout is unchanged). **E9** (the last statement of `openFriend`, after its own counting and wiring) switches the laptop landing page to the friend version when a share link arrives, and shows the friend's picks beside an existing ballot.

## Task 5 — The laptop script (edit E10)

**E10.** Find (must occur exactly once):

```js

/* ---------- start ---------- */
```
↳ This text starts with a line break (the empty first line) and ends with a line break.

Replace with:

```js

/*DESK*/
/* ---------- laptop layout (1024px and wider) ----------
   Draws from the same state as the phone layout (ballot, picks, whys, friend); picking goes through pick(), so both
   layouts always agree. It renders even on phones (hidden by CSS) so resizing a window never shows stale picks, but
   it only tracks events and takes keyboard shortcuts when the wide layout is actually on screen. */
const desk = (() => {
  const WIDE = window.matchMedia('(min-width: 1024px)');
  const saved = LS.get('ballotta.desk', {}) || {};
  const ui = { view: ['decide', 'glance', 'vote', 'crib'].includes(saved.v) ? saved.v : 'decide', cur: typeof saved.c === 'string' ? saved.c : '',
    filter: 'all', q: '', landing: false, addr: '', hideUnopp: false, two: false, hideCrib: false, cmpFor: null };
  const P = () => $('dk-paper'), N = () => $('dk-notes');
  const save = () => LS.set('ballotta.desk', { v: ui.view, c: ui.cur });
  const idx = (cid) => ballot.findIndex(b => b.c.id === cid);
  const curB = () => ballot[idx(ui.cur)] || ballot[0];
  const decided = (cid) => current(cid).length > 0;
  const hasWhy = (cid) => !!(whys[cid] && whys[cid].trim());
  const isUnopp = (c) => c.type !== 'measure' && optionsOf(c).length === 1;
  const initial = () => esc((friend && friend.name ? friend.name : '?').charAt(0).toUpperCase());
  const possessive = () => esc(friend && friend.name ? friend.name + '’s' : 'your friend’s');
  function nextUndecided(from) {
    const i = idx(from);
    for (let k = 1; k <= ballot.length; k++) { const b = ballot[(i + k + ballot.length) % ballot.length]; if (b && !decided(b.c.id)) return b; }
    return null;
  }
  function samePick(id) { const f = friend.P[id], m = current(id); return m.length > 0 && m[0] !== '__skip' && m.length === f.length && m.every(x => f.includes(x)); }
  function whenLine() {
    const d = new Date(NOW.getFullYear(), NOW.getMonth(), NOW.getDate()).getTime(), t = (m, day) => new Date(2026, m, day).getTime();
    if (d < t(9, 19)) return 'Early voting starts Mon Oct 19';
    if (d <= t(9, 30)) return 'Early voting through Fri Oct 30 · 7am–7pm';
    if (d < t(10, 3)) return 'Election Day is Tue Nov 3 · 7am–7pm';
    if (d === t(10, 3)) return 'Election Day today · 7am–7pm';
    return 'Election Day was Nov 3';
  }

  /* ----- frame: which screen, header, rail ----- */
  function mode() {
    const app = ballot.length > 0 && !ui.landing, cls = document.body.classList;
    cls.toggle('dk-app-on', app);
    cls.toggle('dk-has', ballot.length > 0);
    cls.toggle('dk-friend', !app && !!friend);
    $('dk-fcta').innerHTML = friend ? '<span class="ov">Next: your own ballot</span><h2 style="font-size:28px">See ' + possessive() + ' picks beside yours</h2><p class="lead">Enter the address where you’re registered. ' + (friend.name ? esc(friend.name) + '’s' : 'Their') + ' picks show up next to yours, race by race, and never change them.</p>' : '';
    return app;
  }
  function header() {
    const n = ballot.length;
    $('dk-share').classList.toggle('hidden', !n);
    $('dk-loc').innerHTML = n ? '<b>Precinct ' + esc(String(lastLookup.precinct || '')) + '</b>' + (ui.addr ? ' · ' + esc(ui.addr) : '') + ' · <button type="button" class="dk-link" id="dk-change">change</button>' : 'Travis County · Nov 3, 2026 election';
    if (n) $('dk-change').addEventListener('click', toLanding);
    $('dk-when').textContent = whenLine();
  }
  function matches(b) {
    if (ui.filter === 'und' && decided(b.c.id)) return false;
    if (ui.filter === 'why' && !hasWhy(b.c.id)) return false;
    return !ui.q || (cleanTitle(b.c) + ' ' + optionsOf(b.c).join(' ')).toLowerCase().includes(ui.q.toLowerCase());
  }
  function rail() {
    const n = ballot.length, done = ballot.filter(b => decided(b.c.id)).length;
    $('dk-count').textContent = done + ' of ' + n + ' decided';
    $('dk-bar').style.width = (n ? Math.round(100 * done / n) : 0) + '%';
    document.querySelectorAll('#dk-views button').forEach(b => b.setAttribute('aria-current', b.dataset.view === ui.view ? 'page' : 'false'));
    const counts = { all: 'All ' + n, und: 'Undecided ' + (n - done), why: 'Reasons ' + ballot.filter(b => hasWhy(b.c.id)).length };
    document.querySelectorAll('#dk-filt button').forEach(b => { b.textContent = counts[b.dataset.f]; b.setAttribute('aria-pressed', b.dataset.f === ui.filter ? 'true' : 'false'); });
    const byLevel = {}; ballot.forEach(b => (byLevel[b.c.level] = byLevel[b.c.level] || []).push(b));
    let html = '';
    LEVELS.filter(L => byLevel[L]).forEach(L => {
      const all = byLevel[L], shown = all.filter(matches);
      if (!shown.length) return;
      html += '<div class="dk-g"><span>' + esc(LEVEL_LABEL[L] || L) + '</span><span>' + all.filter(b => decided(b.c.id)).length + '/' + all.length + '</span></div>';
      html += shown.map(b => {
        const id = b.c.id, v = current(id), sub = !v.length ? 'Undecided' : v[0] === '__skip' ? 'Skipping' : v.map(x => optLabel(b.c, x)).join(', ');
        const fa = friend && friend.P[id] ? '<span class="dk-fa' + (samePick(id) ? '' : ' diff') + '" title="' + possessive() + ' pick: ' + esc(friend.P[id].map(x => optLabel(b.c, x)).join(', ')) + '">' + initial() + '</span>' : '';
        return '<button type="button" class="dk-row" data-row="' + id + '"' + (id === ui.cur && ui.view === 'decide' ? ' aria-current="true"' : '') + '><span class="dk-d' + (v.length && v[0] !== '__skip' ? ' on' : '') + '" aria-hidden="true"></span><span class="dk-rt"><b>' + esc(cleanTitle(b.c)) + '</b><small>' + esc(sub) + (b.conf === 'medium' ? ' · Double-check' : '') + '</small></span>' + fa + '</button>';
      }).join('');
    });
    $('dk-out').innerHTML = html || '<p class="dk-empty">' + (ui.q ? 'Nothing matches “' + esc(ui.q) + '”.' : ui.filter === 'und' ? 'Every contest is decided.' : 'No reasons written yet.') + '</p>';
    $('dk-out').querySelectorAll('.dk-row').forEach(r => r.addEventListener('click', () => go(r.dataset.row, true)));
  }

  /* ----- views ----- */
  function render() {
    const app = mode(); header();
    if (!ballot.length) return;
    if (idx(ui.cur) < 0) ui.cur = ballot[0].c.id;
    rail();
    $('dk-desk').className = 'dk-desk' + (ui.view === 'glance' || ui.view === 'vote' ? ' wide' : '');
    ({ decide: viewDecide, glance: viewGlance, vote: viewVote, crib: viewCrib })[ui.view]();
    if (app && friend && WIDE.matches && ui.cmpFor !== friend) { ui.cmpFor = friend; track('share_compare', {}); }
  }
  function go(cid, focus) {
    if (idx(cid) < 0) return;
    ui.cur = cid; ui.view = 'decide'; save(); render();
    if (!WIDE.matches) return;
    window.scrollTo(0, 0);
    if (focus) P().focus({ preventScroll: true });
    const r = $('dk-out').querySelector('[aria-current="true"]'); if (r) r.scrollIntoView({ block: 'nearest' });
  }
  function setView(v) { ui.view = v; save(); render(); if (WIDE.matches) window.scrollTo(0, 0); }
  function nextLabel() {
    const nx = nextUndecided(ui.cur);
    return nx ? '<span class="dk-nt">Next undecided: ' + esc(cleanTitle(nx.c)) + '</span> <span class="kbd" aria-hidden="true">N</span>' : '<span class="dk-nt">All decided · see At a glance</span>';
  }
  function line(c, val, sub, k, links) {
    const on = current(c.id).includes(val), F = friend && friend.P[c.id];
    const fr = F && F.includes(val) ? '<div class="dk-fp"><span class="dk-fa">' + initial() + '</span><span><b>' + esc(friendName()) + ' picked this</b>' + (friend.W[c.id] ? ' · “' + esc(friend.W[c.id]) + '”' : '') + '</span></div>' : '';
    return '<div class="dk-lw"><button type="button" class="dk-line" data-c="' + c.id + '" data-pick="' + esc(val) + '" aria-pressed="' + on + '"><span class="dk-oval" aria-hidden="true"></span><span class="dk-nm">' + esc(optLabel(c, val)) + (sub ? '<small>' + esc(sub) + '</small>' : '') + '</span>' + (k < 9 ? '<span class="kbd" aria-hidden="true">' + (k + 1) + '</span>' : '') + '</button>' + (links || '') + fr + '</div>';
  }
  function viewDecide() {
    const b = curB(), c = b.c, L = DATA.learn[c.id] || {}, isM = c.type === 'measure', n = seats(c), opts = optionsOf(c), cur = current(c.id), i = idx(c.id);
    const where = c.entity && c.entity !== c.level ? c.entity : (LEVEL_LABEL[c.level] || c.level);
    let h = friend ? '<div class="dk-fchip"><span class="dk-fa">' + initial() + '</span>Showing ' + possessive() + ' picks · <button type="button" class="dk-link" data-act="hidefriend">Hide</button></div>' : '';
    h += '<div class="dk-top"><span class="ov">' + esc(where) + ' · contest ' + (i + 1) + ' of ' + ballot.length + '</span><span class="note">Saved on this device</span></div>';
    const t = cleanTitle(c);  // the entity is already on the line above, so the heading drops it
    h += '<h1>' + esc(c.entity && t.startsWith(c.entity + ', ') ? t.slice(c.entity.length + 2) : t) + '</h1>';
    if (!isM) h += '<div class="dk-meta">' + (opts.length === 1 ? 'Unopposed' : (n > 1 ? 'Vote for up to ' + n : 'Vote for 1')) + (c.choices.includes('Write-in') ? ' · write-in allowed' : '') + '</div>';
    if (b.conf === 'medium') h += '<span class="flag">Double-check</span><p class="note">' + esc(b.note || 'Not yet confirmed for your address.') + '</p>';
    if (isM) {
      if (c.text) h += '<div class="sub"><span class="ov">Exactly as printed on your ballot</span><p class="verbatim">' + esc(c.text) + '</p></div>';
      if (L.plain) h += '<div class="sub"><span class="ov">In plain words</span><p>' + esc(L.plain) + '</p>' + (L.for ? '<div class="meaning"><b>FOR</b><span>' + esc(L.for) + '</span><b>AGAINST</b><span>' + esc(L.against) + '</span></div>' : '') + '</div>';
      if (L.money || L.tax) h += '<div class="dk-two">' + (L.money ? '<div class="sub"><span class="ov">Where the money goes</span><div>' + L.money.map(m => '<div class="bar"><span>' + esc(m[0]) + '</span><b>' + esc(m[1]) + '</b></div>').join('') + '</div><p class="note">' + esc(L.moneyNote || '') + '</p></div>' : '') + (L.tax ? '<div class="sub"><span class="ov">Effect on taxes</span><p>' + esc(L.tax) + '</p></div>' : '') + '</div>';
      if (L.note) h += '<p class="note">' + esc(L.note) + '</p>';
      h += '<div class="dk-lines dk-mrow">' + opts.map((o, k) => line(c, o, '', k, '')).join('') + '</div>';
    } else {
      const raw = c.choices.filter(x => x !== 'Write-in');
      h += '<div class="dk-lines">' + raw.map((o, k) => { const m = o.match(/\((REP|DEM|LIB|GRN)\)$/); return line(c, opts[k], m ? PARTY[m[1]] : '', k, candLinks(L, opts[k])); }).join('') + '</div>';
    }
    h += '<button type="button" class="skip" data-c="' + c.id + '" data-pick="__skip" aria-pressed="' + (cur[0] === '__skip') + '">Skip this ' + (isM ? 'measure' : 'race') + ' <span class="kbd" aria-hidden="true">S</span></button>';
    h += '<div class="dk-why"><label for="dk-w">Why? <span>Private unless you choose to share it</span><span class="kbd" aria-hidden="true">R</span></label><textarea id="dk-w" placeholder="Your reasoning, in your words">' + esc(whys[c.id] || '') + '</textarea>' +
      '<div class="dk-prompts"><button type="button" data-prompt="What matters most to me here: ">What matters most to me here…</button><button type="button" data-prompt="Still deciding because ">Still deciding because…</button></div></div>';
    h += '<div class="dk-nav"><button type="button" class="btn secondary small" data-act="prev"' + (i <= 0 ? ' disabled' : '') + '><span class="kbd" aria-hidden="true">K</span> Previous</button><button type="button" class="btn small" data-act="next" id="dk-next">' + nextLabel() + '</button></div>';
    P().innerHTML = h;
    P().querySelectorAll('[data-pick]').forEach(btn => btn.addEventListener('click', () => pick(btn.dataset.c, btn.dataset.pick)));
    const ta = $('dk-w');
    ta.addEventListener('input', () => {
      whys[c.id] = ta.value; LS.set('ballotta.whys', whys);
      const pw = $('w' + c.id); if (pw) pw.value = ta.value;  // keep the phone layout's box in step
      renderCrib(); rail();
    });
    P().querySelectorAll('[data-prompt]').forEach(btn => btn.addEventListener('click', () => {
      ta.value = ta.value.trim() ? ta.value.replace(/\s*$/, ' ') + btn.dataset.prompt : btn.dataset.prompt;
      ta.dispatchEvent(new Event('input')); ta.focus(); ta.setSelectionRange(ta.value.length, ta.value.length);
    }));
    P().querySelectorAll('[data-act]').forEach(btn => btn.addEventListener('click', () => act(btn.dataset.act)));
    notesDecide();
  }
  function notesDecide() {
    const c = curB().c, L = DATA.learn[c.id] || {}, isM = c.type === 'measure';
    let h = '';
    if (friend) {
      const mine = new Set(ballot.map(b => b.c.id)), ids = Object.keys(friend.P).filter(id => mine.has(id));
      const same = ids.filter(samePick).length, none = ids.filter(id => !current(id).length).length, diff = ids.length - same - none;
      h += '<section class="dk-fbox"><h3>You and ' + esc(friendName()) + '</h3><div class="dk-kv"><div><b>' + same + '</b><span>same pick</span></div><div><b>' + diff + '</b><span>different</span></div><div><b>' + none + '</b><span>you haven’t picked</span></div></div><p class="note">Only races ' + esc(friendName()) + ' picked that are also on your ballot. Their picks never change yours. <button type="button" class="dk-link" data-act="hidefriend">Hide ' + possessive() + ' picks</button></p></section>';
    }
    if (L.office) h += '<section><h3>About this office</h3><p>' + esc(L.office) + '</p></section>';
    if (L.src && L.src.length) h += '<section><h3>' + (isM ? 'Sources' : 'Learn more · neutral sources') + '</h3>' + srcHTML(L.src) + '</section>';
    h += '<section><h3>Shortcuts</h3><div class="dk-keys"><span><span class="kbd">1</span>–<span class="kbd">9</span> pick</span><span><span class="kbd">S</span> skip</span><span><span class="kbd">N</span> next undecided</span><span><span class="kbd">J</span><span class="kbd">K</span> next, previous</span><span><span class="kbd">R</span> reason</span><span><span class="kbd">/</span> search</span></div></section>';
    if (!isM && L.lwvRace) h += '<p class="note">Campaign sites and answers as listed in the League of Women Voters of the Austin Area 2026 Voters Guide. Links open outside Ballotta. We link to every candidate the same way, say so when something’s missing, and never write about candidates ourselves.</p>';
    else if (!isM) h += '<p class="note">The League of Women Voters guide doesn’t cover this race.</p>';
    N().innerHTML = h;
    N().querySelectorAll('[data-act]').forEach(btn => btn.addEventListener('click', () => act(btn.dataset.act)));
  }
  function viewGlance() {
    let rows = '', last = '';
    ballot.forEach(b => {
      const c = b.c, id = c.id, v = current(id), L = DATA.learn[id] || {}, lw = (L.src || []).find(s => s.lwv);
      if (ui.hideUnopp && isUnopp(c)) return;
      if (c.level !== last) { last = c.level; rows += '<tr class="dk-tg"><th colspan="4" scope="colgroup">' + esc(LEVEL_LABEL[last] || last) + '</th></tr>'; }
      const ctl = seats(c) > 1
        ? esc(v.length ? (v[0] === '__skip' ? 'Skipping' : v.join(', ')) : 'Undecided') + ' · <button type="button" class="dk-link" data-go="' + id + '">Choose</button>'
        : '<select class="dk-sel" data-sel="' + id + '" aria-label="Your pick: ' + esc(cleanTitle(c)) + '"><option value="">Pick one…</option>' + optionsOf(c).map(o => '<option value="' + esc(o) + '"' + (v[0] === o ? ' selected' : '') + '>' + esc(optLabel(c, o)) + '</option>').join('') + '<option value="__skip"' + (v[0] === '__skip' ? ' selected' : '') + '>Skip</option></select>';
      const why = hasWhy(id) ? '<span class="dk-wt">' + esc(whys[id]) + '</span> <button type="button" class="dk-link" data-go="' + id + '" data-why="1">Edit</button>' : '<button type="button" class="dk-link muted" data-go="' + id + '" data-why="1">Add a reason…</button>';
      rows += '<tr data-tr="' + id + '"><th scope="row"><button type="button" class="dk-link" data-go="' + id + '">' + esc(cleanTitle(c)) + '</button>' + (isUnopp(c) ? '<small>Unopposed</small>' : '') + (b.conf === 'medium' ? '<small class="dk-chk">Double-check</small>' : '') + '</th><td>' + ctl + '</td><td>' + why + '</td><td>' + (lw ? '<a href="' + esc(lw.u) + '" target="_blank" rel="noopener">League guide, p. ' + esc(lw.u.split('#page=')[1] || '') + '</a>' : '<span class="note">—</span>') + '</td></tr>';
    });
    P().innerHTML = '<div class="dk-gh"><div><span class="ov">At a glance</span><h1>Your whole ballot</h1></div><label class="dk-tog"><input type="checkbox" id="dk-hideu"' + (ui.hideUnopp ? ' checked' : '') + '> Hide unopposed races</label></div>' +
      '<table class="dk-tbl"><thead><tr><th scope="col">Contest</th><th scope="col">Your pick</th><th scope="col">Your reason</th><th scope="col">Learn more</th></tr></thead><tbody>' + rows + '</tbody></table>';
    P().querySelectorAll('[data-sel]').forEach(sel => sel.addEventListener('change', () => {
      const id = sel.dataset.sel, v = current(id), val = sel.value;
      if (!val) { if (v.length) pick(id, v[0]); }       // "Pick one…" clears: pick() toggles the current choice off
      else if (v[0] !== val) pick(id, val);
    }));
    P().querySelectorAll('[data-go]').forEach(btn => btn.addEventListener('click', () => { go(btn.dataset.go, !btn.dataset.why); if (btn.dataset.why && $('dk-w')) $('dk-w').focus(); }));
    $('dk-hideu').addEventListener('change', () => { ui.hideUnopp = $('dk-hideu').checked; viewGlance(); $('dk-hideu').focus(); });
    N().innerHTML = '';
  }
  // Orientation labels for the map (approximate centers of well-known places).
  const PLACES = [['Downtown', -97.7431, 30.2672], ['UT campus', -97.7341, 30.2849], ['Zilker', -97.7729, 30.2669], ['East Austin', -97.7150, 30.2620],
    ['Mueller', -97.7050, 30.2980], ['The Domain', -97.7253, 30.4021], ['Pflugerville', -97.6200, 30.4394], ['Manor', -97.5569, 30.3405],
    ['Lakeway', -97.9795, 30.3638], ['Oak Hill', -97.8710, 30.2349], ['Del Valle', -97.6420, 30.2018], ['Sunset Valley', -97.8131, 30.2266]];
  function sitesNow() {
    const all = DATA.sites[period].map(s => ({ name: s[0], room: s[1], street: s[2], city: s[3], f: s[4], pt: [s[5], s[6]], d: here ? miles(here, [s[5], s[6]]) : null }));
    if (here) all.sort((a, b) => a.d - b.d); else all.sort((a, b) => a.name.localeCompare(b.name));
    return all;
  }
  function dotMap(all) {
    if (!here) return '<p class="note">Look up your address to see the closest vote centers on a map.</p>';
    const W = 560, H = 520, sx = 0.12, sy = sx * H / W * Math.cos(here[1] * Math.PI / 180);
    const X = (lon) => (lon - here[0] + sx / 2) / sx * W, Y = (lat) => (here[1] + sy / 2 - lat) / sy * H;
    const inView = (p) => X(p[0]) >= 8 && X(p[0]) <= W - 8 && Y(p[1]) >= 8 && Y(p[1]) <= H - 8;
    let g = '';
    for (let k = 50; k < W; k += 50) g += '<line x1="' + k + '" y1="0" x2="' + k + '" y2="' + H + '"></line>';
    for (let k = 50; k < H; k += 50) g += '<line x1="0" y1="' + k + '" x2="' + W + '" y2="' + k + '"></line>';
    const labels = PLACES.filter(p => inView([p[1], p[2]])).map(p => '<text x="' + X(p[1]).toFixed(0) + '" y="' + Y(p[2]).toFixed(0) + '">' + esc(p[0]) + '</text>').join('');
    const rest = all.slice(5).filter(s => inView(s.pt)).map(s => '<circle cx="' + X(s.pt[0]).toFixed(1) + '" cy="' + Y(s.pt[1]).toFixed(1) + '" r="6"' + (s.f.includes('L') ? ' class="late"' : '') + '><title>' + esc(s.name) + '</title></circle>').join('');
    const top = all.slice(0, 5).map((s, k) => [s, k]).filter(([s]) => inView(s.pt)).map(([s, k]) => '<g class="top"><circle cx="' + X(s.pt[0]).toFixed(1) + '" cy="' + Y(s.pt[1]).toFixed(1) + '" r="11"><title>' + esc(s.name) + '</title></circle><text x="' + X(s.pt[0]).toFixed(1) + '" y="' + (Y(s.pt[1]) + 4).toFixed(1) + '">' + (k + 1) + '</text></g>').join('');
    const you = '<g aria-hidden="true"><circle cx="' + W / 2 + '" cy="' + H / 2 + '" r="16" style="fill:#E9A92A;opacity:.3;stroke:none"></circle><rect x="' + (W / 2 - 6) + '" y="' + (H / 2 - 6) + '" width="12" height="12" rx="2" fill="#241A2E" transform="rotate(45 ' + W / 2 + ' ' + H / 2 + ')"></rect></g>';
    return '<svg class="dk-map" id="dk-map" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="Map of vote centers around your address, with the five closest numbered">' + g + labels + rest + top + you + '</svg>' +
      '<p class="note">Drawn on your device from the county’s list; no map company sees where you live. Numbers match the list. Gold dots stay open till 10pm Oct 29–30.</p>';
  }
  function viewVote() {
    const all = sitesNow(), list = (showAll || !here) ? all : all.slice(0, 5);
    const items = list.map((s, k) => {
      const tags = (s.f.includes('B') ? '<span class="chip">On a bus route</span>' : '') + (s.f.includes('L') ? '<span class="chip gold">Open till 10pm Oct 29–30</span>' : '') + (s.f.includes('F') ? '<span class="chip gold">Fri Oct 30 only</span>' : '');
      const dir = 'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(s.street + ', ' + s.city + ', TX');
      return '<li class="dk-site"><span class="dk-num' + (here && k < 5 ? '' : ' blank') + '" aria-hidden="true">' + (here && k < 5 ? k + 1 : '') + '</span><div class="site"><div class="top"><b>' + esc(s.name) + '</b>' + (s.d != null ? '<span class="note" style="white-space:nowrap">' + s.d.toFixed(1) + ' mi</span>' : '') + '</div><span class="addr">' + esc(s.street + ', ' + s.city) + ' · ' + esc(s.room) + '</span><div class="chips">' + tags + '<a href="' + dir + '" target="_blank" rel="noopener">Directions</a></div></div></li>';
    }).join('');
    const extra = [...$('vote').querySelectorAll(':scope > .sub:not(#hours), :scope > p.note')].map(e => e.outerHTML).join('');
    P().innerHTML = '<span class="ov">Where to vote</span><h1>Where and when to vote</h1>' +
      '<div class="dk-vote"><div><div class="seg" role="group" aria-label="Voting period"><button type="button" data-period="early" aria-pressed="' + (period === 'early') + '">Early voting · Oct 19–30</button><button type="button" data-period="eday" aria-pressed="' + (period === 'eday') + '">Election Day · Nov 3</button></div>' +
      '<p>You can vote at <b>any</b> vote center in Travis County.</p><div class="sub">' + $('hours').innerHTML + '</div>' +
      '<div style="display:flex;justify-content:space-between;align-items:center;gap:10px"><span class="ov">' + esc($('sitehead').textContent) + '</span>' + (here ? '<button type="button" class="dk-link" id="dk-all">' + (showAll ? 'Show closest 5' : 'See all ' + all.length) + '</button>' : '') + '</div>' +
      '<ul class="dk-sites" id="dk-sites">' + items + '</ul><a class="btn secondary small" href="' + esc($('waits').href) + '" target="_blank" rel="noopener">Check live wait times</a>' + extra + '</div>' +
      '<div>' + dotMap(all) + '</div></div>';
    P().querySelectorAll('[data-period]').forEach(btn => btn.addEventListener('click', () => { period = btn.dataset.period; renderVote(); viewVote(); }));
    if ($('dk-all')) $('dk-all').addEventListener('click', () => { showAll = !showAll; renderVote(); viewVote(); });
    N().innerHTML = '';
  }
  function cribPaper() {
    P().innerHTML = '<span class="ov">Crib sheet</span><h1>Print your notes</h1><p class="lead">Phones must be off in the room where you vote in Texas. Printed notes are allowed, so print this and bring it.</p><div class="dk-page' + (ui.two ? ' two' : '') + '" id="dk-page">' + $('crib').innerHTML + '</div>';
  }
  function viewCrib() {
    cribPaper();
    N().innerHTML = '<section><h3>Print options</h3><div class="sw"><label for="dk-cw">Include my reasons</label><input type="checkbox" role="switch" id="dk-cw"' + ($('withwhy').checked ? ' checked' : '') + '></div>' +
      '<div class="sw"><label for="dk-c2">Two columns</label><input type="checkbox" role="switch" id="dk-c2"' + (ui.two ? ' checked' : '') + '></div>' +
      '<div class="sw"><label for="dk-cu">Hide unopposed races</label><input type="checkbox" role="switch" id="dk-cu"' + (ui.hideCrib ? ' checked' : '') + '></div></section>' +
      '<button class="btn" type="button" data-act="print">Print crib sheet</button><p class="note">The printout has your picks and, if you choose, your reasons. Nothing else.</p>';
    $('dk-cw').addEventListener('change', () => { $('withwhy').checked = $('dk-cw').checked; renderCrib(); cribPaper(); });
    $('dk-c2').addEventListener('change', () => { ui.two = $('dk-c2').checked; $('crib').classList.toggle('two', ui.two); cribPaper(); });
    $('dk-cu').addEventListener('change', () => { ui.hideCrib = $('dk-cu').checked; renderCrib(); cribPaper(); });
    N().querySelectorAll('[data-act]').forEach(btn => btn.addEventListener('click', () => act(btn.dataset.act)));
  }

  /* ----- actions ----- */
  function act(a) {
    if (a === 'prev') { const i = idx(ui.cur); if (i > 0) go(ballot[i - 1].c.id); }
    else if (a === 'next') { const nx = nextUndecided(ui.cur); if (nx) go(nx.c.id); else setView('glance'); }
    else if (a === 'hidefriend') { if ($('f-hide')) $('f-hide').click(); render(); }
    else if (a === 'print') $('print').click();
  }
  function toLanding() { ui.landing = true; render(); window.scrollTo(0, 0); setTimeout(() => $('street').focus(), 50); }
  function info(which) {
    const box = $('dk-info');
    if (!box.dataset.built) {
      // Same words as the phone layout, copied from the page so the two never drift apart.
      const priv = document.createElement('section'), about = document.createElement('section');
      priv.id = 'dk-i-privacy'; about.id = 'dk-i-about';
      priv.innerHTML = '<h3>How your privacy works</h3>'; about.innerHTML = '<h3>About Ballotta &amp; sources</h3>';
      priv.append(document.querySelector('#lookup > p.note').cloneNode(true), document.querySelector('#d-keep > p.note').cloneNode(true));
      $('feedback').closest('footer').previousElementSibling.querySelectorAll('p').forEach(p => about.append(p.cloneNode(true)));
      box.append(priv, about); box.dataset.built = '1';
    }
    $('d-info').showModal();
    $('dk-i-' + which).scrollIntoView({ block: 'start' });
  }
  function menu(open) {
    $('dk-menu').classList.toggle('hidden', !open);
    $('dk-help').setAttribute('aria-expanded', open ? 'true' : 'false');
    if (open) $('dk-menu').querySelector('button').focus();
  }
  $('dk-help').addEventListener('click', () => menu($('dk-menu').classList.contains('hidden')));
  document.addEventListener('click', (e) => { if (!$('dk-menu').classList.contains('hidden') && !e.target.closest('.dk-menuwrap')) menu(false); });
  document.querySelector('.dk-menuwrap').addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !$('dk-menu').classList.contains('hidden')) { e.preventDefault(); menu(false); $('dk-help').focus(); }
  });
  document.querySelector('.dk-menuwrap').addEventListener('focusout', () => setTimeout(() => {
    const a = document.activeElement;
    if (a && a !== document.body && !a.closest('.dk-menuwrap')) menu(false);
  }, 0));
  $('dk-menu').addEventListener('keydown', (e) => {
    const items = [...$('dk-menu').querySelectorAll('button')], i = items.indexOf(document.activeElement);
    if (e.key === 'ArrowDown') { e.preventDefault(); items[(i + 1) % items.length].focus(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); items[(i - 1 + items.length) % items.length].focus(); }
  });
  $('dk-menu').querySelectorAll('[data-help]').forEach(btn => btn.addEventListener('click', () => {
    menu(false); $('dk-help').focus();  // the item is about to be hidden: give focus somewhere a closing window can return it
    const a = btn.dataset.help;
    if (a === 'feedback') $('feedback').click();
    else if (a === 'privacy' || a === 'about') info(a);
    else if (a === 'address') toLanding();
    else if (a === 'clear') { $('reset').click(); render(); }
  }));
  $('friend').addEventListener('click', (e) => { if (e.target.closest('#f-hide')) render(); });  // after the button's own handler
  $('dk-share').addEventListener('click', () => $('a-share').click());
  $('dk-keep').addEventListener('click', () => $('a-keep').click());
  $('dk-print').addEventListener('click', () => $('print').click());
  $('dk-back').addEventListener('click', () => { ui.landing = false; render(); });
  document.querySelectorAll('#dk-views button').forEach(btn => btn.addEventListener('click', () => setView(btn.dataset.view)));
  document.querySelectorAll('#dk-filt button').forEach(btn => btn.addEventListener('click', () => { ui.filter = btn.dataset.f; rail(); }));
  $('dk-q').addEventListener('input', () => { ui.q = $('dk-q').value.trim(); rail(); });
  $('dk-q').addEventListener('keydown', (e) => { if (e.key === 'Escape') { $('dk-q').value = ''; ui.q = ''; rail(); } });
  document.addEventListener('keydown', (e) => {
    if (!WIDE.matches || !ballot.length || ui.landing || e.metaKey || e.ctrlKey || e.altKey || e.defaultPrevented) return;
    if (document.querySelector('dialog[open]') || !$('dk-menu').classList.contains('hidden')) return;
    const t = e.target, typing = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable);
    if (typing) { if (e.key === 'Escape') t.blur(); return; }
    const k = e.key.length === 1 ? e.key.toLowerCase() : e.key;
    if (k === '/') { e.preventDefault(); $('dk-q').focus(); return; }
    if (ui.view !== 'decide') return;
    const b = curB();
    if (/^[1-9]$/.test(k)) { const o = optionsOf(b.c)[+k - 1]; if (o !== undefined) { e.preventDefault(); pick(b.c.id, o); } }
    else if (k === 's') { e.preventDefault(); pick(b.c.id, '__skip'); }
    else if (k === 'n') { e.preventDefault(); act('next'); }
    else if (k === 'j') { e.preventDefault(); const i = idx(b.c.id); if (i < ballot.length - 1) go(ballot[i + 1].c.id); }
    else if (k === 'k') { e.preventDefault(); act('prev'); }
    else if (k === 'r') { e.preventDefault(); $('dk-w').focus(); }
  });
  WIDE.addEventListener('change', render);

  /* ----- hooks the shared code calls (the DESK one-liners in showBallot, refresh, renderCrib and openFriend) ----- */
  return {
    render,
    ballot(meta) {
      ui.landing = false;
      if (!ballot.length) return render();
      const first = String(meta.where || '').split(' · ')[0];
      // The street is shown for this visit only; it is never saved (the saved ballot keeps just the precinct).
      ui.addr = /^Precinct /.test(first) ? '' : first.split(',')[0].toLowerCase().replace(/\b[a-z]/g, ch => ch.toUpperCase());
      if (idx(ui.cur) < 0) ui.cur = (nextUndecided('') || ballot[0]).c.id;
      render();
    },
    refresh() {
      if (!ballot.length) return;
      rail();
      if (ui.view === 'decide' && $('dk-next')) { $('dk-next').innerHTML = nextLabel(); notesDecide(); }
      else if (ui.view === 'crib') cribPaper();
    },
    cribSkip: (c) => ui.hideCrib && isUnopp(c),
  };
})();
window.desk = desk;
desk.render();
/*/DESK*/
/* ---------- start ---------- */
```
↳ This text starts with a line break (the empty first line) and ends with a line break.

## Task 6 — Tests: `tests/test_site.py`

Exact find/replace edits (T1–T10), then the new tests.

**T1.** Find (must occur exactly once):

```python
    python3 tests/test_site.py            # builds nothing; serves the repo root and runs every check
```
↳ This text ends with a line break.

Replace with:

```python
    python3 tests/test_site.py                                    # builds nothing; checks the live page (index.html)
    BALLOTTA_PAGE=next/index.html python3 tests/test_site.py      # checks the preview, laptop layout included
```
↳ This text ends with a line break.

**T2.** Find (must occur exactly once):

```python
import http.server, threading, functools, json, pathlib, re, sys, traceback, urllib.parse
```
↳ This text ends with a line break.

Replace with:

```python
import http.server, threading, functools, json, pathlib, re, sys, traceback, urllib.parse, hashlib, importlib.util, os
```
↳ This text ends with a line break.

**T3.** Find (must occur exactly once):

```python
BASE = f'http://127.0.0.1:{PORT}/index.html'
```
↳ This text ends with a line break.

Replace with:

```python
PAGE = os.environ.get('BALLOTTA_PAGE', 'index.html')
BASE = f'http://127.0.0.1:{PORT}/{PAGE}'
HAS_DESK = 'id="dk-app"' in (ROOT / PAGE).read_text(encoding='utf-8')
# sha256 of the live index.html as built from commit 0ae877c (Oct 14). The laptop layout must not change it until
# Lane promotes the preview. A data rebuild (ballot or League data) changes it legitimately: re-pin it in that commit.
LIVE_SHA = 'fcbf41e3792c67b0efedc81f5e12c6c3519437fa62a5be0640d222c7d7a0a7f5'
```
↳ This text ends with a line break.

**T4.** Find (must occur exactly once):

```python
def new_page(browser, sent=None):
    ctx = browser.new_context(viewport={'width': 400, 'height': 900}, permissions=['clipboard-read', 'clipboard-write'])
```
↳ This text ends with a line break.

Replace with:

```python
def new_page(browser, sent=None, wide=False):
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900} if wide else {'width': 400, 'height': 900}, permissions=['clipboard-read', 'clipboard-write'])
```
↳ This text ends with a line break.

**T5.** Find (must occur exactly 3 times):

```python
url.replace(url.split('/index.html')[0], f'http://127.0.0.1:{PORT}')
```
↳ No line break at the end: the text stops at the last character shown.

Replace with:

```python
url
```
↳ No line break at the end: the text stops at the last character shown.

**T6.** Find (must occur exactly 3 times):

```python
(ROOT / 'index.html').read_text()
```
↳ No line break at the end: the text stops at the last character shown.

Replace with:

```python
(ROOT / PAGE).read_text()
```
↳ No line break at the end: the text stops at the last character shown.

**T7.** Find (must occur exactly once):

```python

def main():
```
↳ This text starts with a line break (the empty first line) and ends with a line break.

Replace with:

```python

# ---------- laptop layout (preview build only; skipped when the page has no laptop layout) ----------
DESK_TESTS = set()
def desk_test(fn): TESTS.append(fn); DESK_TESTS.add(fn.__name__); return fn

def build_module():
    spec = importlib.util.spec_from_file_location('build_site', ROOT / 'source' / 'build_site.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def lookup_wide(pg, street='1000 Guadalupe St', zip_='78701'):
    pg.fill('#street', street); pg.fill('#zip', zip_); pg.click('#go')
    pg.wait_for_selector('body.dk-app-on', timeout=30000)
    pg.wait_for_function("/ of \\d+ decided$/.test(document.getElementById('dk-count').textContent)", timeout=30000)

def cur(pg, cid): return pg.evaluate(f"current('{cid}')")

@test
def live_build_is_unchanged_until_promotion(b):
    m = build_module()
    assert m.strip_desk('a\n/*DESK*/\nb\n/*/DESK*/\nc\n') == 'a\nc\n'                         # whole-line block
    assert m.strip_desk('x();/*DESK*/ y();/*/DESK*/\nz\n') == 'x();\nz\n'                       # inline block
    assert m.strip_desk('<i><!--DESK--><b><!--/DESK--></i>\n') == '<i></i>\n'
    try:
        m.strip_desk('/*DESK*/ x')
        unpaired_caught = False
    except AssertionError:
        unpaired_caught = True
    assert unpaired_caught, 'an unpaired marker must stop the build'
    live, prev = m.build(preview=False), m.build(preview=True)
    if m.DESK_LIVE:
        assert 'id="dk-app"' in live, 'promoted: the live page carries the laptop layout'
    else:
        assert 'id="dk-app"' not in live and 'DESK' not in live, 'laptop layout leaked into the live build'
        got = hashlib.sha256(live.encode('utf-8')).hexdigest()
        assert got == LIVE_SHA, f'live index.html changed ({got}). Expected only after a data rebuild: re-pin LIVE_SHA in that commit.'
    assert 'id="dk-app"' in prev and 'data-domains="preview.invalid"' in prev and 'src="../umami.js"' in prev
    assert "url('../fonts/" in prev and '[Preview]' in prev and 'data-domains="preview.invalid"' not in live

@desk_test
def desk_layout_header_and_rail(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE)
    assert pg.is_visible('#start') and pg.is_visible('.dk-steps') and pg.is_hidden('#dk-app') and pg.is_hidden('#dk-share')
    lookup_wide(pg)
    assert pg.is_hidden('main.wrap') and pg.is_visible('#dk-paper') and pg.is_visible('#dk-notes')
    loc = pg.inner_text('#dk-loc'); assert 'Precinct 300' in loc and '1000 Guadalupe St' in loc and 'change' in loc, loc
    h, s = pg.locator('#dk-help').bounding_box(), pg.locator('#dk-share').bounding_box()
    assert h['x'] + h['width'] <= s['x'], 'Help & info sits left of Share my picks'
    assert pg.locator('.dk-row').count() == 63 and pg.inner_text('#dk-count') == '0 of 63 decided'
    assert 'United States Senator' in pg.inner_text('#dk-paper h1')                                 # first undecided contest
    for width in (1280, 1366, 1440, 1920):                                                         # notes sit evenly between paper and edge
        pg.set_viewport_size({'width': width, 'height': 900})
        p, n = pg.locator('#dk-paper').bounding_box(), pg.locator('#dk-notes').bounding_box()
        left, mid, right = p['x'] - 288, n['x'] - (p['x'] + p['width']), width - (n['x'] + n['width'])
        assert min(left, mid, right) >= 23 and abs(mid - right) <= 2 and abs(left - mid) <= 2, (width, left, mid, right)
    pg.set_viewport_size({'width': 1440, 'height': 900})
    stored = json.dumps(pg.evaluate('Object.assign({}, localStorage)')).upper()
    assert 'GUADALUPE' not in stored, 'the street is shown for this visit only, never saved'
    ctx.close()

@desk_test
def desk_decide_pick_keys_and_sync(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c070"]')
    assert pg.inner_text('#dk-paper h1') == 'City Council Member, District 9'
    pg.locator('.dk-line', has_text='Qadri').click()
    assert pg.locator('.dk-line', has_text='Qadri').get_attribute('aria-pressed') == 'true'
    assert 'Qadri' in pg.inner_text('.dk-row[data-row="c070"]') and 'Qadri' in pg.inner_text('#sc070')   # phone layout agrees
    pg.keyboard.press('2'); assert cur(pg, 'c070') == ['Katie Kam']
    pg.keyboard.press('s'); assert cur(pg, 'c070') == ['__skip']
    pg.keyboard.press('s'); assert cur(pg, 'c070') == []
    pg.click('#dk-w'); pg.keyboard.type('Knows the district s')                                   # typing an "s" must not skip
    assert cur(pg, 'c070') == [] and pg.input_value('#wc070') == 'Knows the district s'
    assert pg.evaluate("JSON.parse(localStorage.getItem('ballotta.whys')).c070") == 'Knows the district s'
    pg.keyboard.press('Escape'); pg.keyboard.press('j')
    assert 'Proposition A' in pg.inner_text('#dk-paper h1')
    pg.keyboard.press('k'); assert pg.inner_text('#dk-paper h1') == 'City Council Member, District 9'
    pg.keyboard.press('n'); assert 'Proposition A' in pg.inner_text('#dk-paper h1')                  # next undecided after D9
    pg.keyboard.press('1'); assert cur(pg, 'c071') == ['FOR']
    pg.keyboard.press('/'); assert pg.evaluate('document.activeElement.id') == 'dk-q'
    pg.keyboard.type('Qadri'); assert pg.locator('.dk-row').count() == 1
    ctx.close()

@desk_test
def desk_learn_more_symmetric_and_measure(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c070"]')
    for row in pg.locator('#dk-paper .dk-lw').all():
        assert row.locator('.links > *').count() == 2, row.inner_text()                           # same two slots for everyone
    kai = pg.locator('#dk-paper .dk-lw', has_text='Kai Huang').inner_text()
    assert 'Didn’t answer the League guide' in kai and 'No campaign site listed' in kai, kai
    site = pg.locator('#dk-paper .dk-lw', has_text='Qadri').locator('a', has_text='Campaign site')
    assert site.get_attribute('href') == 'https://zoforaustin.com' and site.get_attribute('target') == '_blank'
    notes = pg.inner_text('#dk-notes')
    assert 'One of 10 district council members' in notes and 'League of Women Voters of the Austin Area 2026 Voters Guide' in notes
    pg.click('.dk-row[data-row="c071"]'); body = pg.inner_text('#dk-paper')
    assert 'principle of and interest in bonds' in body and '$65.5M' in body and '$14.34' in body and 'Supporters' not in body
    pg.click('.dk-line[data-pick="FOR"]'); assert pg.get_attribute('.dk-line[data-pick="FOR"]', 'aria-pressed') == 'true'
    pg.click('.dk-row[data-row="c034"]')
    assert 'Unopposed · no questions in the League guide' in pg.inner_text('#dk-paper') and pg.inner_text('.dk-meta').startswith('Unopposed')
    ctx.close()

@desk_test
def desk_glance_selects_and_filters(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('#dk-views [data-view="glance"]')
    pg.select_option('select[data-sel="c001"]', 'Ted Brown'); assert cur(pg, 'c001') == ['Ted Brown']
    assert pg.inner_text('#dk-count') == '1 of 63 decided'
    pg.select_option('select[data-sel="c001"]', ''); assert cur(pg, 'c001') == []
    pg.select_option('select[data-sel="c001"]', '__skip'); assert cur(pg, 'c001') == ['__skip']
    assert pg.locator('tr[data-tr="c034"]').count() == 1
    pg.check('#dk-hideu')
    assert pg.locator('tr[data-tr="c034"]').count() == 0 and pg.locator('tr[data-tr="c070"]').count() == 1
    a = pg.locator('tr[data-tr="c070"] a')
    assert a.inner_text() == 'League guide, p. 32' and a.get_attribute('href').endswith('#page=32'), a.inner_text()
    pg.click('#dk-filt [data-f="und"]'); assert pg.locator('.dk-row[data-row="c001"]').count() == 0
    pg.click('tr[data-tr="c071"] [data-why]')
    assert pg.evaluate('document.activeElement.id') == 'dk-w' and 'Proposition A' in pg.inner_text('#dk-paper h1')
    ctx.close()

@desk_test
def desk_where_to_vote_list_and_private_map(b):
    sent = []
    ctx, pg = new_page(b, sent, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('#dk-views [data-view="vote"]')
    rows = pg.locator('#dk-sites .dk-site'); assert rows.count() == 5
    d = [float(re.search(r'([\d.]+) mi', r.inner_text()).group(1)) for r in rows.all()]
    assert d == sorted(d) and d[0] < 1, d
    assert pg.locator('#dk-map .top').count() == 5 and 'Austin Recreation Center' in pg.inner_text('#dk-sites')
    pg.click('#dk-all'); assert pg.locator('#dk-sites .dk-site').count() == 45
    pg.click('[data-period="eday"]'); assert pg.locator('#dk-sites .dk-site').count() == 201
    assert 'Election%20Day' in pg.locator('#dk-paper a.btn').get_attribute('href')
    for u in sent:                                                                                # drawn on the page: no map service sees the address
        assert not re.search(r'tile|maps\.googleapis|openstreetmap|mapbox|arcgisonline', u), u
    ctx.close()

@desk_test
def desk_crib_options_and_print(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c001"]'); pg.locator('.dk-line', has_text='Ted Brown').click()
    pg.fill('#dk-w', 'Wanted a third option.')
    pg.click('#dk-views [data-view="crib"]')
    t034 = pg.evaluate("cleanTitle(BYID['c034'])")
    page = pg.inner_text('#dk-page'); assert 'Ted Brown' in page and t034 in page and 'Wanted a third option' not in page
    pg.check('#dk-cu'); assert t034 not in pg.inner_text('#dk-page') and t034 not in pg.inner_text('#crib')
    pg.check('#dk-cw'); assert 'Wanted a third option' in pg.inner_text('#dk-page') and pg.is_checked('#withwhy')
    pg.check('#dk-c2'); assert 'two' in pg.get_attribute('#crib', 'class') and 'two' in pg.get_attribute('#dk-page', 'class')
    pg.emulate_media(media='print')
    assert pg.is_visible('#crib') and pg.is_hidden('#dk-app') and pg.is_hidden('#dk-hdr')
    ctx.close()

@desk_test
def desk_help_menu_info_address_and_clear(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('#dk-help')
    assert pg.is_visible('#dk-menu') and pg.get_attribute('#dk-help', 'aria-expanded') == 'true'
    assert pg.evaluate('document.activeElement.dataset.help') == 'feedback'
    pg.keyboard.press('ArrowDown'); assert pg.evaluate('document.activeElement.dataset.help') == 'privacy'
    pg.keyboard.press('Escape'); assert pg.is_hidden('#dk-menu') and pg.evaluate('document.activeElement.id') == 'dk-help'
    pg.click('#dk-help'); pg.click('[data-help="privacy"]'); pg.wait_for_selector('#d-info[open]')
    t = pg.inner_text('#d-info')
    assert 'Ballotta never receives your address' in t and 'packed inside the link itself' in t and "isn't affiliated with Travis County" in t, t
    pg.keyboard.press('Escape'); assert pg.evaluate('document.activeElement.id') == 'dk-help', 'focus comes back to Help & info'
    pg.click('#dk-help'); pg.keyboard.press('Shift+Tab'); pg.keyboard.press('Escape')               # Escape from the button, menu open
    assert pg.is_hidden('#dk-menu'), 'Escape closes the menu from the Help & info button too'
    pg.click('#dk-help')
    for _ in range(6): pg.keyboard.press('Tab')                                                  # tab out of the menu
    pg.wait_for_selector('#dk-menu', state='hidden', timeout=2000)                              # leaving the menu with the keyboard closes it
    pg.click('#dk-help'); pg.click('[data-help="address"]')
    assert pg.is_visible('#start') and pg.is_visible('#dk-back') and pg.is_hidden('#dk-app')
    pg.click('#dk-back'); assert pg.is_visible('#dk-paper')
    pg.click('.dk-row[data-row="c001"]'); pg.locator('.dk-line', has_text='Ted Brown').click()
    pg.once('dialog', lambda d: d.accept())
    pg.click('#dk-help'); pg.click('[data-help="clear"]')
    assert cur(pg, 'c001') == [] and pg.locator('.dk-line[aria-pressed="true"]').count() == 0 and pg.inner_text('#dk-count') == '0 of 63 decided'
    ctx.close()

DESK_FRIEND = {'v': 1, 'n': 'Maya', 'c': 'deskfrnd', 'g': 1, 'p': {'70': 2, '71': 0}, 'w': {'70': 'Knows the district.'}}

@desk_test
def desk_friend_link_landing_and_inline(b):
    ctx, pg = new_page(b, wide=True); fresh_goto(pg, link('s', DESK_FRIEND)); pg.wait_for_selector('#friend:not(.hidden)')
    assert 'Maya shared 2 picks' in pg.inner_text('#friend') and 'See Maya’s picks beside yours' in pg.inner_text('#dk-fcta')
    assert pg.is_hidden('#f-own') and pg.is_hidden('.dk-steps') and pg.locator('#start h1').is_hidden()
    lookup_wide(pg)
    assert pg.is_visible('.dk-fchip') and pg.locator('.dk-row[data-row="c070"] .dk-fa').count() == 1
    pg.click('.dk-row[data-row="c070"]')
    fp = pg.locator('#dk-paper .dk-lw', has_text='Qadri').inner_text(); assert 'Maya picked this' in fp and 'Knows the district.' in fp, fp
    assert 'you and maya' in pg.inner_text('#dk-notes').lower()                                  # small caps on screen
    pg.locator('.dk-line', has_text='Qadri').click()
    assert pg.inner_text('.dk-fbox .dk-kv div:first-child b') == '1'
    pg.wait_for_function("(window.__events||[]).filter(e => e[0] === 'share_compare').length === 1")
    pg.click('.dk-row[data-row="c071"]'); pg.wait_for_timeout(300)
    assert names(pg).count('share_compare') == 1, 'counted once per friend link, not per screen'
    pg.click('.dk-fchip [data-act="hidefriend"]')
    assert pg.locator('#dk-app .dk-fa').count() == 0 and pg.is_hidden('#friend')
    ctx.close()

@desk_test
def desk_friend_hide_on_landing(b):
    ctx, pg = new_page(b, wide=True); fresh_goto(pg, link('s', DESK_FRIEND)); pg.wait_for_selector('#friend:not(.hidden)')
    pg.click('#f-hide')
    assert 'dk-friend' not in pg.evaluate('document.body.className') and pg.locator('#start h1').is_visible()
    assert pg.inner_text('#dk-fcta') == '' and pg.is_visible('.dk-steps'), 'back to the plain landing page'
    ctx.close()

@desk_test
def desk_friend_link_with_saved_ballot_counts_in_order(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    fresh_goto(pg, link('s', dict(DESK_FRIEND, c='ordered1'))); pg.wait_for_selector('.dk-fchip')
    pg.wait_for_function("(window.__events||[]).some(e => e[0] === 'share_compare')")
    seq = [n for n in names(pg) if n in ('share_opened', 'share_compare')]
    assert seq == ['share_opened', 'share_compare'], seq                                           # the open is counted before the compare
    ctx.close()

@desk_test
def desk_stays_quiet_on_phones(b):
    ctx, pg = new_page(b); fresh_goto(pg, link('s', DESK_FRIEND)); pg.wait_for_selector('#friend:not(.hidden)')
    assert pg.is_hidden('#dk-hdr') and pg.is_hidden('#dk-app') and pg.is_visible('main.wrap') and pg.is_visible('#f-own')
    pg.click('#f-own'); lookup(pg); pg.wait_for_timeout(1000)
    assert names(pg).count('share_compare') == 0, 'the hidden laptop layout must not count a compare'
    pg.evaluate('document.activeElement.blur()')                                                # not typing in the address box
    pg.keyboard.press('1'); assert cur(pg, 'c001') == [], 'no laptop shortcuts on a phone'
    ctx.close()

@desk_test
def desk_resize_keeps_layouts_in_step(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c001"]'); pg.locator('.dk-line', has_text='Ted Brown').click()
    pg.set_viewport_size({'width': 400, 'height': 900})
    assert pg.is_visible('#result') and 'Ted Brown' in pg.inner_text('#sc001')
    pick(pg, 'c070', 'Qadri'); open_race(pg, 'c001'); pg.fill('#wc001', 'Typed on the phone')
    pg.set_viewport_size({'width': 1440, 'height': 900})
    assert 'Qadri' in pg.inner_text('.dk-row[data-row="c070"]') and pg.inner_text('#dk-count') == '2 of 63 decided'
    assert pg.input_value('#dk-w') == 'Typed on the phone', 'the paper on screen picks up a reason typed in the phone layout'
    ctx.close()

@desk_test
def desk_share_and_keep_open_as_centered_windows(b):
    ctx, pg = new_page(b, wide=True); pg.goto(BASE); lookup_wide(pg)
    pg.click('.dk-row[data-row="c001"]'); pg.locator('.dk-line', has_text='Ted Brown').click()
    pg.click('#dk-share'); pg.wait_for_selector('#d-share[open]')
    r = pg.locator('#d-share').bounding_box()
    assert abs(r['x'] + r['width'] / 2 - 720) < 4 and r['y'] > 40 and r['y'] + r['height'] < 860, r
    assert names(pg).count('share_sheet_open') == 1
    pg.click('#d-share [data-close]'); pg.click('#dk-keep'); pg.wait_for_selector('#d-keep[open]')
    ctx.close()

@desk_test
def desk_restore_link_on_laptop(b):
    ctx, pg = new_page(b, wide=True)
    fresh_goto(pg, link('k', {'v': 1, 'pr': '300', 'b': [1, 70], 'p': {'70': 2}, 'w': {'70': 'Knows'}}))
    pg.wait_for_selector('#d-restore[open]'); pg.click('#restore-go')
    pg.wait_for_selector('body.dk-app-on')
    assert pg.inner_text('#dk-count') == '1 of 2 decided'
    loc = pg.inner_text('#dk-loc'); assert 'Precinct 300' in loc and 'Guadalupe' not in loc, loc
    ctx.close()

@desk_test
def desk_hostile_friend_is_escaped(b):
    o = {'v': 1, 'n': '<img src=x onerror=alert(1)>', 'c': 'abc', 'g': 1, 'p': {'70': 0}, 'w': {'70': '<script>x</script>'}}
    ctx, pg = new_page(b, wide=True); fresh_goto(pg, link('s', o)); pg.wait_for_selector('#friend:not(.hidden)')
    assert pg.locator('#dk-fcta img').count() == 0
    lookup_wide(pg); pg.click('.dk-row[data-row="c070"]')
    assert pg.locator('#dk-app img').count() == 0 and pg.locator('#dk-app script').count() == 0
    assert '<script>x</script>' in pg.inner_text('#dk-paper') and '<img src=x' in pg.inner_text('#dk-notes')
    ctx.close()

@desk_test
def desk_phone_layout_matches_live_page(b):
    # Phones must not change: the preview at phone width is pixel-for-pixel the live page, before and after a lookup.
    shots = []
    for page in ['index.html', PAGE]:
        ctx, pg = new_page(b); pg.goto(f'http://127.0.0.1:{PORT}/{page}'); pg.wait_for_timeout(600)
        first = pg.screenshot(full_page=True)
        lookup(pg); open_race(pg, 'c070'); pg.evaluate('window.scrollTo(0, 0)'); pg.wait_for_timeout(600)
        shots.append((first, pg.screenshot(full_page=True))); ctx.close()
    assert shots[0][0] == shots[1][0], 'landing differs from the live page at phone width'
    assert shots[0][1] == shots[1][1], 'ballot differs from the live page at phone width'

def main():
```
↳ This text starts with a line break (the empty first line) and ends with a line break.

**T8.** Find (must occur exactly once):

```python
    failed = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        for fn in TESTS:
            try:
```
↳ This text ends with a line break.

Replace with:

```python
    failed = skipped = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        for fn in TESTS:
            if fn.__name__ in DESK_TESTS and not HAS_DESK:
                skipped += 1; print('SKIP', fn.__name__, '- no laptop layout in', PAGE); continue
            try:
```
↳ This text ends with a line break.

**T9.** Find (must occur exactly once):

```python
    print(f'{len(TESTS) - failed}/{len(TESTS)} passed')
```
↳ This text ends with a line break.

Replace with:

```python
    ran = len(TESTS) - skipped
    print(f'{ran - failed}/{ran} passed' + (f', {skipped} skipped' if skipped else '') + f' ({PAGE})')
```
↳ This text ends with a line break.

**T10.** Find (must occur exactly once):

```python
    assert '<script defer src="umami.js"' in src and 'cloud.umami.is/script.js"' not in src                             # A14
```
↳ This text ends with a line break.

Replace with:

```python
    assert re.search(r'<script defer src="(\.\./)?umami\.js"', src) and 'cloud.umami.is/script.js"' not in src            # A14
```
↳ This text ends with a line break.

T7 inserts the new tests directly above `def main():`.

What the 17 new checks cover (one build check + 16 laptop checks, skipped automatically when the page under test has no laptop layout):

| Test | Proves |
|---|---|
| `live_build_is_unchanged_until_promotion` | Marker stripping (whole-line, inline, unpaired → build stops); live build sha256 = pinned `LIVE_SHA` until `DESK_LIVE`; preview has the layout, `../` assets, the never-matching tracker domain |
| `desk_layout_header_and_rail` | Landing → lookup → app; header text; Help & info left of Share; 63 outline rows; equal gutters of at least 24px at 1280, 1366, 1440 and 1920 wide; street never saved |
| `desk_decide_pick_keys_and_sync` | Click and keyboard picks, skip, reason syncs to the phone box and storage, typing never triggers shortcuts, J/K/N, / search |
| `desk_learn_more_symmetric_and_measure` | Two link slots for every candidate, new-tab links, office note and League attribution, measure facts, unopposed wording |
| `desk_glance_selects_and_filters` | Dropdown pick / clear / skip, hide unopposed, League page link, Undecided filter, "Add a reason…" jumps to the reason box |
| `desk_where_to_vote_list_and_private_map` | 5 closest, sorted; 5 numbered dots; See all 45; Election Day 201; wait-times link; no map-service requests |
| `desk_crib_options_and_print` | Preview matches the printout; hide unopposed; reasons on; two columns; printing shows only the crib |
| `desk_help_menu_info_address_and_clear` | Menu keyboard (focus, arrows, Escape from the list or the button closes it and returns focus, Tab out closes it); privacy/about text; focus returns to Help & info when that window closes; Change address → landing → back; Clear my picks |
| `desk_friend_link_landing_and_inline` | Friend landing; badges, "Maya picked this", You and Maya counts; `share_compare` once per link; Hide |
| `desk_friend_hide_on_landing` | "Hide these picks" on the laptop landing page returns to the plain landing page |
| `desk_friend_link_with_saved_ballot_counts_in_order` | A friend link opened over a saved ballot counts `share_opened` before `share_compare` |
| `desk_stays_quiet_on_phones` | At phone width the laptop layout is hidden, counts nothing, takes no shortcuts |
| `desk_resize_keeps_layouts_in_step` | Picks and a reason made in one layout show in the other after resizing |
| `desk_share_and_keep_open_as_centered_windows` | Share and Keep open as centered windows from the header and rail |
| `desk_restore_link_on_laptop` | A keep link restores straight into the laptop layout (precinct only in the header) |
| `desk_hostile_friend_is_escaped` | A hostile name and reason render as text everywhere in the laptop layout |
| `desk_phone_layout_matches_live_page` | At phone width the preview is pixel-for-pixel the live page, before and after a lookup |

## Task 7 — README

Exact find/replace edits in `README.md`, read the same way as Task 2's:

**R1.** Find (must occur exactly once):

```markdown
### Anonymous counts
```
↳ This text ends with a line break.

Replace with:

```markdown
### Laptop layout (preview)

On screens 1024px and wider the page switches to a laptop layout: a plum column with your ballot's outline (search, filters, progress), one contest at a time on a white "paper" with the office note and neutral sources beside it, keyboard shortcuts (1–9 pick, S skip, N next undecided, J/K next and previous, R reason, / search), an at-a-glance table, where to vote with a map drawn on the page (no map service sees your address), and a crib-sheet preview with print options. Phones keep the existing layout, pixel for pixel. Both layouts read the same picks and reasons, so resizing a window never loses anything.

The laptop code is marked in `source/template-travis.html` (`/*DESK*/ … /*/DESK*/` in CSS and JS, `<!--DESK--> … <!--/DESK-->` in HTML). Until it's approved, `build_site.py` strips those blocks from the live page, so `index.html` stays byte-for-byte what it was (a test checks its fingerprint), and `build_site.py --preview` writes `next/index.html`, served at https://ballotta.org/next/, with the laptop layout on. The preview loads the same tracker with a domain list no real site matches, so it never counts anything. To promote: set `DESK_LIVE = True` in `source/build_site.py`, rebuild, and replace `next/index.html` with a redirect to the main page.

### Anonymous counts
```
↳ This text ends with a line break.

**R2.** Find (must occur exactly once):

```markdown
`share_own_ballot`, `share_compare`,
```
↳ No line break at the end: the text stops at the last character shown.

Replace with:

```markdown
`share_own_ballot`, `share_compare` (on a laptop, once per friend link when their picks first appear beside your ballot),
```
↳ No line break at the end: the text stops at the last character shown.

**R3.** Find (must occur exactly once):

```markdown
python3 source/build_site.py                        # writes index.html
python3 tests/test_site.py                          # end-to-end checks (Playwright, live county services)
```
↳ This text ends with a line break.

Replace with:

```markdown
python3 source/build_site.py                        # writes index.html
python3 source/build_site.py --preview              # writes next/index.html (laptop layout preview)
python3 tests/test_site.py                          # end-to-end checks (Playwright, live county services)
BALLOTTA_PAGE=next/index.html python3 tests/test_site.py   # the same checks against the preview, plus the laptop ones
```
↳ This text ends with a line break.


## Task 8 — Build, prove the syntax check can fail, run both suites

```bash
cd /home/claude/ballotta
python3 source/build_site.py && sha256sum index.html && git status --short index.html
# expect: "index.html 264 KB", fcbf41e3…a7f5, and no status line for index.html (live page unchanged)
python3 source/build_site.py --preview                                     # expect: next/index.html 315 KB
node -e "try{new Function('const a=1; const a=2;');console.log('CHECKER BROKEN')}catch(e){console.log('checker catches errors')}"
# L19: expect "checker catches errors" before trusting the next line
node -e "const h=require('fs').readFileSync('next/index.html','utf8');const re=/<script>([\s\S]*?)<\/script>/g;let m,i=0;while((m=re.exec(h))){new Function(m[1]);i++}console.log(i,'inline scripts parse')"
# expect: 2 inline scripts parse
```

```bash
cd /home/claude/ballotta && timeout 590 python3 tests/test_site.py | tail -1
# expect: 20/20 passed, 16 skipped (index.html)        (under a minute)
```

```bash
cd /home/claude/ballotta && timeout 590 env BALLOTTA_PAGE=next/index.html python3 tests/test_site.py | tail -1
# expect: 36/36 passed (next/index.html)               (one to two minutes)
```

The tests use the live Travis County and Census services; a county outage fails lookups in both runs alike (rerun later rather than "fixing" tests).

## Task 9 — Mutation kill (RED-first, L17)

Save this as `/tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/mutate_desk.py` (the session scratchpad, not the repo). Run from the repo root after Task 8's builds. It first runs every target test unmutated and stops if any fails, then changes one thing at a time from an in-memory copy and restores it in a `finally` (never git, L2). After each kill it reruns the killing tests on the restored file and stops with INCONCLUSIVE if they fail there too, so a county-service hiccup can't pass for a kill. A kill is reported with the exception's type.

```python
"""Mutation-kill check for the laptop-layout tests: every mutant must turn at least one named test RED.
Files are restored from an in-memory copy in a finally block (never git).
Run from the repo root after both builds:  python3 <this file> [first last]   (a slice of the list, e.g. 0 10)"""
import os, sys, pathlib
os.environ['BALLOTTA_PAGE'] = 'next/index.html'
ROOT = pathlib.Path.cwd()
sys.path.insert(0, str(ROOT / 'tests'))
import test_site as T
from playwright.sync_api import sync_playwright

PREV, TPL, BLD = ROOT / 'next/index.html', ROOT / 'source/template-travis.html', ROOT / 'source/build_site.py'
M = [
 ('M1 live page changes', TPL, '<title>Ballotta ·', '<title>Ballotta  ·', ['live_build_is_unchanged_until_promotion']),
 ('M2 block stripping gone', BLD, "    html = re.sub(r'^[ \\t]*' + OPEN", "    0 and re.sub(r'^[ \\t]*' + OPEN", ['live_build_is_unchanged_until_promotion']),
 ('M3 paper picks not wired', PREV, "P().querySelectorAll('[data-pick]').forEach(btn => btn.addEventListener('click', () => pick(btn.dataset.c, btn.dataset.pick)));", '', ['desk_decide_pick_keys_and_sync']),
 ('M4 shortcuts fire while typing', PREV, "if (typing) { if (e.key === 'Escape') t.blur(); return; }", '', ['desk_decide_pick_keys_and_sync']),
 ('M5 reason not mirrored to phone box', PREV, "const pw = $('w' + c.id); if (pw) pw.value = ta.value;", '', ['desk_decide_pick_keys_and_sync']),
 ('M6 candidate links dropped', PREV, "k, candLinks(L, opts[k]));", "k, '');", ['desk_learn_more_symmetric_and_measure']),
 ('M7 glance cannot clear', PREV, "if (!val) { if (v.length) pick(id, v[0]); }", "if (!val) {}", ['desk_glance_selects_and_filters']),
 ('M8 hide-unopposed ignored', PREV, "      if (ui.hideUnopp && isUnopp(c)) return;\n", '', ['desk_glance_selects_and_filters']),
 ('M9 four numbered dots', PREV, "const top = all.slice(0, 5)", "const top = all.slice(0, 4)", ['desk_where_to_vote_list_and_private_map']),
 ('M10 crib hide ignored', PREV, "cribSkip: (c) => ui.hideCrib && isUnopp(c),", "cribSkip: (c) => false,", ['desk_crib_options_and_print']),
 ('M11 app shown in print', PREV, ".dk-hdr,.dk-app,.dk-steps,.dk-fcta,.dk-back{display:none}", ".dk-steps,.dk-fcta,.dk-back{display:none}", ['desk_crib_options_and_print']),
 ('M12 menu Escape loses focus', PREV, "{ e.preventDefault(); menu(false); $('dk-help').focus(); }", "{ e.preventDefault(); menu(false); }", ['desk_help_menu_info_address_and_clear']),
 ('M13 privacy text missing', PREV, "priv.append(document.querySelector('#lookup > p.note').cloneNode(true), ", "priv.append(", ['desk_help_menu_info_address_and_clear']),
 ('M14 compare counted on phones', PREV, "if (app && friend && WIDE.matches && ui.cmpFor !== friend)", "if (app && friend && ui.cmpFor !== friend)", ['desk_stays_quiet_on_phones']),
 ('M15 compare counted per screen', PREV, "if (app && friend && WIDE.matches && ui.cmpFor !== friend)", "if (app && friend && WIDE.matches)", ['desk_friend_link_landing_and_inline']),
 ('M16 refresh hook gone', PREV, "renderCompare();/*DESK*/ if (window.desk) desk.refresh();/*/DESK*/", "renderCompare();", ['desk_glance_selects_and_filters', 'desk_decide_pick_keys_and_sync']),
 ('M16b no redraw on resize', PREV, "  WIDE.addEventListener('change', render);\n", '', ['desk_resize_keeps_layouts_in_step']),
 ('M17 friend reason unescaped', PREV, "' · “' + esc(friend.W[c.id]) + '”'", "' · “' + friend.W[c.id] + '”'", ['desk_hostile_friend_is_escaped']),
 ('M18 dialogs stay bottom sheets', PREV, "  dialog.sheet{max-width:520px;margin:auto;border-radius:16px;padding:24px 28px}\n", '', ['desk_share_and_keep_open_as_centered_windows']),
 ('M19 ballot hook gone', PREV, "renderVote();/*DESK*/ if (window.desk) desk.ballot(meta);/*/DESK*/", "renderVote();", ['desk_layout_header_and_rail', 'desk_restore_link_on_laptop']),
 ('M20 street saved', PREV, "      if (idx(ui.cur) < 0) ui.cur = (nextUndecided('') || ballot[0]).c.id;", "      LS.set('ballotta.addr', ui.addr); if (idx(ui.cur) < 0) ui.cur = (nextUndecided('') || ballot[0]).c.id;", ['desk_layout_header_and_rail']),
 ('M21 friend hook gone', PREV, "  }/*DESK*/ if (window.desk) desk.render();/*/DESK*/\n}\nlet wantCompare", "  }\n}\nlet wantCompare", ['desk_friend_link_landing_and_inline']),
 ('M25 compare counted before open', PREV, "  f.classList.remove('hidden');\n", "  f.classList.remove('hidden'); if (window.desk) desk.render();\n", ['desk_friend_link_with_saved_ballot_counts_in_order']),
 ('M26 focus lost after Help window', PREV, "menu(false); $('dk-help').focus();  //", "menu(false);  //", ['desk_help_menu_info_address_and_clear']),
 ('M27 menu stays open after Tab', PREV, "    if (a && a !== document.body && !a.closest('.dk-menuwrap')) menu(false);", "", ['desk_help_menu_info_address_and_clear']),
 ('M28 no gutters at 1280', PREV, "justify-content:space-evenly;gap:24px;align-items:start;min-width:0;padding:28px 24px 64px}", "justify-content:space-evenly;align-items:start;min-width:0;padding:28px 0 64px}", ['desk_layout_header_and_rail']),
 ('M29 hiding a friend leaves the landing broken', PREV, "  $('friend').addEventListener('click', (e) => { if (e.target.closest('#f-hide')) render(); });", "", ['desk_friend_hide_on_landing']),
 ('M30 Escape only inside the list', PREV, "    if (e.key === 'Escape' && !$('dk-menu').classList.contains('hidden')) { e.preventDefault(); menu(false); $('dk-help').focus(); }", "", ['desk_help_menu_info_address_and_clear']),
 ('M22 phone takes laptop shortcuts', PREV, "if (!WIDE.matches || !ballot.length || ui.landing", "if (!ballot.length || ui.landing", ['desk_stays_quiet_on_phones']),
 ('M24 phone spacing lost', PREV, "#start{display:flex;flex-direction:column;gap:18px}", '', ['desk_phone_layout_matches_live_page']),
 ('M23 uneven gutters', PREV, "justify-content:space-evenly", "justify-content:center", ['desk_layout_header_and_rail']),
]
if len(sys.argv) > 2: M = M[int(sys.argv[1]):int(sys.argv[2])]   # run the list in slices if a shell caps how long a command may take
srv = T.serve(); res = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        # A kill only means something if the same tests pass without the mutant (a county outage fails them all).
        for tn in sorted({t for m in M for t in m[4]}):
            getattr(T, tn)(b)
        print('baseline: every target test passes unmutated', flush=True)
        for name, f, a, z, tests in M:
            orig = f.read_text(encoding='utf-8')
            assert orig.count(a) == 1, (name, 'anchor found', orig.count(a), 'times')
            f.write_text(orig.replace(a, z), encoding='utf-8')
            try:
                killed = []
                for tn in tests:
                    try: getattr(T, tn)(b)
                    except Exception as e: killed.append(tn + ':' + type(e).__name__)   # AssertionError, or a Playwright timeout
                res.append((name, 'KILLED' if killed else 'SURVIVED', ','.join(killed)))
            finally:
                f.write_text(orig, encoding='utf-8')
            # A kill counts only if the same tests pass again on the restored file (a service hiccup fails both).
            for tn in [k.split(':')[0] for k in killed]:
                try: getattr(T, tn)(b)
                except Exception as e: raise SystemExit(f'INCONCLUSIVE {name}: {tn} also fails unmutated ({type(e).__name__}); rerun later')
            print(*res[-1], flush=True)
        b.close()
finally:
    srv.shutdown()
print(sum(r[1] == 'KILLED' for r in res), 'of', len(res), 'mutants killed')
```

```bash
cd /home/claude/ballotta && timeout 590 python3 /tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/mutate_desk.py 0 10 | tail -1
# expect: 10 of 10 mutants killed
```

```bash
cd /home/claude/ballotta && timeout 590 python3 /tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/mutate_desk.py 10 20 | tail -1
# expect: 10 of 10 mutants killed
```

```bash
cd /home/claude/ballotta && timeout 590 python3 /tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/mutate_desk.py 20 31 | tail -1
# expect: 11 of 11 mutants killed (31 in all)
```

```bash
cd /home/claude/ballotta && python3 source/build_site.py && python3 source/build_site.py --preview && sha256sum index.html && git status --short
# files restored: expect fcbf41e3…a7f5, then only README.md, source/build_site.py, source/template-travis.html, tests/test_site.py, next/
```

Any SURVIVED line: strengthen the test until the mutant dies, then rerun Task 8.

## Task 10 — Adversarial audit before any commit (remediation-audit, L7/L8/L20)

Re-read the ritual first (L20): this step and Task 11's checks are owed **before** the push.

**Pass 1.** Tar the working tree to the scratchpad (`tar czf /tmp/claude-0/-home-claude-ballotta/7d9da39c-ec33-5dbf-8988-21abbb8a6e22/scratchpad/ballotta-desk.tgz -C /home/claude ballotta`) and dispatch one independent agent with no context, with this prompt (verbatim lines in quotes are mandatory):

- "Do not run any git command (not even status/diff) against /home/claude/ballotta; work on a copy: extract the tarball into your own folder."
- "Break this. Write and run a script that actually demonstrates any bug you claim; a bug you cannot reproduce is a hypothesis and must be labeled as such. Label each finding PRE-EXISTING or INTRODUCED."
- The diff: `source/build_site.py`, the marked blocks and hooks in `source/template-travis.html`, `tests/test_site.py`, built `index.html` and `next/index.html`.
- Attack surfaces to enumerate:
  1. Every `innerHTML` the laptop script writes: a friend's name and reasons from a link, contest titles and candidate names from data, the search text echoed in "Nothing matches “…”".
  2. `strip_desk`: any marker arrangement that leaves partial code in the live build, or eats a neighbouring line.
  3. The four hooks run on phones too: any input that makes laptop code throw and break the phone flow (empty ballot, restored link with 1 contest, friend link with no picks, a contest id missing from the saved ballot).
  4. The keyboard handler: shortcuts while typing, with a dialog or the menu open, with modifier keys, during IME composition.
  5. Counting: the `share_compare` change; any path where the laptop layout counts on a phone or counts twice; anything personal in event details.
  6. Privacy: the street in the header must never reach storage, a link, the feedback email, or the tracker.
  7. Printing from the laptop layout: the printout is exactly the crib sheet.
  8. The preview tracker: prove it cannot send from ballotta.org/next/ (read the pinned `umami.js`).
  9. Accessibility: menu focus and Escape, dialogs, `aria-pressed`, `aria-current`, focus after picking from the outline.
  10. Resizing between layouts mid-edit (reason half typed, dialog open, menu open).
- Budget ~20 minutes. Afterwards, argue each finding down; fix the survivors RED-first (new test, mutant proves it, Task 8 suites).

**Pass 2** (only if Pass 1 changed code): a second agent, scoped to ONLY the reworked hunks: "This is attempt #2; rework is the highest-risk part of the diff. ~20 tool calls, at most 2 reproductions, everything else may be reported as HYPOTHESIS." Same no-git line. Stop at convergence: a third pass only if the second needed a non-trivial code change.

## Task 11 — Commit and push the preview

```bash
cd /home/claude/ballotta
git diff --quiet -- index.html && echo "live page unchanged"          # must print; otherwise stop
git add README.md source/build_site.py source/template-travis.html tests/test_site.py next/index.html docs/plans/2026-10-15-laptop-layout.md   # the plan: only if Lane's review changed it
git -c user.name="Lane Becker" -c user.email="3211673+lanebecker@users.noreply.github.com" commit -q -F - <<'MSG'
Preview the laptop layout at /next/ (live page unchanged)

Laptop screens (1024px and wider) get a plum ballot column, one contest at a time on a
paper with notes beside it, keyboard shortcuts, at a glance, a private map, and a crib
preview. Phones are unchanged. The live build strips the marked laptop code until
DESK_LIVE is set, so index.html keeps its exact bytes; next/index.html carries it.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01ESRbqS3dGWHQThLF6J7gxN
MSG
git push origin main
```

Then wait for GitHub Pages (about a minute) and check what's actually served:

```bash
curl -s https://ballotta.org/ | sha256sum                     # expect fcbf41e3…a7f5 (live page unchanged)
curl -s https://ballotta.org/next/ | grep -o '<title>[^<]*'    # expect: <title>[Preview] Ballotta · What's on your ballot? (Travis County test)
curl -s -o /dev/null -w '%{http_code}\n' https://ballotta.org/fonts/ZillaSlab-Bold.woff2   # expect 200 (the preview's ../fonts/ target)
```

Then send Lane the preview link with what to try (look up, pick with keys, glance, vote, crib, share, a friend link), and update `claude/ballotta-where-things-live.md` in the project.

## Task 12 — Lane's review rounds

Each change Lane asks for: confirm the design change with him first (L5), then edit → test RED-first → Task 8 → Task 10 (Pass 2 scoped to the change) → push to the preview. The live page stays untouched throughout (Task 11's two checks run after every push).

## Task 13 — Cold audit before promotion (cold-audit skill)

When Lane says the preview is right: one independent no-context agent audits the laptop layout (same no-git line; tarball; no severity hints, no "don't flag" list). Argue findings down; **file the survivors as GitHub issues before fixing** (milestone "Laptop layout: audit (Oct 2026)", via `gh api`), each fix commit with `Closes #N` before EACH number (L4). Fixes get remediation-audit Pass 1/2. Then a verification pass on the audit report.

## Task 14 — Promote (only on Lane's explicit "go")

1. In `source/build_site.py`, set `DESK_LIVE = True`.
2. `cd /home/claude/ballotta && python3 source/build_site.py` (the live page now carries the layout), then replace `next/index.html` with this redirect, so links made from the preview still open. (`build_site.py --preview` refuses to run once `DESK_LIVE` is True, so it can't overwrite this file by accident.)

```html
<!doctype html>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<title>Ballotta</title>
<script>location.replace('../' + location.hash);</script>
<p><a href="../">Ballotta has moved to the main page.</a></p>
```

3. Run `cd /home/claude/ballotta && timeout 590 python3 tests/test_site.py | tail -1`: all 36 run (the build test takes its "promoted" branch; the laptop tests now run against `index.html`); expect `36/36 passed (index.html)`. The `desk_phone_layout_matches_live_page` test compares `index.html` to itself after promotion, so it passes trivially; the phone half of the next plan replaces it.
4. Commit ("Turn on the laptop layout"), push, then `curl -s https://ballotta.org/ | grep -c 'id="dk-app"'` → `1`.
5. Update the README's "Laptop layout (preview)" heading and paragraph to describe it as live.

**Rollback** at any point after promotion: set `DESK_LIVE = False`, rebuild, push. The live page returns to the pre-laptop bytes (sha256 `fcbf41e3…a7f5`, unless the data has been rebuilt since).

## Lane's lessons cited (from `Claude.nosync/Projects/_infra/shared/LESSONS.md`)

- **L2** Never revert with `git checkout --` / `reset --hard` / `stash`, even in a scratch clone: save and restore in memory.
- **L3** Verify the base before building: `origin/main` and a baseline test count.
- **L4** Every fix commit carries `Closes #N`, with the keyword before EACH issue number.
- **L5** Confirm design changes with Lane before building on them.
- **L7** A green suite doesn't exempt a diff: adversarially audit it before commit.
- **L8** Reviewer-caused rework gets its own narrow second pass.
- **L17** Mutation-kill is a step you can point at: see each new test go red.
- **L19** Prove a checker can fail before trusting that it passed.
- **L20** Re-read the ritual before handing off; put the no-git rule in every agent dispatch.

## Verification pass (Oct 15): what it caught

An independent agent with no context executed this plan from its text alone and checked every claim. What it found, and what changed (the original text is struck through):

1. ~~E1, E2, E4, E5 and E10 replaced text like «the CSS block below», with the block shown separately and line breaks unstated.~~ Applied literally, the build crashed; with a newline after every block, the live page changed by one blank line. **Now** every REPLACE fence holds the complete text, each block states its line breaks, and the dry run applies the document literally.
2. ~~`$SCRATCH` set once in Task 0 and used in Tasks 8 and 10.~~ Shell variables don't carry over between commands here. **Now** absolute paths everywhere, and every block starts with its own `cd`.
3. ~~"Equal gutters" with `padding:28px 0` and no column gap.~~ At 1280px the paper touched the plum column and the notes touched the window edge. **Now** 24px minimum gutters and gap, tested at 1280, 1366, 1440 and 1920.
4. ~~Mutation runner counted any exception as a kill.~~ A no-op mutant was "KILLED" with the network blocked. **Now** it runs every target unmutated first and stops if any fails, and reports how each mutant died.
5. ~~Help & info → privacy → Escape left keyboard focus on the page body.~~ **Now** focus goes back to the Help & info button (tested, mutant M26).
6. ~~Tabbing out of the open menu left it open, which disabled every shortcut.~~ **Now** the menu closes when focus leaves it (tested, mutant M27).
7. ~~README edits came after the step whose expected output included them.~~ **Now** README is Task 7, before the builds and tests.
8. ~~Smaller slips in the expected output~~ ("no status lines" in Task 0, T-edits out of order, L-numbers undefined, `timeout 900` over the 10-minute shell cap). **Now** corrected, the T-edits are in order, the lessons are listed above, and runs use `timeout 590`.
9. ~~"The mock listed 1–5 and no R"~~: the mock's "Why?" label did show R. **Now** corrected, and four unlisted differences from the mocks are added (items 12–15).
10. ~~"The phone markup and code are untouched"; "Map shows 12 orientation labels"; "one setting flips"; the glance comment "picking the current value again clears it".~~ **Now** each says what's actually true.
11. ~~The friend hook ran before `openFriend`'s own counting~~, so a friend link opened over a saved ballot counted `share_compare` before `share_opened`. **Now** the hook is `openFriend`'s last statement (tested, mutant M25).
12. ~~After promotion, `--preview` would overwrite the redirect page.~~ **Now** it refuses once `DESK_LIVE` is True.

A **second, narrow pass** over just that rework (Oct 15) found:

13. ~~"Hide these picks" in the friend view on the laptop landing page~~ left a half-switched page (friend heading still shown, form alone in the right column). **Now** the laptop layout redraws after that button too (test `desk_friend_hide_on_landing`, mutant M29).
14. ~~"So an outage can't pass for a kill"~~: the baseline ran once, so a service failure later in the run could still look like kills. **Now** every kill is re-checked on the restored file.
15. ~~Notes flush under the paper between 1024 and 1279px~~ (column gap only). **Now** `gap:24px` both ways.
16. ~~Escape did nothing with focus on the Help & info button and the menu open.~~ **Now** Escape closes it from anywhere in the menu area (tested, mutant M30).
17. ~~R2's FIND and REPLACE ended with an invisible space.~~ **Now** they end on the comma.
18. ~~"The phone markup gains one wrapper"~~ understated the hidden laptop-only elements. **Now** listed.

Each fix is one or two lines with its own test proven red, so a third pass wasn't triggered (the skill's rule: a third pass only when the second needed a non-trivial code change).

Its numbers that held: the base, the sha256, every FIND count, the test sets matching the table and the mutants, the promotion run, the preview never counting, the street never being stored, the new-tab links, Help & info left of Share, phones pixel-identical at 320, 375, 400, 768 and 1023px wide, and escaping.

## Rough timing

Tasks 0–9: about an hour (the code is written and dry-run; the test and mutation runs take about 20 minutes of that). Task 10: about 30–45 minutes (two-core sandbox, agents run one at a time). Task 11: 10 minutes. So the preview can be up the same session Lane approves this plan, well before early voting starts Monday.

## Self-review (write-plan)

- **Spec coverage:** every screen on the canvas's laptop column maps to a task: landing (Task 3 E3/E4 + CSS), decide race and measure, at a glance, where to vote, crib sheet, friend arrival and decide-with-friend, share, keep, restore, help & info (Tasks 2–5); preview-first (Tasks 1, 11); live page unchanged (Tasks 1, 8, 11); phones unchanged (Task 6's pixel test). Deviations are listed above for Lane.
- **Placeholder scan:** `grep -nE 'TBD|appropriate error handling|write tests for the above|similar to Task|«' docs/plans/2026-10-15-laptop-layout.md` → only this line and the struck-through verification item 1.
- **Names and types:** element ids (`dk-*`), storage key `ballotta.desk`, hooks `desk.ballot / refresh / render / cribSkip`, test names and mutant names are identical across Tasks 2–9 (the plan is assembled from the dry-run files, and the dry run applies the plan's own text).

## Execution log (Oct 15)

- **Tasks 0–9** ran exactly as written: base `142ee7f` (this plan's commit on top of `0ae877c`), 19/19 baseline, the plan applied literally (byte-identical to the dry run), live sha256 unchanged, 20/20 + 16 skipped, 36/36, 31 of 31 mutants.
- **Task 10, remediation-audit Pass 1** (cold agent, executed reproductions) found 7; all fixed RED-first:
  1. A non-text reason in storage made laptop code throw inside a hook and stop `start()`, so a friend link never opened on phones. Now `hasWhy` checks the type, and all four hooks are wrapped in `try … catch`, so laptop code can never stop the shared flow.
  2. `share_compare` was counted on every reload, on links with no shared race, and twice across layouts. Now once per link code per browser (`ballotta.compared`), only when one of the friend's races is on your ballot, and labelled `{layout: 'laptop'}` so it isn't confused with the phone's Compare tap. **Deviation from item 10 above ("no new details"): Lane to confirm.**
  3. `strip_desk` could silently delete shared code if text followed a closing marker. Now a single loop both checks and removes blocks, and refuses any stray marker.
  4. Laptop print options stayed on after switching to the phone layout; now they reset.
  5. A held number key toggled the pick on and off; key repeat is now ignored for picks (and so is IME composition).
  6. J/K/N dropped keyboard focus; they now keep it on the paper.
  7. (Hypothesis, made defensive) IME composition guard.
- **Pass 2** (the rework only) found 2 real defects in that rework, both fixed RED-first: a real print (narrower than 1024px) was mistaken for a switch to the phone layout and wiped the print options, so the printout ignored them (now guarded by `beforeprint`/`afterprint`, tested with a real `page.pdf()`); and odd whitespace (CR, NBSP, form feed) after a closing marker still let a block swallow code (now one definition of "alone" for checking and removal). Also: the compare count could be blocked by a first view with no shared race (fixed); weak test spots tightened.
- **Pass 3** (that rework only): a stray marker *inside* a block could still swallow code (now refused); the PDF check now normalises wrapped lines and has a positive control; the print flag clears on the next key or tap in case a browser never sends `afterprint`. Converged.
- **Filed, not fixed (pre-existing, affects the live page):** #20, non-text reasons in storage make Keep and Share throw. It touches shared code outside the markers, which must stay byte-identical until promotion.
- **Final:** live sha256 `fcbf41e3…a7f5` unchanged; `20/20 passed, 18 skipped (index.html)`; `38/38 passed (next/index.html)`; **44 of 44 mutants killed**, each kill re-checked against the unmutated file. The mutation runner is kept at `tests/mutate_desk.py` (run from the repo root after both builds, in slices: `python3 tests/mutate_desk.py 0 15`, `15 30`, `30 44`).
- **Lane's first review round (Oct 15, morning):** the laptop reason box grows as you type and opens at full height for a long saved reason (phones unchanged until the phone round); the Why section is a "notes card" (Lane picked option A); the header button reads "Feedback & Info"; the paper and notes stay centred together, with the gap between them growing from 24px to at most 32px (1/3 inch, Lane) and only the outer margins growing after that. Scoped audit + narrow Pass 2: the page no longer jumps when typing at the bottom of a long reason. 48 of 48 mutants killed; 20/20 + 19 skipped, 39/39.
- **Lane's second review round (Oct 15, late morning): the landing page.** Lane picked option B of three mocked directions. The whole top bar is plum on the landing page; a full-width plum band holds a gold "For now, Ballotta only works for Travis County, Texas addresses." strip, a big logo, the tagline (Lane: "Don't wait to meet your ballot in the booth.") and a one-line description. The form's paper overlaps the band's foot, the side column starts below it, "Share my picks" turns gold on the plum bar, and a six-card "What's going on here?" FAQ (wording approved by Lane) sits under the form. It is laptop-only for now; phones get it in the phone round. RED-first test `desk_landing_plum_band_and_faq`, 23 landing mutants (L1–L23), all killed.
  - **Pass 1** (cold agent, executed reproductions) found, and we fixed RED-first: the FAQ privacy answer left out the U.S. Census geocoder fallback; "Show my ballot" fell below the fold in 1366×768 and 1024×768 windows (now a compact band below 880px of window height); "learn about every race" overclaimed, since 17 small districts have no neutral sources (now "the races"); "Share links can't use names like…" overclaimed, since look-alike letters get through (now "We try to block share names that pretend to be…"); and two test gaps (a hidden FAQ card still passed, so mutant L17 survived; the contrast check ignored transparency).
  - **Pass 2** (that rework only): the rework holds. On "Change address" the Back button pushed the form under the fold at 1024×821–860, so the compact cutoff moved from 820 to 880px; the opacity check now covers parent elements and filters. Converged.
  - **Copy changes to the approved wording, made for accuracy:** the FAQ privacy answer, "We try to block…", and "the races". Lane to see them in the preview.
  - **Filed, pre-existing:** #21 look-alike letters and "Dems" in share names; #22 the "change" link's focus ring is clipped; #23 a very long unbroken friend name scrolls the page sideways; #24 the friend card says every race links to neutral sources.
  - **Final:** live sha256 `fcbf41e3…a7f5` unchanged; 20/20 + 20 skipped (index.html); 40/40 (next/index.html). Run the landing mutants with `python3 tests/mutate_desk.py 48 71`.
- **Task 13, pre-launch cold audit (Oct 15, midday).** One independent agent audited the whole laptop layout. Survivors were filed under the milestone "Laptop layout: audit (Oct 2026)" (#25–#38; #13 efficiency was argued down: about 4ms per keystroke is fine).
  - **Fixed before launch, RED-first:**
    - #25: rail titles wrap, so "…Place 3" and "…Place 4" stay readable.
    - #26: a damaged or too-old link shows a dismissible notice above the paper when the app is open.
    - #27: a stale mutant anchor; the runner now checks every anchor first and picks the right page after promotion.
    - #28: the phone-parity test now builds both flavours in memory, so it still guards phones after promotion.
    - #30: single-key shortcuts act only on the ballot paper (WCAG 2.1.4); picks and skips are announced politely.
    - #31: `role=main` on the desk, and a `:focus-visible` ring on the paper.
    - #35: no key hints on touch screens.
  - **Pass 1 on those fixes:**
    - Shortcuts died after view tabs and dialogs; Decide by pointer now returns focus to the paper.
    - A warning stayed up after a good link or Change address.
    - The notice covered the friend's Hide button; it now sits in the page flow above the paper.
    - Screen readers heard rail titles twice; the tooltips were removed.
    - The mutation runner could leave the live page mutated on SIGTERM; a signal handler now restores it.
    - The parity test could leave temp files; it now serves both builds from memory.
    - New guard: pages on disk must equal what the build writes.
  - **Pass 2:**
    - '/' falls under the same 2.1.4 gate.
    - Keyboard activation of Decide keeps focus on the tab.
    - The notice scrolls into view when it appears.
    - Atomic mutant writes, and a second signal can't interrupt the restore.
    - `--preview` exits 0 after promotion.
  - **Pass 3:** converged (two Lows filed as #40 and #41). Pre-existing #39 (J/K/N are silent for screen readers) was filed too.
  - **Final:** live sha256 `fcbf41e3…a7f5` unchanged before promotion; 21/21 + 20 skipped (index.html); 41/41 (next/index.html); **89 of 89 mutants killed** (`python3 tests/mutate_desk.py 0 89`).

