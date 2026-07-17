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


def _mask_phone(phone):
    """Telefon raqamni mask qiladi: +998901234567 → +998 90 ***-**-67"""
    p = ''.join(filter(str.isdigit, phone or ''))
    if len(p) >= 9:
        return phone[:4] + ' ** *** ** ' + phone[-2:]
    return '** *** ** **'


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
            'client_phone': o.client.phone_number if o.status != 'pending' else _mask_phone(o.client.phone_number),
            'price':        str(o.price) if o.price else None,
            'distance_km':  o.distance_km,
            'payment_type': o.payment_type,
            'note':         o.note or '',
            'commission':   str(o.commission) if o.commission else None,
            'is_dispatched': o.dispatched_to_id == driver.id,
            'timer_sec':    timer_sec,
        })

    _tariff = TariffSettings.get()
    # Bugungi statistika
    from django.utils import timezone
    from django.db.models import Sum, Count, Q as DQ
    today = timezone.now().date()
    today_stats = Order.objects.filter(
        driver=driver, created_at__date=today
    ).aggregate(
        earned=Sum('price', filter=DQ(status='completed')),
        trips=Count('id', filter=DQ(status='completed')),
    )
    return render(request, 'driver/home.html', {
        'driver':      driver,
        'orders':      orders,
        'orders_json': json.dumps(orders_data, ensure_ascii=False),
        'active_tab':  'home',
        'chat_unread': _chat_unread(driver),
        'tariff':      _tariff,
        'tariff_base_price': int(_tariff.base_price),
        'tariff_per_km': int(_tariff.price_per_km),
        'driver_balance_int': int(driver.balance),
        'today_earned': int(today_stats['earned'] or 0),
        'today_trips': today_stats['trips'] or 0,
        'VAPID_PUBLIC_KEY': getattr(__import__('django.conf', fromlist=['settings']).settings, 'VAPID_PUBLIC_KEY', ''),
    })


@driver_login_required
def driver_orders_json(request, driver):
    """AJAX: buyurtmalar ro'yxati + yangi pending ID lar."""
    from django.db.models import Q
    from django.utils import timezone
    qs = Order.objects.select_related('client').filter(
        Q(status='pending', dispatched_to=driver) |
        Q(status='pending', dispatched_to__isnull=True) |
        Q(driver=driver, status__in=['accepted', 'on_way', 'arrived'])
    ).exclude(Q(status='pending', rejected_by=driver)).order_by('-created_at')

    orders_data = []
    for o in qs:
        timer_sec = None
        if o.status == 'pending' and o.dispatched_to_id == driver.id and o.dispatched_at:
            timeout = TariffSettings.get().dispatch_timeout
            elapsed = (timezone.now() - o.dispatched_at).total_seconds()
            timer_sec = max(0, int(timeout - elapsed))
        orders_data.append({
            'id':            o.id,
            'status':        o.status,
            'from_address':  o.from_address,
            'to_address':    o.to_address,
            'client_name':   o.client.full_name or 'Mijoz',
            'client_phone':  o.client.phone_number if o.status != 'pending' else _mask_phone(o.client.phone_number),
            'price':         str(o.price) if o.price else None,
            'distance_km':   o.distance_km,
            'payment_type':  o.payment_type,
            'note':          o.note or '',
            'commission':    str(o.commission) if o.commission else None,
            'is_dispatched': o.dispatched_to_id == driver.id,
            'timer_sec':     timer_sec,
        })

    ids = [o['id'] for o in orders_data]
    return JsonResponse({'new_ids': ids, 'orders': orders_data})


# ── Order actions ─────────────────────────────────────────────────────────────

