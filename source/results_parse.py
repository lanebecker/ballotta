"""Parsers for each results source (docs/plans/2026-10-20-results.md, Task 3). Each turns one raw file, exactly as
fetched or downloaded, into the same report:

    {"source": "travis" | "bastrop" | "williamson" | "hays" | "sos" | "sos_canvass",
     "label": "Travis County" | ... | "Texas Secretary of State",
     "posted": "YYYY-MM-DDTHH:MM" (Austin time: when the source says it posted these numbers),
     "contests": {source's key: {"name": as the source prints it, "vote_for": int,
                                 "choices": [[name as printed, votes]], "registered": int or None}}}

A file that doesn't add up (a contest's choices against its own total, a page's two copies of a number) is refused
with BadFile, never half-read. Names are matched later, through source/results_map.json, after norm().

Stdlib, except the two PDF parsers, which import pdfplumber (pinned in requirements.txt) only when called.
"""
import datetime as dt, html as htmlmod, io, json, base64, re, zipfile
from zoneinfo import ZoneInfo

AUSTIN = ZoneInfo("America/Chicago")
LABELS = {"travis": "Travis County", "bastrop": "Bastrop County", "williamson": "Williamson County", "hays": "Hays County",
          "sos": "Texas Secretary of State", "sos_canvass": "Texas Secretary of State",
          "caldwell": "Caldwell County", "lee": "Lee County"}       # ACC only; no file ever comes from them (Task 1 finding 11)
PARTIES = {"REP", "DEM", "LIB", "GRN", "IND", "NON", "W", "WI", "W-I"}


class BadFile(ValueError):
    """A raw file that can't be trusted: refused whole."""


def norm(s):
    """The form names are matched in: capitals, straight quotes, single spaces, no incumbent mark "(I)"."""
    s = s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    s = re.sub(r"\s*\(I\)\s*$", "", s.strip())
    return re.sub(r"\s+", " ", s).upper().strip()


def same_person(a, b):
    """Two printings of one name: equal once normalized, or one's words all among the other's (the canvass report
    prints "JESUS GARCIA, JR" for the feed's "JESUS TOMAS GARCIA, JR"). Callers require a unique match."""
    ta, tb = set(re.findall(r"[A-Z0-9'\"-]+", norm(a))), set(re.findall(r"[A-Z0-9'\"-]+", norm(b)))
    return norm(a) == norm(b) or (bool(ta) and bool(tb) and (ta <= tb or tb <= ta))


def match(name, candidates):
    """The one candidate that name prints, or None when none or several do."""
    exact = [c for c in candidates if norm(c) == norm(name)]
    if len(exact) == 1:
        return exact[0]
    loose = [c for c in candidates if same_person(name, c)]
    return loose[0] if len(loose) == 1 else None


def stamp(t):
    """An aware datetime, as Austin time to the minute."""
    return t.astimezone(AUSTIN).strftime("%Y-%m-%dT%H:%M")


def local(naive):
    """A time printed without a zone, read as Austin time."""
    return stamp(naive.replace(tzinfo=AUSTIN))


def num(s):
    return int(s.replace(",", ""))


def check_sum(where, choices, total):
    got = sum(v for _, v in choices)
    if got != total:
        raise BadFile(f"{where}: choices add up to {got:,}, but the file says {total:,}")


# ---------------------------------------------------------------- Clarity Detail XML (Travis, Bastrop: Lane downloads)
CLARITY_COUNTIES = {"Travis": "travis", "Bastrop": "bastrop", "Williamson": "williamson"}


