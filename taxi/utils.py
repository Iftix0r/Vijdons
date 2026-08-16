import math
import re
import urllib.request
import urllib.parse
import urllib.error
import json
from decimal import Decimal

def reverse_geocode_address(lat, lng):
    """Koordinatadan manzil olish — MapsSettings provider orqali."""
    try:
        from taxi.models import MapsSettings
        maps = MapsSettings.get()
        if maps.provider == MapsSettings.PROVIDER_YANDEX and maps.api_key:
            url = (f'https://geocode-maps.yandex.ru/1.x/?apikey={maps.api_key}'
                   f'&geocode={lng},{lat}&format=json&lang=uz_UZ&results=1')
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            members = data['response']['GeoObjectCollection']['featureMember']
            if members:
                obj = members[0]['GeoObject']
                name = obj.get('name', '')
                desc = obj.get('description', '')
                return f'{name}, {desc}' if name and desc else name or desc
        else:
            url = (f'https://nominatim.openstreetmap.org/reverse'
                   f'?lat={lat}&lon={lng}&format=json&accept-language=uz,ru&zoom=16')
            req = urllib.request.Request(url, headers={'User-Agent': 'VijdonTaxiDriverApp/1.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            addr = data.get('address', {})
            parts = [p for p in [
                addr.get('road') or addr.get('street') or addr.get('residential'),
                addr.get('suburb') or addr.get('neighbourhood') or addr.get('village'),
                addr.get('city') or addr.get('town') or addr.get('county'),
            ] if p]
            return ', '.join(parts) or data.get('display_name', '')
    except Exception:
        return ''


def geocode_search_nominatim(query):
    """Manzil matnidan koordinata(lar) qidiradi (forward geocoding) —
    operator panelining xarita qidiruv qutisi uchun. `MapsSettings.provider`dan
    mustaqil, doim Nominatim (kalitsiz) ishlatadi — panel xaritasi endi
    hech qanday tashqi API kalitiga bog'liq bo'lmasligi kerak.
    O'zbekistonga moslab cheklangan (countrycodes=uz)."""
    try:
        url = ('https://nominatim.openstreetmap.org/search'
               f'?q={urllib.parse.quote(query)}&format=json&limit=6'
               '&countrycodes=uz&accept-language=uz,ru')
        req = urllib.request.Request(url, headers={'User-Agent': 'VijdonTaxiPanel/1.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return [
            {'display_name': d['display_name'], 'lat': float(d['lat']), 'lng': float(d['lon'])}
            for d in data
        ]
    except Exception:
        return []


_PLACE_TYPES_MAIN = {'city', 'town', 'village', 'suburb', 'quarter'}


def geocode_suggest_places_nominatim(region_name, district_name):
    """Berilgan viloyat+tuman nomi bo'yicha Nominatim'dan "asosiy" (shahar/
    qishloq/mahalla darajasidagi, class=place) joylarni qidiradi — TAKLIF
    sifatida, operator "Viloyatlar" bo'limida ko'rib, kerak bo'lganlarini
    tasdiqlab SavedAddress sifatida qo'shadi. Kichik/tasodifiy nuqtalarni
    (isolated_dwelling, locality) chiqarib tashlaydi — faqat kattaroq
    aholi punktlari qoladi. Bo'sh natija — ko'p tumanlar uchun OSM
    ma'lumoti yo'q/kam bo'lishi mumkin, bu XATO EMAS, kutilgan holat."""
    try:
        url = ('https://nominatim.openstreetmap.org/search'
               f'?state={urllib.parse.quote(region_name)}'
               f'&county={urllib.parse.quote(district_name)}'
               '&country=Uzbekistan&format=json&addressdetails=1'
               '&namedetails=1&limit=30&accept-language=uz,ru')
        req = urllib.request.Request(url, headers={'User-Agent': 'VijdonTaxiPanel/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        results = []
        for d in data:
            if d.get('class') != 'place' or d.get('type') not in _PLACE_TYPES_MAIN:
                continue
            name = (d.get('namedetails') or {}).get('name') or d['display_name'].split(',')[0]
            results.append({
                'name': name.strip(), 'display_name': d['display_name'],
                'lat': float(d['lat']), 'lng': float(d['lon']), 'type': d.get('type'),
            })
        return results
    except Exception:
        return []


def capture_order_action_location(order, new_status, original_status, lat, lng):
    """Haydovchi "Yo'lga chiqdim"/"Yetib keldim" tugmasini bosgan paytdagi
    haqiqiy GPS joylashuvini `order`ga yozadi (mutatsiya qiladi, saqlamaydi
    — chaqiruvchi `order.save(update_fields=...)` qiladi). Operator
    panelida va taximetr vidjetida "qaysi manzilda yo'lga chiqilgani/yetib
    kelingani" ko'rsatish uchun.

    `original_status` — DB'ga yozishdan OLDINGI holat: veb ilova ba'zan
    alohida 'arrived' bosqichisiz to'g'ridan-to'g'ri 'on_way' -> 'completed'
    o'tkazadi ("Yetib keldim" tugmasi shu yerda 'complete' amalini
    chaqiradi) — bunday holda ham bosilgan ondagi joylashuv "yetib kelingan
    joy" sifatida saqlanadi.

    Diqqat: manzil NOMI (`on_way_address`/`arrived_address`) shu yerda
    SINXRON hisoblanmaydi — `reverse_geocode_address()` tashqi HTTP so'rov
    (Yandex/Nominatim, 5s gacha) bo'lgani uchun, avval haydovchi "Yo'lga
    chiqdim"/"Yetib keldim"/"Yakunlash" tugmasini bosganda shu javobni
    kutib, bir necha soniya "osilib" qolardi — ayniqsa internet sekin
    bo'lganda. Endi koordinata darhol saqlanadi, manzil NOMI esa fon
    oqimida (`_schedule_reverse_geocode`) keyinroq alohida yoziladi —
    tugma javobi endi geocoder tezligiga bog'liq emas.

    Qaytaradi: yangilangan maydon nomlari ro'yxati (bo'sh bo'lishi mumkin)."""
    if lat is None or lng is None:
        return []
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return []
    if new_status == 'on_way':
        order.on_way_lat = lat
        order.on_way_lng = lng
        _schedule_reverse_geocode(order.pk, 'on_way_address', lat, lng)
        return ['on_way_lat', 'on_way_lng']
    if new_status == 'arrived' or (new_status == 'completed' and original_status == 'on_way' and order.arrived_lat is None):
        order.arrived_lat = lat
        order.arrived_lng = lng
        _schedule_reverse_geocode(order.pk, 'arrived_address', lat, lng)
        return ['arrived_lat', 'arrived_lng']
    return []


def _schedule_reverse_geocode(order_pk, field_name, lat, lng):
    """`reverse_geocode_address()` ni fon oqimida bajaradi va natijani
    to'g'ridan-to'g'ri (alohida) UPDATE bilan yozadi — chaqiruvchining
    `order.save(update_fields=...)` bilan poyga sharoitiga tushmasin uchun
    (u ancha oldin, geocoder javob berishidan oldin tugaydi)."""
    import threading

    def _run():
        address = reverse_geocode_address(lat, lng)
        if address:
            from taxi.models import Order
            Order.objects.filter(pk=order_pk).update(**{field_name: address})

    threading.Thread(target=_run, daemon=True).start()


def reverse_geocode_admin_area(lat, lng):
    """Koordinatadan (viloyat nomi, tuman nomi) juftligini olishga urinadi —
    `reverse_geocode_address` bilan bir xil geocoder javobidan, lekin
    to'liq manzil matni o'rniga hududiy ierarxiya (Yandex `Components`/
    Nominatim `state`+`county`) o'qiladi. SavedAddress avtomatik
    yaratilganda Region/District'ga avtomatik biriktirish uchun ishlatiladi.
    Aniqlab bo'lmasa (ikkalasi ham yoki bittasi) — mos qiymat o'rniga
    `None` qaytaradi, xato emas: chaqiruvchi shu holda manzilni tumansiz
    qoldiradi (operator keyin qo'lda biriktirishi mumkin)."""
    try:
        from taxi.models import MapsSettings
        maps = MapsSettings.get()
        if maps.provider == MapsSettings.PROVIDER_YANDEX and maps.api_key:
            url = (f'https://geocode-maps.yandex.ru/1.x/?apikey={maps.api_key}'
                   f'&geocode={lng},{lat}&format=json&lang=uz_UZ&results=1')
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            members = data['response']['GeoObjectCollection']['featureMember']
            if not members:
                return None, None
            components = (
                members[0]['GeoObject']['metaDataProperty']['GeocoderMetaData']
                .get('Address', {}).get('Components', [])
            )
            region_name = next((c.get('name') for c in components if c.get('kind') in ('region', 'province')), None)
            district_name = next((c.get('name') for c in components if c.get('kind') == 'area'), None)
            return region_name, district_name
        else:
            url = (f'https://nominatim.openstreetmap.org/reverse'
                   f'?lat={lat}&lon={lng}&format=json&accept-language=uz,ru&zoom=10')
            req = urllib.request.Request(url, headers={'User-Agent': 'VijdonTaxiDriverApp/1.0'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            addr = data.get('address', {})
            return addr.get('state'), (addr.get('county') or addr.get('state_district'))
    except Exception:
        return None, None


def _match_region(name):
    """Geocoder qaytargan viloyat nomini bazadagi Region'ga moslashtiradi.
    Avval aniq (case-insensitive) moslik, topilmasa "viloyati"/"shahri"/
    "respublikasi" so'zlarisiz asosiy nom bo'yicha qidiriladi — geocoder
    ba'zan shu qo'shimchalarsiz qaytarishi mumkin (masalan "Andijon"
    "Andijon viloyati" o'rniga)."""
    from taxi.models import Region
    name = (name or '').strip()
    if not name:
        return None
    exact = Region.objects.filter(name__iexact=name).first()
    if exact:
        return exact
    core = name.lower()
    for suffix in ('viloyati', 'shahri', 'respublikasi'):
        core = core.replace(suffix, '')
    core = core.strip()
    if not core:
        return None
    return Region.objects.filter(name__icontains=core).first()


def _resolve_district(region, name):
    """Berilgan Region ostida shu nomli District'ni topadi.

    Diqqat: avval bu yerda topilmasa YANGI District avtomatik YARATILARDI —
    lekin geocoder (ayniqsa Nominatim/OSM, O'zbekiston bo'yicha to'liq
    bo'lmagan chegara ma'lumoti bilan) noto'g'ri/qo'shni tuman nomini
    qaytarsa, bu xato nom TEKSHIRUVSIZ, doimiy ravishda bazaga Tuman
    sifatida yozilib qolardi (masalan "Oqbuloq" nuqtasi uchun "Qirg'izobod"
    kabi). Endi topilmasa `None` qaytariladi — SavedAddress `district=None`
    holda yaratiladi, operator "Manzillar" bo'limida ko'rib, to'g'ri
    tumanni QO'LDA biriktiradi. Yangi Tuman yaratish endi FAQAT operator
    "Viloyatlar" bo'limida ataylab qo'shganda sodir bo'ladi (`district_create`)."""
    from taxi.models import District
    name = (name or '').strip()
    if not name:
        return None
    return District.objects.filter(region=region, name__iexact=name).first()


def haversine(lat1, lon1, lat2, lon2):
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 2 * math.asin(math.sqrt(a)) * 6371


def get_surge_multiplier():
    from taxi.models import Order, Driver
    pending = Order.objects.filter(status='pending').count()
    on_duty = Driver.objects.filter(
        is_active=True, is_on_duty=True, approval_status='approved'
    ).count()
    if on_duty == 0:
        return 1.5, "Haydovchilar kam"
    ratio = pending / on_duty
    if ratio >= 3:
        return 2.0, "Talab juda yuqori"
    elif ratio >= 1.5:
        return 1.5, "Talab yuqori"
    else:
        return 1.0, "Normal"

def find_fairest_driver(drivers, lat, lng, fairness_weight_km=0, max_radius_km=0):
    """Nomzodlar orasidan eng mos haydovchini tanlaydi — sof masofa emas,
    balki har bir nomzod uchun hisoblangan Score bo'yicha (eng kichik Score
    g'olib):

        Score = masofa (km)
                + (bugun yakunlagan buyurtmalari soni * fairness_weight_km)
                - (oxirgi yakunlagan buyurtmasidan beri kutgan daqiqasi * 0.1)

    - Ko'p ishlagan haydovchining "samarali masofasi" oshadi (jarima),
      uzoq kutib turgan haydovchiniki esa kamayadi (bonus) — shu orqali
      band haydovchi hammasini olib ketmaydi, lekin uzoq kutgan haydovchi
      ham tez-tez ustunlik oladi.
    - Hech qachon yakunlagan buyurtmasi bo'lmagan haydovchi uchun kutish
      vaqti 30 daqiqa deb olinadi (o'rtacha, na haddan ortiq ustunlik,
      na kamsitish).
    - max_radius_km berilgan bo'lsa (0 dan katta), shu radiusdan
      uzoqdagi nomzodlar Score hisobida (adolat/kutish bonusi bilan)
      qatnashmaydi — mijozni haddan tashqari uzoq kutdirmaslik uchun
      (adolat mijoz tajribasidan ustun qo'yilmaydi). Lekin agar radius
      ichida HECH KIM topilmasa (masalan haydovchilar hammasi tarqoq
      joylashgan bo'lsa), buyurtma umumiy tabloga (hammaga baravar)
      tashlab yuborilmaydi — shu holatda eng yaqin haydovchiga (adolatni
      hisobga olmay) baribir individual yuboriladi, aks holda mijoz
      hech kim bilan bog'lanmay navbatsiz qolib ketardi.
    - fairness_weight_km=0 bo'lsa — avvalgidek faqat masofa hal qiladi."""
    from django.utils import timezone

    now = timezone.now()
    today = now.date()

    best_driver = None
    best_score = float('inf')
    best_dist = float('inf')
    fallback_driver = None
    fallback_dist = float('inf')

    for driver in drivers:
        if driver.latitude is None or driver.longitude is None:
            continue
        dist = haversine(lat, lng, driver.latitude, driver.longitude)
        if dist is None:
            continue

        # Radius ichida hech kim topilmasa ishlatiladigan zaxira — doim eng
        # yaqinini kuzatib boramiz.
        if dist < fallback_dist:
            fallback_dist = dist
            fallback_driver = driver

        if max_radius_km and dist > max_radius_km:
            continue

        if fairness_weight_km:
            today_orders_count = driver.orders.filter(status='completed', created_at__date=today).count()
            last_order = driver.orders.filter(status='completed').order_by('-updated_at').first()
            idle_minutes = (now - last_order.updated_at).total_seconds() / 60 if last_order else 30
            score = dist + today_orders_count * fairness_weight_km - idle_minutes * 0.1
        else:
            score = dist

        if score < best_score:
            best_score = score
            best_driver = driver
            best_dist = dist

    if best_driver is not None:
        return best_driver, best_dist
    return fallback_driver, fallback_dist


def send_telegram(text, token=None, chat_ids=None, reply_markup=None):
    """Telegram guruh(lar)iga xabar yuborish. Bot qo'shilgan barcha guruhlarga."""
    try:
        from taxi.models import BotSettings
        cfg = BotSettings.get()
        _token = token or cfg.bot_token.strip()
        _ids   = chat_ids or cfg.get_all_group_ids()
    except Exception:
        from django.conf import settings
        _token = token or getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
        _ids   = chat_ids or [getattr(settings, 'TELEGRAM_GROUP_ID', '')]

    if not _token or not _ids:
        return

    for chat_id in _ids:
        if not chat_id:
            continue
        try:
            payload = {
                'chat_id':    chat_id,
                'text':       text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': 'true',
            }
            if reply_markup:
                payload['reply_markup'] = json.dumps(reply_markup)
            data = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{_token}/sendMessage',
                data=data,
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass


def send_telegram_photo(photo_url, caption='', token=None, chat_ids=None, reply_markup=None):
    """Telegram guruh(lar)iga/chat(lar)iga rasm yuborish (masalan to'lov cheki)."""
    try:
        from taxi.models import BotSettings
        cfg = BotSettings.get()
        _token = token or cfg.bot_token.strip()
        _ids   = chat_ids or cfg.get_all_group_ids()
    except Exception:
        _token = token or ''
        _ids   = chat_ids or []

    if not _token or not _ids:
        return

    for chat_id in _ids:
        if not chat_id:
            continue
        try:
            payload = {
                'chat_id':    chat_id,
                'photo':      photo_url,
                'caption':    caption,
                'parse_mode': 'HTML',
            }
            if reply_markup:
                payload['reply_markup'] = json.dumps(reply_markup)
            data = urllib.parse.urlencode(payload).encode()
            req = urllib.request.Request(
                f'https://api.telegram.org/bot{_token}/sendPhoto',
                data=data,
            )
            urllib.request.urlopen(req, timeout=8)
        except Exception:
            pass


def edit_telegram_message(chat_id, message_id, text, token=None, reply_markup=None):
    """Mavjud Telegram xabarini tahrirlash."""
    try:
        from taxi.models import BotSettings
        cfg = BotSettings.get()
        _token = token or cfg.bot_token.strip()
    except Exception:
        _token = token or ''
    if not _token:
        return
    try:
        payload = {
            'chat_id':    chat_id,
            'message_id': message_id,
            'text':       text,
            'parse_mode': 'HTML',
            'disable_web_page_preview': 'true',
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)
        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{_token}/editMessageText',
            data=data,
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass


def _cfg():
    """BotSettings singleton ni qaytaradi."""
    try:
        from taxi.models import BotSettings
        return BotSettings.get()
    except Exception:
        return None


def log_panel_event(event_type, message=''):
    """Operator panel ovozli bildirishnomasi uchun hodisani jurnalga yozadi.
    Telegram notify_* sozlamalaridan mustaqil — shuning uchun har doim, tekshiruvdan oldin chaqiriladi."""
    try:
        from taxi.models import PanelEvent
        PanelEvent.objects.create(event_type=event_type, message=message[:500])
    except Exception:
        pass


DEVELOPER_TELEGRAM_CHAT_ID = '2114098498'


def notify_developer(text):
    """Dasturchining shaxsiy Telegram chatiga (DEVELOPER_TELEGRAM_CHAT_ID) jonli
    xabar yuboradi — asosiy bot tokeni bilan, BotSettings'dagi notify_*
    sozlamalaridan va guruh ro'yxatidan mustaqil."""
    try:
        send_telegram(text, chat_ids=[DEVELOPER_TELEGRAM_CHAT_ID])
    except Exception:
        pass


def log_system_event(event_type, message='', level='info', request=None, user=None, detail=''):
    """Tizim (dasturchi) paneli uchun xavfsizlik/audit yozuvi — PanelEvent'dan
    ATAYLAB alohida (operatorlarning ovozli bildirishnoma feedini
    "iflos"lamasin deb), faqat /system/ panelidagi Jurnal sahifasida ko'rinadi.
    Har bir yozuv, dasturchining shaxsiy Telegram chatiga (DEVELOPER_TELEGRAM_CHAT_ID)
    ham jonli tarzda yuboriladi — BotSettings'dagi notify_* sozlamalaridan mustaqil."""
    try:
        from taxi.models import SystemAuditLog
        ip = None
        path = ''
        if request is not None:
            path = request.path
            xff = request.META.get('HTTP_X_FORWARDED_FOR')
            ip = xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')
            if user is None and request.user.is_authenticated:
                user = request.user
        SystemAuditLog.objects.create(
            event_type=event_type, message=message[:500], level=level,
            user=user, ip_address=ip, path=path[:300], detail=detail,
        )
    except Exception:
        pass

    try:
        from django.utils import timezone
        icon = {'error': '❌', 'warning': '⚠️'}.get(level, 'ℹ️')
        lines = [
            f"{icon} <b>Tizim jurnali</b>",
            f"Turi: <code>{event_type}</code>",
        ]
        if message:
            lines.append(f"Xabar: {message}")
        if user is not None:
            lines.append(f"Foydalanuvchi: {getattr(user, 'username', user)}")
        if ip:
            lines.append(f"IP: {ip}")
        if path:
            lines.append(f"Manzil: {path}")
        lines.append(f"Vaqt: {timezone.now():%d.%m.%Y %H:%M:%S}")
        notify_developer('\n'.join(lines))
    except Exception:
        pass


# ── Guruh jonli ovozli aloqa ("efir") — umumiy yordamchilar ─────────────────
# Haydovchi (taxi/driver_views.py) va operator panel (taxi/views.py) tomonlari
# bir xil "efir" xonasini ulashadi, shuning uchun ikkalasi ham shu funksiyalardan
# foydalanadi. Ishtirokchi kaliti — 'd<driver_id>' yoki 'o<user_id>' shaklidagi
# satr (masalan 'd5', 'o3') — frontend JS uchun bitta tekis ID makonini
# ta'minlaydi, backend esa prefiksga qarab qaysi FK (driver/operator) ekanini biladi.
#
# ── Eskiz.uz SMS ──────────────────────────────────────────────────────────────

def normalize_phone_uz(raw):
    """Telefon raqamni Eskiz uchun 998XXXXXXXXX (9 xonali, kod bilan 12 xona) formatiga keltiradi."""
    digits = ''.join(ch for ch in (raw or '') if ch.isdigit())
    if digits.startswith('00998'):
        digits = digits[2:]
    if digits.startswith('998') and len(digits) == 12:
        return digits
    if len(digits) == 9:
        return '998' + digits
    return None


def _eskiz_login(cfg):
    """Eskiz.uz'dan yangi auth token oladi va DB'ga saqlaydi."""
    if not cfg.email or not cfg.password:
        return ''
    try:
        from django.utils import timezone
        data = urllib.parse.urlencode({'email': cfg.email, 'password': cfg.password}).encode()
        req = urllib.request.Request('https://notify.eskiz.uz/api/auth/login', data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode())
        token = result.get('data', {}).get('token', '')
        if token:
            cfg.token = token
            cfg.token_updated_at = timezone.now()
            cfg.save(update_fields=['token', 'token_updated_at'])
        return token
    except Exception:
        return ''


def notify_sms_gateway(message):
    """SMS-shlyuz qurilmalariga (vijdon_sms_gateway, mahalliy SIM orqali
    yuboruvchi Android ilova) navbatga yangi xabar qo'shilgani haqida
    push yuboradi. Bir nechta qurilma bo'lsa, barchasiga yuboriladi —
    qaysi biri birinchi bo'sh bo'lsa, o'sha `pending/` so'rovida shu
    xabarni ko'radi va oladi (tabiiy yuk taqsimlash, alohida "biriktirish"
    mantig'i shart emas)."""
    from taxi.models import SmsGatewayToken
    for token in SmsGatewayToken.objects.values_list('fcm_token', flat=True):
        send_fcm(
            token, title='Yangi SMS', body=message.phone_number,
            data={'type': 'new_sms', 'message_id': str(message.id)},
        )


def send_sms(phone, text):
    """Mijozga/haydovchiga SMS yuboradi. `SmsSettings.provider`ga qarab:
    - Eskiz.uz orqali (standart, pullik), YOKI
    - PROVIDER_LOCAL_GATEWAY bo'lsa — Eskiz'ga umuman murojaat qilinmaydi,
      xabar navbatga (`SmsGatewayMessage`) yozib qo'yiladi, haqiqiy
      yuborishni vijdon_sms_gateway ilovasi o'rnatilgan telefon o'zining
      SIM kartasi orqali bajaradi (`notify_sms_gateway`, yuqorida).
      Diqqat: bu holda funksiya SMS haqiqatan YETIB BORGANINI emas, faqat
      NAVBATGA QO'YILGANINI bildiradi — chunki haqiqiy yuborish
      asinxron, boshqa qurilmada sodir bo'ladi.
    (ok, message) qaytaradi."""
    try:
        from taxi.models import SmsSettings
        cfg = SmsSettings.get()
    except Exception:
        return False, 'SMS sozlamalari topilmadi'

    mobile = normalize_phone_uz(phone)
    if not mobile:
        return False, f"Telefon raqam formati noto'g'ri: {phone}"

    if cfg.provider == SmsSettings.PROVIDER_LOCAL_GATEWAY:
        from taxi.models import SmsGatewayMessage
        message = SmsGatewayMessage.objects.create(phone_number=mobile, text=text)
        notify_sms_gateway(message)
        return True, "Navbatga qo'shildi (mahalliy SIM orqali yuboriladi)"

    if not cfg.email or not cfg.password:
        return False, "Eskiz email/parol kiritilmagan"

    token = cfg.token or _eskiz_login(cfg)
    if not token:
        return False, 'Eskiz tokeni olinmadi — email/parolni tekshiring'

    def _send(tok):
        payload = json.dumps({
            'mobile_phone': mobile,
            'message': text,
            'from': cfg.nickname or '4546',
        }).encode()
        req = urllib.request.Request(
            'https://notify.eskiz.uz/api/message/sms/send',
            data=payload,
            headers={'Authorization': f'Bearer {tok}', 'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status

    try:
        _send(token)
        return True, 'SMS yuborildi'
    except urllib.error.HTTPError as e:
        if e.code == 401:
            # Token muddati o'tgan bo'lishi mumkin — qayta login qilib bir marta urinib ko'ramiz
            new_token = _eskiz_login(cfg)
            if new_token:
                try:
                    _send(new_token)
                    return True, 'SMS yuborildi'
                except Exception as e2:
                    return False, f'Eskiz xatoligi: {e2}'
            return False, 'Eskiz tokeni yaroqsiz — email/parolni tekshiring'
        return False, f'Eskiz xatoligi: {e}'
    except Exception as e:
        return False, f'Xatolik: {e}'


CLIENT_BOT_PROMO_LINK = 't.me/vijdon1351bot'


def sms_order_status(order, event):
    """Mijozga buyurtma holati o'zgarganda SMS yuboradi.
    event: 'accepted' | 'arrived' | 'completed' | 'cancelled'"""
    try:
        from taxi.models import SmsSettings
        cfg = SmsSettings.get()
    except Exception:
        return

    toggle = {
        'accepted':  cfg.sms_accepted,
        'arrived':   cfg.sms_arrived,
        'completed': cfg.sms_completed,
        'cancelled': cfg.sms_cancelled,
    }.get(event)
    if not toggle:
        return

    client = getattr(order, 'client', None)
    if not client or not client.phone_number:
        return

    driver = getattr(order, 'driver', None)
    if event == 'accepted':
        car = f"{driver.car_model} {driver.car_number}".strip() if driver else ''
        text = (f"Vijdon Taxi: Buyurtmangiz (#{order.id}) qabul qilindi."
                + (f" Haydovchi: {driver.full_name}, {car}, tel: {driver.phone_number}." if driver else "")
                + " Iltimos kuting.")
    elif event == 'arrived':
        text = (f"Vijdon Taxi: Haydovchi{f' ({driver.full_name})' if driver else ''} "
                f"manzilingizga yetib keldi. Buyurtma #{order.id}.")
    elif event == 'completed':
        text = (f"Vijdon Taxi: Buyurtmangiz (#{order.id}) yakunlandi. "
                f"Narxi: {order.price or '—'} so'm. Xizmatimizdan foydalanganingiz uchun rahmat! "
                f"Keyingi safar Telegram orqali ham buyurtma bering: {CLIENT_BOT_PROMO_LINK}")
    else:  # cancelled
        text = (f"Vijdon Taxi: Buyurtmangiz (#{order.id}) bekor qilindi. "
                f"Telegram orqali ham buyurtma berishingiz mumkin: {CLIENT_BOT_PROMO_LINK}")

    send_sms(client.phone_number, text)


def match_driver_or_client_by_phone(phone):
    """Berilgan telefon raqamiga (turli formatda bo'lishi mumkin — +998,
    998, oldindagi nollar bilan/nolsiz) mos Driver yoki Client'ni oxirgi
    9 raqam (mamlakat kodisiz obunachi raqami) bo'yicha topadi. Formatlash
    farqlaridan qat'i nazar ishonchli moslashtirish uchun."""
    from taxi.models import Driver, Client
    digits = ''.join(ch for ch in (phone or '') if ch.isdigit())
    last9 = digits[-9:]
    if not last9:
        return None, None
    driver = Driver.objects.filter(phone_number__endswith=last9).first()
    if driver:
        return driver, None
    client = Client.objects.filter(phone_number__endswith=last9).first()
    return None, client


SMS_OPT_OUT_KEYWORDS = {"BEKOR", "STOP", "TO'XTAT", "TOXTAT"}


def handle_sms_opt_out_keyword(phone, text):
    """Kelgan SMS matni "BEKOR"/"STOP" kabi kalit so'zlardan biriga teng
    bo'lsa — mos Driver/Client'ni ommaviy (marketing) SMS'lardan chiqarib
    qo'yadi va bir martalik tasdiq SMS'i yuboradi. Buyurtma/balans kabi
    tranzaksion SMS'larga TA'SIR QILMAYDI."""
    normalized = (text or '').strip().upper().replace('’', "'").replace('ʻ', "'")
    if normalized not in SMS_OPT_OUT_KEYWORDS:
        return
    driver, client = match_driver_or_client_by_phone(phone)
    person = driver or client
    if not person or person.sms_opt_out:
        return
    person.sms_opt_out = True
    person.save(update_fields=['sms_opt_out'])
    send_sms(phone, "Vijdon Taxi: Siz ommaviy SMS xabarlaridan chiqdingiz. Buyurtma holati haqidagi xabarlar davom etadi.")


def sms_driver_event(driver, event, order=None, amount=None):
    """Haydovchiga turli hodisalar bo'yicha SMS yuboradi — push/Telegram'ga
    QO'SHIMCHA (ularni almashtirmaydi), internet yo'q/sekin bo'lgan paytda
    ham yetib borishi uchun.
    event: 'order_cancelled' | 'new_order' | 'low_balance' | 'topup_approved'"""
    if not driver or not driver.phone_number:
        return
    try:
        from taxi.models import SmsSettings
        cfg = SmsSettings.get()
    except Exception:
        return

    toggle = {
        'order_cancelled':  cfg.sms_driver_cancelled,
        'new_order':        cfg.sms_driver_new_order,
        'low_balance':      cfg.sms_driver_low_balance,
        'topup_approved':   cfg.sms_driver_topup_approved,
    }.get(event)
    if not toggle:
        return

    if event == 'order_cancelled':
        text = f"Vijdon Taxi: Buyurtma #{order.id} bekor qilindi/qayta ochildi."
        if amount:
            text += f" {amount} so'm balansingizga qaytarildi."
    elif event == 'new_order':
        text = f"Vijdon Taxi: Yangi buyurtma! {order.from_address}"
        if order.to_address:
            text += f" → {order.to_address}"
        text += ". Ilovada ko'ring."
    elif event == 'low_balance':
        from taxi.models import TariffSettings
        tariff = TariffSettings.get()
        text = (f"Vijdon Taxi: Balansingiz kam ({driver.balance} so'm). Yangi buyurtma qabul qilish "
                f"uchun kamida {tariff.commission} so'm to'ldiring.")
    else:  # topup_approved
        text = f"Vijdon Taxi: Balansingiz {amount} so'mga to'ldirildi. Joriy balans: {driver.balance} so'm."

    send_sms(driver.phone_number, text)


# ── Telegram xabar shablonlari ────────────────────────────────────────────────

def _order_url(order_id):
    from django.conf import settings
    base = getattr(settings, 'SITE_URL', '').rstrip('/')
    return f'{base}/panel/orders/{order_id}/'


def _driver_url(driver_id):
    from django.conf import settings
    base = getattr(settings, 'SITE_URL', '').rstrip('/')
    return f'{base}/panel/drivers/{driver_id}/detail/'


def _driver_app_url():
    from django.conf import settings
    base = getattr(settings, 'SITE_URL', '').rstrip('/')
    return f'{base}/driver/home/'


def _order_inline(order_id):
    return {'inline_keyboard': [[{'text': '🔍 Batafsil', 'url': _order_url(order_id)}]]}


def _driver_inline(driver_id):
    return {'inline_keyboard': [[{'text': '👤 Haydovchi', 'url': _driver_url(driver_id)}]]}


def _driver_group_inline():
    return {'inline_keyboard': [[{'text': '📱 Ilovaga kirish', 'url': _driver_app_url()}]]}


def _notify_driver_group(text, reply_markup=None):
    """Haydovchilar guruhi(lari)ga xabar yuboradi — cfg.notify_driver_group yoqilgan
    va kamida bitta guruh ID kiritilgan bo'lsa."""
    cfg = _cfg()
    if not cfg or not cfg.notify_driver_group:
        return
    ids = cfg.get_all_driver_group_ids()
    if not ids:
        return
    send_telegram(text, chat_ids=ids, reply_markup=reply_markup or _driver_group_inline())


def tg_order_creating():
    """Operator buyurtma oynasini ochib, ma'lumot to'ldirayotganda haydovchi
    ilovasiga (in-app toast) ogohlantiruvchi xabar yuboradi — buyurtma hali
    yaratilmagan bo'lsa ham. Diqqat: Telegram haydovchilar guruhiga xabar
    endi yuborilmaydi (so'rov bo'yicha olib tashlandi)."""
    from django.utils import timezone
    cfg = _cfg()
    if cfg:
        cfg.last_order_creating_at = timezone.now()
        cfg.save(update_fields=['last_order_creating_at'])


def tg_new_order(order):
    log_panel_event('panel_new_order', f"Buyurtma #{order.id} — {order.from_address}")
    cfg = _cfg()
    client = order.client

    if not cfg or cfg.notify_new_order:
        lines = [
            f"🚨 <b>Yangi buyurtma #{order.id}</b>",
            f"👤 Mijoz: {client.full_name or '—'} | <code>{client.phone_number}</code>",
            f"📍 Qayerdan: <b>{order.from_address}</b>",
        ]
        if order.to_address:
            lines.append(f"🏁 Qayerga: <b>{order.to_address}</b>")
        if order.distance_km:
            lines.append(f"📏 Masofa: {order.distance_km:.1f} km")
        if order.price:
            lines.append(f"💰 Narx: <b>{order.price} UZS</b>")
        lines.append(f"💳 To'lov: {'Naqd 💵' if order.payment_type == 'cash' else 'Karta 💳'}")
        if order.note:
            lines.append(f"📝 Izoh: {order.note}")
        lines.append(f"🕐 Vaqt: {order.created_at.strftime('%d.%m.%Y %H:%M') if order.created_at else '—'}")
        send_telegram('\n'.join(lines), reply_markup=_order_inline(order.id))

    # Haydovchilar guruhiga — telefon raqamisiz, mijoz tarixi bilan
    completed = client.orders.filter(status='completed').count()
    cancelled = client.orders.filter(status='cancelled').count()
    d_lines = [
        f"🚨 <b>Yangi buyurtma #{order.id}</b>",
        f"👤 Mijoz: <b>{client.full_name or 'Nomaʻlum mijoz'}</b>",
        f"📍 Qayerdan: <b>{order.from_address}</b>",
    ]
    if order.to_address:
        d_lines.append(f"🏁 Qayerga: <b>{order.to_address}</b>")
    if order.distance_km:
        d_lines.append(f"📏 Masofa: {order.distance_km:.1f} km")
    if order.price:
        d_lines.append(f"💰 Narx: <b>{order.price} UZS</b>")
    d_lines.append(f"💳 To'lov: {'Naqd 💵' if order.payment_type == 'cash' else 'Karta 💳'}")
    if order.note:
        d_lines.append(f"📝 Izoh: {order.note}")
    d_lines.append(f"✅ Yakunlagan: {completed} ta | ❌ Bekor qilgan: {cancelled} ta")
    _notify_driver_group('\n'.join(d_lines))

    if not order.driver_id:
        notify_operators(
            'Yangi buyurtma',
            f"#{order.id} — {order.from_address}" + (f" → {order.to_address}" if order.to_address else ''),
            data={'type': 'new_order', 'order_id': str(order.id)},
        )


def tg_order_dispatched(order, driver):
    cfg = _cfg()
    if cfg and not cfg.notify_dispatched:
        return
    markup = {'inline_keyboard': [[
        {'text': '🔍 Buyurtma', 'url': _order_url(order.id)},
        {'text': '👤 Haydovchi', 'url': _driver_url(driver.id)},
    ]]}
    send_telegram(
        f"📡 <b>Buyurtma #{order.id} yuborildi</b>\n"
        f"🚗 Haydovchi: <b>{driver.full_name}</b> | <code>{driver.car_number}</code>\n"
        f"📍 {order.from_address}",
        reply_markup=markup,
    )


def tg_client_message(chat_id, text):
    """Mijoz botidan (client_bot_token) mijozga to'g'ridan-to'g'ri xabar yuboradi.
    Mijoz mijoz botidan buyurtma bermagan bo'lsa (chat_id yo'q) yoki bot
    sozlanmagan bo'lsa, jimgina hech narsa qilmaydi."""
    if not chat_id:
        return
    from taxi.models import BotSettings
    token = BotSettings.get().client_bot_token.strip()
    if not token:
        return
    import urllib.request, urllib.parse
    payload = urllib.parse.urlencode({'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}).encode()
    try:
        urllib.request.urlopen(f'https://api.telegram.org/bot{token}/sendMessage', data=payload, timeout=5)
    except Exception:
        pass


def tg_order_accepted(order, driver):
    cfg = _cfg()
    if not cfg or cfg.notify_accepted:
        markup = {'inline_keyboard': [[
            {'text': '🔍 Buyurtma', 'url': _order_url(order.id)},
            {'text': '👤 Haydovchi', 'url': _driver_url(driver.id)},
        ]]}
        send_telegram(
            f"✅ <b>Buyurtma #{order.id} qabul qilindi</b>\n"
            f"🚗 <b>{driver.full_name}</b> | {driver.car_model} <code>{driver.car_number}</code>\n"
            f"👤 {order.client.full_name or '—'} | <code>{order.client.phone_number}</code>\n"
            f"📍 {order.from_address}" + (f" → {order.to_address}" if order.to_address else "") + "\n"
            f"💰 {order.price or '—'} UZS",
            reply_markup=markup,
        )

    # Haydovchilar guruhiga — buyurtma band bo'lganini va kim qabul qilganini bildiradi
    _notify_driver_group(
        f"✅ <b>Buyurtma #{order.id} band qilindi</b>\n"
        f"🚗 Qabul qildi: <b>{driver.full_name}</b> | {driver.car_model} <code>{driver.car_number}</code>"
    )

    # Mijozga — agar mijoz bot orqali buyurtma bergan bo'lsa, haydovchi
    # ma'lumotlarini shu yerdan ham yuboramiz
    client = getattr(order, 'client', None)
    tg_client_message(
        getattr(client, 'telegram_chat_id', ''),
        f"✅ <b>Buyurtmangiz qabul qilindi!</b>\n"
        f"🚗 Haydovchi: <b>{driver.full_name}</b>\n"
        f"📞 Tel: <code>{driver.phone_number}</code>\n"
        f"🚘 Mashina: {driver.car_model} <code>{driver.car_number}</code>\n"
        f"⏳ Haydovchi tez orada yetib keladi."
    )


def tg_order_on_way(order, driver):
    log_panel_event('panel_order_on_way', f"Buyurtma #{order.id} — {driver.full_name}")
    cfg = _cfg()
    if cfg and not cfg.notify_on_way:
        return
    markup = {'inline_keyboard': [[
        {'text': '🔍 Buyurtma', 'url': _order_url(order.id)},
        {'text': '👤 Haydovchi', 'url': _driver_url(driver.id)},
    ]]}
    send_telegram(
        f"🚗 <b>Haydovchi yo'lda — #{order.id}</b>\n"
        f"🚗 <b>{driver.full_name}</b> | <code>{driver.car_number}</code>\n"
        f"👤 {order.client.full_name or '—'} | <code>{order.client.phone_number}</code>",
        reply_markup=markup,
    )


def tg_order_arrived(order, driver):
    log_panel_event('panel_order_arrived', f"Buyurtma #{order.id} — {driver.full_name}")
    cfg = _cfg()
    if cfg and not cfg.notify_arrived:
        return
    markup = {'inline_keyboard': [[
        {'text': '🔍 Buyurtma', 'url': _order_url(order.id)},
        {'text': '👤 Haydovchi', 'url': _driver_url(driver.id)},
    ]]}
    send_telegram(
        f"📍 <b>Haydovchi yetib keldi — #{order.id}</b>\n"
        f"🚗 <b>{driver.full_name}</b> | <code>{driver.car_number}</code> kutmoqda\n"
        f"👤 {order.client.full_name or '—'} | <code>{order.client.phone_number}</code>",
        reply_markup=markup,
    )


def tg_order_completed(order, driver):
    log_panel_event('panel_order_completed', f"Buyurtma #{order.id} — {driver.full_name}")
    _check_driver_milestone(driver)
    cfg = _cfg()
    if cfg and not cfg.notify_completed:
        return
    markup = {'inline_keyboard': [[
        {'text': '🔍 Buyurtma', 'url': _order_url(order.id)},
        {'text': '👤 Haydovchi', 'url': _driver_url(driver.id)},
    ]]}
    send_telegram(
        f"🏁 <b>Buyurtma yakunlandi — #{order.id}</b>\n"
        f"🚗 <b>{driver.full_name}</b> | <code>{driver.car_number}</code>\n"
        f"👤 {order.client.full_name or '—'} | <code>{order.client.phone_number}</code>\n"
        f"📍 {order.from_address}" + (f" → {order.to_address}" if order.to_address else "") + "\n"
        f"💰 {order.price or '—'} UZS | 📏 {f'{order.distance_km:.1f} km' if order.distance_km else '—'}",
        reply_markup=markup,
    )


def tg_order_cancelled(order, driver, reassigned=False):
    log_panel_event('panel_order_cancelled', f"Buyurtma #{order.id} — {driver.full_name}")
    cfg = _cfg()
    if cfg and not cfg.notify_cancelled:
        return
    reason_line = f"\n📝 Sabab: {order.cancel_reason}" if order.cancel_reason else ""
    reassign_line = "\n🔁 Boshqa haydovchilarga qayta yuborilmoqda" if reassigned else ""
    markup = {'inline_keyboard': [[
        {'text': '🔍 Buyurtma', 'url': _order_url(order.id)},
        {'text': '👤 Haydovchi', 'url': _driver_url(driver.id)},
    ]]}
    send_telegram(
        f"❌ <b>Buyurtma bekor qilindi — #{order.id}</b>\n"
        f"🚗 Haydovchi: <b>{driver.full_name}</b>\n"
        f"👤 {order.client.full_name or '—'} | <code>{order.client.phone_number}</code>\n"
        f"📍 {order.from_address}"
        f"{reason_line}{reassign_line}",
        reply_markup=markup,
    )
    # Diqqat: haydovchilar guruhiga bu haqda endi xabar yuborilmaydi
    # (so'rov bo'yicha olib tashlandi) — faqat operator/admin kanaliga
    # yuqoridagi xabar boradi.


def tg_order_rejected(order, driver):
    log_panel_event('panel_order_rejected', f"Buyurtma #{order.id} — {driver.full_name} rad etdi")
    cfg = _cfg()
    if cfg and not cfg.notify_rejected:
        return
    send_telegram(
        f"🔄 <b>Buyurtma #{order.id} rad etildi</b>\n"
        f"🚗 <b>{driver.full_name}</b> rad etdi\n"
        f"📍 {order.from_address}",
        reply_markup=_order_inline(order.id),
    )


def tg_order_deleted(order):
    # Diqqat: log_panel_event bu yerda CHAQIRILMAYDI — chaqiruvchi (order_delete
    # view'i) buyurtmani o'chirishdan oldin buni allaqachon o'zi yozadi, aks
    # holda panel ovozli bildirishnomasi feedida ikkita bir xil yozuv paydo bo'lardi.
    cfg = _cfg()
    if cfg and not cfg.notify_deleted:
        return
    lines = [f"🗑️ <b>Buyurtma o'chirildi — #{order.id}</b>"]
    if order.driver_id:
        lines.append(f"🚗 Haydovchi: <b>{order.driver.full_name}</b>")
    lines.append(f"👤 {order.client.full_name or '—'} | <code>{order.client.phone_number}</code>")
    lines.append(f"📍 {order.from_address}" + (f" → {order.to_address}" if order.to_address else ""))
    send_telegram('\n'.join(lines))


def tg_driver_registered(driver):
    log_panel_event('panel_driver_registered', f"{driver.full_name} | {driver.phone_number}")
    cfg = _cfg()
    if cfg and not cfg.notify_driver_register:
        return
    markup = {'inline_keyboard': [[
        {'text': '✅ Tasdiqlash', 'url': _driver_url(driver.id)},
    ]]}
    send_telegram(
        f"🆕 <b>Yangi haydovchi ro'yxatdan o'tdi</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>\n"
        f"🚗 {driver.car_model} | <code>{driver.car_number}</code>\n"
        f"⏳ Tasdiqlash kutilmoqda",
        reply_markup=markup,
    )


def tg_driver_approved(driver):
    log_panel_event('panel_driver_approved', f"{driver.full_name} | {driver.phone_number}")
    cfg = _cfg()
    if cfg and not cfg.notify_driver_approved:
        return
    send_telegram(
        f"✅ <b>Haydovchi tasdiqlandi</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>\n"
        f"🚗 {driver.car_model} | <code>{driver.car_number}</code>",
        reply_markup=_driver_inline(driver.id),
    )


def tg_driver_rejected(driver):
    log_panel_event('panel_driver_rejected', f"{driver.full_name} | {driver.phone_number}")
    cfg = _cfg()
    if cfg and not cfg.notify_driver_rejected:
        return
    send_telegram(
        f"🚫 <b>Haydovchi rad etildi</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>",
        reply_markup=_driver_inline(driver.id),
    )


def tg_driver_blocked(driver):
    log_panel_event('panel_driver_blocked', f"{driver.full_name} — bloklandi")
    cfg = _cfg()
    if cfg and not cfg.notify_driver_blocked:
        return
    send_telegram(
        f"🔒 <b>Haydovchi bloklandi</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>\n"
        f"🚗 {driver.car_model} | <code>{driver.car_number}</code>",
        reply_markup=_driver_inline(driver.id),
    )


def tg_driver_unblocked(driver):
    log_panel_event('panel_driver_blocked', f"{driver.full_name} — blokdan chiqarildi")
    cfg = _cfg()
    if cfg and not cfg.notify_driver_blocked:
        return
    send_telegram(
        f"🔓 <b>Haydovchi bloki ochildi</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>",
        reply_markup=_driver_inline(driver.id),
    )


def tg_driver_login(driver, ip=None):
    cfg = _cfg()
    if cfg and not cfg.notify_driver_login:
        return
    send_telegram(
        f"🔑 <b>Haydovchi kirdi</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>\n"
        + (f"🌐 IP: <code>{ip}</code>" if ip else ""),
        reply_markup=_driver_inline(driver.id),
    )


def tg_balance_changed(driver, amount, action):
    sign = '+' if action == 'add' else '-'
    log_panel_event('panel_balance_changed', f"{driver.full_name} — {sign}{amount} UZS")
    cfg = _cfg()
    if cfg and not cfg.notify_balance_changed:
        return
    emoji = '💚' if action == 'add' else '🔴'
    text = (
        f"{emoji} <b>Balans o'zgardi</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>\n"
        f"💰 {sign}{amount} UZS\n"
        f"📊 Joriy balans: <b>{driver.balance} UZS</b>"
    )
    send_telegram(text, reply_markup=_driver_inline(driver.id))

    # Balans to'ldirilganda haydovchilar guruhiga ham xabar beriladi
    if action == 'add' and cfg and cfg.notify_balance_changed_to_driver_group:
        _notify_driver_group(
            f"💚 <b>Balans to'ldirildi</b>\n"
            f"👤 <b>{driver.full_name}</b>\n"
            f"💰 +{amount} UZS"
        )


def tg_low_balance_alert(driver):
    """Komissiya yechilgandan keyin balans yetarli bo'lmasa (haydovchi endi
    yangi buyurtma qabul qila olmaydi/navbatga kira olmaydi), adminni ogohlantiradi."""
    from taxi.models import TariffSettings
    tariff = TariffSettings.get()
    if driver.balance >= tariff.commission:
        return
    log_panel_event('panel_low_balance', f"{driver.full_name} — balans kam: {driver.balance} UZS")

    from taxi.driver_views import send_push_to_driver
    send_push_to_driver(
        driver, '⚠️ Balans kam',
        f"Balansingiz {driver.balance} UZS. Yangi buyurtma qabul qilish uchun kamida {tariff.commission} UZS kerak — iltimos to'ldiring.",
    )

    # SMS har buyurtma qabul qilinganda emas — bir necha soatda bir marta
    # (aks holda balans kam bo'lgan holatda haydovchi har safar buyurtma
    # qabul qilganda qayta-qayta SMS olib, katta hajm/xarajat/SIM-blok
    # xavfini oshirar edi).
    from django.utils import timezone
    from datetime import timedelta
    LOW_BALANCE_SMS_THROTTLE = timedelta(hours=6)
    if not driver.low_balance_sms_at or timezone.now() - driver.low_balance_sms_at > LOW_BALANCE_SMS_THROTTLE:
        sms_driver_event(driver, 'low_balance')
        driver.low_balance_sms_at = timezone.now()
        driver.save(update_fields=['low_balance_sms_at'])

    cfg = _cfg()
    if cfg and not cfg.notify_low_balance:
        return
    send_telegram(
        f"⚠️ <b>Balans kam</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>\n"
        f"💰 Joriy balans: <b>{driver.balance} UZS</b> (komissiya: {tariff.commission} UZS)\n"
        f"Haydovchi endi yangi buyurtma qabul qila olmaydi.",
        reply_markup=_driver_inline(driver.id),
    )

    # Balans kam qolganda haydovchilar guruhiga ham xabar beriladi
    if cfg and cfg.notify_low_balance_to_driver_group:
        _notify_driver_group(
            f"⚠️ <b>Balans kam</b>\n"
            f"👤 <b>{driver.full_name}</b>\n"
            f"💰 Joriy balans: <b>{driver.balance} UZS</b> (komissiya: {tariff.commission} UZS)"
        )


def tg_topup_request(request_obj, receipt_url):
    """Haydovchi balans to'ldirish uchun chek yuklaganda adminlarga rasm bilan xabar yuboradi."""
    driver = request_obj.driver
    log_panel_event('panel_topup_request', f"{driver.full_name} — {request_obj.amount} UZS to'lov cheki")
    caption = (
        f"💳 <b>Balans to'ldirish so'rovi #{request_obj.id}</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>\n"
        f"💰 So'ralgan summa: <b>{request_obj.amount} UZS</b>\n\n"
        f"Tasdiqlash uchun operator botga: /tolovtasdiq {request_obj.id}\n"
        f"Rad etish uchun: /tolovrad {request_obj.id}"
    )
    send_telegram_photo(receipt_url, caption=caption)

    try:
        from taxi.models import BotAdmin
        cfg = _cfg()
        admin_ids = list(BotAdmin.objects.filter(is_active=True).values_list('chat_id', flat=True))
        if cfg and admin_ids:
            send_telegram_photo(receipt_url, caption=caption, token=cfg.bot_token.strip(), chat_ids=admin_ids)
    except Exception:
        pass

    notify_operators(
        "Yangi to'lov so'rovi",
        f"{driver.full_name} — {request_obj.amount} UZS",
        data={'type': 'topup_request', 'topup_id': str(request_obj.id)},
    )


def tg_duty_changed(driver, is_on_duty):
    cfg = _cfg()
    if cfg and not cfg.notify_duty_changed:
        return
    emoji = '🟢' if is_on_duty else '🔴'
    status = 'Navbatga kirdi' if is_on_duty else 'Navbatdan chiqdi'
    send_telegram(
        f"{emoji} <b>{status}</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>\n"
        f"🚗 {driver.car_model} | <code>{driver.car_number}</code>",
        reply_markup=_driver_inline(driver.id),
    )


def tg_morning_greeting():
    """Har kuni ertalab haydovchilar guruhiga iliq salomlashuv xabari yuboradi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_morning_greeting:
        return
    from django.utils import timezone
    from taxi.models import Driver
    today = timezone.localtime().strftime('%d.%m.%Y')
    on_duty = Driver.objects.filter(is_active=True, is_on_duty=True, approval_status='approved').count()
    text = (
        "🌅 <b>Xayrli tong, aziz haydovchilar!</b>\n\n"
        "Yangi kun — yangi yo'llar, yangi baraka! Bugun ham xushmuomalalik va ehtiyotkorlik bilan "
        "yo'lovchilarni tashib, yaxshi kayfiyatda ishlang.\n"
        "Yo'lda omad va xavfsizlik tilaymiz! 🚕💐\n\n"
        f"📅 {today} | 🟢 Hozir navbatda: <b>{on_duty}</b> haydovchi"
    )
    _notify_driver_group(text)


def _top_drivers_for_period(date_from, date_to):
    """`date_from`—`date_to` (ikkalasi ham kiritiladi) oralig'ida yakunlangan
    buyurtmalar soni bo'yicha TOP-10 haydovchilarni qaytaradi."""
    from django.db.models import Count, Sum, Q
    from taxi.models import Driver

    return (
        Driver.objects.filter(is_active=True)
        .annotate(
            completed=Count('orders', filter=Q(
                orders__status='completed',
                orders__created_at__date__gte=date_from,
                orders__created_at__date__lte=date_to,
            )),
            earned=Sum('orders__price', filter=Q(
                orders__status='completed',
                orders__created_at__date__gte=date_from,
                orders__created_at__date__lte=date_to,
            )),
        )
        .filter(completed__gt=0)
        .order_by('-completed')[:10]
    )


def _format_top_drivers(title, subtitle, top):
    medals = ['🥇', '🥈', '🥉']
    lines = [f"🏆 <b>{title}</b>", subtitle, ""]
    for i, d in enumerate(top):
        rank = medals[i] if i < 3 else f"{i + 1}."
        earned = d.earned or 0
        lines.append(f"{rank} <b>{d.full_name}</b> — {d.completed} ta buyurtma | {earned:,.0f} UZS".replace(',', ' '))
    return lines


def tg_evening_top_drivers():
    """Kechqurun haydovchilar guruhiga o'sha kunning eng ko'p ishlagan TOP-10
    haydovchilari ro'yxatini yuboradi (yakunlangan buyurtmalar soni bo'yicha)."""
    cfg = _cfg()
    if not cfg or not cfg.notify_evening_top_drivers:
        return
    from django.utils import timezone

    today = timezone.localdate()
    top = _top_drivers_for_period(today, today)
    if not top:
        return
    lines = _format_top_drivers("Bugungi TOP-10 haydovchilar", f"📅 {today.strftime('%d.%m.%Y')}", top)
    lines.append("\nAjoyib mehnat uchun rahmat! Ertaga ham shu ruhda davom etamiz 💪")
    _notify_driver_group('\n'.join(lines))


def tg_weekly_top_drivers():
    """Har hafta yakshanba kuni shu haftaning (dushanbadan bugungi kungacha)
    TOP-10 haydovchilari ro'yxatini yuboradi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_weekly_top_drivers:
        return
    from datetime import timedelta
    from django.utils import timezone

    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    top = _top_drivers_for_period(week_start, today)
    if not top:
        return
    lines = _format_top_drivers(
        "Haftalik TOP-10 haydovchilar",
        f"📅 {week_start.strftime('%d.%m')} — {today.strftime('%d.%m.%Y')}",
        top,
    )
    lines.append("\nShu hafta ajoyib mehnat uchun rahmat! 💪")
    _notify_driver_group('\n'.join(lines))


def tg_monthly_top_drivers():
    """Har oyning oxirgi kuni shu oyning (1-kunidan bugungi kungacha) TOP-10
    haydovchilari ro'yxatini yuboradi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_monthly_top_drivers:
        return
    from django.utils import timezone

    today = timezone.localdate()
    month_start = today.replace(day=1)
    top = _top_drivers_for_period(month_start, today)
    if not top:
        return
    lines = _format_top_drivers("Oylik TOP-10 haydovchilar", f"📅 {month_start.strftime('%m.%Y')}", top)
    lines.append("\nShu oy ajoyib mehnat uchun rahmat! 🏆")
    _notify_driver_group('\n'.join(lines))


def tg_inactive_drivers_report():
    """Bir necha kundir faol bo'lmagan (navbatga chiqmagan) haydovchilar
    ro'yxatini operatorlar guruhiga yuboradi — qayta bog'lanish uchun."""
    cfg = _cfg()
    if not cfg or not cfg.notify_inactive_drivers:
        return
    from datetime import timedelta
    from django.db.models import Q
    from django.utils import timezone
    from taxi.models import Driver

    days = 3
    cutoff = timezone.now() - timedelta(days=days)
    inactive = (
        Driver.objects.filter(is_active=True, approval_status='approved', is_on_duty=False)
        .filter(Q(last_seen__lt=cutoff) | Q(last_seen__isnull=True))
        .order_by('last_seen')[:30]
    )
    if not inactive:
        return

    lines = [f"😴 <b>{days}+ kundan beri faol bo'lmagan haydovchilar</b>", ""]
    for d in inactive:
        last = d.last_seen.strftime('%d.%m.%Y') if d.last_seen else 'hech qachon'
        lines.append(f"👤 <b>{d.full_name}</b> | <code>{d.phone_number}</code> — oxirgi faollik: {last}")
    send_telegram('\n'.join(lines))


FREEZE_INACTIVE_DAYS = 3


def freeze_inactive_drivers():
    """3+ kundan beri onlayn bo'lmagan (last_seen eski yoki umuman
    bo'lmagan) tasdiqlangan haydovchilarni avtomatik muzlatadi — keyingi
    safar ilovaga kirganda 'Hisobingiz muzlatildi' sahifasi ko'rsatiladi,
    qayta ishga tushirish uchun operator/admin blokni ochishi kerak bo'ladi
    (taxi/views.py driver_toggle_frozen)."""
    from datetime import timedelta
    from django.db.models import Q
    from django.utils import timezone
    from taxi.models import Driver, DriverActivityLog

    cutoff = timezone.now() - timedelta(days=FREEZE_INACTIVE_DAYS)
    to_freeze = Driver.objects.filter(
        is_active=True, approval_status=Driver.APPROVAL_APPROVED, is_frozen=False,
    ).filter(
        Q(last_seen__lt=cutoff) | Q(last_seen__isnull=True, registered_at__lt=cutoff)
    )

    for driver in to_freeze:
        driver.is_frozen = True
        driver.save(update_fields=['is_frozen'])
        DriverActivityLog.objects.create(
            driver=driver, action=DriverActivityLog.ACTION_FREEZE,
            detail=f"{FREEZE_INACTIVE_DAYS}+ kun onlayn bo'lmagani uchun avtomatik muzlatildi",
        )


AUTO_OFFLINE_MINUTES = 10  # last_seen shuncha daqiqa yangilanmasa, avtomatik ish navbatidan chiqariladi


def auto_offline_stale_drivers():
    """Ilova background'da yopilib/tarmoq uzilib, last_seen yangilanishi
    to'xtagan haydovchilarni avtomatik ish navbatidan chiqaradi. Aks holda
    is_on_duty=True holicha abadiy osilib qolib, "onlayn" hisoblanadigan
    barcha ro'yxatlarda (jumladan manzil navbati) haqiqatda ancha vaqtdan
    beri ilovaga kirmagan haydovchi ham ko'rinib turaverar edi — chunki
    driver_address_queue kabi ba'zi endpointlar navbatda TURGAN haydovchi
    stale bo'lib qolmasligi uchun last_seen'ni har 10s'da yangilab turadi,
    biroq bu faqat ilova haqiqatda ishlab turgandagina davom etadi; ilova
    to'liq to'xtasa (yopilsa/signal yo'qolsa), last_seen ham yangilanmay
    qoladi va shu funksiya buni ushlab, is_on_duty'ni o'chiradi."""
    from datetime import timedelta
    from django.db.models import Q
    from django.utils import timezone
    from taxi.models import AddressQueueEntry, Driver, DriverActivityLog

    cutoff = timezone.now() - timedelta(minutes=AUTO_OFFLINE_MINUTES)
    stale_drivers = list(
        Driver.objects.filter(is_on_duty=True)
        .filter(Q(last_seen__lt=cutoff) | Q(last_seen__isnull=True))
    )
    if not stale_drivers:
        return

    ids = [d.pk for d in stale_drivers]
    Driver.objects.filter(pk__in=ids).update(is_on_duty=False)
    AddressQueueEntry.objects.filter(driver_id__in=ids, left_at__isnull=True).update(left_at=timezone.now())
    for driver in stale_drivers:
        DriverActivityLog.objects.create(
            driver=driver, action=DriverActivityLog.ACTION_DUTY_OFF,
            detail=f"Avtomatik: {AUTO_OFFLINE_MINUTES}+ daqiqa signal kelmadi",
        )
        tg_duty_changed(driver, False)


def warn_drivers_before_freeze():
    """freeze_inactive_drivers() dan bir kun oldin ishga tushadi — hali
    muzlamagan, lekin (FREEZE_INACTIVE_DAYS - 1) kundan beri onlayn
    bo'lmagan haydovchilarga oldindan ogohlantirish yuboradi (push + Telegram).
    Driver.freeze_warning_sent_at haydovchi qayta faollashguncha (driver_location_sync)
    qayta ogohlantirilib yubormasligini ta'minlaydi."""
    from datetime import timedelta
    from django.db.models import Q
    from django.utils import timezone
    from taxi.models import Driver

    freeze_cutoff = timezone.now() - timedelta(days=FREEZE_INACTIVE_DAYS)
    warn_cutoff = timezone.now() - timedelta(days=FREEZE_INACTIVE_DAYS - 1)
    to_warn = list(Driver.objects.filter(
        is_active=True, approval_status=Driver.APPROVAL_APPROVED, is_frozen=False,
        freeze_warning_sent_at__isnull=True,
    ).filter(
        Q(last_seen__lt=warn_cutoff, last_seen__gte=freeze_cutoff) |
        Q(last_seen__isnull=True, registered_at__lt=warn_cutoff, registered_at__gte=freeze_cutoff)
    ))
    if not to_warn:
        return

    from taxi.driver_views import send_push_to_driver
    for driver in to_warn:
        driver.freeze_warning_sent_at = timezone.now()
        driver.save(update_fields=['freeze_warning_sent_at'])
        send_push_to_driver(
            driver, '⏰ Hisobingiz muzlatilishi mumkin',
            f"{FREEZE_INACTIVE_DAYS - 1} kundan beri onlaynsiz. Ertaga ham kirmasangiz, hisobingiz vaqtincha muzlatiladi.",
        )

    cfg = _cfg()
    if cfg and not cfg.notify_freeze_warning:
        return
    lines = ["⏰ <b>Muzlashga 1 kun qolgan haydovchilar</b>", ""]
    for d in to_warn:
        lines.append(f"👤 <b>{d.full_name}</b> | <code>{d.phone_number}</code>")
    send_telegram('\n'.join(lines))


_SURGE_ALERT_COOLDOWN_MINUTES = 20
_SURGE_ALERT_MIN_MULTIPLIER = 1.5


def tg_surge_alert_check():
    """Talab keskin oshganda (surge) haydovchilar guruhiga navbatga chiqishni
    taklif qiluvchi xabar yuboradi. Ketma-ket spam bo'lmasligi uchun oxirgi
    yuborilgandan _SURGE_ALERT_COOLDOWN_MINUTES o'tmagan bo'lsa jim turadi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_surge_alert:
        return
    multiplier, label = get_surge_multiplier()
    if multiplier < _SURGE_ALERT_MIN_MULTIPLIER:
        return

    from datetime import timedelta
    from django.db.models import Q
    from django.utils import timezone
    from taxi.models import BotSettings

    now = timezone.now()
    cutoff = now - timedelta(minutes=_SURGE_ALERT_COOLDOWN_MINUTES)
    claimed = BotSettings.objects.filter(pk=1).filter(
        Q(last_surge_alert_at__isnull=True) | Q(last_surge_alert_at__lt=cutoff)
    ).update(last_surge_alert_at=now)
    if not claimed:
        return

    _notify_driver_group(
        f"📈 <b>Talab yuqori — {label}!</b>\n"
        f"Hozir navbatga chiqsangiz, ko'proq buyurtma tegishi mumkin. Omad! 🚕"
    )


def check_goals():
    """Faol maqsadlarni tekshiradi (scheduler tick'ida va Maqsadlar sahifasi
    ochilganda chaqiriladi): maqsad qiymatiga yetilgan bo'lsa "Erishildi"ga
    o'tkazadi va guruhga tabrik xabari yuboradi (faqat bir marta,
    `notified_completed` orqali); muddat o'tib ketgan, hali yetilmagan
    bo'lsa "Muddati o'tdi"ga o'tkazadi; muddatga 3 kun yoki kamroq qolib,
    hali yetilmagan bo'lsa — bir martalik eslatma yuboradi."""
    from django.utils import timezone
    from taxi.models import Goal

    cfg = _cfg()
    notify = bool(cfg and cfg.notify_goal_events)

    today = timezone.localdate()
    for goal in Goal.objects.filter(status=Goal.STATUS_ACTIVE):
        current = goal.current_value()
        if goal.target_value and current >= goal.target_value:
            goal.status = Goal.STATUS_COMPLETED
            goal.completed_at = timezone.now()
            update_fields = ['status', 'completed_at']
            if notify and not goal.notified_completed:
                send_telegram(
                    f"🎯 <b>Maqsadga erishildi!</b>\n\n<b>{goal.title}</b>\n"
                    f"Natija: {current} / {goal.target_value}\n"
                    f"Muddat: {goal.deadline.strftime('%d.%m.%Y')}\n\n"
                    "Jamoaga rahmat! 🎉"
                )
                goal.notified_completed = True
                update_fields.append('notified_completed')
            goal.save(update_fields=update_fields)
            continue

        if today > goal.deadline:
            goal.status = Goal.STATUS_FAILED
            goal.save(update_fields=['status'])
            continue

        days_left = (goal.deadline - today).days
        if notify and days_left <= 3 and not goal.notified_deadline_soon:
            send_telegram(
                f"⏳ <b>Muddat yaqinlashmoqda</b>\n\n<b>{goal.title}</b>\n"
                f"Qoldi: {days_left} kun\n"
                f"Joriy natija: {current} / {goal.target_value}"
            )
            goal.notified_deadline_soon = True
            goal.save(update_fields=['notified_deadline_soon'])


def tg_low_rating_alert(driver):
    """Haydovchining o'rtacha reytingi belgilangan chegaradan pastga
    tushganda operatorlar guruhini ogohlantiradi."""
    cfg = _cfg()
    if cfg and not cfg.notify_low_rating:
        return
    send_telegram(
        f"⚠️ <b>Reyting pasaydi</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>\n"
        f"⭐ Joriy reyting: <b>{driver.rating}</b> ({driver.rating_count} ta baho)\n"
        f"Xizmat sifatiga e'tibor qaratish tavsiya etiladi.",
        reply_markup=_driver_inline(driver.id),
    )


# Xulq-atvorga asoslangan reyting: Driver.rating (avval hech qachon
# avtomatik o'zgarmagan, statik 5.00) endi har bir YAKUNLANGAN buyurtmadan
# keyin ozgina ko'tariladi (yakunlash — "kutilgan me'yor", shu sabab sekin),
# qabul qilingandan keyin BEKOR qilingan har bir buyurtmadan keyin esa
# ancha ko'proq pasayadi (yomon xulq-atvor tezroq "sezilishi" uchun).
RATING_STEP_UP = Decimal('0.02')
RATING_STEP_DOWN = Decimal('0.15')
RATING_MIN = Decimal('1.00')
RATING_MAX = Decimal('5.00')
RATING_WARNING_THRESHOLD = Decimal('4.00')


def _adjust_driver_rating(driver, delta):
    """`driver.rating`ni `delta` qadar o'zgartiradi (RATING_MIN..RATING_MAX
    oralig'ida ushlab turadi) va DB'ga yozadi. Agar natija
    RATING_WARNING_THRESHOLD'ni YUQORIDAN PASTGA kesib o'tsa (avval undan
    baland, endi past bo'lsa — faqat aynan shu chegara kesilganda, har
    safar emas — aks holda haydovchi 4.00 dan pastda qolib ketsa, har bir
    keyingi bekor qilishda qayta-qayta ogohlantirilib, spam bo'lib qolardi),
    haydovchining o'ziga push va operatorlar guruhiga Telegram
    ogohlantirish yuboriladi."""
    old_rating = driver.rating
    new_rating = max(RATING_MIN, min(RATING_MAX, old_rating + delta))
    if new_rating == old_rating:
        return
    driver.rating = new_rating
    driver.save(update_fields=['rating'])
    if new_rating < RATING_WARNING_THRESHOLD <= old_rating:
        send_fcm(
            driver.fcm_token,
            title='Reytingingiz pasaymoqda',
            body=f"Joriy reytingingiz: {new_rating}. Buyurtmalarni ko'proq yakunlab, kamroq bekor qiling.",
            data={'type': 'low_rating_warning'},
        )
        tg_low_rating_alert(driver)


def reward_driver_rating_on_completion(driver):
    """Buyurtma yakunlanganda chaqiriladi (`_transition` — native ilova,
    `driver_order_action` — veb ilova) — reytingni ozgina ko'taradi."""
    _adjust_driver_rating(driver, RATING_STEP_UP)


def penalize_driver_rating_on_cancellation(driver):
    """Qabul qilingan buyurtma bekor qilinganda/o'chirilganda chaqiriladi
    (`_refund_order_commission`, `views.py`) — reytingni ancha pasaytiradi."""
    _adjust_driver_rating(driver, -RATING_STEP_DOWN)


_MILESTONE_TRIPS = (1, 10, 50, 100, 250, 500, 1000, 2500, 5000, 10000)


def _check_driver_milestone(driver):
    """Haydovchi jami yakunlagan safarlari muhim raqamga (masalan 100, 500,
    1000) yetganda haydovchilar guruhida tabriklaydi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_driver_milestone:
        return
    from taxi.models import Order

    completed = Order.objects.filter(driver=driver, status='completed').count()
    if completed not in _MILESTONE_TRIPS:
        return
    _notify_driver_group(
        f"🎉 <b>Tabriklaymiz!</b>\n"
        f"👤 <b>{driver.full_name}</b> jami <b>{completed}</b> ta safarni muvaffaqiyatli yakunladi!\n"
        f"Ajoyib mehnatingiz uchun rahmat 🚕💪"
    )


def tg_group_announcement(text):
    """Operator panelidan haydovchilar guruhiga erkin matnli e'lon yuboradi."""
    _notify_driver_group(f"📢 <b>E'lon</b>\n\n{text}")


def _today_duty_seconds():
    """Bugun har bir haydovchi jami necha soniya navbatda (is_on_duty) turganini
    hisoblaydi — DriverActivityLog dagi duty_on/duty_off juftliklaridan."""
    from django.utils import timezone
    from taxi.models import DriverActivityLog

    now = timezone.localtime()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    logs = (
        DriverActivityLog.objects
        .filter(created_at__gte=today_start,
                action__in=[DriverActivityLog.ACTION_DUTY_ON, DriverActivityLog.ACTION_DUTY_OFF])
        .order_by('driver_id', 'created_at')
    )

    seconds = {}
    open_on = {}
    for log in logs:
        if log.action == DriverActivityLog.ACTION_DUTY_ON:
            open_on[log.driver_id] = log.created_at
        else:
            start = open_on.pop(log.driver_id, today_start)
            seconds[log.driver_id] = seconds.get(log.driver_id, 0) + (log.created_at - start).total_seconds()
    # Hozir ham navbatda turganlar uchun shu daqiqagacha bo'lgan vaqtni qo'shamiz
    for driver_id, start in open_on.items():
        seconds[driver_id] = seconds.get(driver_id, 0) + (timezone.now() - start).total_seconds()
    return seconds


def tg_top_hours_drivers():
    """Har kuni kechqurun bugun eng uzoq navbatda turgan (is_on_duty bo'lgan)
    haydovchilar TOP-10 ro'yxatini haydovchilar guruhiga yuboradi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_top_hours_drivers:
        return
    from django.utils import timezone
    from taxi.models import Driver

    seconds = _today_duty_seconds()
    top = sorted(seconds.items(), key=lambda kv: kv[1], reverse=True)[:10]
    top = [(driver_id, secs) for driver_id, secs in top if secs >= 600]  # 10 daqiqadan kam bo'lsa hisobga olinmaydi
    if not top:
        return

    drivers = {d.id: d for d in Driver.objects.filter(id__in=[driver_id for driver_id, _ in top])}
    medals = ['🥇', '🥈', '🥉']
    today = timezone.localdate()
    lines = ["⏱ <b>Bugun eng uzoq navbatda turgan haydovchilar</b>", f"📅 {today.strftime('%d.%m.%Y')}", ""]
    for i, (driver_id, secs) in enumerate(top):
        d = drivers.get(driver_id)
        if not d:
            continue
        rank = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{rank} <b>{d.full_name}</b> — {secs / 3600:.1f} soat")
    lines.append("\nFidoyiligingiz uchun rahmat! 🙌")
    _notify_driver_group('\n'.join(lines))


def tg_high_rejection_report():
    """Bugun ko'p buyurtmani rad etgan haydovchilarni operatorlar guruhiga
    ma'lum qiladi. Taxminiy hisob: shu kun yaratilgan buyurtmalar orasida
    rad etganlar soni va qabul qilganlar soni solishtiriladi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_high_rejection:
        return
    from django.utils import timezone
    from taxi.models import Driver, Order

    threshold = 0.5
    min_sample = 5
    today = timezone.localdate()
    lines = []
    for d in Driver.objects.filter(is_active=True, approval_status='approved'):
        rejected = Order.objects.filter(rejected_by=d, created_at__date=today).count()
        accepted = Order.objects.filter(driver=d, created_at__date=today).count()
        total = rejected + accepted
        if total < min_sample:
            continue
        rate = rejected / total
        if rate > threshold:
            lines.append(f"👤 <b>{d.full_name}</b> — {rejected}/{total} ta rad etgan ({rate * 100:.0f}%)")
    if not lines:
        return
    send_telegram('\n'.join([
        "⚠️ <b>Bugun ko'p buyurtmani rad etgan haydovchilar</b>", "",
        *lines,
    ]))


def _company_stats_for_period(date_from, date_to):
    from django.db.models import Count, Sum
    from taxi.models import Order

    qs = Order.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    completed = qs.filter(status='completed').aggregate(count=Count('id'), revenue=Sum('price'))
    cancelled_count = qs.filter(status='cancelled').count()
    return {
        'completed': completed['count'] or 0,
        'revenue':   completed['revenue'] or 0,
        'cancelled': cancelled_count,
    }


def tg_daily_summary():
    """Kun oxirida kompaniya bo'yicha umumiy hisobotni operatorlar guruhiga yuboradi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_daily_summary:
        return
    from django.utils import timezone
    from taxi.models import Driver

    today = timezone.localdate()
    stats = _company_stats_for_period(today, today)
    active_drivers = Driver.objects.filter(is_active=True, is_on_duty=True, approval_status='approved').count()
    revenue = stats['revenue']
    send_telegram(
        f"📊 <b>Kunlik hisobot</b>\n"
        f"📅 {today.strftime('%d.%m.%Y')}\n\n"
        f"✅ Yakunlangan: <b>{stats['completed']}</b> ta\n"
        f"💰 Tushum: <b>{revenue:,.0f} UZS</b>\n"
        f"❌ Bekor qilingan: {stats['cancelled']} ta\n"
        f"🟢 Hozir navbatda: {active_drivers} haydovchi".replace(',', ' ')
    )


def tg_weekly_summary():
    """Har yakshanba kechqurun kompaniya bo'yicha haftalik hisobotni
    operatorlar guruhiga yuboradi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_weekly_summary:
        return
    from datetime import timedelta
    from django.utils import timezone

    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    stats = _company_stats_for_period(week_start, today)
    revenue = stats['revenue']
    send_telegram(
        f"📊 <b>Haftalik hisobot</b>\n"
        f"📅 {week_start.strftime('%d.%m')} — {today.strftime('%d.%m.%Y')}\n\n"
        f"✅ Yakunlangan: <b>{stats['completed']}</b> ta\n"
        f"💰 Tushum: <b>{revenue:,.0f} UZS</b>\n"
        f"❌ Bekor qilingan: {stats['cancelled']} ta".replace(',', ' ')
    )


def tg_monthly_financial_report():
    """Har oyning birinchi kunida, endigina yakunlangan o'tgan oy bo'yicha
    moliyaviy hisobotni operatorlar guruhiga yuboradi: tushum, haydovchilarga
    to'ldirilgan pul, komissiya sifatida yechilgan pul va sof farq."""
    cfg = _cfg()
    if not cfg or not cfg.notify_monthly_financial_report:
        return
    from datetime import timedelta
    from django.db.models import Sum
    from django.utils import timezone
    from taxi.models import BalanceLog

    today = timezone.localdate()
    month_end = today.replace(day=1) - timedelta(days=1)
    month_start = month_end.replace(day=1)

    order_stats = _company_stats_for_period(month_start, month_end)
    topped_up = BalanceLog.objects.filter(
        action=BalanceLog.ACTION_ADD, created_at__date__gte=month_start, created_at__date__lte=month_end
    ).aggregate(s=Sum('amount'))['s'] or 0
    deducted = BalanceLog.objects.filter(
        action=BalanceLog.ACTION_DEDUCT, created_at__date__gte=month_start, created_at__date__lte=month_end
    ).aggregate(s=Sum('amount'))['s'] or 0

    send_telegram(
        f"🗓️ <b>Oylik moliyaviy hisobot</b>\n"
        f"📅 {month_start.strftime('%m.%Y')}\n\n"
        f"✅ Yakunlangan buyurtmalar: <b>{order_stats['completed']}</b> ta\n"
        f"💰 Buyurtmalardan tushum: <b>{order_stats['revenue']:,.0f} UZS</b>\n"
        f"➕ Haydovchilarga to'ldirilgan: <b>{topped_up:,.0f} UZS</b>\n"
        f"➖ Komissiya sifatida yechilgan: <b>{deducted:,.0f} UZS</b>\n"
        f"📈 Sof farq (komissiya − to'ldirish): <b>{deducted - topped_up:,.0f} UZS</b>".replace(',', ' ')
    )


def tg_daily_highlight_trip():
    """Kun oxirida eng uzoq va eng qimmat safarni haydovchilar guruhida
    e'lon qiladi — kichik qiziqarli shoutout."""
    cfg = _cfg()
    if not cfg or not cfg.notify_daily_highlight:
        return
    from django.utils import timezone
    from taxi.models import Order

    today = timezone.localdate()
    qs = Order.objects.filter(status='completed', created_at__date=today, driver__isnull=False)
    longest  = qs.exclude(distance_km__isnull=True).order_by('-distance_km').first()
    priciest = qs.exclude(price__isnull=True).order_by('-price').first()
    if not longest and not priciest:
        return

    lines = ["🌟 <b>Kunning yorqin lahzalari</b>", f"📅 {today.strftime('%d.%m.%Y')}", ""]
    if longest:
        lines.append(f"📏 Eng uzoq safar: <b>{longest.distance_km:.1f} km</b> — {longest.driver.full_name}")
    if priciest:
        lines.append(f"💰 Eng qimmat safar: <b>{priciest.price:,.0f} UZS</b> — {priciest.driver.full_name}".replace(',', ' '))
    _notify_driver_group('\n'.join(lines))


def tg_flyer_voucher_redeemed(voucher, driver):
    """Haydovchi flayerdagi kuponni ishlatganda haydovchilar guruhiga
    tabriklovchi xabar yuboradi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_flyer_redeemed:
        return
    _notify_driver_group(
        f"🎁 <b>Flayer kuponi ishlatildi!</b>\n"
        f"👤 <b>{driver.full_name}</b> balansiga <b>{voucher.amount:,.0f} UZS</b> qo'shildi.".replace(',', ' ')
    )


def tg_night_greeting():
    """Kechasi hozir navbatda turgan (tungi smenada ishlayotgan) haydovchilarga
    alohida salomlashuv xabarini haydovchilar guruhiga yuboradi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_night_greeting:
        return
    from taxi.models import Driver

    night_drivers = list(
        Driver.objects.filter(is_active=True, is_on_duty=True, approval_status='approved')
    )
    if not night_drivers:
        return

    names = ', '.join(f"<b>{d.full_name}</b>" for d in night_drivers)
    text = (
        "🌙 <b>Xayrli kech, tungi navbatchi haydovchilar!</b>\n\n"
        f"Bu kecha navbatda turganlar: {names}\n\n"
        "Tungi yo'llarda ehtiyot bo'ling, diqqatingizni yo'ldan bo'lmang. "
        "Xavfsiz va samarali tun tilaymiz! 🚕✨"
    )
    _notify_driver_group(text)


_ENGAGEMENT_MESSAGES = [
    "🦺 <b>Xavfsizlik maslahati:</b> Yo'lovchi tushishidan oldin atrofni albatta tekshiring.",
    "🗣️ <b>Maslahat:</b> Yo'lovchi bilan yoqimli suhbat kayfiyatni ko'taradi, lekin haydashdan chalg'itmasin.",
    "🔥 <b>Motivatsiya:</b> Har bir safar — yangi imkoniyat. Bugun ham eng yaxshisini bering!",
    "🌟 <b>Motivatsiya:</b> Yaxshi xizmat — doimiy mijoz demakdir. Kichik xushmuomalalik katta ishonch yaratadi.",
    "😄 Haydovchi va navigatsiya doim tortishadi: u chapga, siz o'ngga burilasiz 😅 Baribir yo'lni siz yaxshi bilasiz!",
    "⛽ <b>Maslahat:</b> Yoqilg'i darajasini har safar oldindan tekshirib turing — yo'lda qolib ketmang.",
    "📵 <b>Xavfsizlik maslahati:</b> Rulda telefon bilan band bo'lmang — xavfsizlik hammasidan muhim.",
    "💪 <b>Motivatsiya:</b> Charchagan kunlar ham o'tadi, lekin mehnatingiz albatta mevasini beradi.",
    "😂 Eng yaxshi GPS — bu tajribali haydovchining xotirasi! Lekin baribir ilovaga ham ishoning 😉",
    "🧼 <b>Maslahat:</b> Mashinangiz toza bo'lsa, mijozlar ko'proq mamnun bo'ladi va qayta buyurtma berishadi.",
    "🚀 <b>Motivatsiya:</b> Kichik qadamlar katta natijalarga olib keladi — har bir buyurtma muhim.",
    "😊 <b>Maslahat:</b> Kutish vaqtida sabr-toqatli bo'ling — bu eng yaxshi hamrohingiz.",
    "🎶 Yo'lda yoqimli musiqa safarni yanada yoqimli qiladi — lekin ovozni me'yorida tuting.",
    "🅿️ <b>Maslahat:</b> Yo'lovchini olib ketishdan oldin to'g'ri manzilni tasdiqlab oling — vaqtni tejaydi.",
    "🏆 <b>Motivatsiya:</b> Eng yaxshi haydovchilar — doimiy va barqaror ishlaydiganlar. Siz ham shunday bo'lyapsiz!",
    "🌦️ Ob-havo qanday bo'lmasin, sizning kayfiyatingiz doim quyoshli bo'lsin! ☀️",
]


def tg_driver_engagement():
    """Kun davomida bir necha marta (peshin va kechqurun) haydovchilar guruhiga
    tasodifiy motivatsion so'z, foydali maslahat yoki kichik hazil xabar
    yuboradi — guruhni jonli va qiziqarli tutish uchun."""
    cfg = _cfg()
    if not cfg or not cfg.notify_driver_engagement:
        return
    import random
    _notify_driver_group(random.choice(_ENGAGEMENT_MESSAGES))


def tg_driver_fun_stats():
    """Kunning davomida yig'ilgan qiziqarli raqamlarni (bosib o'tilgan masofa,
    yakunlangan safarlar soni, eng ko'p buyurtma qilingan hudud) haydovchilar
    guruhiga yuboradi."""
    cfg = _cfg()
    if not cfg or not cfg.notify_driver_fun_stats:
        return
    from django.db.models import Count, Sum
    from django.utils import timezone
    from taxi.models import Order

    today = timezone.localdate()
    qs = Order.objects.filter(status='completed', created_at__date=today)
    total_completed = qs.count()
    if not total_completed:
        return
    total_distance = qs.aggregate(s=Sum('distance_km'))['s'] or 0
    top_address = (
        qs.exclude(from_address='').values('from_address')
        .annotate(c=Count('id')).order_by('-c').first()
    )

    lines = [
        "📊 <b>Bugungi qiziqarli raqamlar</b>",
        f"📅 {today.strftime('%d.%m.%Y')}",
        "",
        f"🚕 Yakunlangan safarlar: <b>{total_completed}</b> ta",
        f"🛣️ Jami bosib o'tilgan masofa: <b>{total_distance:.0f} km</b>",
    ]
    if top_address:
        lines.append(f"📍 Eng ko'p buyurtma qilingan hudud: <b>{top_address['from_address']}</b> ({top_address['c']} marta)")
    lines.append("\nHar bir safar — yangi tajriba! Davom eting 🚀")
    _notify_driver_group('\n'.join(lines))


def tg_sos_alert(alert):
    driver = alert.driver
    log_panel_event('panel_sos_alert', f"SOS #{alert.id} — {driver.full_name}")
    lines = [
        f"🆘 <b>SOS SIGNAL! #{alert.id}</b>",
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>",
        f"🚗 {driver.car_model} <code>{driver.car_number}</code>",
    ]
    if alert.address:
        lines.append(f"📍 Manzil: {alert.address}")
    if alert.latitude and alert.longitude:
        lines.append(f"🗺 Koordinata: <code>{alert.latitude:.5f}, {alert.longitude:.5f}</code>")
        lines.append(f"🔗 <a href='https://maps.google.com/?q={alert.latitude},{alert.longitude}'>Google Maps</a>")
    if alert.note:
        lines.append(f"📝 Izoh: {alert.note}")
    markup = {'inline_keyboard': [[
        {'text': '👤 Haydovchi', 'url': _driver_url(driver.id)},
    ]]}
    text = '\n'.join(lines)
    send_telegram(text, reply_markup=markup)

    notify_operators(
        'SOS SIGNAL',
        f"{driver.full_name} — {alert.address or 'manzil nomaʻlum'}",
        data={'type': 'sos', 'alert_id': str(alert.id), 'driver_id': str(driver.id)},
    )

    # Bot adminlarga shaxsiy DM ham yuboriladi — SOS xavfsizlik uchun muhim,
    # operator guruhida bo'lmagan adminlar ham darhol xabardor bo'lishi kerak.
    try:
        from taxi.models import BotAdmin
        cfg = _cfg()
        admin_ids = list(BotAdmin.objects.filter(is_active=True).values_list('chat_id', flat=True))
        if cfg and admin_ids:
            send_telegram(text, token=cfg.bot_token.strip(), chat_ids=admin_ids, reply_markup=markup)
    except Exception:
        pass

    # Haydovchilar guruhiga ham — yaqin atrofdagi haydovchilar yordam bera olishi uchun
    cfg = _cfg()
    if cfg and cfg.notify_sos_to_driver_group:
        _notify_driver_group(text, reply_markup=markup)


_fcm_credentials = None  # lazy-cached google.oauth2.service_account.Credentials


def _get_fcm_access_token():
    """FCM HTTP v1 uchun OAuth2 access token qaytaradi (xizmat hisobi
    kalitidan) — modul darajasida keshlanadi va muddati tugaganda
    avtomatik yangilanadi, har chaqiriqda diskdan qayta o'qimaslik uchun."""
    global _fcm_credentials
    from django.conf import settings
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    key_file = getattr(settings, 'FCM_SERVICE_ACCOUNT_FILE', '')
    if not key_file:
        return None
    if _fcm_credentials is None:
        _fcm_credentials = service_account.Credentials.from_service_account_file(
            key_file, scopes=['https://www.googleapis.com/auth/firebase.messaging'],
        )
    if not _fcm_credentials.valid:
        _fcm_credentials.refresh(Request())
    return _fcm_credentials.token


def send_fcm(fcm_token, title, body, data=None):
    """FCM push notification yuborish (HTTP v1 API — legacy 'fcm/send' Google
    tomonidan butunlay o'chirilgan, shu sabab xizmat hisobi orqali OAuth2
    bilan ishlaydigan v1 endpoint ishlatiladi).

    Diqqat: xabarda ATAYLAB `notification` bloki YO'Q — faqat `data`. Agar
    top-level `notification` bo'lsa, Android ilova fonda/o'chirilgan
    bo'lganda FCM SDK bildirishnomani android tizimi darajasida o'zi avtomatik
    ko'rsatib yuboradi va ilovaning `onMessageReceived()` kodi umuman
    chaqirilmaydi — bu esa yangi buyurtma uchun to'liq ekran (full-screen)
    ochish, ovoz/tebranish kabi maxsus mantiqni chetlab o'tib ketardi. Sof
    `data`-xabar esa ilova qaysi holatda bo'lishidan qat'i nazar (fonda,
    o'chirilgan, ochiq) doim `onMessageReceived()`ga yetib boradi."""
    from django.conf import settings
    project_id = getattr(settings, 'FCM_PROJECT_ID', '')
    if not project_id or not fcm_token:
        return False
    try:
        access_token = _get_fcm_access_token()
        if not access_token:
            return False
        # v1 xabarida `data` faqat string qiymatlarni qabul qiladi.
        str_data = {str(k): str(v) for k, v in (data or {}).items()}
        str_data['title'] = title
        str_data['body'] = body
        payload = json.dumps({
            'message': {
                'token': fcm_token,
                'data': str_data,
                'android': {'priority': 'high'},
            },
        }).encode()
        req = urllib.request.Request(
            f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send',
            data=payload,
            headers={
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json; UTF-8',
            },
        )
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False


def notify_operators(title, body, data=None):
    """Barcha operator native ilova (vijdon_operator_native) qurilmalariga
    push yuboradi — yangi dispetcherlanmagan buyurtma, yangi to'lov so'rovi,
    SOS kabi operator e'tibori kerak bo'lgan hodisalar uchun. `send_fcm()`
    bilan bir xil (data-only, HTTP v1) mexanizm — faqat token manbai
    Driver.fcm_token o'rniga OperatorPushToken jadvali."""
    from taxi.models import OperatorPushToken
    for token in OperatorPushToken.objects.values_list('fcm_token', flat=True):
        send_fcm(token, title=title, body=body, data=data)


def _log_dispatch_attempt(order, driver, distance_km=None):
    """Buyurtma bitta haydovchiga taklif qilinganda chaqiriladi — "Taqsimlash
    tarixi" (order_detail.html) uchun urinishni ketma-ketlik va masofa bilan
    yozib boradi."""
    from taxi.models import DispatchAttempt
    attempt_number = order.dispatch_attempts.count() + 1
    return DispatchAttempt.objects.create(
        order=order, driver=driver, distance_km=distance_km, attempt_number=attempt_number,
    )


def _resolve_dispatch_attempt(order, driver_id, result):
    """Eng oxirgi "kutilmoqda" urinishni yakuniy natija bilan yopadi
    (qabul qildi / rad etdi / javob bermadi / bekor qilindi)."""
    from taxi.models import DispatchAttempt
    from django.utils import timezone
    DispatchAttempt.objects.filter(
        order=order, driver_id=driver_id, result=DispatchAttempt.RESULT_PENDING,
    ).update(result=result, resolved_at=timezone.now())


def auto_reject_timeout(order_id, driver_id, timeout_seconds):
    """
    Haydovchi belgilangan vaqt ichida javob bermasa, buyurtmani avtomatik rad etadi
    va keyingi haydovchiga o'tkazadi.

    Diqqat (poyga sharoiti/race condition): agar aynan shu daqiqada haydovchi
    "Qabul qildim" so'rovini yuborgan bo'lsa-yu, u hali serverga
    yetib/qayta ishlanib ulgurmagan bo'lsa — avvalgi versiyada bu funksiya
    oddiy `.get()` bilan (hech qanday qulfsiz) o'qib, ESKI ('pending')
    holatga asoslanib buyurtmani darhol boshqa haydovchiga o'tkazib
    yuborardi. Keyin haydovchining "Qabul qildim" so'rovi (select_for_update
    bilan) yetib kelganda, DB'da haydovchining o'zi allaqachon qabul qilgan
    bo'lsa ham, `dispatched_to` boshqasiga o'zgargani sabab "Bu buyurtma
    sizga yuborilmagan" xatosini olardi — go'yo tugma "qotib qolgandek"
    ko'rinardi, aslida esa qabul qilish muvaffaqiyatli bo'lgan, faqat shu
    fon jarayoni uni "bekor qilib" ulgurgan edi. Endi shu yerda ham
    select_for_update ishlatiladi — agar "Qabul qildim" tranzaksiyasi
    aynan shu daqiqada davom etayotgan bo'lsa, bu funksiya uning
    tugashini KUTADI, keyin ENDI HAM DB'dan qayta o'qiydi — shu orqali
    haqiqatan qabul qilingan buyurtmani hech qachon qayta ochib
    yubormaydi."""
    import time
    time.sleep(timeout_seconds)

    from django.db import transaction
    from taxi.models import Order, DispatchAttempt
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(pk=order_id)
            if order.status == 'pending' and order.dispatched_to_id == driver_id:
                order.rejected_by.add(driver_id)
                order.dispatched_to = None
                order.save(update_fields=['dispatched_to'])
                _resolve_dispatch_attempt(order, driver_id, DispatchAttempt.RESULT_TIMEOUT)
                # Diqqat: avval bu yerda javob bermagan haydovchi manzil
                # navbatining OXIRIGA tushirilardi (_requeue_driver_to_back).
                # Foydalanuvchi so'rovi bo'yicha olib tashlandi — endi
                # haydovchi navbatdagi o'rnini FAQAT oflaynga chiqqanda
                # yoki biror buyurtmani qabul qilganda yo'qotadi (duty_toggle
                # va order_accept'dagi AddressQueueEntry.left_at yozuvlari).
            else:
                return

        notify_dispatch_offer_cancelled(driver_id, order, "javob berilmagani uchun boshqa haydovchiga o'tkazildi")

        # Keyingi haydovchiga yuborish — tranzaksiya (va shu bilan qulf)
        # yopilgandan KEYIN, aks holda dispatch_order() ichidagi yangi
        # DispatchAttempt/notify chaqiruvlari qulf ushlab turilgan holda
        # bajarilib, boshqa so'rovlarni keraksiz kutishga majburlardi.
        dispatch_order(order)
    except Exception:
        pass


def notify_dispatch_offer_cancelled(driver_id, order, reason):
    """Haydovchiga avval taklif qilingan (dispatched_to) buyurtma endi
    unga tegishli emasligi haqida push yuboradi — javob bermay vaqti
    tugagani (`auto_reject_timeout`), operator boshqa haydovchiga
    qayta yo'naltirgani yoki hali qabul qilinmagan buyurtmani
    o'chirib/bekor qilgani sabab. Bu haydovchining telefonida hali ham
    ko'rinib turgan "Yangi buyurtma" bildirishnomasini yopish uchun kerak
    (aks holda ekranda/qo'ng'iroq ohangida abadiy "osilib" qolardi).
    `type: order_timeout` — VijdonFirebaseMessagingService.onMessageReceived()
    shu turni ko'rib, notificationId=order_id bo'yicha uni yopadi (sabab —
    barcha holatda ilova tarafidan bir xil: shunchaki bildirishnomani yopish)."""
    from taxi.models import Driver
    fcm_token = Driver.objects.filter(pk=driver_id).values_list('fcm_token', flat=True).first()
    if not fcm_token:
        return
    send_fcm(
        fcm_token,
        title='Buyurtma taklifi bekor qilindi',
        body=f"Buyurtma #{order.id} — {reason}.",
        data={'type': 'order_timeout', 'order_id': str(order.id)},
    )


ADDRESS_QUEUE_RADIUS_KM = 1.0        # manzil navbatiga "QO'SHILISH" radiusi
ADDRESS_QUEUE_LEAVE_RADIUS_KM = 2.0  # navbatdan "CHIQISH" radiusi — QO'SHILISH'dan ataylab kattaroq
                                      # (hysteresis): GPS bir oz tebransa yoki haydovchi bir zumga
                                      # 1-2 km oralig'ida chiqib qolsa ham, darhol navbatdan
                                      # chiqarib yuborilmasin — faqat chindan ham uzoqlashganda
                                      # (yoki boshqa manzilga o'tganda) chiqariladi.
ADDRESS_QUEUE_MAX_ATTEMPTS = 3       # navbatdan ketma-ket ko'pi bilan nechta haydovchiga taklif qilinadi
ADDRESS_QUEUE_STALE_MINUTES = 4      # shuncha daqiqa faollik (Driver.last_seen) bo'lmasa, navbatda
                                      # "hozir turgan" deb hisoblanmaydi — faqat masofa (hysteresis)
                                      # tekshirilsa, uzoq vaqt oflayn/ilovani yopib qo'ygan haydovchi
                                      # (garchi joyidan jilmagan bo'lsa ham) abadiy eski o'rnini
                                      # saqlab qolaverar edi.
                                      # Diqqat: avval bu 1 daqiqa edi — lekin native ilova
                                      # (DriverLocationService.kt: maybeReportToServer) harakatsiz
                                      # turgan haydovchining joylashuvini serverga ENG KO'PI BILAN
                                      # har 2 daqiqada bir marta yuboradi. Natijada 1 daqiqalik
                                      # chegara doim shu 2 daqiqalik oraliqdan KICHIK bo'lib,
                                      # navbatda TINCH turgan har bir haydovchi har safar yangi
                                      # joylashuv kelganda "qaytib keldi" deb hisoblanib, navbat
                                      # OXIRIGA tushib qolaverardi — garchi u joyidan sira
                                      # jilmagan bo'lsa ham. 4 daqiqa — 2 daqiqalik yuborish
                                      # oralig'idan (tarmoq kechikishi uchun ham zахira bilan)
                                      # xavfsiz yuqori.

# Yaqin atrofda (ADDRESS_QUEUE_RADIUS_KM ichida) hech qanday SavedAddress
# topilmasa — operator O'ZI oldindan qo'lda manzil qo'shishi shart emas.
# Haydovchi shu AUTO_ADDRESS_DWELL_RADIUS_KM ichida AUTO_ADDRESS_DWELL_MINUTES
# davomida "turib qolsa" (haqiqatan navbatga tushgandek), tizim o'sha nuqtada
# yangi SavedAddress'ni AVTOMATIK yaratadi (nomi reverse-geocode orqali).
# Shunchaki yo'lda o'tib ketayotgan yoki svetoforda to'xtagan haydovchi uchun
# manzil yaratilib qolmasligi uchun ikkalasi ham ataylab "qattiqroq" (torroq
# radius, bir necha daqiqa) qilib tanlangan.
#
# Diqqat: native ilova harakatsiz turgan haydovchining joylashuvini
# serverga eng tez ~2 daqiqada bir marta yuboradi (batareya tejash uchun,
# DriverLocationService.kt) — shu sabab bu qiymatni 2 daqiqadan PASTGA
# tushirish amalda hech narsani tezlashtirmaydi (ikkinchi so'rov baribir
# ~2 daqiqadan keyin keladi). 2 daqiqa — birinchi va ikkinchi so'rov
# orasidagi "tabiiy" oraliqqa mos, shu bilan birga eng qisqa amaliy kutish.
AUTO_ADDRESS_DWELL_RADIUS_KM = 0.1    # ~100 metr (GPS tebranishiga bir oz zахira bilan)
AUTO_ADDRESS_DWELL_MINUTES = 2

# Yangi manzil YARATISHDAN OLDIN — yaqin atrofda (kengroq radiusda) shu
# nomdagi/hududdagi manzil ALLAQACHON bor-yo'qligini tekshirish uchun.
# Diqqat: bu ADDRESS_QUEUE_RADIUS_KM (1km, jonli navbat aniqligi) dan
# ATAYIN kattaroq — bitta qishloq/mahalla (masalan "Tepaqo'rg'on") odatda
# 1km dan kengroq maydonni qamrab oladi, lekin undagi HAR QANDAY nuqta
# reverse-geocode orqali bir xil nomga chiqadi. Avval bu tekshiruv
# yo'q edi — shu sabab bir necha yuz metr farq bilan bir-biriga juda
# yaqin, bir xil nomli "duplikat" manzillar yaratilib qolayotgan edi.
AUTO_ADDRESS_DEDUPE_RADIUS_KM = 3.0


def find_matching_saved_address(lat, lng, radius_km=None, addresses=None):
    """Berilgan koordinata biror SavedAddress (Manzillar) radiusida
    bo'lsa — o'sha manzilni qaytaradi (eng yaqinini, bir nechtasi mos
    kelsa), aks holda None. dispatch_order() shu orqali "oddiy taqsimlash"
    bilan "manzil navbati"ni ajratadi.

    `radius_km` berilmasa sukut bo'yicha ADDRESS_QUEUE_RADIUS_KM (jonli
    navbat qo'shilish aniqligi) ishlatiladi — bu qat'iy qolishi kerak,
    aks holda dispetcherlik xato joyga "yaqin" deb hisoblab qolishi mumkin.
    Kengroq radius faqat AVTOMATIK MANZIL YARATISHDAN OLDIN, "bu joy
    allaqachon bor-yo'qligini" tekshirish uchun beriladi (pastga qarang).

    `addresses` berilsa (chaqiruvchi oldindan SavedAddress.objects.all()ni
    bir marta olib qo'ygan bo'lsa), DB'ga qayta so'rov yuborilmaydi — bu
    ro'yxatning o'zidan qidiriladi. Ko'p koordinata ustida tsikl ichida
    (masalan bugungi barcha buyurtmalar) chaqirilganda N+1 so'rovning
    oldini olish uchun shart."""
    from taxi.models import SavedAddress
    radius = radius_km if radius_km is not None else ADDRESS_QUEUE_RADIUS_KM
    nearest_addr, nearest_dist = None, float('inf')
    candidates = addresses if addresses is not None else SavedAddress.objects.all()
    for a in candidates:
        d = haversine(lat, lng, a.lat, a.lng)
        if d is not None and d <= radius and d < nearest_dist:
            nearest_dist = d
            nearest_addr = a
    return nearest_addr


def update_address_queue_membership(driver, lat, lng, was_stale=False):
    """Haydovchi GPS koordinatasi yangilanganda (driver_location_sync yoki
    driver_address_queue) chaqiriladi — biror manzil (SavedAddress)
    radiusiga kirsa navbatga "yoziladi" (AddressQueueEntry). Kelgan vaqti
    (`joined_at`) saqlanib boradi — shu orqali dispatch_order() "kim
    birinchi kelgan" tartibida taklif qila oladi (taksi bekati navbati
    kabi).

    Diqqat: agar yaqin atrofda operator oldindan qo'shgan manzil bo'lmasa,
    funksiya shu yerda TO'XTAB QOLMAYDI — pastda (AUTO_ADDRESS_DWELL_*)
    haydovchi shu nuqtada bir necha daqiqa turib qolsa, yangi SavedAddress
    AVTOMATIK yaratiladi. Shu sabab operator endi HAR bir manzilni oldindan
    qo'lda kiritishi shart emas.

    Diqqat: allaqachon navbatda bo'lsa, uni chiqarish uchun QO'SHILISH
    radiusidan (300m) KATTAROQ chegara (ADDRESS_QUEUE_LEAVE_RADIUS_KM,
    600m) ishlatiladi — hysteresis. Aks holda GPS aniqligi tebranib
    tursa yoki haydovchi bir zumga chetga chiqsa, navbatdagi o'rni
    doim-doim yo'qolib-qayta paydo bo'lib turardi.

    `was_stale=True` bo'lsa (chaqiruvchi, bu yangilanishdan OLDINGI
    driver.last_seen ADDRESS_QUEUE_STALE_MINUTES dan eski ekanini
    aniqlagan bo'lsa) — hysteresis e'tiborga olinmaydi, eski yozuv
    yopilib, yangi joined_at bilan navbat OXIRIGA qo'yiladi. Aks holda:
    haydovchi ilovani 10+ daqiqa yopib qo'yib, o'sha manzildan jilmagan
    holda qaytsa, eski (uzoq vaqt oldingi) joined_at hysteresis tufayli
    saqlanib qolardi — u butun shu vaqt "stale" filtri orqali navbatda
    KO'RINMASA HAM, qaytib faollashgach birdaniga eski (yaxshi) o'rniga
    "sakrab" tushib, doim faol turgan boshqa haydovchilarni ORQAGA surib
    yuborardi.

    Diqqat: hysteresis faqat "joriy navbatdagi manzildan hali uzoqlashib
    ketmadimmi" deb tekshiradi — agar ikkita saqlangan manzil bir-biridan
    ADDRESS_QUEUE_LEAVE_RADIUS_KM dan yaqin bo'lsa (masalan ikkita bozor
    bir-biriga yaqin joylashgan), haydovchi A navbatidan haydab B manziliga
    borib to'xtasa ham, B hali A dan 2km ichida bo'lgani uchun eski A
    yozuvi hech qachon yopilmay, haydovchi ABADIY A navbatida "yopishib"
    qolar, B navbatida esa umuman ko'rinmas edi. Shu sabab avval joriy
    GPS nuqtasiga ENG YAQIN manzil aniqlanadi — agar u joriy navbatdagi
    manzildan BOSHQA bo'lsa, bu haqiqiy manzil almashinuvi deb hisoblanadi
    va hysteresis e'tiborga olinmaydi.

    Qulf: driver.last_seen (GPS sync) va driver_address_queue (10s poll)
    bir xil haydovchi uchun deyarli bir vaqtda kelib qolishi mumkin —
    qulfsiz bo'lsa, ikkalasi ham bir xil "ochiq yozuv yo'q/uzoqlashgan"
    holatni o'qib, ikkalasi ham yangi AddressQueueEntry yaratib, bitta
    haydovchi uchun IKKITA ochiq yozuv qolib ketardi (navbat soni/tartibi
    buzilardi). Shu sabab Driver qatori select_for_update bilan
    qulflanadi — shu haydovchi uchun chaqiruvlar ketma-ket bajariladi."""
    from taxi.models import AddressQueueEntry, Driver, Order
    from django.db import transaction
    from django.utils import timezone

    with transaction.atomic():
        Driver.objects.select_for_update().get(pk=driver.pk)

        open_entry = AddressQueueEntry.objects.filter(driver=driver, left_at__isnull=True).select_related('address').first()

        # Zakazi bor (hali yakunlanmagan) haydovchi manzil navbatiga umuman
        # kirmasin — u band, shu manzilda yangi buyurtmani qabul qila olmaydi.
        # (Buyurtma QABUL QILINGANDA ochiq yozuv driver_order_action'da
        # allaqachon yopiladi — bu yerdagi tekshiruv esa haydovchi hali band
        # holatda, masalan yo'lda saqlangan manzil radiusidan o'tib ketganda,
        # navbatga QAYTA yozilib qolishining oldini oladi.)
        if Order.objects.filter(driver=driver, status__in=Order.ACTIVE_STATUSES).exists():
            if open_entry:
                open_entry.left_at = timezone.now()
                open_entry.save(update_fields=['left_at'])
            return

        nearest_addr = find_matching_saved_address(lat, lng)

        if open_entry:
            switched_address = nearest_addr is not None and nearest_addr.pk != open_entry.address_id
            dist_to_current = haversine(lat, lng, open_entry.address.lat, open_entry.address.lng)
            if (
                not was_stale and not switched_address
                and dist_to_current is not None and dist_to_current <= ADDRESS_QUEUE_LEAVE_RADIUS_KM
            ):
                return  # hali "yetarlicha yaqin" — navbatdagi o'rni saqlanib qoladi
            open_entry.left_at = timezone.now()
            open_entry.save(update_fields=['left_at'])

        if nearest_addr:
            AddressQueueEntry.objects.create(address=nearest_addr, driver=driver)
            if driver.pending_stand_lat is not None:
                driver.pending_stand_lat = None
                driver.pending_stand_lng = None
                driver.pending_stand_since = None
                driver.save(update_fields=['pending_stand_lat', 'pending_stand_lng', 'pending_stand_since'])
            return

        # Bu yerga faqat yaqin atrofda HECH QANDAY SavedAddress topilmaganda
        # kelinadi. Operator oldindan manzil kiritmagan bo'lsa ham tizim
        # o'zi ishlayversin deb — haydovchi shu nuqtada yetarlicha uzoq
        # (AUTO_ADDRESS_DWELL_MINUTES) turib qolsa, YANGI SavedAddress
        # avtomatik yaratiladi. Faqat ish holatidagi (is_on_duty) haydovchilar
        # uchun — aks holda oddiy uydan/ko'chadan o'tayotgan onlaynsiz
        # haydovchi ham manzil "yaratib" yurardi.
        if not driver.is_on_duty:
            return

        anchor_dist = None
        if driver.pending_stand_lat is not None and driver.pending_stand_lng is not None:
            anchor_dist = haversine(lat, lng, driver.pending_stand_lat, driver.pending_stand_lng)

        if anchor_dist is None or anchor_dist > AUTO_ADDRESS_DWELL_RADIUS_KM:
            # Yangi "nomzod" nuqta — hisoblash shu yerdan qayta boshlanadi
            # (haydovchi harakatlanmoqda yoki bu birinchi urinish).
            driver.pending_stand_lat = lat
            driver.pending_stand_lng = lng
            driver.pending_stand_since = timezone.now()
            driver.save(update_fields=['pending_stand_lat', 'pending_stand_lng', 'pending_stand_since'])
            return

        dwell_minutes = (timezone.now() - driver.pending_stand_since).total_seconds() / 60
        if dwell_minutes < AUTO_ADDRESS_DWELL_MINUTES:
            return  # hali yetarlicha turmadi

        from taxi.models import SavedAddress

        # Yaratishdan OLDIN — kengroq radiusda "bu joy allaqachon bormi"
        # tekshiriladi (duplikat manzillarning oldini olish uchun). Topilsa,
        # YANGISINI yaratmasdan o'sha mavjud manzilga qo'shiladi — xuddi
        # oddiy (1km) moslik topilgandagi kabi.
        wider_match = find_matching_saved_address(lat, lng, radius_km=AUTO_ADDRESS_DEDUPE_RADIUS_KM)
        if wider_match:
            AddressQueueEntry.objects.create(address=wider_match, driver=driver)
            driver.pending_stand_lat = None
            driver.pending_stand_lng = None
            driver.pending_stand_since = None
            driver.save(update_fields=['pending_stand_lat', 'pending_stand_lng', 'pending_stand_since'])
            return

        name = reverse_geocode_address(lat, lng) or f'Nomsiz manzil ({lat:.4f}, {lng:.4f})'
        # Tuman ham avtomatik biriktiriladi — operator har bir avtomatik
        # manzilga qo'lda tuman tanlab o'tirmasin. Aniqlab bo'lmasa (masalan
        # geocoder javob bermasa) — district=None qoladi, keyin qo'lda
        # to'g'irlash mumkin, bu xato emas.
        region_name, district_name = reverse_geocode_admin_area(lat, lng)
        region_obj = _match_region(region_name) if region_name else None
        district_obj = _resolve_district(region_obj, district_name) if region_obj and district_name else None
        new_addr = SavedAddress.objects.create(
            name=name[:100], address=name[:255], lat=lat, lng=lng,
            district=district_obj, auto_created=True,
        )
        AddressQueueEntry.objects.create(address=new_addr, driver=driver)
        driver.pending_stand_lat = None
        driver.pending_stand_lng = None
        driver.pending_stand_since = None
        driver.save(update_fields=['pending_stand_lat', 'pending_stand_lng', 'pending_stand_since'])


def _next_address_queue_driver(address, rejected_ids):
    """Manzil navbatida hozir turgan (hali chiqib ketmagan, ish holatida)
    haydovchilardan eng oldin kelganini qaytaradi — rad etganlar/urinilganlar
    hisobga olinmaydi.

    Avval so'nggi ADDRESS_QUEUE_STALE_MINUTES ichida faol (Driver.last_seen)
    bo'lganlar orasidan tanlanadi. Agar ULAR HECH BIRI topilmasa (masalan,
    navbatdagi hamma haydovchi ilova fonga o'tib/ekran qulflanib qolgani
    sababli last_seen bir necha soniyaga kechikkan bo'lsa — bu haqiqiy
    "ketib qolgan" emas, shunchaki vaqtinchalik), navbat butunlay
    tashlab yuborilmaydi: staleness filtri e'tiborga olinmasdan, baribir
    navbatdagi eng birinchisiga taklif qilinadi. Aks holda dispatch_order()
    bu manzilni "navbat bo'sh" deb hisoblab, buyurtmani manzil bilan
    hech qanday aloqasi yo'q butun faol haydovchilar to'dasiga ochib
    yuborardi — navbatda turganlar chetda qolib."""
    from taxi.models import AddressQueueEntry
    from django.utils import timezone
    import datetime

    base_qs = (
        AddressQueueEntry.objects.filter(
            address=address, left_at__isnull=True,
            driver__is_active=True, driver__is_on_duty=True,
            driver__approval_status='approved',
        )
        .exclude(driver_id__in=rejected_ids)
        .select_related('driver')
        .order_by('joined_at')
    )

    stale_cutoff = timezone.now() - datetime.timedelta(minutes=ADDRESS_QUEUE_STALE_MINUTES)
    entry = base_qs.filter(driver__last_seen__gte=stale_cutoff).first()
    if not entry:
        entry = base_qs.first()
    return entry.driver if entry else None


# Shuncha soniya hech kim tomonidan qabul qilinmay "kutib qolgan" buyurtma
# uchun — balans komissiyadan kam bo'lsa ham QARZGA (balans manfiy bo'lib)
# qabul qilishga ruxsat beriladi. Aks holda atrofda FAQAT past balansli
# haydovchi(lar) qolgan holatda, mijoz butunlay xizmatsiz qolib ketardi —
# komissiya yig'ishdan ko'ra, buyurtmani BAJARISH ustun qo'yiladi.
ORDER_DEBT_ACCEPT_AGE_SECONDS = 120


def order_credit_accept_allowed(order):
    """`order.created_at`dan beri `ORDER_DEBT_ACCEPT_AGE_SECONDS`dan ko'proq
    vaqt o'tganmi — ya'ni bu buyurtma "kutib qolgan" hisoblanadimi."""
    from django.utils import timezone
    return (timezone.now() - order.created_at).total_seconds() >= ORDER_DEBT_ACCEPT_AGE_SECONDS


def mark_driver_debt_from_order(driver, order, commission):
    """Haydovchi balansi komissiyadan kam bo'lsa ham (`order_credit_accept_allowed`
    orqali) qabul qilishga ruxsat berilganda chaqiriladi. Diqqat: bu
    ODATDAGI qo'lda "Qarzdor" belgilashdan (`driver_toggle_qarz`, operator
    ANIQ shu qarorni qabul qiladi) farq qiladi — bu yerda TIZIM O'ZI qaror
    qabul qilgani uchun, operator buni ALBATTA ko'rib, kuzatib borishi
    uchun avtomatik "Qarzdorlar" ro'yxatiga qo'shiladi (agar hali u yerda
    bo'lmasa — allaqachon qarzdor bo'lsa, mavjud izoh saqlanib qoladi)."""
    from django.utils import timezone
    from .models import DriverActivityLog

    note = (
        f"Buyurtma #{order.id} — balans yetarli bo'lmasa ham (buyurtma "
        f"{ORDER_DEBT_ACCEPT_AGE_SECONDS // 60} daqiqadan ko'p kutib qolgani uchun) qarzga qabul qilindi"
    )[:255]
    if not driver.is_qarzdor:
        driver.is_qarzdor = True
        driver.qarz_note = note
        driver.qarz_marked_at = timezone.now()
        driver.save(update_fields=['is_qarzdor', 'qarz_note', 'qarz_marked_at'])
    DriverActivityLog.objects.create(driver=driver, action=DriverActivityLog.ACTION_QARZ_ON, detail=note)


def dispatch_order(order):
    """
    Buyurtmani navbatma-navbat eng yaqin/adolatli haydovchilarga yuborish.

    Agar buyurtma manzili (from_lat/from_lng) operator panelda saqlangan
    tezkor manzillardan (Manzillar) biriga yaqin bo'lsa — bu yerda oddiy
    "eng yaqin/adolatli" hisob-kitob ISHLATILMAYDI, buning o'rniga soddaroq
    "taksi bekati navbati" mantig'i ishlaydi: o'sha manzilga eng oldin kelib
    turgan haydovchiga taklif qilinadi, rad etsa/javob bermasa navbatdagi
    keyingisiga (ko'pi bilan ADDRESS_QUEUE_MAX_ATTEMPTS=3 tagacha), hech kim
    olmasa umumiy tabloga (hammaga baravar) tushadi.

    Aks holda (manzil navbatiga tegishli bo'lmasa) — TariffSettings dagi
    Score (masofa + adolat vazni − kutish bonusi) bo'yicha eng mos
    haydovchi tanlanadi, max_dispatch_attempts sonigacha urinadi.
    """
    from django.utils import timezone
    from taxi.models import TariffSettings, Driver

    # Order yangi holatda bo'lishi kerak
    if order.status != 'pending':
        return None

    if not order.from_lat or not order.from_lng:
        return None

    tariff = TariffSettings.get()
    attempts_count = order.rejected_by.count()
    rejected_ids = list(order.rejected_by.values_list('id', flat=True))

    address = find_matching_saved_address(order.from_lat, order.from_lng)

    if address:
        # ── Manzil navbati (sodda, "kim birinchi kelgan") ──
        if attempts_count >= ADDRESS_QUEUE_MAX_ATTEMPTS:
            if order.dispatched_to is not None:
                order.dispatched_to = None
                order.save(update_fields=['dispatched_to'])
            return None
        nearest = _next_address_queue_driver(address, rejected_ids)
        if not nearest:
            if order.dispatched_to is not None:
                order.dispatched_to = None
                order.save(update_fields=['dispatched_to'])
            return None
        dist = haversine(order.from_lat, order.from_lng, nearest.latitude, nearest.longitude)
    else:
        # ── Oddiy Score bo'yicha taqsimlash ──
        if attempts_count >= tariff.max_dispatch_attempts:
            if order.dispatched_to is not None:
                order.dispatched_to = None
                order.save(update_fields=['dispatched_to'])
            return None

        candidates = list(
            Driver.objects.filter(
                is_active=True,
                is_on_duty=True,
                approval_status='approved',
                latitude__isnull=False,
                longitude__isnull=False,
            ).exclude(id__in=rejected_ids)
        )
        if not candidates:
            if order.dispatched_to is not None:
                order.dispatched_to = None
                order.save(update_fields=['dispatched_to'])
            return None

        nearest, dist = find_fairest_driver(
            candidates, order.from_lat, order.from_lng,
            tariff.fairness_weight_km, tariff.fairness_max_radius_km,
        )
        if not nearest:
            if order.dispatched_to is not None:
                order.dispatched_to = None
                order.save(update_fields=['dispatched_to'])
            return None

    order.dispatched_to = nearest
    order.dispatched_at = timezone.now()
    order.save(update_fields=['dispatched_to', 'dispatched_at'])
    _log_dispatch_attempt(order, nearest, dist if dist and dist != float('inf') else None)

    notify_driver_new_order(order, nearest)
    start_dispatch_timeout(order, nearest, tariff.dispatch_timeout)

    return nearest


def notify_driver_new_order(order, driver):
    """Buyurtma biror haydovchiga tayinlanganda (avtomatik dispatch_order()
    orqali yoki operator tomonidan qo'lda) unga FCM push, Web Push va
    Telegram orqali xabar yuborish — ikkala holatda ham bir xil ishlaydi."""
    body = f"📍 {order.from_address}" + (f" → {order.to_address}" if order.to_address else "")
    if order.note:
        body += f"\n📝 {order.note}"
    send_fcm(
        driver.fcm_token,
        title='🚖 Yangi buyurtma!',
        body=body,
        data={
            'type':       'new_order',
            'order_id':   str(order.id),
            'from_addr':  order.from_address,
            'to_addr':    order.to_address or '',
            'note':       order.note or '',
            'price':      str(order.price or ''),
            'client_phone': order.client.phone_number,
        },
    )
    try:
        from taxi.driver_views import send_push_to_driver
        body = f"📍 {order.from_address}"
        if order.price:
            body += f" | 💰 {int(order.price):,} so'm"
        send_push_to_driver(driver, '🚖 Yangi buyurtma!', body)
    except Exception:
        pass
    sms_driver_event(driver, 'new_order', order=order)
    tg_order_dispatched(order, driver)


def start_dispatch_timeout(order, driver, timeout_seconds):
    """Belgilangan haydovchi (avtomatik yoki operator tomonidan qo'lda
    tayinlangan bo'lsa ham) dispatch_timeout ichida javob bermasa, uni
    rad etganlar ro'yxatiga qo'shib, buyurtmani avtomatik bo'shatish uchun
    fon taymeri. Shu bilan operator qo'lda tayinlagan buyurtma ham
    javobsiz haydovchiga abadiy "osilib qolmaydi"."""
    import threading
    threading.Thread(
        target=auto_reject_timeout,
        args=(order.id, driver.id, timeout_seconds),
        daemon=True
    ).start()


# O'zbekcha matn faqat lotin (o', g' kabi maxsus harflar bilan) yoki kirill
# alifbosida bo'ladi — Whisper ba'zan boshqa tilga (arabcha/forscha, xitoycha
# va h.k.) chalkashib ketsa, natija shu skriptlardan birida chiqadi.
_NON_UZBEK_SCRIPT_RE = re.compile(
    '['
    '؀-ۿݐ-ݿ'  # arabcha / forscha
    '一-鿿぀-ヿ'  # xitoycha / yaponcha
    '가-힯'               # koreyscha
    'ऀ-ॿ'               # hindcha (devanagari)
    '֐-׿'               # ibroniycha
    '฀-๿'               # tailandcha
    ']'
)

# Telefon raqamni ovoz bilan aytganda Whisper ba'zan raqamlarni so'z bilan
# ("to'qson besh" kabi) yozadi — shu so'zlarni raqamga o'giramiz.
_UZ_PHONE_UNITS = {
    'nol': '0', 'bir': '1', 'ikki': '2', 'uch': '3',
    "to'rt": '4', 'tort': '4', 'besh': '5', 'olti': '6',
    'yetti': '7', 'sakkiz': '8', "to'qqiz": '9', 'toqqiz': '9',
}
_UZ_PHONE_TENS = {
    "o'n": 10, 'on': 10, 'yigirma': 20, "o'ttiz": 30, 'ottiz': 30,
    'qirq': 40, 'ellik': 50, 'oltmish': 60, 'yetmish': 70,
    'sakson': 80, "to'qson": 90, 'toqson': 90,
}


def parse_uz_spoken_phone(text):
    """Whisper'dan kelgan matnni (raqamlar so'z bilan yoki numerik holda
    aytilgan bo'lishi mumkin) '+998 XX XXX XX XX' formatidagi telefon
    raqamiga o'giradi. (raqam_yoki_None, xato_matni_yoki_None) qaytaradi."""
    norm = text.lower().replace('’', "'").replace('‘', "'").replace('`', "'")
    tokens = re.findall(r"[a-z']+|\d+", norm)

    digits = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok.isdigit():
            digits.append(tok)
            i += 1
        elif tok in _UZ_PHONE_TENS:
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            if nxt in _UZ_PHONE_UNITS and _UZ_PHONE_UNITS[nxt] != '0':
                digits.append(str(_UZ_PHONE_TENS[tok] + int(_UZ_PHONE_UNITS[nxt])))
                i += 2
            else:
                digits.append(str(_UZ_PHONE_TENS[tok]))
                i += 1
        elif tok in _UZ_PHONE_UNITS:
            digits.append(_UZ_PHONE_UNITS[tok])
            i += 1
        else:
            i += 1  # "raqam", "telefon", "plyus" kabi so'zlar e'tiborsiz qoldiriladi

    all_digits = ''.join(digits)
    if all_digits.startswith('998') and len(all_digits) == 12:
        local = all_digits[3:]
    elif len(all_digits) == 9:
        local = all_digits
    else:
        return None, "Telefon raqam tushunilmadi — iltimos, raqamlarni birma-bir aniqroq ayting"

    return f"+998 {local[0:2]} {local[2:5]} {local[5:7]} {local[7:9]}", None


def transcribe_audio_uz(audio_bytes, filename='speech.webm', content_type='audio/webm'):
    """Ovoz yozuvini (masalan buyurtma oynasidagi mikrofon tugmasi orqali
    yozilgan manzil) OpenAI Whisper orqali o'zbekcha matnga o'giradi.
    (matn_yoki_None, xato_matni_yoki_None) qaytaradi."""
    import uuid
    from taxi.models import AiSettings

    cfg = AiSettings.get()
    if not cfg.api_key:
        return None, "OpenAI API kalit sozlanmagan (Sozlamalar > AI)"

    boundary = uuid.uuid4().hex
    parts = []
    # Diqqat: OpenAI transcriptions endpointi 'uz' (o'zbekcha) tilini
    # 'language' parametrida rasman qo'llab-quvvatlamaydi (xato qaytaradi) —
    # shu sabab tilni ko'rsatmaymiz. O'rniga 'prompt' orqali o'zbekcha lotin
    # yozuvidagi manzil namunasi beramiz — Whisper shu uslub/tilni davom
    # ettirishga moyil bo'ladi, aks holda ba'zan arabcha/forscha kabi
    # aloqasiz tillarga chalkashib ketishi mumkin edi.
    for name, value in (
        ('model',  'whisper-1'),
        ('prompt', "Toshkent shahri, Chilonzor tumani, Bunyodkor ko'chasi, 12-uy."),
    ):
        parts.append(f'--{boundary}'.encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"'.encode())
        parts.append(b'')
        parts.append(value.encode())
    parts.append(f'--{boundary}'.encode())
    parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
    parts.append(f'Content-Type: {content_type}'.encode())
    parts.append(b'')
    parts.append(audio_bytes)
    parts.append(f'--{boundary}--'.encode())
    parts.append(b'')
    body = b'\r\n'.join(parts)

    req = urllib.request.Request(
        'https://api.openai.com/v1/audio/transcriptions',
        data=body,
        headers={
            'Authorization': f'Bearer {cfg.api_key}',
            'Content-Type': f'multipart/form-data; boundary={boundary}',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        text = (data.get('text') or '').strip()
        if not text:
            return None, "Ovozda matn topilmadi"
        if _NON_UZBEK_SCRIPT_RE.search(text):
            return None, "Til noto'g'ri aniqlandi (o'zbekcha emas) — iltimos, yana bir bor aniqroq gapiring"
        return text, None
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode()).get('error', {}).get('message', str(e))
        except Exception:
            err = str(e)
        return None, err
    except Exception as e:
        return None, str(e)


def generate_growth_insights(stats):
    """Joriy statistika asosida OpenAI'dan taksi biznesini rivojlantirish bo'yicha
    qadam-baqadam tavsiyalar, top haydovchi/mijoz uchun sovg'a taklifi va orqaga
    ketish bo'lsa ogohlantirish so'raydi. (ok, dict_yoki_xato_matni) qaytaradi.
    dict — {'tavsiyalar': [{'sarlavha','tavsif'}...], 'top_haydovchi_sovrini': str,
    'top_mijoz_sovrini': str, 'ogohlantirish': str}."""
    try:
        from taxi.models import AiSettings
        cfg = AiSettings.get()
    except Exception:
        return False, 'AI sozlamalari topilmadi'

    if not cfg.api_key:
        return False, 'OpenAI API kalit kiritilmagan — AI sozlamalari sahifasidan kiriting'

    prompt = (
        "Sen taksi xizmati uchun o'sish va operatsion samaradorlik bo'yicha tajribali maslahatchisan. "
        "Quyidagi joriy statistika asosida to'rtta narsani tayyorla. Faqat o'zbek tilida yoz. "
        "Matn ichida markdown belgilaridan (**, #, -, *) foydalanma — oddiy tekst yoz.\n\n"
        "1) tavsiyalar: buyurtmalar va qo'ng'iroqlar sonini oshirish, biznesni rivojlantirish uchun "
        "4-6 ta aniq, amaliy va qadama-qadam bajarish mumkin bo'lgan tavsiya. Har biri qisqa sarlavha "
        "va 1-2 gapli aniq tushuntirishdan iborat bo'lsin. Statistikaning turli qirralariga tegishli "
        "bo'lsin (marketing, haydovchilarni rag'batlantirish, narxlash, mijozlarni ushlab qolish, "
        "bekor qilishlarni kamaytirish va h.k.) — bir xil g'oyani takrorlama.\n"
        "2) top_haydovchi_sovrini: 'oyning_eng_faol_haydovchisi' maydonidagi haydovchi uchun aniq, "
        "amalga oshirish mumkin bo'lgan rag'batlantirish/sovg'a taklifi (masalan bonus miqdori yoki "
        "unvon) — 1-2 gap. Agar bu maydon bo'sh bo'lsa, bo'sh satr qaytar.\n"
        "3) top_mijoz_sovrini: 'oyning_eng_faol_mijozi' maydonidagi mijoz uchun xuddi shunday sovg'a/"
        "chegirma taklifi — 1-2 gap. Agar bu maydon bo'sh bo'lsa, bo'sh satr qaytar.\n"
        "4) ogohlantirish: agar 'buyurtmalar_ozgarish_foizi' yoki 'daromad_ozgarish_foizi' manfiy va "
        "sezilarli (taxminan -10% yoki undan yomon) bo'lsa, aniq nima orqaga ketayotganini va nega "
        "shoshilinch chora ko'rish kerakligini tushuntiruvchi qisqa va keskin ogohlantirish matni yoz "
        "(2-3 gap). Agar orqaga ketish bo'lmasa yoki ma'lumot yetarli bo'lmasa (None), bo'sh satr "
        "qaytar — soxta ogohlantirish yozma.\n\n"
        "Javobni faqat quyidagi JSON formatda qaytar, boshqa hech narsa yozma:\n"
        '{"tavsiyalar": [{"sarlavha": "...", "tavsif": "..."}], '
        '"top_haydovchi_sovrini": "...", "top_mijoz_sovrini": "...", "ogohlantirish": "..."}\n\n'
        f"Statistika:\n{json.dumps(stats, ensure_ascii=False, indent=2)}"
    )

    payload = json.dumps({
        'model': cfg.model or 'gpt-4o-mini',
        'messages': [{'role': 'user', 'content': prompt}],
        'temperature': 0.7,
        'response_format': {'type': 'json_object'},
    }).encode()
    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=payload,
        headers={
            'Authorization': f'Bearer {cfg.api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        content = data['choices'][0]['message']['content'].strip()
        parsed = json.loads(content)
        raw_items = parsed.get('tavsiyalar') or []
        items = [
            {'sarlavha': str(it.get('sarlavha', '')).strip(),
             'tavsif':   str(it.get('tavsif', '')).strip()}
            for it in raw_items if isinstance(it, dict) and (it.get('sarlavha') or it.get('tavsif'))
        ]
        if not items:
            return False, "AI javobini o'qib bo'lmadi, qayta urinib ko'ring"
        return True, {
            'tavsiyalar':            items,
            'top_haydovchi_sovrini': str(parsed.get('top_haydovchi_sovrini') or '').strip(),
            'top_mijoz_sovrini':     str(parsed.get('top_mijoz_sovrini') or '').strip(),
            'ogohlantirish':         str(parsed.get('ogohlantirish') or '').strip(),
        }
    except urllib.error.HTTPError as e:
        try:
            err = json.loads(e.read().decode())
            msg = err.get('error', {}).get('message', str(e))
        except Exception:
            msg = str(e)
        return False, f'OpenAI xatosi: {msg}'
    except (KeyError, json.JSONDecodeError):
        return False, "AI javobini o'qib bo'lmadi, qayta urinib ko'ring"
    except Exception as e:
        return False, f'Tarmoq xatosi: {e}'


AI_CHAT_TOOLS = [
    {
        'type': 'function',
        'function': {
            'name': 'cancel_active_order',
            'description': "Haydovchining joriy faol buyurtmasini bekor qiladi. FAQAT haydovchi aniq tasdiqlagandan keyin chaqir.",
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'toggle_duty_status',
            'description': "Haydovchining onlayn/oflayn (navbat) holatini almashtiradi — hozir onlayn bo'lsa oflaynga, aksincha. Past xavfli amal, alohida tasdiq so'rash shart emas.",
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_today_stats',
            'description': "Haydovchining BUGUNGI yakunlangan buyurtmalar soni va jami daromadini qaytaradi. Faqat ma'lumot beradi, hech narsani o'zgartirmaydi.",
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'explain_rating',
            'description': "Haydovchining reytingi so'nggi 30 kunda nega shunday ekanini (nechta buyurtma yakunlagani/bekor qilgani asosida) tushuntiradi. Faqat ma'lumot beradi.",
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_nearby_queue_info',
            'description': "Haydovchining joriy GPS'iga eng yaqin saqlangan manzillarda hozir nechta haydovchi navbatda turganini qaytaradi. Faqat ma'lumot beradi.",
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'get_balance_history',
            'description': "Haydovchining so'nggi balans to'ldirish so'rovlari tarixini (summa, sana, holati) qaytaradi. Faqat ma'lumot beradi.",
            'parameters': {'type': 'object', 'properties': {}, 'required': []},
        },
    },
    {
        'type': 'function',
        'function': {
            'name': 'escalate_to_operator',
            'description': "Sen yecha olmaydigan yoki haydovchi aniq 'odam bilan gaplashmoqchiman' degan muammoni operatorlar guruhiga USTUVOR (shoshilinch) belgi bilan yuboradi.",
            'parameters': {
                'type': 'object',
                'properties': {'reason': {'type': 'string', 'description': "Muammoning qisqa tavsifi, o'zbek tilida"}},
                'required': ['reason'],
            },
        },
    },
]


def generate_ai_chat_reply(driver, history):
    """Haydovchi ilovasidagi "Chat" bo'limida AI yordamchi javobini
    generatsiya qiladi — `generate_growth_insights()` bilan bir xil xom
    HTTP naqsh (`openai` python paketisiz), faqat bu yerda OpenAI'ning
    "function calling" (`tools`, `AI_CHAT_TOOLS`) imkoniyati ham
    ishlatiladi, chunki AI haqiqiy amallar (buyurtmani bekor qilish,
    onlayn/oflayn almashtirish, operatorga eskalatsiya) so'ray olishi kerak.

    `history` — [{'role': 'user'|'assistant', 'content': str}, ...]
    (oxirgi ChatMessage'lardan qurilgan, eng eskisi birinchi).

    Qaytaradi: (reply_text, tool_name, tool_args) — `tool_name` odatda
    `None`. AI biror funksiyani chaqirishga qaror qilsa, shu funksiya nomi
    va argumentlari (dict) qaytadi — bu holda `reply_text` odatda bo'sh
    bo'ladi, chaqiruvchi mos `ai_*()` funksiyasini ishga tushirib, UNING
    natijasini haqiqiy javob sifatida yozadi. Xato/sozlanmagan holatda
    (None, None, None) — chaqiruvchi jim o'tkazib yuboradi, operator
    odatdagidek qo'lda javob beraveradi."""
    try:
        from taxi.models import AiSettings, Order, TariffSettings
        from django.utils import timezone
        cfg = AiSettings.get()
    except Exception:
        return None, None, None

    if not cfg.api_key or not cfg.chat_ai_enabled:
        return None, None, None

    active_order = Order.objects.filter(driver=driver, status__in=Order.ACTIVE_STATUSES).order_by('-id').first()
    if active_order:
        order_context = (
            f"Hozir faol buyurtmasi bor: #{active_order.id}, holati "
            f"'{active_order.get_status_display()}', manzil: {active_order.from_address}."
        )
    else:
        order_context = "Hozir faol buyurtmasi yo'q."

    tariff = TariffSettings.get()
    tariff_context = (
        f"Joriy tarif: bazaviy narx {tariff.base_price} so'm, km narxi {tariff.price_per_km} so'm, "
        f"kutish (1 daqiqa) {tariff.waiting_price_per_minute} so'm, komissiya {tariff.commission} so'm."
    )

    recent_orders = Order.objects.filter(driver=driver, status='completed').order_by('-created_at')[:5]
    if recent_orders:
        lines = []
        for o in recent_orders:
            when = timezone.localtime(o.created_at).strftime('%d.%m %H:%M') if o.created_at else '?'
            lines.append(f"- {when}: {o.from_address} → {o.to_address or '?'}, {o.price or 0} so'm")
        history_context = "So'nggi yakunlangan buyurtmalari:\n" + "\n".join(lines)
    else:
        history_context = "Hali yakunlangan buyurtmasi yo'q."

    system_prompt = (
        "Sen Vijdon Taxi haydovchilar ilovasidagi \"Chat\" bo'limidagi AI yordamchisan. "
        "Faqat shu haydovchining O'ZIGA tegishli savollariga (ish tartibi, buyurtma, balans, "
        "navbat, tarif, umumiy savol-javob) qisqa va aniq, faqat o'zbek tilida javob ber. "
        "Boshqa haydovchi/mijoz haqida ma'lumot bera olmaysan va berma.\n\n"
        f"Haydovchi: {driver.full_name}. Balansi: {driver.balance} so'm. "
        f"Holati: {'onlayn' if driver.is_on_duty else 'oflayn'}. {order_context}\n"
        f"{tariff_context}\n"
        f"{history_context}\n\n"
        "Amallar bo'yicha qoidalar:\n"
        "1) Buyurtmani bekor qilish — ENG XAVFLI amal. Haydovchi so'raganda AVVAL qaysi "
        "buyurtma ekanini (yuqoridagi kontekstdan) tasdiqla va ANIQ savol ber (\"#{id} "
        "buyurtmasini bekor qilishni tasdiqlaysizmi?\"). Haydovchi ANIQ ha/tasdiq (\"ha\", "
        "\"tasdiqlayman\", \"bekor qil\" kabi qat'iy javob) BERGANDAN KEYINGINA "
        "`cancel_active_order` funksiyasini chaqir — birinchi so'ragan zahoti emas.\n"
        "2) Onlayn/oflayn almashtirish (`toggle_duty_status`) — past xavfli, so'ralishi "
        "bilan darhol chaqirsang bo'ladi, qo'shimcha tasdiq shart emas.\n"
        "3) Bugungi statistika (`get_today_stats`), reyting tushuntirishi (`explain_rating`), "
        "yaqin manzillardagi navbat holati (`get_nearby_queue_info`), balans to'ldirish "
        "tarixi (`get_balance_history`) — hammasi faqat ma'lumot beradi, darhol chaqirsang "
        "bo'ladi, tasdiq shart emas.\n"
        "4) Agar haydovchining muammosini o'zing hal qila olmasang, yoki u aniq odam bilan "
        "gaplashmoqchi bo'lsa — `escalate_to_operator`ni qisqa sabab bilan chaqir.\n"
        "5) Balansni TO'LDIRISHNI (yangi so'rov yaratishni) so'rasa — o'zing amalga oshira "
        "olmaysing (chek rasmi kerak, senda rasm yuklash imkoniyati yo'q). Buning o'rniga: "
        "ilovadagi \"Balans\" bo'limiga o'tib, \"To'ldirish\" tugmasini bosib, to'lov chekini "
        "rasmga olib yuklashi kerakligini tushuntir. Lekin AVVALGI to'ldirish so'rovlari "
        "TARIXINI so'rasa (masalan \"oxirgi to'ldirishlarim\"), `get_balance_history`ni chaqir.\n"
        "Agar faol buyurtma yo'q bo'lsa, `cancel_active_order` chaqirma — buni aytib qo'y."
    )

    messages = [{'role': 'system', 'content': system_prompt}] + history
    payload = json.dumps({
        'model': cfg.model or 'gpt-4o-mini',
        'messages': messages,
        'temperature': 0.4,
        'tools': AI_CHAT_TOOLS,
        'tool_choice': 'auto',
    }).encode()
    req = urllib.request.Request(
        'https://api.openai.com/v1/chat/completions',
        data=payload,
        headers={
            'Authorization': f'Bearer {cfg.api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        message = data['choices'][0]['message']
        tool_calls = message.get('tool_calls') or []
        if tool_calls:
            call = tool_calls[0]
            fn = call.get('function', {})
            name = fn.get('name')
            try:
                args = json.loads(fn.get('arguments') or '{}')
            except (TypeError, json.JSONDecodeError):
                args = {}
            if name in {t['function']['name'] for t in AI_CHAT_TOOLS}:
                return None, name, args
        reply = (message.get('content') or '').strip()
        if not reply:
            return None, None, None
        return reply, None, None
    except Exception:
        return None, None, None


def ai_toggle_duty(driver):
    """AI-chat orqali onlayn/oflayn holatini almashtiradi —
    `driverapp_views.py:duty_toggle`dagi bilan bir xil mantiq (navbat
    yozuvini yopish, faoliyat jurnali, Telegram xabari), faqat `request`
    obyektisiz (fon oqimida ishlaydi) chaqirish mumkin bo'lishi uchun
    `_log_activity()` o'rniga to'g'ridan-to'g'ri yoziladi."""
    from django.utils import timezone
    from taxi.models import AddressQueueEntry, DriverActivityLog

    driver.is_on_duty = not driver.is_on_duty
    driver.save(update_fields=['is_on_duty'])
    if not driver.is_on_duty:
        AddressQueueEntry.objects.filter(driver=driver, left_at__isnull=True).update(left_at=timezone.now())
    action = DriverActivityLog.ACTION_DUTY_ON if driver.is_on_duty else DriverActivityLog.ACTION_DUTY_OFF
    DriverActivityLog.objects.create(driver=driver, action=action, detail='AI-chat orqali', ip_address=None, user_agent='AI-chat')
    tg_duty_changed(driver, driver.is_on_duty)
    state = 'onlayn' if driver.is_on_duty else 'oflayn'
    return True, f"Endi siz {state}siz."


def ai_today_stats(driver):
    """AI-chat orqali — haydovchining bugungi yakunlangan buyurtmalari
    soni va jami daromadini qaytaradi. Faqat o'qish, hech narsa
    o'zgartirmaydi."""
    from django.utils import timezone
    from django.db.models import Sum, Count
    from taxi.models import Order

    today = timezone.localdate()
    agg = Order.objects.filter(
        driver=driver, status='completed', created_at__date=today,
    ).aggregate(count=Count('id'), total=Sum('price'))
    count = agg['count'] or 0
    total = agg['total'] or 0
    if count == 0:
        return True, "Bugun hali yakunlangan buyurtmangiz yo'q."
    return True, f"Bugun {count} ta buyurtma yakunladingiz, jami {total:.0f} so'm ishladingiz."


def ai_escalate_to_operator(driver, reason):
    """AI-chat orqali — AI o'zi yecha olmaydigan yoki haydovchi aniq odam
    bilan gaplashmoqchi bo'lgan holatni operatorlar guruhiga USTUVOR
    belgi bilan yuboradi (oddiy xabarlar ham Telegramga ketadi,
    `chat_private_send`da — bu ALOHIDA, ko'zga tashlanadigan shoshilinch
    xabar)."""
    reason = (reason or "aniqlanmagan").strip()
    send_telegram(
        f"🚨 <b>USTUVOR — AI yordamchi operator e'tiborini so'ramoqda</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>\n"
        f"Sabab: {reason}",
    )
    return True, "Operatorlarga xabar berdim, tez orada siz bilan bog'lanishadi."


def ai_explain_rating(driver):
    """AI-chat orqali — reyting so'nggi 30 kunda NEGA shunday ekanini
    (nechta buyurtma yakunlagani/bekor qilgani asosida) tushuntiradi.
    Aniq arifmetik hisob-kitob va'da qilmaydi (reyting MIN/MAX'da
    to'xtab qolgan bo'lishi mumkin) — faqat umumiy tendensiyani ko'rsatadi."""
    from django.utils import timezone
    import datetime
    from taxi.models import Order

    cutoff = timezone.now() - datetime.timedelta(days=30)
    completed = Order.objects.filter(driver=driver, status='completed', updated_at__gte=cutoff).count()
    cancelled = Order.objects.filter(driver=driver, status='cancelled', updated_at__gte=cutoff).count()
    if completed == 0 and cancelled == 0:
        return True, f"So'nggi 30 kunda buyurtma tarixingiz yo'q. Joriy reytingingiz: {driver.rating}."
    text = (
        f"So'nggi 30 kunda {completed} ta buyurtma yakunladingiz (har biri reytingni ozgina "
        f"ko'taradi) va {cancelled} ta buyurtma bekor qilindi (har biri sezilarli pasaytiradi). "
        f"Joriy reytingingiz: {driver.rating}. "
    )
    if cancelled > 0:
        text += "Reytingni ko'tarish uchun buyurtmalarni kamroq bekor qilib, ko'proq yakunlang."
    return True, text


def ai_nearby_queue_info(driver):
    """AI-chat orqali — haydovchining joriy GPS'iga eng yaqin saqlangan
    manzillarda hozir nechta haydovchi navbatda turganini qaytaradi
    (`driver_all_addresses`/`addresses_list`dagi bilan bir xil bulk
    Count() hisoblash, faqat matn ko'rinishida)."""
    import datetime
    from django.db.models import Count, Q as DQ
    from django.utils import timezone
    from taxi.models import SavedAddress

    online_cutoff = timezone.now() - datetime.timedelta(seconds=120)
    addresses = list(SavedAddress.objects.annotate(
        queue_count=Count('queue_entries', filter=DQ(
            queue_entries__left_at__isnull=True, queue_entries__driver__is_active=True,
            queue_entries__driver__is_on_duty=True, queue_entries__driver__approval_status='approved',
            queue_entries__driver__last_seen__gte=online_cutoff,
        )),
    ))
    if not addresses:
        return True, "Hozircha saqlangan manzillar yo'q."
    if driver.latitude and driver.longitude:
        addresses.sort(key=lambda a: haversine(driver.latitude, driver.longitude, a.lat, a.lng) or float('inf'))
    addresses = addresses[:6]
    lines = [f"- {a.name}: {a.queue_count} kishi navbatda" for a in addresses]
    return True, "Yaqin manzillardagi navbat holati:\n" + "\n".join(lines)


def ai_balance_history(driver):
    """AI-chat orqali — so'nggi balans to'ldirish so'rovlari tarixini
    (summa, sana, holati) qaytaradi."""
    from django.utils import timezone
    from taxi.models import BalanceTopupRequest

    recent = BalanceTopupRequest.objects.filter(driver=driver).order_by('-created_at')[:5]
    if not recent:
        return True, "Hali birorta balans to'ldirish so'rovingiz yo'q."
    lines = []
    for r in recent:
        when = timezone.localtime(r.created_at).strftime('%d.%m.%Y')
        lines.append(f"- {when}: {r.amount} so'm — {r.get_status_display()}")
    return True, "So'nggi to'ldirish so'rovlaringiz:\n" + "\n".join(lines)


def build_contract_pdf(contract, driver=None, signature=None):
    """Shartnoma matnidan bitta sahifaga sig'adigan, chop etishga mos ikki
    ustunli (gazeta uslubi) PDF quradi (BytesIO qaytaradi). `driver`/`signature`
    berilsa — haydovchi ma'lumotlari va raqamli imzo rasmi hujjat oxiriga
    qo'shiladi. Aks holda (imzosiz namuna) hujjat oxirida qog'ozda qo'lda
    to'ldirish uchun bo'sh imzo qatorlari chiziladi."""
    from io import BytesIO
    from django.utils import timezone
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Image
    from django.contrib.staticfiles import finders

    ACCENT = colors.HexColor('#f59e0b')
    LINE   = colors.HexColor('#d1d5db')
    logo_path = finders.find('taxi/img/logo.png')

    def esc(text):
        return (text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    .replace('\n', '<br/>'))

    margin      = 10 * mm
    header_h    = 22 * mm
    col_gap     = 6 * mm
    page_w, page_h = A4
    col_w = (page_w - 2 * margin - col_gap) / 2
    # Footer matni pastki margin zonasiga (frame tagidan pastda) chizilgani
    # uchun uning uchun alohida joy band qilinmaydi — aks holda ustun bo'yicha
    # foydali balandlik behuda kamayib, matn ikkinchi sahifaga o'tib ketardi.
    col_h = page_h - 2 * margin - header_h

    def draw_chrome(canvas_obj, doc_obj):
        canvas_obj.saveState()
        # Nafis tashqi ramka — chop etilganda hujjatga "rasmiy" ko'rinish beradi
        canvas_obj.setStrokeColor(LINE)
        canvas_obj.setLineWidth(0.8)
        canvas_obj.rect(margin - 5, margin - 5, page_w - 2 * (margin - 5), page_h - 2 * (margin - 5))
        # Tepadagi brend chizig'i
        canvas_obj.setFillColor(ACCENT)
        canvas_obj.rect(margin - 5, page_h - margin + 5, page_w - 2 * (margin - 5), 2.2, stroke=0, fill=1)

        top = page_h - margin
        canvas_obj.setFont('Helvetica-Bold', 9)
        canvas_obj.setFillColor(ACCENT)
        canvas_obj.drawString(margin, top - 10, 'VIJDON TAXI')
        canvas_obj.setFont('Helvetica-Bold', 13)
        canvas_obj.setFillColor(colors.black)
        canvas_obj.drawString(margin, top - 24, contract.title)
        canvas_obj.setFont('Helvetica', 7.5)
        canvas_obj.setFillColor(colors.grey)
        meta = (f"Generatsiya: {timezone.now().strftime('%d.%m.%Y %H:%M')}  |  Versiya: {contract.version}")
        if driver:
            meta += f"  |  Haydovchi: {driver.full_name}  |  Tel: {driver.phone_number}  |  Mashina: {driver.car_model} ({driver.car_number})"
        canvas_obj.drawString(margin, top - 34, meta)

        if logo_path:
            logo_size = 26
            canvas_obj.drawImage(logo_path, page_w - margin - logo_size, top - logo_size - 2,
                                  width=logo_size, height=logo_size, preserveAspectRatio=True,
                                  anchor='c', mask='auto')

        canvas_obj.setStrokeColor(LINE)
        canvas_obj.setLineWidth(0.6)
        canvas_obj.line(margin, top - 38, page_w - margin, top - 38)

        canvas_obj.setFont('Helvetica', 7)
        canvas_obj.setFillColor(colors.grey)
        canvas_obj.drawString(margin, margin - 4, "Vijdon Taxi — avtomatik generatsiya qilingan hujjat")
        canvas_obj.drawRightString(page_w - margin, margin - 4, f"Sahifa {doc_obj.page}")
        canvas_obj.restoreState()

    buf = BytesIO()
    frame1 = Frame(margin, margin, col_w, col_h, id='col1', topPadding=0, bottomPadding=0)
    frame2 = Frame(margin + col_w + col_gap, margin, col_w, col_h, id='col2', topPadding=0, bottomPadding=0)
    doc = BaseDocTemplate(buf, pagesize=A4)
    doc.addPageTemplates(PageTemplate(id='two-col', frames=[frame1, frame2], onPage=draw_chrome))

    styles = getSampleStyleSheet()
    body_style = ParagraphStyle('ContractBody', parent=styles['Normal'], fontSize=8, leading=10.2, spaceAfter=4)
    meta_style = ParagraphStyle('ContractMeta', parent=styles['Normal'], fontSize=7.5, textColor=colors.grey, leading=9.5)
    sign_style = ParagraphStyle('ContractSignLine', parent=styles['Normal'], fontSize=8.5, leading=15, spaceAfter=2)

    def render_paragraph(raw):
        """Bo'lim sarlavhasi (butunlay bosh harfli birinchi qator) bo'lsa,
        uni qalin va rangli qilib ajratib ko'rsatadi."""
        lines = raw.split('\n')
        first, rest = lines[0], lines[1:]
        is_header = bool(first.strip()) and first.strip() == first.strip().upper() and any(c.isalpha() for c in first)
        if is_header:
            head_html = f"<font color='#f59e0b'><b>{esc(first)}</b></font>"
            body_html = '<br/>'.join(esc(l) for l in rest)
            html = head_html + ('<br/>' + body_html if body_html else '')
        else:
            html = esc(raw)
        return Paragraph(html, body_style)

    elements = []
    for para in contract.content.split('\n\n'):
        if para.strip():
            elements.append(render_paragraph(para))

    if signature:
        # Raqamli imzo bilan tasdiqlangan — imzo rasmi va metama'lumot ko'rsatiladi
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(
            esc(f"Imzolangan sana: {signature.signed_at.strftime('%d.%m.%Y %H:%M')} | "
                f"Versiya: {signature.version} | IP: {signature.ip_address or '-'}"), meta_style))
        elements.append(Spacer(1, 4))
        try:
            elements.append(Image(signature.signature.path, width=col_w * 0.9, height=22 * mm, kind='proportional'))
        except Exception:
            pass
        elements.append(Paragraph(esc(f"Imzolagan: {signature.full_name}"), meta_style))
    else:
        # Namunaviy (imzosiz) hujjat — qog'ozda qo'lda to'ldirish uchun bo'sh qatorlar
        blank = '.' * 34
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("<b>TOMONLARNING IMZOLARI</b>", meta_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"Haydovchi F.I.Sh: {blank}", sign_style))
        elements.append(Paragraph(f"Imzo: {'.' * 18}&nbsp;&nbsp;&nbsp;&nbsp;Sana: {'.' * 12}", sign_style))
        elements.append(Spacer(1, 6))
        elements.append(Paragraph(f"Kompaniya vakili: {blank}", sign_style))
        elements.append(Paragraph(f"Imzo: {'.' * 18}&nbsp;&nbsp;&nbsp;&nbsp;Sana: {'.' * 12}", sign_style))

    doc.build(elements)
    buf.seek(0)
    return buf


def build_balance_receipt_pdf(log):
    """Bitta balans harakati (BalanceLog) uchun 80mm termal chek uslubidagi
    PDF chek quradi (BytesIO qaytaradi) — chop etish yoki mijozga/haydovchiga
    yuborish uchun."""
    from io import BytesIO
    from textwrap import wrap
    from django.utils import timezone
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as pdfcanvas
    from django.contrib.staticfiles import finders
    from taxi.models import BalanceLog

    ACCENT = colors.HexColor('#f59e0b')
    LINE   = colors.HexColor('#d1d5db')
    logo_path = finders.find('taxi/img/logo.png')
    note_lines = wrap(log.note, 40) if log.note else []

    width  = 80 * mm
    height = (150 + len(note_lines) * 4) * mm
    buf = BytesIO()
    c = pdfcanvas.Canvas(buf, pagesize=(width, height))

    x = 6 * mm
    y = height - 10 * mm

    if logo_path:
        try:
            c.drawImage(logo_path, width / 2 - 8 * mm, y - 16 * mm, width=16 * mm, height=16 * mm,
                        preserveAspectRatio=True, anchor='c', mask='auto')
            y -= 20 * mm
        except Exception:
            pass

    c.setFont('Helvetica-Bold', 12)
    c.setFillColor(ACCENT)
    c.drawCentredString(width / 2, y, 'VIJDON TAXI')
    y -= 5.5 * mm
    c.setFont('Helvetica', 8)
    c.setFillColor(colors.grey)
    c.drawCentredString(width / 2, y, "To'lov cheki")
    y -= 7 * mm

    def dashed_line():
        nonlocal y
        c.setStrokeColor(LINE)
        c.setDash(1, 2)
        c.line(x, y, width - x, y)
        c.setDash()
        y -= 6 * mm

    def row(label, value, bold=False):
        nonlocal y
        c.setFont('Helvetica', 8)
        c.setFillColor(colors.grey)
        c.drawString(x, y, label)
        c.setFont('Helvetica-Bold' if bold else 'Helvetica', 8)
        c.setFillColor(colors.black)
        c.drawRightString(width - x, y, value)
        y -= 5.5 * mm

    dashed_line()
    row('Chek №', f'#{log.id}')
    row('Sana', log.created_at.strftime('%d.%m.%Y %H:%M'))
    row('Haydovchi', log.driver.full_name)
    row('Telefon', log.driver.phone_number)
    row('Mashina', f'{log.driver.car_model} ({log.driver.car_number})')
    y -= 1 * mm
    dashed_line()

    action_label = "Balansga qo'shildi" if log.action == BalanceLog.ACTION_ADD else "Balansdan yechildi"
    sign = '+' if log.action == BalanceLog.ACTION_ADD else '-'
    row(action_label, f"{sign}{log.amount:,.0f} UZS".replace(',', ' '), bold=True)
    row('Joriy balans', f"{log.balance_after:,.0f} UZS".replace(',', ' '), bold=True)

    if note_lines:
        y -= 1 * mm
        c.setFont('Helvetica-Oblique', 7)
        c.setFillColor(colors.grey)
        for line in note_lines:
            c.drawString(x, y, line)
            y -= 4 * mm

    y -= 2 * mm
    dashed_line()
    c.setFont('Helvetica', 6)
    c.setFillColor(colors.grey)
    c.drawCentredString(width / 2, y, f"Chek yaratildi: {timezone.now().strftime('%d.%m.%Y %H:%M')}")
    y -= 4 * mm
    c.drawCentredString(width / 2, y, "Vijdon Taxi — rahmat!")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


def generate_voucher_codes(n, existing=None):
    """`n` ta noyob, taxminlab bo'lmaydigan maxfiy flayer kodi yaratadi
    (0/O/1/I kabi chalkash belgilarsiz, 8 ta belgi). `existing` — bazadagi
    band kodlar to'plami, ular bilan to'qnashmaydi."""
    import secrets
    alphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
    existing = existing or set()
    codes = set()
    while len(codes) < n:
        candidate = ''.join(secrets.choice(alphabet) for _ in range(8))
        if candidate not in existing:
            codes.add(candidate)
    return list(codes)


def build_flyer_pdf(codes, owner_driver=None):
    """Reklama flayeri: har bir A4 varag'iga 3 tadan flayer (gorizontal
    chiziqlar bo'ylab kesiladi), har bir flayerda o'ziga xos maxfiy tekshirish
    kodi VA shu kodni tekshirish sahifasiga olib boruvchi QR kod bosiladi
    (soxtalashtirishning oldini olish uchun — mijoz telefon kamerasi bilan
    skanerlab, flayer asl yoki soxta ekanini darhol bilib oladi). `codes` —
    flayerlar soniga teng satrlar ro'yxati (3 ga karrali bo'lishi kerak).

    Har bir varaq juftligi ketma-ket chiqadi: old tomon, so'ng o'sha varaqning
    orqa tomoni — ikki tomonlama chop etganda "uzun tomondan aylantirish"
    (flip on long edge) rejimida mos tushadi. BytesIO qaytaradi.

    Diqqat: bu haqiqiy banknota tasvirining nusxasi emas — valyuta dizaynini
    aniq takrorlash huquqiy jihatdan xavfli, shuning uchun pul uslubidagi,
    lekin aniq "CHEGIRMA SERTIFIKATI" deb belgilangan dizayn ishlatilgan."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.graphics.barcode import qr as qr_barcode
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF
    from django.conf import settings

    def draw_qr(canvas_obj, url, x, y, size):
        """Berilgan URL manzilini QR kod sifatida `(x, y)` (chapdan-pastdan)
        nuqtaga `size` x `size` o'lchamda chizadi."""
        widget = qr_barcode.QrCodeWidget(url)
        b = widget.getBounds()
        w, h = b[2] - b[0], b[3] - b[1]
        d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
        d.add(widget)
        renderPDF.draw(d, canvas_obj, x, y)

    page_w, page_h = A4
    n = 3
    strip_h = page_h / n

    DARK        = colors.HexColor('#111827')
    AMBER       = colors.HexColor('#f59e0b')
    GREEN       = colors.HexColor('#15803d')
    GREEN_LIGHT = colors.HexColor('#ecfdf5')
    GREEN_TEXT  = colors.HexColor('#166534')
    GREY_TEXT   = colors.HexColor('#374151')

    from django.contrib.staticfiles import finders
    logo_path = finders.find('taxi/img/logo.png')

    driver_photo_path = None
    if owner_driver and owner_driver.photo:
        try:
            driver_photo_path = owner_driver.photo.path
        except Exception:
            driver_photo_path = None

    buf = BytesIO()
    c = pdfcanvas.Canvas(buf, pagesize=A4)

    def cut_lines():
        c.saveState()
        c.setDash([3, 3])
        c.setStrokeColor(colors.grey)
        c.setLineWidth(0.5)
        for i in range(1, n):
            y = page_h - i * strip_h
            c.line(0, y, page_w, y)
        c.restoreState()

    def draw_front(strip_codes):
        for i in range(n):
            y0 = page_h - (i + 1) * strip_h
            code = strip_codes[i] if i < len(strip_codes) else ''
            c.saveState()
            c.translate(0, y0)

            c.setFillColor(colors.white)
            c.rect(0, 0, page_w, strip_h, stroke=0, fill=1)

            # Bosh joyni jonlantiruvchi yumshoq fon doirasi — endi narx katta
            # sarlavha sifatida chiqqani uchun bu faqat nafis fon bezagi,
            # e'tiborni tortmaydi
            c.saveState()
            c.setFillColor(AMBER)
            c.setFillAlpha(0.07)
            c.circle(page_w - 18 * mm, strip_h - 10 * mm, 40 * mm, stroke=0, fill=1)
            c.restoreState()

            block_w = 58 * mm
            c.setFillColor(DARK)
            c.rect(0, 0, block_w, strip_h, stroke=0, fill=1)

            image_path = driver_photo_path or logo_path
            if image_path:
                badge = 44 * mm
                badge_x = (block_w - badge) / 2
                badge_y = strip_h - badge - 12 * mm
                c.setFillColor(colors.white)
                c.roundRect(badge_x, badge_y, badge, badge, 5 * mm, stroke=0, fill=1)
                pad = 3 * mm
                c.drawImage(image_path, badge_x + pad, badge_y + pad, width=badge - 2 * pad,
                            height=badge - 2 * pad, preserveAspectRatio=True, anchor='c', mask='auto')
            else:
                badge_y = strip_h - 44 * mm - 12 * mm
                c.setFillColor(AMBER)
                c.setFont('Helvetica-Bold', 20)
                c.drawCentredString(block_w / 2, strip_h / 2 + 6, 'VIJDON')
                c.drawCentredString(block_w / 2, strip_h / 2 - 10, 'TAXI')

            c.setFillColor(colors.white)
            if owner_driver:
                name = owner_driver.full_name or ''
                font_size = 11
                max_w = block_w - 8 * mm
                while font_size > 7 and c.stringWidth(name, 'Helvetica-Bold', font_size) > max_w:
                    font_size -= 1
                c.setFont('Helvetica-Bold', font_size)
                c.drawCentredString(block_w / 2, badge_y - 9 * mm, name[:24])
                c.setFont('Helvetica', 8)
                c.drawCentredString(block_w / 2, badge_y - 15 * mm, "shaxsiy haydovchingiz")
            else:
                c.setFont('Helvetica-Bold', 9)
                c.drawCentredString(block_w / 2, badge_y - 9 * mm, "ISHONCHLI VA TEZ")
                c.setFont('Helvetica', 9)
                c.drawCentredString(block_w / 2, badge_y - 15 * mm, "taksi xizmati")

            # Blokning pastki chetida ingichka amber chiziq — nafis yakunlovchi chiziq
            c.setStrokeColor(AMBER)
            c.setLineWidth(1)
            c.line(10 * mm, 10 * mm, block_w - 10 * mm, 10 * mm)

            # Qorong'i blok bilan oq maydonni ajratuvchi rangli chiziq
            c.setFillColor(AMBER)
            c.rect(block_w, 0, 2.2 * mm, strip_h, stroke=0, fill=1)

            right_x = block_w + 10 * mm
            right_edge = page_w - 8 * mm

            # Eyebrow — "AKSIYA" yorlig'i
            pill_w, pill_h = 26 * mm, 6.5 * mm
            pill_y = strip_h - 15 * mm
            c.setFillColor(AMBER)
            c.roundRect(right_x, pill_y, pill_w, pill_h, pill_h / 2, stroke=0, fill=1)
            c.setFillColor(colors.white)
            c.setFont('Helvetica-Bold', 8)
            c.drawCentredString(right_x + pill_w / 2, pill_y + pill_h / 2 - 2.8, "AKSIYA")

            # Katta narx sarlavhasi — endi asosiy diqqat markazi
            c.setFillColor(DARK)
            c.setFont('Helvetica-Bold', 32)
            c.drawString(right_x, strip_h - 35 * mm, "3 000 so'm")
            c.setFont('Helvetica-Bold', 15)
            c.setFillColor(AMBER)
            c.drawString(right_x, strip_h - 45 * mm, "SOVG'A OLING!")

            c.setFont('Helvetica', 9.5)
            c.setFillColor(GREY_TEXT)
            c.drawString(right_x, strip_h - 55 * mm, "Ushbu flayerni haydovchimizga ko'rsating —")
            c.drawString(right_x, strip_h - 61 * mm, "safaringiz 3 000 so'mga arzonlashadi.")

            c.setStrokeColor(colors.HexColor('#e5e7eb'))
            c.setLineWidth(0.8)
            c.line(right_x, 23 * mm, right_edge, 23 * mm)

            c.setFont('Helvetica', 9.5)
            c.setFillColor(GREY_TEXT)
            c.drawString(right_x, 15 * mm, "Buyurtma berish uchun qo'ng'iroq qiling:")
            c.setFont('Helvetica-Bold', 22)
            c.setFillColor(AMBER)
            c.drawString(right_x, 4 * mm, "1351")

            # Tashqi ramka
            c.setStrokeColor(AMBER)
            c.setLineWidth(1.2)
            c.rect(2 * mm, 2 * mm, page_w - 4 * mm, strip_h - 4 * mm, stroke=1, fill=0)
            c.restoreState()
        cut_lines()
        c.showPage()

    def draw_back(strip_codes):
        for i in range(n):
            y0 = page_h - (i + 1) * strip_h
            code = strip_codes[i] if i < len(strip_codes) else ''
            c.saveState()
            c.translate(0, y0)

            c.setFillColor(GREEN_LIGHT)
            c.rect(0, 0, page_w, strip_h, stroke=0, fill=1)

            # Fon suvbelgisi — nafis, deyarli sezilmas tarzda "VIJDON" so'zi
            c.saveState()
            c.translate(page_w / 2, strip_h / 2)
            c.rotate(-16)
            c.setFillColor(GREEN)
            c.setFillAlpha(0.055)
            c.setFont('Helvetica-Bold', 70)
            c.drawCentredString(0, -20, "VIJDON")
            c.restoreState()

            c.setStrokeColor(GREEN)
            c.setLineWidth(1.6)
            c.rect(4 * mm, 4 * mm, page_w - 8 * mm, strip_h - 8 * mm, stroke=1, fill=0)
            c.setLineWidth(0.5)
            c.setDash([1, 2])
            c.rect(7 * mm, 7 * mm, page_w - 14 * mm, strip_h - 14 * mm, stroke=1, fill=0)
            c.setDash([])

            # Kupon "tishchalari" — chekka o'rtasida chapdan va o'ngdan yarim
            # doira bite — haqiqiy yirtiladigan kupon hissini beradi
            c.setFillColor(colors.white)
            c.circle(0, strip_h / 2, 3.5 * mm, stroke=0, fill=1)
            c.circle(page_w, strip_h / 2, 3.5 * mm, stroke=0, fill=1)

            # Tepa qator: chap tomonda QR + izoh, o'ng tomonda maxfiy kod
            if code:
                site_url = getattr(settings, 'SITE_URL', 'https://vijdontaxi.uz').rstrip('/')
                qr_size = 16 * mm
                qr_x, qr_y = 11 * mm, strip_h - 29 * mm
                draw_qr(c, f"{site_url}/flayer/{code}/", qr_x, qr_y, qr_size)
                c.setFont('Helvetica-Bold', 6.6)
                c.setFillColor(GREEN)
                c.drawString(qr_x + qr_size + 3 * mm, qr_y + qr_size - 6, "ASLLIGINI")
                c.drawString(qr_x + qr_size + 3 * mm, qr_y + qr_size - 12, "TEKSHIRISH")
                c.setFont('Helvetica', 6)
                c.setFillColor(GREEN_TEXT)
                c.drawString(qr_x + qr_size + 3 * mm, qr_y + qr_size - 18, "uchun skanerlang")

            c.setFont('Courier-Bold', 9)
            c.setFillColor(GREEN)
            c.drawRightString(page_w - 11 * mm, strip_h - 16 * mm, f"KOD: {code}")

            c.setFillColor(GREEN)
            c.setFont('Helvetica-Bold', 11)
            c.drawCentredString(page_w / 2, strip_h - 40 * mm, "CHEGIRMA SERTIFIKATI")
            c.setFont('Helvetica-Bold', 38)
            c.drawCentredString(page_w / 2, strip_h / 2 - 8 * mm, "3 000 SO'M")
            c.setFont('Helvetica', 8)
            c.setFillColor(GREEN_TEXT)
            c.drawCentredString(page_w / 2, strip_h / 2 - 16 * mm, "chegirma summasi")

            c.setFont('Helvetica', 8.3)
            c.setFillColor(GREEN_TEXT)
            c.drawCentredString(page_w / 2, 18.5 * mm, "Faqat bitta safar uchun amal qiladi.")
            c.drawCentredString(page_w / 2, 14 * mm, "Boshqa aksiyalar bilan birlashtirilmaydi.")

            foot_text = "VIJDON TAXI"
            c.setFont('Helvetica-Bold', 9)
            text_w = c.stringWidth(foot_text, 'Helvetica-Bold', 9)
            logo_sz = 7 * mm
            gap = 1.8 * mm
            total_w = (logo_sz + gap if logo_path else 0) + text_w
            start_x = page_w / 2 - total_w / 2
            if logo_path:
                c.drawImage(logo_path, start_x, 9 * mm - logo_sz / 2 + 1, width=logo_sz, height=logo_sz,
                            preserveAspectRatio=True, anchor='c', mask='auto')
                start_x += logo_sz + gap
            c.setFillColor(GREEN)
            c.drawString(start_x, 9 * mm - 3, foot_text)
            c.restoreState()
        cut_lines()
        c.showPage()

    for start in range(0, len(codes), n):
        chunk = codes[start:start + n]
        draw_front(chunk)
        draw_back(chunk)

    c.save()
    buf.seek(0)
    return buf


def build_flyer_business_card_pdf(codes, owner_driver=None):
    """Xuddi shu chegirma kuponini VIZITKA o'lchamida (90x50mm, standart CIS
    o'lchami) chop etish uchun alohida, shu kichik o'lchamga moslab
    LOYIHALANGAN (kattaroq flayerni shunchaki kichraytirish emas) PDF quradi.

    Katta flayerni vizitka o'lchamigacha kichraytirsa, matn va QR kod
    o'qib/skanerlab bo'lmas darajada mayda bo'lib qolar edi — shuning uchun
    bu funksiya shriftlarni va joylashuvni to'g'ridan-to'g'ri 90x50mm uchun
    hisoblab chiqadi. Har bir A4 varag'iga 2 ustun x 5 qator = 10 tadan
    vizitka chiqadi (kesish chiziqlari bilan). `codes` — vizitkalar soniga
    teng satrlar ro'yxati."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as pdfcanvas
    from reportlab.graphics.barcode import qr as qr_barcode
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF
    from django.conf import settings
    from django.contrib.staticfiles import finders

    def draw_qr(canvas_obj, url, x, y, size):
        widget = qr_barcode.QrCodeWidget(url)
        b = widget.getBounds()
        w, h = b[2] - b[0], b[3] - b[1]
        d = Drawing(size, size, transform=[size / w, 0, 0, size / h, 0, 0])
        d.add(widget)
        renderPDF.draw(d, canvas_obj, x, y)

    DARK  = colors.HexColor('#111827')
    AMBER = colors.HexColor('#f59e0b')
    GREEN = colors.HexColor('#15803d')
    GREEN_LIGHT = colors.HexColor('#ecfdf5')
    GREY_TEXT   = colors.HexColor('#374151')
    logo_path = finders.find('taxi/img/logo.png')

    driver_photo_path = None
    if owner_driver and owner_driver.photo:
        try:
            driver_photo_path = owner_driver.photo.path
        except Exception:
            driver_photo_path = None

    card_w, card_h = 90 * mm, 50 * mm
    cols, rows = 2, 5
    per_page = cols * rows
    page_w, page_h = A4
    margin_x = (page_w - cols * card_w) / 2
    margin_y = (page_h - rows * card_h) / 2

    buf = BytesIO()
    c = pdfcanvas.Canvas(buf, pagesize=A4)

    def cut_lines():
        c.saveState()
        c.setDash([2, 2])
        c.setStrokeColor(colors.grey)
        c.setLineWidth(0.4)
        for col in range(cols + 1):
            x = margin_x + col * card_w
            c.line(x, margin_y, x, page_h - margin_y)
        for row in range(rows + 1):
            y = margin_y + row * card_h
            c.line(margin_x, y, page_w - margin_x, y)
        c.restoreState()

    def card_origin(idx):
        col = idx % cols
        row = idx // cols
        return margin_x + col * card_w, page_h - margin_y - (row + 1) * card_h

    def draw_front(chunk):
        for idx in range(per_page):
            x0, y0 = card_origin(idx)
            c.saveState()
            c.translate(x0, y0)

            c.setFillColor(colors.white)
            c.rect(0, 0, card_w, card_h, stroke=0, fill=1)

            block_w = 26 * mm
            c.setFillColor(DARK)
            c.rect(0, 0, block_w, card_h, stroke=0, fill=1)
            image_path = driver_photo_path or logo_path
            if image_path:
                badge = 15 * mm if owner_driver else 17 * mm
                badge_x = (block_w - badge) / 2
                badge_y = (card_h - badge) / 2 + (2.5 * mm if owner_driver else 0)
                c.setFillColor(colors.white)
                c.roundRect(badge_x, badge_y, badge, badge, 2.2 * mm, stroke=0, fill=1)
                pad = 1.4 * mm
                c.drawImage(image_path, badge_x + pad, badge_y + pad, width=badge - 2 * pad,
                            height=badge - 2 * pad, preserveAspectRatio=True, anchor='c', mask='auto')
                if owner_driver:
                    name = (owner_driver.full_name or '')[:20]
                    font_size = 6.2
                    max_w = block_w - 3 * mm
                    while font_size > 4.5 and c.stringWidth(name, 'Helvetica-Bold', font_size) > max_w:
                        font_size -= 0.3
                    c.setFillColor(colors.white)
                    c.setFont('Helvetica-Bold', font_size)
                    c.drawCentredString(block_w / 2, badge_y - 4 * mm, name)
            c.setFillColor(AMBER)
            c.rect(block_w, 0, 1 * mm, card_h, stroke=0, fill=1)

            rx = block_w + 4 * mm
            c.setFillColor(DARK)
            c.setFont('Helvetica-Bold', 15)
            c.drawString(rx, card_h - 15 * mm, "3 000 so'm")
            c.setFont('Helvetica-Bold', 9)
            c.setFillColor(AMBER)
            c.drawString(rx, card_h - 21 * mm, "SOVG'A OLING!")
            c.setFont('Helvetica', 6.3)
            c.setFillColor(GREY_TEXT)
            c.drawString(rx, card_h - 28 * mm, "Flayerni haydovchiga ko'rsating")
            c.setFont('Helvetica', 7.5)
            c.setFillColor(GREY_TEXT)
            c.drawString(rx, 8 * mm, "Buyurtma:")
            c.setFont('Helvetica-Bold', 13)
            c.setFillColor(AMBER)
            c.drawString(rx, 2.5 * mm, "1351")

            c.setStrokeColor(AMBER)
            c.setLineWidth(0.8)
            c.rect(0.8 * mm, 0.8 * mm, card_w - 1.6 * mm, card_h - 1.6 * mm, stroke=1, fill=0)
            c.restoreState()
        cut_lines()
        c.showPage()

    def draw_back(chunk):
        site_url = getattr(settings, 'SITE_URL', 'https://vijdontaxi.uz').rstrip('/')
        for idx in range(per_page):
            code = chunk[idx] if idx < len(chunk) else ''
            x0, y0 = card_origin(idx)
            c.saveState()
            c.translate(x0, y0)

            c.setFillColor(GREEN_LIGHT)
            c.rect(0, 0, card_w, card_h, stroke=0, fill=1)
            c.setStrokeColor(GREEN)
            c.setLineWidth(1)
            c.rect(1.2 * mm, 1.2 * mm, card_w - 2.4 * mm, card_h - 2.4 * mm, stroke=1, fill=0)

            c.setFillColor(GREEN)
            c.setFont('Helvetica-Bold', 7.5)
            c.drawCentredString(card_w / 2, card_h - 8 * mm, "CHEGIRMA SERTIFIKATI")

            if code:
                qr_size = 21 * mm
                qr_x, qr_y = 5 * mm, 6 * mm
                draw_qr(c, f"{site_url}/flayer/{code}/", qr_x, qr_y, qr_size)
                c.setFont('Helvetica', 5.2)
                c.setFillColor(GREEN)
                c.drawCentredString(qr_x + qr_size / 2, 3 * mm, "Asllik tekshiruvi")

            info_x = 5 * mm + 21 * mm + 4 * mm
            c.setFillColor(GREEN)
            c.setFont('Helvetica-Bold', 22)
            c.drawString(info_x, card_h - 24 * mm, "3 000")
            c.setFont('Helvetica-Bold', 11)
            c.drawString(info_x, card_h - 30 * mm, "SO'M CHEGIRMA")
            c.setFont('Courier-Bold', 8)
            c.drawString(info_x, card_h - 38 * mm, f"KOD: {code}")
            c.setFont('Helvetica', 5.8)
            c.setFillColor(GREY_TEXT)
            c.drawString(info_x, 5 * mm, "Faqat bitta safar uchun amal qiladi.")

            c.restoreState()
        cut_lines()
        c.showPage()

    for start in range(0, len(codes), per_page):
        chunk = codes[start:start + per_page]
        draw_front(chunk)
        draw_back(chunk)

    c.save()
    buf.seek(0)
    return buf