@driver_login_required
@require_POST
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
        return JsonResponse({'ok': True, 'new_balance': float(driver.balance)})

    if order.driver_id and order.driver_id != driver.id:
        return JsonResponse({'ok': False, 'error': 'Bu buyurtma sizga tegishli emas'}, status=403)

    order.status = new_status
    update_fields = ['status', 'updated_at']

    # Taximeter ma'lumotlarini saqlash (arrived, complete)
    try:
        tmx_dist = request.POST.get('tmx_dist_km')
        tmx_price = request.POST.get('tmx_price')
        if tmx_dist and float(tmx_dist) > 0:
            order.distance_km = round(float(tmx_dist), 2)
            update_fields.append('distance_km')
        if tmx_price and float(tmx_price) > 0 and not order.price:
            order.price = round(float(tmx_price), 2)
            update_fields.append('price')
    except Exception:
        pass

    order.save(update_fields=update_fields)

    if new_status == 'completed':
        try:
            order.client.trips_count += 1
            order.client.save(update_fields=['trips_count'])
        except Exception:
            pass
        # Haydovchi trips_count ni ham yangilaymiz
        try:
            driver.trips_count = (driver.trips_count or 0) + 1
            driver.save(update_fields=['trips_count'])
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
    from django.db.models import Sum, Count, Q as DQ
    orders = Order.objects.filter(driver=driver).order_by('-created_at')[:50]
    stats = orders.aggregate(
        total_earned=Sum('price', filter=DQ(status='completed')),
        completed=Count('id', filter=DQ(status='completed')),
    )
    return render(request, 'driver/history.html', {
        'driver':      driver,
        'orders':      orders,
        'total_earned': stats['total_earned'] or 0,
        'active_tab':  'history',
        'chat_unread': _chat_unread(driver),
    })


# ── Chat ──────────────────────────────────────────────────────────────────────

@driver_login_required
def driver_chat(request, driver):
    ChatMessage.objects.filter(driver=driver, sender=ChatMessage.SENDER_OPERATOR, is_read=False).update(is_read=True)
    # Evaluate the queryset to a list so template's .last won't call .reverse() on a sliced queryset
    messages = list(ChatMessage.objects.filter(driver=driver).order_by('created_at')[:100])
    last_msg_id = messages[-1].id if messages else 0
    return render(request, 'driver/chat.html', {
        'driver':      driver,
        'messages':    messages,
        'last_msg_id': last_msg_id,
        'active_tab':  'chat',
        'chat_unread': 0,
    })


@driver_login_required
@require_POST
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


@driver_login_required
@require_POST
def driver_profile_photo(request, driver):
    photo = request.FILES.get('photo')
    if not photo:
        return JsonResponse({'ok': False, 'error': 'Rasm tanlanmadi'}, status=400)
    if driver.photo:
        driver.photo.delete(save=False)
    driver.photo = photo
    driver.save(update_fields=['photo'])
    return JsonResponse({'ok': True, 'url': request.build_absolute_uri(driver.photo.url)})


@driver_login_required
@require_POST
def driver_profile_password(request, driver):
    old = request.POST.get('old_password', '')
    new = request.POST.get('new_password', '')
    if not driver.user:
        return JsonResponse({'ok': False, 'error': 'Foydalanuvchi topilmadi'}, status=400)
    if not driver.user.check_password(old):
        return JsonResponse({'ok': False, 'error': "Eski parol noto'g'ri"}, status=400)
    if len(new) < 6:
        return JsonResponse({'ok': False, 'error': 'Parol kamida 6 ta belgi bo\'lishi kerak'}, status=400)
    driver.user.set_password(new)
    driver.user.save()
    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, driver.user)
    return JsonResponse({'ok': True})


# ── Web Push ─────────────────────────────────────────────────────────────────

@driver_login_required
@require_POST
def driver_push_subscribe(request, driver):
    """Haydovchining push subscription ma'lumotini saqlaydi."""
    try:
        data = json.loads(request.body)
        driver.push_subscription = json.dumps(data)
        driver.save(update_fields=['push_subscription'])
    except Exception:
        return JsonResponse({'ok': False}, status=400)
    return JsonResponse({'ok': True})


