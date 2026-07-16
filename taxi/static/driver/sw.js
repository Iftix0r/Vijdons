// Service Worker — Web Push handler
self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  e.waitUntil(
    self.registration.showNotification(data.title || 'Yangi buyurtma!', {
      body:    data.body  || '',
      icon:    data.icon  || '/static/driver/icon-192.png',
      badge:   data.badge || '/static/driver/icon-192.png',
      tag:     'new-order',
      renotify: true,
      vibrate: [100, 50, 100, 50, 200],
      data:    { url: data.url || '/driver/home/' },
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data.url));
});
