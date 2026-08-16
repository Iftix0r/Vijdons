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
    # Qaysi qurilmadan kirganini serverda saqlab qo'yamiz — operator paneli
    # (haydovchi tafsiloti) shundan ko'rsatadi. Har kirishda yangilanadi,
    # shu sabab qurilma almashtirilsa ham holat doim yangi.
    device_model = str(request.data.get('device_model', '')).strip()[:120]
    if device_model and device_model != driver.device_model:
        driver.device_model = device_model
        driver.save(update_fields=['device_model'])
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
    # Batareya foizi — ixtiyoriy, ilova joylashuv yuborgan har safar birga
    # keladi (real qurilma holatini kuzatib turish uchun, operator panelida
    # ko'rsatiladi — masalan batareyasi kamayib qolgan haydovchini bilish).
    battery = request.data.get('battery')
    if battery is not None:
        try:
            battery_int = max(0, min(100, int(battery)))
            driver.battery_level = battery_int
            update_fields.append('battery_level')
        except (TypeError, ValueError):
            pass
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
            # Shaxsan shu haydovchiga yuborilgan (dispatched_to) buyurtma —
            # yo'nalish filtridan qat'i nazar HAR DOIM ko'rinishi kerak.
            # Aks holda operator/tizim aynan unga yo'llagan buyurtma
            # "yo'nalish rejimi" tufayli sezilmasdan yashirinib, haydovchi
            # hech qachon ko'rmasdan "javob bermadi" bo'lib qolardi —
            # shaxsiy tayinlash umumiy filtrlardan ustun turishi kerak.
            if o.dispatched_to_id == driver.id:
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
    from .utils import _resolve_dispatch_attempt, dispatch_order, tg_order_rejected
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
                # Diqqat: avval bu yerda haydovchi rad etganda manzil
                # navbatining OXIRIGA tushirilardi (endi javobsizlik/timeout
                # holatida ham xuddi shunday tushirilmaydi — utils.py
                # auto_reject_timeout()ga qarang). Endi "Rad etish" (yoki
                # javob bermaslik) navbat o'rniga umuman TA'SIR qilmaydi —
                # haydovchi navbatdagi o'rnini FAQAT oflaynga chiqqanda yoki
                # biror buyurtmani qabul qilganda yo'qotadi.
    if should_redispatch:
        tg_order_rejected(locked, driver)
        dispatch_order(locked)
    return Response({'detail': 'Rad etildi.'})


@api_view(['POST'])
@driver_required
def order_accept(request, driver, pk):
    from django.utils import timezone
    from .models import DispatchAttempt, AddressQueueEntry
    from .utils import (
        _resolve_dispatch_attempt, tg_order_accepted, tg_low_balance_alert, sms_order_status,
        order_credit_accept_allowed, mark_driver_debt_from_order,
    )

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
        # Diqqat: balans yetarli bo'lmasa ham, buyurtma UZOQ VAQT (2 daqiqa)
        # hech kim tomonidan qabul qilinmay kutib qolgan bo'lsa — QARZGA
        # ham bo'lsa qabul qilishga ruxsat beriladi (mijoz butunlay
        # xizmatsiz qolib ketmasin deb). `on_credit` — pastda balans manfiy
        # bo'lib qolganini "Qarzdorlar" ro'yxatiga avtomatik belgilash uchun.
        on_credit = driver.balance < commission
        if on_credit and not order_credit_accept_allowed(locked):
            return Response({'detail': f'Balans yetarli emas. Komissiya: {commission} UZS'}, status=400)
        driver.balance -= Decimal(str(commission))
        driver.save(update_fields=['balance'])
        if on_credit:
            mark_driver_debt_from_order(driver, locked, commission)
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
    from .utils import (
        tg_order_on_way, tg_order_arrived, tg_order_completed, tg_order_cancelled,
        sms_order_status, haversine, capture_order_action_location,
    )

    order = get_object_or_404(Order, pk=pk)
    if order.driver_id != driver.id:
        return Response({'detail': 'Bu buyurtma sizga tegishli emas.'}, status=403)
    if order.status not in allowed_statuses:
        return Response({'detail': f"'{order.get_status_display()}' holatida bu amal mumkin emas."}, status=400)

    original_status = order.status
    order.status = new_status
    update_fields = ['status', 'updated_at']
    update_fields += capture_order_action_location(
        order, new_status, original_status, request.data.get('lat'), request.data.get('lng'),
    )

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
        from .utils import reward_driver_rating_on_completion
        reward_driver_rating_on_completion(driver)

        # Buyurtma yakunlangach, haydovchi darhol o'z manzili navbatiga
        # qayta qo'shilishi kerak (masalan safar aynan o'sha stoyanka
        # yonida tugagan bo'lsa). Avval bu FAQAT keyingi mustaqil GPS
        # ping'ini (fon xizmati, harakat/vaqt chegarasiga qarab bir necha
        # daqiqagacha kechikishi mumkin) kutardi — haydovchi "men shu
        # yerdaman, nega navbatda emasman" deb shikoyat qilgan edi. Endi
        # shu so'rov bilan birga kelgan koordinata bo'lsa, darhol
        # qayta baholanadi.
        lat, lng = request.data.get('lat'), request.data.get('lng')
        if lat is not None and lng is not None:
            try:
                lat, lng = float(lat), float(lng)
                from django.utils import timezone as _tz
                import datetime
                from .utils import update_address_queue_membership, ADDRESS_QUEUE_STALE_MINUTES
                stale_cutoff = _tz.now() - datetime.timedelta(minutes=ADDRESS_QUEUE_STALE_MINUTES)
                was_stale = not driver.last_seen or driver.last_seen < stale_cutoff
                update_address_queue_membership(driver, lat, lng, was_stale=was_stale)
                Driver.objects.filter(pk=driver.pk).update(last_seen=_tz.now())
            except (TypeError, ValueError):
                pass

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


