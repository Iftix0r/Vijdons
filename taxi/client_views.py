"""
Yo'lovchi (mijoz) Web UI views — WebView ilovasi uchun.
URL prefix: /client/
"""
import json
from decimal import Decimal
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Client, Order, TariffSettings
from .serializers import ClientRegisterSerializer
from .utils import haversine, dispatch_order, tg_new_order, log_panel_event

ACTIVE_STATUSES = ('pending', 'accepted', 'on_way', 'arrived')


# ── Auth decorator ───────────────────────────────────────────────────────────

def client_login_required(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('client:login')
        try:
            client = request.user.client_profile
        except Client.DoesNotExist:
            return redirect('client:login')
        if client.is_blocked:
            return render(request, 'client/blocked.html', {'client': client})
        return fn(request, client, *args, **kwargs)
    return wrapper


def _active_order(client):
    return (
        Order.objects.select_related('driver')
        .filter(client=client, status__in=ACTIVE_STATUSES)
        .order_by('-created_at')
        .first()
    )


def _order_data(order):
    driver = order.driver
    driver_distance_km = None
    driver_eta_minutes = None
    if driver and driver.latitude is not None and driver.longitude is not None and order.from_lat and order.from_lng:
        d = haversine(driver.latitude, driver.longitude, order.from_lat, order.from_lng)
        if d is not None:
            driver_distance_km = round(d, 2)
            driver_eta_minutes = max(1, round(d / 30 * 60))
    return {
        'id':               order.id,
        'status':           order.status,
        'status_label':     order.get_status_display(),
        'from_address':     order.from_address,
        'to_address':       order.to_address,
        'price':            str(order.price) if order.price else None,
        'distance_km':      order.distance_km,
        'payment_type':     order.payment_type,
        'car_type':         order.car_type,
        'car_type_display': order.get_car_type_display(),
        'note':             order.note or '',
        'created_at':       order.created_at.isoformat() if order.created_at else None,
        'driver': {
            'full_name':  driver.full_name,
            'phone':      driver.phone_number,
            'car_model':  driver.car_model,
            'car_number': driver.car_number,
            'rating':     str(driver.rating),
            'distance_km': driver_distance_km,
            'eta_minutes': driver_eta_minutes,
        } if driver else None,
    }


# ── Auth ──────────────────────────────────────────────────────────────────────

def client_login_view(request):
    if request.user.is_authenticated and hasattr(request.user, 'client_profile'):
        return redirect('client:home')
    error = None
    if request.method == 'POST':
        phone    = request.POST.get('phone_number', '').strip()
        password = request.POST.get('password', '')
        user     = authenticate(request, username=phone, password=password)
        if user is None:
            error = "Telefon raqami yoki parol noto'g'ri."
        else:
            try:
                client = user.client_profile
            except Client.DoesNotExist:
                error = "Yo'lovchi profili topilmadi."
            else:
                if client.is_blocked:
                    error = "Hisobingiz bloklangan. Operator bilan bog'laning."
                else:
                    login(request, user)
                    return redirect('client:home')
    return render(request, 'client/login.html', {'error': error})


def client_logout_view(request):
    logout(request)
    return redirect('client:login')


def client_register_view(request):
    error = None
    if request.method == 'POST':
        data = {
            'full_name':    request.POST.get('full_name', ''),
            'phone_number': request.POST.get('phone_number', ''),
            'password':     request.POST.get('password', ''),
        }
        s = ClientRegisterSerializer(data=data)
        if s.is_valid():
            client = s.save()
            user = authenticate(request, username=data['phone_number'], password=data['password'])
            if user is not None:
                login(request, user)
                return redirect('client:home')
            return redirect('client:login')
        error = ' '.join([str(v[0]) for v in s.errors.values()])
    return render(request, 'client/register.html', {'error': error})


# ── Home / Order ──────────────────────────────────────────────────────────────

@client_login_required
def client_home(request, client):
    order = _active_order(client)
    tariff = TariffSettings.get()
    return render(request, 'client/home.html', {
        'client':            client,
        'active_tab':        'home',
        'active_order':      order,
        'active_order_json': json.dumps(_order_data(order), ensure_ascii=False) if order else 'null',
        'tariff_base_price': int(tariff.base_price),
        'tariff_per_km':     int(tariff.price_per_km),
        'operator_phone':    tariff.operator_phone,
        'car_type_choices':  [c for c in Order._meta.get_field('car_type').choices],
    })


@client_login_required
@require_POST
def client_order_create(request, client):
    if _active_order(client):
        return JsonResponse({'ok': False, 'error': 'Sizda allaqachon faol buyurtma bor.'}, status=400)
    if client.is_blocked:
        return JsonResponse({'ok': False, 'error': 'Hisobingiz bloklangan.'}, status=403)

    from_address = request.POST.get('from_address', '').strip()
    to_address   = request.POST.get('to_address', '').strip()
    if not from_address:
        return JsonResponse({'ok': False, 'error': "Qayerdan ekanligini belgilang."}, status=400)

    def _f(name):
        v = request.POST.get(name)
        try:
            return float(v) if v not in (None, '') else None
        except ValueError:
            return None

    f_lat, f_lng = _f('from_lat'), _f('from_lng')
    t_lat, t_lng = _f('to_lat'), _f('to_lng')

    tariff = TariffSettings.get()
    distance_km = None
    price = None
    if f_lat and f_lng and t_lat and t_lng:
        distance_km = haversine(f_lat, f_lng, t_lat, t_lng)
        if distance_km:
            price = tariff.calc_price(distance_km)

    payment_type = request.POST.get('payment_type', 'cash')
    car_type     = request.POST.get('car_type', 'light')
    note         = request.POST.get('note', '').strip()

    order = Order.objects.create(
        client=client,
        from_address=from_address, from_lat=f_lat, from_lng=f_lng,
        to_address=to_address, to_lat=t_lat, to_lng=t_lng,
        distance_km=distance_km, price=price,
        commission=tariff.commission,
        payment_type=payment_type, car_type=car_type, note=note,
        status='pending',
    )

    tg_new_order(order)

    has_coords = bool(f_lat and f_lng)
    if has_coords and tariff.auto_dispatch:
        import threading
        threading.Thread(target=dispatch_order, args=(order,), daemon=True).start()

    return JsonResponse({'ok': True, 'order': _order_data(order)})


@client_login_required
def client_order_status(request, client, pk):
    order = get_object_or_404(Order, pk=pk, client=client)
    return JsonResponse(_order_data(order))


@client_login_required
def client_active_order_poll(request, client):
    order = _active_order(client)
    if not order:
        return JsonResponse({'active': False})
    data = _order_data(order)
    data['active'] = True
    return JsonResponse(data)


@client_login_required
@require_POST
def client_order_cancel(request, client, pk):
    order = get_object_or_404(Order, pk=pk, client=client)
    if order.status != 'pending':
        tariff = TariffSettings.get()
        return JsonResponse(
            {'ok': False, 'error': f"Haydovchi qabul qilgan buyurtmani bekor qilish uchun operatorga qo'ng'iroq qiling: {tariff.operator_phone}"},
            status=400,
        )
    order.status = 'cancelled'
    order.save(update_fields=['status', 'updated_at'])
    log_panel_event('panel_order_cancelled', f"Buyurtma #{order.id} — mijoz bekor qildi")
    return JsonResponse({'ok': True})


# ── History ───────────────────────────────────────────────────────────────────

@client_login_required
def client_history(request, client):
    orders = (
        Order.objects.select_related('driver')
        .filter(client=client)
        .exclude(status__in=ACTIVE_STATUSES)
        .order_by('-created_at')[:100]
    )
    return render(request, 'client/history.html', {
        'client':     client,
        'active_tab': 'history',
        'orders':     orders,
    })


# ── Profile ───────────────────────────────────────────────────────────────────

@client_login_required
def client_profile(request, client):
    return render(request, 'client/profile.html', {
        'client':     client,
        'active_tab': 'profile',
    })


@client_login_required
@require_POST
def client_profile_update(request, client):
    full_name = request.POST.get('full_name', '').strip()
    if full_name:
        client.full_name = full_name
        client.save(update_fields=['full_name'])
    return JsonResponse({'ok': True})


@client_login_required
@require_POST
def client_profile_password(request, client):
    old = request.POST.get('old_password', '')
    new = request.POST.get('new_password', '')
    if not client.user:
        return JsonResponse({'ok': False, 'error': 'Foydalanuvchi topilmadi'}, status=400)
    if not client.user.check_password(old):
        return JsonResponse({'ok': False, 'error': "Eski parol noto'g'ri"}, status=400)
    if len(new) < 6:
        return JsonResponse({'ok': False, 'error': "Parol kamida 6 ta belgi bo'lishi kerak"}, status=400)
    client.user.set_password(new)
    client.user.save()
    from django.contrib.auth import update_session_auth_hash
    update_session_auth_hash(request, client.user)
    return JsonResponse({'ok': True})