def parse_clarity(data):
    """data: the detailxml.zip Lane downloaded (or the detail.xml inside it), as bytes. Its <Region> names the county,
    so a file in the wrong inbox folder is caught. Contests are keyed by Clarity's key (names can repeat)."""
    import xml.etree.ElementTree as ET
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml = [n for n in z.namelist() if n.lower().endswith(".xml")]
            if len(xml) != 1:
                raise BadFile(f"the zip holds {len(xml)} XML files, not one")
            data = z.read(xml[0])
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise BadFile(f"not XML: {e}")
    region = (root.findtext("Region") or "").strip()
    if region not in CLARITY_COUNTIES:
        raise BadFile(f"region {region!r} is not a county Ballotta reads")
    m = re.fullmatch(r"(\d+/\d+/\d{4} \d+:\d{2}:\d{2} [AP]M) (CST|CDT|UTC|GMT)", (root.findtext("Timestamp") or "").strip())
    if not m:
        raise BadFile(f"timestamp {root.findtext('Timestamp')!r} isn't one Ballotta can read")
    t = dt.datetime.strptime(m.group(1), "%m/%d/%Y %I:%M:%S %p")
    posted = local(t) if m.group(2) in ("CST", "CDT") else stamp(t.replace(tzinfo=dt.timezone.utc))
    reg = {p.get("name"): int(p.get("totalVoters")) for p in root.find("VoterTurnout").find("Precincts")}
    contests = {}
    for c in root.findall("Contest"):
        key, choices, precincts = c.get("key"), [], set()
        for ch in c.findall("Choice"):
            total = int(ch.get("totalVotes"))
            by_type = 0
            for vt in ch.findall("VoteType"):
                by_type += int(vt.get("votes"))
                ps = vt.findall("Precinct")
                if ps and sum(int(p.get("votes")) for p in ps) != int(vt.get("votes")):
                    raise BadFile(f"{c.get('text')}: {ch.get('text')}'s {vt.get('name')} precincts don't add up")
                precincts.update(p.get("name") for p in ps)
            if ch.findall("VoteType") and by_type != total:
                raise BadFile(f"{c.get('text')}: {ch.get('text')}'s vote types add up to {by_type:,}, not {total:,}")
            choices.append([ch.get("text"), total])
        if key in contests:
            raise BadFile(f"contest key {key} appears twice")
        contests[key] = {"name": c.get("text"), "vote_for": int(c.get("voteFor") or 1), "choices": choices,
                         "registered": sum(reg.get(p, 0) for p in precincts)}
    src = CLARITY_COUNTIES[region]
    return {"source": src, "label": LABELS[src], "posted": posted, "contests": contests}


# ---------------------------------------------------------------- Texas SOS election night feed (by script)
def sos_section(feed, k):
    v = feed.get(k)
    if not isinstance(v, str) or k == "Version":
        return v
    try:
        return json.loads(base64.b64decode(v).decode("utf-8"))
    except ValueError as e:
        raise BadFile(f"SOS section {k} isn't base64 JSON: {e}")


def parse_sos(data, zone="America/Chicago"):
    """data: the body of /s3/enr/election/{id}, as fetched. zone: how LastUpdatedTime reads (Task 1 finding 10:
    settled on election night; source/results_map.json's meta.sos_time_zone). Races keyed by the feed's race id."""
    try:
        feed = json.loads(data)
    except ValueError as e:
        raise BadFile(f"not JSON: {e}")
    home = sos_section(feed, "Home") or {}
    try:
        t = dt.datetime.strptime(home["LastUpdatedTime"], "%b %d, %Y %H:%M:%S")
    except (KeyError, TypeError, ValueError):
        raise BadFile(f"LastUpdatedTime {home.get('LastUpdatedTime')!r} isn't one Ballotta can read")
    posted = stamp(t.replace(tzinfo=ZoneInfo(zone)))
    contests = {}
    for k in ("Federal", "StateWide", "StateWideQ", "Districted"):
        sec = sos_section(feed, k)
        for r in ((sec or {}).get("Races") or []) if isinstance(sec, dict) else []:
            choices = [[c["N"], int(c.get("V") or 0)] for c in r.get("Candidates", [])]
            if "T" in r and r["T"] is not None:
                check_sum(f"SOS race {r.get('N')}", choices, int(r["T"]))
            contests[str(r["id"])] = {"name": r["N"], "vote_for": 1, "choices": choices, "registered": None,
                                      "write_ins": [c["N"] for c in r.get("Candidates", []) if c.get("P") == "W"]}
    if not contests:
        raise BadFile("no races in the SOS feed")
    reports = sos_section(feed, "ReportList") or {}
    canvass = bool((reports.get("OfficialCanvassReport") or {}).get("view"))
    return {"source": "sos", "label": LABELS["sos"], "posted": posted, "contests": contests, "canvass_report": canvass}