# ── Tarix / Reyting ────────────────────────────────────────────────────────────

@api_view(['GET'])
@driver_required
def order_history(request, driver):
    from django.db.models import Sum, Count, Q as DQ
    from django.utils import timezone
    import datetime

    period = request.query_params.get('period', 'all')
    qs = Order.objects.filter(driver=driver)
    now = timezone.now()
    if period == 'today':
        qs = qs.filter(created_at__date=now.date())
    elif period == 'week':
        qs = qs.filter(created_at__gte=now - datetime.timedelta(days=7))
    elif period == 'month':
        qs = qs.filter(created_at__gte=now - datetime.timedelta(days=30))

    orders = qs.select_related('client', 'driver').order_by('-created_at')[:100]
    stats = qs.aggregate(
        total_earned=Sum('price', filter=DQ(status='completed')),
        completed=Count('id', filter=DQ(status='completed')),
    )
    return Response({
        'orders': DriverAppOrderSerializer(orders, many=True, context={'driver': driver}).data,
        'total_earned': stats['total_earned'] or 0,
        'completed': stats['completed'] or 0,
    })


@api_view(['GET'])
@driver_required
def rating(request, driver):
    from django.db.models import Count, Sum, Q as DQ
    from django.utils import timezone

    today = timezone.localdate()
    month_start = today.replace(day=1)
    leaderboard = list(
        Driver.objects.filter(is_active=True)
        .annotate(
            completed=Count('orders', filter=DQ(
                orders__status='completed', orders__created_at__date__gte=month_start, orders__created_at__date__lte=today,
            )),
            earned=Sum('orders__price', filter=DQ(
                orders__status='completed', orders__created_at__date__gte=month_start, orders__created_at__date__lte=today,
            )),
        )
        .order_by('-completed', '-earned', 'full_name')
    )
    rows = []
    my_row = None
    for i, d in enumerate(leaderboard, start=1):
        row = {'rank': i, 'full_name': d.full_name, 'completed': d.completed, 'earned': int(d.earned or 0), 'is_me': d.id == driver.id}
        rows.append(row)
        if row['is_me']:
            my_row = row
    gap_to_next = None
    if my_row and my_row['rank'] > 1:
        ahead_row = rows[my_row['rank'] - 2]
        gap_to_next = max(1, ahead_row['completed'] - my_row['completed'] + 1)
    return Response({'rows': rows, 'my_row': my_row, 'gap_to_next': gap_to_next})


# ── Profil ──────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@driver_required
def profile_photo(request, driver):
    photo = request.FILES.get('photo')
    if not photo:
        return Response({'detail': 'Rasm tanlanmadi.'}, status=400)
    if driver.photo:
        driver.photo.delete(save=False)
    driver.photo = photo
    driver.save(update_fields=['photo'])
    return Response({'photo_url': request.build_absolute_uri(driver.photo.url)})


