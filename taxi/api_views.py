"""
REST API — Haydovchi mobil ilovasi uchun.

Endpoints:
  POST /api/driver/register/        — Ro'yxatdan o'tish
  POST /api/driver/login/           — Kirish → token
  GET  /api/driver/profile/         — O'z profili
  POST /api/driver/duty/            — is_on_duty toggle
  PUT  /api/driver/fcm/             — FCM token yangilash
  POST /api/driver/location/        — GPS lokatsiyani yangilash

  GET  /api/orders/available/       — Pending + o'z faol buyurtmalari
  GET  /api/orders/my/              — O'z tarixi
  POST /api/orders/<id>/accept/     — Qabul qilish (komissiya yechiladi)
  POST /api/orders/<id>/on_way/     — Yo'lda
  POST /api/orders/<id>/complete/   — Yakunlash
  POST /api/orders/<id>/cancel/     — Bekor qilish

  GET  /api/tariff/                 — Joriy tariff (base_price, price_per_km)
"""

from django.contrib.auth import authenticate
from django.db.models import Q
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .models import Driver, Order, TariffSettings, ChatMessage, MapsSettings, DriverActivityLog, SosAlert
from .serializers import (
    DriverRegisterSerializer,
    DriverLoginSerializer,
    DriverProfileSerializer,
    OrderSerializer,
)
from .utils import send_telegram, dispatch_order, tg_new_order, tg_order_accepted, tg_order_on_way, tg_order_arrived, tg_order_completed, tg_order_cancelled, tg_order_rejected, tg_driver_registered, tg_driver_login, tg_duty_changed, tg_sos_alert


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log(driver, action, detail='', request=None):
    ip = _get_ip(request) if request else None
    ua = request.META.get('HTTP_USER_AGENT', '') if request else ''
    DriverActivityLog.objects.create(driver=driver, action=action, detail=detail, ip_address=ip, user_agent=ua)


# ── helpers ──────────────────────────────────────────────────────────────────────────────────────

def get_driver(request):
    try:
        return request.user.driver_profile
    except Driver.DoesNotExist:
        return None


def driver_required(fn):
    from functools import wraps
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        driver = get_driver(request)
        if driver is None:
            return Response({'detail': 'Haydovchi profili topilmadi.'}, status=403)
        if driver.approval_status != Driver.APPROVAL_APPROVED:
            return Response(
                {'detail': 'Hisobingiz hali tasdiqlanmagan. Admin tasdiqlashini kuting.'},
                status=403,
            )
        return fn(request, driver, *args, **kwargs)
    return wrapper


def get_driver_by_user(user):
    try:
        return user.driver_profile
    except Exception:
        return None


