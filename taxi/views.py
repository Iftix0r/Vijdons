from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .models import Order, Driver, Client
from .utils import haversine, find_nearest_driver


# ── Order ──────────────────────────────────────────────────────────────────────

def order_create(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        from_address = request.POST.get('from_address', '').strip()
        to_address   = request.POST.get('to_address', '').strip()
        driver_id    = request.POST.get('driver_id') or None
        commission   = request.POST.get('commission')
        
        commission = float(commission) if commission else 1000.0
        
        from_lat = request.POST.get('from_lat')
        from_lng = request.POST.get('from_lng')
        to_lat   = request.POST.get('to_lat')
        to_lng   = request.POST.get('to_lng')

        if phone_number and from_address and to_address:
            client, _ = Client.objects.get_or_create(phone_number=phone_number)
            driver = Driver.objects.filter(pk=driver_id).first() if driver_id else None
            
            # Convert to float
            f_lat = float(from_lat) if from_lat else None
            f_lng = float(from_lng) if from_lng else None
            t_lat = float(to_lat) if to_lat else None
            t_lng = float(to_lng) if to_lng else None
            
            distance_km = None
            price = None
            if f_lat and f_lng and t_lat and t_lng:
                distance_km = haversine(f_lat, f_lng, t_lat, t_lng)
                if distance_km:
                    # Example: 3000 UZS base + 1500 UZS per km
                    price = 3000 + (distance_km * 1500)
            
            if driver is None and f_lat and f_lng:
                active_drivers = Driver.objects.filter(is_active=True, is_on_duty=True, approval_status=Driver.APPROVAL_APPROVED)
                nearest_driver, _ = find_nearest_driver(active_drivers, f_lat, f_lng)
                if nearest_driver:
                    driver = nearest_driver

            Order.objects.create(
                client=client,
                from_address=from_address,
                from_lat=f_lat,
                from_lng=f_lng,
                to_address=to_address,
                to_lat=t_lat,
                to_lng=t_lng,
                distance_km=distance_km,
                price=price,
                commission=commission,
                driver=driver,
                status='pending' if not driver else 'accepted',
            )
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
        try:
            amount = float(amount)
            driver.balance += amount
            driver.save(update_fields=['balance'])
        except (ValueError, TypeError):
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
    context = {
        'orders':               orders,
        'total_orders':         Order.objects.count(),
        'total_drivers':        Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED).count(),
        'total_clients':        Client.objects.count(),
        'pending_orders':       Order.objects.filter(status='pending').count(),
        'completed_orders':     Order.objects.filter(status='completed').count(),
        'active_drivers':       Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED),
        'pending_drivers':      pending_drivers,
        'pending_driver_count': pending_drivers.count(),
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