@api_view(['POST'])
@driver_required
def profile_password(request, driver):
    old = str(request.data.get('old_password', ''))
    new = str(request.data.get('new_password', ''))
    if not driver.user:
        return Response({'detail': 'Foydalanuvchi topilmadi.'}, status=400)
    if not driver.user.check_password(old):
        return Response({'detail': "Eski parol noto'g'ri."}, status=400)
    if len(new) < 6:
        return Response({'detail': "Parol kamida 6 ta belgi bo'lishi kerak."}, status=400)
    driver.user.set_password(new)
    driver.user.save()
    return Response({'detail': 'Parol yangilandi.'})


# ── Balans ──────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@driver_required
def balance_history(request, driver):
    from .models import BalanceLog

    logs = driver.balance_logs.all()[:100]
    entries = [{
        'is_income': log.action == BalanceLog.ACTION_ADD,
        'amount': str(log.amount),
        'note': log.note or ("Balans to'ldirildi" if log.action == BalanceLog.ACTION_ADD else 'Balansdan yechildi'),
        'created_at': log.created_at.isoformat(),
    } for log in logs]

    commission_orders = Order.objects.filter(
        driver=driver, status__in=Order.ACTIVE_STATUSES + ('completed',)
    ).order_by('-updated_at')[:100]
    entries += [{
        'is_income': False,
        'amount': str(o.commission),
        'note': f"Komissiya — buyurtma #{o.id}",
        'created_at': o.updated_at.isoformat(),
    } for o in commission_orders]

    entries.sort(key=lambda e: e['created_at'], reverse=True)
    return Response({'entries': entries[:100], 'balance': str(driver.balance)})


@api_view(['POST'])
@driver_required
def balance_topup(request, driver):
    from decimal import InvalidOperation
    from .models import BalanceTopupRequest
    from .utils import tg_topup_request

    receipt = request.FILES.get('receipt')
    amount_raw = str(request.data.get('amount', '')).strip()
    if not receipt:
        return Response({'detail': 'Chek rasmi tanlanmadi.'}, status=400)
    try:
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        return Response({'detail': "Summani to'g'ri kiriting."}, status=400)

    topup = BalanceTopupRequest.objects.create(driver=driver, amount=amount, receipt=receipt)
    tg_topup_request(topup, request.build_absolute_uri(topup.receipt.url))
    return Response({'detail': "So'rov yuborildi. Admin tasdiqlashini kuting."}, status=201)


# ── Shartnoma ───────────────────────────────────────────────────────────────────

@api_view(['GET'])
@driver_required
def contract_detail(request, driver):
    from .models import ContractSettings

    contract = ContractSettings.get()
    signed = driver.contract_signatures.filter(version=contract.version).exists()
    return Response({'title': contract.title, 'content': contract.content, 'version': contract.version, 'signed': signed})


@api_view(['POST'])
@driver_required
def contract_sign(request, driver):
    from .models import ContractSettings, DriverContractSignature

    contract = ContractSettings.get()
    if driver.contract_signatures.filter(version=contract.version).exists():
        return Response({'detail': 'Siz bu versiyani allaqachon imzolagansiz.'}, status=400)
    signature_file = request.FILES.get('signature')
    if not signature_file:
        return Response({'detail': 'Imzo chizilmagan.'}, status=400)
    if str(request.data.get('agree')) != '1':
        return Response({'detail': 'Shartlarga rozilik belgilanmagan.'}, status=400)

    DriverContractSignature.objects.create(
        driver=driver, version=contract.version, full_name=driver.full_name,
        signature=signature_file, ip_address=_get_ip(request),
    )
    return Response({'detail': 'Shartnoma imzolandi.'}, status=201)


# ── Manzil navbati ────────────────────────────────────────────────────────────

