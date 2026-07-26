from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from .models import Order, Driver, Client, TariffSettings, ChatMessage, MapsSettings, DriverActivityLog, BotSettings, BotAdmin, SosAlert, BalanceLog, BalanceTopupRequest, GroupMessage, PanelEvent, PanelSound, SmsSettings, AiSettings, AiRewardLog, Task, ContractSettings, DriverContractSignature, FlyerVoucher
from .utils import haversine, find_nearest_driver, send_telegram, dispatch_order, tg_new_order, tg_driver_registered, tg_driver_approved, tg_driver_rejected, tg_driver_blocked, tg_driver_unblocked, tg_balance_changed, tg_order_cancelled, log_panel_event, reverse_geocode_address, sms_order_status, send_sms, generate_growth_insights, build_contract_pdf, build_flyer_pdf, generate_voucher_codes, tg_flyer_voucher_redeemed
import csv

ONLINE_THRESHOLD_SECONDS = 120  # last_seen shundan yangi bo'lsa — online (yashil)
PENDING_ORDER_AGING_SECONDS = 120  # buyurtma shuncha vaqt haydovchisiz tursa — operator e'tiboriga chiqadi


def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ── Order ──────────────────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('client', 'driver', 'dispatched_to')
             .prefetch_related('rejected_by'),
        pk=pk
    )
    client_orders = Order.objects.filter(client=order.client).order_by('-created_at')[:10]
    return render(request, 'taxi/order_detail.html', {
        'order':         order,
        'client_orders': client_orders,
        'drivers':       Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED),
    })


@login_required(login_url='taxi:panel_login')
def client_detail(request, pk):
    from django.db.models import Sum, Count
    client = get_object_or_404(Client, pk=pk)
    orders = Order.objects.filter(client=client).select_related('driver').order_by('-created_at')
    stats = orders.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status='completed')),
        cancelled=Count('id', filter=Q(status='cancelled')),
        total_spent=Sum('price', filter=Q(status='completed')),
    )
    return render(request, 'taxi/client_detail.html', {
        'client': client,
        'orders': orders,
        'stats':  stats,
    })


@login_required(login_url='taxi:panel_login')
def order_create(request):
    if request.method == 'POST':
        phone_number  = request.POST.get('phone_number', '').strip()
        customer_name = request.POST.get('customer_name', '').strip()
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
            if client.is_blocked:
                from django.contrib import messages
                messages.error(request, f"🚫 {client.full_name or phone_number} — bloklangan mijoz! Buyurtma berish uchun avval blokdan chiqaring.")
                return redirect(request.META.get('HTTP_REFERER', 'taxi:order_list'))
            if customer_name and not client.full_name:
                client.full_name = customer_name
                client.save(update_fields=['full_name'])
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

            # Avtomatik taqsimlash — FAQAT haritadan koordinata belgilangan bo'lsa
            # Manzil qo'lda yozilsa (from_lat yo'q) → umumiy tabloga tushadi, hammaga ko'rinadi
            has_coords = bool(f_lat and f_lng)
            if driver is None and tariff.auto_dispatch and has_coords:
                pass  # dispatch_order() thread ichida eng yaqinga yuboradi

            payment_type = request.POST.get('payment_type', 'cash')
            car_type     = request.POST.get('car_type', Driver.CAR_TYPE_LIGHT)
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
                car_type=car_type,
                note=note,
                status='pending',
            )

            # Telegram xabar
            tg_new_order(order)

            # Dispatch — faqat koordinata belgilangan bo'lsa eng yaqin haydovchiga yuboriladi
            # Koordinata yo'q (qo'lda yozilgan manzil) → umumiy tabloda qoladi, hammaga ko'rinadi
            if has_coords and driver is None:
                import threading
                threading.Thread(target=dispatch_order, args=(order,), daemon=True).start()
    return redirect(request.META.get('HTTP_REFERER', 'taxi:panel_dashboard'))


@login_required(login_url='taxi:panel_login')
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
        if new_status in ('accepted', 'arrived', 'completed', 'cancelled'):
            sms_order_status(order, new_status)
        # Haydovchiga FCM yuborish — buyurtma bekor qilinsa yoki yakunlansa
        if new_status in ('cancelled', 'completed') and order.driver:
            from .utils import send_fcm
            send_fcm(
                order.driver.fcm_token,
                title='Buyurtma holati o\'zgardi',
                body=f'Buyurtma #{order.id} — {order.get_status_display()}',
                data={'type': 'order_update', 'order_id': str(order.id), 'status': new_status},
            )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:order_list'))


@login_required(login_url='taxi:panel_login')
def order_cancel_reassign(request, pk):
    """Haydovchi operatorga qo'ng'iroq qilib buyurtmani bekor qilishni so'raganda
    ishlatiladi: haydovchidan yechilgan komissiya unga qaytariladi, buyurtma undan
    yechib olinib qayta 'kutilmoqda' holatiga o'tkaziladi — shu bilan boshqa
    haydovchilar uni qabul qilishi mumkin bo'ladi."""
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST' and order.driver_id and order.status in ('accepted', 'on_way', 'arrived'):
        from decimal import Decimal
        from .utils import send_fcm

        old_driver = order.driver
        commission = order.commission or TariffSettings.get().commission
        old_driver.balance += Decimal(str(commission))
        old_driver.save(update_fields=['balance'])
        BalanceLog.objects.create(
            driver=old_driver, action=BalanceLog.ACTION_ADD, amount=commission,
            balance_after=old_driver.balance,
            note=f"Komissiya qaytarildi — buyurtma #{order.id} operator tomonidan bekor qilindi",
        )

        order.rejected_by.add(old_driver)
        order.driver = None
        order.dispatched_to = None
        order.dispatched_at = None
        order.status = 'pending'
        order.save(update_fields=['driver', 'dispatched_to', 'dispatched_at', 'status', 'updated_at'])

        log_panel_event('panel_order_cancelled', f"Buyurtma #{order.id} — {old_driver.full_name} dan bekor qilindi, qayta ochildi")
        send_fcm(
            old_driver.fcm_token,
            title='Buyurtma bekor qilindi',
            body=f"Buyurtma #{order.id} operator tomonidan bekor qilindi. {commission} so'm balansingizga qaytarildi.",
            data={'type': 'order_cancelled', 'order_id': str(order.id)},
        )

        tariff = TariffSettings.get()
        if tariff.auto_dispatch:
            import threading
            threading.Thread(target=dispatch_order, args=(order,), daemon=True).start()

        messages.success(
            request,
            f"Buyurtma #{order.id} bekor qilindi — {old_driver.full_name}ga {commission} so'm qaytarildi, buyurtma qayta ochildi.",
        )
    return redirect(request.META.get('HTTP_REFERER', 'taxi:order_list'))


@login_required(login_url='taxi:panel_login')
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        log_panel_event('panel_order_deleted', f"Buyurtma #{order.id} — {order.from_address}")
        order.delete()
    return redirect('taxi:order_list')


# ── Driver ─────────────────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def driver_create(request):
    if request.method == 'POST':
        full_name    = request.POST.get('full_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        car_model    = request.POST.get('car_model', '').strip()
        car_number   = request.POST.get('car_number', '').strip()
        car_type     = request.POST.get('car_type', Driver.CAR_TYPE_LIGHT)
        if full_name and phone_number:
            driver = Driver.objects.create(
                full_name=full_name,
                phone_number=phone_number,
                car_model=car_model,
                car_number=car_number,
                car_type=car_type,
                approval_status=Driver.APPROVAL_APPROVED,
                is_active=True,
            )
            tg_driver_registered(driver)
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


@login_required(login_url='taxi:panel_login')
def driver_delete(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        if driver.user:
            driver.user.delete()
        else:
            driver.delete()
    return redirect('taxi:driver_list')


@login_required(login_url='taxi:panel_login')
def driver_toggle_active(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        driver.is_active = not driver.is_active
        driver.save(update_fields=['is_active'])
        action = DriverActivityLog.ACTION_UNBLOCK if driver.is_active else DriverActivityLog.ACTION_BLOCK
        detail = 'Admin tomonidan ' + ('blok ochildi' if driver.is_active else 'bloklandi')
        DriverActivityLog.objects.create(driver=driver, action=action, detail=detail,
            ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''))
        if driver.is_active:
            tg_driver_unblocked(driver)
        else:
            tg_driver_blocked(driver)
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


@login_required(login_url='taxi:panel_login')
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
            tg_driver_approved(driver)
        elif action == 'reject':
            driver.approval_status = Driver.APPROVAL_REJECTED
            driver.is_active = False
            tg_driver_rejected(driver)
        driver.save(update_fields=['approval_status', 'is_active'])
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


@login_required(login_url='taxi:panel_login')
def driver_recharge(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        amount = request.POST.get('amount')
        action = request.POST.get('action', 'add')
        from decimal import Decimal
        try:
            amount = Decimal(amount)
            if action == 'deduct':
                driver.balance -= amount
                detail = f"-{amount} UZS (admin ayirdi)"
            else:
                driver.balance += amount
                detail = f"+{amount} UZS (admin qo'shdi)"
            driver.save(update_fields=['balance'])
            BalanceLog.objects.create(
                driver=driver, action=action, amount=amount,
                balance_after=driver.balance, note=request.POST.get('note', '')
            )
            DriverActivityLog.objects.create(driver=driver, action=DriverActivityLog.ACTION_BALANCE, detail=detail,
                ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''))
            tg_balance_changed(driver, amount, action)
        except (ValueError, TypeError, Exception):
            pass
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


# ── Driver Detail ─────────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def driver_detail(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    logs   = driver.activity_logs.all()[:100]
    orders = driver.orders.select_related('client').order_by('-created_at')[:20]
    contract = ContractSettings.get()
    contract_signature = driver.contract_signatures.filter(version=contract.version).first()
    return render(request, 'taxi/driver_detail.html', {
        'driver': driver,
        'logs':   logs,
        'orders': orders,
        'contract_signature': contract_signature,
    })


# ── Client ─────────────────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
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


@login_required(login_url='taxi:panel_login')
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.delete()
    return redirect('taxi:client_list')


@login_required(login_url='taxi:panel_login')
def client_block_toggle(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.is_blocked = not client.is_blocked
        client.save(update_fields=['is_blocked'])
    return redirect('taxi:client_list')


# ── Pages ──────────────────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def panel_dashboard(request):
    from django.utils import timezone
    from django.db.models import Sum, Avg, Count
    from decimal import Decimal

    today = timezone.now().date()
    online_threshold = timezone.now() - timezone.timedelta(minutes=2)
    aging_cutoff = timezone.now() - timezone.timedelta(seconds=PENDING_ORDER_AGING_SECONDS)
    orders = Order.objects.select_related('client', 'driver').order_by('-created_at')[:10]
    aging_orders = Order.objects.select_related('client').filter(
        status='pending', created_at__lte=aging_cutoff
    ).order_by('created_at')
    pending_drivers = Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).order_by('-registered_at')
    on_duty_drivers = Driver.objects.filter(
        is_active=True, is_on_duty=True, approval_status=Driver.APPROVAL_APPROVED
    ).count()
    online_drivers = Driver.objects.filter(
        is_active=True, approval_status=Driver.APPROVAL_APPROVED,
        last_seen__gte=online_threshold
    ).count()

    completed_qs = Order.objects.filter(status='completed')
    today_qs     = Order.objects.filter(created_at__date=today)

    total_revenue   = completed_qs.aggregate(s=Sum('price'))['s'] or Decimal('0')
    today_revenue   = today_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or Decimal('0')
    today_orders    = today_qs.count()
    avg_price       = completed_qs.aggregate(a=Avg('price'))['a'] or Decimal('0')
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    all_orders_count = Order.objects.count()
    cancellation_rate = round(cancelled_orders / all_orders_count * 100, 1) if all_orders_count else 0

    # So'nggi 7 kunlik statistika (grafik uchun)
    from datetime import timedelta
    weekly_labels, weekly_revenue, weekly_counts = [], [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_qs = Order.objects.filter(created_at__date=day)
        weekly_labels.append(day.strftime('%d/%m'))
        weekly_revenue.append(float(day_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0))
        weekly_counts.append(day_qs.count())

    # Shu hafta vs o'tgan hafta o'sish foizi (daromad va buyurtmalar soni)
    this_week_start = today - timedelta(days=6)
    last_week_start = this_week_start - timedelta(days=7)
    last_week_end    = this_week_start - timedelta(days=1)
    this_week_qs = Order.objects.filter(created_at__date__gte=this_week_start, created_at__date__lte=today)
    last_week_qs = Order.objects.filter(created_at__date__gte=last_week_start, created_at__date__lte=last_week_end)
    this_week_revenue = float(this_week_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0)
    last_week_revenue = float(last_week_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0)
    this_week_orders  = this_week_qs.count()
    last_week_orders  = last_week_qs.count()
    revenue_growth_pct = round((this_week_revenue - last_week_revenue) / last_week_revenue * 100, 1) if last_week_revenue else None
    orders_growth_pct  = round((this_week_orders - last_week_orders) / last_week_orders * 100, 1) if last_week_orders else None

    # Ogohlantirishlar: balansi kam va uzoq faol bo'lmagan haydovchilar
    tariff_for_alerts = TariffSettings.get()
    low_balance_drivers = Driver.objects.filter(
        is_active=True, approval_status=Driver.APPROVAL_APPROVED, balance__lt=tariff_for_alerts.commission
    ).order_by('balance')
    inactive_cutoff = timezone.now() - timedelta(days=3)
    inactive_drivers = Driver.objects.filter(
        is_active=True, approval_status=Driver.APPROVAL_APPROVED, is_on_duty=False
    ).filter(Q(last_seen__lt=inactive_cutoff) | Q(last_seen__isnull=True))

    context = {
        'orders':               orders,
        'total_orders':         Order.objects.count(),
        'total_drivers':        Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED).count(),
        'on_duty_drivers':      on_duty_drivers,
        'online_drivers':       online_drivers,
        'total_clients':        Client.objects.count(),
        'pending_orders':       Order.objects.filter(status='pending').count(),
        'completed_orders':     completed_qs.count(),
        'cancelled_orders':     cancelled_orders,
        'active_drivers':       Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED),
        'pending_drivers':      pending_drivers,
        'pending_driver_count': pending_drivers.count(),
        'aging_orders':         aging_orders,
        'aging_order_count':    aging_orders.count(),
        'aging_threshold_minutes': PENDING_ORDER_AGING_SECONDS // 60,
        'tariff':               TariffSettings.get(),
        'total_revenue':        total_revenue,
        'today_revenue':        today_revenue,
        'today_orders':         today_orders,
        'avg_price':            avg_price,
        'weekly_labels':        weekly_labels,
        'weekly_revenue':       weekly_revenue,
        'weekly_counts':        weekly_counts,
        'cancellation_rate':    cancellation_rate,
        'revenue_growth_pct':   revenue_growth_pct,
        'orders_growth_pct':    orders_growth_pct,
        'low_balance_drivers':  low_balance_drivers,
        'low_balance_driver_count': low_balance_drivers.count(),
        'inactive_drivers':     inactive_drivers,
        'inactive_driver_count': inactive_drivers.count(),
    }
    return render(request, 'taxi/panel.html', context)


@login_required(login_url='taxi:panel_login')
def aging_orders_count(request):
    from django.utils import timezone
    cutoff = timezone.now() - timezone.timedelta(seconds=PENDING_ORDER_AGING_SECONDS)
    count = Order.objects.filter(status='pending', created_at__lte=cutoff).count()
    return JsonResponse({'count': count})


@login_required(login_url='taxi:panel_login')
def order_list(request):
    qs = Order.objects.select_related('client', 'driver')
    q      = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')
    sort   = request.GET.get('sort', '').strip()
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

    if sort == 'top_price':
        qs = qs.order_by('-price', '-created_at')
    else:
        qs = qs.order_by('-created_at')

    context = {
        'orders':   qs,
        'drivers':  Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED),
        'q':        q,
        'status':   status,
        'sort':     sort,
        'statuses': Order.STATUS_CHOICES,
    }
    return render(request, 'taxi/order_list.html', context)


