# Ballotta (early test)

**Your ballot, considered together.** Enter the Travis County, Texas address where you're registered to vote, see exactly what's on your November 3, 2026 ballot, make picks with private notes, and print a crib sheet to bring to the polls (Texas bans phones where you vote; paper notes are allowed).

Live test: https://ballotta.org (the old lanebecker.github.io/ballotta address redirects there)

## How it works

It's one static page with no server.

1. Your browser looks up your address on the Travis County Tax Office's public voter-district map server. If the county can't match it, the browser places it with the U.S. Census geocoder and uses the nearest registered addresses. The Census answers only as a script, so it runs in a sandboxed frame (`census.html`) that can't read the page or its storage and can pass back only a map point.
2. The page routes the 214 contests on the county's consolidated ballot to your address using district codes (precinct, city, council district, school district, MUD, ESD and more).
3. Picks and reasons are saved only in your browser (`localStorage`), along with your ballot's contest list and a rounded location for sorting vote centers. Everything Ballotta keeps is under `ballotta.*` keys: `ballotta.ballot` (precinct, contest list, rounded location), `ballotta.picks`, `ballotta.whys`, `ballotta.name` (your share name), `ballotta.gen` (your place in a share chain), `ballotta.opened` and `ballotta.compared` (codes of friend links already counted), `ballotta.desk` (laptop view), `ballotta.nudge` (which backup-link cards were seen, and whether a link was kept), and in `sessionStorage` a link being opened (`ballotta.incoming`) and which friend links already counted an own-ballot lookup (`ballotta.ownTracked`). **Clear everything on this device** (under the crib sheet and, on a phone, at the bottom of the page whenever anything is stored; Feedback & Info on a laptop) removes them all.

Each race links to neutral sources: every candidate gets the same two slots (the campaign site and the answers *as listed in* the League of Women Voters of the Austin Area 2026 Voters Guide), and the page says so when something is missing. Measures show the ballot text as printed (an audit on Oct 17 found 37 of them carrying a stray Spanish caption at the end, to be fixed), plus official sources where Ballotta has them (the Austin, county, school and college measures; most MUD and ESD measures carry only the ballot text). "Where and when to vote" sorts the county's 45 early and 201 Election Day vote centers by straight-line distance.

### Links: keep your picks, share with a friend

- **Keep** (`#k=…`) packs your ballot's contest list, precinct, picks and reasons into the link's `#` fragment, to send to yourself. Opening it asks before replacing anything.
- **Share** (`#s=…`) packs only the sections you choose (all on by default), optionally your reasons, a first name, a random 8-character link code and a generation number.
- Browsers never send the fragment to servers. A script at the top of the page also removes it from the address bar before anything else runs, including analytics.

### Laptop layout

On screens 1024px and wider the page switches to a laptop layout: a plum column with your ballot's outline (search, filters, progress), one contest at a time on a white "paper" with the office note and neutral sources beside it, keyboard shortcuts on the ballot paper (1–9 pick, S skip, N next undecided, J/K next and previous, R reason, / search), an at-a-glance table, where to vote with a map drawn on the page (no map service sees your address), and a crib-sheet preview with print options. Before a ballot is shown, the laptop landing page has a plum band with the logo, the tagline, a gold "Travis County only" strip and a "What's going on here?" FAQ under the address form. Phones keep the existing layout, pixel for pixel. Both layouts read the same picks and reasons, so resizing a window never loses anything.

The laptop layout went live on Oct 15, 2026. Its code is still marked in `source/template-travis.html` (`/*DESK*/ … /*/DESK*/` in CSS and JS, `<!--DESK--> … <!--/DESK-->` in HTML), and `DESK_LIVE = True` in `source/build_site.py` keeps it in the live page. **Rollback:** set `DESK_LIVE = False` and rebuild; `build_site.py` then strips the marked blocks and the page goes back to the phone-only layout. `next/` now holds the phone-layout preview (next section). A test builds the page both ways in memory and checks that phones see exactly the same pixels with and without the laptop code.

### Phone layout (preview at ballotta.org/next/)