@api_view(['GET'])
@driver_required
def addresses_list(request, driver):
    from django.db.models import Count, Q as DQ
    from django.utils import timezone
    from .models import SavedAddress
    from .utils import find_matching_saved_address

    today = timezone.localdate()
    today_orders = Order.objects.filter(
        created_at__date=today, from_lat__isnull=False, from_lng__isnull=False,
    ).exclude(status='cancelled').values_list('from_lat', 'from_lng')
    # Bir marta olib, tsikl ichida qayta-qayta DB'ga so'rov yubormaymiz.
    all_saved_addresses = list(SavedAddress.objects.all())
    counts = {}
    for lat, lng in today_orders:
        addr = find_matching_saved_address(lat, lng, addresses=all_saved_addresses)
        if addr:
            counts[addr.id] = counts.get(addr.id, 0) + 1

    online_cutoff = timezone.now() - timezone.timedelta(seconds=120)
    addresses = SavedAddress.objects.select_related('district', 'district__region').annotate(
        queue_count=Count('queue_entries', filter=DQ(
            queue_entries__left_at__isnull=True, queue_entries__driver__is_active=True,
            queue_entries__driver__is_on_duty=True, queue_entries__driver__approval_status='approved',
            queue_entries__driver__last_seen__gte=online_cutoff,
        )),
    )

    # Haydovchi ilovasidagi qidiruv/hudud filtri — ATAYIN ixtiyoriy, hech
    # narsa berilmasa avvalgidek TO'LIQ ro'yxat qaytadi (masofa bo'yicha
    # saralash ekranning o'zida bo'ladi). O'zbekiston bo'ylab manzillar
    # ko'payishi bilan haydovchi "boshqa hududda talab bormi" deb qarab
    # chiqishi uchun.
    region_id = request.query_params.get('region', '').strip()
    district_id = request.query_params.get('district', '').strip()
    q = request.query_params.get('q', '').strip()
    if district_id:
        addresses = addresses.filter(district_id=district_id)
    elif region_id:
        addresses = addresses.filter(district__region_id=region_id)
    if q:
        addresses = addresses.filter(DQ(name__icontains=q) | DQ(address__icontains=q))

    return Response([
        {
            'id': a.id, 'name': a.name, 'address': a.address, 'lat': a.lat, 'lng': a.lng,
            'today_orders': counts.get(a.id, 0), 'queue_count': a.queue_count,
            'district_id': a.district_id, 'district_name': a.district.name if a.district else None,
            'region_id': a.district.region_id if a.district else None,
            'region_name': a.district.region.name if a.district else None,
        }
        for a in addresses
    ])


@api_view(['GET'])
@driver_required
def regions_list(request, driver):
    """Viloyat→tuman ro'yxati — haydovchi ilovasidagi manzil qidiruv/filtr
    oynasida ishlatiladi (taxi/views.py'dagi operator panel bilan bir xil
    ma'lumot, faqat token-autentifikatsiyali JSON ko'rinishida)."""
    from .models import Region

    regions = Region.objects.prefetch_related('districts').all()
    return Response([
        {
            'id': r.id, 'name': r.name,
            'districts': [{'id': d.id, 'name': d.name} for d in r.districts.all()],
        }
        for r in regions
    ])


@api_view(['GET'])
@driver_required
def current_area(request, driver):
    """Haydovchi ilovasidagi "Manzillar" ekrani ochilganda — GPS
    koordinatasi bo'yicha qaysi viloyat/tumanda ekanini aniqlab, filtrni
    shu bo'yicha oldindan tanlash uchun. Avtomatik manzil yaratishda
    ishlatiladigan bilan bir xil reverse-geocode mexanizmi, lekin bu yerda
    YANGI District YARATILMAYDI — faqat mavjudi topiladi (topilmasa
    district_id null, region_id esa bo'lishi mumkin)."""
    from .utils import reverse_geocode_admin_area, _match_region
    from .models import District

    try:
        lat = float(request.query_params.get('lat'))
        lng = float(request.query_params.get('lng'))
    except (TypeError, ValueError):
        return Response({'region_id': None, 'district_id': None})

    region_name, district_name = reverse_geocode_admin_area(lat, lng)
    region = _match_region(region_name)
    if not region:
        return Response({'region_id': None, 'district_id': None})
    district = None
    if district_name:
        district = District.objects.filter(region=region, name__iexact=district_name.strip()).first()
    return Response({'region_id': region.id, 'district_id': district.id if district else None})


