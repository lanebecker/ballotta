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
check(not [n for n in real if n in html], "no real candidate's name anywhere in the demo")
check("fetch('results.json'" not in html, "the demo never asks for the real results")
check('<meta name="robots" content="noindex">' in html and 'data-domains="preview.invalid"' in html, "search engines kept out; the tracker can't send")
check("Demo · made-up results" in html and "TEST DATA (not real results)" in html, "labeled a demo on every screen, and in every result's source")
check("localStorage.getItem('demo:' + k" in html and "sw.register(" not in html, "its own storage; no offline copy")
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
