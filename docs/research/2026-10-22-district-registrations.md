# Travis-area results tool: county splits and registrations (research notes)

Researched 2026-10-22. Every number has its source URL and the date of the data. Anything marked **ESTIMATE** is my own calculation. It is not a published figure.

---

## 0. Context found along the way (affects the tool)

- Ordinance No. 20260806-003, passed Aug 6, 2026, orders the Nov 3, 2026 general election for Council Districts 1, 3, 5, 8 and 9. It adopts the voting systems of Travis, Williamson and Hays counties. It does **not** say which districts lie in which county.
  https://services.austintexas.gov/edims/document.cfm?id=482445 (this is Exhibit B to the Oct 8, 2026 agenda item). Hays County re-posted the same ordinance at https://www.hayscountytx.gov/DocumentCenter/View/5071.
- Austin also has two **citywide** measures on Nov 3, 2026. Item 32 on the Oct 8, 2026 council agenda is a General Obligation **Bond Election** (Ord. 20260806-002). Item 34 is a **special election on charter amendments** (Ord. 20260806-004). Agenda: https://www.austintexas.gov/council/2026/20261008-reg
  - This explains why Williamson County voters are in the Austin 2026 election even though no 2026 council district reaches Williamson (see section 1). Austin voters in Williamson County get the bond and charter questions but no council race.
- ACC is also holding a **special annexation election** on Nov 3, 2026, for "the territory in the Pflugerville ISD that is not already within the ACC taxing district". It is held in Travis County only. Notice: https://drive.google.com/file/d/15zC64jT156yXaHBJLh2Bg4A-ufdDIBFZ/view (linked from https://offices.austincc.edu/community-and-government-affairs/acc-board-of-trustees-elections/, page last modified 2026-10-07).
- ACC annexed **Lockhart ISD** on Nov 5, 2024 (61.2% For). ACC's taxing district in Caldwell County is therefore now mostly Lockhart ISD, not a sliver. Source: https://sites.austincc.edu/newsroom/2024/11/06/acc-welcomes-lockhart-isd-to-the-district (posted Nov 6, 2024). See section 3.

---

## 1. Which 2026 council districts reach Williamson or Hays County

| District | Williamson | Hays | Evidence strength |
|---|---|---|---|
| 1 | No | No | High (GIS) |
| 3 | No | No | High (GIS) |
| 5 | No voters there (a tiny land piece of about 0.27 km² is in Hays) | Land only, **0 Austin ballots cast in Hays outside precinct 438 in Nov 2025** | Medium-high |
| 8 | No | **Yes**: Hays precinct 438 (565 registered voters in Nov 2025) plus about 15 km² of land | High |
| 9 | No | No | High (GIS) |
| (6, not on the 2026 ballot) | Yes: all of Austin's Williamson part | No | High |

**Method (GIS).** I intersected the City's council-district polygons with Census TIGER county boundaries.
- Council districts: data.austintexas.gov dataset `w3v2-cj58`, "Boundaries: City of Austin Council Districts". Export: https://data.austintexas.gov/api/geospatial/w3v2-cj58?method=export&format=GeoJSON. Features were created 2022-02-25 (the 2021/22 ICRC map). District 10's feature was modified 2026-10-01, probably for annexations. Downloaded 2026-10-22.
- Counties: Census TIGERweb State_County MapServer layer 1, https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/State_County/MapServer/1
- Results in km²:
  - D1: 121.9, all Travis.
  - D3: 58.8, all Travis.
  - D9: 31.5, all Travis.
  - D5: 60.55 in Travis and 0.27 in Hays. The Hays part is two compact pieces near 30.078,-97.787 and 30.088,-97.800, each about 130–170 m wide, so they are real pieces and not edge slivers.
  - D8: 116.5 in Travis and 15.2 in Hays. The Hays part centers near 30.145,-97.912.
  - D6: 29.9 in Travis and 54.3 in Williamson.
  - D7 and D10 each touch Williamson with a 0.7 m-wide sliver (0.002 and 0.001 km²). That is boundary noise and does not count as territory.
