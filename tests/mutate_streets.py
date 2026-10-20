"""Mutation-kill check for the street map's tests (Lane, Oct 19): every mutant must turn at least one named test RED.
The same runner as mutate_desk.py (files restored from an in-memory copy, even when stopped), against the page with the
street map: next/index.html until promotion, index.html after. Run from the repo root after the build:
    python3 tests/mutate_streets.py [first last]   (a slice of the list, e.g. 0 10)"""
import os, re, sys, pathlib
ROOT = pathlib.Path.cwd()
_set = re.findall(r'^STREETS_LIVE\s*=\s*(True|False)\b', (ROOT / 'source/build_site.py').read_text(encoding='utf-8'), re.M)
assert len(_set) == 1, ('STREETS_LIVE set', len(_set), 'times in build_site.py')
LIVE = _set[0] == 'True'                                                                    # the setting's own line
os.environ['BALLOTTA_MUTATE_PAGE'] = 'index.html' if LIVE else 'next/index.html'
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import mutate_desk as R

PREV, TPL, BLD = R.PREV, R.TPL, R.BLD
D, B = 'street_map_draws_streets_and_asks_nobody', 'street_map_waits_for_promotion'
M = [
 ('S1 the grid stays', PREV, '    g = streetLayer(all, X, Y, W, H, sx, sy);   // streets and water in place of the grid\n', '', [D]),
 ('S2 a widened map keeps every street', PREV, "(sx <= 0.6 ? d(L.art) : '')", 'd(L.art)', [D]),
 ('S3 lines above and below the view drawn', PREV, 'f.b[2] >= w && f.b[0] <= e && f.b[3] >= s && f.b[1] <= n', 'f.b[2] >= w && f.b[0] <= e', [D]),
 ('S4 lines left and right of the view drawn', PREV, 'f.b[2] >= w && f.b[0] <= e && f.b[3] >= s && f.b[1] <= n', 'f.b[3] >= s && f.b[1] <= n', [D]),
 ('S5 a tag lands on whatever is there', PREV, 'inside(x, y) && !taken.some(t => overlaps(box(x, y), t)));', 'inside(x, y));', [D]),
 ('S6 tags pile on each other', PREV, '      taken.push(box(x, y));\n', '', [D]),
 ('S7 tags ignore the town names', PREV, "const taken = mapMarks(all, X, Y, W, H).concat(PLACES", "const taken = mapMarks(all, X, Y, W, H).concat(PLACES.slice(0, 0)", [D]),
 ('S8 town names stay under the dots', PREV, '/*STREETS*/.map(p => placeClear(p, all, X, Y, W, H, sy)).filter(Boolean)/*/STREETS*/', '', [D]),
 ('S9 a town name may sit on you', PREV, '    return [[W / 2 - 18, H / 2 - 18, W / 2 + 18, H / 2 + 18]].concat(all.map', '    return [].concat(all.map', [D]),
 ('S10 a moved town name moves the wrong way', PREV, "return [p[0], p[1], p[2] - dy * sy / H];", "return [p[0], p[1], p[2] + dy * sy / H];", [D]),
 ('S11 phone tags at laptop size', PREV, "const fs = matchMedia('(max-width: 1023.98px)').matches ? 12 : 10, best = {};", 'const fs = 10, best = {};', [D]),
 ('S12 the tag box ignores the label', PREV, 'bw = name.length * fs * 0.64 + fs, bh', 'bw = 30, bh', [D]),
 ('S13 a tag hangs off the edge', PREV, '.find(([, x, y]) => inside(x, y) && !taken.some(', '.find(([, x, y]) => !taken.some(', [D]),
 ('S14 no halo on the town names', PREV, '  .dk-map .st-wat ~ text{font-weight:600;fill:var(--ink2);paint-order:stroke;stroke:var(--ground);stroke-width:3px;stroke-linejoin:round}\n  .dk-map .st-tag rect{fill:#fff;stroke:#CDBFAE;stroke-width:1}\n  .dk-map .st-tag text{font-weight:700;fill:var(--muted)}\n/*/STREETS*/\n  /* crib sheet preview', '  .dk-map .st-tag rect{fill:#fff;stroke:#CDBFAE;stroke-width:1}\n  .dk-map .st-tag text{font-weight:700;fill:var(--muted)}\n/*/STREETS*/\n  /* crib sheet preview', [D]),
 ('S15 no water drawn', PREV, "let out = '<path class=\"st-wat\" d=\"' + d(L.water) + '\"></path>'", "let out = '<path class=\"st-wat\" d=\"\"></path>'", [D]),
 ('S16 freeways only', PREV, "const fw = d(L.fwy), hw = d(L.hwy);", "const fw = d(L.fwy), hw = '';", [D]),
 ('S17 the main page gets the street map', BLD, 'streets = streets if streets is not None else bool((preview or STREETS_LIVE) and desk)', 'streets = streets if streets is not None else bool(desk)', [B]),
 ('S18 the preview has no street map', BLD, 'streets = streets if streets is not None else bool((preview or STREETS_LIVE) and desk)', 'streets = streets if streets is not None else bool(STREETS_LIVE and desk)', [B]),
 ('S19 the street data spaced out', BLD, 'script_json(json.load(open(HERE / "data/streets.json", encoding="utf-8")), compact=True)', 'script_json(json.load(open(HERE / "data/streets.json", encoding="utf-8")))', [B]),
 ('S20 the preview without its offline copy', BLD, '"next/sw.js": sw_js(True) if OFFLINE else sw_off_js(True), "next/index.html": build(True)', '"next/sw.js": sw_off_js(True), "next/index.html": build(True)', [B]),
 ('S21 the street strip between the phone if and its else', BLD, '    if not streets:   # before the phone layout\'s if/else below, never between them\n        html = strip_streets(html)\n    if not phone:\n        html = strip_phone(html)\n', '    if not phone:\n        html = strip_phone(html)\n    if not streets:\n        html = strip_streets(html)\n', ['live_build_is_unchanged_until_promotion', B]),
 ('S22 the street map drawn without the laptop layout', BLD, '    assert desk or not streets, "the street map is drawn by the laptop layout\'s code"\n', '', [B]),
 ('S23 no credit', TPL, '<!--STREETS--> Streets and water on the map: U.S. Census Bureau TIGER/Line, 2024.<!--/STREETS-->', '', [B]),
 ('S25 search engines may list the preview', BLD, "html.replace('<meta name=\"referrer\" content=\"no-referrer\">', '<meta name=\"referrer\" content=\"no-referrer\">\\n<meta name=\"robots\" content=\"noindex\">', 1)", "html", [B]),
 ("S26 the preview asks for a version.json that isn't there", BLD, """("fetch('version.json?'", "fetch('../version.json?'")""", """("fetch('version.json?'", "fetch('version.json?'")""", [B]),
 ('S27 the main copy fetches the preview at install', BLD, "    if not preview and not STREETS_LIVE:   # next/ is the street map's preview", "    if False:   # next/ is the street map's preview", [B]),
 ('S28 a kept hand-off page outlives the preview', BLD, "        js = js.replace(STALE_NEXT[0], STALE_NEXT[1], 1)\n        assert STALE_NEXT[1] in js\n", '', [B]),
 ('S24 a malformed STREETS marker passes', BLD, "def strip_streets(html):\n    return strip_marked(html, 'STREETS')", "def strip_streets(html):\n    return html.replace('/*STREETS*/', '').replace('/*/STREETS*/', '')", [B]),
]
# Only while the street map is in preview: their code runs only with STREETS_LIVE = False, so once it is live they
# change nothing and can't be killed (measured on a promoted copy, Oct 19; checked again by a third review pass). The
# runner leaves them out then.
PREVIEW_ONLY = {'S17', 'S18', 'S20', 'S27', 'S28'}   # (S21 still matters: a phone-layout rollback after promotion)
if LIVE:
    M = [m for m in M if m[0].split()[0] not in PREVIEW_ONLY]
if __name__ == '__main__':
    R.main(M)
