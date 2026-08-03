import math
import urllib.request
import urllib.parse
import urllib.error
import json

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

def find_nearest_driver(drivers, lat, lng):
    nearest_driver = None
    min_dist = float('inf')
    
    for driver in drivers:
        if driver.latitude is not None and driver.longitude is not None:
            dist = haversine(lat, lng, driver.latitude, driver.longitude)
            if dist is not None and dist < min_dist:
                min_dist = dist
                nearest_driver = driver
                
    return nearest_driver, min_dist


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
VOICE_STALE_SECONDS = 12


def voice_prune_stale():
    """Heartbeat uzoq vaqt kelmagan (masalan ilova yopilgan) ishtirokchilarni
    "efir"dan olib tashlaydi."""
    from django.utils import timezone
    import datetime
    from taxi.models import VoiceParticipant
    cutoff = timezone.now() - datetime.timedelta(seconds=VOICE_STALE_SECONDS)
    VoiceParticipant.objects.filter(last_seen__lt=cutoff).delete()


def voice_participant_key(participant):
    return f'd{participant.driver_id}' if participant.driver_id else f'o{participant.operator_id}'


def voice_participants_list(exclude_key):
    """"Efir"dagi barcha ishtirokchilarni (so'rov yuborayotgan tomondan
    tashqari) frontend uchun {'key', 'name', 'is_operator'} shaklida qaytaradi."""
    from taxi.models import VoiceParticipant
    out = []
    for p in VoiceParticipant.objects.select_related('driver', 'operator'):
        key = voice_participant_key(p)
        if key == exclude_key:
            continue
        if p.driver_id:
            out.append({'key': key, 'name': p.driver.full_name, 'car_number': p.driver.car_number, 'is_operator': False})
        else:
            out.append({'key': key, 'name': f"Operator — {p.operator.get_full_name() or p.operator.username}", 'is_operator': True})
    return out


def voice_target_kwargs(prefix, key):
    """'d5' yoki 'o3' kalitini `VoiceSignal.objects.create(...)` ga mos
    `{'to_driver_id': 5}` yoki `{'to_operator_id': 3}` kabi kwargs ga aylantiradi.
    `prefix` — 'to' yoki 'from'. Noto'g'ri/bo'sh kalit uchun None qaytaradi."""
    if not key or len(key) < 2:
        return None
    kind, raw_id = key[0], key[1:]
    if not raw_id.isdigit():
        return None
    if kind == 'd':
        return {f'{prefix}_driver_id': int(raw_id)}
    if kind == 'o':
        return {f'{prefix}_operator_id': int(raw_id)}
    return None


def voice_signal_sender_info(signal):
    """VoiceSignal qatoridan yuboruvchining (key, name) juftligini qaytaradi —
    `select_related('from_driver', 'from_operator')` bilan olingan bo'lishi kerak."""
    if signal.from_driver_id:
        return f'd{signal.from_driver_id}', signal.from_driver.full_name
    return f'o{signal.from_operator_id}', f"Operator — {signal.from_operator.get_full_name() or signal.from_operator.username}"


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


def send_sms(phone, text):
    """Mijozga Eskiz.uz orqali SMS yuboradi. (ok, message) qaytaradi."""
    try:
        from taxi.models import SmsSettings
        cfg = SmsSettings.get()
    except Exception:
        return False, 'SMS sozlamalari topilmadi'

    if not cfg.email or not cfg.password:
        return False, "Eskiz email/parol kiritilmagan"

    mobile = normalize_phone_uz(phone)
    if not mobile:
        return False, f"Telefon raqam formati noto'g'ri: {phone}"

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
                + (f" Haydovchi: {driver.full_name}, {car}." if driver else "")
                + " Iltimos kuting.")
    elif event == 'arrived':
        text = (f"Vijdon Taxi: Haydovchi{f' ({driver.full_name})' if driver else ''} "
                f"manzilingizga yetib keldi. Buyurtma #{order.id}.")
    elif event == 'completed':
        text = (f"Vijdon Taxi: Buyurtmangiz (#{order.id}) yakunlandi. "
                f"Narxi: {order.price or '—'} so'm. Xizmatimizdan foydalanganingiz uchun rahmat!")
    else:  # cancelled
        text = f"Vijdon Taxi: Buyurtmangiz (#{order.id}) bekor qilindi."

    send_sms(client.phone_number, text)


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


