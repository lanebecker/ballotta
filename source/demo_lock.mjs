// Locks the results demo (source/build_demo.py) behind a password, for ballotta.org/demo/ (Lane, Oct 20).
//
//     DEMO_PASSWORD='…' node source/demo_lock.mjs demo.html OUT/index.html
//
// GitHub Pages can't ask for a password, so the page itself is encrypted: AES-256-GCM, with the key stretched from the
// password by PBKDF2-SHA-256 (600,000 rounds, a fresh random salt and nonce on every build). What's published is a small
// page with a password box and the encrypted demo; the browser decrypts it (Web Crypto) and shows it. Without the
// password the made-up results can't be read, by a visitor or a crawler, or in the public repo (only the Pages deploy
// ever has the unlocked page, and it never commits it). The password comes from the DEMO_PASSWORD secret, never a file.
// The tab remembers it (sessionStorage) so switching scenes, which reloads, doesn't ask again; closing the tab forgets it.
// Node's own crypto only: nothing to install.
import { webcrypto as C, createHash } from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const ITER = 600000;
const [src, out] = process.argv.slice(2);
const pw = process.env.DEMO_PASSWORD || '';
if (!src || !out) { console.error('usage: DEMO_PASSWORD=… node source/demo_lock.mjs demo.html OUT/index.html'); process.exit(2); }
if (pw.length < 16) { console.error('DEMO_PASSWORD must be at least 16 characters (four or five random words is good)'); process.exit(2); }

const html = fs.readFileSync(src, 'utf8');
const csp = (html.match(/<meta http-equiv="Content-Security-Policy" content="([^"]*)">/) || [])[1];
if (!csp || !csp.includes("script-src 'self' ")) { console.error('the demo page has no Content-Security-Policy to build on'); process.exit(1); }

const salt = C.getRandomValues(new Uint8Array(16)), iv = C.getRandomValues(new Uint8Array(12));
const base = await C.subtle.importKey('raw', new TextEncoder().encode(pw), 'PBKDF2', false, ['deriveKey']);
const key = await C.subtle.deriveKey({ name: 'PBKDF2', salt, iterations: ITER, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['encrypt']);
const sealed = new Uint8Array(await C.subtle.encrypt({ name: 'AES-GCM', iv }, key, new TextEncoder().encode(html)));
const box = Buffer.concat([salt, iv, sealed]).toString('base64');

// The unlocking script. Its hash joins the demo's own in the policy: the demo's scripts must run once it's written in,
// and document.open() keeps this page's policy.
const js = `(() => {
  const ITER = ${ITER}, bytes = Uint8Array.from(atob(document.getElementById('box').textContent.trim()), (c) => c.charCodeAt(0));
  const form = document.getElementById('lock'), pw = document.getElementById('pw'), msg = document.getElementById('msg'), go = document.getElementById('go');
  async function unlock(p, quiet) {
    try {
      const base = await crypto.subtle.importKey('raw', new TextEncoder().encode(p), 'PBKDF2', false, ['deriveKey']);
      const key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: bytes.slice(0, 16), iterations: ITER, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, false, ['decrypt']);
      const page = new TextDecoder().decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: bytes.slice(16, 28) }, key, bytes.slice(28)));
      try { sessionStorage.setItem('demo:pw', p); } catch (e) {}
      document.open(); document.write(page); document.close();
    } catch (e) {
      try { sessionStorage.removeItem('demo:pw'); } catch (e2) {}
      go.disabled = false; msg.textContent = quiet ? '' : 'That password didn\\u2019t work.'; if (!quiet) pw.select();
    }
  }
  form.addEventListener('submit', (e) => { e.preventDefault(); if (!pw.value) return; go.disabled = true; msg.textContent = 'Unlocking\\u2026'; unlock(pw.value, false); });
  let saved = null; try { saved = sessionStorage.getItem('demo:pw'); } catch (e) {}
  if (saved) { go.disabled = true; msg.textContent = 'Unlocking\\u2026'; unlock(saved, true); }
})();`;
const hash = "'sha256-" + createHash('sha256').update(js, 'utf8').digest('base64') + "'";
const policy = csp.replace("script-src 'self' ", "script-src 'self' " + hash + ' ');

const page = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="${policy}">
<meta name="referrer" content="no-referrer">
<meta name="robots" content="noindex, nofollow">
<title>Ballotta demo</title>
<link rel="icon" href="../favicon.svg">
<style>
@font-face{font-family:'Zilla Slab';src:url('../fonts/ZillaSlab-Bold.woff2') format('woff2');font-weight:700}
@font-face{font-family:'Public Sans';src:url('../fonts/PublicSans-wght.woff2') format('woff2');font-weight:100 900}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px 16px;background:#4B2A6B;color:#241A2E;font:16px/1.5 'Public Sans',system-ui,sans-serif;font-variant-numeric:lining-nums}
form{width:100%;max-width:400px;background:#FFF9F1;border-radius:12px;padding:24px;display:flex;flex-direction:column;gap:14px}
h1{margin:0;font:700 28px/1.1 'Zilla Slab',Rockwell,Georgia,serif}
p{margin:0}.note{font-size:14px;color:#5E4B73}
label{font-size:14px;font-weight:600;display:flex;flex-direction:column;gap:6px}
input{font:inherit;font-size:16px;height:48px;padding:0 12px;border-radius:10px;border:1px solid #8E7FA0;background:#fff;color:#241A2E}
button{font:inherit;font-weight:600;min-height:52px;border:none;border-radius:12px;background:#4B2A6B;color:#fff;cursor:pointer}
button:disabled{opacity:.6}
input:focus-visible,button:focus-visible{outline:3px solid #E9A92A;outline-offset:2px}
#msg{min-height:1.5em;font-size:14px;font-weight:600;color:#7A5A00}
</style>
</head>
<body>
<form id="lock">
  <h1>Ballotta demo</h1>
  <p class="note">Made-up results for testing the results pages. Not real, and not for sharing.</p>
  <label for="pw">Password<input id="pw" type="password" autocomplete="current-password" autofocus></label>
  <button id="go" type="submit">Unlock</button>
  <p id="msg" role="status"></p>
</form>
<script type="application/octet-stream" id="box">${box}</script>
<script>${js}</script>
</body>
</html>
`;
fs.mkdirSync(path.dirname(out), { recursive: true });   // a bare file name is its own folder's (the cold audit, #150)
fs.writeFileSync(out, page);
console.log(`locked: ${out} (${Math.round(page.length / 1024)} KB)`);
