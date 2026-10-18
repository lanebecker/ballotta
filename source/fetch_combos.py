"""Every combination of district codes in the county's voter-address layer, with how many addresses carry it (#85).

    python3 source/fetch_combos.py        # writes source/data/district_combos.json; then run build_rules.py

build_rules.py reads the result to check that every contest reaches someone and to count who each rule reaches. One
statistics query to the Tax Office's VotingAddresses layer, grouped by every district field and counted: no addresses,
only codes and counts. The county updates the layer as people register, so a rerun gives slightly different counts
(on Oct 18, 2026: 20 more addresses than Oct 13, and some rows newly carrying a Split code; build_rules.py's output
was unchanged). It stops rather than write a partial answer.
"""
import json, pathlib, sys, urllib.parse, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "data/district_combos.json"
LAYER = "https://taxmaps.traviscountytx.gov/arcgis/rest/services/VotingAddresses/VA/MapServer/0/query"
FIELDS = "Precinct,Split,Commissioner,Congressional,JPConstable,Legislative,Senate,Muni,MuniSMD,ISD,ISDSMD,College,MUD,ESD,ESD2,Library,WCID,Temp"


def fetch():
    q = {"where": "1=1", "groupByFieldsForStatistics": FIELDS, "orderByFields": FIELDS, "f": "json",
         "outStatistics": json.dumps([{"statisticType": "count", "onStatisticField": "OBJECTID", "outStatisticFieldName": "n"}])}
    with urllib.request.urlopen(LAYER + "?" + urllib.parse.urlencode(q), timeout=180) as r:
        d = json.load(r)
    if "error" in d: sys.exit(f"the county answered with an error: {d['error']}")
    if d.get("exceededTransferLimit"): sys.exit("the county cut the answer short (exceededTransferLimit): nothing written")
    names = [f["name"] for f in d.get("fields", [])]
    if names != FIELDS.split(",") + ["n"]: sys.exit(f"unexpected fields {names}: nothing written")
    if len(d.get("features", [])) < 1000: sys.exit(f"only {len(d.get('features', []))} combinations (about 1,300 expected): nothing written")
    return d


if __name__ == "__main__":
    d = fetch()
    OUT.write_text(json.dumps(d, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"{len(d['features'])} combinations, {sum(f['attributes']['n'] for f in d['features'])} addresses -> {OUT.relative_to(HERE.parent)}")