@api_view(['GET'])
@driver_required
def address_queue_position(request, driver, pk):
    from django.utils import timezone
    import datetime
    from .models import AddressQueueEntry
    from .utils import update_address_queue_membership, ADDRESS_QUEUE_STALE_MINUTES

    lat = request.query_params.get('lat')
    lng = request.query_params.get('lng')
    if lat and lng:
        try:
            stale_cutoff = timezone.now() - datetime.timedelta(minutes=ADDRESS_QUEUE_STALE_MINUTES)
            was_stale = not driver.last_seen or driver.last_seen < stale_cutoff
            update_address_queue_membership(driver, float(lat), float(lng), was_stale=was_stale)
            Driver.objects.filter(pk=driver.pk).update(last_seen=timezone.now())
        except (TypeError, ValueError):
            pass

    online_cutoff = timezone.now() - datetime.timedelta(seconds=120)
    queue_ids = list(
        AddressQueueEntry.objects.filter(
            address_id=pk, left_at__isnull=True, driver__is_active=True, driver__is_on_duty=True,
            driver__approval_status='approved', driver__last_seen__gte=online_cutoff,
        ).order_by('joined_at').values_list('driver_id', flat=True)
    )
    position = queue_ids.index(driver.id) + 1 if driver.id in queue_ids else None
    return Response({'position': position, 'total': len(queue_ids)})


@api_view(['GET'])
@driver_required
def address_queue_drivers(request, driver, pk):
    from django.utils import timezone
    from .models import AddressQueueEntry, SavedAddress

    address = get_object_or_404(SavedAddress, pk=pk)
    online_cutoff = timezone.now() - timezone.timedelta(seconds=120)
    entries = (
        AddressQueueEntry.objects.filter(
            address=address, left_at__isnull=True, driver__is_active=True, driver__is_on_duty=True,
            driver__approval_status='approved', driver__last_seen__gte=online_cutoff,
        ).select_related('driver').order_by('joined_at')
    )
    return Response([
        {
            'position': i + 1, 'full_name': e.driver.full_name, 'car_model': e.driver.car_model,
            'car_number': e.driver.car_number, 'joined_at': timezone.localtime(e.joined_at).strftime('%H:%M'),
            'is_me': e.driver_id == driver.id,
            'photo_url': request.build_absolute_uri(e.driver.photo.url) if e.driver.photo else None,
        }
        for i, e in enumerate(entries)
    ])


# ── Yo'nalish rejimi / SOS / Surge / Yaqin haydovchilar ────────────────────────

@api_view(['POST'])
@driver_required
def destination_set(request, driver):
    if str(request.data.get('clear')) in ('1', 'true', 'True'):
        driver.destination_mode = False
        driver.destination_lat = None
        driver.destination_lng = None
        driver.destination_address = ''
        driver.save(update_fields=['destination_mode', 'destination_lat', 'destination_lng', 'destination_address'])
        return Response({'active': False})

    lat = request.data.get('lat')
    lng = request.data.get('lng')
    address = str(request.data.get('address', '')).strip()
    if lat is None or lng is None:
        return Response({'detail': "Koordinata kerak."}, status=400)
    try:
        driver.destination_lat = float(lat)
        driver.destination_lng = float(lng)
    except (TypeError, ValueError):
        return Response({'detail': "Koordinata noto'g'ri."}, status=400)
    driver.destination_mode = True
    driver.destination_address = address
    driver.save(update_fields=['destination_mode', 'destination_lat', 'destination_lng', 'destination_address'])
    return Response({'active': True})


@api_view(['POST'])
@driver_required
def sos_send(request, driver):
    from .models import SosAlert
    from .utils import tg_sos_alert

    lat = request.data.get('lat')
    lng = request.data.get('lng')
    try:
        lat_f = float(lat) if lat is not None else None
        lng_f = float(lng) if lng is not None else None
    except (TypeError, ValueError):
        return Response({'detail': "Koordinata noto'g'ri."}, status=400)

    alert = SosAlert.objects.create(
        driver=driver, latitude=lat_f, longitude=lng_f,
        address=str(request.data.get('address', '')).strip(),
        note=str(request.data.get('note', '')).strip(),
    )
    tg_sos_alert(alert)
    return Response({'id': alert.id}, status=201)


@api_view(['GET'])
@driver_required
def surge_info(request, driver):
    from .utils import get_surge_multiplier

    multiplier, reason = get_surge_multiplier()
    return Response({'multiplier': multiplier, 'reason': reason})


@api_view(['GET'])
@driver_required
def nearby_drivers(request, driver):
    from django.utils import timezone

    online_cutoff = timezone.now() - timezone.timedelta(seconds=120)
    peers = Driver.objects.filter(
        is_on_duty=True, is_active=True, approval_status=Driver.APPROVAL_APPROVED,
        latitude__isnull=False, longitude__isnull=False, last_seen__gte=online_cutoff,
    ).exclude(pk=driver.pk)
    return Response([
        {
            'id': d.id, 'full_name': d.full_name, 'car_type': d.car_type, 'car_model': d.car_model,
            'car_number': d.car_number, 'photo_url': (d.photo.url if d.photo else ''),
            'latitude': d.latitude, 'longitude': d.longitude, 'trips_count': d.trips_count,
            'rating': float(d.rating), 'level': d.level,
        }
        for d in peers
    ])


