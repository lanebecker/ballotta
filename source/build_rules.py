"""Map every contest in the Travis County answer key to Tax Office district codes.

Rule = list of OR-clauses; each clause = {field: [allowed values]} (AND across fields).
Pseudo-fields CD/HD/SD come from the Texas Legislative Council precinct table (authoritative
for state/federal), keyed by 2026 precinct number.
Confidence: "high" = code meaning confirmed by the county's JurisdictionCodes key and ballot text;
"medium" = plausible but unconfirmed (see note). Contests with rule None cannot be routed yet.
"""
import csv, json, re, collections, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent

KEY = json.load(open(HERE / "answer_key.json", encoding="utf-8"))
contests = KEY["contests"]

tlc = {}
for r in csv.DictReader(open(HERE / "data/travis_precincts26p_districts.csv")):
    tlc[int(r["PREC"])] = {"CD": "G" + r["PlanC2333"], "HD": "L" + r["PlanH2316"], "SD": "N" + r["PlanS2168"]}

ALL = [{}]  # empty clause = everyone in Travis County


def rule_for(c):
    t, ent = c["title"], c["entity"]
    m = re.match(r"United States Representative, District (\d+)", t)
    if m: return [{"CD": ["G" + m.group(1)]}], "high", None
    if t == "United States Senator": return ALL, "high", None
    if c["level"] in ("State", "Courts"):
        m = re.match(r"State Senator, District (\d+)", t)
        if m: return [{"SD": ["N" + m.group(1)]}], "high", None
        m = re.match(r"State Representative, District (\d+)", t)
        if m: return [{"HD": ["L" + m.group(1)]}], "high", None
        return ALL, "high", None  # statewide offices, SBOE 5 (all Travis), appeals courts, district judges
    if ent == "Travis Central Appraisal District": return ALL, "high", None
    if ent == "Travis County":
        m = re.match(r"County Commissioner, Precinct (\d)", t)
        if m: return [{"Commissioner": ["P0" + m.group(1)]}], "high", None
        m = re.match(r"Justice of the Peace, Precinct (\d)", t)
        if m: return [{"JPConstable": ["J0" + m.group(1)]}], "high", None
        m = re.match(r"County Constable, Precinct (\d)", t)
        if m: return [{"JPConstable": ["J0" + m.group(1)]}], "high", None
        return ALL, "high", None
    if ent == "City of Austin":
        m = re.search(r"District (\d+)", t)
        if m: return [{"Muni": ["C10", "C11"], "MuniSMD": ["CA" + m.group(1)]}], "high", None
        # Propositions: full-purpose residents certain; limited-purpose (C11) unconfirmed
        return [{"Muni": ["C10"]}, {"Muni": ["C11"], "_conf": "medium"}], "high", \
            "Austin limited-purpose residents may or may not vote on city propositions (asking the Tax Office)."
    city = {"City of Elgin": "C21", "City of Jonestown": "C01", "City of Lago Vista": "C02", "City of Manor": "C03",
            "City of Pflugerville": "C04", "City of Sunset Valley": "C06", "Village of Volente": "C22"}
    if ent in city:
        if ent == "City of Elgin":
            return [{"Muni": ["C21"]}], "medium", "The ballot doesn't say whether this is citywide or Ward 1 only; no Travis address is coded to Ward 1."
        return [{"Muni": [city[ent]]}], "high", None
    if ent == "Austin Community College":
        if "Proposition" in t:
            return [{"Temp": ["ACCX"]}], "high", None
        return [{"College": ["ACC"]}], "high", None
    if ent == "Austin ISD":
        m = re.search(r"District (\d)", t)
        if m: return [{"ISD": ["S01"], "ISDSMD": ["T4" + m.group(1)]}], "high", None
        return [{"ISD": ["S01"]}], "high", None
    if ent == "Del Valle ISD":
        m = re.search(r"District (\d)", t)
        if m: return [{"ISD": ["S02"], "ISDSMD": ["D2" + m.group(1)]}], "high", None
        return [{"ISD": ["S02"]}], "high", None
    isd = {"Coupland ISD": "S15", "Leander ISD": "S10", "Manor ISD": "S11", "Pflugerville ISD": "S13", "Round Rock ISD": "S14"}
    if ent in isd: return [{"ISD": [isd[ent]]}], "high", None
    mud = {"Eastwood MUD": "M123", "Hero Way West MUD": "M118", "Hidden Lakes MUD No. 1": "M127",
           "Kennedy Hill MUD": "M126", "North Austin MUD No. 1": "M20", "Northtown MUD": "M23",
           "Sunfield MUD No. 2": "M93", "Vista MUD of Travis County": "M14",
           "Williamson-Travis Counties MUD No. 1": "M50"}
    if ent in mud:
        code = mud[ent]
        return [{"MUD": [code]}, {"Temp": [code]}], "high", None
    if ent == "Travis County MMD No. 1":
        return [{"MUD": ["M125"]}, {"Temp": ["M125"]}], "medium", "Two possible county codes for this district (M125 or M119); using M125 until the Tax Office confirms."
    if ent == "Travis County MUD No. 41":   # Lane, Oct 17: route it at medium confidence rather than to nobody
        return [{"MUD": ["M41"]}, {"Temp": ["M41"]}], "medium", \
            "Matched to the county's district code M41, which the Tax Office hasn't confirmed is MUD No. 41."
    if ent == "Cypress Ranch WCID No. 1": return [{"WCID": ["W02"]}], "high", None
    if ent == "Travis County WCID No. 17": return [{"WCID": ["W17"]}], "high", None
    if ent == "Wells Branch Community Library District": return [{"Library": ["L02"]}], "high", None
    if ent == "Travis County ESD No. 4":
        return [{"Temp": ["E04A"]}], "medium", "Expansion-area election; the county tags 140 addresses, but which voters receive it is unconfirmed."
    if ent == "Travis County ESD No. 9":
        if "territory" in t:
            return [{"Temp": ["E09A"]}], "medium", "Annexation-territory version; voter group unconfirmed."
        return [{"ESD": ["E09"], "Temp!": ["E09A"]}], "medium", "Current-district version; voter group unconfirmed."
    if ent == "Travis County ESD No. 10":
        if "second" in t:
            return [{"Temp": ["E10A"]}], "medium", "Two versions of these measures exist; which group gets which is unconfirmed."
        return [{"ESD": ["E10"], "Temp!": ["E10A"]}], "medium", "Two versions of these measures exist; which group gets which is unconfirmed."
    raise ValueError("no rule for " + t)