# ---------------------------------------------------------------- Texas SOS Official Canvass Report PDF (by script)
SOS_OFFICE = re.compile(r"^(.*?)\s+([\d,]+)\s+[\d.]+ %$")
SOS_CAND = re.compile(r"^(.*?)\s+(?:(" + "|".join(sorted(PARTIES, key=len, reverse=True)) + r")\s+)?([\d,]+)\s+[\d.]+ %$")
SOS_TOTAL = re.compile(r"^Total\s+([\d,]+)$")
SOS_FOOT = re.compile(r"^(\d{2}/\d{2}/\d{4} \d{2}:\d{2} [AP]M)$")


def parse_sos_canvass(data):
    """data: the PDF bytes of /electionReports/{id}/OfficialCanvassReport/pdf (decoded from its {"upload": …}).
    Offices keyed by norm(office name), which equals norm() of the feed's race name."""
    import pdfplumber
    lines, foot = [], None
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for p in pdf.pages:
            for ln in (p.extract_text() or "").splitlines():
                ln = ln.strip()
                if SOS_FOOT.match(ln):
                    foot = foot or SOS_FOOT.match(ln).group(1)
                lines.append(ln)
    if not lines or "Official Canvass Report" not in lines[:4]:
        raise BadFile("not an SOS Official Canvass Report")
    contests, office, choices, naming = {}, None, [], False
    for ln in lines:
        if office is None:
            m = SOS_OFFICE.match(ln)
            if m and not SOS_CAND.match(ln.replace(" %", "% ")) and not ln.startswith("Total"):
                office, choices, naming = m.group(1), [], True
            continue
        mt = SOS_TOTAL.match(ln)
        if mt:
            check_sum(f"canvass {office}", choices, num(mt.group(1)))
            key = norm(office)
            if key in contests:
                raise BadFile(f"office {office} appears twice")
            contests[key] = {"name": office, "vote_for": 1, "choices": choices, "registered": None}
            office = None
            continue
        mc = SOS_CAND.match(ln)
        if mc:
            choices.append([mc.group(1), num(mc.group(3))]); naming = False
        elif naming:
            office += " " + ln                                   # a long office name wraps onto the next line
        elif choices and not re.search(r"\d", ln):              # ...and so does a long candidate name
            choices[-1][0] += ("" if choices[-1][0].endswith("-") else " ") + ln
    if office is not None:
        raise BadFile(f"office {office} has no Total line")
    if not foot:
        raise BadFile("no report time at the foot of the pages")
    posted = local(dt.datetime.strptime(foot, "%m/%d/%Y %I:%M %p"))
    return {"source": "sos_canvass", "label": LABELS["sos_canvass"], "posted": posted, "contests": contests}


# ---------------------------------------------------------------- Williamson County results page (by script)
WC_HEAD = re.compile(r'id="raceHeading_(\d+)" class="sr-only">Contest: (.*?), VOTE FOR (\d+), Precincts Reported')
WC_CELL = re.compile(r'<td data-race="(\d+)" data-contestant="(\d+)" data-(candidate|votes)="true" class="content-data">(.*?)</td>', re.S)
WC_PIE = re.compile(r'data-race-id="(\d+)" class="pie-results">.*?(\[\[.*?\]\]);', re.S)
WC_TIME = re.compile(r'id="lblLastPublishedDateTime" class="updated-at">([^<]+)<')


