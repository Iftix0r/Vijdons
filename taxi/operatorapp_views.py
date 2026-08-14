"""
REST API — native Android operator ilovasi uchun.
URL prefix: /api/operatorapp/  (config/urls.py, `/panel/` prefiksisiz — xuddi
`taxi/driverapp_urls.py` bilan bir xil sabab bilan: Cloudflare WAF qoidasida
shu aniq prefiksni istisno qilish oson bo'lishi uchun).

Auth: DRF TokenAuthentication (`Authorization: Token <key>`). Operatorlar
alohida profil modeliga ega emas — oddiy `django.contrib.auth.User`
(`is_staff=True`), xuddi `/panel/` veb-interfeysida ishlatilgani kabi
(`taxi/views.py: panel_login_required`). Og'ir/pul bilan bog'liq mantiq
(komissiya qaytarish, dispetcherlash) qayta yozilmaydi — `taxi/utils.py` va
`taxi/views.py`dagi sinovdan o'tgan funksiyalar to'g'ridan-to'g'ri chaqiriladi.
"""
from functools import wraps

from django.contrib.auth import authenticate
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import (
    Driver, Order, Client, TariffSettings, BalanceLog, BalanceTopupRequest,
    ChatMessage, GroupMessage, OperatorPushToken,
)
from .operatorapp_serializers import OperatorAppDriverSerializer, OperatorAppOrderSerializer

ONLINE_THRESHOLD_SECONDS = 120     # taxi/views.py bilan bir xil qiymat (dublikat — bu yerda faqat oddiy sonlar, mantiq emas)
PENDING_ORDER_AGING_SECONDS = 120
TOPUP_AGING_HOURS = 3


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _operator_dict(user):
    return {
        'id': user.id,
        'username': user.username,
        'full_name': user.get_full_name() or user.username,
        'is_superuser': user.is_superuser,
    }


# ── Auth ──────────────────────────────────────────────────────────────────────

def operator_required(fn):
    """Faqat is_staff foydalanuvchi kirishi mumkin — `taxi/views.py:
    panel_login_required` bilan bir xil huquq tekshiruvi, faqat sessiya
    o'rniga token orqali. Resolve qilingan `User`ni view'ga uzatadi
    (`driverapp_views.driver_required`dagi kabi)."""
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'detail': 'Ruxsat yoq.', 'code': 'not_staff'}, status=403)
        return fn(request, request.user, *args, **kwargs)
    return wrapper


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    from .utils import log_system_event

    username = str(request.data.get('username', '')).strip()
    password = str(request.data.get('password', ''))
    if not username or not password:
        return Response({'detail': 'Login va parol kiritilishi shart.'}, status=400)
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_staff:
        log_system_event('operatorapp_login_failed', f"Operator ilova: '{username}' bilan kirish urinishi muvaffaqiyatsiz", level='warning', request=request)
        return Response({'detail': "Login yoki parol noto'g'ri."}, status=401)
    token, _ = Token.objects.get_or_create(user=user)
    log_system_event('operatorapp_login_success', f"Operator ilova: '{username}' kirdi", request=request, user=user)
    return Response({'token': token.key, 'operator': _operator_dict(user)})


@api_view(['GET'])
@operator_required
def me(request, user):
    return Response(_operator_dict(user))


@api_view(['POST'])
@operator_required
def fcm_sync(request, user):
    token = str(request.data.get('fcm_token', '')).strip()
    if not token:
        return Response({'detail': 'fcm_token kiritilishi shart.'}, status=400)
    OperatorPushToken.objects.get_or_create(user=user, fcm_token=token)
    return Response({'detail': 'FCM token yangilandi.'})


# ── Dashboard ────────────────────────────────────────────────────────────────