@api_view(['GET'])
@driver_required
def driver_sounds(request, driver):
    """Veb haydovchi panelidagi bilan bir xil, operator sozlagan (yoki
    standart) ovoz fayllari — `taxi/context_processors.py`dagi
    `driver_sounds` bilan bir xil mantiq, faqat native ilova uchun JSON
    ko'rinishida. `PanelSound.resolve_url()` NISBIY (masalan `/media/...`)
    yo'l qaytaradi — native ilova bevosita ishlata olishi uchun bu yerda
    `request.build_absolute_uri()` bilan TO'LIQ URL'ga aylantiriladi."""
    from .models import PanelSound
    from .constants import DRIVER_SOUND_EVENTS

    sounds = PanelSound.get_map()
    data = {}
    for key, _label in DRIVER_SOUND_EVENTS:
        snd = sounds.get(key)
        enabled = snd.enabled if snd else True
        url = snd.resolve_url() if snd else None
        data[key] = {
            'enabled': enabled,
            'url': request.build_absolute_uri(url) if url else None,
        }
    return Response(data)


# ── Operator chati ────────────────────────────────────────────────────────────
# Haydovchi bilan operator o'rtasidagi XUSUSIY (faqat ikkalasi ko'radigan)
# suhbat — boshqa haydovchilar bu xabarlarni ko'rmaydi. Operator tarafi
# `taxi/views.py`dagi `operator_chat` panelida (`ChatMessage` modeli, xuddi
# eski Flutter ilovasi `api_views.py: chat_messages/chat_send` bilan bir xil
# model/mantiq) — shu sabab operator panelida hech narsa o'zgartirishga hojat
# yo'q, faqat shu modelni token-autentifikatsiya bilan native ilovaga ochamiz.
# Audio xabar bu yerda YO'Q — native ilovaning birinchi versiyasi faqat
# matnli xabar bilan cheklangan.

def _chat_message_dict(msg):
    return {
        'id': msg.id,
        'sender': msg.sender,
        'text': msg.text,
        'is_read': msg.is_read,
        'created_at': msg.created_at.isoformat(),
    }


@api_view(['GET'])
@driver_required
def chat_private_list(request, driver):
    from .models import ChatMessage

    ChatMessage.objects.filter(driver=driver, sender=ChatMessage.SENDER_OPERATOR, is_read=False).update(is_read=True)
    # Diqqat: avval `created_at` bo'yicha O'SUVCHI tartibda kesilgan edi —
    # bu suhbat 100 tadan oshgach doim ENG ESKI 100 tani qaytarardi (yangi
    # xabarlar hech qachon ko'rinmasdi). Endi ENG SO'NGGI 100 ta olinadi,
    # keyin ekranda eskisi tepada bo'lishi uchun xronologik tartibga
    # qaytariladi.
    msgs = reversed(ChatMessage.objects.filter(driver=driver).order_by('-created_at')[:100])
    return Response([_chat_message_dict(m) for m in msgs])