@login_required(login_url='taxi:panel_login')
def driver_list(request):
    from django.db.models import Case, When, Value, IntegerField
    from django.utils import timezone

    q    = request.GET.get('q', '').strip()
    tab  = request.GET.get('tab', 'approved')
    sort = request.GET.get('sort', '').strip()
    online_cutoff = timezone.now() - timezone.timedelta(seconds=ONLINE_THRESHOLD_SECONDS)
    qs  = Driver.objects.annotate(
        completed_count=Count('orders', filter=Q(orders__status='completed')),
        cancelled_count=Count('orders', filter=Q(orders__status='cancelled')),
        is_online=Case(
            When(last_seen__gte=online_cutoff, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
    )
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

    if sort == 'top_completed':
        qs = qs.order_by('-is_online', '-completed_count')
    elif sort == 'top_cancelled':
        qs = qs.order_by('-is_online', '-cancelled_count')
    elif sort == 'top_rating':
        qs = qs.order_by('-is_online', '-rating')
    elif sort == 'top_balance':
        qs = qs.order_by('-is_online', '-balance')
    elif sort == 'newest':
        qs = qs.order_by('-is_online', '-registered_at')
    else:
        qs = qs.order_by('-is_online', '-last_seen')

    return render(request, 'taxi/driver_list.html', {
        'drivers':        qs,
        'q':              q,
        'tab':            tab,
        'sort':           sort,
        'pending_count':  Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).count(),
        'approved_count': Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).count(),
        'rejected_count': Driver.objects.filter(approval_status=Driver.APPROVAL_REJECTED).count(),
    })


@login_required(login_url='taxi:panel_login')
def client_list(request):
    q      = request.GET.get('q', '').strip()
    filter_ = request.GET.get('filter', '').strip()
    sort    = request.GET.get('sort', '').strip()
    qs = Client.objects.annotate(orders_count=Count('orders'))
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(phone_number__icontains=q))
    if filter_ == 'blocked':
        qs = qs.filter(is_blocked=True)
    elif filter_ == 'active':
        qs = qs.filter(is_blocked=False)
    if sort == 'top_orders':
        qs = qs.order_by('-orders_count')
    return render(request, 'taxi/client_list.html', {'clients': qs, 'q': q, 'filter': filter_, 'sort': sort})


# ── Tariff Settings ────────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def bot_settings(request):
    from django.conf import settings as django_settings
    bot = BotSettings.get()
    if request.method == 'POST':
        bot.bot_token = request.POST.get('bot_token', '').strip()
        bot.group_id  = request.POST.get('group_id', '').strip()
        bot.extra_group_ids = request.POST.get('extra_group_ids', '').strip()
        bot.client_bot_token = request.POST.get('client_bot_token', '').strip()
        bot.driver_group_id = request.POST.get('driver_group_id', '').strip()
        bot.driver_extra_group_ids = request.POST.get('driver_extra_group_ids', '').strip()
        bot.notify_driver_group    = 'notify_driver_group'    in request.POST
        bot.notify_new_order       = 'notify_new_order'       in request.POST
        bot.notify_dispatched      = 'notify_dispatched'      in request.POST
        bot.notify_accepted        = 'notify_accepted'        in request.POST
        bot.notify_on_way          = 'notify_on_way'          in request.POST
        bot.notify_arrived         = 'notify_arrived'         in request.POST
        bot.notify_completed       = 'notify_completed'       in request.POST
        bot.notify_cancelled       = 'notify_cancelled'       in request.POST
        bot.notify_rejected        = 'notify_rejected'        in request.POST
        bot.notify_driver_register = 'notify_driver_register' in request.POST
        bot.notify_driver_approved = 'notify_driver_approved' in request.POST
        bot.notify_driver_rejected = 'notify_driver_rejected' in request.POST
        bot.notify_driver_blocked  = 'notify_driver_blocked'  in request.POST
        bot.notify_driver_login    = 'notify_driver_login'    in request.POST
        bot.notify_duty_changed    = 'notify_duty_changed'    in request.POST
        bot.notify_balance_changed = 'notify_balance_changed' in request.POST
        bot.notify_low_balance     = 'notify_low_balance'     in request.POST
        bot.notify_morning_greeting    = 'notify_morning_greeting'    in request.POST
        bot.notify_evening_top_drivers = 'notify_evening_top_drivers' in request.POST
        bot.notify_night_greeting      = 'notify_night_greeting'      in request.POST
        bot.notify_weekly_top_drivers  = 'notify_weekly_top_drivers'  in request.POST
        bot.notify_monthly_top_drivers = 'notify_monthly_top_drivers' in request.POST
        bot.notify_inactive_drivers    = 'notify_inactive_drivers'    in request.POST
        bot.notify_low_rating          = 'notify_low_rating'          in request.POST
        bot.notify_surge_alert         = 'notify_surge_alert'         in request.POST
        bot.notify_driver_milestone    = 'notify_driver_milestone'    in request.POST
        bot.notify_sos_to_driver_group = 'notify_sos_to_driver_group' in request.POST
        bot.notify_top_hours_drivers   = 'notify_top_hours_drivers'   in request.POST
        bot.notify_high_rejection      = 'notify_high_rejection'      in request.POST
        bot.notify_daily_summary       = 'notify_daily_summary'       in request.POST
        bot.notify_weekly_summary      = 'notify_weekly_summary'      in request.POST
        bot.notify_daily_highlight     = 'notify_daily_highlight'     in request.POST
        bot.notify_flyer_redeemed      = 'notify_flyer_redeemed'      in request.POST
        bot.save()
        # SITE_URL ni settings ga yozish
        site_url = request.POST.get('site_url', '').strip()
        if site_url:
            django_settings.SITE_URL = site_url
        # Test xabar yuborish
        if 'test' in request.POST and bot.bot_token and bot.group_id:
            from .utils import send_telegram
            send_telegram('✅ <b>VijdonTaxi bot ulanishi muvaffaqiyatli!</b>\nBu test xabari.')
        # Haydovchilar guruhiga erkin matnli e'lon yuborish
        announce_text = request.POST.get('announce_text', '').strip()
        if 'announce' in request.POST and announce_text and bot.bot_token:
            from .utils import tg_group_announcement
            tg_group_announcement(announce_text)
        return redirect('taxi:bot_settings')
    site_url = getattr(django_settings, 'SITE_URL', '')
    order_notifs = [
        ('notify_new_order',  'Yangi buyurtma',          '🚨', bot.notify_new_order),
        ('notify_dispatched', 'Buyurtma yuborildi',       '📡', bot.notify_dispatched),
        ('notify_accepted',   'Buyurtma qabul qilindi',   '✅', bot.notify_accepted),
        ('notify_on_way',     "Haydovchi yo'lda",         '🚗', bot.notify_on_way),
        ('notify_arrived',    'Haydovchi yetib keldi',    '📍', bot.notify_arrived),
        ('notify_completed',  'Buyurtma yakunlandi',      '🏁', bot.notify_completed),
        ('notify_cancelled',  'Buyurtma bekor qilindi',   '❌', bot.notify_cancelled),
        ('notify_rejected',   'Buyurtma rad etildi',      '🔄', bot.notify_rejected),
    ]
    driver_notifs = [
        ('notify_driver_register', "Yangi haydovchi ro'yxatdan o'tdi", '🆕', bot.notify_driver_register),
        ('notify_driver_approved', 'Haydovchi tasdiqlandi',             '✅', bot.notify_driver_approved),
        ('notify_driver_rejected', 'Haydovchi rad etildi',              '🚫', bot.notify_driver_rejected),
        ('notify_driver_blocked',  'Haydovchi bloklandi/ochildi',       '🔒', bot.notify_driver_blocked),
        ('notify_driver_login',    'Haydovchi kirdi (login)',           '🔑', bot.notify_driver_login),
        ('notify_duty_changed',    "Navbat holati o'zgardi",            '🟢', bot.notify_duty_changed),
        ('notify_balance_changed', "Balans o'zgardi",                   '💰', bot.notify_balance_changed),
        ('notify_low_balance',     'Balans kam ogohlantirish',          '⚠️', bot.notify_low_balance),
        ('notify_morning_greeting',    'Ertalabki salomlashuv (07:00)',        '🌅', bot.notify_morning_greeting),
        ('notify_evening_top_drivers', 'Kechqurungi TOP-10 (20:00)',           '🏆', bot.notify_evening_top_drivers),
        ('notify_night_greeting',      'Tungi navbatchilarga salom (23:00)',   '🌙', bot.notify_night_greeting),
        ('notify_weekly_top_drivers',  'Haftalik TOP-10 (yakshanba 21:00)',    '📅', bot.notify_weekly_top_drivers),
        ('notify_monthly_top_drivers', 'Oylik TOP-10 (oy oxiri 21:00)',        '🗓️', bot.notify_monthly_top_drivers),
        ('notify_inactive_drivers',    "Faol bo'lmagan haydovchilar (10:00)",  '😴', bot.notify_inactive_drivers),
        ('notify_low_rating',          'Reyting pasayganda ogohlantirish',     '⭐', bot.notify_low_rating),
        ('notify_surge_alert',         'Talab yuqori bo\'lganda ogohlantirish','📈', bot.notify_surge_alert),
        ('notify_driver_milestone',    'Haydovchi yubileyi (safarlar soni)',   '🎉', bot.notify_driver_milestone),
        ('notify_sos_to_driver_group', 'SOS ni haydovchilar guruhiga ham yuborish', '🆘', bot.notify_sos_to_driver_group),
        ('notify_top_hours_drivers',   "Eng ko'p soat ishlagan (21:00)",       '⏱️', bot.notify_top_hours_drivers),
        ('notify_high_rejection',      "Ko'p rad etish haqida ogohlantirish (19:00)", '🚫', bot.notify_high_rejection),
        ('notify_daily_summary',       'Kunlik umumiy hisobot (22:00)',        '📊', bot.notify_daily_summary),
        ('notify_weekly_summary',      'Haftalik umumiy hisobot (yakshanba 22:00)', '📈', bot.notify_weekly_summary),
        ('notify_daily_highlight',     "Kunning yorqin lahzalari (20:00)",     '🌟', bot.notify_daily_highlight),
        ('notify_flyer_redeemed',      'Flayer kuponi ishlatilganda xabar',    '🎁', bot.notify_flyer_redeemed),
    ]
    return render(request, 'taxi/bot_settings.html', {
        'bot': bot,
        'site_url': site_url,
        'order_notifs': order_notifs,
        'driver_notifs': driver_notifs,
        'admins': BotAdmin.objects.all(),
    })


