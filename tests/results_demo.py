"""Demo results for every contest, for looking at the page (Lane's wording pass and visual review). Never published.

    python3 tests/results_demo.py OUT.json nov4|nov13|dec8

Made-up numbers, run through the real rules (source/results_rules.py) with the real canvassers (source/results_map.json);
every source is labeled "TEST DATA (not real results)". Guardrail: a contested partisan race is always too close to
call, so no picture shows a real candidate in a party race winning or losing; nonpartisan local races get made-up
leaders so Leading / Won / Didn't win can be seen. The Dec 8 scene (the state canvass done) makes the state's races
official, so a party race has a winner there: it is for the locked demo only, where every candidate's name is made up
(source/build_demo.py); never use it with real names.
"""
import json, pathlib, random, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "source"))
import check_results, results_rules as R  # noqa: E402

KEY = check_results.answer_key()
MAP = json.loads((ROOT / "source/results_map.json").read_text(encoding="utf-8"))
TEST = "TEST DATA (not real results)"
PARTY = re.compile(r"\((REP|DEM|LIB|GRN)\)$")
# Chosen outcomes for the demo ballot (precinct 300) so every state shows up; anything else is drawn at random.
SHAPE = {  # cid: shares of the ballot's choices, in ballot order
    "c070": [0.49, 0.24, 0.15, 0.08, 0.04],   # Austin District 9: may go to a runoff, then a runoff
    "c071": [0.58, 0.42], "c072": [0.44, 0.56], "c073": [0.503, 0.497], "c074": [0.61, 0.39], "c075": [0.53, 0.47],
    "c117": [0.57, 0.43], "c119": [0.41, 0.59], "c125": [0.55, 0.30, 0.15], "c065": [0.47, 0.53],
}
PARTIAL = {"c071", "c072", "c073", "c074", "c075", "c076", "c077", "c078", "c079", "c080"}   # Hays not in yet on Nov 4


def shares(cid, n, rng):
    if cid in SHAPE and len(SHAPE[cid]) == n:
        return SHAPE[cid]
    w = [rng.uniform(0.6, 1.6) for _ in range(n)]
    return [x / sum(w) for x in w]


def votes_for(cid, c, rng, cast):
    names = check_results.pick_names(c)
    partisan = any(PARTY.search(x) for x in c["choices"])
    if partisan and len(names) > 1:          # the guardrail: always too close to call
        third = [0.012] * (len(names) - 2)
        top = (1 - sum(third)) / 2
        sh = [top + 0.0015, top - 0.0015] + third
        if random.Random("order:" + cid).random() < 0.5:   # who's ahead by a hair is a coin toss, so the Dec 8 scene's winners show no pattern (#139)
            sh[0], sh[1] = sh[1], sh[0]
    else:
        sh = shares(cid, len(names), rng)
    return list(zip(names, [round(cast * s) for s in sh]))


def entry(cid, when):
    c, m = KEY[cid], MAP["contests"][cid]
    rng = random.Random(cid)
    cast = rng.randint(4000, 9000) if m["source"] == "counties" and len(m["electorate"]) == 1 else rng.randint(120000, 400000)
    if m["source"] == "sos":
        cast = rng.randint(600000, 9000000) if not m.get("travis_only") else rng.randint(40000, 90000)
    rows = votes_for(cid, c, rng, cast)
    wi = [w["name"] for w in m.get("write_ins", [])]
    rows += [(w, rng.randint(200, 2000)) for w in wi]
    cv = MAP["canvassers"][m["canvasser"]]
    local_done = when in ("nov13", "dec8") and cv["kind"] == "local" or when == "dec8" and cv["kind"] == "state"
    missing = ["Hays County"] if when == "nov4" and cid in PARTIAL else []
    slack = 565 if missing else 0
    n = int(re.search(r"vote for up to (\d)", c["title"]).group(1)) if "vote for up to" in c["title"] else 1
    needs = m.get("needs")
    try:
        if local_done and not m.get("outcome_from_canvass"):
            v, leaders, runoff = R.official(c["type"], rows, n, m["majority"], wi, cid, needs)
        elif m.get("outcome_from_canvass"):
            v, leaders, runoff = (("passed", [], []) if local_done else ("none", [], []))
        else:
            v, leaders, runoff = R.unofficial(c["type"], rows, n, m["majority"], slack, wi, cid, needs)
    except ValueError:
        v, leaders, runoff = R.unofficial(c["type"], rows, n, m["majority"], slack, wi, cid, needs)
        local_done = False
    total = sum(x for _, x in rows)
    posted = {"nov4": "2026-11-04T08:41", "nov13": "2026-11-13T08:30", "dec8": "2026-12-08T09:15"}[when]
    travis = None
    if m["source"] == "sos" and not m.get("travis_only") or (m["source"] == "counties" and len(m["electorate"]) > 1):
        tt = [round(x * rng.uniform(0.18, 0.3)) for _, x in rows[: len(check_results.pick_names(c))]]
        travis = [[nm, x, R.pct(x, sum(tt))] for (nm, _), x in zip(rows, tt)]
    state = "official" if local_done else ("partial" if missing else "unofficial")
    return {"state": state, "verdict": v, "leaders": leaders, "runoff": runoff,
            "choices": [[nm, x, R.pct(x, total), nm in wi] for nm, x in rows],
            "sources": [[TEST, posted]], "missing": missing, "travis": travis, "canvasser": cv["label"],
            "canvass": {"kind": cv["kind"], "by": None if cv["kind"] == "legislature" else ("2026-12-07" if cv["kind"] == "state" else "2026-11-17"),
                        "on": "2026-11-12" if cid in ("c070", "c071") and when == "nov4" else None,
                        "done": ("2026-12-07" if cv["kind"] == "state" else "2026-11-12") if local_done else None},
            "official_numbers": True, "changed": 1, "corrected": None, "note": None, "who": m.get("who"),
            "runoff_on": "2026-12-12" if v == "runoff" and local_done else None, "recount": None,
            "write_ins": bool(wi), "needs": "two_thirds" if needs == "two_thirds" else None}


def scene(when):
    contests = {cid: entry(cid, when) for cid in KEY}
    seq = {"nov4": 1, "nov13": 2, "dec8": 3}[when]
    for e in contests.values():
        if seq > 1:
            e["changed"] = 1 if e["state"] != "official" else 3 if e["canvass"]["kind"] == "state" else 2
    return {"seq": seq, "election": "2026-11-03", "withdrawn": False, "late_until": "2026-11-17", "contests": contests}


if __name__ == "__main__":
    out, when = pathlib.Path(sys.argv[1]), sys.argv[2]
    obj = scene(when)
    bad = check_results.check(obj, KEY)
    if bad:
        sys.exit("demo fails the check: " + "; ".join(bad[:8]))
    out.write_text(json.dumps(obj, ensure_ascii=False) + "\n", encoding="utf-8")
    import collections
    print(when, collections.Counter((e["state"], e["verdict"]) for e in obj["contests"].values()).most_common())
