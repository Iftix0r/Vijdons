// Barcha keshlarni tozalaymiz — sahifa har doim serverdan yuklanadi
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(keys.map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});
// Fetch: hech narsani keshlamaymiz, har doim network

// Push notification — OVOZLI va kuchli
self.addEventListener('push', e => {
  let data = {};
  try { data = e.data ? e.data.json() : {}; } catch(_) {}

  const title = data.title || '🚖 Yangi buyurtma!';
  const body  = data.body  || 'Yaqin atrofda buyurtma kutmoqda';
  const url   = data.url   || '/driver/home/';

  const opts = {
    body:    body,
    icon:    '/static/driver/sounds/../icon-192.png',
    badge:   '/static/driver/sounds/../icon-192.png',
    tag:     'new-order',
    renotify: true,
    requireInteraction: true,         // foydalanuvchi yopmagunicha turadi
    vibrate:  [200, 100, 200, 100, 400, 100, 600],
    sound:   '/static/driver/sounds/new_order.wav',
    data:    { url: url },
    actions: [
      { action: 'open',    title: '✅ Ko\'rish' },
      { action: 'dismiss', title: '❌ Yopish'   },
    ],
  };

  e.waitUntil(
    self.registration.showNotification(title, opts)
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  if (e.action === 'dismiss') return;
  const url = (e.notification.data && e.notification.data.url) || '/driver/home/';
  e.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      // Agar sahifa allaqachon ochiq bo'lsa — focusga olamiz
      for (const c of list) {
        if (c.url.includes('/driver/') && 'focus' in c) return c.focus();
      }
      return clients.openWindow(url);
    })
  );
});
