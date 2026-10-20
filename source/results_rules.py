"""The verdict rules for results.json (docs/plans/2026-10-20-results.md, "The rules"). Stdlib only, no clock, no I/O:
each rule is a small function, tested on its own in tests/test_results.py.

Words used here:
  votes    the votes for each choice in ballot order, declared write-ins after: [(name, votes), ...]
  total    the votes cast in the contest: the sum of every choice's votes (write-ins included)
  slack    votes that may still arrive from a county whose file is missing: that county's registered voters in the
           electorate. Every verdict must hold even if all of them go to whoever it would hurt. None = unknown, so
           no verdict at all until the file arrives (the partial rule).
  clear    one choice ahead of another by at least 1 point AND at least 20 votes (Lane's answer 2), after the slack
"""
from fractions import Fraction

POINT, FLOOR = 1, 20                 # the leading test: >= 1 point and >= 20 votes (Lane, Oct 20, answer 2)
MAJ_HIGH, MAJ_LOW = 52, 48           # majority contests: over 52% leads, under 48% heads to a runoff, between: may
MEASURE_PASS, MEASURE_FAIL = Fraction(101, 2), Fraction(99, 2)   # 50.5% / 49.5%
LEGISLATURE_TIES = {"c006", "c007", "c008", "c009", "c010"}      # Governor, Lt. Gov., AG, Comptroller, Land (§2.002(h))


def pct(v, total):
    """A choice's percent of the votes cast, to 2 places; 0 when nothing has been cast."""
    return round(100 * v / total, 2) if total else 0


def clear(a, b, total, slack=0):
    """a ahead of b by the leading test, even if every outstanding vote (slack) went to b."""
    if slack is None:
        return False
    gap, cast = a - b - slack, total + slack
    return gap >= FLOOR and cast > 0 and Fraction(100 * gap, cast) >= POINT


def ranked(votes):
    """Choices from most votes to fewest; ties keep ballot order (so a tie is never broken by who is listed first:
    every caller checks the tie itself)."""
    return sorted(votes, key=lambda nv: -nv[1])


def is_unopposed(candidates, seats, write_ins):
    """No more named candidates than seats and no declared write-in (c053 County Clerk has one, so it isn't)."""
    return len(candidates) <= seats and not write_ins


HALF, TWO_THIRDS = Fraction(1, 2), Fraction(2, 3)
NEEDS = {None: HALF, "two_thirds": TWO_THIRDS}       # a measure's threshold; "unsure": a verdict only where both agree


def unofficial(kind, votes, seats=1, majority=False, slack=0, write_ins=(), cid=None, needs=None):
    """(verdict, leaders, runoff) before the canvass. kind: 'candidate' or 'measure'. write_ins: the declared
    write-ins' names (they are in votes, after the ballot's choices). needs: a measure's threshold (None: more than
    half; "two_thirds": road bonds, Tex. Const. art. III §52(b); "unsure": not yet settled, so a verdict only where
    a majority and two-thirds agree)."""
    total = sum(v for _, v in votes)
    if kind == "measure":
        if needs == "unsure":
            a, b = measure(votes, total, slack, HALF), measure(votes, total, slack, TWO_THIRDS)
            return (a if a == b else "none"), [], []      # no call (W69), never "too close" when it isn't
        return measure(votes, total, slack, NEEDS[needs]), [], []
    names = [n for n, _ in votes if n not in write_ins]
    if is_unopposed(names, seats, write_ins):
        return "unopposed", names, []
    if total == 0 or slack is None:
        return "none", [], []
    if majority == "unsure":                         # the rule isn't settled: a verdict only where both readings agree
        a = unofficial(kind, votes, seats, False, slack, write_ins, cid)
        b = unofficial(kind, votes, seats, True, slack, write_ins, cid)
        return a if a == b else ("none", [], [])
    r = ranked(votes)
    if majority and seats == 1 and len(votes) >= 3:
        return majority_zone(r, total, slack)
    if len(r) <= seats:                                   # fewer choices than seats, a declared write-in among them
        return "leading", [n for n, _ in r if _], []
    # plurality, or a two-choice majority contest (with two, only an exact tie means a runoff): the leading test
    # between the Nth and the (N+1)th
    nth, nxt = r[seats - 1][1], r[seats][1]
    if clear(nth, nxt, total, slack):
        return "leading", [n for n, _ in r[:seats]], []
    return "too_close", [], []


