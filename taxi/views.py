from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Order, Driver, Client, TariffSettings, ChatMessage, MapsSettings, DriverActivityLog, BotSettings, BotAdmin, SosAlert, BalanceLog, GroupMessage, PanelEvent, PanelSound
from .utils import haversine, find_nearest_driver, send_telegram, dispatch_order, tg_new_order, tg_driver_registered, tg_driver_approved, tg_driver_rejected, tg_driver_blocked, tg_driver_unblocked, tg_balance_changed, tg_order_cancelled, log_panel_event, reverse_geocode_address
import csv


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
    return render(request, 'taxi/driver_detail.html', {
        'driver': driver,
        'logs':   logs,
        'orders': orders,
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
    orders = Order.objects.select_related('client', 'driver').order_by('-created_at')[:10]
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

    # So'nggi 7 kunlik statistika (grafik uchun)
    from datetime import timedelta
    weekly_labels, weekly_revenue, weekly_counts = [], [], []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_qs = Order.objects.filter(created_at__date=day)
        weekly_labels.append(day.strftime('%d/%m'))
        weekly_revenue.append(float(day_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0))
        weekly_counts.append(day_qs.count())

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
        'tariff':               TariffSettings.get(),
        'total_revenue':        total_revenue,
        'today_revenue':        today_revenue,
        'today_orders':         today_orders,
        'avg_price':            avg_price,
        'weekly_labels':        weekly_labels,
        'weekly_revenue':       weekly_revenue,
        'weekly_counts':        weekly_counts,
    }
    return render(request, 'taxi/panel.html', context)


@login_required(login_url='taxi:panel_login')
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


@login_required(login_url='taxi:panel_login')
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


@login_required(login_url='taxi:panel_login')
def client_list(request):
    q      = request.GET.get('q', '').strip()
    filter_ = request.GET.get('filter', '').strip()
    qs = Client.objects.all()
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(phone_number__icontains=q))
    if filter_ == 'blocked':
        qs = qs.filter(is_blocked=True)
    elif filter_ == 'active':
        qs = qs.filter(is_blocked=False)
    return render(request, 'taxi/client_list.html', {'clients': qs, 'q': q, 'filter': filter_})


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
        bot.save()
        # SITE_URL ni settings ga yozish
        site_url = request.POST.get('site_url', '').strip()
        if site_url:
            django_settings.SITE_URL = site_url
        # Test xabar yuborish
        if 'test' in request.POST and bot.bot_token and bot.group_id:
            from .utils import send_telegram
            send_telegram('✅ <b>VijdonTaxi bot ulanishi muvaffaqiyatli!</b>\nBu test xabari.')
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
    ]
    return render(request, 'taxi/bot_settings.html', {
        'bot': bot,
        'site_url': site_url,
        'order_notifs': order_notifs,
        'driver_notifs': driver_notifs,
        'admins': BotAdmin.objects.all(),
    })


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
        [{'text': '📊 Statistika'}, {'text': '❓ Yordam'}],
    ],
    'resize_keyboard': True,
}

_LOCATION_KB = {
    'keyboard': [[{'text': '📍 Joylashuvni yuborish', 'request_location': True}]],
    'resize_keyboard': True,
}

_LOCATION_OR_SKIP_KB = {
    'keyboard': [
        [{'text': '📍 Joylashuvni yuborish', 'request_location': True}],
        [{'text': "O'tkazib yuborish ➡️"}],
    ],
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
        "📊 Statistika — bugungi buyurtmalar va tushum hisoboti\n"
        "/buyurtma &lt;id&gt; — buyurtma haqida to'liq ma'lumot\n"
        "/bekor &lt;id&gt; — buyurtmani bekor qilish\n"
        "/qayta &lt;id&gt; — buyurtmani qayta ochish va eng yaqin haydovchiga qayta yuborish\n"
        "/blok &lt;id&gt; — haydovchini bloklash\n"
        "/blokoch &lt;id&gt; — haydovchini blokdan chiqarish\n"
        "/balans &lt;id&gt; &lt;miqdor&gt; — balans qo'shish (ayirish uchun manfiy son, masalan -20000)"
    )


