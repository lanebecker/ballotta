"""Mutation check for the results back end (docs/plans/2026-10-20-results.md, Task 6): each mutant below is a small,
plausible bug in the rules, the parsers, the build or the fetcher, and tests/test_results.py must turn red on every
one. No browser; about two minutes.

    python3 tests/mutate_backend.py          # from the repo root; restores every file, even when stopped
"""
import pathlib, signal, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
S = ROOT / "source"
RULES, PARSE, BUILD, FETCH = S / "results_rules.py", S / "results_parse.py", S / "build_results.py", S / "fetch_results.py"
M = [
    ("B1 the 20-vote floor is 19", RULES, "POINT, FLOOR = 1, 20", "POINT, FLOOR = 1, 19"),
    ("B2 a point exactly isn't enough", RULES, "Fraction(100 * gap, cast) >= POINT", "Fraction(100 * gap, cast) > POINT"),
    ("B3 a missing county's voters ignored", RULES, "gap, cast = a - b - slack, total + slack", "gap, cast = a - b, total"),
    ("B4 52% exactly leads", RULES, "if worst > MAJ_HIGH and", "if worst >= MAJ_HIGH and"),
    ("B5 a runoff pair named when second and third are close", RULES, "pair = [r[0][0], r[1][0]] if clear(r[1][1], r[2][1], total, slack) else []", "pair = [r[0][0], r[1][0]]"),
    ("B6 a measure passes on any lead", RULES, "- 100 * need >= Fraction(1, 2) and f - need * cast >= FLOOR // 2:", "- 100 * need >= 0 and f - need * cast >= FLOOR // 2:"),
    ("B7 a tied measure passes", RULES, '"failed_tie" if f == a', '"passed" if f == a'),
    ("B8 exactly two-thirds fails", RULES, "3 * f >= 2 * total", "3 * f > 2 * total"),
    ("B9 a Governor tie goes to state law", RULES, 'LEGISLATURE_TIES = {"c006", ', 'LEGISLATURE_TIES = {'),
    ("B10 a declared write-in doesn't count against unopposed", RULES, "return len(candidates) <= seats and not write_ins", "return len(candidates) <= seats"),
    ("B11 an unsettled threshold reads as a majority", RULES, 'return (a if a == b else "too_close"), [], []', "return a, [], []"),
    ("B12 an unsettled majority rule reads as plurality", RULES, 'return a if a == b else ("none", [], [])', "return a"),
    ("B13 a two-way majority tie is just tied", RULES, 'return "tied_runoff", [], []', 'return "tied", [], []'),
    ("B14 precincts never added up", PARSE, "if ps and sum(int(p.get(\"votes\")) for p in ps) != int(vt.get(\"votes\")):", "if False:"),
    ("B15 Williamson's two copies never compared", PARSE, 'if rid in pies and [[str(x[0]), int(x[-1])] for x in pies[rid]] != choices:', "if False:"),
    ("B16 an SOS total never checked", PARSE, '            if "T" in r and r["T"] is not None:\n', '            if False:\n'),
    ("B17 Clarity's zone ignored", PARSE, 'posted = local(t) if m.group(2) in ("CST", "CDT") else stamp(t.replace(tzinfo=dt.timezone.utc))', "posted = local(t)"),
    ("B18 a wrapped name dropped", PARSE, '            choices[-1][0] += ("" if choices[-1][0].endswith("-") else " ") + ln\n', '            pass\n'),
    ("B19 a loose name match that isn't unique", PARSE, "return loose[0] if len(loose) == 1 else None", "return loose[0] if loose else None"),
    ("B20 a file in the wrong folder filed", BUILD, 'if rep["source"] != folder.name:', "if False:"),
    ("B21 excluded files read", BUILD, "if rel in excluded or not f.is_file():", "if not f.is_file():"),
    ("B22 two files the same minute: the later one wins", BUILD, 'if len(best) > 1 and best[-1]["posted"] == best[-2]["posted"]:', "if False:"),
    ("B23 a missing county with unknown voters still gets a verdict", BUILD, 'slack = None if (slack is None or reg is None) else slack + reg', "slack = slack + (reg or 0)"),
    ("B24 official through any canvasser", BUILD, 'line = official.get("canvasses", {}).get(cv_slug, {})', 'line = next(iter(official.get("canvasses", {}).values()), {})'),
    ("B25 numbers before the canvass called official", BUILD, 'if done and rep["posted"][:10] < done:', "if False:"),
    ("B26 a correction never named", BUILD, '                e["corrected"] = corrections[cid]\n', '                pass\n'),
    ("B27 seq never moves", BUILD, '        out["seq"] = prev["seq"] + 1\n', '        out["seq"] = prev["seq"]\n'),
    ("B28 a generic write-in line counted", BUILD, 'if P.norm(printed) in GENERIC_WRITE_IN:', "if False:"),
    ("B29 an annexation's two votes swapped", BUILD, 'd_cid, a_cid = (cid, pair) if m.get("who") == "district" else (pair, cid)', 'd_cid, a_cid = (pair, cid) if m.get("who") == "district" else (cid, pair)'),
    ("B30 the canvass report fetched before it exists", FETCH, "    if has_canvass:\n", "    if True:\n"),
]
ORIG = {}


def restore(*_):
    for f, text in ORIG.items():
        f.write_text(text, encoding="utf-8")
    if _:
        sys.exit("stopped: files restored")


def main():
    for name, f, a, z in M:
        n = f.read_text(encoding="utf-8").count(a)
        assert n == 1, (name, "anchor found", n, "times in", f.name)
    signal.signal(signal.SIGINT, restore); signal.signal(signal.SIGTERM, restore)
    base = subprocess.run([sys.executable, str(ROOT / "tests/test_results.py")], capture_output=True, text=True)
    assert base.returncode == 0, "the results tests must pass unmutated first:\n" + base.stdout[-2000:]
    survived = []
    try:
        for name, f, a, z in M:
            ORIG.setdefault(f, f.read_text(encoding="utf-8"))
            f.write_text(ORIG[f].replace(a, z, 1), encoding="utf-8")
            r = subprocess.run([sys.executable, str(ROOT / "tests/test_results.py")], capture_output=True, text=True)
            f.write_text(ORIG[f], encoding="utf-8")
            failed = [ln.split(" - ")[0][5:] for ln in r.stdout.splitlines() if ln.startswith("FAIL ")]
            print(f"{name}: " + (f"KILLED {', '.join(failed[:3])}" if r.returncode else "SURVIVED"), flush=True)
            if not r.returncode:
                survived.append(name)
    finally:
        restore()
    print(f"{len(M) - len(survived)} of {len(M)} mutants killed")
    sys.exit(1 if survived else 0)


if __name__ == "__main__":
    main()
