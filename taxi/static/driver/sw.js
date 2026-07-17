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
self.addEventListener('activate', e => e.waitUntil(clients.claim()));