@login_required(login_url='taxi:panel_login')
def sms_settings(request):
    sms = SmsSettings.get()
    saved = False
    test_result = None
    if request.method == 'POST':
        if 'test' in request.POST:
            test_phone = request.POST.get('test_phone', '').strip()
            ok, message = send_sms(test_phone, 'Vijdon Taxi: bu test SMS xabari.')
            test_result = {'ok': ok, 'message': message}
        else:
            new_email    = request.POST.get('email', '').strip()
            new_password = request.POST.get('password', '').strip()
            if new_email != sms.email or new_password != sms.password:
                # Kirish ma'lumotlari o'zgardi — eski token endi yaroqsiz
                sms.token = ''
                sms.token_updated_at = None
            sms.email    = new_email
            sms.password = new_password
            sms.nickname = request.POST.get('nickname', '').strip() or '4546'
            sms.sms_accepted  = 'sms_accepted'  in request.POST
            sms.sms_arrived   = 'sms_arrived'   in request.POST
            sms.sms_completed = 'sms_completed' in request.POST
            sms.sms_cancelled = 'sms_cancelled' in request.POST
            sms.save()
            saved = True
    sms_notifs = [
        ('sms_accepted',  'Buyurtma qabul qilindi',  '✅', sms.sms_accepted),
        ('sms_arrived',   'Haydovchi yetib keldi',   '📍', sms.sms_arrived),
        ('sms_completed', 'Buyurtma yakunlandi',     '🏁', sms.sms_completed),
        ('sms_cancelled', 'Buyurtma bekor qilindi',  '❌', sms.sms_cancelled),
    ]
    return render(request, 'taxi/sms_settings.html', {
        'sms': sms,
        'saved': saved,
        'test_result': test_result,
        'sms_notifs': sms_notifs,
    })


# ── AI o'sish tavsiyalari ─────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def ai_settings(request):
    cfg = AiSettings.get()
    saved = False
    if request.method == 'POST':
        cfg.api_key = request.POST.get('api_key', '').strip()
        cfg.model   = request.POST.get('model', cfg.model)
        cfg.save()
        saved = True
    return render(request, 'taxi/ai_settings.html', {
        'cfg': cfg,
        'saved': saved,
        'model_choices': AiSettings.MODEL_CHOICES,
    })


@login_required(login_url='taxi:panel_login')
def panel_ai_insights(request):
    from django.utils import timezone
    from django.db.models import Sum, Count, Avg
    from datetime import timedelta

    now   = timezone.now()
    today = now.date()
    completed_qs = Order.objects.filter(status='completed')
    total_orders = Order.objects.count()
    cancelled_orders = Order.objects.filter(status='cancelled').count()
    cancel_rate = round(cancelled_orders / total_orders * 100, 1) if total_orders else 0

    weekly_counts = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        weekly_counts.append(Order.objects.filter(created_at__date=day).count())

    # ── Shu hafta / o'tgan hafta taqqoslash — orqaga ketishni aniqlash uchun ──
    this_week_start = today - timedelta(days=6)
    prev_week_start  = today - timedelta(days=13)
    prev_week_end    = today - timedelta(days=7)
    this_week_qs = Order.objects.filter(created_at__date__gte=this_week_start, created_at__date__lte=today)
    prev_week_qs = Order.objects.filter(created_at__date__gte=prev_week_start, created_at__date__lte=prev_week_end)
    this_week_orders  = this_week_qs.count()
    prev_week_orders  = prev_week_qs.count()
    this_week_revenue = float(this_week_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0)
    prev_week_revenue = float(prev_week_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0)
    orders_change_pct  = round((this_week_orders - prev_week_orders) / prev_week_orders * 100, 1) if prev_week_orders else None
    revenue_change_pct = round((this_week_revenue - prev_week_revenue) / prev_week_revenue * 100, 1) if prev_week_revenue else None

    online_threshold = timezone.now() - timezone.timedelta(minutes=2)
    top_drivers = list(Driver.objects.annotate(
        completed=Count('orders', filter=Q(orders__status='completed'))
    ).filter(completed__gt=0).order_by('-completed')[:5])
    bottom_drivers = Driver.objects.filter(
        is_active=True, approval_status=Driver.APPROVAL_APPROVED
    ).annotate(
        completed=Count('orders', filter=Q(orders__status='completed'))
    ).order_by('completed')[:5]

    total_clients = Client.objects.count()
    repeat_clients = Client.objects.annotate(total=Count('orders')).filter(total__gt=1).count()
    repeat_rate = round(repeat_clients / total_clients * 100, 1) if total_clients else 0

    # ── Eng ko'p ishlagan haydovchi va eng faol mijoz (shu oy, bo'lmasa umumiy) ──
    # Bu oy allaqachon "berdim" deb belgilangan haydovchi/mijoz qayta taklif qilinmaydi —
    # operator ularga sovg'a berganini tasdiqlagach, navbat keyingisiga o'tadi.
    month_start = today.replace(day=1)
    period = today.strftime('%Y-%m')
    rewarded_driver_ids = set(AiRewardLog.objects.filter(
        reward_type=AiRewardLog.TYPE_DRIVER, period=period
    ).values_list('driver_id', flat=True))
    rewarded_client_ids = set(AiRewardLog.objects.filter(
        reward_type=AiRewardLog.TYPE_CLIENT, period=period
    ).values_list('client_id', flat=True))

    top_driver_month = Driver.objects.exclude(id__in=rewarded_driver_ids).annotate(
        completed=Count('orders', filter=Q(orders__status='completed', orders__created_at__date__gte=month_start)),
        earned=Sum('orders__price', filter=Q(orders__status='completed', orders__created_at__date__gte=month_start)),
    ).filter(completed__gt=0).order_by('-completed').first()
    top_driver_fallback = next((d for d in top_drivers if d.id not in rewarded_driver_ids), None)
    top_driver = top_driver_month or top_driver_fallback

    top_client_month = Client.objects.exclude(id__in=rewarded_client_ids).annotate(
        total=Count('orders', filter=Q(orders__created_at__date__gte=month_start)),
        spent=Sum('orders__price', filter=Q(orders__status='completed', orders__created_at__date__gte=month_start)),
    ).filter(total__gt=0).order_by('-total').first()
    top_client_fallback = Client.objects.exclude(id__in=rewarded_client_ids).annotate(
        total=Count('orders'), spent=Sum('orders__price', filter=Q(orders__status='completed'))
    ).filter(total__gt=0).order_by('-total').first()
    top_client = top_client_month or top_client_fallback

    top_driver_data = None
    if top_driver:
        top_driver_data = {
            'id': top_driver.id,
            'ism': top_driver.full_name,
            'yakunlangan_safar': getattr(top_driver, 'completed', None),
            'daromad_keltirdi_som': float(getattr(top_driver, 'earned', None) or 0),
        }
    top_client_data = None
    if top_client:
        top_client_data = {
            'id': top_client.id,
            'ism': top_client.full_name or top_client.phone_number,
            'buyurtmalar_soni': getattr(top_client, 'total', None),
            'sarflagan_pul_som': float(getattr(top_client, 'spent', None) or 0),
        }

    stats = {
        'jami_buyurtmalar':              total_orders,
        'yakunlangan_buyurtmalar':       completed_qs.count(),
        'bekor_qilingan_buyurtmalar':    cancelled_orders,
        'bekor_qilish_foizi':            cancel_rate,
        'jami_daromad_som':              float(completed_qs.aggregate(s=Sum('price'))['s'] or 0),
        'ortacha_narx_som':              float(completed_qs.aggregate(a=Avg('price'))['a'] or 0),
        'songgi_7_kun_buyurtmalar_soni': weekly_counts,
        'shu_hafta_buyurtmalar':         this_week_orders,
        'otgan_hafta_buyurtmalar':       prev_week_orders,
        'buyurtmalar_ozgarish_foizi':    orders_change_pct,
        'shu_hafta_daromad_som':         this_week_revenue,
        'otgan_hafta_daromad_som':       prev_week_revenue,
        'daromad_ozgarish_foizi':        revenue_change_pct,
        'faol_haydovchilar_soni':        Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED).count(),
        'online_haydovchilar_soni':      Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED, last_seen__gte=online_threshold).count(),
        'eng_faol_haydovchilar':         [{'ism': d.full_name, 'yakunlangan_safar': d.completed} for d in top_drivers],
        'kam_faol_haydovchilar':         [{'ism': d.full_name, 'yakunlangan_safar': d.completed} for d in bottom_drivers],
        'oyning_eng_faol_haydovchisi':   top_driver_data,
        'oyning_eng_faol_mijozi':        top_client_data,
        'jami_mijozlar':                 total_clients,
        'qaytib_kelgan_mijozlar_foizi':  repeat_rate,
        'bloklangan_mijozlar':           Client.objects.filter(is_blocked=True).count(),
    }

    ok, result = generate_growth_insights(stats)
    if ok:
        return JsonResponse({
            'ok': True,
            'items': result['tavsiyalar'],
            'warning': result.get('ogohlantirish') or '',
            'period': period,
            'top_driver': top_driver_data,
            'top_driver_reward': result.get('top_haydovchi_sovrini') or '',
            'top_client': top_client_data,
            'top_client_reward': result.get('top_mijoz_sovrini') or '',
        })
    return JsonResponse({'ok': False, 'error': result}, status=400)


@login_required(login_url='taxi:panel_login')
@require_POST
def panel_ai_reward_given(request):
    """Operator AI tavsiya qilgan sovg'ani haydovchi/mijozga qo'lda berganini
    tasdiqlaydi. AI hech qachon sovg'ani o'zi avtomatik bermaydi — bu yerda faqat
    inson tasdiqlagan holat qayd etiladi, shundan keyin shu davrda ular AI
    tavsiyasida qayta taklif qilinmaydi."""
    reward_type = request.POST.get('type', '').strip()
    target_id   = request.POST.get('id', '').strip()
    period      = request.POST.get('period', '').strip()
    reward_text = request.POST.get('reward_text', '').strip()

    if reward_type not in (AiRewardLog.TYPE_DRIVER, AiRewardLog.TYPE_CLIENT) or not target_id or not period:
        return JsonResponse({'ok': False, 'error': "Noto'g'ri so'rov"}, status=400)

    kwargs = {'reward_type': reward_type, 'period': period}
    if reward_type == AiRewardLog.TYPE_DRIVER:
        driver = get_object_or_404(Driver, pk=target_id)
        kwargs['driver'] = driver
    else:
        client = get_object_or_404(Client, pk=target_id)
        kwargs['client'] = client

    obj, created = AiRewardLog.objects.get_or_create(
        **kwargs,
        defaults={'reward_text': reward_text, 'given_by': request.user},
    )
    if not created:
        return JsonResponse({'ok': False, 'error': 'Bu shaxsga shu oy uchun allaqachon belgilangan'}, status=400)
    return JsonResponse({'ok': True})