@api_view(['GET'])
@operator_required
def dashboard(request, user):
    from datetime import timedelta
    from django.db.models import Sum
    from django.utils import timezone

    today = timezone.now().date()
    aging_cutoff = timezone.now() - timedelta(seconds=PENDING_ORDER_AGING_SECONDS)
    topup_aging_cutoff = timezone.now() - timedelta(hours=TOPUP_AGING_HOURS)
    online_cutoff = timezone.now() - timedelta(seconds=ONLINE_THRESHOLD_SECONDS)
    today_qs = Order.objects.filter(created_at__date=today)
    tariff = TariffSettings.get()

    return Response({
        'today_orders': today_qs.count(),
        'today_revenue': str(today_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'aging_orders': Order.objects.filter(status='pending', created_at__lte=aging_cutoff).count(),
        'on_duty_drivers': Driver.objects.filter(is_active=True, is_on_duty=True, approval_status=Driver.APPROVAL_APPROVED).count(),
        'online_drivers': Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED, last_seen__gte=online_cutoff).count(),
        'pending_driver_approvals': Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).count(),
        'low_balance_drivers': Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED, balance__lt=tariff.commission).count(),
        'pending_topups': BalanceTopupRequest.objects.filter(status=BalanceTopupRequest.STATUS_PENDING).count(),
        'aging_topups': BalanceTopupRequest.objects.filter(status=BalanceTopupRequest.STATUS_PENDING, created_at__lte=topup_aging_cutoff).count(),
    })


# ── Buyurtmalar ──────────────────────────────────────────────────────────────

def _order_qs():
    return Order.objects.select_related('client', 'driver', 'dispatched_to').prefetch_related('rejected_by', 'dispatch_attempts__driver')


