"""The shape of results.json, and the check every published copy must pass (docs/plans/2026-10-20-results.md).

    python3 source/check_results.py                      # checks results.json; exits non-zero, naming each problem
    python3 source/check_results.py FILE [--prev OLD]    # checks FILE; with OLD (the copy published before it), also
                                                         # that seq goes up by one and posted times never go backwards

results.json is the same file for everyone: the page compares a visitor's picks with it on the device. Stdlib only, so
the Pages workflow's deploy job can run it even when the pipeline tests are skipped. The page checks the same shape
again before using anything in it (it is untrusted input there too).

The file (every key required unless marked optional):

  seq          int >= 0: +1 with every published change (the placeholder is 0)
  election     "2026-11-03"
  withdrawn    bool: true hides every result (the kill switch; W52)
  late_until   "YYYY-MM-DD": through this day an unofficial result says late ballots are still being counted (W4);
               after it, state contests say counting is finished (W5)
  contests     {contest id: entry}, only ids in source/answer_key.json

An entry:

  state        counting | unofficial | partial | official | recount
  verdict      none | leading | too_close | may_runoff | runoff | won | elected | passing | failing | passed | failed |
               failed_tie | unopposed | tied | tied_legislature | tied_runoff | tied_second
  leaders      [choice name]: who leads, won or was elected (empty when the verdict names no one)
  runoff       [choice name]: the two headed to a runoff (empty unless the verdict is runoff, and then 0 or 2)
  choices      [[name, votes, percent, write_in]] in ballot order; name is the page's own pick name (candidate
               names without the party; FOR / AGAINST); write_in true only for a declared write-in candidate, listed
               after the ballot's choices
  sources      [[label, posted]]: each source of these numbers ("Travis County", "Texas Secretary of State") and the
               time it posted them, "YYYY-MM-DDTHH:MM" in Austin time
  missing      [label]: counties in the electorate whose numbers aren't in yet (state partial)
  travis       [[name, votes, percent]] or null: how Travis County voted, for contests decided beyond the county
  canvasser    who makes it official, as the page says it: "the Austin City Council", "the state", "the Legislature"
  canvass      {kind: local | state | legislature, by: date or null (the last legal day), on: date or null (an
               announced meeting), done: date or null (canvassed)}
  official_numbers  bool: false when a contest is official but the numbers shown are the last unofficial count (W11)
  changed      int: the seq at which this contest's state or verdict last changed
  corrected    date or null: a published verdict was corrected that day (W51)
  note         null | district_not_confirmed | annex_both | annex_district_rejected | annex_area_rejected |
               annex_both_rejected
  who          null | district | area: which voters decide an annexation contest (W33)
  runoff_on    date or null: the runoff's date, once known (W30)
  recount      https URL or null (W29)
  write_ins    bool: declared write-in candidates are listed in choices (W45)
  needs        null | two_thirds: a measure that needs two-thirds of the vote to pass (road bonds, Tex. Const. art.
               III §52(b); W68)
  no_call      null | two_majorities | rule_unsettled: why votes are shown with no verdict (W69): an outcome that needs
               separate majorities one total can't show (ESD 4's annexation), or a rule not yet confirmed whose two
               readings disagree; settled at the canvass
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATE = re.compile(r"\d{4}-\d{2}-\d{2}$")
TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
STATES = {"counting", "unofficial", "partial", "official", "recount"}
VERDICTS = {"none", "leading", "too_close", "may_runoff", "runoff", "won", "elected", "passing", "failing", "passed", "failed",
            "failed_tie", "unopposed", "tied", "tied_legislature", "tied_runoff", "tied_second"}
NOTES = {None, "district_not_confirmed", "annex_both", "annex_district_rejected", "annex_area_rejected", "annex_both_rejected"}
KINDS = {"local", "state", "legislature"}
TOP = {"seq", "election", "withdrawn", "late_until", "contests"}
ENTRY = {"state", "verdict", "leaders", "runoff", "choices", "sources", "missing", "travis", "canvasser", "canvass",
         "official_numbers", "changed", "corrected", "note", "who", "runoff_on", "recount", "write_ins", "needs", "no_call"}
# The verdicts each state may carry: an unofficial count never says won, passed or elected (Lane, Oct 20: "Won" only
# when official), and an official one never says leading.
ALLOWED = {
    "counting": {"none"},
    "unofficial": {"none", "leading", "too_close", "may_runoff", "runoff", "passing", "failing", "unopposed"},
    "partial": {"none", "leading", "too_close", "may_runoff", "runoff", "passing", "failing", "unopposed"},
    "official": {"won", "elected", "passed", "failed", "failed_tie", "runoff", "tied", "tied_legislature", "tied_runoff", "tied_second"},
    "recount": {"won", "elected", "passed", "failed", "failed_tie", "runoff", "tied", "tied_legislature", "tied_runoff", "tied_second"},
}


def pick_names(contest):
    """The names the page stores picks under (template optionsOf()): FOR / AGAINST for a measure; otherwise the ballot's
    candidates without the party in parentheses, and never the Write-in line."""
    if contest["type"] == "measure":
        return ["FOR", "AGAINST"]
    return [re.sub(r"\s*\((REP|DEM|LIB|GRN)\)$", "", x) for x in contest["choices"] if x != "Write-in"]


def answer_key(root=ROOT):
    return {c["id"]: c for c in json.loads((root / "source/answer_key.json").read_text(encoding="utf-8"))["contests"]}


def is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def excluded_stamps(excluded):
    """{(source label, posted time): date excluded} for each raw file in excluded.json: a published time that came
    from one of these may go back to an older file's, and a contest that read from it is a correction (#154)."""
    import results_parse as P
    out = {}
    for x in excluded or []:
        parts = str(x.get("path", "")).split("/")
        if len(parts) >= 3 and parts[0] == "raw" and parts[1] in P.LABELS and len(parts[2]) >= 16:
            st = (P.LABELS[parts[1]], parts[2][:13] + ":" + parts[2][14:16])
            out[st] = max(out.get(st, ""), str(x.get("date", "")))
    return out


