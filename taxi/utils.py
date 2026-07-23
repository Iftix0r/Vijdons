import math
import urllib.request
import urllib.parse
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

