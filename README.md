# Ballotta (early test)

**Your ballot, considered together.** Enter the Travis County, Texas address where you're registered to vote, see exactly what's on your November 3, 2026 ballot, make picks with private notes, and print a crib sheet to bring to the polls (Texas bans phones where you vote; paper notes are allowed).

Live test: https://lanebecker.github.io/ballotta/ (moving to https://ballotta.org, see "Custom domain" below)

## How it works

It's one static page with no server.

1. Your browser looks up your address on the Travis County Tax Office's public voter-district map server. If the county can't match it, the browser places it with the U.S. Census geocoder and uses the nearest registered addresses.
2. The page routes the 214 contests on the county's consolidated ballot to your address using district codes (precinct, city, council district, school district, MUD, ESD and more).
3. Picks and reasons are saved only in your browser (`localStorage`), along with your ballot's contest list and a rounded location for sorting vote centers.

Each race links to neutral sources: every candidate gets the same two slots (the campaign site and the answers *as listed in* the League of Women Voters of the Austin Area 2026 Voters Guide), and the page says so when something is missing. Measures show the ballot text verbatim plus official sources. "Where and when to vote" sorts the county's 45 early and 201 Election Day vote centers by straight-line distance.

### Links: keep your picks, share with a friend

- **Keep** (`#k=…`) packs your ballot's contest list, precinct, picks and reasons into the link's `#` fragment, to send to yourself. Opening it asks before replacing anything.
- **Share** (`#s=…`) packs only the sections you choose (all on by default), optionally your reasons, a first name, a random 8-character link code and a generation number.
- Browsers never send the fragment to servers. A script at the top of the page also removes it from the address bar before anything else runs, including analytics.

### Anonymous counts

[Umami](https://umami.is) (cookieless) counts page views and these events, with only the details listed: `ballot_found` (match type), `share_sheet_open`, `share_created` (section keys, reasons yes/no, picks 1–5/6–15/16+, share sheet or copy, generation, link code), `share_opened` (generation, already had picks, link code; once per browser per link), `share_own_ballot`, `share_compare`, `keep_created`, `keep_restored`, `crib_printed`. Never sent: addresses, precincts, districts, picks, reasons or names. The tracker is a pinned copy (`umami.js`, fetched 2026-10-14) so it can't change underneath the page; it reports to gateway.umami.is, and only on the hostnames in `UMAMI_DOMAINS`.

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

## Rebuilding

Everything that makes the page lives in `source/`:

- `template-travis.html`: the page itself, with a `__DATA__` placeholder
- `answer_key.json`: the 214 contests, parsed from the county's consolidated ballot (`source/ballot/`)
- `rules.json`, `tlc_precincts.json`: which contests apply to which district codes, built by `build_rules.py` from the files in `source/data/`
- `data/lwv_candidates.json`, `data/lwv_measures.json`: from `parse_lwv.py` (the League guide PDF), link-checked by `check_sites.py`
- `learn.json`: per-race "learn more" data and office notes, built by `build_learn.py`
- `vote_sites.json`: the county's vote center lists, geocoded

```
python3 source/build_rules.py                       # only when the contests or district data change
python3 source/parse_lwv.py LWVAA-VG-EN.pdf source/answer_key.json source/data/lwv_candidates.json
python3 source/check_sites.py                       # after any parse: records which listed sites load
python3 source/build_learn.py
python3 source/build_site.py                        # writes index.html
python3 tests/test_site.py                          # end-to-end checks (Playwright, live county services)
```

`parse_lwv.py` stops the build if a listed site can't be credited, if a contested race shows an "unopposed" candidate, or if a sole candidate is shown as answering without a hand check.

## Custom domain (ballotta.org)

GitHub Pages serves the site at the custom domain once DNS points to it:

1. At the domain registrar, add four `A` records for `ballotta.org`: 185.199.108.153, 185.199.109.153, 185.199.110.153, 185.199.111.153 (optionally the `AAAA` records 2606:50c0:8000::153, 8001::153, 8002::153, 8003::153), and a `CNAME` for `www` pointing to `lanebecker.github.io`.
2. In GitHub: repo Settings → Pages → Custom domain → `ballotta.org` → Save (this commits a `CNAME` file), wait for the DNS check, then tick **Enforce HTTPS**.
3. Change `BASE_URL` in `source/build_site.py` to `https://ballotta.org/` and rebuild, so link previews use the new address.

The old github.io address then redirects to ballotta.org, keeping any `#` fragment. Picks saved in a browser don't move across addresses, because browser storage belongs to one address: testers should use "Keep my picks" before the switch.
