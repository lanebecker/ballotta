"""The results demo (Lane, Oct 20): the real page, with made-up results, at ballotta.org/demo/ behind a password.

    python3 source/build_demo.py OUT.html            # the unlocked demo page; source/demo_lock.mjs locks it

What makes it a demo, and never mistakable for the real thing:
- Every candidate's name is swapped for a made-up one (contests, sources and results alike), so no picture of the demo
  can show a real person winning or losing. Contest titles stay real: they're the ballot's own.
- Campaign links go to example.com, and the League's answers aren't linked: they'd be real people's words under
  made-up names.
- Results come from tests/results_demo.py (made-up numbers through the real rules), built into the page. The page never
  asks for results.json, so the demo can't show real results either.
- The page's clock is the scene's ("Wed, Nov 4, 9 am", ...), picked from a gold "Demo · made-up results" ribbon that
  stays on every screen.
- Picks and reasons are kept apart from the real page's (localStorage keys start "demo:"), the tracker can't send
  anything (the preview's dead domain list), no offline copy is installed, and search engines are asked to stay out.
The page is built by build_site.build(preview=True, results=True): the preview build already lives one folder down and
counts nothing. This only adds the demo's changes, through build()'s two hooks.
"""
import json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tests"))
import build_site  # noqa: E402
import results_demo  # noqa: E402

# Made-up names. Common first and last names, paired by a fixed rule, so the same real name always gets the same made-up
# one and two different real names never share one.
FIRST = ["Maya", "Daniel", "Sam", "Lena", "Omar", "Grace", "Jordan", "Priya", "Nina", "Marcus", "Ruth", "Alan", "Beth",
         "Dana", "Luis", "Helen", "Chris", "Ana", "Teresa", "Wade", "Keisha", "June", "Ray", "Ken", "Rebecca", "Elena",
         "Victor", "Hannah", "Isaac", "Carmen", "Felix", "Iris", "Malik", "Nora", "Pablo", "Quinn", "Rosa", "Theo", "Uma",
         "Walter", "Yvonne", "Zane", "Celia", "Dev", "Esther", "Gabe", "Hope", "Ivan", "Joy", "Kurt", "Lila", "Miles"]
LAST = ["Ortega", "Price", "Whitfield", "Brooks", "Haddad", "Tran", "Lee", "Nand", "Shah", "Webb", "Alvarez", "Cho",
        "Moran", "Ruiz", "Ortiz", "Marsh", "Bell", "Flores", "Gomez", "Ellison", "Grant", "Park", "Duval", "Ward", "Lang",
        "Castillo", "Hale", "Okafor", "Brandt", "Sato", "Mercer", "Quintero", "Lowell", "Abbott", "Fenn", "Garza", "Holm",
        "Ivers", "Jamison", "Kerr", "Lindqvist", "Madsen", "Novak", "Osei", "Pruitt", "Rao", "Sutter", "Talley", "Underhill",
        "Vance", "Winslow", "Yates", "Zeller", "Adair", "Bishop", "Crane", "Dorsey", "Eaton", "Fry", "Gentry", "Hollis"]
PARTY = re.compile(r"\s*\((REP|DEM|LIB|GRN|IND)\)$")
NOT_A_NAME = {"write-in", "for", "against", "yes", "no"}   # compared in lower case: some ballots say FOR / AGAINST

SCENES = {   # the scene's clock (Austin time) and its label in the ribbon; results_demo makes each one's results
    "nov4": ("2026-11-04T09:00", "Wed, Nov 4 · the morning after"),
    "nov13": ("2026-11-13T09:00", "Thu, Nov 13 · local canvasses done"),
    "dec8": ("2026-12-08T09:30", "Tue, Dec 8 · state canvass done"),
}
DEFAULT = "nov13"


def base(name):
    return PARTY.sub("", name)