def _run_ai_chat_reply(driver_id):
    """Fon oqimida (`_schedule_reverse_geocode`, utils.py bilan bir xil
    naqsh) AI javobini so'raydi va yozadi — haydovchining "xabar yuborish"
    so'rovini AI javobini kutib sekinlatmasin uchun."""
    import threading

    def _run():
        from django.utils import timezone
        from .models import ChatMessage, Driver
        from .utils import generate_ai_chat_reply, ai_toggle_duty, ai_today_stats, ai_escalate_to_operator

        try:
            driver = Driver.objects.get(pk=driver_id)
        except Driver.DoesNotExist:
            return

        # Chat ekranining tepasida "AI yozmoqda..." ko'rsatilishi uchun —
        # aniq boshlanish/tugash (freshness-timeout emas), `chat_typing_status`
        # shu maydonni o'qiydi. `finally` bilan — xato chiqsa ham "abadiy
        # yozmoqda" bo'lib qolib ketmasin.
        Driver.objects.filter(pk=driver.pk).update(ai_typing_at=timezone.now())
        try:
            # Oxirgi 20 ta xabar — AI va operator ikkalasi ham "assistant"
            # tomon sifatida beriladi (AI oldingi operator javobidan xabardor
            # bo'lsin, takrorlab/qarama-qarshi gapirmasin).
            recent = list(ChatMessage.objects.filter(driver=driver).order_by('-created_at')[:20])
            history = [
                {'role': 'user' if m.sender == ChatMessage.SENDER_DRIVER else 'assistant', 'content': m.text}
                for m in reversed(recent) if m.text
            ]
            reply_text, tool_name, tool_args = generate_ai_chat_reply(driver, history)
            result_text = None
            if tool_name == 'cancel_active_order':
                from .views import ai_cancel_active_order
                _ok, result_text = ai_cancel_active_order(driver)
            elif tool_name == 'toggle_duty_status':
                _ok, result_text = ai_toggle_duty(driver)
            elif tool_name == 'get_today_stats':
                _ok, result_text = ai_today_stats(driver)
            elif tool_name == 'escalate_to_operator':
                _ok, result_text = ai_escalate_to_operator(driver, (tool_args or {}).get('reason', ''))

            if result_text:
                ChatMessage.objects.create(driver=driver, sender=ChatMessage.SENDER_AI, text=result_text)
            elif reply_text:
                ChatMessage.objects.create(driver=driver, sender=ChatMessage.SENDER_AI, text=reply_text)
        finally:
            Driver.objects.filter(pk=driver.pk).update(ai_typing_at=None)

    threading.Thread(target=_run, daemon=True).start()


@api_view(['POST'])
@driver_required
def chat_private_send(request, driver):
    from .models import ChatMessage
    from .utils import send_telegram

    text = str(request.data.get('text', '')).strip()
    if not text:
        return Response({'detail': "Xabar matni bo'sh bo'lishi mumkin emas."}, status=400)
    msg = ChatMessage.objects.create(driver=driver, sender=ChatMessage.SENDER_DRIVER, text=text)
    send_telegram(f"💬 <b>{driver.full_name}</b> ({driver.car_number}):\n{text}")
    _run_ai_chat_reply(driver.id)
    return Response(_chat_message_dict(msg), status=201)


@api_view(['GET'])
@driver_required
def chat_private_unread(request, driver):
    from .models import ChatMessage

    count = ChatMessage.objects.filter(driver=driver, sender=ChatMessage.SENDER_OPERATOR, is_read=False).count()
    return Response({'count': count})


# Operator "yozmoqda" belgisi hech qachon tozalanmaydi (`operator_typing_at`
# faqat operator klaviaturada bosganda YANGILANADI — pastdagi kabi), shu
# sabab "hozir yozayaptimi" degan xulosa faqat YAQINDAGI (bir necha soniya
# ichidagi) yozuv bo'lsagina chiqariladi — aks holda operator BIR MARTA
# yozgan bo'lsa ham, u "abadiy yozmoqda" bo'lib qolib ketardi.
CHAT_TYPING_FRESHNESS_SECONDS = 6


@api_view(['GET'])
@driver_required
def chat_typing_status(request, driver):
    """Chat ekranining tepasida (Telegram'dagi kabi) "Operator yozmoqda..."/
    "AI yozmoqda..." animatsiyasi uchun — kim (agar bo'lsa) hozir javob
    tayyorlayotganini qaytaradi."""
    from django.utils import timezone
    import datetime

    cutoff = timezone.now() - datetime.timedelta(seconds=CHAT_TYPING_FRESHNESS_SECONDS)
    if driver.ai_typing_at and driver.ai_typing_at >= cutoff:
        typing = 'ai'
    elif driver.operator_typing_at and driver.operator_typing_at >= cutoff:
        typing = 'operator'
    else:
        typing = None
    return Response({'typing': typing})


# ── Musiqa ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@driver_required
def music_tracks(request, driver):
    """Haydovchi ilovasidagi "Musiqa" bo'limi (Asosiy'dan o'ngga surilganda
    ochiladigan pleylist) — operator panelida qo'shilgan (`taxi/views.py:
    music_list`) faol qo'shiqlar ro'yxati."""
    from .models import MusicTrack

    tracks = MusicTrack.objects.filter(is_active=True)
    data = []
    for t in tracks:
        url = t.resolve_url()
        if not url:
            continue
        data.append({
            'id': t.id,
            'title': t.title,
            'artist': t.artist,
            'url': request.build_absolute_uri(url) if url.startswith('/') else url,
        })
    return Response(data)
