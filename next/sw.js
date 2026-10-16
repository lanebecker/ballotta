// Built by source/build_site.py; don't edit sw.js. Ballotta's offline copy: network first, kept copy as a fallback.
const CACHE = 'ballotta-next-1';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(caches.keys()
  .then((ks) => Promise.all(ks.filter((k) => k.startsWith('ballotta-next-') && !k.startsWith('ballotta-next-next-') && k !== CACHE).map((k) => caches.delete(k))))
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
  e.respondWith(Promise.race([net.catch(() => null), new Promise((ok) => setTimeout(ok, 4000, null))])
    .then(async (first) => first || (await caches.open(CACHE).then((c) => c.match(key))) || net));  // only its own copies; nothing kept: wait for the network
});