@api_view(['GET'])
@operator_required
def order_list(request, user):
    from django.core.paginator import Paginator

    qs = _order_qs()
    q = request.query_params.get('q', '').strip()
    status_filter = request.query_params.get('status', '')
    if q:
        qs = qs.filter(
            Q(client__full_name__icontains=q) | Q(client__phone_number__icontains=q) |
            Q(from_address__icontains=q) | Q(to_address__icontains=q) | Q(driver__full_name__icontains=q)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    qs = qs.order_by('-created_at')

    page = Paginator(qs, 40).get_page(request.query_params.get('page'))
    return Response({
        'orders': OperatorAppOrderSerializer(page.object_list, many=True, context={'request': request}).data,
        'page': page.number,
        'has_next': page.has_next(),
        'total_count': page.paginator.count,
    })


@api_view(['GET'])
@operator_required
def order_detail(request, user, pk):
    order = get_object_or_404(_order_qs(), pk=pk)
    return Response(OperatorAppOrderSerializer(order, context={'request': request}).data)


@api_view(['POST'])
@operator_required
def order_create(request, user):
    from .utils import (
        haversine, dispatch_order, tg_new_order, notify_driver_new_order,
        start_dispatch_timeout, _log_dispatch_attempt, log_system_event,
    )

    phone_number = str(request.data.get('phone_number', '')).strip()
    customer_name = str(request.data.get('customer_name', '')).strip()
    from_address = str(request.data.get('from_address', '')).strip()
    to_address = str(request.data.get('to_address', '')).strip()
    driver_id = request.data.get('driver_id') or None

    if not phone_number or not from_address:
        return Response({'detail': 'Mijoz raqami va manzil kiritilishi shart.'}, status=400)

    tariff = TariffSettings.get()
    client, _created = Client.objects.get_or_create(phone_number=phone_number)
    if client.is_blocked:
        return Response({'detail': 'Bu mijoz bloklangan.'}, status=400)
    if customer_name and not client.full_name:
        client.full_name = customer_name
        client.save(update_fields=['full_name'])

    driver = Driver.objects.filter(pk=driver_id).first() if driver_id else None

    def _coord(key):
        v = request.data.get(key)
        try:
            return float(v) if v not in (None, '') else None
        except (TypeError, ValueError):
            return None

    f_lat, f_lng = _coord('from_lat'), _coord('from_lng')
    t_lat, t_lng = _coord('to_lat'), _coord('to_lng')
    is_delivery = bool(request.data.get('is_delivery'))

    distance_km = None
    price = None
    if f_lat and f_lng and t_lat and t_lng:
        distance_km = haversine(f_lat, f_lng, t_lat, t_lng)
        if distance_km:
            price = tariff.calc_price(distance_km)

    # Yetkazib berish (dastavka) — narx kamida 10 000 so'm, komissiya qat'iy
    # 3000 so'm — xuddi taxi/views.py:order_create bilan bir xil qoida.
    commission = tariff.commission
    if is_delivery:
        price = max(price or 0, 10000)
        commission = 3000

    has_coords = bool(f_lat and f_lng)
    payment_type = request.data.get('payment_type', Order.PAYMENT_CASH)
    car_type = request.data.get('car_type', Driver.CAR_TYPE_LIGHT)
    note = str(request.data.get('note', '')).strip()

    order = Order.objects.create(
        client=client, from_address=from_address, from_lat=f_lat, from_lng=f_lng,
        to_address=to_address, to_lat=t_lat, to_lng=t_lng, distance_km=distance_km,
        price=price, commission=commission, driver=driver, payment_type=payment_type,
        car_type=car_type, is_delivery=is_delivery, note=note, status='pending',
    )

    # Operator qo'lda haydovchi tanlagan bo'lsa — buyurtma FAQAT o'sha
    # haydovchiga ko'rinishi kerak (dispatched_to), avtomatik dispatch bilan
    # bir xil push/Telegram va javob bermasa avtomatik bo'shatuvchi taymer.
    if driver is not None:
        from django.utils import timezone
        order.dispatched_to = driver
        order.dispatched_at = timezone.now()
        order.save(update_fields=['dispatched_to', 'dispatched_at'])
        manual_dist = haversine(f_lat, f_lng, driver.latitude, driver.longitude) if has_coords and driver.latitude and driver.longitude else None
        _log_dispatch_attempt(order, driver, manual_dist)
        notify_driver_new_order(order, driver)
        start_dispatch_timeout(order, driver, tariff.dispatch_timeout)

    tg_new_order(order)

    # Diqqat: SINXRON chaqiriladi — taxi/views.py:order_create'dagi bilan bir
    # xil sababga ko'ra (dispatched_to belgilanmaguncha bo'sh oraliqda hammaga
    # ko'rinib qolmasligi uchun).
    if has_coords and driver is None and tariff.auto_dispatch:
        dispatch_order(order)

    log_system_event(
        'order_created',
        f"Buyurtma #{order.id} yaratildi (operator ilova) — {from_address} → {to_address or '?'}"
        + (f" ({driver.full_name}ga tayinlandi)" if driver else ''),
        request=request,
    )
    order.refresh_from_db()
    return Response(OperatorAppOrderSerializer(order, context={'request': request}).data, status=201)


@api_view(['POST'])
@operator_required
def order_status(request, user, pk):
    from django.utils import timezone
    from .models import DispatchAttempt
    from .utils import (
        haversine, notify_driver_new_order, start_dispatch_timeout, _log_dispatch_attempt,
        _resolve_dispatch_attempt, sms_order_status, send_fcm, log_system_event,
        notify_dispatch_offer_cancelled,
    )
    from .views import _refund_order_commission

    order = get_object_or_404(Order, pk=pk)
    old_status = order.status
    old_driver = order.driver
    new_status = request.data.get('status')
    driver_id = request.data.get('driver_id') or None

    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
    reassigned_driver = None
    prev_dispatched_id = order.dispatched_to_id
    if driver_id:
        order.driver = Driver.objects.filter(pk=driver_id).first()
        if order.status == 'pending' and order.driver:
            order.dispatched_to = order.driver
            order.dispatched_at = timezone.now()
            reassigned_driver = order.driver
    order.save()

    if reassigned_driver:
        if prev_dispatched_id and prev_dispatched_id != reassigned_driver.id:
            _resolve_dispatch_attempt(order, prev_dispatched_id, DispatchAttempt.RESULT_CANCELLED)
            notify_dispatch_offer_cancelled(prev_dispatched_id, order, "operator tomonidan boshqa haydovchiga qayta yo'naltirildi (ilova)")
        manual_dist = haversine(order.from_lat, order.from_lng, reassigned_driver.latitude, reassigned_driver.longitude) if order.from_lat and order.from_lng and reassigned_driver.latitude else None
        _log_dispatch_attempt(order, reassigned_driver, manual_dist)
        notify_driver_new_order(order, reassigned_driver)
        start_dispatch_timeout(order, reassigned_driver, TariffSettings.get().dispatch_timeout)
    elif prev_dispatched_id and old_status == 'pending' and order.status != 'pending':
        notify_dispatch_offer_cancelled(prev_dispatched_id, order, "operator tomonidan bekor qilindi (ilova)")

    refunded = False
    if new_status == 'cancelled' and old_status in Order.ACTIVE_STATUSES and old_driver:
        _refund_order_commission(order, old_driver, "operator tomonidan bekor qilindi (ilova)")
        refunded = True

    if new_status in ('accepted', 'arrived', 'completed', 'cancelled'):
        sms_order_status(order, new_status)
    if new_status in ('cancelled', 'completed') and order.driver and not refunded:
        send_fcm(
            order.driver.fcm_token, title="Buyurtma holati o'zgardi",
            body=f'Buyurtma #{order.id} — {order.get_status_display()}',
            data={'type': 'order_update', 'order_id': str(order.id), 'status': new_status},
        )

    log_system_event(
        'order_status_changed',
        f"Buyurtma #{order.id}: {old_status} → {order.status} (operator ilova)"
        + (f" (haydovchi: {order.driver.full_name})" if order.driver else ''),
        request=request,
    )
    order.refresh_from_db()
    return Response(OperatorAppOrderSerializer(order, context={'request': request}).data)


@api_view(['POST'])
@operator_required
def order_dispatch(request, user, pk):
    from .utils import dispatch_order, log_system_event

    order = get_object_or_404(Order, pk=pk)
    if order.status != 'pending':
        return Response({'detail': "Faqat 'kutilmoqda' holatidagi buyurtmani dispetcherlash mumkin."}, status=400)
    dispatch_order(order)
    log_system_event('order_dispatched_manual', f"Buyurtma #{order.id} qo'lda dispetcherlandi (operator ilova)", request=request)
    order.refresh_from_db()
    return Response(OperatorAppOrderSerializer(order, context={'request': request}).data)


@api_view(['POST'])
@operator_required
def order_cancel(request, user, pk):
    """Haydovchi telefon qilib bekor qilishni so'raganda — `taxi/views.py:
    order_cancel_reassign` bilan bir xil: komissiya qaytariladi, buyurtma
    qayta 'kutilmoqda' holatiga o'tadi (boshqa haydovchilar qabul qilishi
    mumkin bo'ladi)."""
    from decimal import Decimal
    from .utils import dispatch_order, send_fcm, log_panel_event, log_system_event

    order = get_object_or_404(Order, pk=pk)
    if not (order.driver_id and order.status in Order.ACTIVE_STATUSES):
        return Response({'detail': "Bu buyurtmani bekor qilib bo'lmaydi."}, status=400)

    old_driver = order.driver
    commission = order.commission or TariffSettings.get().commission
    old_driver.balance += Decimal(str(commission))
    old_driver.save(update_fields=['balance'])
    BalanceLog.objects.create(
        driver=old_driver, action=BalanceLog.ACTION_ADD, amount=commission,
        balance_after=old_driver.balance,
        note=f"Komissiya qaytarildi — buyurtma #{order.id} operator tomonidan bekor qilindi (ilova)",
    )

    order.rejected_by.add(old_driver)
    order.driver = None
    order.dispatched_to = None
    order.dispatched_at = None
    order.status = 'pending'
    order.save(update_fields=['driver', 'dispatched_to', 'dispatched_at', 'status', 'updated_at'])

    log_panel_event('panel_order_cancelled', f"Buyurtma #{order.id} — {old_driver.full_name} dan bekor qilindi (operator ilova), qayta ochildi")
    log_system_event('order_cancelled_reassigned', f"Buyurtma #{order.id} — {old_driver.full_name}dan bekor qilindi (operator ilova), qayta ochildi", request=request)
    send_fcm(
        old_driver.fcm_token, title='Buyurtma bekor qilindi',
        body=f"Buyurtma #{order.id} operator tomonidan bekor qilindi. {commission} so'm balansingizga qaytarildi.",
        data={'type': 'order_cancelled', 'order_id': str(order.id)},
    )

    if TariffSettings.get().auto_dispatch:
        dispatch_order(order)

    order.refresh_from_db()
    return Response(OperatorAppOrderSerializer(order, context={'request': request}).data)


@api_view(['POST'])
@operator_required
def order_delete(request, user, pk):
    from .utils import log_panel_event, log_system_event, tg_order_deleted, notify_dispatch_offer_cancelled
    from .views import _refund_order_commission

    order = get_object_or_404(Order, pk=pk)
    if order.driver_id and order.status in Order.ACTIVE_STATUSES:
        _refund_order_commission(order, order.driver, "o'chirildi (operator ilova)")
    if order.status == 'pending' and order.dispatched_to_id:
        notify_dispatch_offer_cancelled(order.dispatched_to_id, order, "o'chirildi")
    log_panel_event('panel_order_deleted', f"Buyurtma #{order.id} — {order.from_address}")
    log_system_event('order_deleted', f"Buyurtma #{order.id} — {order.from_address} o'chirildi (operator ilova)", level='warning', request=request)
    tg_order_deleted(order)
    order.delete()
    return Response({'detail': "Buyurtma o'chirildi."})


# ── Haydovchilar ─────────────────────────────────────────────────────────────

@api_view(['GET'])
@operator_required
def driver_list(request, user):
    from django.core.paginator import Paginator
    from django.db.models import Case, When, Value, IntegerField, Count
    from django.utils import timezone

    q = request.query_params.get('q', '').strip()
    tab = request.query_params.get('tab', 'approved')
    sort = request.query_params.get('sort', '').strip()
    online_cutoff = timezone.now() - timezone.timedelta(seconds=ONLINE_THRESHOLD_SECONDS)
    qs = Driver.objects.annotate(
        completed_count=Count('orders', filter=Q(orders__status='completed')),
        cancelled_count=Count('orders', filter=Q(orders__status='cancelled')),
        is_online=Case(When(last_seen__gte=online_cutoff, then=Value(1)), default=Value(0), output_field=IntegerField()),
    )
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(phone_number__icontains=q) | Q(car_model__icontains=q) | Q(car_number__icontains=q))
    if tab == 'pending':
        qs = qs.filter(approval_status=Driver.APPROVAL_PENDING)
    elif tab == 'rejected':
        qs = qs.filter(approval_status=Driver.APPROVAL_REJECTED)
    else:
        qs = qs.filter(approval_status=Driver.APPROVAL_APPROVED)

    sort_map = {
        'top_completed': ('-is_online', '-completed_count', '-id'),
        'top_cancelled': ('-is_online', '-cancelled_count', '-id'),
        'top_rating':    ('-is_online', '-rating', '-id'),
        'top_balance':   ('-is_online', '-balance', '-id'),
        'newest':        ('-is_online', '-registered_at', '-id'),
    }
    qs = qs.order_by(*sort_map.get(sort, ('-is_online', '-last_seen', '-id')))

    if tab == 'pending':
        drivers, page_number, has_next, total_count = qs, 1, False, qs.count()
    else:
        page = Paginator(qs, 40).get_page(request.query_params.get('page'))
        drivers, page_number, has_next, total_count = page.object_list, page.number, page.has_next(), page.paginator.count

    return Response({
        'drivers': OperatorAppDriverSerializer(drivers, many=True, context={'request': request}).data,
        'page': page_number,
        'has_next': has_next,
        'total_count': total_count,
        'pending_count': Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).count(),
        'approved_count': Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).count(),
        'rejected_count': Driver.objects.filter(approval_status=Driver.APPROVAL_REJECTED).count(),
    })


