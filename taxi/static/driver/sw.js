const CACHE = 'vijdon-v3';
const PRECACHE = [
  '/driver/home/',
  '/driver/history/',
  '/driver/chat/',
  '/driver/profile/',
];

// Install: asosiy sahifalarni keshga olish
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

// Activate: eski keshlarni tozalash
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

// Fetch: Network-first, offline bo'lsa keshdan
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API so'rovlarini keshlamaymiz
  if (url.pathname.includes('/json') ||
      url.pathname.includes('/sync/') ||
      url.pathname.includes('/orders/') ||
      e.request.method !== 'GET') return;

  e.respondWith(
    fetch(e.request)
      .then(res => {
        // Muvaffaqiyatli javobni keshga saqlaymiz
        if (res.ok && url.pathname.startsWith('/driver/')) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});

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
