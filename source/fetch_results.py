"""Fetches the results sources a script may fetch (docs/plans/2026-10-20-results.md; Lane's answer 7, Task 1 findings 4,
5 and 7) into source/results/raw/, the way Lane's downloads are filed. Run by the Results workflow's read-only job.

    python3 source/fetch_results.py [--report FILE]   # every source in source/results_map.json's meta.fetch; the
                                                      # report (errors, each source's newest file) goes in the PR

  sos          the Texas SOS election night feed (election meta.sos_election), every run
  sos_canvass  its Official Canvass Report PDF, once the feed's ReportList says it's there
  williamson   Williamson County's results page (meta.fetch.williamson, once its Nov 3 page is known)
  hays         Hays County's cumulative results PDFs (meta.fetch.hays: each URL tried; Hays deletes its unofficial
               PDFs later, so every copy is kept)

Travis and Bastrop are never fetched: Clarity refuses cloud servers, and Ballotta doesn't work around that (Lane
downloads them). Each fetch names Ballotta in its User-Agent and is tried three times. A source that fails is reported
(in the pull request, through --report) and skipped; the others still run, and the run never fails on a fetch, so
Lane's uploads are always built (the deep audit, #161). A file already in raw/ (same hash) isn't written again.
"""
import base64, datetime as dt, email.utils, json, pathlib, sys, time, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "source"))
import build_results as B, results_parse as P  # noqa: E402

UA = "Ballotta results (https://ballotta.org)"
SOS = "https://goelect.txelections.civixapps.com/api-ivis-system/api/s3/enr"


class Body(bytes):
    """A response's bytes, with the server's Date header (UTC), which settles how the SOS feed's times read."""
    date = None


def get(url, timeout=60, tries=3, wait=(5, 20)):
    """The response body; a timeout, a dropped connection or a 5xx/429 is tried again (5 s, then 20 s), a 404 isn't."""
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                if r.status != 200:
                    raise OSError(f"{url}: HTTP {r.status}")
                body = Body(r.read())
                when = r.headers.get("Date")
                body.date = email.utils.parsedate_to_datetime(when) if when else None
                return body
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == tries - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if i == tries - 1:
                raise
        time.sleep(wait[min(i, len(wait) - 1)])


def keep(res, source, data, name, parse, election=None):
    """Parse (so a bad file is never filed), then file under raw/<source>/<posted>-<hash8>/<name>. Another election's
    file is refused (a mistyped meta.sos_election, or last year's Hays address)."""
    rep = parse(data)
    if election and rep.get("election") not in (None, election):
        raise P.BadFile(f"this is the file for the {rep['election']} election, not {election}")
    sent = getattr(data, "date", None)
    if source == "sos" and sent and dt.datetime.fromisoformat(rep["posted"]).replace(tzinfo=P.AUSTIN) > sent + dt.timedelta(minutes=5):
        # read in meta.sos_time_zone, the feed's last update is after the server's own clock: that zone is wrong (the
        # feed writes UTC, say), and every time filed from it would be hours off (Task 1 finding 10; #161)
        raise P.BadFile(f"its LastUpdatedTime reads as {rep['posted']} Austin time, after the server's clock "
                        f"({sent.astimezone(P.AUSTIN):%Y-%m-%dT%H:%M}): set meta.sos_time_zone in results_map.json to the zone it's written in")
    d = B.raw_dir(res, source, rep["posted"], data)
    if d.exists():
        return None
    d.mkdir(parents=True)
    (d / name).write_bytes(data)
    return d / name


def fetch_all(meta, res=B.RES, fetch=get, election=None):
    """[(source, filed path or None, error or None)] for each fetch tried."""
    out = []
    def one(source, url, name, parse, decode=None):
        try:
            data = fetch(url)
            if decode:
                data = decode(data)
            out.append((source, keep(res, source, data, name, parse, election), None))
        except Exception as e:   # anything one source's file does (a PDF library's own errors, broken JSON) is that source's error: the others still go (#137)
            out.append((source, None, f"{url}: {type(e).__name__}: {e}"))
    eid = meta["sos_election"]
    zone = meta["sos_time_zone"]
    one("sos", f"{SOS}/election/{eid}", "election.json", lambda d: P.parse_sos(d, zone=zone))
    filed = out[-1][1] or next(iter(sorted((res / "raw/sos").glob("*/election.json"), reverse=True)), None)
    try:
        has_canvass = filed is not None and P.parse_sos(filed.read_bytes(), zone=zone)["canvass_report"]
    except Exception:   # an old filed feed this parser can't read never stops the run (#137)
        has_canvass = False
    if has_canvass:
        one("sos_canvass", f"{SOS}/electionReports/{eid}/OfficialCanvassReport/pdf", "official-canvass.pdf",
            P.parse_sos_canvass, decode=lambda b: base64.b64decode(json.loads(b)["upload"]))
    wc = (meta.get("fetch") or {}).get("williamson")
    if wc:
        one("williamson", wc, "results.html", P.parse_williamson)
    for url in (meta.get("fetch") or {}).get("hays") or []:
        one("hays", url, url.rsplit("/", 1)[-1].replace("%20", "-") or "results.pdf", P.parse_hays)
    return out


def report(out, res=B.RES, now=None):
    """The lines the pull request shows under "Sources": each fetch error, and how old each source's newest file is
    (a county that stopped posting, or an upload Lane forgot, shows here)."""
    now = (now or dt.datetime.now(P.AUSTIN)).astimezone(P.AUSTIN)
    lines = [f"- {source}: could not fetch: {err}" for source, _, err in out if err]
    for source in ("travis", "bastrop", "williamson", "hays", "sos", "sos_canvass"):
        try:
            rep = B.latest(res, source, {}, B.POLLS_CLOSE, [], B.ELECTION)
        except Exception as e:   # the build says what's wrong; this line is only a summary
            lines.append(f"- {P.LABELS[source]}: newest file unreadable ({e})"); continue
        if rep is None:
            lines.append(f"- {P.LABELS[source]}: no file yet"); continue
        hours = (now - dt.datetime.fromisoformat(rep["posted"]).replace(tzinfo=P.AUSTIN)).total_seconds() / 3600
        lines.append(f"- {P.LABELS[source]}: newest file posted {rep['posted'].replace('T', ' ')} ({hours:.0f} h before this run)")
    return lines


def main(argv):
    meta = json.loads((ROOT / "source/results_map.json").read_text(encoding="utf-8"))["meta"]
    out = fetch_all(meta, election=B.ELECTION)
    for source, path, err in out:
        print(f"{source}: " + (f"filed {path.relative_to(ROOT)}" if path else "error: " + err if err else "nothing new"))
    if "--report" in argv:
        pathlib.Path(argv[argv.index("--report") + 1]).write_text(json.dumps(report(out)), encoding="utf-8")
    # never a failed step: Lane's uploads are built whatever the network did


if __name__ == "__main__":
    main(sys.argv)