def made_up(names):
    """Each real name (without its party label) to a made-up one, the same on every build."""
    real = sorted({base(n) for n in names if base(n).lower() not in NOT_A_NAME})
    out, used = {}, set()
    for k, n in enumerate(real):
        i = k
        while True:
            fake = FIRST[i % len(FIRST)] + " " + LAST[(i * 7 + i // len(FIRST)) % len(LAST)]
            if fake not in used and fake not in real:
                break
            i += 1
        used.add(fake); out[n] = fake
    return out


def swap(name, names):
    b = base(name)
    if b not in names:
        return name
    return names[b] + name[len(b):]   # keeps " (REP)" and the like


def candidate_names(contests, scenes):
    seen = [ch for c in contests if c["type"] != "measure" for ch in c["choices"]]
    for s in scenes.values():
        for e in s["contests"].values():
            seen += [x[0] for x in e["choices"]] + e["leaders"] + e["runoff"] + [x[0] for x in (e["travis"] or [])]
    return seen


def results_with(names, obj):
    for e in obj["contests"].values():
        e["choices"] = [[swap(x[0], names)] + x[1:] for x in e["choices"]]
        e["leaders"] = [swap(n, names) for n in e["leaders"]]
        e["runoff"] = [swap(n, names) for n in e["runoff"]]
        if e["travis"]:
            e["travis"] = [[swap(x[0], names)] + x[1:] for x in e["travis"]]
    return obj


def data_with(names):
    def hook(data):
        for c in data["contests"]:
            if c["type"] != "measure":
                c["choices"] = [swap(ch, names) for ch in c["choices"]]
        for cid, L in data["learn"].items():
            if L.get("cands"):
                L["cands"] = {swap(n, names): {**v, "s": "https://example.com/", "a": 0} for n, v in L["cands"].items()}   # no League answers: below
            if L.get("src"):   # the League's guide quotes the real candidates: not under made-up names
                L["src"] = [x for x in L["src"] if not x.get("lwv")]
        return data
    return hook


RIBBON = """const DEMO = (() => {
  const S = __SCENES__, D = '__DEFAULT__';
  let k = D; try { k = sessionStorage.getItem('demo:scene') || D; } catch (e) {}
  if (!S[k]) k = D;
  return { key: k, scenes: S, now: S[k].now, results: S[k].results };
})();
addEventListener('DOMContentLoaded', () => {
  const bar = document.createElement('div');
  bar.setAttribute('role', 'region'); bar.setAttribute('aria-label', 'Demo');
  bar.style.cssText = 'position:fixed;z-index:2147483000;display:flex;gap:10px;align-items:center;padding:6px 8px 6px 14px;border-radius:999px;background:#E9A92A;color:#241A2E;font:600 13px/1.2 "Public Sans",system-ui,sans-serif;box-shadow:0 6px 18px rgba(36,26,46,.25);max-width:calc(100vw - 24px)';
  const place = () => { const narrow = matchMedia('(max-width: 1023.98px)').matches; bar.style.bottom = narrow ? '88px' : '16px'; bar.style.left = narrow ? '12px' : 'auto'; bar.style.right = narrow ? 'auto' : '16px'; };   // clear of the phone's bottom bar, and of the laptop rail's buttons
  place(); matchMedia('(max-width: 1023.98px)').addEventListener('change', place);
  const label = document.createElement('span'); label.textContent = 'Demo · made-up results';
  const pick = document.createElement('select'); pick.setAttribute('aria-label', 'Demo scene');
  pick.style.cssText = 'font:inherit;padding:4px 6px;border-radius:999px;border:1px solid rgba(36,26,46,.35);background:#FFF9F1;color:#241A2E;max-width:60vw';
  Object.keys(DEMO.scenes).forEach((k) => { const o = document.createElement('option'); o.value = k; o.textContent = DEMO.scenes[k].label; o.selected = k === DEMO.key; pick.appendChild(o); });
  pick.addEventListener('change', () => { try { sessionStorage.setItem('demo:scene', pick.value); } catch (e) {} location.reload(); });
  bar.append(label, pick);
  document.body.appendChild(bar);
});"""


def page():
    obj = {k: results_demo.scene(k) for k in SCENES}
    key = json.load(open(HERE / "answer_key.json", encoding="utf-8"))["contests"]
    names = made_up(candidate_names(key, obj))
    scenes = {k: {"now": SCENES[k][0], "label": SCENES[k][1], "results": results_with(names, obj[k])} for k in SCENES}

    def hook(html):
        swaps = [   # (what the page has, what the demo has instead); each must be there exactly once
            ("<title>[Preview] Ballotta ·", "<title>[Demo] Ballotta ·"),
            # the scene's clock, for everything that asks the date (the results' Nov 4 gate included)
            (re.search(r"^const today = \(\) => .*$", html, re.M).group(0), "const today = () => new Date(DEMO.now);  // the demo's scene (source/build_demo.py)"),
            # the scene's results, built in: the demo never asks for results.json
            ("fetch('results.json', { cache: 'no-store' })", "Promise.resolve(new Response(JSON.stringify(DEMO.results)))"),
            # no offline copy: the demo is one locked file, and the real page's copy is the real page's
            (build_site.SW_REGISTER, ""),
            # the League guide's answers are real candidates' words: not linked under made-up names
            ("'<span class=\"none\">Didn’t answer the League guide</span>'", "'<span class=\"none\">League answers aren’t linked in the demo</span>'"),
            ("</head>", "<script>" + RIBBON.replace("__SCENES__", build_site.script_json(scenes)).replace("__DEFAULT__", DEFAULT) + "</script>\n</head>"),
        ]
        for a, b in swaps:
            assert html.count(a) == 1, ("the demo expects this once in the page", a[:80], html.count(a))
            html = html.replace(a, b, 1)
        # Everything the page keeps in this browser, kept apart from the real page's (the same origin, ballotta.org): every
        # storage key the page names starts 'ballotta.', so each one becomes 'demo:ballotta.'. That covers reading and
        # writing, and Clear everything, which removes keys by that start and so must never reach the real page's
        # (the cold audit, Oct 21: before this, the demo's Clear everything wiped the visitor's real ballot).
        n = html.count("'ballotta.")
        assert n >= 40, ("the page's storage keys moved", n)
        html = html.replace("'ballotta.", "'demo:ballotta.")
        assert '<meta name="robots" content="noindex">' in html and 'data-domains="preview.invalid"' in html
        assert "fetch('results.json'" not in html
        return html

    html = build_site.build(preview=True, results=True, data_hook=data_with(names), hook=hook)
    leaked = [n for n in names if n in html]
    assert not leaked, ("a real candidate's name is still in the demo", leaked[:5])
    return html


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    out = pathlib.Path(sys.argv[1])
    out.write_text(page(), encoding="utf-8")
    print(f"demo: {out} ({out.stat().st_size // 1024} KB, scenes {', '.join(SCENES)})")