@login_required(login_url='taxi:panel_login')
def bot_admin_add(request):
    if request.method == 'POST':
        chat_id   = request.POST.get('chat_id', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        if chat_id.isdigit():
            BotAdmin.objects.get_or_create(chat_id=chat_id, defaults={'full_name': full_name})
    return redirect('taxi:bot_settings')


@login_required(login_url='taxi:panel_login')
def bot_admin_delete(request, pk):
    admin = get_object_or_404(BotAdmin, pk=pk)
    if request.method == 'POST':
        admin.delete()
    return redirect('taxi:bot_settings')


@login_required(login_url='taxi:panel_login')
def bot_admin_toggle(request, pk):
    admin = get_object_or_404(BotAdmin, pk=pk)
    if request.method == 'POST':
        admin.is_active = not admin.is_active
        admin.save(update_fields=['is_active'])
    return redirect('taxi:bot_settings')


@login_required(login_url='taxi:panel_login')
def sound_settings(request):
    from .constants import PANEL_SOUND_EVENTS, DRIVER_SOUND_EVENTS
    all_keys = [k for k, _ in PANEL_SOUND_EVENTS + DRIVER_SOUND_EVENTS]
    sounds = PanelSound.get_map()
    for key in all_keys:
        if key not in sounds:
            sounds[key] = PanelSound.objects.create(event_key=key)

    if request.method == 'POST':
        for key in all_keys:
            snd = sounds[key]
            if request.POST.get(f'reset_{key}'):
                if snd.file:
                    snd.file.delete(save=False)
                snd.file = None
            elif request.FILES.get(f'file_{key}'):
                snd.file = request.FILES[f'file_{key}']
            snd.enabled = f'enabled_{key}' in request.POST
            snd.save()
        messages.success(request, "Ovoz sozlamalari saqlandi.")
        return redirect('taxi:sound_settings')

    return render(request, 'taxi/sound_settings.html', {
        'panel_sounds':  [(key, label, sounds[key]) for key, label in PANEL_SOUND_EVENTS],
        'driver_sounds': [(key, label, sounds[key]) for key, label in DRIVER_SOUND_EVENTS],
    })


# ── Telegram Client Bot Webhook ───────────────────────────────────────────────

# Har bir mijoz sessiyasi: {chat_id: {'step': 'phone'|'from'|'to', 'phone': ..., 'from_address': ...}}
_client_sessions = {}


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def client_bot_webhook(request):
    """Mijoz Telegram boti webhook — buyurtma qabul qiladi."""
    import json as _json
    if request.method != 'POST':
        from django.http import HttpResponse
        return HttpResponse('ok')

    try:
        data = _json.loads(request.body)
    except Exception:
        from django.http import HttpResponse
        return HttpResponse('ok')

    msg = data.get('message') or data.get('edited_message')
    if not msg:
        from django.http import HttpResponse
        return HttpResponse('ok')

    chat_id = str(msg['chat']['id'])
    text    = (msg.get('text') or '').strip()

    bot = BotSettings.get()
    token = bot.client_bot_token.strip()
    if not token:
        from django.http import HttpResponse
        return HttpResponse('ok')

    def _send(chat, txt, keyboard=None):
        import urllib.request, urllib.parse
        payload = {'chat_id': chat, 'text': txt, 'parse_mode': 'HTML'}
        if keyboard:
            import json as j
            payload['reply_markup'] = j.dumps(keyboard)
        data = urllib.parse.urlencode(payload).encode()
        try:
            urllib.request.urlopen(
                f'https://api.telegram.org/bot{token}/sendMessage',
                data=data, timeout=5
            )
        except Exception:
            pass

    session = _client_sessions.get(chat_id, {})
    step    = session.get('step', 'start')

    if text in ('/start', 'Yangi buyurtma 🚖'):
        _client_sessions[chat_id] = {'step': 'phone'}
        _send(chat_id,
            '📞 <b>Telefon raqamingizni yuboring</b>\n'
            'Masalan: <code>+998901234567</code>',
            {'keyboard': [[{'text': 'Yangi buyurtma 🚖'}]], 'resize_keyboard': True}
        )

    elif step == 'phone':
        phone = text.replace(' ', '')
        if len(phone) < 9:
            _send(chat_id, '❌ Telefon raqam noto\'g\'ri. Qayta kiriting:')
        else:
            _client_sessions[chat_id] = {'step': 'from', 'phone': phone}
            _send(chat_id, '📍 <b>Qayerdan yo\'lga chiqasiz?</b>\nManzilni yozing:')

    elif step == 'from':
        _client_sessions[chat_id] = dict(session, step='to', from_address=text)
        _send(chat_id,
            '🏁 <b>Qayerga borasiz?</b>\nManzilni yozing yoki o\'tkazib yuboring:',
            {'keyboard': [[{'text': "O'tkazib yuborish ➡️"}]], 'resize_keyboard': True}
        )

    elif step == 'to':
        to_address = '' if text == "O'tkazib yuborish ➡️" else text
        phone        = session.get('phone', '')
        from_address = session.get('from_address', '')

        client, _ = Client.objects.get_or_create(phone_number=phone)
        tariff    = TariffSettings.get()
        order = Order.objects.create(
            client=client,
            from_address=from_address,
            to_address=to_address,
            commission=tariff.commission,
            status='pending',
        )
        tg_new_order(order)
        if tariff.auto_dispatch:
            import threading
            threading.Thread(target=dispatch_order, args=(order,), daemon=True).start()

        _client_sessions.pop(chat_id, None)
        _send(chat_id,
            f'✅ <b>Buyurtma #{order.id} qabul qilindi!</b>\n'
            f'📍 Qayerdan: {from_address}\n'
            + (f'🏁 Qayerga: {to_address}\n' if to_address else '') +
            '⏳ Haydovchi tez orada topiladi.',
            {'keyboard': [[{'text': 'Yangi buyurtma 🚖'}]], 'resize_keyboard': True}
        )
    else:
        _send(chat_id, 'Boshlash uchun /start yuboring.',
            {'keyboard': [[{'text': 'Yangi buyurtma 🚖'}]], 'resize_keyboard': True}
        )

    from django.http import HttpResponse
    return HttpResponse('ok')


@login_required(login_url='taxi:panel_login')
def maps_settings(request):
    maps = MapsSettings.get()
    if request.method == 'POST':
        maps.provider          = request.POST.get('provider', maps.provider)
        maps.api_key           = request.POST.get('api_key', '').strip()
        maps.yandex_mapkit_key = request.POST.get('yandex_mapkit_key', '').strip()
        maps.is_active         = request.POST.get('is_active') == 'on'
        maps.save()
        return redirect('taxi:maps_settings')
    return render(request, 'taxi/maps_settings.html', {'maps': maps})


@login_required(login_url='taxi:panel_login')
def tariff_settings(request):
    tariff = TariffSettings.get()
    if request.method == 'POST':
        from decimal import Decimal, InvalidOperation
        try:
            tariff.base_price   = Decimal(request.POST.get('base_price', tariff.base_price))
            tariff.price_per_km = Decimal(request.POST.get('price_per_km', tariff.price_per_km))
            tariff.waiting_price_per_minute = Decimal(request.POST.get('waiting_price_per_minute', tariff.waiting_price_per_minute))
            tariff.commission   = Decimal(request.POST.get('commission', tariff.commission))
            tariff.auto_dispatch = request.POST.get('auto_dispatch') == 'on'
            tariff.max_dispatch_attempts = int(request.POST.get('max_dispatch_attempts', tariff.max_dispatch_attempts))
            tariff.dispatch_timeout      = int(request.POST.get('dispatch_timeout', tariff.dispatch_timeout))
            tariff.operator_phone        = request.POST.get('operator_phone', tariff.operator_phone).strip() or tariff.operator_phone
            tariff.save()
        except (InvalidOperation, ValueError):
            pass
        return redirect('taxi:tariff_settings')
    return render(request, 'taxi/tariff_settings.html', {'tariff': tariff})


# ── SOS ──────────────────────────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def sos_list(request):
    qs = SosAlert.objects.select_related('driver').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)
    return render(request, 'taxi/sos_list.html', {
        'alerts':        qs,
        'status_filter': status_filter,
        'new_count':     SosAlert.objects.filter(status=SosAlert.STATUS_NEW).count(),
    })


@login_required(login_url='taxi:panel_login')
def sos_resolve(request, pk):
    alert = get_object_or_404(SosAlert, pk=pk)
    if request.method == 'POST':
        from django.utils import timezone
        alert.status      = request.POST.get('status', SosAlert.STATUS_RESOLVED)
        alert.resolved_by = request.POST.get('resolved_by', '').strip()
        if alert.status == SosAlert.STATUS_RESOLVED:
            alert.resolved_at = timezone.now()
        alert.save(update_fields=['status', 'resolved_by', 'resolved_at'])
    return redirect(request.META.get('HTTP_REFERER', 'taxi:sos_list'))


def sos_count(request):
    count = SosAlert.objects.filter(status=SosAlert.STATUS_NEW).count()
    return JsonResponse({'count': count})


# ── Balans to'ldirish so'rovlari (admin panel) ──────────────────────────────

@login_required(login_url='taxi:panel_login')
def topup_list(request):
    from django.db.models import Sum
    from django.utils import timezone

    tab = request.GET.get('tab', 'requests')
    status_filter = request.GET.get('status', BalanceTopupRequest.STATUS_PENDING)
    qs = BalanceTopupRequest.objects.select_related('driver').order_by('-created_at')
    if status_filter:
        qs = qs.filter(status=status_filter)

    today = timezone.now().date()
    month_start = today.replace(day=1)
    total_topped_up = BalanceLog.objects.filter(action=BalanceLog.ACTION_ADD).aggregate(s=Sum('amount'))['s'] or 0
    total_deducted  = BalanceLog.objects.filter(action=BalanceLog.ACTION_DEDUCT).aggregate(s=Sum('amount'))['s'] or 0
    month_topped_up = BalanceLog.objects.filter(action=BalanceLog.ACTION_ADD, created_at__date__gte=month_start).aggregate(s=Sum('amount'))['s'] or 0
    month_deducted  = BalanceLog.objects.filter(action=BalanceLog.ACTION_DEDUCT, created_at__date__gte=month_start).aggregate(s=Sum('amount'))['s'] or 0

    history_qs = BalanceLog.objects.select_related('driver').order_by('-created_at')
    history_action = request.GET.get('haction', '')
    history_q       = request.GET.get('q', '').strip()
    history_start   = request.GET.get('hstart', '')
    history_end     = request.GET.get('hend', '')
    if history_action in (BalanceLog.ACTION_ADD, BalanceLog.ACTION_DEDUCT):
        history_qs = history_qs.filter(action=history_action)
    if history_q:
        history_qs = history_qs.filter(Q(driver__full_name__icontains=history_q) | Q(driver__phone_number__icontains=history_q))
    if history_start:
        history_qs = history_qs.filter(created_at__date__gte=history_start)
    if history_end:
        history_qs = history_qs.filter(created_at__date__lte=history_end)

    return render(request, 'taxi/topup_list.html', {
        'tab':           tab,
        'requests':      qs,
        'status_filter': status_filter,
        'pending_count': BalanceTopupRequest.objects.filter(status=BalanceTopupRequest.STATUS_PENDING).count(),
        'drivers': Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED).order_by('full_name'),
        'total_topped_up': total_topped_up,
        'total_deducted':  total_deducted,
        'month_topped_up': month_topped_up,
        'month_deducted':  month_deducted,
        'history':        history_qs[:200],
        'history_action': history_action,
        'history_q':      history_q,
        'history_start':  history_start,
        'history_end':    history_end,
    })


@login_required(login_url='taxi:panel_login')
def balance_log_export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="balans_tarixi.csv"'
    response.write('﻿')
    writer = csv.writer(response)
    writer.writerow(['#', 'Haydovchi', 'Telefon', 'Amal', 'Summa', "Balans (keyin)", 'Izoh', 'Vaqt'])

    qs = BalanceLog.objects.select_related('driver').order_by('-created_at')
    action = request.GET.get('haction', '')
    q       = request.GET.get('q', '').strip()
    start   = request.GET.get('hstart', '')
    end     = request.GET.get('hend', '')
    if action in (BalanceLog.ACTION_ADD, BalanceLog.ACTION_DEDUCT):
        qs = qs.filter(action=action)
    if q:
        qs = qs.filter(Q(driver__full_name__icontains=q) | Q(driver__phone_number__icontains=q))
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)

    for log in qs:
        writer.writerow([
            log.id, log.driver.full_name, log.driver.phone_number, log.get_action_display(),
            log.amount, log.balance_after, log.note, log.created_at.strftime('%d.%m.%Y %H:%M'),
        ])
    return response


