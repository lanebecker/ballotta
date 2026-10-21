"""Builds results.json from the raw files (docs/plans/2026-10-20-results.md, "How it's built").

    python3 source/build_results.py file-inbox            # moves Lane's downloads from source/results/inbox/<county>/
                                                          # into source/results/raw/, refusing a file in the wrong folder
    python3 source/build_results.py build [--prev FILE] [--out FILE] [--changes FILE]
                                                          # writes results.json (default: over the published one, which is
                                                          # also the default --prev) and the change list for the PR
    python3 source/build_results.py suggest FILE          # for each counties contest without a key for FILE's county,
                                                          # the source contests whose names fit (to confirm by hand)

Inputs: source/results_map.json (what each contest is and where its numbers come from), source/results/raw/ (every
file, as fetched or downloaded, never edited), source/results/excluded.json (raw files to ignore, with reasons),
source/results/official.json (canvasses, recounts, runoff dates, the kill switch) and the results.json published before
(seq, changed, corrected carry on from it). Deterministic: no clock, no network. The rules are source/results_rules.py;
the parsers source/results_parse.py; the shape is checked by source/check_results.py before anything is written.
"""
import hashlib, json, pathlib, re, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "source"))
import check_results, results_parse as P, results_rules as R  # noqa: E402

RES = ROOT / "source/results"
GENERIC_WRITE_IN = {"WRITE-IN", "WRITE-INS", "WRITE IN", "WRITE-IN TOTALS", "WRITE-IN VOTES", "UNRESOLVED WRITE-IN"}
SOURCE_OF = {"travis": "clarity", "bastrop": "clarity", "williamson": "williamson", "hays": "hays", "sos": "sos",
             "sos_canvass": "sos_canvass"}
LOCAL_BY, STATE_BY = "2026-11-17", "2026-12-07"


class Problem(Exception):
    """Something the build can't decide on its own: the run stops, naming it (never a guess)."""


