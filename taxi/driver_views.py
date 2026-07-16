"""
Haydovchi Web UI views — WebView ilovasi uchun.
URL prefix: /driver/
"""
import json
from decimal import Decimal
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Driver, Order, ChatMessage, TariffSettings, DriverActivityLog
from .utils import tg_order_accepted, tg_order_on_way, tg_order_arrived, tg_order_completed, tg_order_cancelled, tg_order_rejected


# ── Auth decorator ────────────────────────────────────────────────────────────

def driver_login_required(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('driver:login')
        try:
            driver = request.user.driver_profile
        except Driver.DoesNotExist:
            return redirect('driver:login')
        if driver.approval_status != Driver.APPROVAL_APPROVED:
            return render(request, 'driver/pending.html', {'driver': driver})
        return fn(request, driver, *args, **kwargs)
    return wrapper


def _chat_unread(driver):
    return ChatMessage.objects.filter(driver=driver, sender=ChatMessage.SENDER_OPERATOR, is_read=False).count()


# ── Auth ──────────────────────────────────────────────────────────────────────

def driver_login_view(request):
    if request.user.is_authenticated:
        return redirect('driver:home')
    error = None
    if request.method == 'POST':
        phone    = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        user     = authenticate(request, username=phone, password=password)
        if user is None:
            error = "Telefon raqami yoki parol noto'g'ri."
        else:
            try:
                driver = user.driver_profile
            except Driver.DoesNotExist:
                error = 'Haydovchi profili topilmadi.'
            else:
                if driver.approval_status == Driver.APPROVAL_REJECTED:
                    error = "Hisobingiz rad etilgan."
                elif driver.approval_status == Driver.APPROVAL_PENDING:
                    login(request, user)
                    return redirect('driver:home')
                else:
                    login(request, user)
                    return redirect('driver:home')
    return render(request, 'driver/login.html', {'error': error})


def driver_logout_view(request):
    logout(request)
    return redirect('driver:login')


def driver_register_view(request):
    from .serializers import DriverRegisterSerializer
    error = None
    if request.method == 'POST':
        data = {
            'full_name':    request.POST.get('full_name', ''),
            'phone_number': request.POST.get('phone_number', ''),
            'car_model':    request.POST.get('car_model', ''),
            'car_number':   request.POST.get('car_number', ''),
            'password':     request.POST.get('password', ''),
        }
        s = DriverRegisterSerializer(data=data)
        if s.is_valid():
            s.save()
            return render(request, 'driver/register_done.html')
        error = ' '.join([str(v[0]) for v in s.errors.values()])
    return render(request, 'driver/register.html', {'error': error})


# ── Home ──────────────────────────────────────────────────────────────────────

@driver_login_required
def driver_home(request, driver):
    from django.db.models import Q
    orders = Order.objects.select_related('client', 'driver').filter(
        Q(status='pending', dispatched_to=driver) |
        Q(status='pending', dispatched_to__isnull=True) |
        Q(driver=driver, status__in=['accepted', 'on_way', 'arrived'])
    ).exclude(
        Q(status='pending', rejected_by=driver)
    ).order_by('-created_at')

    orders_data = []
    for o in orders:
        # Dispatch timer uchun qancha vaqt qolganini hisoblash
        timer_sec = None
        if o.status == 'pending' and o.dispatched_to_id == driver.id and o.dispatched_at:
            from django.utils import timezone
            timeout = TariffSettings.get().dispatch_timeout
            elapsed = (timezone.now() - o.dispatched_at).total_seconds()
            timer_sec = max(0, int(timeout - elapsed))

        orders_data.append({
            'id':           o.id,
            'status':       o.status,
            'from_address': o.from_address,
            'to_address':   o.to_address,
            'client_name':  o.client.full_name or 'Mijoz',
            'client_phone': o.client.phone_number if o.status != 'pending' else '+998 ** *** ** **',
            'price':        str(o.price) if o.price else None,
            'distance_km':  o.distance_km,
            'payment_type': o.payment_type,
            'note':         o.note or '',
            'commission':   str(o.commission) if o.commission else None,
            'is_dispatched': o.dispatched_to_id == driver.id,
            'timer_sec':    timer_sec,
        })

    return render(request, 'driver/home.html', {
        'driver':      driver,
        'orders':      orders,
        'orders_json': json.dumps(orders_data, ensure_ascii=False),
        'active_tab':  'home',
        'chat_unread': _chat_unread(driver),
    })


@driver_login_required
def driver_orders_json(request, driver):
    """AJAX: buyurtmalar o'zgardimi tekshirish."""
    from django.db.models import Q
    from django.utils import timezone
    qs = Order.objects.filter(
        Q(status='pending', dispatched_to=driver) |
        Q(status='pending', dispatched_to__isnull=True) |
        Q(driver=driver, status__in=['accepted', 'on_way', 'arrived'])
    ).exclude(Q(status='pending', rejected_by=driver))
    ids = list(qs.values_list('id', flat=True))

    # Dispatch timer: dispatched_to=driver bo'lgan pending buyurtmaga qancha vaqt qoldi
    timer_sec = None
    dispatched = qs.filter(status='pending', dispatched_to=driver).first()
    if dispatched and dispatched.dispatched_at:
        from taxi.models import TariffSettings
        timeout = TariffSettings.get().dispatch_timeout
        elapsed = (timezone.now() - dispatched.dispatched_at).total_seconds()
        timer_sec = max(0, int(timeout - elapsed))

    return JsonResponse({'reload': True, 'new_ids': ids, 'timer_sec': timer_sec})


# ── Order actions ─────────────────────────────────────────────────────────────

@require_POST
@driver_login_required
def driver_order_action(request, driver, pk, action):
    order = get_object_or_404(Order, pk=pk)

    if action == 'reject':
        if order.status == 'pending':
            order.rejected_by.add(driver)
            if order.dispatched_to_id == driver.id:
                order.dispatched_to = None
                order.save(update_fields=['dispatched_to'])
                tg_order_rejected(order, driver)
                import threading
                from .utils import dispatch_order
                threading.Thread(target=dispatch_order, args=(order,), daemon=True).start()
        return JsonResponse({'ok': True})

    allowed = {
        'accept':   (['pending'],                  'accepted'),
        'on_way':   (['accepted'],                 'on_way'),
        'arrived':  (['on_way'],                   'arrived'),
        'complete': (['arrived', 'on_way', 'accepted'], 'completed'),
        'cancel':   (['accepted', 'on_way', 'arrived'], 'cancelled'),
    }
    if action not in allowed:
        return JsonResponse({'ok': False, 'error': 'Noto\'g\'ri amal'}, status=400)

    statuses, new_status = allowed[action]
    if order.status not in statuses:
        return JsonResponse({'ok': False, 'error': f"'{order.get_status_display()}' holatida bu amal mumkin emas"}, status=400)

    if action == 'accept':
        from django.db import transaction
        with transaction.atomic():
            locked = Order.objects.select_for_update().get(pk=pk)
            if locked.status != 'pending':
                return JsonResponse({'ok': False, 'error': 'Bu buyurtmani boshqa haydovchi qabul qildi'}, status=409)
            tariff = TariffSettings.get()
            commission = locked.commission or tariff.commission
            if driver.balance < commission:
                return JsonResponse({'ok': False, 'error': f'Balans yetarli emas. Komissiya: {commission} UZS'}, status=400)
            driver.balance -= Decimal(str(commission))
            driver.save(update_fields=['balance'])
            locked.driver = driver
            locked.status = 'accepted'
            locked.dispatched_to = None
            locked.save(update_fields=['status', 'driver', 'dispatched_to', 'updated_at'])
        tg_order_accepted(locked, driver)
        return JsonResponse({'ok': True})

    if order.driver_id and order.driver_id != driver.id:
        return JsonResponse({'ok': False, 'error': 'Bu buyurtma sizga tegishli emas'}, status=403)

    order.status = new_status
    order.save(update_fields=['status', 'updated_at'])

    if new_status == 'completed':
        try:
            order.client.trips_count += 1
            order.client.save(update_fields=['trips_count'])
        except Exception:
            pass

    tg_map = {
        'on_way': tg_order_on_way, 'arrived': tg_order_arrived,
        'completed': tg_order_completed, 'cancelled': tg_order_cancelled,
    }
    if new_status in tg_map:
        tg_map[new_status](order, driver)

    return JsonResponse({'ok': True})


# ── History ───────────────────────────────────────────────────────────────────

@driver_login_required
def driver_history(request, driver):
    orders = Order.objects.filter(driver=driver).order_by('-created_at')[:50]
    return render(request, 'driver/history.html', {
        'driver':      driver,
        'orders':      orders,
        'active_tab':  'history',
        'chat_unread': _chat_unread(driver),
    })


# ── Chat ──────────────────────────────────────────────────────────────────────

@driver_login_required
def driver_chat(request, driver):
    ChatMessage.objects.filter(driver=driver, sender=ChatMessage.SENDER_OPERATOR, is_read=False).update(is_read=True)
    messages = ChatMessage.objects.filter(driver=driver).order_by('created_at')[:100]
    return render(request, 'driver/chat.html', {
        'driver':      driver,
        'messages':    messages,
        'active_tab':  'chat',
        'chat_unread': 0,
    })


@require_POST
@driver_login_required
def driver_chat_send(request, driver):
    from .utils import send_telegram
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
    except Exception:
        text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'ok': False}, status=400)
    msg = ChatMessage.objects.create(driver=driver, sender=ChatMessage.SENDER_DRIVER, text=text)
    send_telegram(f"💬 <b>{driver.full_name}</b> ({driver.car_number}):\n{text}")
    return JsonResponse({'ok': True, 'id': msg.id, 'text': msg.text, 'created_at': msg.created_at.isoformat()})


