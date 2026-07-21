self.addEventListener('push', function(e) {
  let data = {};
  try { data = e.data.json(); } catch(_) { data = {title: 'Vijdon Driver', body: e.data ? e.data.text() : ''}; }

  const title = data.title || 'Vijdon Driver';
  const body  = data.body  || 'Yangi buyurtma keldi!';
  const url   = data.url   || '/driver/home/';

  e.waitUntil(
    self.registration.showNotification(title, {
      body:    body,
      icon:    '/static/driver/icon-192.png',
      badge:   '/static/driver/icon-72.png',
      vibrate: [100, 50, 100, 50, 200],
      data:    { url },
      tag:     'vijdon-order',
      renotify: true,
    })
  );
});

self.addEventListener('notificationclick', function(e) {
  e.notification.close();
  const url = e.notification.data?.url || '/driver/home/';
  e.waitUntil(
    clients.matchAll({type: 'window', includeUncontrolled: true}).then(list => {
      for (const c of list) {
        if (c.url.includes('/driver/') && 'focus' in c) return c.focus();
      }
      return clients.openWindow(url);
    })
  );
});

self.addEventListener('install',  () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(
  // Diqqat: avvalgi versiyalarda (bir necha kun oldin) bu SW HTML sahifalarni
  // (Cache Storage'da 'vijdon-v1'/'vijdon-v3' nomi bilan) keshlagan edi. O'sha
  // eski keshlar ba'zi qurilmalarda hali ham qolib ketgan bo'lishi mumkin —
  // bu yerda ularni butunlay tozalaymiz, aks holda eski (server yangilagan
  // shablonlardan OLDINGI) sahifalar tasodifan yana o'qilib qolishi mumkin edi.
  caches.keys()
    .then(keys => Promise.all(keys.map(k => caches.delete(k))))
    .then(() => clients.claim())
));
