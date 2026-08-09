"""
REST API — native Android haydovchi ilovasi uchun.
URL prefix: /api/driverapp/  (config/urls.py, `/panel/` prefiksisiz — Cloudflare
WAF qoidasi shu aniq prefiksga qarab osongina istisno qilinishi uchun).

Auth: DRF TokenAuthentication (`Authorization: Token <key>`). Bu fayl
taxi/api_views.py (eski, ishlatilmayotgan mobil API)ga bog'liq emas — mustaqil,
lekin og'ir/pul bilan bog'liq mantiqni (balans yechish, dispatch, taximetr
idempotentligi) taxi/utils.py va taxi/driver_views.py'dagi sinovdan o'tgan
funksiyalarni chaqirib amalga oshiradi, qayta yozmaydi.
"""
import json
from decimal import Decimal
from functools import wraps

from django.contrib.auth import authenticate
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Driver, Order, TariffSettings, DriverActivityLog, MapsSettings
from .driverapp_serializers import DriverAppProfileSerializer, DriverAppOrderSerializer
from .serializers import DriverRegisterSerializer


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log_activity(driver, action, detail, request):
    DriverActivityLog.objects.create(
        driver=driver, action=action, detail=detail,
        ip_address=_get_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )


# ── Auth decorators ───────────────────────────────────────────────────────────

def driver_profile_required(fn):
    """Faqat token orqali haydovchi profili aniqlanishini talab qiladi —
    approval_status/is_frozen tekshirmaydi, chunki `/me/` kabi endpointlar
    ilova ichida "kutilmoqda"/"muzlatilgan" ekranini ko'rsatish uchun aynan
    shu holatning o'zini bilishi kerak."""
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        try:
            driver = request.user.driver_profile
        except Driver.DoesNotExist:
            return Response({'detail': 'Haydovchi profili topilmadi.', 'code': 'no_profile'}, status=403)
        return fn(request, driver, *args, **kwargs)
    return wrapper


def driver_required(fn):
    """To'liq tekshiruv — faqat tasdiqlangan va muzlatilmagan haydovchi
    kirishi mumkin bo'lgan amaliy endpointlar uchun (buyurtmalar, holat,
    joylashuv va h.k.). `code` maydoni orqali ilova aniq qaysi ekranni
    (kutilmoqda/muzlatilgan) ko'rsatishi kerakligini biladi."""
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        try:
            driver = request.user.driver_profile
        except Driver.DoesNotExist:
            return Response({'detail': 'Haydovchi profili topilmadi.', 'code': 'no_profile'}, status=403)
        if driver.is_frozen:
            return Response({'detail': 'Hisobingiz muzlatilgan. Admin bilan bog\'laning.', 'code': 'frozen'}, status=403)
        if driver.approval_status != Driver.APPROVAL_APPROVED:
            return Response({'detail': 'Hisobingiz hali tasdiqlanmagan.', 'code': 'pending'}, status=403)
        return fn(request, driver, *args, **kwargs)
    return wrapper


# ── Auth ──────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    from .utils import tg_driver_registered
    s = DriverRegisterSerializer(data=request.data)
    if not s.is_valid():
        return Response(s.errors, status=400)
    driver = s.save()
    tg_driver_registered(driver)
    return Response({'detail': "Ro'yxatdan o'tish so'rovi yuborildi. Admin tasdiqlashini kuting.", 'driver_id': driver.id}, status=201)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    from .utils import tg_driver_login
    phone    = str(request.data.get('phone_number', '')).strip()
    password = str(request.data.get('password', ''))
    if not phone or not password:
        return Response({'detail': 'Telefon raqami va parol kiritilishi shart.'}, status=400)
    user = authenticate(request, username=phone, password=password)
    if user is None:
        return Response({'detail': "Telefon raqami yoki parol noto'g'ri."}, status=401)
    try:
        driver = user.driver_profile
    except Driver.DoesNotExist:
        return Response({'detail': 'Haydovchi profili topilmadi.'}, status=403)
    if driver.approval_status == Driver.APPROVAL_REJECTED:
        return Response({'detail': 'Hisobingiz rad etilgan.', 'code': 'rejected'}, status=403)
    token, _ = Token.objects.get_or_create(user=user)
    _log_activity(driver, DriverActivityLog.ACTION_LOGIN, 'Android ilovadan kirdi', request)
    tg_driver_login(driver, ip=_get_ip(request))
    return Response({
        'token': token.key,
        'driver': DriverAppProfileSerializer(driver, context={'request': request}).data,
    })


