"""The results demo (source/build_demo.py, source/demo_lock.mjs): what it may never show, and that the lock holds.

    python3 tests/test_demo.py

Needs node (for the lock, as the Pages workflow runs it). Stdlib otherwise.
"""
import json, os, pathlib, re, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "source"))
import build_demo  # noqa: E402

PW = "a long enough test password"
UNLOCK = r"""
import { webcrypto as C } from 'node:crypto'; import fs from 'node:fs';
const page = fs.readFileSync(process.argv[2], 'utf8'), pw = process.argv[3];
const b = Buffer.from(page.match(/<script type="application\/octet-stream" id="box">([^<]*)<\/script>/)[1], 'base64');
const k0 = await C.subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey']);
const k = await C.subtle.deriveKey({ name: 'PBKDF2', salt: b.subarray(0, 16), iterations: +page.match(/ITER = (\d+)/)[1], hash: 'SHA-256' }, k0, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
try { process.stdout.write(new TextDecoder().decode(await C.subtle.decrypt({ name: 'AES-GCM', iv: b.subarray(16, 28) }, k, b.subarray(28)))); }
catch (e) { process.exit(3); }
"""
fails = []
def check(ok, what):
    print(("PASS " if ok else "FAIL ") + what); ok or fails.append(what)

html = build_demo.page()
key = json.load(open(ROOT / "source/answer_key.json", encoding="utf-8"))["contests"]
real = {build_demo.base(ch) for c in key if c["type"] != "measure" for ch in c["choices"]} - {"Write-in", "FOR", "AGAINST", "For", "Against"}
real |= {w["name"] for m in json.load(open(ROOT / "source/results_map.json", encoding="utf-8"))["contests"].values() for w in m.get("write_ins", [])}   # declared write-ins are real people too (#150)
check(not [n for n in real if n in html], "no real candidate's name anywhere in the demo")
check("fetch('results.json'" not in html, "the demo never asks for the real results")
sys.path.insert(0, str(ROOT / "tests")); import results_demo, collections   # noqa: E402
PARTY = re.compile(r"\((REP|DEM|LIB|GRN)\)$"); won = collections.Counter()
for cid, e in results_demo.scene("dec8")["contests"].items():
    full = [x for x in {c["id"]: c for c in key}[cid]["choices"] if e["verdict"] == "won" and x.startswith(e["leaders"][0])]
    if full and PARTY.search(full[0]): won[PARTY.search(full[0]).group(1)] += 1
check(len(won) >= 2 and min(won.values()) * 4 >= sum(won.values()), f"the Dec 8 scene's party races don't all go one way ({dict(won)}) (#139)")
check('<meta name="robots" content="noindex">' in html and 'data-domains="preview.invalid"' in html, "search engines kept out; the tracker can't send")
check("Demo · made-up results" in html and "TEST DATA (not real results)" in html, "labeled a demo on every screen, and in every result's source")
check("'ballotta." not in html and "startsWith('demo:ballotta.')" in html and "sw.register(" not in html, "its own storage; no offline copy")

# In a browser, on the real page's origin: the demo reads and writes only its own keys, and its Clear everything leaves
# the real page's ballot, picks and reasons alone (the cold audit, Oct 21).
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.route("https://ballotta.test/**", lambda r: r.fulfill(status=200, content_type="text/html", body=html) if r.request.url.endswith("/demo/") else r.fulfill(status=404, body=""))
    pg.on("dialog", lambda d: d.accept())
    real = {"ballotta.picks": '{"c001":["x"]}', "ballotta.whys": '{"c001":"mine"}', "ballotta.ballot": '{"pr":"142","b":[1]}'}
    pg.goto("https://ballotta.test/demo/")
    pg.evaluate("kv => { for (const k in kv) localStorage.setItem(k, kv[k]); localStorage.setItem('demo:ballotta.picks', '{}'); }", real)
    pg.goto("https://ballotta.test/demo/"); pg.wait_for_timeout(300)
    pg.evaluate("() => clearEverything()"); pg.wait_for_timeout(500)
    left = pg.evaluate("() => Object.fromEntries(Object.keys(localStorage).map(k => [k, localStorage.getItem(k)]))")
    check(all(left.get(k) == v for k, v in real.items()), "the demo's Clear everything leaves the real page's keys")
    check(not [k for k in left if k.startswith("demo:ballotta.")], "and clears the demo's own")
    b.close()
check("League answers aren’t linked in the demo" in html and "LWVAA-VG-EN.pdf#page=2" not in html, "no League answers or guide pages under made-up names")

with tempfile.TemporaryDirectory() as d:
    src, out = pathlib.Path(d, "demo.html"), pathlib.Path(d, "demo", "index.html")
    src.write_text(html, encoding="utf-8")
    env = {**os.environ, "DEMO_PASSWORD": PW}
    r = subprocess.run(["node", str(ROOT / "source/demo_lock.mjs"), str(src), str(out)], env=env, capture_output=True, text=True)
    check(r.returncode == 0, "the lock runs")
    locked = out.read_text(encoding="utf-8")
    check("Celia" not in locked and "TEST DATA" not in locked and "results" not in locked.split('id="box">')[1][:2000], "the locked page holds nothing readable")
    check('<meta name="robots" content="noindex, nofollow">' in locked, "the locked page is kept out of search too")
    js = pathlib.Path(d, "unlock.mjs"); js.write_text(UNLOCK)
    good = subprocess.run(["node", str(js), str(out), PW], capture_output=True, text=True)
    check(good.returncode == 0 and good.stdout == html, "the right password gives back the demo, byte for byte")
    bad = subprocess.run(["node", str(js), str(out), PW + "x"], capture_output=True, text=True)
    check(bad.returncode == 3 and not bad.stdout, "a wrong password gives back nothing")
    short = subprocess.run(["node", str(ROOT / "source/demo_lock.mjs"), str(src), str(out)], env={**os.environ, "DEMO_PASSWORD": "short"}, capture_output=True, text=True)
    check(short.returncode == 2, "a short password is refused")

print("all passed" if not fails else f"{len(fails)} failed")
sys.exit(1 if fails else 0)
