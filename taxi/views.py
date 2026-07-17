from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.http import JsonResponse
from .models import Order, Driver, Client, TariffSettings, ChatMessage, MapsSettings, DriverActivityLog, BotSettings, SosAlert
from .utils import haversine, find_nearest_driver, send_telegram, dispatch_order, tg_new_order, tg_driver_registered, tg_driver_approved, tg_driver_rejected, tg_driver_blocked, tg_driver_unblocked, tg_balance_changed


def _get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ── Order ──────────────────────────────────────────────────────────────────────

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
            tg_new_order(order)

            # Dispatch — faqat koordinata belgilangan bo'lsa eng yaqin haydovchiga yuboriladi
            # Koordinata yo'q (qo'lda yozilgan manzil) → umumiy tabloda qoladi, hammaga ko'rinadi
            if has_coords and driver is None:
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
        action = DriverActivityLog.ACTION_UNBLOCK if driver.is_active else DriverActivityLog.ACTION_BLOCK
        detail = 'Admin tomonidan ' + ('blok ochildi' if driver.is_active else 'bloklandi')
        DriverActivityLog.objects.create(driver=driver, action=action, detail=detail,
            ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''))
        if driver.is_active:
            tg_driver_unblocked(driver)
        else:
            tg_driver_blocked(driver)
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
            tg_driver_approved(driver)
        elif action == 'reject':
            driver.approval_status = Driver.APPROVAL_REJECTED
            driver.is_active = False
            tg_driver_rejected(driver)
        driver.save(update_fields=['approval_status', 'is_active'])
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


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
            DriverActivityLog.objects.create(driver=driver, action=DriverActivityLog.ACTION_BALANCE, detail=detail,
                ip_address=_get_client_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''))
            tg_balance_changed(driver, amount, action)
        except (ValueError, TypeError, Exception):
            pass
    return redirect(request.META.get('HTTP_REFERER', 'taxi:driver_list'))


# ── Driver Detail ─────────────────────────────────────────────────────────────

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


def client_block_toggle(request, pk):
    client = get_object_or_404(Client, pk=pk)
    if request.method == 'POST':
        client.is_blocked = not client.is_blocked
        client.save(update_fields=['is_blocked'])
    return redirect('taxi:client_list')


# ── Pages ──────────────────────────────────────────────────────────────────────

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

def bot_settings(request):
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
        # Test xabar yuborish
        if 'test' in request.POST and bot.bot_token and bot.group_id:
            from .utils import send_telegram
            send_telegram('✅ <b>VijdonTaxi bot ulanishi muvaffaqiyatli!</b>\nBu test xabari.')
        return redirect('taxi:bot_settings')
    return render(request, 'taxi/bot_settings.html', {'bot': bot})


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


# ── SOS ──────────────────────────────────────────────────────────────────────────────

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
