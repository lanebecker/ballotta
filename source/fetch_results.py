"""Fetches the results sources a script may fetch (docs/plans/2026-10-20-results.md; Lane's answer 7, Task 1 findings 4,
5 and 7) into source/results/raw/, the way Lane's downloads are filed. Run by the Results workflow's read-only job.

    python3 source/fetch_results.py           # every source in source/results_map.json's meta.fetch

  sos          the Texas SOS election night feed (election meta.sos_election), every run
  sos_canvass  its Official Canvass Report PDF, once the feed's ReportList says it's there
  williamson   Williamson County's results page (meta.fetch.williamson, once its Nov 3 page is known)
  hays         Hays County's cumulative results PDFs (meta.fetch.hays: each URL tried; Hays deletes its unofficial
               PDFs later, so every copy is kept)

Travis and Bastrop are never fetched: Clarity refuses cloud servers, and Ballotta doesn't work around that (Lane
downloads them). Each fetch names Ballotta in its User-Agent. A source that fails is reported and skipped; the others
still run. A file already in raw/ (same hash) isn't written again. Exit status 1 only if every source failed.
"""
import base64, json, pathlib, sys, urllib.error, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "source"))
import build_results as B, results_parse as P  # noqa: E402

UA = "Ballotta results (https://ballotta.org)"
SOS = "https://goelect.txelections.civixapps.com/api-ivis-system/api/s3/enr"


def get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        if r.status != 200:
            raise OSError(f"{url}: HTTP {r.status}")
        return r.read()


def keep(res, source, data, name, parse):
    """Parse (so a bad file is never filed), then file under raw/<source>/<posted>-<hash8>/<name>."""
    rep = parse(data)
    d = B.raw_dir(res, source, rep["posted"], data)
    if d.exists():
        return None
    d.mkdir(parents=True)
    (d / name).write_bytes(data)
    return d / name


def fetch_all(meta, res=B.RES, fetch=get):
    """[(source, filed path or None, error or None)] for each fetch tried."""
    out = []
    def one(source, url, name, parse, decode=None):
        try:
            data = fetch(url)
            if decode:
                data = decode(data)
            out.append((source, keep(res, source, data, name, parse), None))
        except Exception as e:   # anything one source's file does (a PDF library's own errors, broken JSON) is that source's error: the others still go (#137)
            out.append((source, None, f"{url}: {type(e).__name__}: {e}"))
    eid = meta["sos_election"]
    zone = meta["sos_time_zone"]
    one("sos", f"{SOS}/election/{eid}", "election.json", lambda d: P.parse_sos(d, zone=zone))
    filed = out[-1][1] or next(iter(sorted((res / "raw/sos").glob("*/election.json"), reverse=True)), None)
    try:
        has_canvass = filed is not None and P.parse_sos(filed.read_bytes(), zone=zone)["canvass_report"]
    except P.BadFile:
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


def main():
    meta = json.loads((ROOT / "source/results_map.json").read_text(encoding="utf-8"))["meta"]
    out = fetch_all(meta)
    for source, path, err in out:
        print(f"{source}: " + (f"filed {path.relative_to(ROOT)}" if path else "error: " + err if err else "nothing new"))
    if out and all(err for _, _, err in out):
        sys.exit("every fetch failed")


if __name__ == "__main__":
    main()