@driver_login_required
def driver_chat_poll(request, driver):
    """AJAX: yangi xabarlar bormi?"""
    last_id = int(request.GET.get('last_id', 0))
    msgs = ChatMessage.objects.filter(driver=driver, id__gt=last_id).order_by('created_at')
    msgs.filter(sender=ChatMessage.SENDER_OPERATOR).update(is_read=True)
    return JsonResponse({'messages': [
        {'id': m.id, 'sender': m.sender, 'text': m.text, 'created_at': m.created_at.isoformat()}
        for m in msgs
    ]})


# ── Profile ───────────────────────────────────────────────────────────────────

@driver_login_required
def driver_profile(request, driver):
    return render(request, 'driver/profile.html', {
        'driver':      driver,
        'active_tab':  'profile',
        'chat_unread': _chat_unread(driver),
    })


# ── Sync endpoints (Native bridge) ───────────────────────────────────────────

@require_POST
@driver_login_required
def driver_fcm_sync(request, driver):
    try:
        data = json.loads(request.body)
        token = data.get('fcm_token', '').strip()
    except Exception:
        token = ''
    if token:
        driver.fcm_token = token
        driver.save(update_fields=['fcm_token'])
    return JsonResponse({'ok': True})


@require_POST
@driver_login_required
def driver_location_sync(request, driver):
    try:
        data = json.loads(request.body)
        lat = float(data.get('lat', 0))
        lng = float(data.get('lng', 0))
        driver.latitude  = lat
        driver.longitude = lng
        driver.save(update_fields=['latitude', 'longitude'])
    except Exception:
        pass
    return JsonResponse({'ok': True})