# ── Auth ──────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def driver_register(request):
    serializer = DriverRegisterSerializer(data=request.data)
    if serializer.is_valid():
        driver = serializer.save()
        tg_driver_registered(driver)
        return Response(
            {
                'detail': "Ro'yxatdan muvaffaqiyatli o'tdingiz. Admin tasdiqlagandan so'ng kirishingiz mumkin.",
                'driver_id': driver.id,
            },
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def driver_login(request):
    serializer = DriverLoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    phone    = serializer.validated_data['phone_number']
    password = serializer.validated_data['password']
    user     = authenticate(request, username=phone, password=password)

    if user is None:
        return Response({'detail': "Telefon raqami yoki parol noto'g'ri."}, status=401)

    driver = get_driver_by_user(user)
    if driver is None:
        return Response({'detail': 'Haydovchi profili topilmadi.'}, status=403)
    if driver.approval_status == Driver.APPROVAL_REJECTED:
        return Response({'detail': "Hisobingiz rad etilgan. Admin bilan bog'laning."}, status=403)
    if driver.approval_status == Driver.APPROVAL_PENDING:
        return Response({'detail': 'Hisobingiz hali tasdiqlanmagan. Admin tasdiqlashini kuting.'}, status=403)

    token, _ = Token.objects.get_or_create(user=user)
    _log(driver, DriverActivityLog.ACTION_LOGIN, request=request)
    tg_driver_login(driver, ip=_get_ip(request))
    return Response({'token': token.key, 'driver': DriverProfileSerializer(driver).data})


# ── Profile ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def driver_profile(request, driver):
    return Response(DriverProfileSerializer(driver, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def driver_photo_upload(request, driver):
    photo = request.FILES.get('photo')
    if not photo:
        return Response({'detail': 'photo fayl talab qilinadi.'}, status=400)
    if driver.photo:
        driver.photo.delete(save=False)
    driver.photo = photo
    driver.save(update_fields=['photo'])
    url = request.build_absolute_uri(driver.photo.url)
    return Response({'photo_url': url})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def driver_duty_toggle(request, driver):
    from django.utils import timezone
    driver.is_on_duty = not driver.is_on_duty
    update_fields = ['is_on_duty']
    if driver.is_on_duty:
        driver.last_seen = timezone.now()
        update_fields.append('last_seen')
    driver.save(update_fields=update_fields)
    action = DriverActivityLog.ACTION_DUTY_ON if driver.is_on_duty else DriverActivityLog.ACTION_DUTY_OFF
    _log(driver, action, request=request)
    tg_duty_changed(driver, driver.is_on_duty)
    return Response({'is_on_duty': driver.is_on_duty})


@api_view(['PUT', 'POST'])
@permission_classes([IsAuthenticated])
@driver_required
def driver_fcm_update(request, driver):
    token = request.data.get('fcm_token', '').strip()
    if not token:
        return Response({'detail': 'fcm_token maydoni talab qilinadi.'}, status=400)
    driver.fcm_token = token
    driver.save(update_fields=['fcm_token'])
    return Response({'detail': 'FCM token yangilandi.'})


AUTO_OFFLINE_MINUTES = 10  # GPS kelmasa shu daqiqadan keyin navbatdan chiqarish


def _auto_offline_check(driver):
    """last_seen dan AUTO_OFFLINE_MINUTES o'tsa is_on_duty=False qiladi."""
    if not driver.is_on_duty or not driver.last_seen:
        return
    from django.utils import timezone
    elapsed = (timezone.now() - driver.last_seen).total_seconds()
    if elapsed > AUTO_OFFLINE_MINUTES * 60:
        driver.is_on_duty = False
        driver.save(update_fields=['is_on_duty'])
        _log(driver, DriverActivityLog.ACTION_DUTY_OFF, detail='Auto offline (GPS kelmadi)')
        tg_duty_changed(driver, False)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def driver_location_update(request, driver):
    """GPS koordinatalarni yangilash."""
    lat = request.data.get('latitude')
    lng = request.data.get('longitude')
    if lat is None or lng is None:
        return Response({'detail': 'latitude va longitude talab qilinadi.'}, status=400)
    try:
        from django.utils import timezone
        from .utils import reverse_geocode_address
        driver.latitude  = float(lat)
        driver.longitude = float(lng)
        driver.last_seen = timezone.now()
        address = reverse_geocode_address(float(lat), float(lng))
        if address:
            driver.last_address = address
        driver.save(update_fields=['latitude', 'longitude', 'last_seen', 'last_address'])
        return Response({'detail': 'Lokatsiya yangilandi.', 'latitude': driver.latitude, 'longitude': driver.longitude})
    except (ValueError, TypeError):
        return Response({'detail': "Noto'g'ri koordinatalar."}, status=400)


# ── Tariff ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([AllowAny])
def get_tariff(request):
    """Joriy tariff ma'lumotlarini qaytaradi (ilovada narx hisoblash uchun)."""
    t = TariffSettings.get()
    return Response({
        'base_price':   str(t.base_price),
        'price_per_km': str(t.price_per_km),
        'commission':   str(t.commission),
    })


# ── Orders ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def available_orders(request, driver):
    _auto_offline_check(driver)
    qs = Order.objects.select_related('client', 'driver').filter(
        Q(status='pending', dispatched_to=driver) |
        Q(status='pending', dispatched_to__isnull=True) |
        Q(driver=driver, status__in=['accepted', 'on_way', 'arrived'])
    ).exclude(
        Q(status='pending', rejected_by=driver)
    )

    # ── Destination mode filtr ──────────────────────────────────────────────
    if driver.destination_mode and driver.destination_lat and driver.destination_lng:
        from .utils import haversine
        RADIUS_KM = 3.0   # yo'nalishdan 3 km radius
        filtered_ids = []
        for order in qs.filter(status='pending'):
            if order.to_lat and order.to_lng:
                dist = haversine(
                    order.to_lat, order.to_lng,
                    driver.destination_lat, driver.destination_lng
                )
                if dist is not None and dist <= RADIUS_KM:
                    filtered_ids.append(order.pk)
        # Faol buyurtmalarni har doim qo'shib qo'yamiz
        active_ids = list(
            qs.filter(driver=driver, status__in=['accepted', 'on_way', 'arrived'])
            .values_list('pk', flat=True)
        )
        qs = qs.filter(pk__in=filtered_ids + active_ids)

    qs = qs.order_by('-created_at')
    return Response(OrderSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def my_orders(request, driver):
    qs = Order.objects.select_related('client').filter(driver=driver).order_by('-created_at')[:50]
    return Response(OrderSerializer(qs, many=True, context={'request': request}).data)


def _order_action(request, driver, pk, allowed_statuses, new_status):
    try:
        order = Order.objects.select_related('client', 'driver').get(pk=pk)
    except Order.DoesNotExist:
        return Response({'detail': 'Buyurtma topilmadi.'}, status=404)

    if order.status not in allowed_statuses:
        return Response(
            {'detail': f"Bu amalni '{order.get_status_display()}' holatida bajarib bo'lmaydi."},
            status=400,
        )

    if order.driver_id and order.driver_id != driver.id:
        return Response({'detail': 'Bu buyurtma sizga tegishli emas.'}, status=403)

    update_fields = ['status', 'updated_at']

    if new_status == 'accepted':
        from django.db import transaction
        from decimal import Decimal
        with transaction.atomic():
            # Atomik: boshqa haydovchi qabul qilmagan bo'lsin
            locked = Order.objects.select_for_update().get(pk=order.pk)
            if locked.status != 'pending':
                return Response({'detail': 'Bu buyurtmani allaqachon boshqa haydovchi qabul qildi.'}, status=409)
            if locked.dispatched_to_id and locked.dispatched_to_id != driver.id:
                return Response({'detail': 'Bu buyurtma sizga yuborilmagan.'}, status=403)

            tariff = TariffSettings.get()
            commission = locked.commission if locked.commission else tariff.commission
            if driver.balance < commission:
                return Response(
                    {'detail': f"Balansingizda yetarli mablag' yo'q. Komissiya: {commission} UZS. Joriy balans: {driver.balance} UZS."},
                    status=400,
                )
            driver.balance -= Decimal(str(commission))
            driver.save(update_fields=['balance'])
            order.driver = driver
            order.commission = commission
            order.dispatched_to = None
            order.status = new_status
            order.save(update_fields=['status', 'driver', 'commission', 'dispatched_to', 'updated_at'])
    else:
        order.status = new_status
        order.save(update_fields=update_fields)

    # Mijoz trips_count ni yangilash (yakunlanganda)
    if new_status == 'completed':
        try:
            order.client.trips_count += 1
            order.client.save(update_fields=['trips_count'])
        except Exception:
            pass  # trips_count optional, buyurtma yakunlanishi bloklanmasin

    # Telegram xabarlari
    if new_status == 'accepted':    tg_order_accepted(order, driver)
    elif new_status == 'on_way':    tg_order_on_way(order, driver)
    elif new_status == 'arrived':   tg_order_arrived(order, driver)
    elif new_status == 'completed': tg_order_completed(order, driver)
    elif new_status == 'cancelled': tg_order_cancelled(order, driver)

    return Response(OrderSerializer(order, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_reject(request, driver, pk):
    """Haydovchi rad etadi — keyingi yaqin haydovchiga yuboriladi yoki umumiy tablodan yashiriladi."""
    try:
        order = Order.objects.filter(
            Q(pk=pk, status='pending'),
            Q(dispatched_to=driver) | Q(dispatched_to__isnull=True)
        ).get()
    except Order.DoesNotExist:
        return Response({'detail': 'Buyurtma topilmadi.'}, status=404)

    was_dispatched = (order.dispatched_to_id == driver.id)

    order.rejected_by.add(driver)
    
    if was_dispatched:
        order.dispatched_to = None
        order.save(update_fields=['dispatched_to'])
        tg_order_rejected(order, driver)
        import threading
        threading.Thread(target=dispatch_order, args=(order,), daemon=True).start()

    return Response({'detail': 'Rad etildi.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_accept(request, driver, pk):
    return _order_action(request, driver, pk, ['pending'], 'accepted')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_on_way(request, driver, pk):
    return _order_action(request, driver, pk, ['accepted'], 'on_way')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_arrived(request, driver, pk):
    return _order_action(request, driver, pk, ['on_way'], 'arrived')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_complete(request, driver, pk):
    return _order_action(request, driver, pk, ['arrived', 'on_way', 'accepted'], 'completed')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def order_cancel(request, driver, pk):
    return _order_action(request, driver, pk, ['accepted', 'on_way', 'arrived'], 'cancelled')



# ── Maps config ──────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def maps_config(request):
    """Mobil ilova uchun Maps API kalitlarini qaytaradi."""
    maps = MapsSettings.get()
    return Response({'yandex_api_key': maps.yandex_mapkit_key})


# ── Geocoding ─────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reverse_geocode(request):
    """Koordinatalarni manzilga aylantiradi — admin tanlagan API orqali."""
    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    if not lat or not lng:
        return Response({'detail': 'lat va lng talab qilinadi.'}, status=400)

    maps = MapsSettings.get()
    address = None

    try:
        import urllib.request, json

        if maps.provider == MapsSettings.PROVIDER_YANDEX and maps.api_key:
            url = (f'https://geocode-maps.yandex.ru/1.x/?apikey={maps.api_key}'
                   f'&geocode={lng},{lat}&format=json&lang=uz_UZ&results=1')
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            members = data['response']['GeoObjectCollection']['featureMember']
            if members:
                obj  = members[0]['GeoObject']
                name = obj.get('name', '')
                desc = obj.get('description', '')
                address = f'{name}, {desc}' if name and desc else name or desc

        elif maps.provider == MapsSettings.PROVIDER_GEOAPIFY and maps.api_key:
            url = (f'https://api.geoapify.com/v1/geocode/reverse'
                   f'?lat={lat}&lon={lng}&lang=uz&apiKey={maps.api_key}')
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            props = data['features'][0]['properties']
            parts = [p for p in [props.get('street'), props.get('suburb') or props.get('district'), props.get('city') or props.get('town')] if p]
            address = ', '.join(parts) or props.get('formatted')

        elif maps.provider == MapsSettings.PROVIDER_GOOGLE and maps.api_key:
            url = (f'https://maps.googleapis.com/maps/api/geocode/json'
                   f'?latlng={lat},{lng}&key={maps.api_key}&language=uz')
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            results = data.get('results', [])
            if results:
                address = results[0].get('formatted_address')

        else:  # Nominatim (default)
            url = (f'https://nominatim.openstreetmap.org/reverse'
                   f'?lat={lat}&lon={lng}&format=json&accept-language=uz,ru&zoom=16')
            req = urllib.request.Request(url, headers={'User-Agent': 'VijdonTaxiDriverApp/1.0'})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
            addr = data.get('address', {})
            parts = [p for p in [
                addr.get('road') or addr.get('street') or addr.get('pedestrian') or addr.get('residential'),
                addr.get('suburb') or addr.get('neighbourhood') or addr.get('village'),
                addr.get('city') or addr.get('town') or addr.get('county'),
            ] if p]
            address = ', '.join(parts) or data.get('display_name')

    except Exception:
        pass

    return Response({'address': address})


# ── Chat ──────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def chat_messages(request, driver):
    ChatMessage.objects.filter(driver=driver, sender=ChatMessage.SENDER_OPERATOR, is_read=False).update(is_read=True)
    msgs = ChatMessage.objects.filter(driver=driver).order_by('created_at')[:100]
    data = []
    for m in msgs:
        item = {
            'id':         m.id,
            'sender':     m.sender,
            'text':       m.text,
            'is_read':    m.is_read,
            'created_at': m.created_at.isoformat(),
            'audio_url':  request.build_absolute_uri(m.audio.url) if m.audio else None,
        }
        data.append(item)
    return Response({'messages': data})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def chat_send(request, driver):
    text  = request.data.get('text', '').strip()
    audio = request.FILES.get('audio')
    if not text and not audio:
        return Response({'detail': 'text yoki audio talab qilinadi.'}, status=400)
    msg = ChatMessage.objects.create(
        driver=driver,
        sender=ChatMessage.SENDER_DRIVER,
        text=text,
        audio=audio or None,
    )
    if text:
        send_telegram(f"💬 <b>{driver.full_name}</b> ({driver.car_number}):\n{text}")
    elif audio:
        send_telegram(f"🎤 <b>{driver.full_name}</b> ({driver.car_number}) ovozli xabar yubordi")
    return Response({
        'id': msg.id, 'sender': msg.sender, 'text': msg.text,
        'audio_url': request.build_absolute_uri(msg.audio.url) if msg.audio else None,
        'created_at': msg.created_at.isoformat()
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def chat_unread_count(request, driver):
    """O'qilmagan operatordan xabarlar soni."""
    count = ChatMessage.objects.filter(driver=driver, sender=ChatMessage.SENDER_OPERATOR, is_read=False).count()
    return Response({'unread': count})


# ── Destination Mode ──────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def destination_mode_set(request, driver):
    """
    Destination mode yoqish/o'chirish.
    Body: { "enabled": true, "lat": 41.2, "lng": 69.2, "address": "Yunusobod..." }
    O'chirish uchun: { "enabled": false }
    """
    enabled = request.data.get('enabled', False)
    if enabled:
        lat  = request.data.get('lat')
        lng  = request.data.get('lng')
        addr = request.data.get('address', '').strip()
        if lat is None or lng is None:
            return Response({'detail': 'lat va lng talab qilinadi.'}, status=400)
        try:
            driver.destination_mode    = True
            driver.destination_lat     = float(lat)
            driver.destination_lng     = float(lng)
            driver.destination_address = addr
            driver.save(update_fields=[
                'destination_mode', 'destination_lat',
                'destination_lng', 'destination_address'
            ])
        except (ValueError, TypeError):
            return Response({'detail': "Noto'g'ri koordinatalar."}, status=400)
    else:
        driver.destination_mode    = False
        driver.destination_lat     = None
        driver.destination_lng     = None
        driver.destination_address = ''
        driver.save(update_fields=[
            'destination_mode', 'destination_lat',
            'destination_lng', 'destination_address'
        ])

    return Response({
        'destination_mode':    driver.destination_mode,
        'destination_address': driver.destination_address,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def destination_mode_get(request, driver):
    """Joriy destination mode holatini qaytaradi."""
    return Response({
        'destination_mode':    driver.destination_mode,
        'destination_lat':     driver.destination_lat,
        'destination_lng':     driver.destination_lng,
        'destination_address': driver.destination_address,
    })


# ── SOS ──────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@driver_required
def sos_send(request, driver):
    """
    Haydovchi SOS signal yuboradi.
    Body: { "lat": 41.2, "lng": 69.2, "address": "...", "note": "..." }
    """
    lat     = request.data.get('lat')
    lng     = request.data.get('lng')
    address = request.data.get('address', '').strip()
    note    = request.data.get('note', '').strip()

    alert = SosAlert.objects.create(
        driver=driver,
        latitude=float(lat) if lat is not None else None,
        longitude=float(lng) if lng is not None else None,
        address=address,
        note=note,
    )
    tg_sos_alert(alert)
    return Response({'id': alert.id, 'detail': 'SOS signal yuborildi.'}, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@driver_required
def sos_my(request, driver):
    """Haydovchining o'z SOS tarixi."""
    alerts = SosAlert.objects.filter(driver=driver)[:20]
    data = [{
        'id':         a.id,
        'latitude':   a.latitude,
        'longitude':  a.longitude,
        'address':    a.address,
        'note':       a.note,
        'status':     a.status,
        'created_at': a.created_at.isoformat(),
    } for a in alerts]
    return Response(data)


from django.http import JsonResponse as DjJsonResponse
from .models import Client, Order

def client_last_order_api(request):
    phone = request.GET.get('phone', '').strip()
    if not phone:
        return DjJsonResponse({'found': False})
    try:
        client = Client.objects.get(phone_number=phone)
    except Client.DoesNotExist:
        return DjJsonResponse({'found': False})
    last = Order.objects.filter(client=client).order_by('-created_at').first()
    if not last:
        return DjJsonResponse({'found': True, 'name': client.full_name or '', 'from_address': '', 'from_lat': '', 'from_lng': ''})
    return DjJsonResponse({
        'found': True,
        'name': client.full_name or '',
        'from_address': last.from_address,
        'from_lat': last.from_lat or '',
        'from_lng': last.from_lng or '',
    })