def _handle_admin_message(token, chat_id, text, location=None):
    """Admin (whitelist'dagi) shaxsiy chatdan yuborgan xabarni qayta ishlaydi."""
    from decimal import Decimal, InvalidOperation

    session = _admin_sessions.get(chat_id, {})
    step = session.get('step')

    # ── Yangi buyurtma yaratish oqimi ──
    if step == 'order_phone':
        phone = text.replace(' ', '')
        if len(phone) < 9:
            _admin_bot_send(token, chat_id, "❌ Telefon raqam noto'g'ri. Qayta kiriting:")
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
        _admin_bot_send(token, chat_id,
            "👋 <b>Admin panel botiga xush kelibsiz!</b>\nQuyidagi menyudan tanlang:",
            _ADMIN_MENU_KB)
        return

    if text in ('🆕 Yangi buyurtma', '/neworder'):
        _admin_sessions[chat_id] = {'step': 'order_phone'}
        _admin_bot_send(token, chat_id,
            "📞 <b>Mijoz telefon raqamini yuboring:</b>\nMasalan: <code>+998901234567</code>")
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
        is_on_duty=True,
        approval_status=Driver.APPROVAL_APPROVED
    )
    maps = MapsSettings.get()
    return render(request, 'taxi/driver_map.html', {
        'drivers': drivers,
        'yandex_api_key': maps.yandex_mapkit_key,
    })


@login_required(login_url='taxi:panel_login')
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
            'last_address': d.last_address or '',
            'photo_url': d.photo.url if d.photo else '',
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
        driver.full_name    = request.POST.get('full_name', driver.full_name).strip()
        driver.phone_number = request.POST.get('phone_number', driver.phone_number).strip()
        driver.car_model    = request.POST.get('car_model', driver.car_model).strip()
        driver.car_number   = request.POST.get('car_number', driver.car_number).strip()
        driver.car_type     = request.POST.get('car_type', driver.car_type)
        driver.save(update_fields=['full_name', 'phone_number', 'car_model', 'car_number', 'car_type'])
        messages.success(request, "Haydovchi ma'lumotlari yangilandi.")
    return redirect('taxi:driver_detail', pk=pk)


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

@login_required(login_url='taxi:panel_login')
def statistics(request):
    from django.utils import timezone
    from django.db.models import Sum, Count, Avg
    from datetime import timedelta
    from decimal import Decimal

    today  = timezone.now().date()
    period = request.GET.get('period', 'week')
    days   = 30 if period == 'month' else (365 if period == 'year' else 7)

    labels, revenues, counts = [], [], []
    for i in range(days - 1, -1, -1):
        day = today - timedelta(days=i)
        day_qs = Order.objects.filter(created_at__date=day)
        labels.append(day.strftime('%d/%m'))
        revenues.append(float(day_qs.filter(status='completed').aggregate(s=Sum('price'))['s'] or 0))
        counts.append(day_qs.count())

    top_drivers = Driver.objects.annotate(
        completed=Count('orders', filter=Q(orders__status='completed')),
        earned=Sum('orders__price', filter=Q(orders__status='completed'))
    ).filter(completed__gt=0).order_by('-completed')[:10]

    top_clients = Client.objects.annotate(
        total=Count('orders'),
        spent=Sum('orders__price', filter=Q(orders__status='completed'))
    ).filter(total__gt=0).order_by('-total')[:10]

    total_revenue = Order.objects.filter(status='completed').aggregate(s=Sum('price'))['s'] or Decimal('0')
    avg_price     = Order.objects.filter(status='completed').aggregate(a=Avg('price'))['a'] or Decimal('0')

    return render(request, 'taxi/statistics.html', {
        'period': period, 'labels': labels, 'revenues': revenues, 'counts': counts,
        'top_drivers': top_drivers, 'top_clients': top_clients,
        'total_revenue': total_revenue, 'avg_price': avg_price,
        'total_orders': Order.objects.count(),
        'completed_orders': Order.objects.filter(status='completed').count(),
        'cancelled_orders': Order.objects.filter(status='cancelled').count(),
        'total_drivers': Driver.objects.filter(approval_status='approved').count(),
        'total_clients': Client.objects.count(),
        'blocked_clients': Client.objects.filter(is_blocked=True).count(),
    })
