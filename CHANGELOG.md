# Changelog

All notable changes to Ballotta (https://ballotta.org) are recorded here, newest first.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), plus a "Tests" section where the checks
changed. Versions follow [Semantic Versioning](https://semver.org/) as the README's "Versioning" section applies it.

`VERSION` is the one source of truth for the current version; the live site reports it at
https://ballotta.org/version.json. Releases before 1.0.0 were numbered on Oct 17, 2026, from the commit history, one
per milestone; each is tagged `v<version>` at the last commit of that milestone. Issue numbers are GitHub issues;
"audit #N" is a finding in `docs/audits/2026-10-17-cold-audit.md`.

---

## [Unreleased]

_Nothing yet._

## [1.1.2] — 2026-10-18

**Phone layout follow-ups** (cold audit wave 4).

### Fixed
- **On the laptop, "Next" never points at the contest already open** (#53). When it's the only undecided one, Next goes
  on in ballot order ("Next: …"), and from the last contest to At a glance ("Last contest · see At a glance").
- **A server error no longer beats the copy saved on a phone** (#74): a 5xx, 408 or 429 that arrives within 4 seconds (a
  deploy, a proxy, a rate limit) opens the kept page with the bar "Ballotta isn’t answering, so this is the copy saved on your phone." A 404
  is shown as it is, so a page that's really gone is never masked by its copy.
- **The saved-copy bar says when the site is back** (#73): once the site answers again, it reads "Ballotta is back."
  with Reload (Lane), where before it stayed until Try again on a slow line and vanished on "online" even when the site
  didn't answer. The page checks when it comes back into view, when the phone says it's online, and every 20 seconds;
  only an answer quick enough that Reload would really get the newer page counts, and if the site stops answering
  again the bar says so again.
- **The offline copy marks its page by the page's own opening tag**, whatever attributes it carries, so a template
  change can't quietly hide the saved-copy bar (#75); `/` and `/index.html` are one kept copy (#76).
- **The map shows all five closest vote centers from an outlying address** (#76): from Manor, Webberville, Lago Vista
  or Mustang Ridge, four or five of them were off the map. It widens just enough; closer in it is unchanged. Town names
  stay clear of the edges, and center 1 is drawn on top.
- **Phones: "Campaign site" and "League guide answers" are full-size (44px) tap targets** (#51).
- Smaller (#76): the map fold stays open when the vote view redraws; after an Android install, the tab stops offering
  "Add to your Home Screen"; a measure with nothing behind its fold shows no fold; a tablet that loads in landscape
  gets the offline copy once it's turned upright; Next from another view counts as opening a contest, as Back does;
  a share link with no readable picks isn't counted as opened; an open comparison follows a new friend's link; only
  contests and choices on today's ballot count as picks (filtered as they're read: what's stored is never trimmed, so
  an older copy of the page can't delete picks it doesn't know).

### Security
- **The page may now ask its own site** (`connect-src 'self'`), for the saved-copy bar's check: a `HEAD` request, which
  the offline copy never answers.

### Tests
- The share-name mutants are settled (#94): "X-GOP", "J/RNC" and "GOP_X" are now tested (blocked only by one line);
  R19 targets a test with a 9 in it; R8 is equivalent (6,916 generated names) and retired with its reason. #52 was
  already fixed and tested in 1.1.0.
- 19 older mutants whose lines waves 2–4 rewrote are re-anchored to the same behavior (a full mutation run would have
  stopped at the first); the Census check's test now also sends a sandboxed answer from the wrong window. P91 and P115
  are retired: the bar no longer goes on its own.
- The offline copy's install guards are tested (#54): a redirected page and a download cut off midway are never kept;
  the test server learns 301s and stalls.
- Three remediation-audit passes, converged; the first two found two real bugs this wave had introduced (a 404 masked by
  the saved copy; picks deleted by an older copy of the page) and one loop ("back" when Reload would still get the copy).

## [1.1.1] — 2026-10-17

**The privacy promise, verified** (cold audit wave 3).

### Security
- **The counting firewall passes no free text** (#50, #67): a page view's title is the page's own title as it loaded,
  no tag is sent, and the page address goes out in its normal form, this site's `/` or `/index.html` only; a payload
  for any other address is dropped whole (so a future `history.pushState` can't carry anything out). The hostname,
  website id, screen size and language pass only as their true values.
- **The tracker is pinned by its hash** (#68): the build refuses any `umami.js` but the reviewed copy, and the tag's
  `integrity=` makes browsers refuse one too.
- **Framed by another site, the page shows nothing of itself** (#69), even in a frame with scripts turned off (which
  shows only the JavaScript note below). GitHub Pages can't send the header that forbids framing, so the page starts
  hidden and its first script shows it only when it isn't framed.
- **Smaller locks** (#85): the Census answer is taken only from the sandboxed frame's own (`null`) origin; the page's
  data is written so that no text in it can end its script or change how it is read; the build stops on a campaign
  site or source link that isn't http(s); counting happens only on ballotta.org (the lanebecker.github.io entry was
  dead: that address redirects).

### Changed
- **With JavaScript off, the page says so:** "Ballotta needs JavaScript to look up your ballot. Turn it on for
  ballotta.org, or use the Travis County Voter Lookup." (with the county's link), instead of a lookup form that couldn't
  work (Lane's wording).

### Tests
- The mutation runner re-hashes a mutated page's Content-Security-Policy, so a kill means a test noticed the change and
  not that the browser refused the page, and it counts a timeout only if it happens twice (#70, #71); it re-hashes only
  the page itself (census.html and next/index.html keep their own policies). Rerun with it, 21 of the 22 mutants it had
  judged are killed; P93 is equivalent and retired with its reason.
- New mutants over the firewall, the pin, the frame guard and the JavaScript note, link handling, ballot routing,
  `esc()` and both CSPs, all killed (#72). New checks: framed with and without scripts (nothing of the page visible,
  text or not), JavaScript off (only the note), and the guard can never stop the first script's link scrub.
- The test stand-in for the tracker loads before the page (the real tag's `integrity=` refuses a substitute).

## [1.1.0] — 2026-10-17

**Look-ups and dates** (cold audit wave 2), two days before early voting starts.

### Fixed
- **Street names that start like a unit are looked up whole** ("2505 Steck Ave", "555 Unity Dr", "Stevens Rd", "Steiner
  Ranch Blvd" were asked as just the number, so an exact match fell back to "nearby") (#57).
- **Two lookups at once no longer race:** the newer address's ballot stands, whatever order the county answers in, and
  a superseded lookup stops asking (#58).
- **A Census outage is no longer reported as a wrong address:** the page says it couldn't reach the U.S. Census address
  finder, and counts it as `census_unreachable` (#59).
- **Dates follow Austin's clock**, not the visitor's: early voting, Election Day lists and the wait-times note change
  on Travis County's dates wherever the phone is (#61).
- **A ballot reopened from this device or a Keep link keeps each "Double-check" contest's own reason** (the county code,
  the district line), as the first lookup showed (#62).
- **A precinct or map point from a link or storage is checked:** only a precinct number shows, and only a point in
  Texas is used for distances (#63).
- **Reloading before answering "Load your saved picks?" asks again** instead of dropping the link (#66).

### Added
- **From Oct 31 to Nov 2 the wait-times note says the county's Election Day map fills in on Nov 3** (#60).
- **A Keep link too long for chat apps says so**, with "Leave my reasons out": long reasons in Chinese, Japanese,
  Korean or emoji can make a link of 100 KB or more (#65).

### Tests
- `BALLOTTA_TODAY` runs the whole suite as of another moment; as of Nov 1 one test failed and is fixed (#64). A stand-in
  for the county's map server (`stub_county`) lets lookup tests run without it.

## [1.0.0] — 2026-10-17

**Phones get the new layout.** The phone layout that was previewed at ballotta.org/next/ is now the main page, for
everyone, two days before early voting starts. 1.0.0 marks that milestone; it is not a breaking change: every Keep
and Share link people already have still opens.

### Added
- **The phone layout on ballotta.org.** Narrower than 1024px, the page is the laptop's app folded up for a phone: a
  plum top bar ("Your ballot", with how many contests are decided, opens the whole ballot as a sheet; Feedback & Info;
  Share), one contest at a time on the paper with its notes behind a "Learn more" fold, and a bottom bar with
  "← Previous" and "Next undecided →".
- **Add to Home Screen.** Android shows the browser's own prompt; on an iPhone, steps that name and draw Safari's own
  buttons, a private picks link to carry your picks into the Home Screen app, and "Paste my picks link" there.
- **An offline copy for phones and tablets.** The page keeps a copy of itself and opens it when there's no
  connection (or the network takes more than 4 seconds), with a bar that says so and "Try again". It keeps the page
  from its first install, so it opens offline before a second visit; that first download gives up after 8 seconds on
  a slow line. Laptops never get it, and turning the phone layout off again removes it from phones.
- **Versioning.** `VERSION`, this changelog, `version.json` on the live site, release tags, and a check that keeps
  them in step (`source/check_release.py`, run by the build, the tests and a GitHub workflow).

### Changed
- **ballotta.org/next/ now sends people to the main page**, with any Keep or Share link made on the preview, and
  removes the preview's offline copy from phones that installed it (audit #21). The main page asks for that removal
  too, for a phone that only ever opens ballotta.org now; a failed request removes nothing. Anyone who added the
  preview to their Home Screen should add ballotta.org again.
- **A friend's picks are counted when they first appear beside your ballot at any width** (`share_compare`), not on a
  Compare tap, which the phone layout doesn't have.
- **Crib sheet print options survive a window narrowed below 1024px**, since a phone now shows them too.

### Removed
- **The old phone page** (every contest on one long page, with its Compare button).

### Fixed
- **The shared link stays on screen after "Share link".** Since Oct 14 the link just copied vanished at once, and
  where copying fails, so did the selected link you were meant to copy by hand.

### Known issues
- The "Slow connection" bar doesn't clear on its own (issue #73), and a server error that arrives within 4 seconds is
  shown instead of the kept copy (issue #74).

### Tests
- The 31 tests that only ran on the old phone page are retired; 34 ports run on the live page (audit #29). The 117
  laptop mutants that named those tests now name the ports, six are re-anchored on the laptop's own copy of their
  line, and five that promotion made unreachable or redundant are retired.

## [0.6.3] — 2026-10-17

### Changed
- **Travis County MUD No. 41 reaches its voters.** Its 7 contests go to the addresses the county codes `M41`
  (precinct 142), marked "Double-check" until the Tax Office confirms the code (Lane's call; issue #56).
- **"The county's wait-times map fills in once voting starts Oct 19"** now shows on the laptop's Where to vote view,
  as the old phone page always said.

## [0.6.2] — 2026-10-17

**What's on the ballot is the ballot** (cold audit wave 1).

### Fixed
- **Ten "vote for up to N" contests list their candidates in the ballot's order** (MUDs, an MMD, two WCIDs and a
  library district: c154, c168, c176, c179, c192, c199, c202, c203, c204, c214; audit #1). Keep and Share links still
  count those ten in the old order, so every link, old or new, means the same candidates to every version of the page.
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

## [0.6.1] — 2026-10-17

### Changed
- **Laptop: At a glance's pick column fits every name on the ballot**, and its title matches the other views' size.
- **The "Crib sheet" tab is "Print your choices"**; its page is titled "Crib sheet", and the printout is headed "My
  ballot choices".
- **Every view's title sits the same distance below its small line**, as Decide's does.

## [0.6.0] — 2026-10-16

### Added
- **A preview of the phone layout at ballotta.org/next/** (ballotta.org itself unchanged): the laptop app folded up
  for a phone, Add to Home Screen and an offline copy with a kill switch; Home Screen steps that name Safari's own
  buttons, and a bar that says when you're looking at the saved copy; "Your ballot" as the top bar's title, with
  "← Previous" and "Next undecided →" at the bottom.

## [0.5.0] — 2026-10-15

### Security
- **The page is locked down** (#36): a Content-Security-Policy built from the hashes of the page's own scripts, no
  referrer to any site, and the Census geocoder in a sandboxed frame (`census.html`) that hands back only a point.

### Added
- **A one-time card after the 5th pick (and at 25) suggests a backup link** (#48), and at the first pick the page asks
  the browser to keep its data (#49).
- **"Clear everything on this device" in the phone page's footer** whenever anything is stored (#42).
- **The laptop's "Print…" opens the Crib sheet view.**

### Fixed
- Saved picks, reasons, share names and generations are checked when read, so junk can't break Keep or Share
  (#20, #44); share names fold look-alike letters and party nicknames (#21, #43); a pick past "vote for up to N" is
  refused with a note that says why (#33); a tab left open past midnight moves to the new day (#34, #47); laptop moves
  and announcements are spoken in order, none cut off (#39, #45); a new ballot clears an older link's notice (#40);
  and smaller fixes (#22–#24, #32, #46).

## [0.4.0] — 2026-10-15

### Added
- **"Clear everything on this device"** next to Clear my picks (and in the laptop menu) removes every Ballotta key
  and reloads other open tabs (#29).

### Changed
- **Usage counts grow to 25 named events behind an allow-list firewall that fails closed**: no address, no picks, no
  candidate names, no query strings or #links. Page speed is counted too, as bare numbers only. Do Not Track and
  Global Privacy Control now turn counting off entirely, page views included.

### Fixed
- A lookup no longer hangs when the county server fails after the Census fallback.

## [0.3.0] — 2026-10-15

### Added
- **The laptop layout** (screens 1024px and wider): a plum column with your ballot's outline, search and filters; one
  contest at a time on a paper with notes beside it; keyboard shortcuts; At a glance; a map of vote centers drawn on
  the page; a crib sheet preview; Feedback & Info. A plum landing band with a gold "Travis County only" strip, the
  tagline "Don't wait to meet your ballot in the booth." and a FAQ. Phones unchanged.

## [0.2.1] — 2026-10-14

### Changed
- **The site moves to ballotta.org** (the old lanebecker.github.io address redirects there). Picks saved in a browser
  at the old address stay there; a Keep link carries them over.
- **Keep and Share links are short and safe to paste into chat apps** (`#k2…`/`#s2…`, about half as long; Messages
  was cutting the old ones); older links still open (#19).

## [0.2.0] — 2026-10-14

### Added
- **Learn more on every race:** an office note, and each candidate's campaign site and League of Women Voters guide
  answers, shown the same way for everyone and saying so when something is missing. Measures: the ballot text; Austin
  Props A–B in plain words, the money split and the City's tax estimate.
- **Where and when to vote:** 45 early and 201 Election Day vote centers, by distance, with late hours, bus routes,
  wait times and ID rules.
- **Keep my picks** (a private link to yourself) and **Share my picks** (a link for a friend, with what to include),
  a friend view and compare.
- Anonymous counts of a few actions (Umami); the About box points at the county's Voter Lookup.

### Changed
- **The ballot follows the county's corrected consolidated ballot** (corrected Oct 14).

## [0.1.0] — 2026-10-13

### Added
- **Ballotta's first test:** look up a Travis County address against the county's own voter-district data, see your
  Nov 3, 2026 ballot, make private picks with reasons, and print a crib sheet. Zilla Slab and Public Sans, self-hosted.