@login_required(login_url='taxi:panel_login')
def topup_resolve(request, pk):
    topup = get_object_or_404(BalanceTopupRequest, pk=pk)
    if request.method == 'POST' and topup.status == BalanceTopupRequest.STATUS_PENDING:
        from django.utils import timezone
        action = request.POST.get('action')
        driver = topup.driver
        if action == 'approve':
            driver.balance += topup.amount
            driver.save(update_fields=['balance'])
            BalanceLog.objects.create(
                driver=driver, action=BalanceLog.ACTION_ADD, amount=topup.amount,
                balance_after=driver.balance, note=f"To'lov cheki tasdiqlandi #{topup.id} (panel)",
            )
            DriverActivityLog.objects.create(
                driver=driver, action=DriverActivityLog.ACTION_BALANCE,
                detail=f"Admin (panel): to'lov cheki #{topup.id} tasdiqlandi, +{topup.amount} UZS",
                ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            topup.status = BalanceTopupRequest.STATUS_APPROVED
            tg_balance_changed(driver, topup.amount, BalanceLog.ACTION_ADD)
            messages.success(request, f"To'lov #{topup.id} tasdiqlandi — {driver.full_name} balansi: {driver.balance} UZS")
        elif action == 'reject':
            topup.status = BalanceTopupRequest.STATUS_REJECTED
            messages.success(request, f"To'lov #{topup.id} rad etildi.")
        topup.resolved_at = timezone.now()
        topup.save(update_fields=['status', 'resolved_at'])
    return redirect(request.META.get('HTTP_REFERER', 'taxi:topup_list'))


@login_required(login_url='taxi:panel_login')
def panel_events_api(request):
    """Operator panel ovozli bildirishnomasi uchun polling endpoint.
    ?since=<id> dan keyingi hodisalarni, har biri uchun mos ovoz URL bilan qaytaradi."""
    since = int(request.GET.get('since') or 0)
    events = list(PanelEvent.objects.filter(id__gt=since).order_by('id')[:20])
    sounds = PanelSound.get_map()
    data = []
    for e in events:
        snd = sounds.get(e.event_type)
        data.append({
            'id': e.id,
            'type': e.event_type,
            'message': e.message,
            'enabled': snd.enabled if snd else True,
            'sound_url': snd.resolve_url() if snd else None,
        })
    last_id = events[-1].id if events else since
    return JsonResponse({'events': data, 'last_id': last_id})


# ── Operator Bot — Admin buyruqlari (shaxsiy chat) ────────────────────────────

# Admin bilan buyurtma yaratish suhbati holati: {chat_id: {'step': ..., ...}}
_admin_sessions = {}

_ADMIN_MENU_KB = {
    'keyboard': [
        [{'text': '🆕 Yangi buyurtma'}],
        [{'text': '📋 Buyurtmalar'}, {'text': '🚖 Haydovchilar'}],
        [{'text': '🆕 Yangi haydovchilar'}, {'text': '📊 Statistika'}],
        [{'text': "💳 To'lov so'rovlari"}, {'text': '❓ Yordam'}],
    ],
    'resize_keyboard': True,
}

_LOCATION_KB = {
    'keyboard': [
        [{'text': '📍 Joylashuvni yuborish', 'request_location': True}],
        [{'text': "❌ Bekor qilish"}],
    ],
    'resize_keyboard': True,
}

_LOCATION_OR_SKIP_KB = {
    'keyboard': [
        [{'text': '📍 Joylashuvni yuborish', 'request_location': True}],
        [{'text': "O'tkazib yuborish ➡️"}, {'text': "❌ Bekor qilish"}],
    ],
    'resize_keyboard': True,
}

_CANCEL_KB = {
    'keyboard': [[{'text': "❌ Bekor qilish"}]],
    'resize_keyboard': True,
}


def _admin_bot_send(token, chat_id, text, keyboard=None):
    import urllib.request, urllib.parse, json as _j
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if keyboard:
        payload['reply_markup'] = _j.dumps(keyboard)
    data = urllib.parse.urlencode(payload).encode()
    try:
        urllib.request.urlopen(
            f'https://api.telegram.org/bot{token}/sendMessage',
            data=data, timeout=5
        )
    except Exception:
        pass


def _admin_help_text():
    return (
        "🤖 <b>Admin buyruqlari</b>\n\n"
        "🆕 Yangi buyurtma — mijoz uchun buyurtma yaratish (manzilni yozish yoki 📍 joylashuv yuborish mumkin)\n"
        "📋 Buyurtmalar — oxirgi faol buyurtmalar\n"
        "🚖 Haydovchilar — tasdiqlangan haydovchilar ro'yxati\n"
        "🆕 Yangi haydovchilar — tasdiqlanishi kerak bo'lgan haydovchilar\n"
        "📊 Statistika — bugungi buyurtmalar va tushum hisoboti\n"
        "/buyurtma &lt;id&gt; — buyurtma haqida to'liq ma'lumot\n"
        "/bekor &lt;id&gt; — buyurtmani bekor qilish\n"
        "/qayta &lt;id&gt; — buyurtmani qayta ochish va eng yaqin haydovchiga qayta yuborish\n"
        "/tasdiq &lt;id&gt; — yangi haydovchini tasdiqlash\n"
        "/rad &lt;id&gt; — yangi haydovchini rad etish\n"
        "/blok &lt;id&gt; — haydovchini bloklash\n"
        "/blokoch &lt;id&gt; — haydovchini blokdan chiqarish\n"
        "/balans &lt;id&gt; &lt;miqdor&gt; — balans qo'shish (ayirish uchun manfiy son, masalan -20000)\n"
        "/tarix &lt;id&gt; — haydovchi balans tarixi\n"
        "💳 To'lov so'rovlari — haydovchi yuborgan to'lov cheklarini ko'rish\n"
        "/tolovtasdiq &lt;id&gt; — to'lov chekini tasdiqlash (balansga qo'shiladi)\n"
        "/tolovrad &lt;id&gt; — to'lov chekini rad etish\n"
        "/cancel — joriy amalni bekor qilish (masalan buyurtma yaratishni to'xtatish)"
    )


def _handle_admin_message(token, chat_id, text, location=None):
    """Admin (whitelist'dagi) shaxsiy chatdan yuborgan xabarni qayta ishlaydi."""
    from decimal import Decimal, InvalidOperation

    session = _admin_sessions.get(chat_id, {})
    step = session.get('step')

    # ── Joriy amaldan chiqish — istalgan bosqichda ishlaydi ──
    if step and text in ('/cancel', '❌ Bekor qilish'):
        _admin_sessions.pop(chat_id, None)
        _admin_bot_send(token, chat_id, "❌ Bekor qilindi.", _ADMIN_MENU_KB)
        return

    # ── Yangi buyurtma yaratish oqimi ──
    if step == 'order_phone':
        phone = text.replace(' ', '')
        if len(phone) < 9:
            _admin_bot_send(token, chat_id, "❌ Telefon raqam noto'g'ri. Qayta kiriting:", _CANCEL_KB)
        else:
            _admin_sessions[chat_id] = {'step': 'order_from', 'phone': phone}
            _admin_bot_send(token, chat_id,
                "📍 <b>Qayerdan yo'lga chiqadi?</b>\nManzilni yozing yoki joylashuvni yuboring:",
                _LOCATION_KB)
        return

    if step == 'order_from':
        if location:
            lat, lng = location.get('latitude'), location.get('longitude')
            address = reverse_geocode_address(lat, lng) or f"{lat:.5f}, {lng:.5f}"
            _admin_sessions[chat_id] = dict(session, step='order_to', from_address=address, from_lat=lat, from_lng=lng)
        else:
            _admin_sessions[chat_id] = dict(session, step='order_to', from_address=text)
        _admin_bot_send(token, chat_id,
            "🏁 <b>Qayerga boradi?</b>\nManzilni yozing, joylashuvni yuboring yoki o'tkazib yuboring:",
            _LOCATION_OR_SKIP_KB)
        return

    if step == 'order_to':
        to_lat, to_lng = None, None
        if location:
            to_lat, to_lng = location.get('latitude'), location.get('longitude')
            to_address = reverse_geocode_address(to_lat, to_lng) or f"{to_lat:.5f}, {to_lng:.5f}"
        elif text == "O'tkazib yuborish ➡️":
            to_address = ''
        else:
            to_address = text

        phone        = session.get('phone', '')
        from_address = session.get('from_address', '')
        from_lat     = session.get('from_lat')
        from_lng     = session.get('from_lng')

        client, _created = Client.objects.get_or_create(phone_number=phone)
        tariff = TariffSettings.get()

        distance_km = None
        price = None
        if from_lat and from_lng and to_lat and to_lng:
            distance_km = haversine(from_lat, from_lng, to_lat, to_lng)
            if distance_km:
                price = tariff.calc_price(distance_km)

        order = Order.objects.create(
            client=client,
            from_address=from_address, from_lat=from_lat, from_lng=from_lng,
            to_address=to_address, to_lat=to_lat, to_lng=to_lng,
            distance_km=distance_km,
            price=price,
            commission=tariff.commission,
            status='pending',
        )
        tg_new_order(order)
        if tariff.auto_dispatch:
            import threading
            threading.Thread(target=dispatch_order, args=(order,), daemon=True).start()

        _admin_sessions.pop(chat_id, None)
        _admin_bot_send(token, chat_id,
            f"✅ <b>Buyurtma #{order.id} yaratildi!</b>\n"
            f"📍 Qayerdan: {from_address}\n"
            + (f"🏁 Qayerga: {to_address}\n" if to_address else '')
            + (f"💰 Narx: {price:.0f} UZS\n" if price else ''),
            _ADMIN_MENU_KB)
        return

    # ── Menyu / buyruqlar ──
    if text in ('/start', '/menu'):
        _admin_sessions.pop(chat_id, None)
        pending_orders  = Order.objects.filter(status='pending').count()
        active_orders   = Order.objects.filter(status__in=Order.ACTIVE_STATUSES).count()
        on_duty         = Driver.objects.filter(is_active=True, is_on_duty=True, approval_status=Driver.APPROVAL_APPROVED).count()
        pending_drivers = Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).count()
        pending_topups  = BalanceTopupRequest.objects.filter(status=BalanceTopupRequest.STATUS_PENDING).count()
        new_sos         = SosAlert.objects.filter(status=SosAlert.STATUS_NEW).count()

        lines = ["👋 <b>Admin panel botiga xush kelibsiz!</b>\n"]
        if new_sos:
            lines.append(f"🆘 <b>{new_sos} ta hal qilinmagan SOS signal!</b>")
        lines.append(f"🕐 Kutilayotgan buyurtmalar: <b>{pending_orders}</b>")
        lines.append(f"⏳ Jarayondagi buyurtmalar: <b>{active_orders}</b>")
        lines.append(f"🟢 Navbatdagi haydovchilar: <b>{on_duty}</b>")
        if pending_drivers:
            lines.append(f"🆕 Tasdiq kutayotgan haydovchilar: <b>{pending_drivers}</b>")
        if pending_topups:
            lines.append(f"💳 Kutilayotgan to'lov so'rovlari: <b>{pending_topups}</b>")
        lines.append("\nQuyidagi menyudan tanlang:")

        _admin_bot_send(token, chat_id, '\n'.join(lines), _ADMIN_MENU_KB)
        return

    if text in ('🆕 Yangi buyurtma', '/neworder'):
        _admin_sessions[chat_id] = {'step': 'order_phone'}
        _admin_bot_send(token, chat_id,
            "📞 <b>Mijoz telefon raqamini yuboring:</b>\nMasalan: <code>+998901234567</code>",
            _CANCEL_KB)
        return

    if text in ('📋 Buyurtmalar', '/orders'):
        qs = (Order.objects.exclude(status__in=['completed', 'cancelled'])
              .select_related('client', 'driver').order_by('-created_at')[:10])
        if not qs:
            _admin_bot_send(token, chat_id, "📋 Hozircha faol buyurtmalar yo'q.", _ADMIN_MENU_KB)
            return
        status_labels = dict(Order.STATUS_CHOICES)
        blocks = []
        for o in qs:
            driver_name = o.driver.full_name if o.driver else '—'
            blocks.append(
                f"<b>#{o.id}</b> — {status_labels.get(o.status, o.status)}\n"
                f"👤 {o.client.phone_number} | 🚖 {driver_name}\n"
                f"📍 {o.from_address}" + (f" → 🏁 {o.to_address}" if o.to_address else '')
            )
        _admin_bot_send(token, chat_id, '📋 <b>Faol buyurtmalar:</b>\n\n' + '\n\n'.join(blocks), _ADMIN_MENU_KB)
        return

    if text in ('🚖 Haydovchilar', '/drivers'):
        qs = Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).order_by('-is_on_duty', 'full_name')[:20]
        if not qs:
            _admin_bot_send(token, chat_id, "🚖 Haydovchilar topilmadi.", _ADMIN_MENU_KB)
            return
        lines = []
        for d in qs:
            status  = "🟢 Navbatda" if d.is_on_duty else "⚪ Navbatda emas"
            blocked = " 🔒 BLOKLANGAN" if not d.is_active else ''
            lines.append(f"<b>#{d.id}</b> {d.full_name} ({d.car_number}) — {status}{blocked}\n💰 {d.balance} UZS")
        lines.append("\n<i>/blok id, /blokoch id, /balans id miqdor</i>")
        _admin_bot_send(token, chat_id, '🚖 <b>Haydovchilar:</b>\n\n' + '\n\n'.join(lines), _ADMIN_MENU_KB)
        return

    if text in ('❓ Yordam', '/help'):
        _admin_bot_send(token, chat_id, _admin_help_text(), _ADMIN_MENU_KB)
        return

    if text in ('🆕 Yangi haydovchilar', '/pending'):
        qs = Driver.objects.filter(approval_status=Driver.APPROVAL_PENDING).order_by('-registered_at')[:20]
        if not qs:
            _admin_bot_send(token, chat_id, "✅ Tasdiqlanishi kerak bo'lgan haydovchilar yo'q.", _ADMIN_MENU_KB)
            return
        lines = []
        for d in qs:
            lines.append(
                f"<b>#{d.id}</b> {d.full_name} | <code>{d.phone_number}</code>\n"
                f"🚗 {d.car_model} | {d.car_number}"
            )
        lines.append("\n<i>/tasdiq id — tasdiqlash, /rad id — rad etish</i>")
        _admin_bot_send(token, chat_id, '🆕 <b>Yangi haydovchilar:</b>\n\n' + '\n\n'.join(lines), _ADMIN_MENU_KB)
        return

    parts = text.split()

    if len(parts) == 2 and parts[0] in ('/blok', '/blokoch') and parts[1].isdigit():
        driver = Driver.objects.filter(pk=int(parts[1])).first()
        if not driver:
            _admin_bot_send(token, chat_id, "❌ Haydovchi topilmadi.")
            return
        unblock = parts[0] == '/blokoch'
        driver.is_active = unblock
        driver.save(update_fields=['is_active'])
        DriverActivityLog.objects.create(
            driver=driver,
            action=DriverActivityLog.ACTION_UNBLOCK if unblock else DriverActivityLog.ACTION_BLOCK,
            detail='Admin (bot) tomonidan ' + ('blok ochildi' if unblock else 'bloklandi'),
        )
        if unblock:
            tg_driver_unblocked(driver)
            _admin_bot_send(token, chat_id, f"🔓 {driver.full_name} blokdan chiqarildi.", _ADMIN_MENU_KB)
        else:
            tg_driver_blocked(driver)
            _admin_bot_send(token, chat_id, f"🔒 {driver.full_name} bloklandi.", _ADMIN_MENU_KB)
        return

    if text in ('📊 Statistika', '/stat', '/statistika', '/hisobot'):
        from django.utils import timezone
        from django.db.models import Sum, Count
        today_start = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        todays = Order.objects.filter(created_at__gte=today_start)
        agg = todays.aggregate(
            total=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled')),
            active=Count('id', filter=Q(status__in=Order.ACTIVE_STATUSES)),
            pending=Count('id', filter=Q(status='pending')),
            revenue=Sum('price', filter=Q(status='completed')),
        )
        on_duty = Driver.objects.filter(is_active=True, is_on_duty=True, approval_status=Driver.APPROVAL_APPROVED).count()
        approved_total = Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).count()
        _admin_bot_send(token, chat_id,
            f"📊 <b>Bugungi statistika</b> ({today_start.strftime('%d.%m.%Y')})\n\n"
            f"🆕 Jami buyurtmalar: {agg['total']}\n"
            f"✅ Yakunlangan: {agg['completed']}\n"
            f"❌ Bekor qilingan: {agg['cancelled']}\n"
            f"⏳ Jarayonda: {agg['active']}\n"
            f"🕐 Kutilmoqda: {agg['pending']}\n"
            f"💰 Tushum: {agg['revenue'] or 0} UZS\n\n"
            f"🚖 Navbatda: {on_duty} / {approved_total} haydovchi",
            _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] in ('/buyurtma', '/qidir') and parts[1].isdigit():
        order = Order.objects.filter(pk=int(parts[1])).select_related('client', 'driver').first()
        if not order:
            _admin_bot_send(token, chat_id, "❌ Buyurtma topilmadi.", _ADMIN_MENU_KB)
            return
        status_labels = dict(Order.STATUS_CHOICES)
        lines = [
            f"📄 <b>Buyurtma #{order.id}</b> — {status_labels.get(order.status, order.status)}",
            f"👤 Mijoz: {order.client.full_name or '—'} | <code>{order.client.phone_number}</code>",
            f"🚖 Haydovchi: {order.driver.full_name if order.driver else '—'}",
            f"📍 {order.from_address}" + (f" → 🏁 {order.to_address}" if order.to_address else ''),
        ]
        if order.distance_km:
            lines.append(f"📏 Masofa: {order.distance_km:.1f} km")
        if order.price:
            lines.append(f"💰 Narx: {order.price} UZS")
        lines.append(f"💳 To'lov: {'Naqd' if order.payment_type == 'cash' else 'Karta'}")
        lines.append(f"🕐 {order.created_at.strftime('%d.%m.%Y %H:%M')}")
        _admin_bot_send(token, chat_id, '\n'.join(lines), _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] == '/bekor' and parts[1].isdigit():
        order = Order.objects.filter(pk=int(parts[1])).select_related('driver').first()
        if not order:
            _admin_bot_send(token, chat_id, "❌ Buyurtma topilmadi.", _ADMIN_MENU_KB)
            return
        if order.status in ('completed', 'cancelled'):
            _admin_bot_send(token, chat_id,
                f"⚠️ Buyurtma #{order.id} allaqachon {dict(Order.STATUS_CHOICES).get(order.status)}.",
                _ADMIN_MENU_KB)
            return
        order.status = 'cancelled'
        order.save(update_fields=['status', 'updated_at'])
        sms_order_status(order, 'cancelled')
        if order.driver:
            from .utils import send_fcm
            send_fcm(
                order.driver.fcm_token,
                title='Buyurtma bekor qilindi',
                body=f"Buyurtma #{order.id} bekor qilindi.",
                data={'type': 'order_cancelled', 'order_id': str(order.id)},
            )
            tg_order_cancelled(order, order.driver)
        else:
            log_panel_event('panel_order_cancelled', f"Buyurtma #{order.id} — admin (bot) tomonidan bekor qilindi")
        _admin_bot_send(token, chat_id, f"❌ Buyurtma #{order.id} bekor qilindi.", _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] == '/qayta' and parts[1].isdigit():
        order = Order.objects.filter(pk=int(parts[1])).select_related('driver').first()
        if not order:
            _admin_bot_send(token, chat_id, "❌ Buyurtma topilmadi.", _ADMIN_MENU_KB)
            return
        reassignable = order.status == 'pending' or (order.driver_id and order.status in Order.ACTIVE_STATUSES)
        if not reassignable:
            _admin_bot_send(token, chat_id,
                f"⚠️ Buyurtma #{order.id} qayta yuborib bo'lmaydi ({dict(Order.STATUS_CHOICES).get(order.status)}).",
                _ADMIN_MENU_KB)
            return
        from .utils import send_fcm
        if order.driver_id and order.status in Order.ACTIVE_STATUSES:
            old_driver = order.driver
            commission = order.commission or TariffSettings.get().commission
            old_driver.balance += Decimal(str(commission))
            old_driver.save(update_fields=['balance'])
            BalanceLog.objects.create(
                driver=old_driver, action=BalanceLog.ACTION_ADD, amount=commission,
                balance_after=old_driver.balance,
                note=f"Komissiya qaytarildi — buyurtma #{order.id} admin (bot) tomonidan qayta ochildi",
            )
            order.rejected_by.add(old_driver)
            order.driver = None
            send_fcm(
                old_driver.fcm_token,
                title='Buyurtma bekor qilindi',
                body=f"Buyurtma #{order.id} qayta ochildi. {commission} so'm balansingizga qaytarildi.",
                data={'type': 'order_cancelled', 'order_id': str(order.id)},
            )
        order.dispatched_to = None
        order.dispatched_at = None
        order.status = 'pending'
        order.save(update_fields=['driver', 'dispatched_to', 'dispatched_at', 'status', 'updated_at'])
        log_panel_event('panel_order_cancelled', f"Buyurtma #{order.id} — admin (bot) tomonidan qayta ochildi")
        if TariffSettings.get().auto_dispatch:
            import threading
            threading.Thread(target=dispatch_order, args=(order,), daemon=True).start()
        _admin_bot_send(token, chat_id, f"🔄 Buyurtma #{order.id} qayta ochildi va eng yaqin haydovchiga yuborilmoqda.", _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] in ('/tasdiq', '/rad') and parts[1].isdigit():
        driver = Driver.objects.filter(pk=int(parts[1]), approval_status=Driver.APPROVAL_PENDING).first()
        if not driver:
            _admin_bot_send(token, chat_id, "❌ Kutilayotgan haydovchi topilmadi.", _ADMIN_MENU_KB)
            return
        if parts[0] == '/tasdiq':
            driver.approval_status = Driver.APPROVAL_APPROVED
            driver.is_active = True
            if driver.user:
                driver.user.is_active = True
                driver.user.save(update_fields=['is_active'])
            driver.save(update_fields=['approval_status', 'is_active'])
            tg_driver_approved(driver)
            _admin_bot_send(token, chat_id, f"✅ {driver.full_name} tasdiqlandi.", _ADMIN_MENU_KB)
        else:
            driver.approval_status = Driver.APPROVAL_REJECTED
            driver.is_active = False
            driver.save(update_fields=['approval_status', 'is_active'])
            tg_driver_rejected(driver)
            _admin_bot_send(token, chat_id, f"🚫 {driver.full_name} rad etildi.", _ADMIN_MENU_KB)
        return

    if len(parts) == 3 and parts[0] == '/balans' and parts[1].isdigit():
        driver = Driver.objects.filter(pk=int(parts[1])).first()
        if not driver:
            _admin_bot_send(token, chat_id, "❌ Haydovchi topilmadi.")
            return
        try:
            amount = Decimal(parts[2])
        except InvalidOperation:
            _admin_bot_send(token, chat_id, "❌ Miqdor noto'g'ri. Masalan: /balans 5 50000")
            return
        action = BalanceLog.ACTION_DEDUCT if amount < 0 else BalanceLog.ACTION_ADD
        driver.balance += amount
        driver.save(update_fields=['balance'])
        BalanceLog.objects.create(
            driver=driver, action=action, amount=abs(amount),
            balance_after=driver.balance, note='Admin (bot)',
        )
        DriverActivityLog.objects.create(
            driver=driver, action=DriverActivityLog.ACTION_BALANCE,
            detail=f"Admin (bot): {'+' if amount >= 0 else ''}{amount} UZS",
        )
        tg_balance_changed(driver, abs(amount), action)
        _admin_bot_send(token, chat_id, f"💰 {driver.full_name} balansi yangilandi: {driver.balance} UZS", _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] in ('/tarix', '/balanstarix') and parts[1].isdigit():
        driver = Driver.objects.filter(pk=int(parts[1])).first()
        if not driver:
            _admin_bot_send(token, chat_id, "❌ Haydovchi topilmadi.", _ADMIN_MENU_KB)
            return
        logs = driver.balance_logs.all()[:10]
        if not logs:
            _admin_bot_send(token, chat_id, f"📄 {driver.full_name} — balans tarixi bo'sh.", _ADMIN_MENU_KB)
            return
        lines = [f"📄 <b>{driver.full_name} — balans tarixi</b>\n"]
        for log in logs:
            sign = '+' if log.action == BalanceLog.ACTION_ADD else '-'
            lines.append(f"{sign}{log.amount} UZS → {log.balance_after} UZS | {log.created_at.strftime('%d.%m %H:%M')}" + (f" | {log.note}" if log.note else ''))
        _admin_bot_send(token, chat_id, '\n'.join(lines), _ADMIN_MENU_KB)
        return

    if text in ('💳 To\'lov so\'rovlari', '/tolovlar'):
        qs = BalanceTopupRequest.objects.filter(status=BalanceTopupRequest.STATUS_PENDING).select_related('driver')[:10]
        if not qs:
            _admin_bot_send(token, chat_id, "✅ Kutilayotgan to'lov so'rovlari yo'q.", _ADMIN_MENU_KB)
            return
        lines = []
        for t in qs:
            lines.append(
                f"<b>#{t.id}</b> {t.driver.full_name} | <code>{t.driver.phone_number}</code>\n"
                f"💰 {t.amount} UZS | {t.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
        lines.append("\n<i>/tolovtasdiq id — tasdiqlash, /tolovrad id — rad etish</i>")
        _admin_bot_send(token, chat_id, "💳 <b>To'lov so'rovlari:</b>\n\n" + '\n\n'.join(lines), _ADMIN_MENU_KB)
        return

    if len(parts) == 2 and parts[0] in ('/tolovtasdiq', '/tolovrad') and parts[1].isdigit():
        topup = BalanceTopupRequest.objects.filter(pk=int(parts[1]), status=BalanceTopupRequest.STATUS_PENDING).select_related('driver').first()
        if not topup:
            _admin_bot_send(token, chat_id, "❌ Kutilayotgan to'lov so'rovi topilmadi.", _ADMIN_MENU_KB)
            return
        from django.utils import timezone
        driver = topup.driver
        if parts[0] == '/tolovtasdiq':
            driver.balance += topup.amount
            driver.save(update_fields=['balance'])
            BalanceLog.objects.create(
                driver=driver, action=BalanceLog.ACTION_ADD, amount=topup.amount,
                balance_after=driver.balance, note=f"To'lov cheki tasdiqlandi #{topup.id}",
            )
            DriverActivityLog.objects.create(
                driver=driver, action=DriverActivityLog.ACTION_BALANCE,
                detail=f"Admin (bot): to'lov cheki #{topup.id} tasdiqlandi, +{topup.amount} UZS",
            )
            topup.status = BalanceTopupRequest.STATUS_APPROVED
            topup.resolved_at = timezone.now()
            topup.save(update_fields=['status', 'resolved_at'])
            tg_balance_changed(driver, topup.amount, BalanceLog.ACTION_ADD)
            _admin_bot_send(token, chat_id, f"✅ To'lov #{topup.id} tasdiqlandi. {driver.full_name} balansi: {driver.balance} UZS", _ADMIN_MENU_KB)
        else:
            topup.status = BalanceTopupRequest.STATUS_REJECTED
            topup.resolved_at = timezone.now()
            topup.save(update_fields=['status', 'resolved_at'])
            _admin_bot_send(token, chat_id, f"🚫 To'lov #{topup.id} rad etildi.", _ADMIN_MENU_KB)
        return

    _admin_bot_send(token, chat_id, "Tushunmadim 🤔\n/help — buyruqlar ro'yxati", _ADMIN_MENU_KB)


@csrf_exempt
def operator_bot_webhook(request):
    """Operator bot webhook — guruhdan callback_query va admin shaxsiy buyruqlarini qayta ishlash."""
    import json as _json
    if request.method != 'POST':
        from django.http import HttpResponse
        return HttpResponse('ok')
    try:
        data = _json.loads(request.body)
    except Exception:
        from django.http import HttpResponse
        return HttpResponse('ok')

    # Shaxsiy chatdan kelgan matnli xabar — whitelist'dagi adminlar uchun buyruqlar
    msg = data.get('message')
    if msg and msg.get('chat', {}).get('type') == 'private':
        from .models import BotSettings
        bot   = BotSettings.get()
        token = bot.bot_token.strip()
        chat_id  = str(msg.get('chat', {}).get('id', ''))
        text     = (msg.get('text') or '').strip()
        location = msg.get('location')
        if token and (text or location) and BotAdmin.objects.filter(chat_id=chat_id, is_active=True).exists():
            _handle_admin_message(token, chat_id, text, location=location)
        from django.http import HttpResponse
        return HttpResponse('ok')

    # Faqat callback_query ni qayta ishlaymiz
    cb = data.get('callback_query')
    if not cb:
        from django.http import HttpResponse
        return HttpResponse('ok')

    cb_id   = cb['id']
    cb_data = cb.get('data', '')

    from .models import BotSettings
    bot = BotSettings.get()
    token = bot.bot_token.strip()
    if not token:
        from django.http import HttpResponse
        return HttpResponse('ok')

    def _answer(text):
        import urllib.request, urllib.parse
        payload = urllib.parse.urlencode({'callback_query_id': cb_id, 'text': text}).encode()
        try:
            urllib.request.urlopen(
                f'https://api.telegram.org/bot{token}/answerCallbackQuery',
                data=payload, timeout=5
            )
        except Exception:
            pass

    # callback_data formatlar: order_<id>, driver_<id>
    if cb_data.startswith('order_'):
        _answer(f"Buyurtma #{cb_data.split('_')[1]} — admin panelda ko'ring")
    elif cb_data.startswith('driver_'):
        _answer(f"Haydovchi #{cb_data.split('_')[1]} — admin panelda ko'ring")
    else:
        _answer('OK')

    from django.http import HttpResponse
    return HttpResponse('ok')


def operator_bot_set_webhook(request):
    """Operator bot webhook URL ni Telegram ga o'rnatish."""
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'message': 'POST talab qilinadi'})
    from .models import BotSettings
    from django.conf import settings as django_settings
    bot = BotSettings.get()
    token = bot.bot_token.strip()
    if not token:
        return JsonResponse({'ok': False, 'message': 'Bot token kiritilmagan'})
    webhook_url = f"{request.scheme}://{request.get_host()}/panel/bot/operator-webhook/"
    import urllib.request, urllib.parse
    try:
        data = urllib.parse.urlencode({'url': webhook_url}).encode()
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{token}/setWebhook',
            data=data,
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            import json as _json
            result = _json.loads(resp.read().decode())
        if result.get('ok'):
            return JsonResponse({'ok': True, 'message': f'Webhook o\'rnatildi: {webhook_url}'})
        return JsonResponse({'ok': False, 'message': result.get('description', 'Xatolik')})
    except Exception as e:
        return JsonResponse({'ok': False, 'message': str(e)})


