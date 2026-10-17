// Built by source/build_site.py: removes Ballotta's offline copy from this browser. It takes the open pages over first,
// so the old copy can't keep filling its cache, then deletes its caches (only Ballotta's), then itself.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim().then(() => caches.keys())
  .then((ks) => Promise.all(ks.filter((k) => k.startsWith('ballotta-next-') && !k.startsWith('ballotta-next-next-')).map((k) => caches.delete(k))))
  .then(() => self.registration.unregister())));
