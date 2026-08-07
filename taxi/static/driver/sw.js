self.addEventListener('push', function(e) {
  let data = {};
  try { data = e.data.json(); } catch(_) { data = {title: 'Vijdon Driver', body: e.data ? e.data.text() : ''}; }

  const title = data.title || 'Vijdon Driver';
  const body  = data.body  || 'Yangi buyurtma keldi!';
  const url   = data.url   || '/driver/home/';

  e.waitUntil(
    Promise.all([
      self.registration.showNotification(title, {
        body:    body,
        icon:    '/static/driver/icon-192.png',
        badge:   '/static/driver/icon-72.png',
        vibrate: [100, 50, 100, 50, 200],
        data:    { url },
        tag:     'vijdon-order',
        renotify: true,
      }),
      // Diqqat: ilova ochiq bo'lgan sahifaga DARHOL xabar beramiz —
      // aks holda push faqat tizim bildirishnomasini ko'rsatardi-yu, sahifa
      // o'zi navbatdagi 10 soniyalik pollingigacha (setInterval(loadOrders,
      // 10000)) yangi buyurtmani bilmasdi. Manzil navbatida dispatch_timeout
      // ham 10s bo'lgani uchun, eng yomon holatda haydovchi buyurtmani
      // ko'rishga ham ulgurmay, vaqt tugab, keyingisiga o'tib ketardi. Endi
      // sahifa (agar ochiq bo'lsa) shu postMessage'ni eshitib, loadOrders()'ni
      // kutmasdan zudlik bilan chaqiradi.
      self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
        list.forEach(c => c.postMessage({ type: 'vijdon_push_refresh' }));
      }),
    ])
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

// Diqqat: FAQAT o'zgarmaydigan statik kutubxonalar (Tailwind, FontAwesome,
// Mapbox, Yandex Maps skriptlari) va ilovaning o'z /static/ fayllari
// keshlanadi — hech qachon Django'dan kelgan sahifalar (HTML) yoki
// /driver/ ostidagi JSON endpointlar emas. Sabab: avvalgi versiyalarda
// (bir necha kun oldin) bu SW HTML sahifalarni ham keshlagan edi va bu
// eski (yangilanmagan) buyurtma/taksometr ma'lumotlari ko'rsatilib qolish
// xatosiga olib kelgan edi ("Disable caching for driver pages" commiti
// shu muammoni tuzatgan). Endi shu xato qaytarilmasligi uchun quyidagi
// ro'yxat qasddan TOR — faqat aniq statik manbalar.
const STATIC_CACHE = 'vijdon-static-v1';
const STATIC_HOSTS = ['cdn.tailwindcss.com', 'cdnjs.cloudflare.com', 'api.mapbox.com', 'api-maps.yandex.ru'];

self.addEventListener('activate', e => e.waitUntil(
  caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== STATIC_CACHE).map(k => caches.delete(k))))
    .then(() => clients.claim())
));

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return; // amallarga (POST) hech qachon tegilmaydi

  const url = new URL(req.url);
  const isStaticLib = STATIC_HOSTS.includes(url.hostname);
  const isOwnStatic = url.origin === self.location.origin && url.pathname.startsWith('/static/');
  if (!isStaticLib && !isOwnStatic) return; // driver sahifalari/API — doim to'g'ridan-to'g'ri tarmoqdan (jonli ma'lumot)

  // Stale-while-revalidate: keshda bo'lsa darhol shuni qaytaramiz (tezkor —
  // sahifadan sahifaga o'tishda qayta yuklanmaydi), fonda esa yangi nusxa
  // olib keshni yangilaymiz — shu bilan kutubxona versiyasi o'zgarsa ham
  // keyingi safar avtomatik yangilanadi.
  event.respondWith(
    caches.open(STATIC_CACHE).then(cache =>
      cache.match(req).then(cached => {
        const networkFetch = fetch(req).then(res => {
          // Diqqat: CDN manbalari (Tailwind/FontAwesome/Mapbox/Yandex) uchun
          // so'rov cross-origin 'no-cors' rejimida bo'lgani sabab javob
          // "opaque" (status har doim 0, tarkibi o'qib bo'lmaydi) keladi —
          // bu normal holat, shunday bo'lsa ham keshlash kerak, aks holda
          // hech qachon keshlanmay qoladi.
          if (res && (res.status === 200 || res.type === 'opaque')) cache.put(req, res.clone());
          return res;
        }).catch(() => cached);
        return cached || networkFetch;
      })
    )
  );
});