@login_required(login_url='taxi:panel_login')
def driver_map(request):
    from taxi.models import MapsSettings
    drivers = Driver.objects.filter(
        is_active=True,
        approval_status=Driver.APPROVAL_APPROVED,
        latitude__isnull=False,
        longitude__isnull=False,
    )
    maps = MapsSettings.get()
    return render(request, 'taxi/driver_map.html', {
        'drivers': drivers,
        'yandex_api_key': maps.yandex_mapkit_key,
    })


@login_required(login_url='taxi:panel_login')
def active_drivers_locations(request):
    from django.utils import timezone
    drivers = Driver.objects.filter(
        is_active=True,
        approval_status=Driver.APPROVAL_APPROVED,
        latitude__isnull=False,
        longitude__isnull=False
    )
    now = timezone.now()
    data = []
    for d in drivers:
        is_online = bool(d.last_seen) and (now - d.last_seen).total_seconds() < ONLINE_THRESHOLD_SECONDS
        data.append({
            'id': d.id,
            'full_name': d.full_name,
            'phone_number': d.phone_number,
            'car_model': d.car_model,
            'car_number': d.car_number,
            'latitude': d.latitude,
            'longitude': d.longitude,
            'balance': str(d.balance),
            'last_address': d.last_address or '',
            'photo_url': d.photo.url if d.photo else '',
            'is_online': is_online,
            'is_on_duty': d.is_on_duty,
        })
    return JsonResponse({'drivers': data})