def check(obj, key, prev=None, rolled=None):
    """Problems with obj (parsed results.json) as a list of strings; [] when it's sound. key: answer_key(). prev: the
    copy published before it, or None."""
    bad = []
    if not isinstance(obj, dict):
        return ["results.json is not an object"]
    if set(obj) != TOP:
        bad.append(f"top-level keys {sorted(obj)} are not {sorted(TOP)}")
    seq = obj.get("seq")
    if not (isinstance(seq, int) and not isinstance(seq, bool) and seq >= 0):
        bad.append("seq must be an integer >= 0")
    if obj.get("election") != "2026-11-03":
        bad.append("election must be 2026-11-03")
    if not isinstance(obj.get("withdrawn"), bool):
        bad.append("withdrawn must be true or false")
    if not (isinstance(obj.get("late_until"), str) and DATE.match(obj["late_until"])):
        bad.append("late_until must be a date (YYYY-MM-DD)")
    contests = obj.get("contests")
    if not isinstance(contests, dict):
        return bad + ["contests must be an object"]
    for cid, e in contests.items():
        where = f"{cid}: "
        if cid not in key:
            bad.append(where + "not a contest on Travis ballots (source/answer_key.json)"); continue
        if not isinstance(e, dict):
            bad.append(where + "not an object"); continue
        if set(e) != ENTRY:
            bad.append(where + f"keys {sorted(set(e) ^ ENTRY)} missing or extra"); continue
        c, names = key[cid], pick_names(key[cid])
        if e["state"] not in STATES:
            bad.append(where + f"state {e['state']!r}")
        if e["verdict"] not in VERDICTS:
            bad.append(where + f"verdict {e['verdict']!r}")
        elif e["state"] in ALLOWED and e["verdict"] not in ALLOWED[e["state"]]:
            bad.append(where + f"verdict {e['verdict']} can't go with state {e['state']}")
        ch = e["choices"]
        if not (isinstance(ch, list) and all(isinstance(x, list) and len(x) == 4 and isinstance(x[0], str) and isinstance(x[1], int)
                                             and not isinstance(x[1], bool) and x[1] >= 0 and is_num(x[2]) and 0 <= x[2] <= 100
                                             and isinstance(x[3], bool) for x in ch)):
            bad.append(where + "choices must be [[name, votes >= 0, percent 0-100, write_in]]"); continue
        ballot = [x[0] for x in ch if not x[3]]
        if ballot != names:
            bad.append(where + f"the ballot's choices, in ballot order, are {names}, not {ballot}")
        if any(x[3] for x in ch) and not all(x[3] for x in ch[len(names):]):
            bad.append(where + "declared write-ins go after the ballot's choices")
        if c["type"] == "measure" and any(x[3] for x in ch):
            bad.append(where + "a measure has no write-ins")
        if e["write_ins"] != any(x[3] for x in ch):
            bad.append(where + "write_ins must say whether declared write-ins are listed")
        all_names = [x[0] for x in ch]
        if len(set(all_names)) != len(all_names):
            bad.append(where + "a choice is listed twice")
        for k in ("leaders", "runoff"):
            if not (isinstance(e[k], list) and all(isinstance(n, str) and n in all_names for n in e[k])):
                bad.append(where + f"{k} must name choices of this contest")
        if isinstance(e["runoff"], list) and len(e["runoff"]) not in (0, 2):
            bad.append(where + "runoff names two choices or none")
        if e["verdict"] != "runoff" and e["runoff"]:
            bad.append(where + "runoff names choices only with the runoff verdict")
        if e["verdict"] in ("leading", "won", "elected", "unopposed") and not e["leaders"]:
            bad.append(where + f"{e['verdict']} needs leaders")
        if e["verdict"] == "won" and isinstance(e["leaders"], list) and len(e["leaders"]) > 1:
            bad.append(where + "won names one winner; several are elected")
        if e["verdict"] in ("none", "too_close", "may_runoff", "runoff", "tied", "tied_legislature", "tied_runoff", "tied_second",
                            "passing", "failing", "passed", "failed", "failed_tie") and e["leaders"]:
            bad.append(where + f"{e['verdict']} names no leaders")
        if c["type"] == "measure" and e["verdict"] not in ("none", "too_close", "passing", "failing", "passed", "failed", "failed_tie"):
            bad.append(where + f"a measure can't be {e['verdict']}")
        if c["type"] != "measure" and e["verdict"] in ("passing", "failing", "passed", "failed", "failed_tie"):
            bad.append(where + f"a race can't be {e['verdict']}")
        if e["state"] == "counting" and any(x[1] for x in ch):
            bad.append(where + "counting means no votes yet")
        if e["verdict"] != "none" and e["state"] != "counting" and not any(x[1] for x in ch) and e["verdict"] != "unopposed":
            bad.append(where + "zero votes never names a verdict")
        src = e["sources"]
        if not (isinstance(src, list) and src and all(isinstance(s, list) and len(s) == 2 and isinstance(s[0], str) and s[0]
                                                     and isinstance(s[1], str) and TIME.match(s[1]) for s in src)):
            bad.append(where + "sources must be [[label, YYYY-MM-DDTHH:MM]], at least one")
        if not (isinstance(e["missing"], list) and all(isinstance(m, str) and m for m in e["missing"])):
            bad.append(where + "missing must be a list of labels")
        elif (e["state"] == "partial") != bool(e["missing"]):
            bad.append(where + "partial means some county is missing, and only then")
        tr = e["travis"]
        if tr is not None and not (isinstance(tr, list) and [x[0] for x in tr if isinstance(x, list)] == [x[0] for x in ch if not x[3]][:len(tr)]
                                   and all(isinstance(x, list) and len(x) == 3 and isinstance(x[1], int) and not isinstance(x[1], bool)
                                           and x[1] >= 0 and is_num(x[2]) for x in tr)):
            bad.append(where + "travis must be null or [[name, votes, percent]] in ballot order")
        if not (isinstance(e["canvasser"], str) and e["canvasser"].startswith("the ")):
            bad.append(where + "canvasser must read as the page says it (\"the …\")")
        cv = e["canvass"]
        if not (isinstance(cv, dict) and set(cv) == {"kind", "by", "on", "done"} and cv["kind"] in KINDS
                and all(cv[k] is None or (isinstance(cv[k], str) and DATE.match(cv[k])) for k in ("by", "on", "done"))):
            bad.append(where + "canvass must be {kind, by, on, done} with dates or null")
        else:
            if (e["state"] in ("official", "recount")) != bool(cv["done"]):
                bad.append(where + "official (or recount) exactly when the canvass is done")
            if cv["kind"] == "legislature" and cv["done"] and cv["done"] < "2027-01-12":
                bad.append(where + "the Legislature canvasses after it meets Jan 12, 2027")
            if cv["kind"] == "state" and cv["done"] and not ("2026-11-21" <= cv["done"] <= "2026-12-07"):
                bad.append(where + "the state canvass is Nov 21 – Dec 7")
            if cv["kind"] == "local" and cv["done"] and not ("2026-11-06" <= cv["done"] <= "2026-11-17"):
                bad.append(where + "a local canvass is Nov 6 – 17")
        if not isinstance(e["official_numbers"], bool):
            bad.append(where + "official_numbers must be true or false")
        elif not e["official_numbers"] and e["state"] not in ("official", "recount"):
            bad.append(where + "official_numbers is false only for an official result (W11)")
        if not (isinstance(e["changed"], int) and not isinstance(e["changed"], bool) and 0 <= e["changed"] <= (seq if isinstance(seq, int) else 0)):
            bad.append(where + "changed must be a seq no later than the file's")
        for k in ("corrected", "runoff_on"):
            if not (e[k] is None or (isinstance(e[k], str) and DATE.match(e[k]))):
                bad.append(where + f"{k} must be a date or null")
        if e["note"] not in NOTES:
            bad.append(where + f"note {e['note']!r}")
        if e["who"] not in (None, "district", "area"):
            bad.append(where + f"who {e['who']!r}")
        if not (e["recount"] is None or (isinstance(e["recount"], str) and e["recount"].startswith("https://"))):
            bad.append(where + "recount must be an https link or null")
        if e["needs"] not in (None, "two_thirds") or (e["needs"] and c["type"] != "measure"):
            bad.append(where + "needs is null, or two_thirds on a measure")
        if e["no_call"] not in (None, "two_majorities", "rule_unsettled") or (e["no_call"] and (e["verdict"] != "none" or e["state"] in ("official", "recount", "counting"))):
            bad.append(where + "no_call is null, or a reason on an unofficial result with no verdict")
        if (e["state"] == "recount") != bool(e["recount"]):
            bad.append(where + "recount state exactly when there's a recount link")
    if prev is not None and not bad:
        bad += check_against(obj, prev, rolled)
    return bad


