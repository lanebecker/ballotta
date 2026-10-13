# Ballotta (early test)

**Your ballot, considered together.** Enter the Travis County, Texas address where you're registered to vote, see exactly what's on your November 3, 2026 ballot, make picks with private notes, and print a crib sheet to bring to the polls (Texas bans phones where you vote; paper notes are allowed).

Live test: https://lanebecker.github.io/ballotta/

## How it works

It's one static page with no server.

1. Your browser looks up your address on the Travis County Tax Office's public voter-district map server. If the county can't match it, the browser places it with the U.S. Census geocoder and uses the nearest registered addresses.
2. The page routes the 214 contests on the county's consolidated ballot to your address using district codes (precinct, city, council district, school district, MUD, ESD and more).
3. Picks and reasons are saved only in your browser (`localStorage`).

Contests marked **Double-check** aren't confirmed for your address yet. Always confirm with your official sample ballot at [VoteTravis.gov](https://votetravis.gov).

## Data sources

- District assignments: Travis County Tax Office voter registration data (public ArcGIS server)
- State and federal districts by precinct: Texas Legislative Council, CC BY 4.0
- Contests and candidates: Travis County consolidated ballot, Nov 3, 2026
- Fonts: Zilla Slab and Public Sans, SIL Open Font License 1.1

Ballotta isn't affiliated with Travis County or any campaign, and it doesn't tell anyone how to vote.

## Rebuilding

Everything that makes the page lives in `source/`:

- `template-travis.html`: the page itself, with a `__DATA__` placeholder
- `answer_key.json`: the 214 contests, parsed from the county's consolidated ballot (`source/ballot/`)
- `rules.json`, `tlc_precincts.json`: which contests apply to which district codes, built by `build_rules.py` from the files in `source/data/`

```
python3 source/build_rules.py   # only when the contests or district data change
python3 source/build_site.py    # writes index.html
```