def parse_williamson(data):
    """data: the livevoterturnout.com results page (one server-rendered HTML file). The race-wide table is read; the
    pie chart's copy of each total (in the same page) must agree, or the file is refused."""
    h = data.decode("utf-8", errors="replace")
    mt = WC_TIME.search(h)
    if not mt:
        raise BadFile("no 'Website Updated' time")
    posted = local(dt.datetime.strptime(mt.group(1).strip(), "%m/%d/%Y %I:%M:%S %p"))
    heads = {rid: (htmlmod.unescape(name), int(vf)) for rid, name, vf in WC_HEAD.findall(h)}
    if not heads:
        raise BadFile("no contests on the page")
    rows = {}
    for rid, k, kind, inner in WC_CELL.findall(h):
        if rid in heads:
            text = htmlmod.unescape(re.sub(r"<[^>]+>", " ", inner))
            text = re.sub(r"\s+", " ", text).strip()
            rows.setdefault(rid, {}).setdefault(int(k), {})[kind] = text
    pies = {rid: json.loads(arr.replace("'", '"')) for rid, arr in WC_PIE.findall(h)}
    contests = {}
    for rid, (name, vf) in heads.items():
        r = rows.get(rid, {})
        choices = []
        for k in sorted(r):
            nm = r[k].get("candidate", "")
            nm = nm[: len(nm) // 2].strip() if len(nm) % 2 == 1 and nm[: len(nm) // 2] == nm[len(nm) // 2 + 1:] else nm   # printed twice (visible + screen reader)
            choices.append([nm, num(r[k].get("votes", "0") or "0")])
        if rid in pies and [[str(x[0]), int(x[-1])] for x in pies[rid]] != choices:
            raise BadFile(f"{name}: the table and the chart disagree")
        contests[rid] = {"name": name, "vote_for": vf, "choices": choices, "registered": None}
    return {"source": "williamson", "label": LABELS["williamson"], "posted": posted, "contests": contests}


# ---------------------------------------------------------------- Hays County cumulative results PDF (by script)
HAYS_ROW = re.compile(r"^(.*?)\s+(?:[\d,]+\s+[\d.]+%\s+){3}([\d,]+)\s+[\d.]+%$")
HAYS_CAST = re.compile(r"^Cast Votes:\s+(?:[\d,]+\s+[\d.]+%\s+){3}([\d,]+)\s+[\d.]+%$")
HAYS_HEAD = re.compile(r"^(Cumulative Results Report|Registered Voters|General Election|Precincts Reporting|\d+ of \d+ = |"
                       r"\d+/\d+/\d{4}$|Run Time|Run Date|Nov\. |[A-Z][a-z]+\.? \d+, \d{4} )")


def parse_hays(data):
    """data: Hays's 'Cumulative Results' PDF. A contest is the title above its 'Choice Party' header, then one row per
    choice (its last number pair is the total), closed by 'Cast Votes:', which the rows must add up to."""
    import pdfplumber
    lines, run_date, run_time = [], None, None
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for p in pdf.pages:
            for ln in (p.extract_text() or "").splitlines():
                ln = ln.strip()
                m = re.match(r"^Run Time (\d+:\d{2} [AP]M)", ln) or None
                if m: run_time = run_time or m.group(1)
                m = re.match(r"^Run Date (\d+/\d+/\d{4})", ln)
                if m: run_date = run_date or m.group(1)
                lines.append(ln)
    if not lines or not lines[0].startswith("Cumulative Results Report") or "Hays County" not in lines[0]:
        raise BadFile("not a Hays County cumulative results report")
    if not (run_date and run_time):
        raise BadFile("no Run Date and Run Time")
    posted = local(dt.datetime.strptime(run_date + " " + run_time, "%m/%d/%Y %I:%M %p"))
    contests, title, cur, choices = {}, [], None, []
    for ln in lines:
        if ln.startswith("Choice Party"):
            cur, choices = " ".join(title).strip(), []
            title = []
            continue
        if cur is None:
            if not HAYS_HEAD.match(ln) and not ln.startswith(("Undervotes:", "Overvotes:", "Page ")):
                title.append(ln)
            continue
        mc = HAYS_CAST.match(ln)
        if mc:
            check_sum(f"Hays {cur}", choices, num(mc.group(1)))
            key = norm(cur)
            if key in contests:
                raise BadFile(f"contest {cur} appears twice")
            contests[key] = {"name": cur, "vote_for": 1, "choices": choices, "registered": None}
            cur, title = None, []
            continue
        mr = HAYS_ROW.match(ln)
        if mr:
            nm = re.sub(r"\s+(" + "|".join(PARTIES) + r")$", "", mr.group(1))
            choices.append([nm, num(mr.group(2))])
    if cur is not None:
        raise BadFile(f"contest {cur} has no Cast Votes line")
    return {"source": "hays", "label": LABELS["hays"], "posted": posted, "contests": contests,
            "official": "Official Results" in lines[0]}


PARSERS = {"clarity": parse_clarity, "sos": parse_sos, "sos_canvass": parse_sos_canvass, "williamson": parse_williamson,
           "hays": parse_hays}