@api_view(['GET'])
@driver_profile_required
def me(request, driver):
    return Response(DriverAppProfileSerializer(driver, context={'request': request}).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def app_config(request):
    """Ilova ishga tushganda bir marta so'raydigan umumiy sozlamalar —
    tarif, operator raqami (bekor qilish uchun), xarita kaliti."""
    tariff = TariffSettings.get()
    maps = MapsSettings.get()
    return Response({
        'base_price': tariff.base_price,
        'price_per_km': tariff.price_per_km,
        'waiting_price_per_minute': tariff.waiting_price_per_minute,
        'commission': tariff.commission,
        'operator_phone': tariff.operator_phone,
        'yandex_api_key': maps.yandex_mapkit_key,
    })


# ── Holat / joylashuv ──────────────────────────────────────────────────────────

@api_view(['POST'])
@driver_required
def duty_toggle(request, driver):
    from django.utils import timezone
    from .models import AddressQueueEntry
    from .utils import tg_duty_changed

    driver.is_on_duty = not driver.is_on_duty
    driver.save(update_fields=['is_on_duty'])
    if not driver.is_on_duty:
        AddressQueueEntry.objects.filter(driver=driver, left_at__isnull=True).update(left_at=timezone.now())
    action = DriverActivityLog.ACTION_DUTY_ON if driver.is_on_duty else DriverActivityLog.ACTION_DUTY_OFF
    _log_activity(driver, action, 'Android ilovadan', request)
    tg_duty_changed(driver, driver.is_on_duty)
    return Response({'is_on_duty': driver.is_on_duty})


@api_view(['POST'])
@driver_required
def location_update(request, driver):
    from django.utils import timezone
    import datetime
    from .utils import update_address_queue_membership, ADDRESS_QUEUE_STALE_MINUTES, reverse_geocode_address

    try:
        lat = float(request.data.get('lat'))
        lng = float(request.data.get('lng'))
    except (TypeError, ValueError):
        return Response({'detail': 'lat/lng noto\'g\'ri.'}, status=400)

    stale_cutoff = timezone.now() - datetime.timedelta(minutes=ADDRESS_QUEUE_STALE_MINUTES)
    was_stale = not driver.last_seen or driver.last_seen < stale_cutoff

    driver.latitude = lat
    driver.longitude = lng
    driver.last_seen = timezone.now()
    driver.last_address = reverse_geocode_address(lat, lng) or driver.last_address
    update_fields = ['latitude', 'longitude', 'last_seen', 'last_address']
    if driver.freeze_warning_sent_at:
        driver.freeze_warning_sent_at = None
        update_fields.append('freeze_warning_sent_at')
    driver.save(update_fields=update_fields)

    update_address_queue_membership(driver, lat, lng, was_stale=was_stale)
    return Response({'latitude': lat, 'longitude': lng})


@api_view(['POST'])
@driver_required
def fcm_sync(request, driver):
    token = str(request.data.get('fcm_token', '')).strip()
    if not token:
        return Response({'detail': 'fcm_token kiritilishi shart.'}, status=400)
    driver.fcm_token = token
    driver.save(update_fields=['fcm_token'])
    return Response({'detail': 'FCM token yangilandi.'})


# ── Buyurtmalar ────────────────────────────────────────────────────────────────

def _visible_orders_qs(driver):
    from django.db.models import Q
    from django.utils import timezone
    import datetime
    from .utils import haversine

    dispatch_cutoff = timezone.now() - datetime.timedelta(seconds=TariffSettings.get().dispatch_timeout)
    active_orders = list(Order.objects.filter(
        driver=driver, status__in=Order.ACTIVE_STATUSES
    ).select_related('client', 'driver'))

    if len(active_orders) >= Order.MAX_ACTIVE_PER_DRIVER:
        base = active_orders
    else:
        pending_qs = Order.objects.select_related('client', 'driver').filter(
            Q(status='pending', dispatched_to=driver) |
            Q(status='pending', dispatched_to__isnull=True) |
            Q(status='pending', dispatched_at__lt=dispatch_cutoff)
        ).exclude(status__in=['cancelled', 'completed']).order_by('-created_at')
        base = active_orders + list(pending_qs)

    if driver.destination_mode and driver.destination_lat and driver.destination_lng:
        filtered = []
        for o in base:
            if o.status != 'pending':
                filtered.append(o)
                continue
            if o.to_lat and o.to_lng:
                d = haversine(o.to_lat, o.to_lng, driver.destination_lat, driver.destination_lng)
                if d is not None and d <= 5:
                    filtered.append(o)
        return filtered
    return base


@api_view(['GET'])
@driver_required
def orders_available(request, driver):
    orders = _visible_orders_qs(driver)
    data = DriverAppOrderSerializer(orders, many=True, context={'driver': driver}).data
    return Response({
        'orders': data,
        'low_balance': driver.balance < TariffSettings.get().commission,
    })


@api_view(['GET'])
@driver_required
def orders_my(request, driver):
    orders = Order.objects.filter(driver=driver).select_related('client', 'driver').order_by('-created_at')[:50]
    return Response(DriverAppOrderSerializer(orders, many=True, context={'driver': driver}).data)


@api_view(['POST'])
@driver_required
def order_reject(request, driver, pk):
    from .utils import _resolve_dispatch_attempt, _requeue_driver_to_back, dispatch_order, tg_order_rejected
    from .models import DispatchAttempt

    should_redispatch = False
    with transaction.atomic():
        locked = get_object_or_404(Order.objects.select_for_update(), pk=pk)
        if locked.status == 'pending':
            locked.rejected_by.add(driver)
            _log_activity(driver, DriverActivityLog.ACTION_ORDER, f"Buyurtma #{locked.id} rad etildi", request)
            should_redispatch = locked.dispatched_to_id == driver.id
            if should_redispatch:
                locked.dispatched_to = None
                locked.save(update_fields=['dispatched_to'])
                _resolve_dispatch_attempt(locked, driver.id, DispatchAttempt.RESULT_REJECTED)
                _requeue_driver_to_back(driver.id, locked)
    if should_redispatch:
        tg_order_rejected(locked, driver)
        dispatch_order(locked)
    return Response({'detail': 'Rad etildi.'})


@api_view(['POST'])
@driver_required
def order_accept(request, driver, pk):
    from django.utils import timezone
    from .models import DispatchAttempt, AddressQueueEntry
    from .utils import _resolve_dispatch_attempt, tg_order_accepted, tg_low_balance_alert, sms_order_status

    with transaction.atomic():
        locked = get_object_or_404(Order.objects.select_for_update(), pk=pk)
        if locked.status != 'pending':
            return Response({'detail': 'Bu buyurtmani boshqa haydovchi qabul qildi.'}, status=409)
        if locked.dispatched_to_id and locked.dispatched_to_id != driver.id:
            return Response({'detail': 'Bu buyurtma sizga yuborilmagan.'}, status=403)
        active_count = Order.objects.filter(driver=driver, status__in=Order.ACTIVE_STATUSES).count()
        if active_count >= Order.MAX_ACTIVE_PER_DRIVER:
            return Response({
                'detail': f"Bir vaqtda ko'pi bilan {Order.MAX_ACTIVE_PER_DRIVER} ta faol buyurtma olish mumkin.",
            }, status=400)
        tariff = TariffSettings.get()
        commission = locked.commission or tariff.commission
        if driver.balance < commission:
            return Response({'detail': f'Balans yetarli emas. Komissiya: {commission} UZS'}, status=400)
        driver.balance -= Decimal(str(commission))
        driver.save(update_fields=['balance'])
        locked.driver = driver
        locked.status = 'accepted'
        locked.dispatched_to = None
        locked.save(update_fields=['status', 'driver', 'dispatched_to', 'updated_at'])
        _resolve_dispatch_attempt(locked, driver.id, DispatchAttempt.RESULT_ACCEPTED)
        AddressQueueEntry.objects.filter(driver=driver, left_at__isnull=True).update(left_at=timezone.now())

    tg_order_accepted(locked, driver)
    tg_low_balance_alert(driver)
    sms_order_status(locked, 'accepted')
    _log_activity(driver, DriverActivityLog.ACTION_ORDER, f"Buyurtma #{locked.id} qabul qilindi, -{commission} UZS komissiya", request)
    return Response(DriverAppOrderSerializer(locked, context={'driver': driver}).data)


def _transition(request, driver, pk, allowed_statuses, new_status):
    from .utils import tg_order_on_way, tg_order_arrived, tg_order_completed, tg_order_cancelled, sms_order_status, haversine

    order = get_object_or_404(Order, pk=pk)
    if order.driver_id != driver.id:
        return Response({'detail': 'Bu buyurtma sizga tegishli emas.'}, status=403)
    if order.status not in allowed_statuses:
        return Response({'detail': f"'{order.get_status_display()}' holatida bu amal mumkin emas."}, status=400)

    order.status = new_status
    update_fields = ['status', 'updated_at']

    if new_status == 'on_way' and not order.tmx_start_time:
        from django.utils import timezone
        order.tmx_start_time = timezone.now()
        update_fields.append('tmx_start_time')

    try:
        tmx_dist = request.data.get('tmx_dist_km')
        tmx_price = request.data.get('tmx_price')
        if tmx_dist and float(tmx_dist) > 0 and float(tmx_dist) >= float(order.tmx_dist_km or 0):
            order.distance_km = round(float(tmx_dist), 2)
            order.tmx_dist_km = round(float(tmx_dist), 2)
            update_fields += ['distance_km', 'tmx_dist_km']
        if tmx_price and float(tmx_price) > 0 and float(tmx_price) >= float(order.price or 0):
            order.price = round(float(tmx_price), 2)
            update_fields.append('price')
    except (TypeError, ValueError):
        pass

    if new_status == 'completed':
        if order.distance_km is None and order.from_lat and order.from_lng and order.to_lat and order.to_lng:
            calc_dist = haversine(order.from_lat, order.from_lng, order.to_lat, order.to_lng)
            if calc_dist:
                order.distance_km = round(calc_dist, 2)
                if 'distance_km' not in update_fields:
                    update_fields.append('distance_km')
        if order.price is None:
            tariff = TariffSettings.get()
            waiting_minutes = (order.tmx_paused_ms or 0) / 60000
            order.price = (
                tariff.calc_price(order.distance_km, waiting_minutes)
                if order.distance_km is not None else tariff.base_price
            )
            if 'price' not in update_fields:
                update_fields.append('price')

    order.save(update_fields=update_fields)

    if new_status == 'completed':
        order.client.trips_count += 1
        order.client.save(update_fields=['trips_count'])
        driver.trips_count = (driver.trips_count or 0) + 1
        driver.save(update_fields=['trips_count'])

    tg_map = {'on_way': tg_order_on_way, 'arrived': tg_order_arrived, 'completed': tg_order_completed, 'cancelled': tg_order_cancelled}
    if new_status in tg_map:
        tg_map[new_status](order, driver)
    if new_status in ('arrived', 'completed', 'cancelled'):
        sms_order_status(order, new_status)

    _log_activity(driver, DriverActivityLog.ACTION_ORDER, f"Buyurtma #{order.id} — {order.get_status_display()}", request)
    return Response(DriverAppOrderSerializer(order, context={'driver': driver}).data)


@api_view(['POST'])
@driver_required
def order_on_way(request, driver, pk):
    return _transition(request, driver, pk, ['accepted'], 'on_way')


@api_view(['POST'])
@driver_required
def order_arrived(request, driver, pk):
    return _transition(request, driver, pk, ['on_way'], 'arrived')


@api_view(['POST'])
@driver_required
def order_complete(request, driver, pk):
    return _transition(request, driver, pk, ['arrived', 'on_way', 'accepted'], 'completed')


@api_view(['POST'])
@driver_required
def order_meter(request, driver, pk):
    order = get_object_or_404(Order, pk=pk, driver=driver)
    if order.status in ('completed', 'cancelled'):
        return Response({'dist_km': order.tmx_dist_km, 'price': float(order.price) if order.price else 0})

    try:
        dist_km = float(request.data.get('dist_km') or 0)
        price = float(request.data.get('price') or 0)
        waiting = str(request.data.get('waiting') or '0') == '1'
        wait_ms = int(request.data.get('wait_ms') or 0)
    except (TypeError, ValueError):
        return Response({'detail': "Noto'g'ri qiymatlar."}, status=400)

    update_fields = ['tmx_paused', 'updated_at']
    order.tmx_paused = waiting

    if dist_km >= float(order.tmx_dist_km or 0):
        order.tmx_dist_km = round(dist_km, 2)
        update_fields.append('tmx_dist_km')
        if dist_km > 0:
            order.distance_km = round(dist_km, 2)
            update_fields.append('distance_km')
    if wait_ms >= (order.tmx_paused_ms or 0):
        order.tmx_paused_ms = max(0, wait_ms)
        update_fields.append('tmx_paused_ms')
    if price > 0 and price >= float(order.price or 0):
        order.price = Decimal(str(round(price)))
        update_fields.append('price')
    order.save(update_fields=update_fields)

    return Response({'dist_km': order.tmx_dist_km, 'price': float(order.price) if order.price else price})


@api_view(['POST'])
@driver_required
def order_create(request, driver):
    from .models import Client, SavedAddress
    from .utils import tg_new_order, tg_order_accepted, tg_low_balance_alert, dispatch_order

    phone_number = str(request.data.get('phone_number', '')).strip()
    customer_name = str(request.data.get('customer_name', '')).strip()
    to_address = str(request.data.get('to_address', '')).strip()
    assign_to = request.data.get('assign_to', 'self')
    saved_address_id = request.data.get('saved_address_id')

    saved_address = SavedAddress.objects.filter(pk=saved_address_id).first() if saved_address_id else None
    if saved_address:
        from_address = saved_address.address or saved_address.name
        from_lat, from_lng = saved_address.lat, saved_address.lng
    else:
        from_address = str(request.data.get('from_address', '')).strip()
        from_lat, from_lng = driver.latitude, driver.longitude

    if not phone_number or not from_address:
        return Response({'detail': "Mijoz raqami va manzil kiritilishi shart."}, status=400)

    tariff = TariffSettings.get()
    client, _created = Client.objects.get_or_create(phone_number=phone_number)
    if client.is_blocked:
        return Response({'detail': 'Bu mijoz bloklangan.'}, status=400)
    if customer_name and not client.full_name:
        client.full_name = customer_name
        client.save(update_fields=['full_name'])

    if assign_to == 'self':
        active_count = Order.objects.filter(driver=driver, status__in=Order.ACTIVE_STATUSES).count()
        if active_count >= Order.MAX_ACTIVE_PER_DRIVER:
            return Response({
                'detail': f"Bir vaqtda ko'pi bilan {Order.MAX_ACTIVE_PER_DRIVER} ta faol buyurtma olish mumkin.",
            }, status=400)
        commission = tariff.commission
        if driver.balance < commission:
            return Response({'detail': f'Balans yetarli emas. Komissiya: {commission} UZS'}, status=400)
        order = Order.objects.create(
            client=client, driver=driver, from_address=from_address, from_lat=from_lat, from_lng=from_lng,
            to_address=to_address, payment_type=Order.PAYMENT_CASH, car_type=driver.car_type,
            commission=commission, status='accepted', created_by_driver=driver,
        )
        driver.balance -= Decimal(str(commission))
        driver.save(update_fields=['balance'])
        _log_activity(driver, DriverActivityLog.ACTION_ORDER, f"Ilova orqali buyurtma #{order.id} yaratdi va o'zi qabul qildi", request)
        tg_order_accepted(order, driver)
        tg_low_balance_alert(driver)
        return Response(DriverAppOrderSerializer(order, context={'driver': driver}).data, status=201)

    order = Order.objects.create(
        client=client, from_address=from_address, from_lat=from_lat, from_lng=from_lng, to_address=to_address,
        payment_type=Order.PAYMENT_CASH, car_type=driver.car_type, commission=tariff.commission,
        status='pending', created_by_driver=driver,
    )
    _log_activity(driver, DriverActivityLog.ACTION_ORDER, f"Ilova orqali buyurtma #{order.id} yaratdi — ochiq", request)
    tg_new_order(order)
    if saved_address and from_lat and from_lng:
        dispatch_order(order)
    return Response(DriverAppOrderSerializer(order, context={'driver': driver}).data, status=201)