- **Precinct check (Texas Legislative Council 2024 VTDs).** Source: https://data.capitol.texas.gov/dataset/vtds, file VTDs_24PG.zip, dated Jan 2025.
  - Hays VTD 0438 is 2.318 km², of which **2.292 km² is in District 8**.
  - D5's Hays pieces fall in Hays VTD 0228. D8 also overlaps Hays VTDs 0430 (11.8 km²) and 0442 (1.1 km²).
  - Every Williamson VTD that touches Austin overlaps only District 6.
- **Election-record check (the strongest evidence).** In the City's Nov 4, 2025 Prop Q canvass, Hays County reported Austin ballots in **one precinct only, 438**. The same 127 ballots appear on the state propositions in precinct 438, so the whole precinct votes in Austin.
  - Canvass exhibit, 255 pages: https://services.austintexas.gov/edims/document.cfm?id=462660 (Council backup, Nov 17, 2025; Hays section near the end).
  - Hays County official canvass: https://www.egovlink.com/public_documents300/hayscounty/published_documents/departments/elections/results/2025/1104%20General/Canvass%20Results%2020251104%20Official.pdf (run 11/10/2025).
  - So in Nov 2025, D5's Hays land had no Austin ballot style. It very likely has **no registered voters**. That is an inference from the canvass; no source states it outright.
  - The Williamson precincts in the same canvass (117, 118, 147, 151, 166, 174, 175, 186, 189, 198, 303, 340, 399) all fall in D6 in the GIS check.