def tg_order_cancelled(order, driver):
    log_panel_event('panel_order_cancelled', f"Buyurtma #{order.id} — {driver.full_name}")
    cfg = _cfg()
    if cfg and not cfg.notify_cancelled:
        return
    markup = {'inline_keyboard': [[
        {'text': '🔍 Buyurtma', 'url': _order_url(order.id)},
        {'text': '👤 Haydovchi', 'url': _driver_url(driver.id)},
    ]]}
    send_telegram(
        f"❌ <b>Buyurtma bekor qilindi — #{order.id}</b>\n"
        f"🚗 Haydovchi: <b>{driver.full_name}</b>\n"
        f"👤 {order.client.full_name or '—'} | <code>{order.client.phone_number}</code>\n"
        f"📍 {order.from_address}",
        reply_markup=markup,
    )


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
    send_telegram(
        f"{emoji} <b>Balans o'zgardi</b>\n"
        f"👤 <b>{driver.full_name}</b> | <code>{driver.phone_number}</code>\n"
        f"💰 {sign}{amount} UZS\n"
        f"📊 Joriy balans: <b>{driver.balance} UZS</b>",
        reply_markup=_driver_inline(driver.id),
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


def send_fcm(fcm_token, title, body, data=None):
    """FCM push notification yuborish."""
    from django.conf import settings
    fcm_key = getattr(settings, 'FCM_SERVER_KEY', '')
    if not fcm_key or not fcm_token:
        return False
    try:
        payload = json.dumps({
            'to': fcm_token,
            'priority': 'high',
            'notification': {
                'title': title,
                'body': body,
                'sound': 'default',
                'android_channel_id': 'new_orders_channel',
            },
            'data': data or {},
        }).encode()
        req = urllib.request.Request(
            'https://fcm.googleapis.com/fcm/send',
            data=payload,
            headers={
                'Authorization': f'key={fcm_key}',
                'Content-Type': 'application/json',
            },
        )
        urllib.request.urlopen(req, timeout=5)
        return True
    except Exception:
        return False


def auto_reject_timeout(order_id, driver_id, timeout_seconds):
    """
    Haydovchi belgilangan vaqt ichida javob bermasa, buyurtmani avtomatik rad etadi
    va keyingi haydovchiga o'tkazadi.
    """
    import time
    time.sleep(timeout_seconds)

    from taxi.models import Order
    try:
        order = Order.objects.get(pk=order_id)
        if order.status == 'pending' and order.dispatched_to_id == driver_id:
            order.rejected_by.add(driver_id)
            order.dispatched_to = None
            order.save(update_fields=['dispatched_to'])

            # Keyingi haydovchiga yuborish
            dispatch_order(order)
    except Exception:
        pass


def dispatch_order(order):
    """
    Buyurtmani navbatma-navbat eng yaqin haydovchilarga yuborish.
    TariffSettings dagi max_dispatch_attempts sonigacha urinadi.
    Aks holda, buyurtmani umumiy tabloda qoldiradi (dispatched_to = None).
    """
    from django.utils import timezone
    from taxi.models import TariffSettings, Driver

    # Order yangi holatda bo'lishi kerak
    if order.status != 'pending':
        return None

    if not order.from_lat or not order.from_lng:
        return None

    tariff = TariffSettings.get()
    
    # Rad etgan haydovchilar sonini tekshirish
    attempts_count = order.rejected_by.count()
    if attempts_count >= tariff.max_dispatch_attempts:
        # Urinishlar tugadi, umumiy tabloda qoladi
        if order.dispatched_to is not None:
            order.dispatched_to = None
            order.save(update_fields=['dispatched_to'])
        return None

    rejected_ids = list(order.rejected_by.values_list('id', flat=True))

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

    nearest, _ = find_nearest_driver(candidates, order.from_lat, order.from_lng)
    if not nearest:
        if order.dispatched_to is not None:
            order.dispatched_to = None
            order.save(update_fields=['dispatched_to'])
        return None

    order.dispatched_to = nearest
    order.dispatched_at = timezone.now()
    order.save(update_fields=['dispatched_to', 'dispatched_at'])

    notify_driver_new_order(order, nearest)
    start_dispatch_timeout(order, nearest, tariff.dispatch_timeout)

    return nearest


def notify_driver_new_order(order, driver):
    """Buyurtma biror haydovchiga tayinlanganda (avtomatik dispatch_order()
    orqali yoki operator tomonidan qo'lda) unga FCM push, Web Push va
    Telegram orqali xabar yuborish — ikkala holatda ham bir xil ishlaydi."""
    send_fcm(
        driver.fcm_token,
        title='🚖 Yangi buyurtma!',
        body=f"📍 {order.from_address}" + (f" → {order.to_address}" if order.to_address else ""),
        data={
            'type':       'new_order',
            'order_id':   str(order.id),
            'from_addr':  order.from_address,
            'to_addr':    order.to_address or '',
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