@api_view(['GET'])
@operator_required
def driver_detail(request, user, pk):
    driver = get_object_or_404(Driver, pk=pk)
    orders = driver.orders.select_related('client').order_by('-created_at')[:20]
    return Response({
        'driver': OperatorAppDriverSerializer(driver, context={'request': request}).data,
        'recent_orders': OperatorAppOrderSerializer(orders, many=True, context={'request': request}).data,
    })


@api_view(['GET'])
@operator_required
def driver_live(request, user):
    from django.db.models import Count
    from django.utils import timezone

    today = timezone.now().date()
    drivers = Driver.objects.filter(
        is_active=True, approval_status=Driver.APPROVAL_APPROVED,
        latitude__isnull=False, longitude__isnull=False,
    ).annotate(today_orders_count=Count('orders', filter=Q(orders__created_at__date=today) & ~Q(orders__status='cancelled')))
    now = timezone.now()
    data = []
    for d in drivers:
        is_online = bool(d.last_seen) and (now - d.last_seen).total_seconds() < ONLINE_THRESHOLD_SECONDS
        data.append({
            'id': d.id, 'full_name': d.full_name, 'phone_number': d.phone_number,
            'car_model': d.car_model, 'car_number': d.car_number,
            'latitude': d.latitude, 'longitude': d.longitude,
            'balance': str(d.balance), 'today_orders_count': d.today_orders_count,
            'last_address': d.last_address or '', 'is_online': is_online, 'is_on_duty': d.is_on_duty,
        })
    return Response({'drivers': data})