@require_POST
@driver_login_required
def driver_duty_toggle(request, driver):
    driver.is_on_duty = not driver.is_on_duty
    driver.save(update_fields=['is_on_duty'])
    return JsonResponse({'ok': True, 'is_on_duty': driver.is_on_duty})


# ── ETA: haydovchi qancha vaqtda yetib keladi ─────────────────────────────────
@driver_login_required
def driver_order_eta(request, driver, pk):
    """Haydovchining buyurtma manziliga ETA ni hisoblaydi (daqiqa)."""
    order = get_object_or_404(Order, pk=pk)
    eta_min = None
    distance_km = None
    if (driver.latitude and driver.longitude and
            order.from_lat and order.from_lng):
        from .utils import haversine
        distance_km = haversine(driver.latitude, driver.longitude,
                                order.from_lat, order.from_lng)
        if distance_km is not None:
            # Shahar ichida o'rtacha 30 km/h tezlik
            eta_min = round(distance_km / 30 * 60)
            eta_min = max(1, eta_min)
    return JsonResponse({'ok': True, 'eta_min': eta_min, 'distance_km': round(distance_km, 2) if distance_km else None})


# ── Rating: buyurtma yakunida haydovchiga reyting berish ─────────────────────
@require_POST
@driver_login_required
def driver_order_rate(request, driver, pk):
    """Operator yoki mijoz haydovchiga reyting beradi (1-5)."""
    order = get_object_or_404(Order, pk=pk)
    if order.status != 'completed':
        return JsonResponse({'ok': False, 'error': 'Faqat yakunlangan buyurtmaga reyting beriladi'}, status=400)
    try:
        stars = int(request.POST.get('stars', 0))
        if not 1 <= stars <= 5:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': '1-5 orasida reyting bering'}, status=400)

    order.client_rating = stars
    order.save(update_fields=['client_rating'])

    # Haydovchi o'rtacha reytingini yangilash
    if order.driver:
        d = order.driver
        rated_orders = Order.objects.filter(
            driver=d, status='completed', client_rating__isnull=False
        )
        count = rated_orders.count()
        if count > 0:
            from django.db.models import Avg
            avg = rated_orders.aggregate(a=Avg('client_rating'))['a']
            d.rating = round(avg, 2)
            d.rating_count = count
            d.save(update_fields=['rating', 'rating_count'])
    return JsonResponse({'ok': True})


# ── Surge: hozirgi narx multiplikatori ───────────────────────────────────────
@driver_login_required
def driver_surge_info(request, driver):
    """Hozirgi surge (narx oshishi) ma'lumotini qaytaradi."""
    from .utils import get_surge_multiplier
    multiplier, reason = get_surge_multiplier()
    return JsonResponse({'ok': True, 'multiplier': multiplier, 'reason': reason})