def measure(votes, total, slack=0, need=Fraction(1, 2)):
    """Symmetric around the threshold: passing when FOR's share is at least half a point above it AND at least 10
    voters would have to switch to undo it; failing likewise below; else too close. At one half this is exactly
    FOR >= 50.5% and 20 votes ahead (Lane's answer 2). The slack goes against whichever way it leans."""
    if total == 0 or slack is None:
        return "none"
    f = dict(votes)["FOR"]
    cast = total + slack
    if Fraction(100 * f, cast) - 100 * need >= Fraction(1, 2) and f - need * cast >= FLOOR // 2:
        return "passing"
    if 100 * need - Fraction(100 * (f + slack), cast) >= Fraction(1, 2) and need * cast - (f + slack) >= FLOOR // 2:
        return "failing"
    return "too_close"


def majority_zone(r, total, slack=0):
    """A majority contest with three or more choices (declared write-ins count). The top choice's share, at its
    worst (every outstanding vote elsewhere) and best (every outstanding vote to it):
      worst over 52%                -> leading
      best under 48%                -> headed to a runoff; the top two named only when second clears third
      otherwise                     -> may go to a runoff"""
    top = r[0][1]
    cast = total + slack
    worst, best = Fraction(100 * top, cast), Fraction(100 * (top + slack), cast)
    if worst > MAJ_HIGH and clear(top, r[1][1], total, slack):
        return "leading", [r[0][0]], []
    if best < MAJ_LOW:
        pair = [r[0][0], r[1][0]] if clear(r[1][1], r[2][1], total, slack) else []
        return "runoff", [], pair
    return "may_runoff", [], []


def official(kind, votes, seats=1, majority=False, write_ins=(), cid=None, needs=None):
    """(verdict, leaders, runoff) once canvassed. Ties: offices -> state law decides (§2.002); c006-c010 -> the
    Legislature (§2.002(h)); a two-way majority contest -> runoff (§2.023(a)); a tie for the second runoff spot ->
    recount decides (§2.023(c)); measures -> fail on a tie."""
    total = sum(v for _, v in votes)
    if kind == "measure":
        f, a = dict(votes)["FOR"], dict(votes)["AGAINST"]
        half = ("passed" if f > a else "failed_tie" if f == a else "failed")
        thirds = "passed" if 3 * f >= 2 * total and total else "failed"          # at least two-thirds of the votes cast
        if needs == "unsure":
            if (half == "passed") != (thirds == "passed"):
                raise ValueError("canvassed, and a majority and two-thirds disagree: settle this measure's threshold")
            return half, [], []
        return (thirds if needs == "two_thirds" else half), [], []
    names = [n for n, _ in votes if n not in write_ins]
    if is_unopposed(names, seats, write_ins):
        return "elected", names, []
    if majority == "unsure":
        a = official(kind, votes, seats, False, write_ins, cid)
        b = official(kind, votes, seats, True, write_ins, cid)
        if a != b:
            raise ValueError("canvassed, and plurality and majority disagree: settle this contest's rule")
        return a
    r = ranked(votes)
    if majority and seats == 1:
        if len(r) == 2 and r[0][1] == r[1][1]:
            return "tied_runoff", [], []
        if total and 2 * r[0][1] > total:
            return "won", [r[0][0]], []
        if len(r) >= 3 and r[1][1] == r[2][1]:
            return "tied_second", [], []
        return "runoff", [], [r[0][0], r[1][0]]
    if len(r) <= seats:
        return "won", [n for n, v in r if v], []
    if r[seats - 1][1] == r[seats][1]:
        return ("tied_legislature" if cid in LEGISLATURE_TIES else "tied"), [], []
    return "won", [n for n, _ in r[:seats]], []


def annex_note(district_passed, area_passed):
    """One outcome line for an annexation voted separately by the district and the area to be added (W33/W38)."""
    if district_passed and area_passed:
        return "annex_both"
    if area_passed:
        return "annex_district_rejected"
    if district_passed:
        return "annex_area_rejected"
    return "annex_both_rejected"