def check_against(obj, prev, rolled=None):
    """obj, published after prev: seq goes up by one when anything changed (and stays when nothing did), and no source's
    posted time goes backwards."""
    bad = []
    same = {k: v for k, v in obj.items() if k != "seq"} == {k: v for k, v in prev.items() if k != "seq"}
    if same and obj["seq"] != prev["seq"]:
        bad.append(f"nothing changed, so seq stays {prev['seq']}")
    if not same and obj["seq"] != prev["seq"] + 1:
        bad.append(f"seq must be {prev['seq'] + 1} (the last published copy's plus one), not {obj['seq']}")
    for cid, e in obj["contests"].items():
        old = prev.get("contests", {}).get(cid)
        if not old:
            continue
        was = dict(map(tuple, old.get("sources", [])))
        for label, t in e["sources"]:
            if label in was and t < was[label] and not e["corrected"] and (label, was[label]) not in (rolled or {}):   # an excluded file's time may go back (#154)
                bad.append(f"{cid}: {label}'s posted time went backwards ({was[label]} → {t}); a correction sets corrected")
    return bad


def main(argv):
    path = pathlib.Path(argv[1]) if len(argv) > 1 and not argv[1].startswith("--") else ROOT / "results.json"
    prev = None
    if "--prev" in argv:
        prev = json.loads(pathlib.Path(argv[argv.index("--prev") + 1]).read_text(encoding="utf-8"))
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        sys.exit(f"results check: can't read {path}: {e}")
    exc = ROOT / "source/results/excluded.json"   # the build's own allowance: an excluded file's time may go back (#154)
    bad = check(obj, answer_key(), prev, excluded_stamps(json.loads(exc.read_text(encoding="utf-8")) if exc.exists() else []))
    if bad:
        sys.exit("results check: " + "; ".join(bad[:20]) + (f" (and {len(bad) - 20} more)" if len(bad) > 20 else ""))
    print(f"results check: {path.name} is sound (seq {obj['seq']}, {len(obj['contests'])} contests)")


if __name__ == "__main__":
    main(sys.argv)
