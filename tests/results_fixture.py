"""Sample results.json files for tests and for Lane's local look (never published: docs/plans/2026-10-20-results.md).

    python3 tests/results_fixture.py OUT.json [scene]     # writes one scene (default: mixed) and checks it

Every source is labeled "TEST DATA", so a screenshot can't pass for real results. Names come from the answer key (the
page matches picks by them); the votes are made up. Each file passes source/check_results.py.
"""
import json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "source"))
import check_results  # noqa: E402

KEY = check_results.answer_key()
TEST = "TEST DATA (not real results)"


def entry(cid, state="unofficial", verdict="leading", votes=None, leaders=None, runoff=(), write_ins=(), travis=None, missing=(),
          kind="local", canvasser="the Austin City Council", by="2026-11-17", on=None, done=None, official_numbers=True,
          changed=1, corrected=None, note=None, who=None, runoff_on=None, recount=None, posted=("2026-11-04T08:41",)):
    c = KEY[cid]
    names = check_results.pick_names(c)
    votes = list(votes) if votes is not None else [1000 * (len(names) - i) for i in range(len(names))]
    rows = list(zip(names, votes)) + [(n, v) for n, v in write_ins]
    total = sum(v for _, v in rows) or 1
    choices = [[n, v, round(100 * v / total, 2), i >= len(names)] for i, (n, v) in enumerate(rows)]
    if leaders is None:
        leaders = [] if verdict not in ("leading", "won", "elected", "unopposed") else [max(rows, key=lambda r: r[1])[0]]
    tv = None
    if travis is not None:
        tt = sum(travis) or 1
        tv = [[n, v, round(100 * v / tt, 2)] for n, v in zip(names, travis)]
    srcs = [[TEST, t] for t in posted]
    return {"state": state, "verdict": verdict, "leaders": list(leaders), "runoff": list(runoff), "choices": choices,
            "sources": srcs, "missing": list(missing), "travis": tv, "canvasser": canvasser,
            "canvass": {"kind": kind, "by": by, "on": on, "done": done}, "official_numbers": official_numbers,
            "changed": changed, "corrected": corrected, "note": note, "who": who, "runoff_on": runoff_on, "recount": recount,
            "write_ins": bool(write_ins)}


def E(cid, over=None, **kw):
    """entry() with kw, then over's keys on top (the official scene's changes)."""
    return entry(cid, **{**kw, **(over or {})})


def scene(name="mixed"):
    S = "the state"
    e = {}
    if name in ("mixed", "official"):
        off = name == "official"
        # The most-watched race never shows a sample winner, even in TEST DATA: too close in every scene.
        e["c001"] = E("c001", kind="state", canvasser=S, by="2026-12-07", verdict="too_close", votes=[4000000, 3990000, 120000],
                          write_ins=[("Jade Simmons", 2100)], travis=[300000, 300000, 9000],
                          over={"state": "official", "verdict": "tied", "done": "2026-12-02", "official_numbers": False} if off else None)
        e["c006"] = entry("c006", kind="legislature", canvasser="the Legislature", by=None, verdict="too_close", votes=[4000000, 3995000, 90000], travis=[300000, 300000, 8000])
        e["c056"] = E("c056", verdict="unopposed", canvasser="the Travis County Commissioners Court", votes=[250000],
                          over={"state": "official", "verdict": "elected", "done": "2026-11-12"} if off else None)
        e["c069"] = entry("c069", verdict="too_close", votes=[10010, 9995], on="2026-11-12")
        e["c071"] = E("c071", verdict="passing", votes=[180000, 120000], travis=[172000, 114000],
                          posted=("2026-11-04T08:41", "2026-11-04T07:55"),
                          over={"state": "official", "verdict": "passed", "done": "2026-11-12"} if off else None)
        e["c072"] = entry("c072", state="partial", verdict="failing", votes=[90000, 140000], missing=("Hays County",), travis=[88000, 136000])
        e["c113"] = entry("c113", canvasser="the Sunset Valley City Council", votes=[400, 380, 120], leaders=["Sarah Ponder", "Robert Johnson"])
        e["c121"] = entry("c121", verdict="may_runoff", canvasser="the Austin ISD Board of Trustees", votes=[5100, 4900])
        e["c147"] = E("c147", verdict="failing", canvasser="the Eastwood MUD board", votes=[8, 30],
                          over={"state": "official", "verdict": "failed", "done": "2026-11-10", "note": "district_not_confirmed"} if off else None)
        e["c117"] = entry("c117", state="counting", verdict="none", votes=[0, 0], canvasser="the ACC Board of Trustees")
    if name == "withdrawn":
        return {"seq": 3, "election": "2026-11-03", "withdrawn": True, "late_until": "2026-11-17", "contests": {}}
    seq = 5 if name == "official" else 2
    for v in e.values():
        v["changed"] = min(v["changed"], seq)
    if name == "official":
        for cid in ("c001", "c056", "c071", "c147"):
            e[cid]["changed"] = 5
    return {"seq": seq, "election": "2026-11-03", "withdrawn": False, "late_until": "2026-11-17", "contests": e}


if __name__ == "__main__":
    out = pathlib.Path(sys.argv[1]); nm = sys.argv[2] if len(sys.argv) > 2 else "mixed"
    obj = scene(nm)
    bad = check_results.check(obj, KEY)
    if bad:
        sys.exit("fixture fails the check: " + "; ".join(bad))
    out.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{out}: scene {nm}, {len(obj['contests'])} contests, sound")
