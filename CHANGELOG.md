# Changelog

All notable changes to Ballotta (https://ballotta.org) are recorded here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`.

`VERSION` is the one source of truth for the current version; the live site reports it at
https://ballotta.org/version.json. To cut a release, see "Versioning" in the README. Releases before 1.0.0 were
numbered on Oct 17, 2026, from the commit history; each is tagged at the last commit of its day's work. Issue numbers
are GitHub issues; "audit #N" is a finding in `docs/audits/2026-10-17-cold-audit.md`.

---

## [Unreleased]

_Nothing yet._

## [1.0.0] — 2026-10-17

**Phones get the new layout.** The phone layout that was previewed at ballotta.org/next/ is now the main page, for
everyone, two days before early voting starts.

### Added
- **The phone layout on ballotta.org.** Narrower than 1024px, the page is the laptop's app folded up for a phone: a
  plum top bar ("Your ballot", with how many contests are decided, opens the whole ballot as a sheet; Feedback & Info;
  Share), one contest at a time on the paper with its notes behind a "Learn more" fold, and a bottom bar with
  "← Previous" and "Next undecided →".
- **Add to Home Screen.** Android shows the browser's own prompt; on an iPhone, steps that name and draw Safari's own
  buttons, a private picks link to carry your picks into the Home Screen app, and "Paste my picks link" there.
- **An offline copy for phones.** The page keeps a copy of itself and opens it when there's no connection (or the
  network takes more than 4 seconds), with a bar that says so and "Try again". It keeps the page from its first
  install, so it opens offline before a second visit. Laptops never get it.
- **Versioning.** `VERSION`, this changelog, `version.json` on the live site, release tags, and a check that keeps them
  in step (`source/check_release.py`, run by the build, the tests and a GitHub workflow).

### Changed
- **ballotta.org/next/ now sends people to the main page**, with any Keep or Share link made on the preview, and
  removes the preview's offline copy from phones that installed it (audit #21). The main page asks for that removal
  too, for a phone that only ever opens ballotta.org now; a failed request removes nothing. Anyone who added the
  preview to their Home Screen should add ballotta.org again.
- **A friend's picks are counted when they first appear beside your ballot at any width** (`share_compare`), not on a
  Compare tap, which the phone layout doesn't have.
- **Crib sheet print options survive a window narrowed below 1024px**, since a phone now shows them too.

### Fixed
- **The shared link stays on screen after "Share link".** Since Oct 14 the link just copied vanished at once, and
  where copying fails, so did the selected link you were meant to copy by hand.
- **The offline copy's first download gives up after 8 seconds** on a slow line, instead of holding up the copy (and
  any update behind it).
- **A rollback removes the offline copy.** Turning the phone layout off again now writes a `sw.js` that removes
  itself and its copies from phones.

