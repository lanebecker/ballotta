// Built by source/build_site.py; don't edit sw.js. Ballotta's offline copy: network first, kept copy as a fallback.
const CACHE = 'ballotta-1';
// The page keeps a copy of itself from the start, so it opens offline before its next visit, and so does a Home
// Screen app that installed the preview, whose next/ now sends it on to ./ (promotion audit #3). Nothing fails if it can't,
// and a slow line never holds the install up for more than 8 seconds (no-cache: a 304 when the page hasn't changed).
self.addEventListener('install', (e) => { self.skipWaiting(); e.waitUntil(caches.open(CACHE).then((c) => Promise.all(['./', 'next/'].map((u) => {
  const at = new URL(u, location.href).href, stop = new AbortController(), t = setTimeout(() => stop.abort(), 8000);
  return fetch(at, { cache: 'no-cache', signal: stop.signal }).then((res) => res.ok && res.type === 'basic' && !res.redirected && c.put(at, res))
    .catch(() => {}).finally(() => clearTimeout(t)); })))); });
self.addEventListener('activate', (e) => e.waitUntil(caches.keys()
  .then((ks) => Promise.all(ks.filter((k) => k.startsWith('ballotta-') && !k.startsWith('ballotta-next-') && k !== CACHE).map((k) => caches.delete(k))))
  .then(() => self.clients.claim())));
self.addEventListener('fetch', (e) => {
  const r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== location.origin || r.headers.has('range')) return;  // the browser handles it, as if there were no copy
  const key = u.origin + u.pathname;  // one copy per file, whatever ?query a link adds
  const net = fetch(r).then((res) => {
    if (res.ok && res.type === 'basic') { const copy = res.clone(); e.waitUntil(caches.open(CACHE).then((c) => c.put(key, copy)).catch(() => {})); }
    return res;
  });
  e.waitUntil(net.catch(() => {}));  // a late answer still refreshes the kept copy
  e.respondWith(Promise.race([net.catch(() => 'offline'), new Promise((ok) => setTimeout(ok, 4000, 'slow'))])
    .then(async (first) => {
      // A server error inside 4 seconds (a deploy, a proxy, a portal) counts as no answer when a copy is kept (#74).
      const bad = typeof first !== 'string' && (first.type === 'error' || (first.type === 'basic' && !first.ok));
      if (typeof first !== 'string' && !bad) return first;  // the network's own answer
      const kept = await caches.open(CACHE).then((c) => c.match(key));  // only its own copies
      if (!kept) return net;  // nothing kept: wait for the network
      const page = r.mode === 'navigate' && (kept.headers.get('content-type') || '').startsWith('text/html');  // never an image or the manifest, even opened directly
      return page ? said(kept.clone(), bad ? 'error' : first).catch(() => kept) : kept;
    }));
});
// A page answered from the kept copy says so, and why, before any of its scripts run (Lane, B4): <html data-copy="offline">,
// "slow" or "error". It marks the document's own opening tag, whatever attributes it has, so a template change can't quietly stop it (#75).
const said = (res, why) => res.text().then((t) => { const h = new Headers(res.headers); h.delete('content-length'); h.delete('content-encoding');
  return new Response(t.replace(/^(\s*(?:<!doctype html>\s*)?<html)(?=[\s>])/i, '$1 data-copy="' + why + '"'), { status: res.status, statusText: res.statusText, headers: h }); });