@api_view(['POST'])
@operator_required
def driver_approve(request, user, pk):
    from .utils import tg_driver_approved, tg_driver_rejected, log_system_event

    driver = get_object_or_404(Driver, pk=pk)
    action = request.data.get('action')
    if action == 'approve':
        driver.approval_status = Driver.APPROVAL_APPROVED
        driver.is_active = True
        if driver.user:
            driver.user.is_active = True
            driver.user.save(update_fields=['is_active'])
        tg_driver_approved(driver)
        log_system_event('driver_approved', f"Haydovchi tasdiqlandi (operator ilova): {driver.full_name} ({driver.phone_number})", request=request)
    elif action == 'reject':
        driver.approval_status = Driver.APPROVAL_REJECTED
        driver.is_active = False
        tg_driver_rejected(driver)
        log_system_event('driver_rejected', f"Haydovchi rad etildi (operator ilova): {driver.full_name} ({driver.phone_number})", level='warning', request=request)
    else:
        return Response({'detail': "action 'approve' yoki 'reject' bo'lishi kerak."}, status=400)
    driver.save(update_fields=['approval_status', 'is_active'])
    return Response(OperatorAppDriverSerializer(driver, context={'request': request}).data)


@api_view(['POST'])
@operator_required
def driver_toggle_active(request, user, pk):
    from .models import DriverActivityLog
    from .utils import tg_driver_blocked, tg_driver_unblocked

    driver = get_object_or_404(Driver, pk=pk)
    driver.is_active = not driver.is_active
    driver.save(update_fields=['is_active'])
    action = DriverActivityLog.ACTION_UNBLOCK if driver.is_active else DriverActivityLog.ACTION_BLOCK
    detail = 'Operator ilova: ' + ('blok ochildi' if driver.is_active else 'bloklandi')
    DriverActivityLog.objects.create(driver=driver, action=action, detail=detail, ip_address=_get_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''))
    (tg_driver_unblocked if driver.is_active else tg_driver_blocked)(driver)
    return Response(OperatorAppDriverSerializer(driver, context={'request': request}).data)