# Contests no address reaches, each with the reason (cold audit, Oct 17, #4). The build stops on any other: one wrong
# or missing code hides a whole election from the voters who have it.
UNREACHED_OK = {}   # Travis County MUD No. 41 was here until Lane chose medium confidence on M41 (Oct 17)

rules = {}
for c in contests:
    r, conf, note = rule_for(c)
    rules[c["id"]] = {"clauses": r, "conf": conf, "note": note}


def applies(rule, rec):
    if rule["clauses"] is None:
        return None
    for cl in rule["clauses"]:
        ok = True
        for f, vals in cl.items():
            if f == "_conf": continue
            if f.endswith("!"):
                if (rec.get(f[:-1]) or "").strip() in vals: ok = False
            elif (rec.get(f) or "").strip() not in vals:
                ok = False
        if ok:
            return cl.get("_conf", rule["conf"])
    return None


if __name__ == "__main__":
    combos = [f["attributes"] for f in json.load(open(HERE / "data/combos_temp.json"))["features"]]
    hits = collections.Counter(); sets = collections.Counter(); problems = []
    by = {c["id"]: c for c in contests}
    no_tlc = collections.Counter()
    for rec in combos:
        p = rec.get("Precinct")
        if not p or p not in tlc:
            if p: no_tlc[p] += rec["n"]   # these addresses would get no US Rep, State Rep or State Senator: stop below
            # (a row with no precinct at all is not a voting address)
            continue
        rec = dict(rec, **tlc[p])
        got = [cid for cid in rules if applies(rules[cid], rec)]
        for cid in got: hits[cid] += rec["n"]
        sets[tuple(got)] += rec["n"]
        cds = [g for g in got if by[g]["title"].startswith("United States Representative")]
        hds = [g for g in got if by[g]["title"].startswith("State Representative")]
        sds = [g for g in got if by[g]["title"].startswith("State Senator")]
        if len(cds) != 1 or len(hds) != 1 or len(sds) > 1:   # not every precinct has a State Senate race this year
            problems.append((p, rec.get("Split"), len(cds), len(hds), len(sds)))
    never = [by[c]["title"] for c in rules if hits[c] == 0 and rules[c]["clauses"] is not None]
    print("combos:", len(combos), "distinct contest sets:", len(sets))
    sizes = [len(s) for s in sets]; print("contests per ballot: min", min(sizes), "max", max(sizes))
    print("routable contests:", sum(1 for c in rules.values() if c["clauses"] is not None), "of", len(rules))
    print("medium:", sum(1 for c in rules.values() if c["conf"] == "medium"), " unrouted:", sum(1 for c in rules.values() if c["clauses"] is None))
    print("contests matching zero addresses:", never)
    print("combos without exactly one US Rep and one State Rep:", problems[:10], len(problems))
    unreached = sorted({by[c]["entity"] for c in rules if hits[c] == 0})
    for e in unreached:
        print(f"no address reaches {e}: {UNREACHED_OK.get(e, 'NOT ALLOWED')}")
    bad = [e for e in unreached if e not in UNREACHED_OK] + [e for e in UNREACHED_OK if e not in unreached]
    if no_tlc: print("precincts missing from the Legislative Council table (addresses):", dict(no_tlc))
    if bad or problems or no_tlc:
        sys.exit(f"stopping: unexplained unreached contests {bad}, district problems {problems[:5]}, precincts without districts {dict(no_tlc)}")
    json.dump(rules, open(HERE / "rules.json", "w"), indent=1)
    json.dump({str(k): v for k, v in tlc.items()}, open(HERE / "tlc_precincts.json", "w"))
