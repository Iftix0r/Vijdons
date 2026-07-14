from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .models import Order, Driver, Client


# ── Order ──────────────────────────────────────────────────────────────────────

def order_create(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()
        from_address = request.POST.get('from_address', '').strip()
        to_address   = request.POST.get('to_address', '').strip()
        driver_id    = request.POST.get('driver_id') or None

        if phone_number and from_address and to_address:
            client, _ = Client.objects.get_or_create(phone_number=phone_number)
            driver = Driver.objects.filter(pk=driver_id).first() if driver_id else None
            Order.objects.create(
                client=client,
                from_address=from_address,
                to_address=to_address,
                driver=driver,
                status='pending',
            )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:panel_dashboard'))


def order_update_status(request, pk):
    """Change status or assign driver via POST."""
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
            )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


def driver_delete(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        driver.delete()
    return redirect('taxi:driver_list')


def driver_toggle_active(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        driver.is_active = not driver.is_active
        driver.save()
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
    context = {
        'orders':         orders,
        'total_orders':   Order.objects.count(),
        'total_drivers':  Driver.objects.filter(is_active=True).count(),
        'total_clients':  Client.objects.count(),
        'pending_orders': Order.objects.filter(status='pending').count(),
        'completed_orders': Order.objects.filter(status='completed').count(),
        'active_drivers': Driver.objects.filter(is_active=True),
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
        'drivers':  Driver.objects.filter(is_active=True),
        'q':        q,
        'status':   status,
        'statuses': Order.STATUS_CHOICES,
    }
    return render(request, 'taxi/order_list.html', context)


def driver_list(request):
    q = request.GET.get('q', '').strip()
    qs = Driver.objects.all()
    if q:
        qs = qs.filter(
            Q(full_name__icontains=q) |
            Q(phone_number__icontains=q) |
            Q(car_model__icontains=q) |
            Q(car_number__icontains=q)
        )
    return render(request, 'taxi/driver_list.html', {'drivers': qs, 'q': q})


def client_list(request):
    q = request.GET.get('q', '').strip()
    qs = Client.objects.all()
    if q:
        qs = qs.filter(
            Q(full_name__icontains=q) |
            Q(phone_number__icontains=q)
        )
    return render(request, 'taxi/client_list.html', {'clients': qs, 'q': q})
