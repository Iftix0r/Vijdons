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


def _order_inline(order_id):
    return {'inline_keyboard': [[{'text': '🔍 Batafsil', 'url': _order_url(order_id)}]]}


def _driver_inline(driver_id):
    return {'inline_keyboard': [[{'text': '👤 Haydovchi', 'url': _driver_url(driver_id)}]]}


def tg_new_order(order):
    log_panel_event('panel_new_order', f"Buyurtma #{order.id} — {order.from_address}")
    cfg = _cfg()
    if cfg and not cfg.notify_new_order:
        return
    client = order.client
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
    if cfg and not cfg.notify_accepted:
        return
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

    send_fcm(
        nearest.fcm_token,
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
    # Web Push
    try:
        from taxi.driver_views import send_push_to_driver
        body = f"📍 {order.from_address}"
        if order.price:
            body += f" | 💰 {int(order.price):,} so'm"
        send_push_to_driver(nearest, '🚖 Yangi buyurtma!', body)
    except Exception:
        pass
    tg_order_dispatched(order, nearest)

    # 10 sekundlik (yoki sozlangan) kutish taymeri
    import threading
    threading.Thread(
        target=auto_reject_timeout,
        args=(order.id, nearest.id, tariff.dispatch_timeout),
        daemon=True
    ).start()

    return nearest


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

    ACCENT = colors.HexColor('#f59e0b')
    LINE   = colors.HexColor('#d1d5db')

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


def build_flyer_pdf():
    """Reklama flayeri: A4 sahifaga 3 tadan flayer (gorizontal chiziqlar bo'ylab
    kesiladi). 1-sahifa — flayerlarning old tomoni (Vijdon Taxi reklamasi),
    2-sahifa — orqa tomoni (5 000 so'mlik chegirma sertifikati dizayni).
    Ikki tomonlama chop etganda "uzun tomondan aylantirish" (flip on long edge)
    rejimida old/orqa tomonlar to'g'ri mos tushadi. BytesIO qaytaradi.

    Diqqat: bu haqiqiy banknota tasvirining nusxasi emas — valyuta dizaynini
    aniq takrorlash huquqiy jihatdan xavfli, shuning uchun pul uslubidagi,
    lekin aniq "CHEGIRMA SERTIFIKATI" deb belgilangan dizayn ishlatilgan."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas as pdfcanvas

    page_w, page_h = A4
    n = 3
    strip_h = page_h / n

    DARK        = colors.HexColor('#111827')
    AMBER       = colors.HexColor('#f59e0b')
    GREEN       = colors.HexColor('#15803d')
    GREEN_LIGHT = colors.HexColor('#ecfdf5')
    GREEN_TEXT  = colors.HexColor('#166534')
    GREY_TEXT   = colors.HexColor('#374151')

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

    # ── OLD TOMON — reklama ──
    for i in range(n):
        y0 = page_h - (i + 1) * strip_h
        c.saveState()
        c.translate(0, y0)

        block_w = 62 * mm
        c.setFillColor(DARK)
        c.rect(0, 0, block_w, strip_h, stroke=0, fill=1)
        c.setFillColor(AMBER)
        c.setFont('Helvetica-Bold', 22)
        c.drawString(8 * mm, strip_h / 2 + 8 * mm, 'VIJDON')
        c.drawString(8 * mm, strip_h / 2 - 8 * mm, 'TAXI')
        c.setFillColor(colors.white)
        c.setFont('Helvetica', 8.5)
        c.drawString(8 * mm, 8 * mm, "Ishonchli va tez taksi xizmati")

        c.setFillColor(DARK)
        c.setFont('Helvetica-Bold', 14.5)
        c.drawString(block_w + 8 * mm, strip_h - 16 * mm, "Buyurtma bering —")
        c.drawString(block_w + 8 * mm, strip_h - 26 * mm, "5 000 so'm sovg'a oling!")
        c.setFont('Helvetica', 9)
        c.setFillColor(GREY_TEXT)
        c.drawString(block_w + 8 * mm, strip_h - 37 * mm, "Ushbu flayerni haydovchimizga ko'rsating —")
        c.drawString(block_w + 8 * mm, strip_h - 43 * mm, "safaringiz 5 000 so'mga arzonlashadi.")
        c.setFont('Helvetica', 9)
        c.setFillColor(GREY_TEXT)
        c.drawString(block_w + 8 * mm, 13 * mm, "Buyurtma berish uchun qo'ng'iroq qiling:")
        c.setFont('Helvetica-Bold', 16)
        c.setFillColor(AMBER)
        c.drawString(block_w + 8 * mm, 4 * mm, "1356")
        c.restoreState()
    cut_lines()
    c.showPage()

    # ── ORQA TOMON — chegirma sertifikati ──
    for i in range(n):
        y0 = page_h - (i + 1) * strip_h
        c.saveState()
        c.translate(0, y0)

        c.setFillColor(GREEN_LIGHT)
        c.rect(0, 0, page_w, strip_h, stroke=0, fill=1)
        c.setStrokeColor(GREEN)
        c.setLineWidth(1.6)
        c.rect(4 * mm, 4 * mm, page_w - 8 * mm, strip_h - 8 * mm, stroke=1, fill=0)
        c.setLineWidth(0.5)
        c.setDash([1, 2])
        c.rect(7 * mm, 7 * mm, page_w - 14 * mm, strip_h - 14 * mm, stroke=1, fill=0)
        c.setDash([])

        c.setFillColor(GREEN)
        c.setFont('Helvetica-Bold', 11)
        c.drawCentredString(page_w / 2, strip_h - 15 * mm, "CHEGIRMA SERTIFIKATI")
        c.setFont('Helvetica-Bold', 32)
        c.drawCentredString(page_w / 2, strip_h / 2 - 4 * mm, "5 000 SO'M")
        c.setFont('Helvetica', 8.3)
        c.setFillColor(GREEN_TEXT)
        c.drawCentredString(page_w / 2, 18.5 * mm, "Faqat bitta safar uchun amal qiladi.")
        c.drawCentredString(page_w / 2, 14 * mm, "Boshqa aksiyalar bilan birlashtirilmaydi.")
        c.setFont('Helvetica-Bold', 9)
        c.setFillColor(GREEN)
        c.drawCentredString(page_w / 2, 9 * mm, "VIJDON TAXI")
        c.restoreState()
    cut_lines()
    c.showPage()

    c.save()
    buf.seek(0)
    return buf

