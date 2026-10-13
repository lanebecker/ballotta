"""Build index.html (the GitHub Pages site) from template-travis.html and the routing data.

Run from anywhere:  python3 source/build_site.py
Rebuild rules first if the answer key or district data change:  python3 source/build_rules.py
"""
import json, re, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
BASE_URL = "https://lanebecker.github.io/ballotta/"

key = json.load(open(HERE / "answer_key.json", encoding="utf-8"))
rules = json.load(open(HERE / "rules.json"))
tlc = json.load(open(HERE / "tlc_precincts.json"))
contests = [{k: c[k] for k in ("id", "title", "type", "choices", "level", "entity")}
            | ({"text": c.get("text", "")} if c["type"] == "measure" else {})
            for c in key["contests"]]
data = json.dumps({"contests": contests, "rules": rules, "tlc": tlc}, ensure_ascii=False)
html = (HERE / "template-travis.html").read_text(encoding="utf-8").replace("__DATA__", data)

# Self-hosted fonts: the only third-party requests are the county and Census lookups.
fonts = ("<style>@font-face{font-family:'Fraunces';src:url('fonts/Fraunces-opsz-wght.woff2') format('woff2');font-weight:100 900;font-display:swap}"
         "@font-face{font-family:'Public Sans';src:url('fonts/PublicSans-wght.woff2') format('woff2');font-weight:100 900;font-display:swap}</style>")
html = re.sub(r"<!--FONTS-->.*?<!--/FONTS-->", fonts, html, flags=re.S).replace("__OG_IMAGE__", BASE_URL + "og.png")
(ROOT / "index.html").write_text(html, encoding="utf-8")
print("index.html", len(html) // 1024, "KB")