### Tests
- The 31 tests that only ran on the old phone page are retired; 34 ports run on the live page (audit #29). Five
  laptop mutants that promotion made unreachable or redundant are retired; every other mutant is re-anchored.

## [0.6.1] — 2026-10-17

### Changed
- **Travis County MUD No. 41 reaches its voters.** Its 7 contests go to the addresses the county codes `M41`
  (precinct 142), marked "Double-check" until the Tax Office confirms the code (Lane's call; issue #56).

### Added
- **"The county's wait-times map fills in once voting starts Oct 19"** on the laptop's Where to vote view, as the
  old phone page always said.

## [0.6.0] — 2026-10-17

**What's on the ballot is the ballot** (cold audit wave 1).

### Fixed
- **Ten "vote for up to N" contests list their candidates in the ballot's order** (MUDs, an MMD, a WCID and a library
  district: c154, c168, c176, c179, c192, c199, c202, c203, c204, c214; audit #1). Keep and Share links still count
  those ten in the old order, so every link, old or new, means the same candidates to every version of the page.
- **37 measures no longer end in a stray Spanish caption** ("… Distrito de Austin Community"); every measure's text
  is now read straight from the county's corrected ballot PDF, English only (audit #2).

### Changed
- **The answer key rebuilds byte for byte from `source/ballot/build_answer_key.py`**, with the Oct 14 corrections in
  the script instead of hand-edited into the JSON (audit #3), and records the ballot PDF by its sha256.
- **The build stops** on a contest no address reaches (unless explained), an address with the wrong number of
  representatives, or a precinct missing from the Legislative Council table (audit #4); dropped ballot lines are
  printed, not silent (audit #5).

### Tests
- `tests/test_pipeline.py`: the key against the PDF (choice order, measure texts, line by line; party labels; the
  count of measures).

## [0.5.1] — 2026-10-17

### Changed
- **Laptop: At a glance's pick column fits every name on the ballot**, and its title matches the other views' size.
- **The "Crib sheet" tab is "Print your choices"**; its page is titled "Crib sheet", and the printout is headed "My
  ballot choices".
- **Every view's title sits the same distance below its small line**, as Decide's does.

### Added
- **The cold audit of Oct 17** (`docs/audits/2026-10-17-cold-audit.md`): 47 findings in six waves.

## [0.5.0] — 2026-10-16

### Added
- **A preview of the phone layout at ballotta.org/next/** (the live page unchanged): the laptop app folded up for a
  phone, Add to Home Screen and an offline copy with a kill switch (round G); Home Screen steps that name Safari's own
  buttons, and a bar that says when you're looking at the saved copy (round H); "Your ballot" as the top bar's title,
  "← Previous" and "Next undecided →" at the bottom (round I).

## [0.4.1] — 2026-10-15

**Issues rounds A, B and C.**

### Security
- **The page is locked down** (#36): a Content-Security-Policy built from the hashes of the page's own scripts, no
  referrer to any site, and the Census geocoder in a sandboxed frame (`census.html`) that hands back only a point.

### Fixed
- Saved picks, reasons, share names and generations are checked when read, so junk can't break Keep or Share
  (#20, #44); share names fold look-alike letters and party nicknames (#21, #43); a pick past "vote for up to N" is
  refused with a note that says why (#33); a tab left open past midnight moves to the new day (#34, #47); laptop
  announcements are queued so none is cut off (#45); and smaller fixes (#22–#24, #32, #46).

### Added
- A one-time card after the 5th pick (and at 25) suggests a backup link (#48); at the first pick, the page asks the
  browser to keep its data (#49).

## [0.4.0] — 2026-10-15

### Added
- **Private usage counts (Umami).** 25 named events behind an allow-list firewall that fails closed: no address, no
  picks, no candidate names, no query strings or #links. Do Not Track and Global Privacy Control send nothing at all.

## [0.3.0] — 2026-10-15

### Added
- **The laptop layout** (screens 1024px and wider): a plum column with your ballot's outline, search and filters; one
  contest at a time on a paper with notes beside it; keyboard shortcuts; At a glance; a map of vote centers drawn on
  the page; a crib sheet preview; Feedback & Info. A plum landing band with a gold "Travis County only" strip, the
  tagline "Don't wait to meet your ballot in the booth." and a FAQ. Phones unchanged.

## [0.2.1] — 2026-10-14

### Changed
- **The site moves to ballotta.org** (the old lanebecker.github.io address redirects there).
- **Keep and Share links are short and safe to paste into chat apps** (`#k2…`/`#s2…`, half as long; Messages was
  cutting the old ones); older links still open (#19).

## [0.2.0] — 2026-10-14

### Added
- **Learn more on every race:** an office note, and each candidate's campaign site and League of Women Voters guide
  answers, shown the same way for everyone and saying so when something is missing. Measures: the ballot text; Austin
  Props A–B in plain words, the money split and the City's tax estimate.
- **Where and when to vote:** 45 early and 201 Election Day vote centers, by distance, with late hours, bus routes,
  wait times and ID rules.
- **Keep my picks** (a private link to yourself) and **Share my picks** (a link for a friend, with what to include),
  a friend view and compare.
- Anonymous counts of a few actions; the About box points at the county's Voter Lookup.

## [0.1.0] — 2026-10-13

### Added
- **Ballotta's first test:** look up a Travis County address against the county's own voter-district data, see your
  Nov 3, 2026 ballot, make private picks with reasons, and print a crib sheet. Zilla Slab and Public Sans, self-hosted.
