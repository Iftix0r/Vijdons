const CACHE = 'vijdon-v1';
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

// Push notification
self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  e.waitUntil(
    self.registration.showNotification(data.title || 'Yangi buyurtma!', {
      body:     data.body  || '',
      icon:     data.icon  || '/static/driver/icon-192.png',
      badge:    data.badge || '/static/driver/icon-192.png',
      tag:      'new-order',
      renotify: true,
      vibrate:  [100, 50, 100, 50, 200],
      data:     { url: data.url || '/driver/home/' },
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data.url));
});