@api_view(['POST'])
@operator_required
def driver_toggle_frozen(request, user, pk):
    from .models import DriverActivityLog

    driver = get_object_or_404(Driver, pk=pk)
    driver.is_frozen = not driver.is_frozen
    driver.save(update_fields=['is_frozen'])
    action = DriverActivityLog.ACTION_FREEZE if driver.is_frozen else DriverActivityLog.ACTION_UNFREEZE
    detail = 'Operator ilova: ' + ('muzlatildi' if driver.is_frozen else 'muzlash bekor qilindi')
    DriverActivityLog.objects.create(driver=driver, action=action, detail=detail, ip_address=_get_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''))
    return Response(OperatorAppDriverSerializer(driver, context={'request': request}).data)


@api_view(['POST'])
@operator_required
def driver_recharge(request, user, pk):
    from decimal import Decimal, InvalidOperation
    from .models import DriverActivityLog
    from .utils import tg_balance_changed, send_fcm

    driver = get_object_or_404(Driver, pk=pk)
    action = 'deduct' if request.data.get('action') == 'deduct' else 'add'
    try:
        amount = Decimal(str(request.data.get('amount', '')))
    except InvalidOperation:
        return Response({'detail': "Summani to'g'ri kiriting."}, status=400)
    if amount <= 0:
        return Response({'detail': "Summa musbat bo'lishi kerak."}, status=400)

    if action == 'deduct':
        driver.balance -= amount
        detail = f"-{amount} UZS (operator ilova ayirdi)"
    else:
        driver.balance += amount
        detail = f"+{amount} UZS (operator ilova qo'shdi)"
    driver.save(update_fields=['balance'])
    BalanceLog.objects.create(driver=driver, action=action, amount=amount, balance_after=driver.balance, note=str(request.data.get('note', '')))
    DriverActivityLog.objects.create(driver=driver, action=DriverActivityLog.ACTION_BALANCE, detail=detail, ip_address=_get_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''))
    tg_balance_changed(driver, amount, action)
    if action == 'deduct':
        send_fcm(driver.fcm_token, title="💰 Balans o'zgardi", body=f"-{amount:,.0f} so'm ayirildi. Joriy balans: {driver.balance:,.0f} so'm".replace(',', ' '), data={'type': 'balance_changed'})
    else:
        send_fcm(driver.fcm_token, title="💰 Balans to'ldirildi", body=f"+{amount:,.0f} so'm qo'shildi. Joriy balans: {driver.balance:,.0f} so'm".replace(',', ' '), data={'type': 'balance_changed'})
    return Response(OperatorAppDriverSerializer(driver, context={'request': request}).data)


