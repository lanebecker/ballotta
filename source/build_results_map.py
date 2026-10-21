"""Writes source/results_map.json: what each of the 214 contests is and where its numbers come from (docs/plans/
2026-10-20-results.md, Task 2). Every fact is in the tables below with where it comes from; the JSON is never edited by
hand except `keys` (filled the morning of Nov 4, when the counties post, as `build_results.py suggest` prints them:
"17 = <the county's name for the contest>", or "absent") and `meta.fetch`.

    python3 source/build_results_map.py           # writes the map, keeping keys and meta.fetch already in it
    python3 source/build_results_map.py --check   # the committed map says what this writes (a test runs it): compared as
                                                  # JSON, so a hand edit to what's kept (keys, spell, write-ins,
                                                  # registered voters, meta.fetch) never fails the Results run (#162)

Researched Oct 20, 2026, from each entity's order and notice of election (votetravis.gov, Required Notices), the
Corrected-Final2 bedsheet ballot, the Texas SOS feed for election 53815, statutes and charters. INFERRED and UNVERIFIED
mark facts Lane should look at (the review list is in the plan).
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "source"))
import check_results  # noqa: E402

OUT = ROOT / "source/results_map.json"
ORDERS = "https://votetravis.gov/resources/required-notices/"

# ---------------------------------------------------------------- who makes each contest official
CANVASSERS = {
    "state": ("the state", "state", "Elec. Code §67.010: the Governor's state canvass, Nov 21 - Dec 7"),
    "legislature": ("the Legislature", "legislature", "Tex. Const. art. IV §3; Elec. Code §67.011 (Governor, Lt. Governor)"),
    "travis-county": ("the Travis County Commissioners Court", "local", "Elec. Code §67.002 (county offices)"),
    "tcad": ("the Travis Central Appraisal District board", "local", "SOS appraisal-district election FAQ 5; TCAD canvassed its May 2024 election"),
    "city-of-austin": ("the Austin City Council", "local", "Elec. Code §67.002; Ord. 20260806-002"),
    "city-of-elgin": ("the Elgin City Council", "local", "Elec. Code §501.109(b)(2) (local option)"),
    "city-of-jonestown": ("the Jonestown City Council", "local", "Jonestown order of election"),
    "city-of-lago-vista": ("the Lago Vista City Council", "local", "Ord. 26-07-16-01"),
    "city-of-manor": ("the Manor City Council", "local", "Res. 2026-16"),
    "city-of-pflugerville": ("the Pflugerville City Council", "local", "Pflugerville orders of election"),
    "city-of-sunset-valley": ("the Sunset Valley City Council", "local", "Ord. 260602-A"),
    "sunset-valley-ccpd": ("the Sunset Valley Crime Control and Prevention District board", "local",
                           "INFERRED: the district's board ordered Prop A (Local Gov't Code ch. 363); its canvass not stated"),
    "village-of-volente": ("the Volente Village Council", "local", "Res. 2026-R-02"),
    "acc": ("the ACC Board of Trustees", "local", "ACC order of election, Nov 2026"),
    "austin-isd": ("the Austin ISD Board of Trustees", "local", "AISD order of election"),
    "coupland-isd": ("the Coupland ISD Board of Trustees", "local", "Coupland ISD orders"),
    "del-valle-isd": ("the Del Valle ISD Board of Trustees", "local", "Del Valle ISD order of election"),
    "leander-isd": ("the Leander ISD Board of Trustees", "local", "Elec. Code §67.002"),
    "manor-isd": ("the Manor ISD Board of Trustees", "local", "Elec. Code §67.002"),
    "pflugerville-isd": ("the Pflugerville ISD Board of Trustees", "local", "Elec. Code §67.002"),
    "round-rock-isd": ("the Round Rock ISD Board of Trustees", "local", "Round Rock ISD orders of election"),
    "eastwood-mud": ("the Eastwood MUD board", "local", "temporary directors: Water Code §49.102(d)"),
    "hero-way-west-mud": ("the Hero Way West MUD board", "local", "Elec. Code §67.002"),
    "hidden-lakes-mud-1": ("the Hidden Lakes MUD No. 1 board", "local", "temporary directors: Water Code §49.102(d)"),
    "kennedy-hill-mud": ("the Kennedy Hill MUD board", "local", "temporary directors: Water Code §49.102(d)"),
    "north-austin-mud-1": ("the North Austin MUD No. 1 board", "local", "its order of election"),
    "northtown-mud": ("the Northtown MUD board", "local", "its order of election"),
    "sunfield-mud-2": ("the Sunfield MUD No. 2 board", "local", "its order of election"),
    "travis-county-mmd-1": ("the Travis County MMD No. 1 board", "local", "initial directors; its order of election"),
    "travis-county-mud-41": ("the Travis County MUD No. 41 board", "local", "temporary directors: Water Code §49.102(d)"),
    "vista-mud": ("the Vista MUD board", "local", "its order of election"),
    "williamson-travis-mud-1": ("the Williamson-Travis Counties MUD No. 1 board", "local", "its order of election"),
    "cypress-ranch-wcid-1": ("the Cypress Ranch WCID No. 1 board", "local", "its order of election"),
    "travis-county-wcid-17": ("the Travis County WCID No. 17 board", "local", "its order of election"),
    "esd-4": ("the Travis County ESD No. 4 board", "local", "Elec. Code §67.002 (its order doesn't say)"),
    "esd-9": ("the Travis County ESD No. 9 board", "local", "its order; Health & Safety Code §775.051"),
    "esd-10": ("the Travis County ESD No. 10 board", "local", "Elec. Code §67.002 (its order doesn't say)"),
    "wells-branch-library": ("the Wells Branch Community Library District board", "local", "its order of election"),
}

# ---------------------------------------------------------------- each entity: canvasser, counties, majority rule
# majority: True (a runoff otherwise), False (plurality), "unsure" (a verdict only where both readings agree).
ENTITIES = {
    "Travis County": ("travis-county", ["travis"], False, "general-election county offices: plurality, Elec. Code §2.001"),
    "Travis Central Appraisal District": ("tcad", ["travis"], True, "Tax Code §6.0301(c): majority, runoff otherwise"),
    "City of Austin": ("city-of-austin", ["travis", "williamson", "hays"], True, "Ord. 20260806-003: 'elected by majority vote'; city spans three counties (Ord. 20260806-002 p1)"),
    "City of Elgin": ("city-of-elgin", ["bastrop", "travis"], False, "Bastrop + Travis (Travis precincts 490, 145, 146); a measure only"),
    "City of Jonestown": ("city-of-jonestown", ["travis"], False, "plurality: Elec. Code §2.001; Travis only per its order"),
    "City of Lago Vista": ("city-of-lago-vista", ["travis"], False, "plurality: Ord. 26-07-16-01 §13"),
    "City of Manor": ("city-of-manor", ["travis"], True, "charter §5.11 runoff; UNVERIFIED: current charter text not read"),
    "City of Pflugerville": ("city-of-pflugerville", ["travis", "williamson"], True, "at-large; INFERRED majority from the 2025 mayoral runoff"),
    "City of Sunset Valley": ("city-of-sunset-valley", ["travis"], False, "plurality: Elec. Code §2.001; one election precinct"),
    "Village of Volente": ("village-of-volente", ["travis"], False, "plurality: Elec. Code §2.001; Travis only per Res. 2026-R-02"),
    "Austin Community College": ("acc", ["travis", "williamson", "hays", "bastrop", "caldwell", "lee"], True, "six counties per its order (pp. 2-3); majority per its order; 2024 runoff"),
    "Austin ISD": ("austin-isd", ["travis"], True, "majority per its order; Travis only"),
    "Coupland ISD": ("coupland-isd", ["travis", "williamson"], False, "Travis + Williamson per its order (not Bastrop); measures only"),
    "Del Valle ISD": ("del-valle-isd", ["travis"], "unsure", "UNVERIFIED: plurality by 2014 practice only; its order is silent"),
    "Leander ISD": ("leander-isd", ["travis", "williamson"], False, "plurality: 2022 Community Impact report and 2022 winners at 35-44%"),
    "Manor ISD": ("manor-isd", ["travis"], False, "measures only"),
    "Pflugerville ISD": ("pflugerville-isd", ["travis", "williamson"], "unsure", "UNVERIFIED; only two-candidate and one-candidate races, so it can't change a result"),
    "Round Rock ISD": ("round-rock-isd", ["travis", "williamson"], False, "plurality: no runoff clause; Place 4 won with 43.2% in 2022"),
    "Eastwood MUD": ("eastwood-mud", ["travis"], False, "directors: plurality, Water Code §49.102(g)"),
    "Hero Way West MUD": ("hero-way-west-mud", ["travis"], False, "plurality: Elec. Code §2.001"),
    "Hidden Lakes MUD No. 1": ("hidden-lakes-mud-1", ["travis"], False, "directors: plurality, Water Code §49.102(g)"),
    "Kennedy Hill MUD": ("kennedy-hill-mud", ["travis"], False, "directors: plurality, Water Code §49.102(g)"),
    "North Austin MUD No. 1": ("north-austin-mud-1", ["travis", "williamson"], False, "four of its five precincts are in Williamson"),
    "Northtown MUD": ("northtown-mud", ["travis"], False, "plurality"),
    "Sunfield MUD No. 2": ("sunfield-mud-2", ["travis", "hays"], False, "Hays + Travis per its order"),
    "Travis County MMD No. 1": ("travis-county-mmd-1", ["travis"], False, "created by TCEQ Aug 17, 2026 (Local Gov't Code ch. 375); no confirmation vote"),
    "Travis County MUD No. 41": ("travis-county-mud-41", ["travis"], False, "directors: plurality, Water Code §49.102(g)"),
    "Vista MUD of Travis County": ("vista-mud", ["travis"], False, "plurality"),
    "Williamson-Travis Counties MUD No. 1": ("williamson-travis-mud-1", ["travis", "williamson"], False, "spans Williamson per its order"),
    "Cypress Ranch WCID No. 1": ("cypress-ranch-wcid-1", ["travis"], False, "plurality"),
    "Travis County WCID No. 17": ("travis-county-wcid-17", ["travis"], False, "plurality"),
    "Travis County ESD No. 4": ("esd-4", ["travis"], False, "measure only"),
    "Travis County ESD No. 9": ("esd-9", ["travis"], False, "measures only"),
    "Travis County ESD No. 10": ("esd-10", ["travis"], False, "measures only"),
    "Wells Branch Community Library District": ("wells-branch-library", ["travis"], False, "Travis only per its order"),
}

# ---------------------------------------------------------------- the 42 contests the SOS reports (feed 53815)
# race id, the feed's race name, declared write-ins (the feed's party "W"; capitals normalized, W67)
SOS = {
    "c001": ("5075", "U. S. SENATOR", ["Avery Ayers", 'Bradford "Brad" Hall', "Zul Mohamed", "Jade Simmons"]),
    "c002": ("5039", "U. S. REPRESENTATIVE DISTRICT 10", []),
    "c003": ("5067", "U. S. REPRESENTATIVE DISTRICT 37", []),
    "c004": ("5040", "U. S. REPRESENTATIVE DISTRICT 11", []),
    "c005": ("5057", "U. S. REPRESENTATIVE DISTRICT 27", ["Wayne Raasch"]),
    "c006": ("3579", "GOVERNOR", ["Edward Earl Giles", "Jenn Mack", "Jinghpaw Majoishingra", "Mike Miller"]),
    "c007": ("4714", "LIEUTENANT GOVERNOR", ["Arturo Espinosa", "Stephen Samuelson"]),
    "c008": ("3", "ATTORNEY GENERAL", []),
    "c009": ("21", "COMPTROLLER OF PUBLIC ACCOUNTS", []),
    "c010": ("20", "COMMISSIONER OF THE GENERAL LAND OFFICE", []),
    "c011": ("19", "COMMISSIONER OF AGRICULTURE", []),
    "c012": ("4843", "RAILROAD COMMISSIONER", []),
    "c013": ("18", "CHIEF JUSTICE, SUPREME COURT", []),
    "c014": ("4706", "JUSTICE, SUPREME COURT, PLACE 2 - UNEXPIRED TERM", []),
    "c015": ("4711", "JUSTICE, SUPREME COURT, PLACE 7", []),
    "c016": ("4712", "JUSTICE, SUPREME COURT, PLACE 8", []),
    "c017": ("3819", "JUDGE, COURT OF CRIMINAL APPEALS, PLACE 3", []),
    "c018": ("3820", "JUDGE, COURT OF CRIMINAL APPEALS, PLACE 4", []),
    "c019": ("3823", "JUDGE, COURT OF CRIMINAL APPEALS, PLACE 9", []),
    "c020": ("4725", "MEMBER, STATE BOARD OF EDUCATION, DISTRICT 5", []),
    "c021": ("5019", "STATE SENATOR, DISTRICT 21", []),
    "c022": ("4917", "STATE REPRESENTATIVE DISTRICT 19", []),
    "c023": ("4947", "STATE REPRESENTATIVE DISTRICT 46", []),
    "c024": ("4948", "STATE REPRESENTATIVE DISTRICT 47", []),
    "c025": ("4949", "STATE REPRESENTATIVE DISTRICT 48", []),
    "c026": ("4950", "STATE REPRESENTATIVE DISTRICT 49", []),
    "c027": ("4952", "STATE REPRESENTATIVE DISTRICT 50", []),
    "c028": ("4953", "STATE REPRESENTATIVE DISTRICT 51", []),
    "c029": ("15242", "CHIEF JUSTICE, 15TH COURT OF APPEALS DISTRICT", []),
    "c030": ("15243", "JUSTICE, 15TH COURT OF APPEALS DISTRICT, PLACE 2", []),
    "c031": ("15244", "JUSTICE, 15TH COURT OF APPEALS DISTRICT, PLACE 3", []),
    "c032": ("11", "CHIEF JUSTICE, 3RD COURT OF APPEALS DISTRICT", []),
    "c033": ("3131", "DISTRICT JUDGE, 147TH JUDICIAL DISTRICT", []),
    "c034": ("3192", "DISTRICT JUDGE, 201ST JUDICIAL DISTRICT", []),
    "c035": ("3246", "DISTRICT JUDGE, 250TH JUDICIAL DISTRICT", []),
    "c036": ("3258", "DISTRICT JUDGE, 261ST JUDICIAL DISTRICT", []),
    "c037": ("3299", "DISTRICT JUDGE, 299TH JUDICIAL DISTRICT", []),
    "c038": ("3337", "DISTRICT JUDGE, 331ST JUDICIAL DISTRICT", []),
    "c039": ("3414", "DISTRICT JUDGE, 403RD JUDICIAL DISTRICT", []),
    "c040": ("3431", "DISTRICT JUDGE, 419TH JUDICIAL DISTRICT", []),
    "c041": ("3470", "DISTRICT JUDGE, 455TH JUDICIAL DISTRICT", []),
    "c043": ("3474", "DISTRICT JUDGE, 459TH JUDICIAL DISTRICT", []),
}
# Decided entirely in Travis (the SOS county file lists these races under Travis alone): no "How Travis County voted"
TRAVIS_ONLY = {"c003", "c023", "c024", "c025", "c026", "c027", "c028", "c033", "c034", "c035", "c036", "c037", "c038",
               "c039", "c040", "c041", "c043"}

# ---------------------------------------------------------------- contest by contest
# Registered voters for counties no file will ever come from (Caldwell, Lee: no machine-readable results, Task 1
# finding 11): the whole county's, from the SOS feed for election 53815 (countyInfo, Oct 16, 2026). An upper bound of
# ACC's slice there, so the partial rule is only ever more careful for it.
ACC_REGISTERED = {"caldwell": 28491, "lee": 12262}
ANNEX = {  # annexations voted separately by the district and the area to be added (one outcome line, W33/W38)
    "c206": ("district", "c208"), "c208": ("area", "c206"), "c207": ("district", "c209"), "c209": ("area", "c207"),   # ESD 9
    "c210": ("district", "c212"), "c212": ("area", "c210"), "c211": ("district", "c213"), "c213": ("area", "c211"),   # ESD 10
}
CONFIRMATION = {  # a MUD's confirmation vote; if it fails, every other contest of the district carries the note
    "c147": [f"c{i}" for i in range(148, 155)],   # Eastwood MUD
    "c158": [f"c{i}" for i in range(159, 169)],   # Hidden Lakes MUD No. 1
    "c169": [f"c{i}" for i in range(170, 177)],   # Kennedy Hill MUD
    "c193": [f"c{i}" for i in range(194, 200)],   # Travis County MUD No. 41
}
TWO_THIRDS = ["c150", "c157", "c161", "c172", "c181", "c188", "c196"]   # road bonds: Tex. Const. art. III §52(b)
UNSURE_THRESHOLD = ["c153", "c162", "c175", "c184", "c191", "c198"]    # refunding road bonds: UNVERIFIED (two-thirds or a majority)
OVERRIDES = {
    # Austin council districts: the Travis portion is confirmed; whether Williamson or Hays has voters in each is
    # settled from their own files on Nov 4 (a key, or "absent"). Until then: partial, never Travis alone.
    **{cid: {"possible": ["williamson", "hays"]} for cid in ("c066", "c067", "c068", "c069", "c070")},
    "c114": {"canvasser": "sunset-valley-ccpd"},
    "c120": {"electorate": ["travis", "williamson"], "who": "area"},     # ACC annexation: Pflugerville ISD not yet in ACC
    "c131": {"majority": "unsure"},                                     # Del Valle SMD 9, three candidates
    "c205": {"outcome_from_canvass": True},  # ESD 4 annexation: separate majorities (H&S Code §775.051(f)), one ballot listing
    **{cid: {"registered": ACC_REGISTERED} for cid in ("c117", "c118", "c119")},
}


def contests():
    key = check_results.answer_key()
    out = {}
    for cid, c in key.items():
        if cid in SOS:
            race, name, wi = SOS[cid]
            out[cid] = {"source": "sos", "canvasser": "legislature" if cid in ("c006", "c007") else "state",
                        "keys": {"sos": race, "travis": None}, "sos_name": name,
                        "write_ins": [{"name": n} for n in wi], "majority": False, "travis_only": cid in TRAVIS_ONLY}
            continue
        cv, counties, majority, why = ENTITIES[c["entity"]]
        m = {"source": "counties", "canvasser": cv, "electorate": list(counties), "keys": {k: None for k in counties},
             "write_ins": [], "majority": majority if c["type"] == "candidate" else False, "why": why}
        o = OVERRIDES.get(cid, {})
        if "possible" in o:
            m["electorate"] += [k for k in o["possible"] if k not in m["electorate"]]
            m["keys"].update({k: None for k in o["possible"]})
            m["possible"] = o["possible"]
        for k in ("canvasser", "who", "registered", "outcome_from_canvass"):
            if k in o:
                m[k] = o[k]
        if "electorate" in o:
            m["electorate"], m["keys"] = list(o["electorate"]), {k: None for k in o["electorate"]}
        if "majority" in o:
            m["majority"] = o["majority"]
        if cid in ANNEX:
            m["who"], m["pair"] = ANNEX[cid]
        for conf, deps in CONFIRMATION.items():
            if cid in deps:
                m["depends_on"] = conf
        if cid in TWO_THIRDS:
            m["needs"] = "two_thirds"
        if cid in UNSURE_THRESHOLD:
            m["needs"] = "unsure"
        out[cid] = m
    return out


def build(old=None):
    old = old or {}
    mp = {"meta": {"election": "2026-11-03", "sos_election": "53815", "sos_time_zone": "America/Chicago",
                   "late_until": "2026-11-17", "orders": ORDERS, "fetch": {"williamson": None, "hays": []}},
          "canvassers": {k: {"label": v[0], "kind": v[1], "why": v[2]} for k, v in CANVASSERS.items()},
          "contests": contests()}
    # what's filled in by hand is kept: each contest's keys (Nov 4), the fetch addresses and the SOS time zone
    for k in ("fetch", "sos_time_zone"):
        if k in (old.get("meta") or {}):
            mp["meta"][k] = old["meta"][k]
    for cid, m in mp["contests"].items():
        was = (old.get("contests") or {}).get(cid, {})
        for county, v in (was.get("keys") or {}).items():
            if county in m["keys"] and v is not None:
                m["keys"][county] = v
        if was.get("spell"):
            m["spell"] = was["spell"]
        if was.get("registered"):   # typed in for a county the tables don't cover; the tables' own numbers win
            m["registered"] = {**was["registered"], **m.get("registered", {})}
        if cid not in SOS and was.get("write_ins"):
            m["write_ins"] = was["write_ins"]
    return mp


def text(mp):
    return json.dumps(mp, indent=1, ensure_ascii=False) + "\n"


def main(argv):
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else None
    new = text(build(old))
    if "--check" in argv:
        if not OUT.exists() or json.loads(OUT.read_text(encoding="utf-8")) != json.loads(new):
            sys.exit("results map: source/results_map.json isn't what build_results_map.py writes: change the tables, then rerun it")
        print("results map: up to date"); return
    OUT.write_text(new, encoding="utf-8")
    print(f"results map: {len(json.loads(new)['contests'])} contests written")


if __name__ == "__main__":
    main(sys.argv)