# ── Operator Chat ──────────────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
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

    if request.method == 'POST' and request.POST.get('group_text'):
        text = request.POST.get('group_text', '').strip()
        if text:
            GroupMessage.objects.create(driver=None, sender_name='Operator', text=text)
        return redirect(request.path + ('?driver_id=' + selected_id if selected_id else '') + '#group')

    if request.method == 'POST' and selected_driver:
        text  = request.POST.get('text', '').strip()
        audio = request.FILES.get('audio')
        if text or audio:
            ChatMessage.objects.create(
                driver=selected_driver,
                sender=ChatMessage.SENDER_OPERATOR,
                text=text,
                audio=audio or None,
            )
            if text:
                _send_fcm_to_driver(selected_driver, '💬 Operator', text)
            elif audio:
                _send_fcm_to_driver(selected_driver, '🎤 Operator', 'Ovozli xabar')
        return redirect(f"{request.path}?driver_id={selected_id}")

    return render(request, 'taxi/operator_chat.html', {
        'driver_data':     driver_data,
        'selected_driver': selected_driver,
        'messages':        messages,
        'selected_id':     selected_id,
        'group_messages':  GroupMessage.objects.select_related('driver').order_by('created_at')[:200],
    })


def operator_chat_unread(request):
    """AJAX: jami o'qilmagan xabarlar soni."""
    count = ChatMessage.objects.filter(sender=ChatMessage.SENDER_DRIVER, is_read=False).count()
    return JsonResponse({'unread': count})


@login_required(login_url='taxi:panel_login')
@require_POST
def operator_chat_typing(request):
    """AJAX: operator xabar yozayotganini haydovchi ilovasiga bildirish uchun belgi qo'yadi."""
    from django.utils import timezone
    driver_id = request.POST.get('driver_id')
    driver = Driver.objects.filter(pk=driver_id).first()
    if driver:
        driver.operator_typing_at = timezone.now()
        driver.save(update_fields=['operator_typing_at'])
    return JsonResponse({'ok': True})


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


# ── Login / Logout ─────────────────────────────────────────────────────────────

def panel_login(request):
    if request.user.is_authenticated:
        return redirect('taxi:panel_dashboard')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user and user.is_staff:
            login(request, user)
            return redirect(request.GET.get('next', 'taxi:panel_dashboard'))
        messages.error(request, "Login yoki parol noto'g'ri!")
    return render(request, 'taxi/login.html')


def panel_logout(request):
    logout(request)
    return redirect('taxi:panel_login')


# ── Driver Edit ────────────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def driver_edit(request, pk):
    driver = get_object_or_404(Driver, pk=pk)
    if request.method == 'POST':
        full_name    = request.POST.get('full_name', driver.full_name).strip()
        phone_number = request.POST.get('phone_number', driver.phone_number).strip()
        car_model    = request.POST.get('car_model', driver.car_model).strip()
        car_number   = request.POST.get('car_number', driver.car_number).strip()
        car_type     = request.POST.get('car_type', driver.car_type)
        new_password = request.POST.get('new_password', '').strip()
        if Driver.objects.filter(phone_number=phone_number).exclude(pk=driver.pk).exists():
            messages.error(request, f"Telefon raqami {phone_number} boshqa haydovchiga tegishli.")
        elif new_password and len(new_password) < 6:
            messages.error(request, "Parol kamida 6 ta belgi bo'lishi kerak.")
        else:
            driver.full_name    = full_name
            driver.phone_number = phone_number
            driver.car_model    = car_model
            driver.car_number   = car_number
            driver.car_type     = car_type
            driver.save(update_fields=['full_name', 'phone_number', 'car_model', 'car_number', 'car_type'])
            if new_password:
                if driver.user:
                    driver.user.set_password(new_password)
                    driver.user.save()
                else:
                    messages.error(request, "Haydovchiga bog'langan foydalanuvchi topilmadi, parol o'zgartirilmadi.")
            messages.success(request, "Haydovchi ma'lumotlari yangilandi.")
    return redirect(request.META.get('HTTP_REFERER') or reverse('taxi:driver_detail', args=[pk]))


# ── Order price edit ───────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def order_edit_price(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        from decimal import Decimal, InvalidOperation
        try:
            order.price = Decimal(request.POST.get('price', ''))
            order.save(update_fields=['price'])
        except (InvalidOperation, TypeError):
            pass
    return redirect('taxi:order_detail', pk=pk)


# ── Orders CSV export ──────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def orders_export_csv(request):
    qs = Order.objects.select_related('client', 'driver').order_by('-created_at')
    date_from = request.GET.get('date_from')
    date_to   = request.GET.get('date_to')
    status    = request.GET.get('status')
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    if status:
        qs = qs.filter(status=status)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="orders.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['#', 'Mijoz', 'Telefon', 'Qayerdan', 'Qayerga', 'Haydovchi', 'Narx', "To'lov", 'Holat', 'Vaqt'])
    for o in qs:
        writer.writerow([
            o.id, o.client.full_name or '', o.client.phone_number,
            o.from_address, o.to_address,
            o.driver.full_name if o.driver else '',
            o.price or '', o.get_payment_type_display(),
            o.get_status_display(), o.created_at.strftime('%d.%m.%Y %H:%M'),
        ])
    return response


