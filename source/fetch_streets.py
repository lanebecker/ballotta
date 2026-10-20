"""The street layer under the vote-center map (Lane, Oct 19): freeways, highways, major streets and water, from the
U.S. Census Bureau's TIGER/Line 2024 shapefiles (public domain), simplified for a map about 560 px across.

    python3 source/fetch_streets.py              # downloads the shapefiles, writes source/data/streets.json
    python3 source/fetch_streets.py --raw DIR    # the same from zips already in DIR (named as the Census names them)
    python3 source/fetch_streets.py --out FILE   # writes FILE instead (to compare a rerun with the committed file)

Only this script needs pyshp and shapely (requirements.txt); the site build and CI read the committed JSON. The same
files and the same shapely (GEOS) give the same bytes. It stops rather than write a partial or oversized answer.

Format of streets.json (read by the page's streetLayer(), template-travis.html):
  {"v": 1, "q": 10000,
   "fwy": [line, …], "hwy": [line, …], "art": [line, …], "water": [ring, …],
   "tags": [[label, x, y], …], "order": [label, …]}
  line / ring: [x0, y0, dx1, dy1, dx2, dy2, …] in 1/10000 degree: x = round(longitude * 10000), y = round(latitude *
  10000); each later point is the one before plus (dx, dy). A ring is a water body's outline (islands not cut out).
  tags: places along each named highway, about 3 km apart, where the page may put that highway's label.
  order: the highway labels, most useful first: the page places them in this order, so I-35 wins a crowded corner.
"""
import collections, io, json, pathlib, re, sys, urllib.request, zipfile

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "data/streets.json"
TIGER = "https://www2.census.gov/geo/tiger/TIGER2024/"
Q = 10000
# Every map view a Travis County address can produce (measured Oct 19 over a 41 x 41 grid of the county's bounding box,
# both voting periods: lon -98.624 … -96.924, lat 29.661 … 30.985), with a margin.
VIEW = (-98.70, 29.60, -96.85, 31.05)
# Major streets: the county and its two neighbours' streets near the county, where close-in views (0.12° across) reach.
NEAR = (-98.30, 29.90, -97.25, 30.75)
ROAD_COUNTIES = ("48453", "48491", "48209")                       # Travis, Williamson, Hays
WATER_COUNTIES = ("48453", "48491", "48209", "48021", "48053", "48031", "48055", "48299", "48287", "48091", "48187", "48149")
# Travis, Williamson, Hays, Bastrop, Burnet, Blanco, Caldwell, Llano, Lee, Comal, Guadalupe, Fayette
LONGEST = 160                                                     # the longest-running named streets near the county …
ALSO = ("E Oltorf St", "Oltorf St W", "W Koenig Ln", "W 38th St", "E 38th St", "W 45th St", "E 45th St",
        "W Cesar Chavez St", "E Cesar Chavez St", "Barton Springs Rd", "E Riverside Dr", "W Riverside Dr", "Enfield Rd",
        "E Martin Luther King Jr Blvd", "W Martin Luther King Jr Blvd", "E 7th St", "E 11th St", "E 12th St",
        "Manor Rd", "Springdale Rd", "Montopolis Dr", "Duval St", "W Anderson Ln", "E Rundberg Ln", "W Rundberg Ln",
        "E Stassney Ln", "W Stassney Ln", "S Congress Ave", "Congress Ave", "N Lamar Blvd")   # … and these in town
TOL = 0.00012                    # simplification, in degrees: about half a pixel at the usual 0.12° view
MIN_LEN = 0.002                  # pieces shorter than this (about 200 m) are dropped
MIN_WATER = 150000               # square metres: in Travis County, lakes and the river, not ponds;
MIN_WATER_AWAY = 1000000          # beyond it, where only widened views reach, the big lakes only
WATER_TOL = 0.00025              # lake outlines: about one pixel at the usual view
TAGS = [("I-35", r"^(N |S )?I- ?35\b"), ("MoPac", r"Mo-? ?[Pp]ac|^State Loop 1$"), ("183", r"US Hwy 183|^Research Blvd|^S Hwy 183"),
        ("290", r"US Hwy 290|^W Hwy 290"), ("71", r"State Hwy 71|^Bastrop Hwy|^Hwy 71|^W Hwy 71"), ("Ben White", r"Ben White Blvd"),
        ("45", r"^State Hwy 45\b"), ("130", r"^State Hwy 130\b"), ("360", r"Capital of Texas Hwy|Loop 360"),
        ("Lamar", r"^(N|S) Lamar Blvd$"), ("Congress", r"Congress Ave")]
TAG_EVERY = 0.03                 # degrees between a highway's tag places
MAX_BYTES = 180_000


def need():
    try:
        import shapefile, shapely  # noqa: F401
    except ImportError:
        sys.exit("needs pyshp and shapely: pip install -r requirements.txt")


def zips(raw):
    names = (["PRISECROADS/tl_2024_48_prisecroads.zip"] + [f"ROADS/tl_2024_{c}_roads.zip" for c in ROAD_COUNTIES]
             + [f"AREAWATER/tl_2024_{c}_areawater.zip" for c in WATER_COUNTIES])
    out = {}
    for n in names:
        base = n.split("/")[1]
        if raw:
            p = pathlib.Path(raw) / base
            if not p.is_file(): sys.exit(f"{p} is missing: nothing written")
            out[base] = p.read_bytes()
        else:
            with urllib.request.urlopen(TIGER + n, timeout=300) as r:
                out[base] = r.read()
        zipfile.ZipFile(io.BytesIO(out[base])).testzip()          # a cut-off download stops here
    return out