# ── Chat (1:1 va umumiy kanal) ────────────────────────────────────────────────
# Bir xil ChatMessage/GroupMessage model — `taxi/views.py: operator_chat`
# bilan bir xil ma'lumot, faqat token-autentifikatsiyali JSON ko'rinishida.

def _chat_message_dict(msg):
    return {
        'id': msg.id, 'sender': msg.sender, 'text': msg.text,
        'is_read': msg.is_read, 'created_at': msg.created_at.isoformat(),
    }


@api_view(['GET'])
@operator_required
def chat_driver_list(request, user):
    drivers = Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).order_by('full_name')
    data = []
    for d in drivers:
        last_msg = ChatMessage.objects.filter(driver=d).order_by('-created_at').first()
        unread = ChatMessage.objects.filter(driver=d, sender=ChatMessage.SENDER_DRIVER, is_read=False).count()
        data.append({
            'driver_id': d.id, 'full_name': d.full_name, 'car_number': d.car_number,
            'last_message': _chat_message_dict(last_msg) if last_msg else None,
            'unread': unread,
        })
    return Response(data)


@api_view(['GET'])
@operator_required
def chat_messages(request, user, driver_id):
    driver = get_object_or_404(Driver, pk=driver_id)
    ChatMessage.objects.filter(driver=driver, sender=ChatMessage.SENDER_DRIVER, is_read=False).update(is_read=True)
    msgs = ChatMessage.objects.filter(driver=driver).order_by('created_at')[:200]
    return Response([_chat_message_dict(m) for m in msgs])


@api_view(['POST'])
@operator_required
def chat_send(request, user, driver_id):
    from .utils import send_fcm

    driver = get_object_or_404(Driver, pk=driver_id)
    text = str(request.data.get('text', '')).strip()
    if not text:
        return Response({'detail': "Xabar matni bo'sh bo'lishi mumkin emas."}, status=400)
    msg = ChatMessage.objects.create(driver=driver, sender=ChatMessage.SENDER_OPERATOR, text=text)
    send_fcm(driver.fcm_token, title='💬 Operator', body=text, data={'type': 'chat'})
    return Response(_chat_message_dict(msg), status=201)


@api_view(['GET'])
@operator_required
def chat_unread(request, user):
    count = ChatMessage.objects.filter(sender=ChatMessage.SENDER_DRIVER, is_read=False).count()
    return Response({'count': count})


def _group_message_dict(msg):
    return {
        'id': msg.id, 'sender_name': msg.display_name, 'text': msg.text,
        'is_driver': msg.driver_id is not None, 'created_at': msg.created_at.isoformat(),
    }


@api_view(['GET'])
@operator_required
def chat_group_list(request, user):
    msgs = GroupMessage.objects.select_related('driver').order_by('-created_at')[:200]
    return Response([_group_message_dict(m) for m in reversed(list(msgs))])


@api_view(['POST'])
@operator_required
def chat_group_send(request, user):
    text = str(request.data.get('text', '')).strip()
    if not text:
        return Response({'detail': "Xabar matni bo'sh bo'lishi mumkin emas."}, status=400)
    msg = GroupMessage.objects.create(driver=None, sender_name=user.get_full_name() or user.username, text=text)
    return Response(_group_message_dict(msg), status=201)


# ── Balans ────────────────────────────────────────────────────────────────────