# ── Statistics ─────────────────────────────────────────────────────────────────

def _statistics_range(request):
    """GET parametrlaridan tahlil qilinadigan sana oralig'ini aniqlaydi:
    ?start=YYYY-MM-DD&end=YYYY-MM-DD berilsa shu oraliq, aks holda ?period=week/month/year."""
    from django.utils import timezone
    from datetime import timedelta, date as date_cls

    today  = timezone.now().date()
    period = request.GET.get('period', 'week')
    start_str = request.GET.get('start')
    end_str   = request.GET.get('end')

    if start_str and end_str:
        try:
            start_date = date_cls.fromisoformat(start_str)
            end_date   = date_cls.fromisoformat(end_str)
            if start_date > end_date:
                start_date, end_date = end_date, start_date
        except ValueError:
            start_date, end_date = today - timedelta(days=6), today
    else:
        days = 30 if period == 'month' else (365 if period == 'year' else 7)
        start_date, end_date = today - timedelta(days=days - 1), today

    return period, start_date, end_date


@login_required(login_url='taxi:panel_login')
def statistics(request):
    from django.db.models import Sum, Count, Avg
    from django.db.models.functions import ExtractHour
    from datetime import timedelta
    from decimal import Decimal

    period, start_date, end_date = _statistics_range(request)
    range_days = (end_date - start_date).days + 1

    labels, revenues, counts = [], [], []
    for i in range(range_days):
        day = start_date + timedelta(days=i)
        day_qs = Order.objects.filter(created_at__date=day)
        labels.append(day.strftime('%d/%m'))
        revenues.append(float(day_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0))
        counts.append(day_qs.count())

    range_qs = Order.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    range_completed_qs = range_qs.filter(status='completed')
    range_orders_count    = range_qs.count()
    range_cancelled_count = range_qs.filter(status='cancelled').count()
    cancellation_rate = round(range_cancelled_count / range_orders_count * 100, 1) if range_orders_count else 0
    range_revenue = float(range_completed_qs.aggregate(s=Sum('price'))['s'] or 0)

    # Oldingi (bir xil uzunlikdagi) davrga nisbatan o'sish foizi
    prev_end_date   = start_date - timedelta(days=1)
    prev_start_date = prev_end_date - timedelta(days=range_days - 1)
    prev_qs = Order.objects.filter(created_at__date__gte=prev_start_date, created_at__date__lte=prev_end_date)
    prev_revenue = float(prev_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0)
    prev_orders_count = prev_qs.count()
    revenue_growth_pct = round((range_revenue - prev_revenue) / prev_revenue * 100, 1) if prev_revenue else None
    orders_growth_pct  = round((range_orders_count - prev_orders_count) / prev_orders_count * 100, 1) if prev_orders_count else None

    # Soatlik yuklama (tanlangan davr bo'yicha, 0-23 soat)
    hourly_counts = [0] * 24
    for row in range_qs.annotate(hour=ExtractHour('created_at')).values('hour').annotate(c=Count('id')):
        hourly_counts[row['hour']] = row['c']

    # Hudud bo'yicha top manzillar (qayerdan)
    top_addresses = list(
        range_qs.exclude(from_address='').values('from_address')
        .annotate(c=Count('id')).order_by('-c')[:10]
    )

    top_drivers = Driver.objects.annotate(
        completed=Count('orders', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date)),
        earned=Sum('orders__price', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date))
    ).filter(completed__gt=0).order_by('-completed')[:10]

    top_clients = Client.objects.annotate(
        total=Count('orders', filter=Q(orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date)),
        spent=Sum('orders__price', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date))
    ).filter(total__gt=0).order_by('-total')[:10]

    total_revenue = Order.objects.filter(status='completed').aggregate(s=Sum('price'))['s'] or Decimal('0')
    avg_price     = Order.objects.filter(status='completed').aggregate(a=Avg('price'))['a'] or Decimal('0')

    return render(request, 'taxi/statistics.html', {
        'period': period, 'labels': labels, 'revenues': revenues, 'counts': counts,
        'start_date': start_date, 'end_date': end_date,
        'custom_range': bool(request.GET.get('start') and request.GET.get('end')),
        'top_drivers': top_drivers, 'top_clients': top_clients,
        'total_revenue': total_revenue, 'avg_price': avg_price,
        'total_orders': Order.objects.count(),
        'completed_orders': Order.objects.filter(status='completed').count(),
        'cancelled_orders': Order.objects.filter(status='cancelled').count(),
        'total_drivers': Driver.objects.filter(approval_status='approved').count(),
        'total_clients': Client.objects.count(),
        'blocked_clients': Client.objects.filter(is_blocked=True).count(),
        'range_revenue': range_revenue,
        'range_orders_count': range_orders_count,
        'cancellation_rate': cancellation_rate,
        'revenue_growth_pct': revenue_growth_pct,
        'orders_growth_pct': orders_growth_pct,
        'hourly_labels': [f"{h:02d}" for h in range(24)],
        'hourly_counts': hourly_counts,
        'top_addresses': top_addresses,
    })


@login_required(login_url='taxi:panel_login')
def statistics_export_csv(request):
    from django.db.models import Sum
    from datetime import timedelta

    period, start_date, end_date = _statistics_range(request)
    range_days = (end_date - start_date).days + 1

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="statistika_{start_date}_{end_date}.csv"'
    response.write('﻿')
    writer = csv.writer(response)

    writer.writerow(['Sana', 'Daromad (UZS)', 'Buyurtmalar soni'])
    for i in range(range_days):
        day = start_date + timedelta(days=i)
        day_qs = Order.objects.filter(created_at__date=day)
        revenue = day_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0
        writer.writerow([day.strftime('%d.%m.%Y'), revenue, day_qs.count()])

    writer.writerow([])
    writer.writerow(['Top haydovchilar', 'Safarlar', 'Daromad (UZS)'])
    top_drivers = Driver.objects.annotate(
        completed=Count('orders', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date)),
        earned=Sum('orders__price', filter=Q(orders__status='completed', orders__created_at__date__gte=start_date, orders__created_at__date__lte=end_date))
    ).filter(completed__gt=0).order_by('-completed')[:20]
    for d in top_drivers:
        writer.writerow([d.full_name, d.completed, d.earned or 0])

    writer.writerow([])
    writer.writerow(['Top hududlar (qayerdan)', 'Buyurtmalar soni'])
    range_qs = Order.objects.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    for row in range_qs.exclude(from_address='').values('from_address').annotate(c=Count('id')).order_by('-c')[:20]:
        writer.writerow([row['from_address'], row['c']])

    return response


# ── Haydovchi shartnomasi ──────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def contract_settings(request):
    contract = ContractSettings.get()
    saved = False
    if request.method == 'POST':
        contract.title   = request.POST.get('title', contract.title).strip()
        contract.content = request.POST.get('content', contract.content).strip()
        contract.save()
        saved = True

    total_approved = Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED).count()
    signed_current = DriverContractSignature.objects.filter(version=contract.version).values('driver').distinct().count()

    return render(request, 'taxi/contract_settings.html', {
        'contract': contract,
        'saved': saved,
        'total_approved': total_approved,
        'signed_current': signed_current,
    })


@login_required(login_url='taxi:panel_login')
def contract_download_blank(request):
    from django.utils.text import slugify
    contract = ContractSettings.get()
    buf = build_contract_pdf(contract)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="shartnoma_namunasi_v{contract.version}.pdf"'
    return response


@login_required(login_url='taxi:panel_login')
def driver_contract_download(request, pk):
    from django.utils.text import slugify
    driver = get_object_or_404(Driver, pk=pk)
    contract = ContractSettings.get()
    signature = driver.contract_signatures.filter(version=contract.version).first()
    if not signature:
        messages.error(request, "Bu haydovchi hali joriy shartnomani imzolamagan.")
        return redirect('taxi:driver_detail', pk=pk)

    buf = build_contract_pdf(contract, driver=driver, signature=signature)
    filename = f"shartnoma_{slugify(driver.full_name) or driver.pk}.pdf"
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


# ── Reklama flayeri ────────────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def flyer_page(request):
    checked_voucher = None
    check_error = None

    if request.method == 'POST' and 'check_code' in request.POST:
        code = request.POST.get('code', '').strip().upper()
        checked_voucher = FlyerVoucher.objects.filter(code=code).select_related('used_by_driver').first()
        if not checked_voucher:
            check_error = "Bunday kod topilmadi — bu flayer soxta bo'lishi mumkin."

    return render(request, 'taxi/flyer.html', {
        'total_vouchers': FlyerVoucher.objects.count(),
        'used_vouchers':  FlyerVoucher.objects.filter(is_used=True).count(),
        'checked_voucher': checked_voucher,
        'check_error': check_error,
        'drivers': Driver.objects.filter(is_active=True, approval_status=Driver.APPROVAL_APPROVED).order_by('full_name'),
    })


@login_required(login_url='taxi:panel_login')
@require_POST
def flyer_download(request):
    try:
        quantity = int(request.POST.get('quantity', 30))
    except (TypeError, ValueError):
        quantity = 30
    quantity = max(3, min(quantity, 300))
    quantity = ((quantity + 2) // 3) * 3  # 3 ga karrali bo'lishi shart (A4'da 3 tadan)

    existing_codes = set(FlyerVoucher.objects.values_list('code', flat=True))
    codes = generate_voucher_codes(quantity, existing=existing_codes)
    FlyerVoucher.objects.bulk_create([FlyerVoucher(code=code) for code in codes])

    buf = build_flyer_pdf(codes)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="vijdon_taxi_flayer.pdf"'
    return response


@login_required(login_url='taxi:panel_login')
@require_POST
def flyer_redeem(request):
    from django.utils import timezone
    code = request.POST.get('code', '').strip().upper()
    driver_id = request.POST.get('driver_id', '').strip()
    voucher = get_object_or_404(FlyerVoucher, code=code)

    if voucher.is_used:
        messages.error(request, "Bu kod allaqachon ishlatilgan.")
        return redirect('taxi:flyer_page')
    if not driver_id:
        messages.error(request, "Haydovchini tanlang.")
        return redirect('taxi:flyer_page')

    driver = get_object_or_404(Driver, pk=driver_id)
    amount = voucher.amount

    voucher.is_used = True
    voucher.used_at = timezone.now()
    voucher.used_by_driver = driver
    voucher.verified_by = request.user
    voucher.save(update_fields=['is_used', 'used_at', 'used_by_driver', 'verified_by'])

    driver.balance += amount
    driver.save(update_fields=['balance'])
    BalanceLog.objects.create(
        driver=driver, action='add', amount=amount,
        balance_after=driver.balance, note=f"Flayer kuponi: {voucher.code}"
    )
    DriverActivityLog.objects.create(
        driver=driver, action=DriverActivityLog.ACTION_BALANCE,
        detail=f"+{amount} UZS (flayer kuponi {voucher.code})",
        ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )
    tg_balance_changed(driver, amount, 'add')
    tg_flyer_voucher_redeemed(voucher, driver)
    messages.success(request, f"Kod tasdiqlandi — {driver.full_name} balansiga {amount} so'm qo'shildi.")
    return redirect('taxi:flyer_page')


# ── Vazifalar (Task board) ────────────────────────────────────────────────────

@login_required(login_url='taxi:panel_login')
def task_list(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if title:
            Task.objects.create(title=title, created_by=request.user)
        return redirect('taxi:task_list')

    tasks = Task.objects.select_related('created_by').all()
    return render(request, 'taxi/tasks.html', {
        'todo_tasks':  tasks.filter(status=Task.STATUS_TODO),
        'doing_tasks': tasks.filter(status=Task.STATUS_DOING),
        'done_tasks':  tasks.filter(status=Task.STATUS_DONE),
    })


@login_required(login_url='taxi:panel_login')
@require_POST
def task_set_status(request, pk):
    from django.utils import timezone
    task = get_object_or_404(Task, pk=pk)
    status = request.POST.get('status', '')
    if status not in dict(Task.STATUS_CHOICES):
        return JsonResponse({'ok': False, 'error': "Noto'g'ri holat"}, status=400)
    task.status = status
    task.completed_at = timezone.now() if status == Task.STATUS_DONE else None
    task.save(update_fields=['status', 'completed_at', 'updated_at'])
    return JsonResponse({'ok': True})


@login_required(login_url='taxi:panel_login')
@require_POST
def task_delete(request, pk):
    Task.objects.filter(pk=pk).delete()
    return JsonResponse({'ok': True})