def send_push_to_driver(driver, title, body, url='/driver/home/'):
    """Haydovchiga Web Push yuboradi."""
    if not getattr(driver, 'push_subscription', None):
        return
    from django.conf import settings
    from pywebpush import webpush, WebPushException
    try:
        sub = json.loads(driver.push_subscription)
        webpush(
            subscription_info=sub,
            data=json.dumps({'title': title, 'body': body, 'url': url}),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims=settings.VAPID_CLAIMS,
        )
    except WebPushException:
        pass
    except Exception:
        pass


# ── Sync endpoints (Native bridge) ───────────────────────────────────────────

@driver_login_required
@require_POST
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


@driver_login_required
@require_POST
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


@driver_login_required
@require_POST
def driver_duty_toggle(request, driver):
    tariff = TariffSettings.get()
    # Navbatga kirishda balans yetarlimi tekshirish
    if not driver.is_on_duty and driver.balance < tariff.commission:
        return JsonResponse({
            'ok': False,
            'error': f"Balans yetarli emas. Kamida {int(tariff.commission):,} so'm bo'lishi kerak."
        }, status=400)
    driver.is_on_duty = not driver.is_on_duty
    driver.save(update_fields=['is_on_duty'])
    return JsonResponse({'ok': True, 'is_on_duty': driver.is_on_duty})


# ── Taxi Meter ───────────────────────────────────────────────────────────────

@driver_login_required
def driver_meter_update(request, driver, pk):
    """GPS koordinatalardan real-time masofa va narx hisoblaydi."""
    order = get_object_or_404(Order, pk=pk, driver=driver)
    try:
        lat = float(request.GET.get('lat', 0))
        lng = float(request.GET.get('lng', 0))
        elapsed = int(request.GET.get('elapsed', 0))  # sekund
    except (ValueError, TypeError):
        return JsonResponse({'ok': False}, status=400)

    from .utils import haversine
    tariff = TariffSettings.get()

    # Agar buyurtmada narx belgilangan bo'lsa — uni qaytaramiz
    if order.price:
        return JsonResponse({
            'ok': True,
            'fixed': True,
            'price': float(order.price),
            'distance_km': order.distance_km,
        })

    # GPS asosida masofa hisoblash
    dist = None
    if lat and lng and order.from_lat and order.from_lng:
        dist = haversine(order.from_lat, order.from_lng, lat, lng)

    # Narx hisoblash: base + km * price_per_km + vaqt bonusi (har 1 daqiqa = 200 so'm)
    price = float(tariff.base_price)
    if dist:
        price += dist * float(tariff.price_per_km)
    price += (elapsed // 60) * 200  # vaqt bonusi

    return JsonResponse({
        'ok': True,
        'fixed': False,
        'price': round(price),
        'distance_km': round(dist, 2) if dist else 0,
        'elapsed': elapsed,
    })


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
@driver_login_required
@require_POST
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


# ── SOS ──────────────────────────────────────────────────────────────────────

@driver_login_required
@require_POST
def driver_sos_send(request, driver):
    import json as _json
    from .models import SosAlert
    from .utils import tg_sos_alert
    try:
        data = _json.loads(request.body)
    except Exception:
        data = {}
    lat     = data.get('lat')
    lng     = data.get('lng')
    address = data.get('address', '').strip()
    note    = data.get('note', '').strip()
    alert = SosAlert.objects.create(
        driver=driver,
        latitude=float(lat) if lat is not None else None,
        longitude=float(lng) if lng is not None else None,
        address=address,
        note=note,
    )
    tg_sos_alert(alert)
    return JsonResponse({'ok': True, 'id': alert.id})


# ── Surge: hozirgi narx multiplikatori ───────────────────────────────────────
@driver_login_required
def driver_surge_info(request, driver):
    """Hozirgi surge (narx oshishi) ma'lumotini qaytaradi."""
    from .utils import get_surge_multiplier
    multiplier, reason = get_surge_multiplier()
    return JsonResponse({'ok': True, 'multiplier': multiplier, 'reason': reason})