- **Not found:** a Williamson or Hays notice of election or sample ballot for Nov 2026 that lists Austin council districts.
  - Hays County election pages (hayscountytx.gov/elections/20261103) returned no ballot-style links. The older hayscountytx.com host returned 502 errors.
  - The joint election contracts with Hays and Williamson (Exhibit E to the Oct 8, 2026 item, https://services.austintexas.gov/edims/document.cfm?id=482448, OCR'd) contain no district or precinct lists and no voter counts.
  - I could not open the Oct 8, 2026 agenda page through WebFetch (permission prompt timed out), so I read it with curl instead.

**Confidence:** high that D1, D3 and D9 are Travis-only. High that D8 has a Hays part with voters. Medium-high that D5's Hays part has no voters, since that rests on the Nov 2025 canvass and not on a 2026 ballot-style list. In practice, D8 is the only 2026 council race with Hays votes, and no 2026 council race has Williamson votes.

---

## 2. Registered voters in Austin's Hays and Williamson parts

### Hays County part
- **565 registered voters**: Hays precinct 438, the only Hays precinct with Austin ballots, Nov 4, 2025 election. 127 ballots were cast, 22.48% turnout.
- Sources: City canvass exhibit https://services.austintexas.gov/edims/document.cfm?id=462660 and the Hays official canvass PDF linked in section 1 (run 11/10/2025).
- Council district: all **District 8** (see section 1).
- Confidence: high for Nov 2025. The 2026 count is not published; it will be close to this.

### Williamson County part (all District 6, so no 2026 council race)
- Source: Williamson precinct-by-precinct report in the same City canvass exhibit (FINAL OFFICIAL, report dated 11/12/2025): https://services.austintexas.gov/edims/document.cfm?id=462660. Data date: Nov 4, 2025.
- Austin Prop Q had 7,617 contest ballots in Williamson (7,526 votes plus 84 undervotes plus 7 overvotes).
- The 13 precincts that had Austin ballots had **37,210 registered voters in total**. That is a whole-precinct figure, so it is an upper bound.
- Nine precincts had every ballot carry the Austin contest, so they are wholly Austin: 117, 118, 147, 151, 174, 175, 189, 198, 399. They total **27,708 registered voters**, which is a hard lower bound.
- Partly Austin: 186 (2,733 RV, 99% of ballots were Austin), 303 (2,687 RV, 99%), 166 (2,076 RV, 14%) and 340 (2,006 RV, 6%).
- **ESTIMATE: about 33,500 registered voters** in Austin-in-Williamson, as of Nov 2025. I weighted each precinct's registered voters by its share of ballots that carried the Austin contest.
- Note: "Registered Voters - Total 451,275" in the same report is the **whole county**, not Austin.

### For context: Travis part (not asked, but useful)
- The 232 Travis precincts that had Austin ballots in Nov 2025 total 734,840 registered voters (whole-precinct upper bound). The precincts whose ballots all carried the Austin contest total 484,416 (lower bound).
- **ESTIMATE: about 611,000** after the same ballot-share weighting.
- The "906,629" in the Travis cumulative report is **Travis County as a whole**.
- Source: same exhibit, id=462660.

### Per council district
- **Not found** from any official source as a breakdown of registered voters by district and county.
- From the above: Hays part = D8, 565. Williamson part = D6, about 33,500 (estimate).

---

## 3. ACC trustee elections: Caldwell and Lee counties

### How ACC defines its election precincts
- ACC's 2026 Order of Election (OCR'd): https://drive.google.com/file/d/1WvaXLoR0FK3X5NobVLk4LWA2nvipKYqu/view. Lee County's copy: https://www.co.lee.tx.us/upload/page/12529/order%20for%20ACC%20nov%202026.pdf
- It designates as ACC precincts the county precincts of Bastrop, Caldwell, Hays, Lee, Travis and Williamson "that are wholly or partially within the territorial boundaries of ACC's taxing district". It gives no voter counts and no precinct list.
- The 2026 Notice (https://drive.google.com/file/d/1-JYIXE-lZWp6rT0jtweNBzCJ3XBrrFrQ/view) addresses "registered voters of ACC in Caldwell County" and "in Lee County". It lists the Caldwell election-day sites (all county precincts) and the Lee vote centers, but no counts.
- 2026 trustee seats: Places 1, 2 and 3.

### Which school-district territory is ACC in each county
- GIS method: Census TIGERweb Unified School Districts (current), https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/School/MapServer/0, intersected with the county boundaries.
- **Caldwell:**
  - Lockhart ISD: 868 km². In ACC since the Nov 5, 2024 annexation vote.
  - Hays CISD: 19.5 km². Hays CISD was already in ACC.
  - Not ACC: Luling ISD, Prairie Lea ISD, San Marcos CISD, Waelder ISD.
- **Lee:** Elgin ISD covers only 7.6 km² of Lee County. The rest of Lee is Giddings, Lexington and Dime Box ISDs, which are not in ACC.

### Caldwell County: registered voters
- **No official count of ACC registered voters was found.**
- **ESTIMATE: about 18,600 registered voters** in ACC territory, as of Nov 2024: about 18,100 in Lockhart ISD and about 500 in Hays CISD.
  - Inputs: TLC registered voters by VTD for the Nov 2024 general. Source file 2024_General_Election_VRTO.csv inside https://data.capitol.texas.gov/dataset/35b16aee-0bb0-4866-b1ec-859f1f044241/resource/e1cd6332-6a7a-4c78-ad2a-852268f6c7a2/download/2024-general-vtds-election-data.zip
  - Split VTDs were apportioned by 2020 census block population: TIGERweb Census2020 Tracts_Blocks layer 2.
  - County total registered voters, Nov 2024: 27,013 (Caldwell official results, https://www.co.caldwell.tx.us/upload/page/0213/docs/2024/OfficialResults110524_County.pdf). The TLC VTD sum is 27,170.
- Cross-check: the same method predicts about 10,900 ballots cast in Lockhart ISD in Nov 2024. The ACC "Annexation and Ad Valorem Tax" contest drew 10,453 votes in Caldwell (6,396 For, 4,057 Against). That fits, with normal roll-off.
- **Votes actually cast in Caldwell in past ACC races (before Lockhart joined, so the Hays CISD part only):**
  - Nov 5, 2024 (final unofficial, 11/13/2024; https://www.co.caldwell.tx.us/upload/page/0213/docs/2024/FinalUnofficialResults110524.pdf):
    - Place 7: 131 votes (Taylor 93, Wilson 38).
    - Place 8: 121 (Gharakhanian, unopposed).
    - Place 9: 128 (Sefton 46, Nitsch 82).
  - Nov 8, 2022 (official, 11/22/2022; https://www.co.caldwell.tx.us/upload/page/0213/docs/2022/Official%20Summary%20110822.pdf):
    - Place 4: 81.
    - Place 5: 84.
    - Place 6: 79.
    - ACC Prop A: 128 (76 For, 52 Against).
  - **ESTIMATE:** about 500 registered voters in Caldwell's Hays CISD part (VTD 0303 area). Expect 2026 ACC votes from Caldwell to be in the thousands, not in the hundreds as in 2022/2024, because Lockhart ISD now votes.
- 2026 Caldwell ACC sample ballot (one style, "ACC Typ:01 Seq:0079"; no precinct list): https://www.co.caldwell.tx.us/page/open/6221/0/Austin%20Community%20College_Sample%20Ballot_Color.pdf
- Confidence: high that Lockhart ISD is now in ACC and that Caldwell's ACC electorate is large. The 18,600 figure is a moderate-confidence estimate (2024 registrations, 2020 population weights, Census ISD lines).

### Lee County: registered voters
- **No official count found.**
- Ballot style: Lee's Nov 3, 2026 sample ballots (scanned PDF, 32 pages) show exactly one style with the ACC contest, labelled precinct **"303 ACC"** (page 17). https://www.co.lee.tx.us/upload/page/12529/sample%20ballots%20110326.pdf
- Lee's daily early-vote check-in files for 2026 split precinct 303 into "S 303.1" and "S 303.2". S 303.1 had 4 check-ins on 10/19 and 4 on 10/20; 10/21 is the third file below. That fits a tiny ACC split, but **no source confirms which split is ACC**.
  - https://www.co.lee.tx.us/upload/page/12529/10-19%20voter%20history.xlsx
  - https://www.co.lee.tx.us/upload/page/12529/voter%20history%2010-20.xlsx
  - https://www.co.lee.tx.us/upload/page/12529/voter%20history%2010-21-2026.xlsx
  - I used counts only, no names.
- **Votes actually cast in Lee in past ACC races** (both are scanned PDFs, so I OCR'd them):
  - Nov 5, 2024 (UNOFFICIAL summary, generated 11/25/2024; https://www.co.lee.tx.us/upload/page/11450/local%20results%2011524.pdf):
    - Place 7: Taylor 23, Wilson 10, 36 undervotes, so **69 ACC ballots**.
    - Place 8: Gharakhanian 28, 41 undervotes.
    - Place 9: Sefton 17, Nitsch 19, 33 undervotes, so also **69 ballots**.
  - Nov 8, 2022 (UNOFFICIAL, 11/08/2022; https://www.co.lee.tx.us/upload/page/10727/total%20result2%2011-8-22.pdf):
    - Place 4: 31.
    - Place 5: 31.
    - Place 6: 35.
    - Prop A: 53 votes cast (26 For, 27 Against).
- **ESTIMATE: about 90–100 registered voters** in ACC's Lee County part, as of 2024.
  - Basis: 69 ACC ballots in a high-turnout presidential year.
  - Basis: 2020 census population in Elgin ISD's Lee portion is 134.
  - The TLC VTD numbers for Lee (VTD 0304 vs county precinct 303) look mismatched, so I did not use the VTD-based figure (19). It is contradicted by the 69 actual ballots.
- Confidence: high that the bound is small (69 ACC ballots in 2024). Low on the exact registered-voter count.

---

## What I could not find
- Any official count of registered voters for: the City of Austin by county for 2026; any council district by county; or ACC's Caldwell or Lee portion.
- A 2026 Hays or Williamson ballot-style or sample-ballot list naming Austin council districts.
- Precinct-level ACC results for Caldwell 2024 (the precinct-by-precinct report covers federal, state and county races only).
- Lee and Caldwell official canvasses giving registered voters per ACC ballot style.