def load(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def seats(contest):
    m = re.search(r"vote for up to (\d)", contest["title"])
    return int(m.group(1)) if m else 1


# ---------------------------------------------------------------- the raw files
def raw_dir(root, source, posted, data):
    return root / "raw" / source / (posted.replace(":", "-") + "-" + hashlib.sha256(data).hexdigest()[:8])


def file_inbox(res=RES):
    """Each file in inbox/<county>/ is parsed, checked to be that county's, and moved to raw/<county>/<posted>-<hash8>/.
    A file already filed (same hash) is just removed from the inbox. Returns the paths filed."""
    filed = []
    for folder in sorted((res / "inbox").glob("*")):
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if f.name.startswith(".") or not f.is_file():
                continue
            data = f.read_bytes()
            kind = "williamson" if folder.name == "williamson" else "hays" if folder.name == "hays" else "clarity"
            try:
                rep = P.PARSERS[kind](data)
            except P.BadFile as e:
                raise Problem(f"inbox/{folder.name}/{f.name}: {e}")
            if rep["source"] != folder.name:
                raise Problem(f"inbox/{folder.name}/{f.name} is {rep['label']}'s file: move it to inbox/{rep['source']}/")
            d = raw_dir(res, rep["source"], rep["posted"], data)
            if not d.exists():
                d.mkdir(parents=True)
                (d / f.name).write_bytes(data)
                filed.append(d / f.name)
            f.unlink()
    return filed


def latest(res, source, excluded):
    """The newest report from one source (by the time posted inside the file), excluded files skipped. Two different
    files posted at the same minute can't be told apart: a Problem, so Lane excludes the wrong one."""
    best = []
    for d in sorted((res / "raw" / source).glob("*")) if (res / "raw" / source).exists() else []:
        for f in sorted(d.iterdir()):
            rel = f.relative_to(res).as_posix()
            if rel in excluded or not f.is_file():
                continue
            try:
                rep = P.PARSERS[SOURCE_OF[source]](f.read_bytes(), **({"zone": ZONE[0]} if source == "sos" else {}))
            except P.BadFile as e:
                raise Problem(f"{rel}: {e} (add it to excluded.json with the reason)")
            rep["file"] = rel
            best.append(rep)
    if not best:
        return None
    best.sort(key=lambda r: r["posted"])
    if len(best) > 1 and best[-1]["posted"] == best[-2]["posted"]:
        raise Problem(f"{best[-2]['file']} and {best[-1]['file']} were both posted at {best[-1]['posted']}: exclude one")
    return best[-1]


ZONE = ["America/Chicago"]


# ---------------------------------------------------------------- one contest
def slice_of(rep, key, names, write_ins, spell, where):
    """One source's numbers for a contest, as [(pick name, votes)] in the page's order (ballot, then declared write-ins),
    plus registered voters. Every printed choice must be a ballot name, a declared write-in, or a generic write-in
    line (dropped: Ballotta never shows a ranked "Write-in" total); otherwise a Problem."""
    c = rep["contests"].get(key)
    if c is None:
        raise Problem(f"{where}: {rep['label']}'s file has no contest {key!r} (fix the map's key)")
    every = names + write_ins
    got = {}
    for printed, votes in c["choices"]:
        if P.norm(printed) in GENERIC_WRITE_IN:
            continue
        who = spell.get(printed) or P.match(printed, every)
        if who is None:
            raise Problem(f"{where}: {rep['label']} prints {printed!r}, which is none of {every} "
                          "(add it to the map's spell, or as a declared write-in)")
        if who in got:
            raise Problem(f"{where}: {rep['label']} prints two choices that read as {who!r}")
        got[who] = votes
    missing = [n for n in names if n not in got]
    if missing:
        raise Problem(f"{where}: {rep['label']} has no line for {missing}")
    return [(n, got[n]) for n in names] + [(n, got.get(n, 0)) for n in write_ins], c.get("registered")


def entry(cid, contest, m, reports, official, canvassers, prev_entry):
    """results.json's entry for one contest, or None when no source has it yet."""
    names, write_ins = check_results.pick_names(contest), [w["name"] for w in m.get("write_ins", [])]
    where = f"{cid} ({contest['title']})"
    cv_slug = m["canvasser"]
    cvr = canvassers[cv_slug]
    line = official.get("canvasses", {}).get(cv_slug, {})
    done = line.get("canvassed")
    sources, missing, slack, travis = [], [], 0, None
    official_numbers = True
    if m["source"] == "sos":
        feed, can = reports.get("sos"), reports.get("sos_canvass")
        if feed is None:
            return None
        rows, _ = slice_of(feed, m["keys"]["sos"], names, write_ins, m.get("spell", {}).get("sos", {}), where)
        sources.append([feed["label"], feed["posted"]])
        if done and can is not None and P.norm(m["sos_name"]) in can["contests"]:
            rows, _ = slice_of(can, P.norm(m["sos_name"]), names, write_ins, m.get("spell", {}).get("sos_canvass", {}), where)
            sources = [[can["label"], can["posted"]]]
        elif done:
            official_numbers = False                         # W11: official, but these are the last unofficial numbers
        if not m.get("travis_only") and reports.get("travis") and m["keys"].get("travis"):
            tv, _ = slice_of(reports["travis"], m["keys"]["travis"], names, write_ins, m.get("spell", {}).get("travis", {}), where)
            tt = sum(v for _, v in tv[: len(names)])
            travis = [[n, v, R.pct(v, tt)] for n, v in tv[: len(names)]]
    else:
        total = {n: 0 for n in names + write_ins}
        any_county = False
        for county in m["electorate"]:
            rep, key = reports.get(county), m["keys"].get(county)
            if key == "absent":                          # confirmed from that county's own file: none of its voters vote here
                continue
            if rep is None or not key:
                missing.append(P.LABELS[county])
                reg = m.get("registered", {}).get(county)
                slack = None if (slack is None or reg is None) else slack + reg
                continue
            rows, _ = slice_of(rep, key, names, write_ins, m.get("spell", {}).get(county, {}), where)
            any_county = True
            for n, v in rows:
                total[n] += v
            sources.append([rep["label"], rep["posted"]])
            if done and rep["posted"][:10] < done:
                official_numbers = False                     # a county's file is from before the canvass
            if county == "travis" and sum(1 for k in m["electorate"] if m["keys"].get(k) != "absent") > 1:
                tt = sum(v for _, v in rows[: len(names)])
                travis = [[n, v, R.pct(v, tt)] for n, v in rows[: len(names)]]
        if not any_county:
            return None
        rows = [(n, total[n]) for n in names + write_ins]
    if missing and done:
        raise Problem(f"{where}: {cvr['label']} canvassed it on {done}, but {missing} aren't loaded")
    cast = sum(v for _, v in rows)
    kind, n = contest["type"], seats(contest)
    if done and cast == 0 and not (kind == "candidate" and R.is_unopposed(names, n, write_ins)):
        raise Problem(f"{where}: {cvr['label']} canvassed it on {done}, but the numbers loaded have no votes")
    recount = (line.get("recount") or {}).get("link")
    needs = m.get("needs")                           # None | "two_thirds" | "unsure" (measures)
    try:
        if done and m.get("outcome_from_canvass"):
            # one total can't show the outcome (ESD 4's annexation, c205: separate majorities, one ballot listing):
            # the canvass's own outcome, entered by hand in official.json
            verdict = official.get("outcomes", {}).get(cid)
            if verdict not in ("passed", "failed"):
                raise Problem(f"{where}: canvassed; put its outcome in official.json's outcomes (passed or failed)")
            leaders, runoff, state = [], [], ("recount" if recount else "official")
        elif done:
            verdict, leaders, runoff = R.official(kind, rows, n, m.get("majority", False), write_ins, cid, needs)
            state = "recount" if recount else "official"
        elif m.get("outcome_from_canvass"):
            verdict, leaders, runoff = "none", [], []
        else:
            verdict, leaders, runoff = R.unofficial(kind, rows, n, m.get("majority", False), slack, write_ins, cid, needs)
    except ValueError as e:
        raise Problem(f"{where}: {e} (source/results_map.json)")
    no_call = None                                   # W69: why votes show with no verdict
    if not done and verdict == "none" and cast and slack is not None:
        if m.get("outcome_from_canvass"):
            no_call = "two_majorities"
        elif "unsure" in (m.get("majority"), needs):
            no_call = "rule_unsettled"
    if not done:
        state = "partial" if missing else ("counting" if cast == 0 and verdict != "unopposed" else "unofficial")
    return {
        "state": state, "verdict": verdict, "leaders": leaders, "runoff": runoff,
        "choices": [[nm, v, R.pct(v, cast), nm in write_ins] for nm, v in rows],
        "sources": sorted(sources, key=lambda s: s[1], reverse=True), "missing": missing, "travis": travis,
        "canvasser": cvr["label"],
        "canvass": {"kind": cvr["kind"], "by": None if cvr["kind"] == "legislature" else (STATE_BY if cvr["kind"] == "state" else LOCAL_BY),
                    "on": line.get("expected"), "done": done},
        "official_numbers": official_numbers if done else True,
        "changed": 0, "corrected": (prev_entry or {}).get("corrected"), "note": None, "who": m.get("who"),
        "runoff_on": official.get("runoffs", {}).get(cid) if verdict in ("runoff", "may_runoff", "tied_runoff") else None,
        "recount": recount, "write_ins": bool(write_ins), "needs": "two_thirds" if needs == "two_thirds" else None, "no_call": no_call,
    }


# ---------------------------------------------------------------- the whole file
def build(res=RES, mp=None, prev=None, key=None):
    """(results, changes): results.json's object, and {verdict_changed, lines} for the pull request."""
    mp = mp if mp is not None else load(ROOT / "source/results_map.json")
    key = key or check_results.answer_key()
    prev = prev or {"seq": 0, "election": "2026-11-03", "withdrawn": False, "late_until": mp["meta"]["late_until"], "contests": {}}
    official = load(res / "official.json", {}) or {}
    excluded = {x["path"]: x for x in load(res / "excluded.json", []) or []}
    ZONE[0] = mp["meta"]["sos_time_zone"]
    reports = {s: latest(res, s, excluded) for s in ("sos", "sos_canvass", "travis", "bastrop", "williamson", "hays")}
    reports = {s: r for s, r in reports.items() if r is not None}
    contests = {}
    if not official.get("withdrawn"):
        for cid, m in mp["contests"].items():
            e = entry(cid, key[cid], m, reports, official, mp["canvassers"], prev["contests"].get(cid))
            if e is not None:
                contests[cid] = e
        notes(contests, mp)
    corrections = {}
    for x in excluded.values():
        for cid in x.get("contests", []):
            corrections[cid] = max(corrections.get(cid, ""), x["date"])
    out = {"seq": prev["seq"], "election": "2026-11-03", "withdrawn": bool(official.get("withdrawn")),
           "late_until": official.get("late_until", mp["meta"]["late_until"]), "contests": contests}
    lines, verdict_changed, fresh = [], False, 0
    for cid in sorted(set(contests) | set(prev["contests"])):
        e, old = contests.get(cid), prev["contests"].get(cid)
        title = key[cid]["title"]
        if e is None:
            if old is not None:
                lines.append(f"- {title}: no longer shown ({cid})"); verdict_changed = True
            continue
        moved = old is None or (e["state"], e["verdict"], e["leaders"], e["runoff"], e["note"]) != (old["state"], old["verdict"], old["leaders"], old["runoff"], old["note"])
        if moved:
            verdict_changed = True
            if old is not None and old["verdict"] != e["verdict"] and corrections.get(cid, "") > (old.get("corrected") or ""):
                e["corrected"] = corrections[cid]
            if old is None and e["state"] == "counting":
                fresh += 1                                # first seen, no votes yet: one summary line, not dozens
            else:
                lines.append(f"- {title}: " + (f"{word(old)} → " if old else "") + word(e) + f" ({cid})")
        e["changed"] = -1 if moved else old["changed"]
    same = {k: v for k, v in out.items() if k != "seq"}
    was = {k: v for k, v in prev.items() if k != "seq"}
    if strip_changed(same) != strip_changed(was) or any(e["changed"] == -1 for e in contests.values()):
        out["seq"] = prev["seq"] + 1
    for e in contests.values():
        if e["changed"] == -1:
            e["changed"] = out["seq"]
    if fresh:
        lines.insert(0, f"- {fresh} contest{'s' if fresh > 1 else ''} now shown, no votes yet")
    if out["seq"] != prev["seq"] and not verdict_changed:
        lines.append("- Numbers only: no result changed")
    if out["withdrawn"] != prev.get("withdrawn"):
        verdict_changed = True
        lines.insert(0, "- RESULTS WITHDRAWN (the kill switch): every result is hidden" if out["withdrawn"] else "- Results restored (the kill switch is off)")
    bad = check_results.check(out, key, prev if prev.get("contests") or prev.get("seq") else None)
    if bad:
        raise Problem("the built file fails the check: " + "; ".join(bad[:10]))
    return out, {"verdict_changed": verdict_changed, "seq": out["seq"], "lines": lines,
                 "files": sorted(r["file"] for r in reports.values())}


def strip_changed(o):
    return {**o, "contests": {k: {**v, "changed": 0} for k, v in o["contests"].items()}}


VERDICT_WORDS = {"none": "No call yet", "leading": "Leading", "too_close": "Too close to call", "may_runoff": "May go to a runoff",
                 "runoff": "Headed to a runoff", "won": "Won", "elected": "Elected", "passing": "Passing", "failing": "Failing",
                 "passed": "Passed", "failed": "Failed", "failed_tie": "Failed on a tie", "unopposed": "Unopposed",
                 "tied": "Tied (state law decides)", "tied_legislature": "Tied (the Legislature decides)",
                 "tied_runoff": "Tied (goes to a runoff)", "tied_second": "Tie for the runoff spot (a recount decides)"}
NOTE_WORDS = {"district_not_confirmed": "the district wasn't confirmed", "annex_both": "annexed",
              "annex_district_rejected": "not annexed: the district voted no", "annex_area_rejected": "not annexed: the area voted no",
              "annex_both_rejected": "not annexed: both voted no"}


def word(e):
    """One contest's standing in plain words, for the pull request: "Leading: Jane Doe (unofficial)"."""
    if e["state"] == "counting":
        return "No votes yet"
    who = " and ".join(e["leaders"] or e["runoff"])
    state = {"partial": "partial: " + ", ".join(e["missing"]) + " missing", "recount": "official, recount requested"}.get(e["state"], e["state"])
    return VERDICT_WORDS[e["verdict"]] + (f": {who}" if who else "") + f" ({state})" + (f"; {NOTE_WORDS[e['note']]}" if e["note"] else "")


def notes(contests, mp):
    """Notes one contest's outcome puts on others: a failed confirmation on the whole district (W? district_not_confirmed);
    an annexation's two votes on each other (one outcome line)."""
    for cid, m in mp["contests"].items():
        dep = m.get("depends_on")
        if dep and cid in contests and contests.get(dep, {}).get("verdict") in ("failed", "failed_tie"):
            contests[cid]["note"] = "district_not_confirmed"
        pair = m.get("pair")
        if pair and cid in contests and pair in contests and contests[cid]["state"] in ("official", "recount") \
                and contests[pair]["state"] in ("official", "recount"):
            d_cid, a_cid = (cid, pair) if m.get("who") == "district" else (pair, cid)
            contests[cid]["note"] = R.annex_note(contests[d_cid]["verdict"] == "passed", contests[a_cid]["verdict"] == "passed")


# ---------------------------------------------------------------- helpers for the morning of Nov 4
def suggest(path, mp=None):
    """Which source contest each unkeyed counties contest probably is, by name: printed for a person to confirm."""
    mp = mp or load(ROOT / "source/results_map.json")
    data = pathlib.Path(path).read_bytes()
    rep = next((f(data) for k, f in P.PARSERS.items() if k in ("clarity", "williamson", "hays") and _ok(f, data)), None)
    if rep is None:
        raise Problem(f"{path} isn't a county results file Ballotta reads")
    key = check_results.answer_key()
    for cid, m in mp["contests"].items():
        if m["source"] != "counties" or rep["source"] not in m["electorate"] or m["keys"].get(rep["source"]):
            continue
        names = set(map(P.norm, check_results.pick_names(key[cid])))
        fits = [(k, c["name"]) for k, c in rep["contests"].items()
                if names <= {P.norm(n) for n, _ in c["choices"]} | ({"FOR", "AGAINST"} if key[cid]["type"] == "measure" else set())]
        print(f"{cid} {key[cid]['title']}: " + ("; ".join(f"{k} = {n}" for k, n in fits[:4]) or "no fit"))


def _ok(f, data):
    try:
        f(data); return True
    except Exception:
        return False


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "build"
    try:
        if cmd == "file-inbox":
            for f in file_inbox():
                print("filed", f.relative_to(ROOT))
        elif cmd == "build":
            arg = lambda k, d: pathlib.Path(argv[argv.index(k) + 1]) if k in argv else d
            out_path, prev_path = arg("--out", ROOT / "results.json"), arg("--prev", ROOT / "results.json")
            obj, changes = build(prev=load(prev_path))
            out_path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
            if "--changes" in argv:
                arg("--changes", None).write_text(json.dumps(changes, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            print(f"results: seq {obj['seq']}, {len(obj['contests'])} contests; verdict changed: {changes['verdict_changed']}")
            for ln in changes["lines"][:60]:
                print(ln)
        elif cmd == "suggest":
            suggest(argv[2])
        else:
            sys.exit(__doc__)
    except Problem as e:
        sys.exit(f"results build stopped: {e}")


if __name__ == "__main__":
    main(sys.argv)