def records(data, base):
    import shapefile
    r = shapefile.Reader(**{k: io.BytesIO(zipfile.ZipFile(io.BytesIO(data[base])).read(base[:-4] + "." + k))
                                      for k in ("shp", "shx", "dbf")})
    for sr in r.iterShapeRecords():
        yield sr.record.as_dict(), sr.shape


def lines_of(g):
    if g.is_empty: return []
    if g.geom_type == "LineString": return [g]
    return [x for part in getattr(g, "geoms", []) for x in lines_of(part)]


def polygons_of(g):
    if g.is_empty: return []
    if g.geom_type == "Polygon": return [g]
    return [x for part in getattr(g, "geoms", []) for x in polygons_of(part)]


def merged(segments, box):
    from shapely.geometry import LineString
    from shapely.ops import linemerge, unary_union
    if not segments: return []
    g = linemerge(unary_union([LineString(s) for s in segments if len(s) > 1]).intersection(box))
    return [l.simplify(TOL) for l in lines_of(g) if l.length >= MIN_LEN]


def encode(coords):
    """[(lon, lat), …] -> [x0, y0, dx, dy, …] in 1/Q degree, dropping points that round onto the one before."""
    pts = [(round(x * Q), round(y * Q)) for x, y in coords]
    out = list(pts[0])
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if (x1, y1) != (x0, y0): out += [x1 - x0, y1 - y0]
    return out if len(out) >= 4 else None


def layer(geoms):
    enc = [e for e in (encode(list(g.coords)) for g in geoms) if e]
    return sorted(enc, key=lambda a: (a[0], a[1], len(a), a))   # a fixed order: the same input gives the same bytes


def build(data):
    from shapely.geometry import LineString, Polygon, box
    from shapely.ops import unary_union
    view, near = box(*VIEW), box(*NEAR)
    tiers, named = collections.defaultdict(list), collections.defaultdict(list)
    for rec, sh in records(data, "tl_2024_48_prisecroads.zip"):
        if sh.points and view.intersects(box(*sh.bbox)):
            tiers[rec["MTFCC"]].append(sh.points); named[rec["FULLNAME"] or ""].append(sh.points)
    if not tiers["S1100"] or not tiers["S1200"]: sys.exit("no freeways or highways in the view: nothing written")
    streets, length = collections.defaultdict(list), collections.Counter()
    for c in ROAD_COUNTIES:
        for rec, sh in records(data, f"tl_2024_{c}_roads.zip"):
            if rec["MTFCC"] != "S1400" or not rec["FULLNAME"] or len(sh.points) < 2 or not near.intersects(box(*sh.bbox)): continue
            streets[rec["FULLNAME"]].append(sh.points); length[rec["FULLNAME"]] += LineString(sh.points).intersection(near).length
    missing = [n for n in ALSO if n not in streets]
    if missing: sys.exit(f"streets not in the Census files: {missing}: nothing written")
    picked = sorted({n for n, _ in sorted(length.items(), key=lambda kv: (-kv[1], kv[0]))[:LONGEST]} | set(ALSO))
    water = []
    for c in WATER_COUNTIES:
        for rec, sh in records(data, f"tl_2024_{c}_areawater.zip"):
            if rec["AWATER"] < (MIN_WATER if c == "48453" else MIN_WATER_AWAY): continue
            ends = list(sh.parts) + [len(sh.points)]
            rings = [sh.points[a:b] for a, b in zip(ends, ends[1:])]
            water.append(Polygon(rings[0], rings[1:]).buffer(0))
    w = unary_union(water).intersection(view)
    polys = [p for p in polygons_of(w) if p.area > 1e-5]
    if not polys: sys.exit("no water in the view: nothing written")
    rings = [LineString(p.simplify(WATER_TOL).exterior.coords) for p in polys]
    tags = []
    for label, rx in TAGS:
        segs = [s for n, ss in named.items() if re.search(rx, n) for s in ss]
        for l in merged(segs, view):
            k = 0.0
            while k < l.length:
                p = l.interpolate(k); tags.append([label, round(p.x * Q), round(p.y * Q)]); k += TAG_EVERY
    if {t[0] for t in tags} != {t[0] for t in TAGS}: sys.exit(f"highways with no tag place: {sorted({t[0] for t in TAGS} - {t[0] for t in tags})}")
    return {"v": 1, "q": Q, "fwy": layer(merged(tiers["S1100"], view)), "hwy": layer(merged(tiers["S1200"], view)),
            "art": layer(merged([s for n in picked for s in streets[n]], near)), "water": layer(rings), "tags": sorted(tags),
            "order": [label for label, _ in TAGS]}


def main():
    need()
    raw = sys.argv[sys.argv.index("--raw") + 1] if "--raw" in sys.argv[1:] else None
    out = OUT
    if "--out" in sys.argv[1:]: out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
    text = json.dumps(build(zips(raw)), separators=(",", ":")) + "\n"
    if len(text) > MAX_BYTES: sys.exit(f"{len(text)} bytes is more than MAX_BYTES ({MAX_BYTES}): nothing written")
    out.parent.mkdir(exist_ok=True)
    out.write_text(text, encoding="utf-8")
    d = json.loads(text)
    print(out, len(text) // 1024, "KB:", ", ".join(f"{k} {len(d[k])}" for k in ("fwy", "hwy", "art", "water", "tags")))


if __name__ == "__main__":
    main()
