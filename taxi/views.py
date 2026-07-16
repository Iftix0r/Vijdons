from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from .models import Order, Driver, Client, TariffSettings, ChatMessage, MapsSettings
from .utils import haversine, find_nearest_driver, send_telegram, dispatch_order


# ── Order ──────────────────────────────────────────────────────────────────────

def order_create(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        from_address = request.POST.get('from_address', '').strip()
        to_address   = request.POST.get('to_address', '').strip()
        driver_id    = request.POST.get('driver_id') or None

        from_lat = request.POST.get('from_lat')
        from_lng = request.POST.get('from_lng')
        to_lat   = request.POST.get('to_lat')
        to_lng   = request.POST.get('to_lng')

        if phone_number and from_address:
            tariff = TariffSettings.get()
            client, _ = Client.objects.get_or_create(phone_number=phone_number)
            driver = Driver.objects.filter(pk=driver_id).first() if driver_id else None

            f_lat = float(from_lat) if from_lat else None
            f_lng = float(from_lng) if from_lng else None
            t_lat = float(to_lat) if to_lat else None
            t_lng = float(to_lng) if to_lng else None

            distance_km = None
            price = None
            if f_lat and f_lng and t_lat and t_lng:
                distance_km = haversine(f_lat, f_lng, t_lat, t_lng)
                if distance_km:
                    price = tariff.calc_price(distance_km)

            # Avtomatik taqsimlash
            if driver is None and tariff.auto_dispatch and f_lat and f_lng:
                active_drivers = Driver.objects.filter(
                    is_active=True, is_on_duty=True,
                    approval_status=Driver.APPROVAL_APPROVED
                )
                nearest_driver, _ = find_nearest_driver(active_drivers, f_lat, f_lng)
                if nearest_driver:
                    driver = nearest_driver

            payment_type = request.POST.get('payment_type', 'cash')
            note         = request.POST.get('note', '').strip()

            order = Order.objects.create(
                client=client,
                from_address=from_address,
                from_lat=f_lat, from_lng=f_lng,
                to_address=to_address,
                to_lat=t_lat, to_lng=t_lng,
                distance_km=distance_km,
                price=price,
                commission=tariff.commission,
                driver=driver,
                payment_type=payment_type,
                note=note,
                status='pending',
            )

            # Telegram xabar
            driver_txt = driver.full_name if driver else 'Biriktirilmagan'
            send_telegram(
                f"🚨 <b>Yangi buyurtma #{order.id}</b>\n"
                f"👤 Mijoz: {client.full_name or phone_number} ({phone_number})\n"
                f"📍 Manzil: {from_address}"
                + (f" → {to_address}" if to_address else "")
                + f"\n💰 Narx: {price or '—'} UZS | {distance_km and f'{distance_km:.1f} km' or '—'}\n"
                f"🚗 Haydovchi: {driver_txt}\n"
                f"💳 To'lov: {'Naqd' if payment_type == 'cash' else 'Karta'}"
                + (f"\n📝 Izoh: {note}" if note else "")
            )

            # Dispatch — eng yaqin haydovchiga yuborish
            import threading
            threading.Thread(target=dispatch_order, args=(order,), daemon=True).start()
    return redirect(request.META.get('HTTP_REFERER', 'taxi:panel_dashboard'))


def order_update_status(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        driver_id  = request.POST.get('driver_id') or None
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
        if driver_id:
            order.driver = Driver.objects.filter(pk=driver_id).first()
        order.save()
    return redirect(request.META.get('HTTP_REFERER', 'taxi:order_list'))


def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order.delete()
    return redirect('taxi:order_list')


# ── Driver ─────────────────────────────────────────────────────────────────────

def driver_create(request):
    if request.method == 'POST':
        full_name    = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        car_model    = request.POST.get('car_model', '').strip()
        car_number   = request.POST.get('car_number', '').strip()
        if full_name and phone_number:
            Driver.objects.create(
                full_name=full_name,
                phone_number=phone_number,
                car_model=car_model,
                car_number=car_number,
                approval_status=Driver.APPROVAL_APPROVED,
                is_active=True,
            )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


def driver_delete(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        if driver.user:
            driver.user.delete()
        else:
            driver.delete()
    return redirect('taxi:driver_list')


def driver_toggle_active(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        driver.is_active = not driver.is_active
        driver.save(update_fields=['is_active'])
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


def driver_approve(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'approve':
            driver.approval_status = Driver.APPROVAL_APPROVED
            driver.is_active = True
            if driver.user:
                driver.user.is_active = True
                driver.user.save(update_fields=['is_active'])
        elif action == 'reject':
            driver.approval_status = Driver.APPROVAL_REJECTED
            driver.is_active = False
        driver.save(update_fields=['approval_status', 'is_active'])
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


def driver_recharge(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        from decimal import Decimal
        try:
            amount = Decimal(amount)
            driver.balance += amount
            driver.save(update_fields=['balance'])
        except (ValueError, TypeError, Exception):
            pass
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


# ── Client ─────────────────────────────────────────────────────────────────────

def client_create(request):
    if request.method == 'POST':
        full_name    = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        if phone_number:
            Client.objects.get_or_create(
                phone_number=phone_number,
                defaults={'full_name': full_name},
            )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:client_list'))


def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.delete()
    return redirect('taxi:client_list')


# ── Pages ──────────────────────────────────────────────────────────────────────

def panel_dashboard(request):
    orders = Order.objects.select_related('client', 'driver').order_by('-created_at')[:10]
    pending_drivers = Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).order_by('-registered_at')
    on_duty_drivers = Driver.objects.filter(
        is_active=True, is_on_duty=True, approval_status=Driver.APPROVAL_APPROVED
    ).count()
    context = {
        'orders':               orders,
        'total_orders':         Order.objects.count(),
        'total_drivers':        Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED).count(),
        'on_duty_drivers':      on_duty_drivers,
        'total_clients':        Client.objects.count(),
        'pending_orders':       Order.objects.filter(status='pending').count(),
        'completed_orders':     Order.objects.filter(status='completed').count(),
        'active_drivers':       Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED),
        'pending_drivers':      pending_drivers,
        'pending_driver_count': pending_drivers.count(),
        'tariff':               TariffSettings.get(),
    }
    return render(request, 'taxi/panel.html', context)


def order_list(request):
    qs = Order.objects.select_related('client', 'driver').order_by('-created_at')
    q      = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    if q:
        qs = qs.filter(
            Q(client__full_name__icontains=q) |
            Q(client__phone_number__icontains=q) |
            Q(from_address__icontains=q) |
            Q(to_address__icontains=q) |
            Q(driver__full_name__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    context = {
        'orders':   qs,
        'drivers':  Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED),
        'q':        q,
        'status':   status,
        'statuses': Order.STATUS_CHOICES,
    }
    return render(request, 'taxi/order_list.html', context)


def driver_list(request):
    q   = request.GET.get('q', '').strip()
    tab = request.GET.get('tab', 'approved')
    qs  = Driver.objects.all()
    if q:
        qs = qs.filter(
            Q(full_name__icontains=q) |
            Q(phone_number__icontains=q) |
            Q(car_model__icontains=q) |
            Q(car_number__icontains=q)
        )
    if tab == 'pending':
        qs = qs.filter(approval_status=Driver.APPROVAL_PENDING)
    elif tab == 'rejected':
        qs = qs.filter(approval_status=Driver.APPROVAL_REJECTED)
    else:
        qs = qs.filter(approval_status=Driver.APPROVAL_APPROVED)

    return render(request, 'taxi/driver_list.html', {
        'drivers':        qs,
        'q':              q,
        'tab':            tab,
        'pending_count':  Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).count(),
        'approved_count': Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).count(),
        'rejected_count': Driver.objects.filter(approval_status=Driver.APPROVAL_REJECTED).count(),
    })


def client_list(request):
    q  = request.GET.get('q', '').strip()
    qs = Client.objects.all()
    if q:
        qs = qs.filter(
            Q(full_name__icontains=q) |
            Q(phone_number__icontains=q)
        )
    return render(request, 'taxi/client_list.html', {'clients': qs, 'q': q})


# ── Tariff Settings ────────────────────────────────────────────────────────────

def maps_settings(request):
    maps = MapsSettings.get()
    if request.method == 'POST':
        maps.provider  = request.POST.get('provider', maps.provider)
        maps.api_key   = request.POST.get('api_key', '').strip()
        maps.is_active = request.POST.get('is_active') == 'on'
        maps.save()
        return redirect('taxi:maps_settings')
    return render(request, 'taxi/maps_settings.html', {'maps': maps})


def tariff_settings(request):
    tariff = TariffSettings.get()
    if request.method == 'POST':
        from decimal import Decimal, InvalidOperation
        try:
            tariff.base_price   = Decimal(request.POST.get('base_price', tariff.base_price))
            tariff.price_per_km = Decimal(request.POST.get('price_per_km', tariff.price_per_km))
            tariff.commission   = Decimal(request.POST.get('commission', tariff.commission))
            tariff.auto_dispatch = request.POST.get('auto_dispatch') == 'on'
            tariff.max_dispatch_attempts = int(request.POST.get('max_dispatch_attempts', tariff.max_dispatch_attempts))
            tariff.dispatch_timeout      = int(request.POST.get('dispatch_timeout', tariff.dispatch_timeout))
            tariff.save()
        except (InvalidOperation, ValueError):
            pass
        return redirect('taxi:tariff_settings')
    return render(request, 'taxi/tariff_settings.html', {'tariff': tariff})


def driver_map(request):
    drivers = Driver.objects.filter(
        is_active=True,
        is_on_duty=True,
        approval_status=Driver.APPROVAL_APPROVED
    )
    return render(request, 'taxi/driver_map.html', {'drivers': drivers})


def active_drivers_locations(request):
    drivers = Driver.objects.filter(
        is_active=True,
        is_on_duty=True,
        approval_status=Driver.APPROVAL_APPROVED,
        latitude__isnull=False,
        longitude__isnull=False
    )
    data = []
    for d in drivers:
        data.append({
            'id': d.id,
            'full_name': d.full_name,
            'phone_number': d.phone_number,
            'car_model': d.car_model,
            'car_number': d.car_number,
            'latitude': d.latitude,
            'longitude': d.longitude,
            'balance': str(d.balance),
        })
    return JsonResponse({'drivers': data})


# ── Operator Chat ──────────────────────────────────────────────────────────────────

def operator_chat(request):
    drivers = Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).order_by('full_name')
    driver_data = []
    for d in drivers:
        last_msg = ChatMessage.objects.filter(driver=d).order_by('-created_at').first()
        unread   = ChatMessage.objects.filter(driver=d, sender=ChatMessage.SENDER_DRIVER, is_read=False).count()
        driver_data.append({'driver': d, 'last_msg': last_msg, 'unread': unread})

    selected_id     = request.GET.get('driver_id')
    selected_driver = None
    messages        = []
    if selected_id:
        selected_driver = Driver.objects.filter(pk=selected_id).first()
        if selected_driver:
            ChatMessage.objects.filter(
                driver=selected_driver, sender=ChatMessage.SENDER_DRIVER, is_read=False
            ).update(is_read=True)
            messages = ChatMessage.objects.filter(driver=selected_driver).order_by('created_at')

    if request.method == 'POST' and selected_driver:
        text = request.POST.get('text', '').strip()
        if text:
            ChatMessage.objects.create(
                driver=selected_driver, sender=ChatMessage.SENDER_OPERATOR, text=text
            )
            _send_fcm_to_driver(selected_driver, '💬 Operator', text)
        return redirect(f"{request.path}?driver_id={selected_id}")

    return render(request, 'taxi/operator_chat.html', {
        'driver_data':     driver_data,
        'selected_driver': selected_driver,
        'messages':        messages,
        'selected_id':     selected_id,
    })


def operator_chat_unread(request):
    """AJAX: jami o'qilmagan xabarlar soni."""
    count = ChatMessage.objects.filter(sender=ChatMessage.SENDER_DRIVER, is_read=False).count()
    return JsonResponse({'unread': count})


def _send_fcm_to_driver(driver, title, body):
    import urllib.request, json
    from django.conf import settings
    fcm_key = getattr(settings, 'FCM_SERVER_KEY', '')
    if not fcm_key or not driver.fcm_token:
        return
    try:
        data = json.dumps({
            'to': driver.fcm_token,
            'notification': {'title': title, 'body': body, 'sound': 'default'},
            'data': {'type': 'chat'},
        }).encode()
        req = urllib.request.Request(
            'https://fcm.googleapis.com/fcm/send',
            data=data,
            headers={'Authorization': f'key={fcm_key}', 'Content-Type': 'application/json'},
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception:
        pass