@api_view(['GET'])
@operator_required
def topup_list(request, user):
    status_filter = request.query_params.get('status', BalanceTopupRequest.STATUS_PENDING)
    qs = BalanceTopupRequest.objects.select_related('driver').order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)
    data = [{
        'id': t.id, 'driver_id': t.driver_id, 'driver_name': t.driver.full_name,
        'driver_phone': t.driver.phone_number, 'amount': str(t.amount),
        'receipt_url': request.build_absolute_uri(t.receipt.url) if t.receipt else None,
        'status': t.status, 'reject_reason': t.reject_reason,
        'created_at': t.created_at.isoformat(),
        'resolved_at': t.resolved_at.isoformat() if t.resolved_at else None,
    } for t in qs[:100]]
    return Response({
        'requests': data,
        'pending_count': BalanceTopupRequest.objects.filter(status=BalanceTopupRequest.STATUS_PENDING).count(),
    })


@api_view(['POST'])
@operator_required
def topup_resolve(request, user, pk):
    from django.utils import timezone
    from .models import DriverActivityLog
    from .utils import tg_balance_changed, send_fcm

    topup = get_object_or_404(BalanceTopupRequest, pk=pk)
    if topup.status != BalanceTopupRequest.STATUS_PENDING:
        return Response({'detail': "Bu so'rov allaqachon hal qilingan."}, status=400)
    action = request.data.get('action')
    driver = topup.driver
    if action == 'approve':
        driver.balance += topup.amount
        driver.save(update_fields=['balance'])
        BalanceLog.objects.create(
            driver=driver, action=BalanceLog.ACTION_ADD, amount=topup.amount,
            balance_after=driver.balance, note=f"To'lov cheki tasdiqlandi #{topup.id} (operator ilova)",
        )
        DriverActivityLog.objects.create(
            driver=driver, action=DriverActivityLog.ACTION_BALANCE,
            detail=f"Operator ilova: to'lov cheki #{topup.id} tasdiqlandi, +{topup.amount} UZS",
            ip_address=_get_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        topup.status = BalanceTopupRequest.STATUS_APPROVED
        tg_balance_changed(driver, topup.amount, BalanceLog.ACTION_ADD)
        send_fcm(
            driver.fcm_token, title="💰 Balans to'ldirildi",
            body=f"+{topup.amount:,.0f} so'm qo'shildi. Joriy balans: {driver.balance:,.0f} so'm".replace(',', ' '),
            data={'type': 'balance_changed'},
        )
    elif action == 'reject':
        reason = str(request.data.get('reason', '')).strip()
        topup.status = BalanceTopupRequest.STATUS_REJECTED
        topup.reject_reason = reason
        send_fcm(
            driver.fcm_token, title="❌ To'lov so'rovi rad etildi",
            body=f"{topup.amount} UZS to'lov so'rovingiz rad etildi." + (f" Sabab: {reason}" if reason else ''),
            data={'type': 'topup_rejected'},
        )
    else:
        return Response({'detail': "action 'approve' yoki 'reject' bo'lishi kerak."}, status=400)
    topup.resolved_at = timezone.now()
    topup.save(update_fields=['status', 'resolved_at', 'reject_reason'])
    return Response({'detail': 'ok', 'status': topup.status})


@api_view(['GET'])
@operator_required
def balance_log(request, user):
    from django.core.paginator import Paginator

    qs = BalanceLog.objects.select_related('driver').order_by('-created_at')
    q = request.query_params.get('q', '').strip()
    action_filter = request.query_params.get('action', '')
    if action_filter in (BalanceLog.ACTION_ADD, BalanceLog.ACTION_DEDUCT):
        qs = qs.filter(action=action_filter)
    if q:
        qs = qs.filter(Q(driver__full_name__icontains=q) | Q(driver__phone_number__icontains=q))
    page = Paginator(qs, 30).get_page(request.query_params.get('page'))
    data = [{
        'id': log.id, 'driver_id': log.driver_id, 'driver_name': log.driver.full_name,
        'action': log.action, 'amount': str(log.amount), 'balance_after': str(log.balance_after),
        'note': log.note, 'created_at': log.created_at.isoformat(),
    } for log in page.object_list]
    return Response({'entries': data, 'page': page.number, 'has_next': page.has_next(), 'total_count': page.paginator.count})