Narrower than 1024px, the preview shows the laptop's app folded up for a phone: a plum top bar (the logo mark; **Your ballot** as the title, "N of M decided" under it, which opens the laptop's outline, search and filters as a full-screen sheet with At a glance, Where to vote, Crib sheet, Keep my picks and Print; Feedback & Info as an (i); Share), one contest at a time on the white paper (its top line carries the precinct), its office note and neutral sources behind an "About this office · Learn more" fold, and a plum bottom bar with **← Previous** ("← Contest N" from another view) and **Next undecided →** ("Next →" once everything is decided, "Crib sheet →" at the end). Feedback & Info opens as a sheet; the landing page gets the laptop's plum band, tagline, gold "Travis County only" strip and FAQ (as folds). Every pick goes through the same code on both widths, so resizing never loses anything.

It also adds **Add to Home Screen**: `manifest.webmanifest`, three icons (`icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, drawn by `source/make_icons.py`) and an offline copy (`sw.js`, network first: online, every request goes to the network and the answer is kept; offline, or with no answer after 4 seconds, the kept copy of that file is used; lookups always need the network, and a link's #picks never reach it; phones and tablets only, never a laptop, even in a narrow window; the preview and the live page keep separate copies, `ballotta-next-…` and `ballotta-…`). A page opened from the kept copy is marked (`<html data-copy="offline">` or `"slow"`), and a gold bar under the top bar says "No connection" or "Slow connection, so this is the copy saved on your phone", with Try again; it goes when the network comes back. On Android the menu's "Add to your Home Screen" shows the browser's own prompt. On an iPhone it explains the steps, naming and drawing the browser's own buttons (Safari's ••• and Share, View More where it appears; Chrome's Share; any other browser's), and marks the step to do now; a Home Screen app there keeps its own storage, apart from Safari's (and Safari's 7-day clean-up), so it starts empty: the steps offer to copy a private picks link first, and the Home Screen app offers "Paste my picks link". The 25-pick backup card mentions it once. The page's Content-Security-Policy gains `manifest-src 'self'` and `worker-src 'self'` for these. The kept copy holds only the site's own files (never an address, a pick or a link), and **Clear everything on this device** leaves it in place; a browser's own "clear site data" removes it.

Until Lane promotes it, the phone layout is marked in `source/template-travis.html` (`/*PHONE*/ … /*/PHONE*/`, `<!--PHONE--> … <!--/PHONE-->`) and `PHONE_LIVE = False` in `source/build_site.py` strips it from `index.html`, so the live page stays byte-for-byte what it was (a test pins its fingerprint). A second test builds the page with and without the phone code and checks that laptops see exactly the same pixels. **Offline kill switch:** set `OFFLINE = False` in `source/build_site.py`, rebuild and push: the page then asks the browser to fetch `sw.js` again instead of installing it, and the new `sw.js` takes the page over, deletes Ballotta's copies (no others) and removes itself (a test runs this end to end). On promotion the build keeps writing `next/sw.js` as that self-removing version, so phones that installed the preview drop its copy. Two laptop details changed on purpose: crib-sheet print options now survive a window narrowed below 1024px and widened again (a phone shows them too), and a friend's picks are counted (`share_compare`) when they first show beside a ballot at any width, so after promotion phone counts mean that rather than a Compare tap.

### Anonymous counts

[Umami](https://umami.is) (cookieless) counts page views, page speed (load time and responsiveness) and the events below, each with only the details listed. Every event also carries `layout` (`phone` or `laptop`), and, from a phone-width Home Screen app only, `app` (`yes`).

- Where people drop off: `lookup_started`; `lookup_failed` (reason: no street, bad ZIP, not found, no voters nearby, county server unreachable); `units_asked` (the "which unit is yours?" picker); `ballot_found` (match type); `address_changed` (a lookup that brings up a different ballot from the one already showing, whether from this visit or saved earlier); `link_damaged` (damaged or too old).
- How far people get: `progress` when a pick or skip crosses 25, 50, 75 or 100% decided, with reasons written and races skipped as 0, 1–5 or 6+. A ballot shown already decided (a saved ballot, a keep link, a returning voter) counts nothing; which milestones were reached is kept in memory only, never stored.
- What helps: `source_opened` (kind of link: League guide, campaign site, official, news, reference or other; and the race's level: federal, state, courts, county, city, school, special district or measure; never which race or candidate); `directions_opened` and `wait_times_opened` (early voting or Election Day).
- Laptop features: `view_opened` (decide, at a glance, where to vote, crib sheet); `shortcut_used` (pick, skip, move, reason or search; once per kind per visit); `search_used` (once per visit) and `filter_used` (once per filter per visit); `faq_seen` (after the visitor scrolls); `help_opened` (which Feedback & Info item).
- Keeping and sharing: `keep_created` (how), `keep_restored`, `backup_nudge` (the backup-link card at 5 or 25 picks: shown, keep, dismiss, or home for its Home Screen line), `home_screen` (Add to Home Screen: the steps opened, from the menu or the card; the browser's prompt shown; added; a picks link copied to carry over; one pasted into a Home Screen app), `share_sheet_open`, `share_created` (section keys, reasons yes/no, picks 1–5/6–15/16+, how, generation, link code), `share_opened` (generation, already had picks, link code; once per browser per link), `share_own_ballot` (generation), `share_compare` (today's phone page: each Compare tap; laptop, and the phone preview: once per friend link when one of their races is first shown beside your ballot), `crib_printed` (two columns and hide-unopposed, yes or no), `cleared` (picks, or everything).

**The privacy firewall.** `source/template-travis.html` lists every event and the only values each detail may take (`EVENTS`). The page's `track()` and the tracker's before-send hook (`ballottaBeforeSend`) both drop anything not on that list, so a new feature or a bug can't send something unlisted. The hook also rebuilds every payload from a fixed set of text fields, with any `?query` or `#fragment` cut from the page address and the referrer reduced to its site: only page views, events and page-speed reports pass, page views and speed reports carry no details, and no distinct id or `identify` data is ever sent. (Umami still groups one visit's requests into a session, as it does on any site.) A stand-in placed before the tracker tag drops everything until the page's check exists, so if the page's script failed, nothing would be sent. Never sent: addresses, precincts, districts, which race, candidate names, parties, picks, reasons or names. If the browser sends **Do Not Track** or **Global Privacy Control**, nothing is counted, not even page views. Tests run real journeys on both layouts, and the real tracker against a stand-in Umami server, and the test suite fails if anything off the list would be sent; another test fails if this README misses an event. The tracker is a pinned copy (`umami.js`, fetched 2026-10-14) so it can't change underneath the page; it reports to gateway.umami.is, and only on the hostnames in `UMAMI_DOMAINS`.

Contests marked **Double-check** aren't confirmed for your address yet. Always confirm with your official sample ballot at [VoteTravis.gov](https://votetravis.gov).

## Data sources

- District assignments: Travis County Tax Office voter registration data (public ArcGIS server)
- State and federal districts by precinct: Texas Legislative Council, CC BY 4.0
- Contests and candidates: Travis County consolidated ballot, Nov 3, 2026 (corrected version posted Oct 14, 2026)
- Candidate answers and listed campaign websites: [League of Women Voters of the Austin Area 2026 Voters Guide](https://austinvotersguide.org/LWVAA-VG-EN.pdf), linked as published (page numbers and listed sites parsed from the PDF; Ballotta isn't affiliated with the League)
- Vote centers: Travis County Clerk's early voting and Election Day lists; positions from the U.S. Census geocoder, Travis County's geocoder and © OpenStreetMap contributors (ODbL)
- City of Austin Props A–B money split and tax estimate: City of Austin 2026 bond page and staff memo (May 15, 2026)
- Fonts: Zilla Slab and Public Sans, SIL Open Font License 1.1

Ballotta isn't affiliated with Travis County, the League of Women Voters or any campaign, and it doesn't tell anyone how to vote.

The page is locked down: a Content-Security-Policy (built by `build_site.py` from the hashes of the page's own scripts) lets only its own scripts and files from this site run, lets it talk only to the county map server and the counting service, and allows frames only from this site. It sends no referrer to any site it asks or links to.

## Rebuilding

Everything that makes the page lives in `source/`:

- `template-travis.html`: the page itself, with a `__DATA__` placeholder
- `answer_key.json`: the 214 contests, parsed from the county's consolidated ballot (`source/ballot/`)
- `rules.json`, `tlc_precincts.json`: which contests apply to which district codes, built by `build_rules.py` from the files in `source/data/`
- `data/lwv_candidates.json`, `data/lwv_measures.json`: from `parse_lwv.py` (the League guide PDF), link-checked by `check_sites.py`
- `learn.json`: per-race "learn more" data and office notes, built by `build_learn.py`
- `vote_sites.json`: the county's vote center lists, geocoded

```
python3 source/ballot/build_answer_key.py           # only when the ballot changes: writes answer_key.json
python3 source/build_rules.py                       # only when the contests or district data change
python3 source/parse_lwv.py LWVAA-VG-EN.pdf source/answer_key.json source/data/lwv_candidates.json
python3 source/check_sites.py                       # after any parse: records which listed sites load
python3 source/build_learn.py
python3 source/build_site.py                        # writes index.html and census.html
python3 source/build_site.py --preview              # writes next/ (the phone preview, its manifest.webmanifest and sw.js)
python3 source/make_icons.py                        # only if the logo changes: the Home Screen icons
python3 tests/test_pipeline.py                      # the answer key against the ballot PDF (no browser)
python3 tests/test_site.py                          # end-to-end checks (Playwright, live county services) of the live page
BALLOTTA_PAGE=next/index.html python3 tests/test_site.py   # the same against the phone preview
python3 tests/mutate_desk.py                        # mutation check of the tests (slow; restores every file it touches, even when stopped)
python3 tests/mutate_phone.py                       # the same for the phone layout's tests, against the preview
```

`parse_lwv.py` prints any listed site it couldn't credit to a candidate, and stops the build if a contested race shows an "unopposed" candidate or if a sole candidate is shown as answering without a hand check. It needs PyMuPDF (`pip install pymupdf`); the tests need Playwright with Chromium (`pip install playwright && playwright install chromium`); `make_icons.py` needs Playwright too.

`build_answer_key.py` turns `source/ballot/parsed.json` (from `parse_ballot.py`, which read per-column text files extracted from the ballot PDF by hand, not in the repo) into the key. Its hand fixes live in the script, so a rerun gives the committed key byte for byte, the Oct 14 corrections included: the order of choices in the "vote for up to N" contests is the ballot's, top to bottom, and every measure's text is read straight from the corrected ballot PDF (`source/ballot/bedsheet.pdf`, by `source/ballot/pdf_lines.py`: English only, since the ballot sets Spanish in italic). Both need pdfplumber (`pip install pdfplumber`). `tests/test_pipeline.py` holds the key to the PDF: choice order, measure texts, party labels and the count of measures.

Keep and Share links store picks by each choice's position in its list. The Oct 17 fix put ten lists in ballot order, so links made before it (no `r: 2` inside) are read through the page's `REORDERED` table and keep meaning the same candidates; never reorder a list again without the same care.

`build_rules.py` stops the build when a contest's district is reached by no address on file (unless it's explained in `UNREACHED_OK`: today only Travis County MUD No. 41, whose county code isn't confirmed), when an address would get anything but one member of Congress and one State Rep, or more than one State Senator, or when an address's precinct is missing from the Legislative Council table.

## Custom domain (ballotta.org)

GitHub Pages serves the site at ballotta.org (done Oct 14, 2026). How it was set up, for the record:

1. At the domain registrar, add four `A` records for `ballotta.org`: 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 (optionally the `AAAA` records 2606:50c0:8000::153, 8001::153, 8002::153, 8003::153), and a `CNAME` for `www` pointing to `lanebecker.github.io`.
2. In GitHub: repo Settings → Pages → Custom domain → `ballotta.org` → Save (this commits a `CNAME` file), wait for the DNS check, then tick **Enforce HTTPS**.
3. `BASE_URL` in `source/build_site.py` is `https://ballotta.org/`, so link previews use that address.

The old github.io address redirects to ballotta.org, keeping any `#` fragment. Picks saved in a browser don't move across addresses, because browser storage belongs to one address.
