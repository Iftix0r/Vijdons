import math
import urllib.request
import urllib.parse
import json

def haversine(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points 
    on the earth (specified in decimal degrees)
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    # convert decimal degrees to radians 
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

    # haversine formula 
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a)) 
    r = 6371 # Radius of earth in kilometers.
    return c * r

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


def send_telegram(text):
    """Telegram guruhiga xabar yuborish."""
    from django.conf import settings
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(settings, 'TELEGRAM_GROUP_ID', '')
    if not token or not chat_id:
        return
    try:
        data = urllib.parse.urlencode({
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
        }).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=data,
        )
        urllib.request.urlopen(req, timeout=5)
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


def dispatch_order(order):
    """
    Buyurtmani eng yaqin, rad etmagan haydovchiga yuborish.
    Qaytaradi: haydovchi yoki None.
    """
    if not order.from_lat or not order.from_lng:
        return None

    rejected_ids = list(order.rejected_by.values_list('id', flat=True))

    candidates = list(
        __import__('taxi.models', fromlist=['Driver']).Driver.objects.filter(
            is_active=True,
            is_on_duty=True,
            approval_status='approved',
            latitude__isnull=False,
            longitude__isnull=False,
        ).exclude(id__in=rejected_ids)
    )

    if not candidates:
        return None

    nearest, _ = find_nearest_driver(candidates, order.from_lat, order.from_lng)
    if not nearest:
        return None

    order.dispatched_to = nearest
    order.save(update_fields=['dispatched_to'])

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
    return nearest
