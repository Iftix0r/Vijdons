"""
Haydovchi Web UI views — WebView ilovasi uchun.
URL prefix: /driver/
"""
import json
import os
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Driver, Order, ChatMessage, GroupMessage, TariffSettings, DriverActivityLog, BalanceLog, BalanceTopupRequest, PanelSound, VoiceParticipant, VoiceSignal, ContractSettings, DriverContractSignature
from .utils import tg_order_accepted, tg_order_on_way, tg_order_arrived, tg_order_completed, tg_order_cancelled, tg_order_rejected, tg_driver_login, tg_duty_changed, tg_low_balance_alert, tg_topup_request, sms_order_status


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _log_activity(driver, action, detail, request):
    DriverActivityLog.objects.create(
        driver=driver, action=action, detail=detail,
        ip_address=_get_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', ''),
    )


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


def _pending_orders_count(driver):
    """Haydovchiga hozir ko'rinadigan, hali qabul qilinmagan buyurtmalar soni — tab-bardagi Asosiy belgisi uchun."""
    from django.db.models import Q
    from django.utils import timezone
    from .utils import haversine
    dispatch_cutoff = timezone.now() - timezone.timedelta(seconds=TariffSettings.get().dispatch_timeout)
    qs = Order.objects.filter(
        Q(status='pending', dispatched_to=driver) |
        Q(status='pending', dispatched_to__isnull=True) |
        Q(status='pending', dispatched_at__lt=dispatch_cutoff)
    )
    if driver.destination_mode and driver.destination_lat and driver.destination_lng:
        count = 0
        for o in qs:
            if o.to_lat and o.to_lng:
                d = haversine(o.to_lat, o.to_lng, driver.destination_lat, driver.destination_lng)
                if d is not None and d <= 5:
                    count += 1
        return count
    return qs.count()


def _active_orders_count(driver):
    """Haydovchining hali yakunlanmagan (accepted/on_way/arrived) buyurtmalari soni — tab-bardagi Tarix belgisi uchun."""
    return Order.objects.filter(driver=driver, status__in=Order.ACTIVE_STATUSES).count()


def driver_service_worker(request):
    """Service Worker faylini /driver/ ostidan xizmat qiladi (Web Push uchun).
    /static/driver/sw.js dan farqli — bu yerda skriptning o'zi allaqachon
    /driver/ ostida bo'lgani uchun {scope:'/driver/'} bilan ro'yxatdan
    o'tkazish (base.html) hech qanday qo'shimcha sozlashsiz to'g'ri ishlaydi
    (aks holda brauzer "scope ruxsat etilgan maksimal doiradan tashqarida"
    degan xato berardi, chunki /static/ ostidagi skript standart holda
    faqat /static/ doirasini boshqara oladi)."""
    with open(os.path.join(settings.BASE_DIR, 'taxi', 'static', 'driver', 'sw.js'), 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/javascript')
    # Brauzer HTTP darajasida ushbu javobni keshlab qo'ymasin — aks holda
    # reg.update() chaqiruvi ham eski (HTTP keshidagi) nusxani solishtirib,
    # yangilanishni sezmay qolishi mumkin edi.
    response['Cache-Control'] = 'no-cache'
    return response


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
                    request.session['vj_just_logged_in'] = True
                    _log_activity(driver, DriverActivityLog.ACTION_LOGIN, 'Saytdan kirdi', request)
                    tg_driver_login(driver, ip=_get_ip(request))
                    return redirect('driver:home')
                else:
                    login(request, user)
                    request.session['vj_just_logged_in'] = True
                    _log_activity(driver, DriverActivityLog.ACTION_LOGIN, 'Saytdan kirdi', request)
                    tg_driver_login(driver, ip=_get_ip(request))
                    return redirect('driver:home')
    return render(request, 'driver/login.html', {'error': error})


def driver_logout_view(request):
    if request.user.is_authenticated:
        try:
            driver = request.user.driver_profile
            _log_activity(driver, DriverActivityLog.ACTION_LOGOUT, 'Saytdan chiqdi', request)
        except Driver.DoesNotExist:
            pass
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
            'car_type':     request.POST.get('car_type', 'light'),
            'password':     request.POST.get('password', ''),
        }
        s = DriverRegisterSerializer(data=data)
        if s.is_valid():
            s.save()
            return render(request, 'driver/register_done.html')
        error = ' '.join([str(v[0]) for v in s.errors.values()])
    return render(request, 'driver/register.html', {'error': error, 'car_type_choices': Driver.CAR_TYPE_CHOICES})


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
    from django.utils import timezone
    from .utils import haversine

    _tariff = TariffSettings.get()

    # Haydovchi "Asosiy" sahifani ochganda avtomatik navbatga chiqadi — buning
    # uchun endi "Liniyaga chiqish" tugmasini bosish shart emas. Balans kam
    # bo'lsa ham navbatga chiqaveradi — u baribir buyurtmalarni ko'radi,
    # faqat balans yetmasa qabul qila olmaydi (order_status'dagi tekshiruv).
    if not driver.is_on_duty:
        driver.is_on_duty = True
        driver.save(update_fields=['is_on_duty'])

    # Dispatch muddati o'tgan buyurtmalar (masalan, avtomatik qayta-yuborish
    # jarayoni server qayta ishga tushishi/ishchi jarayon almashinishi sababli
    # bajarilmay qolgan bo'lsa) hamma haydovchiga ko'rinadigan bo'lsin — aks
    # holda ular abadiy faqat bitta (javob bermagan) haydovchiga "osilib qoladi"
    dispatch_cutoff = timezone.now() - timezone.timedelta(seconds=_tariff.dispatch_timeout)

    # Haydovchida bajarilayotgan buyurtma(lar) (accepted/on_way/arrived)
    # bo'lsa ham — ular Order.MAX_ACTIVE_PER_DRIVER (hozircha 2) tagacha bo'lsa,
    # haydovchi yana bitta yangi buyurtma qabul qila oladi, shu sabab pending
    # buyurtmalar HAM ko'rsatiladi va bildirishnoma keladi. Faqat allaqachon
    # limitga yetgan bo'lsa, yangi (hali hech kim olmagan) buyurtmalar
    # ko'rsatilmaydi — aks holda qabul qilib bo'lmaydigan narsani ko'rsatib,
    # haydovchini chalg'itardik.
    active_orders = list(Order.objects.filter(
        driver=driver, status__in=Order.ACTIVE_STATUSES
    ).select_related('client', 'driver'))

    if len(active_orders) >= Order.MAX_ACTIVE_PER_DRIVER:
        base_qs = active_orders
    else:
        # Diqqat: haydovchi avval "Rad etish" bosgan bo'lsa ham, agar buyurtma
        # hali ham hech kim tomonidan olinmagan (pending) bo'lib qolsa, umumiy
        # ro'yxatda ko'rinishda davom etadi — rad etish faqat avtomatik
        # yuborish (dispatch) navbatidan chiqarib yuboradi, buyurtmani
        # butunlay yashirmaydi.
        pending_qs = Order.objects.select_related('client', 'driver').filter(
            Q(status='pending', dispatched_to=driver) |
            Q(status='pending', dispatched_to__isnull=True) |
            Q(status='pending', dispatched_at__lt=dispatch_cutoff)
        ).exclude(
            status__in=['cancelled', 'completed']
        ).order_by('-created_at')
        base_qs = active_orders + list(pending_qs)

    # Destination mode: faqat yo'nalish atrofidagi buyurtmalar
    if driver.destination_mode and driver.destination_lat and driver.destination_lng:
        filtered = []
        for o in base_qs:
            if o.status != 'pending':
                filtered.append(o)
                continue
            if o.to_lat and o.to_lng:
                d = haversine(o.to_lat, o.to_lng, driver.destination_lat, driver.destination_lng)
                if d is not None and d <= 5:  # 5 km radius
                    filtered.append(o)
        orders = filtered
    else:
        orders = list(base_qs)

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
            'from_lat':     o.from_lat,
            'from_lng':     o.from_lng,
            'to_address':   o.to_address,
            'to_lat':       o.to_lat,
            'to_lng':       o.to_lng,
            'client_name':  o.client.full_name or 'Mijoz',
            'client_phone': o.client.phone_number if o.status != 'pending' else _mask_phone(o.client.phone_number),
            'price':        str(o.price) if o.price else None,
            'distance_km':  o.distance_km,
            'payment_type': o.payment_type,
            'car_type':     o.car_type,
            'car_type_display': o.get_car_type_display(),
            'note':         o.note or '',
            'commission':   str(o.commission) if o.commission else None,
            'is_dispatched': o.dispatched_to_id == driver.id,
            'timer_sec':    timer_sec,
            'tmx_dist_km':  o.tmx_dist_km or 0,
            'tmx_start_time': o.tmx_start_time.isoformat() if o.tmx_start_time else None,
            'tmx_paused':    o.tmx_paused,
            'tmx_paused_ms': o.tmx_paused_ms or 0,
        })

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
        # Login sahifasida "Kirish"ni bosgandan keyingi ilk sahifa yuklanishida
        # bir marta "Xush kelibsiz" ovozini chalish uchun — sahifani yangilasa
        # (F5) qayta chalinmasligi uchun session'dan darhol olib tashlanadi.
        'just_logged_in': request.session.pop('vj_just_logged_in', False),
        'chat_unread': _chat_unread(driver),
        # Tab-bar belgilari uchun — bu yerda allaqachon yuklangan `orders`dan
        # hisoblaymiz, qayta so'rov yubormaslik uchun
        'pending_orders_count': sum(1 for o in orders if o.status == 'pending'),
        'active_orders_count': sum(1 for o in orders if o.status in ('accepted', 'on_way', 'arrived')),
        'tariff':      _tariff,
        'tariff_base_price': int(_tariff.base_price),
        'tariff_per_km': int(_tariff.price_per_km),
        'tariff_commission': int(_tariff.commission),
        'max_active_orders': Order.MAX_ACTIVE_PER_DRIVER,
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
    # Dispatch muddati o'tgan buyurtmalar (avtomatik qayta-yuborish bajarilmay
    # qolgan bo'lsa ham) hamma haydovchiga ko'rinsin — driver_home dagi bilan bir xil
    dispatch_cutoff = timezone.now() - timezone.timedelta(seconds=TariffSettings.get().dispatch_timeout)

    # Haydovchi hozir biror buyurtmani bajarayotgan bo'lsa ham — driver_home
    # dagi bilan bir xil mantiq: Order.MAX_ACTIVE_PER_DRIVER ga yetmagan bo'lsa,
    # yana bitta buyurtma qabul qilishi mumkin, shu sabab pending buyurtmalar
    # ham ko'rinadi/bildirishnoma keladi.
    active_orders = list(Order.objects.filter(
        driver=driver, status__in=Order.ACTIVE_STATUSES
    ).select_related('client'))

    if len(active_orders) >= Order.MAX_ACTIVE_PER_DRIVER:
        qs = active_orders
    else:
        # rad etilgan bo'lsa ham, hali hech kim olmagan (pending) buyurtma
        # umumiy ro'yxatda ko'rinishda davom etadi — driver_home dagi bilan
        # bir xil mantiq
        pending_qs = Order.objects.select_related('client').filter(
            Q(status='pending', dispatched_to=driver) |
            Q(status='pending', dispatched_to__isnull=True) |
            Q(status='pending', dispatched_at__lt=dispatch_cutoff)
        ).exclude(
            status__in=['cancelled', 'completed']
        ).order_by('-created_at')
        qs = active_orders + list(pending_qs)

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
            'from_lat':      o.from_lat,
            'from_lng':      o.from_lng,
            'to_address':    o.to_address,
            'to_lat':        o.to_lat,
            'to_lng':        o.to_lng,
            'client_name':   o.client.full_name or 'Mijoz',
            'client_phone':  o.client.phone_number if o.status != 'pending' else _mask_phone(o.client.phone_number),
            'price':         str(o.price) if o.price else None,
            'distance_km':   o.distance_km,
            'payment_type':  o.payment_type,
            'car_type':      o.car_type,
            'car_type_display': o.get_car_type_display(),
            'note':          o.note or '',
            'commission':    str(o.commission) if o.commission else None,
            'is_dispatched': o.dispatched_to_id == driver.id,
            'timer_sec':     timer_sec,
            'tmx_dist_km':   o.tmx_dist_km or 0,
            'tmx_start_time': o.tmx_start_time.isoformat() if o.tmx_start_time else None,
            'tmx_paused':    o.tmx_paused,
            'tmx_paused_ms': o.tmx_paused_ms or 0,
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
            _log_activity(driver, DriverActivityLog.ACTION_ORDER, f"Buyurtma #{order.id} rad etildi", request)
            if order.dispatched_to_id == driver.id:
                order.dispatched_to = None
                order.save(update_fields=['dispatched_to'])
                tg_order_rejected(order, driver)
                import threading
                from .utils import dispatch_order
                threading.Thread(target=dispatch_order, args=(order,), daemon=True).start()
        return JsonResponse({'ok': True})

    # Haydovchi endi qabul qilingan buyurtmani o'zi bekor qila olmaydi — bekor
    # qilish uchun operatorga qo'ng'iroq qilishi kerak (operator komissiyani
    # qaytaradi va buyurtmani boshqa haydovchilarga ochadi). Shu bilan birga,
    # UI'dagi tugma ham qo'ng'iroqqa yo'naltiriladi (taxi/templates/driver/home.html,
    # history.html) — bu yerdagi tekshiruv shunchaki himoya qatlami.
    if action == 'cancel':
        tariff = TariffSettings.get()
        return JsonResponse({
            'ok': False,
            'error': f"Buyurtmani bekor qilish uchun operatorga qo'ng'iroq qiling: {tariff.operator_phone}",
        }, status=403)

    allowed = {
        'accept':   (['pending'],                  'accepted'),
        'on_way':   (['accepted'],                 'on_way'),
        'arrived':  (['on_way'],                   'arrived'),
        'complete': (['arrived', 'on_way', 'accepted'], 'completed'),
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
            # Diqqat (xavfsizlik): buyurtma hozir aniq bir haydovchiga
            # (dispatched_to) navbat bilan yuborilgan bo'lsa, o'sha oynada
            # FAQAT o'sha haydovchi qabul qila oladi — aks holda boshqa
            # haydovchi to'g'ridan-to'g'ri pk bilan so'rov yuborib, navbatni
            # chetlab o'tib olishi mumkin edi (mobil API'dagi _order_action
            # bu tekshiruvni allaqachon qilardi, veb panel yo'q edi).
            if locked.dispatched_to_id and locked.dispatched_to_id != driver.id:
                return JsonResponse({'ok': False, 'error': 'Bu buyurtma sizga yuborilmagan'}, status=403)
            active_count = Order.objects.filter(driver=driver, status__in=Order.ACTIVE_STATUSES).count()
            if active_count >= Order.MAX_ACTIVE_PER_DRIVER:
                return JsonResponse({
                    'ok': False,
                    'error': f"Bir vaqtda ko'pi bilan {Order.MAX_ACTIVE_PER_DRIVER} ta faol buyurtma olish mumkin. Avval joriy buyurtma(lar)ni yakunlang.",
                }, status=400)
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
        tg_low_balance_alert(driver)
        sms_order_status(locked, 'accepted')
        _log_activity(driver, DriverActivityLog.ACTION_ORDER, f"Buyurtma #{locked.id} qabul qilindi, -{commission} UZS komissiya", request)
        return JsonResponse({'ok': True, 'new_balance': float(driver.balance)})

    if order.driver_id and order.driver_id != driver.id:
        return JsonResponse({'ok': False, 'error': 'Bu buyurtma sizga tegishli emas'}, status=403)

    order.status = new_status
    update_fields = ['status', 'updated_at']

    # Taximetr boshlangan haqiqiy vaqtini saqlaymiz — ilova qayta ochilganda ham
    # o'tgan vaqt to'g'ri hisoblansin (frontendda Date.now() qayta boshlanib ketmasin)
    if new_status == 'on_way' and not order.tmx_start_time:
        from django.utils import timezone
        order.tmx_start_time = timezone.now()
        update_fields.append('tmx_start_time')

    # Taximeter ma'lumotlarini saqlash (arrived, complete)
    # distance_km va tmx_dist_km har doim birga yangilanadi — aks holda
    # davriy /meter/ autosave ulgurmagan holatlarda (masalan darhol Tarixga
    # o'tilsa) ikkala maydon bir-biridan uzilib, biri eski/0 bo'lib qolardi.
    try:
        tmx_dist = request.POST.get('tmx_dist_km')
        tmx_price = request.POST.get('tmx_price')
        if tmx_dist and float(tmx_dist) > 0:
            order.distance_km = round(float(tmx_dist), 2)
            order.tmx_dist_km = round(float(tmx_dist), 2)
            update_fields.append('distance_km')
            update_fields.append('tmx_dist_km')
        if tmx_price and float(tmx_price) > 0:
            order.price = round(float(tmx_price), 2)
            update_fields.append('price')
    except Exception:
        pass

    # Zaxira hisoblash: haydovchi "Yo'lga chiqdim"ni bosmay, to'g'ridan-to'g'ri
    # "Yakunlash"ni bossa (accepted -> completed), taximetr umuman ishlamagan
    # bo'ladi va yuqoridagi tmx qiymatlari bo'sh keladi. Bunday holda buyurtma
    # narxsiz/masofasiz abadiy "—" bo'lib qolib ketmasligi uchun, tarif asosida
    # hisoblab qo'yamiz (xuddi mobil API'dagi order_complete kabi).
    if new_status == 'completed':
        if order.distance_km is None and order.from_lat and order.from_lng and order.to_lat and order.to_lng:
            from .utils import haversine
            calc_dist = haversine(order.from_lat, order.from_lng, order.to_lat, order.to_lng)
            if calc_dist:
                order.distance_km = round(calc_dist, 2)
                if 'distance_km' not in update_fields:
                    update_fields.append('distance_km')
        if order.price is None:
            tariff = TariffSettings.get()
            waiting_minutes = (order.tmx_paused_ms or 0) / 60000
            order.price = (
                tariff.calc_price(order.distance_km, waiting_minutes)
                if order.distance_km is not None else tariff.base_price
            )
            if 'price' not in update_fields:
                update_fields.append('price')

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
    if new_status in ('arrived', 'completed', 'cancelled'):
        sms_order_status(order, new_status)

    _log_activity(driver, DriverActivityLog.ACTION_ORDER, f"Buyurtma #{order.id} — {order.get_status_display()}", request)

    return JsonResponse({'ok': True})


# ── History ───────────────────────────────────────────────────────────────────

@driver_login_required
def driver_history(request, driver):
    from django.db.models import Sum, Count, Q as DQ
    from django.utils import timezone
    import datetime

    period = request.GET.get('period', 'all')  # all, today, week, month
    qs = Order.objects.filter(driver=driver)

    now = timezone.now()
    if period == 'today':
        qs = qs.filter(created_at__date=now.date())
    elif period == 'week':
        qs = qs.filter(created_at__gte=now - datetime.timedelta(days=7))
    elif period == 'month':
        qs = qs.filter(created_at__gte=now - datetime.timedelta(days=30))

    orders = qs.order_by('-created_at')[:100]
    stats = qs.aggregate(
        total_earned=Sum('price', filter=DQ(status='completed')),
        completed=Count('id', filter=DQ(status='completed')),
    )
    _tariff = TariffSettings.get()
    return render(request, 'driver/history.html', {
        'driver':         driver,
        'orders':         orders,
        'total_earned':   stats['total_earned'] or 0,
        'active_tab':     'history',
        'chat_unread':    _chat_unread(driver),
        'pending_orders_count': _pending_orders_count(driver),
        'active_orders_count': _active_orders_count(driver),
        'period':         period,
        'period_choices': [('all','Barchasi'),('today','Bugun'),('week','7 kun'),('month','30 kun')],
        'tariff_base_price': int(_tariff.base_price),
        'tariff_per_km': int(_tariff.price_per_km),
    })


# ── Mustaqil taksometr (yo'l-yo'lakay olingan qo'shimcha mijoz uchun) ────────
# Dispetcherlik orqali kelmagan, haydovchi o'zi yo'lda olib ketayotgan mijoz
# uchun. Asosiy buyurtma taksometridan farqli — bu butunlay mustaqil, faol
# buyurtma (accepted/on_way/arrived) sifatida saqlanmaydi (aks holda Asosiy
# sahifadagi bitta joy uchun mavjud buyurtma bilan bir vaqtda ko'rsatilolmas
# edi), shuning uchun GPS/vaqt hisobi to'liq frontendda yuritiladi va faqat
# "Yakunlash" bosilganda tayyor (completed) Buyurtma sifatida yoziladi.

def _walkin_client():
    """Taksometr orqali yo'l-yo'lakay olingan mijozlar uchun umumiy tizim
    yozuvi — bular ro'yxatdan o'tgan haqiqiy mijoz emas, shuning uchun har
    safar yangi Client yaratish o'rniga bitta doimiy yozuv ishlatiladi."""
    from .models import Client
    client, _ = Client.objects.get_or_create(
        phone_number='000',
        defaults={'full_name': "Qo'shimcha yo'lovchi (taksometr)"},
    )
    return client


@driver_login_required
@require_POST
def driver_taximeter_finish(request, driver):
    from django.utils import timezone

    try:
        dist_km = round(float(request.POST.get('dist_km', 0)), 2)
    except (TypeError, ValueError):
        dist_km = 0.0
    try:
        wait_ms = max(0, int(float(request.POST.get('wait_ms', 0))))
    except (TypeError, ValueError):
        wait_ms = 0
    try:
        duration_sec = max(0, int(float(request.POST.get('duration_sec', 0))))
    except (TypeError, ValueError):
        duration_sec = 0

    if dist_km <= 0 and duration_sec < 30:
        return JsonResponse({'ok': False, 'error': "Taksometr hali boshlanmagan yoki juda qisqa."}, status=400)

    tariff = TariffSettings.get()
    price = tariff.calc_price(dist_km, wait_ms / 60000)
    started_at = timezone.now() - timezone.timedelta(seconds=duration_sec)

    order = Order.objects.create(
        client=_walkin_client(), driver=driver,
        from_address="Yo'l-yo'lakay olingan mijoz (taksometr)",
        status='completed',
        payment_type='cash', car_type=driver.car_type,
        distance_km=dist_km, tmx_dist_km=dist_km,
        tmx_start_time=started_at, tmx_paused_ms=wait_ms,
        price=price, commission=tariff.commission,
    )

    driver.balance -= tariff.commission
    driver.trips_count = (driver.trips_count or 0) + 1
    driver.save(update_fields=['balance', 'trips_count'])

    _log_activity(
        driver, DriverActivityLog.ACTION_BALANCE,
        f"Taksometr (qo'shimcha mijoz): -{tariff.commission} UZS komissiya, buyurtma #{order.id}",
        request,
    )
    tg_order_completed(order, driver)
    tg_low_balance_alert(driver)

    return JsonResponse({
        'ok': True, 'price': float(price),
        'new_balance': float(driver.balance), 'order_id': order.id,
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
        'pending_orders_count': _pending_orders_count(driver),
        'active_orders_count': _active_orders_count(driver),
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
    last_id = int(request.GET.get('last_id', 0))
    msgs = ChatMessage.objects.filter(driver=driver, id__gt=last_id).order_by('created_at')
    msgs.filter(sender=ChatMessage.SENDER_OPERATOR).update(is_read=True)
    # Operator o'qib chiqqan (haydovchi yuborgan) xabarlar — check-double
    # belgisini jonli yangilash uchun (haydovchi hali sahifani qayta
    # yuklamagan bo'lsa ham, operator xabarni o'qiganini darhol ko'rsatish).
    read_ids = list(
        ChatMessage.objects
        .filter(driver=driver, sender=ChatMessage.SENDER_DRIVER, is_read=True, id__lte=last_id)
        .order_by('-id').values_list('id', flat=True)[:50]
    )
    # Operator hozir yozayotgan bo'lsa ("Yozmoqda..." indikatori uchun) — so'nggi
    # 4 soniya ichida belgi qo'yilgan bo'lsa hali ham "yozmoqda" deb hisoblanadi.
    typing = bool(
        driver.operator_typing_at and
        (timezone.now() - driver.operator_typing_at).total_seconds() < 4
    )
    return JsonResponse({
        'messages': [
            {
                'id': m.id, 'sender': m.sender, 'text': m.text,
                'audio_url': request.build_absolute_uri(m.audio.url) if m.audio else None,
                'created_at': m.created_at.isoformat()
            }
            for m in msgs
        ],
        'read_ids': read_ids,
        'operator_typing': typing,
    })


@driver_login_required
def driver_balance_poll(request, driver):
    """Haydovchi ilovasida balans to'ldirilganda ovoz chiqarish uchun polling endpoint."""
    last_id = int(request.GET.get('last_id', 0))
    logs = BalanceLog.objects.filter(driver=driver, id__gt=last_id).order_by('id')
    snd = PanelSound.objects.filter(event_key='driver_balance_changed').first()
    data = [
        {
            'id': l.id,
            'action': l.action,
            'amount': str(l.amount),
            'balance_after': str(l.balance_after),
            'enabled': snd.enabled if snd else True,
            'sound_url': snd.resolve_url() if snd else None,
        }
        for l in logs
    ]
    last = logs.last()
    return JsonResponse({'logs': data, 'last_id': last.id if last else last_id})


@driver_login_required
@require_POST
def driver_chat_send_audio(request, driver):
    from .utils import send_telegram
    audio = request.FILES.get('audio')
    if not audio:
        return JsonResponse({'ok': False}, status=400)
    msg = ChatMessage.objects.create(driver=driver, sender=ChatMessage.SENDER_DRIVER, audio=audio)
    send_telegram(f"🎤 <b>{driver.full_name}</b> ({driver.car_number}) ovozli xabar yubordi")
    return JsonResponse({
        'ok': True, 'id': msg.id,
        'audio_url': request.build_absolute_uri(msg.audio.url),
        'created_at': msg.created_at.isoformat()
    })


# ── Profile ───────────────────────────────────────────────────────────────────

@driver_login_required
def driver_profile(request, driver):
    from django.utils import timezone
    from datetime import timedelta

    contract = ContractSettings.get()
    signed = driver.contract_signatures.filter(version=contract.version).exists()

    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    referral_count = driver.owned_vouchers.filter(is_used=True).count()
    referral_count_week = driver.owned_vouchers.filter(is_used=True, used_at__date__gte=week_start).count()

    return render(request, 'driver/profile.html', {
        'driver':      driver,
        'active_tab':  'profile',
        'chat_unread': _chat_unread(driver),
        'pending_orders_count': _pending_orders_count(driver),
        'active_orders_count': _active_orders_count(driver),
        'contract_needs_signature': not signed,
        'referral_count': referral_count,
        'referral_count_week': referral_count_week,
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
def driver_balance_topup(request, driver):
    """Haydovchi to'lov chekini yuklab balans to'ldirishni so'raydi —
    admin operator botdan chekni ko'rib tasdiqlaydi yoki rad etadi."""
    receipt = request.FILES.get('receipt')
    amount  = request.POST.get('amount', '').strip()
    if not receipt:
        return JsonResponse({'ok': False, 'error': 'Chek rasmi tanlanmadi'}, status=400)
    try:
        amount = Decimal(amount)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': "Summani to'g'ri kiriting"}, status=400)

    topup = BalanceTopupRequest.objects.create(driver=driver, amount=amount, receipt=receipt)
    tg_topup_request(topup, request.build_absolute_uri(topup.receipt.url))
    return JsonResponse({'ok': True})


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


# ── Shartnoma ─────────────────────────────────────────────────────────────────

@driver_login_required
def driver_contract(request, driver):
    contract = ContractSettings.get()
    signature = driver.contract_signatures.filter(version=contract.version).first()
    return render(request, 'driver/contract.html', {
        'driver':      driver,
        'active_tab':  'profile',
        'contract':    contract,
        'signature':   signature,
        'chat_unread': _chat_unread(driver),
        'pending_orders_count': _pending_orders_count(driver),
        'active_orders_count': _active_orders_count(driver),
    })


@driver_login_required
@require_POST
def driver_contract_sign(request, driver):
    contract = ContractSettings.get()
    if driver.contract_signatures.filter(version=contract.version).exists():
        return JsonResponse({'ok': False, 'error': 'Siz bu versiyani allaqachon imzolagansiz'}, status=400)

    signature_file = request.FILES.get('signature')
    if not signature_file:
        return JsonResponse({'ok': False, 'error': 'Imzo chizilmagan'}, status=400)
    if request.POST.get('agree') != '1':
        return JsonResponse({'ok': False, 'error': "Shartlarga rozilik belgilanmagan"}, status=400)

    DriverContractSignature.objects.create(
        driver=driver,
        version=contract.version,
        full_name=driver.full_name,
        signature=signature_file,
        ip_address=_get_ip(request),
    )
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
        from django.utils import timezone
        data = json.loads(request.body)
        lat = float(data.get('lat', 0))
        lng = float(data.get('lng', 0))
        driver.latitude  = lat
        driver.longitude = lng
        driver.last_seen = timezone.now()
        driver.save(update_fields=['latitude', 'longitude', 'last_seen'])
    except Exception:
        pass
    return JsonResponse({'ok': True})


@driver_login_required
def driver_nearby_locations(request, driver):
    """Asosiy sahifadagi xarita uchun — hozir ish navbatidagi BOSHQA
    haydovchilarning joylashuvi. Diqqat: bu haydovchilar bir-biriga ko'rinadi,
    shuning uchun faqat xaritada belgi chizish uchun zarur maydonlar
    qaytariladi — telefon raqami va balans kabi shaxsiy/moliyaviy
    ma'lumotlar (panel uchun mo'ljallangan active_drivers_locations'dan
    farqli o'laroq) bu yerda umuman berilmaydi."""
    from django.utils import timezone
    online_cutoff = timezone.now() - timezone.timedelta(seconds=120)
    peers = Driver.objects.filter(
        is_on_duty=True, is_active=True, approval_status=Driver.APPROVAL_APPROVED,
        latitude__isnull=False, longitude__isnull=False,
        last_seen__gte=online_cutoff,
    ).exclude(pk=driver.pk)
    data = [{
        'id':        d.id,
        'full_name': d.full_name,
        'car_type':  d.car_type,
        'photo_url': d.photo.url if d.photo else '',
        'latitude':  d.latitude,
        'longitude': d.longitude,
    } for d in peers]
    return JsonResponse({'drivers': data})


@driver_login_required
@require_POST
def driver_duty_toggle(request, driver):
    # Diqqat: is_on_duty faqat YANGI buyurtma dispatch qilish uchun filtr
    # sifatida ishlatiladi (utils.dispatch_order va h.k.) — joriy (accepted/
    # on_way/arrived) buyurtmani boshqarish Tarix orqali navbat holatidan
    # mustaqil davom etadi. Shu sababli bu yerda faol buyurtma borligi uchun
    # navbatdan chiqishni taqiqlamaymiz (avval taqiqlangan edi — bu haydovchi
    # uchun "tugma bosilsa ham hech narsa bo'lmaydi" holatini keltirib
    # chiqargan, mobil ilova API'sida ham bunday cheklov yo'q).
    # Balans kam bo'lsa ham navbatga chiqishga ruxsat beriladi — u baribir
    # buyurtmalarni ko'radi, faqat balans yetmasa qabul qila olmaydi
    # (order_status'dagi alohida tekshiruv shu ishni qiladi).
    driver.is_on_duty = not driver.is_on_duty
    driver.save(update_fields=['is_on_duty'])
    action = DriverActivityLog.ACTION_DUTY_ON if driver.is_on_duty else DriverActivityLog.ACTION_DUTY_OFF
    _log_activity(driver, action, 'Saytdan', request)
    tg_duty_changed(driver, driver.is_on_duty)
    return JsonResponse({'ok': True, 'is_on_duty': driver.is_on_duty})


# ── Taxi Meter ───────────────────────────────────────────────────────────────

@driver_login_required
def driver_meter_update(request, driver, pk):
    """Taximetr ma'lumotlarini DBga saqlaydi va qaytaradi."""
    order = get_object_or_404(Order, pk=pk, driver=driver)
    if order.status in ('completed', 'cancelled'):
        # Buyurtma allaqachon yakunlangan/bekor qilingan — tarmoq kechikishi
        # tufayli keyin yetib kelgan eski autosave so'rovi yakuniy narx va
        # masofani eski qiymat bilan ustidan yozib yubormasin.
        return JsonResponse({
            'ok': True,
            'dist_km': order.tmx_dist_km,
            'price':   float(order.price) if order.price else 0,
        })
    try:
        dist_km = float(request.POST.get('dist_km') or request.GET.get('dist_km') or 0)
        price   = float(request.POST.get('price')   or request.GET.get('price')   or 0)
        waiting = (request.POST.get('waiting') or request.GET.get('waiting') or '0') == '1'
        wait_ms = int(request.POST.get('wait_ms') or request.GET.get('wait_ms') or 0)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False}, status=400)

    update_fields = ['tmx_dist_km', 'tmx_paused', 'tmx_paused_ms', 'updated_at']
    order.tmx_dist_km = round(dist_km, 2)
    order.tmx_paused = waiting
    order.tmx_paused_ms = max(0, wait_ms)
    if dist_km > 0:
        order.distance_km = round(dist_km, 2)
        update_fields.append('distance_km')
    if price > 0:
        from decimal import Decimal
        order.price = Decimal(str(round(price)))
        update_fields.append('price')
    order.save(update_fields=update_fields)

    return JsonResponse({
        'ok': True,
        'dist_km': order.tmx_dist_km,
        'price':   float(order.price) if order.price else price,
    })


# ── ETA: haydovchi qancha vaqtda yetib keladi ─────────────────────────────────
@driver_login_required
def driver_order_eta(request, driver, pk):
    """Haydovchining buyurtma manziliga ETA ni hisoblaydi (daqiqa)."""
    order = get_object_or_404(Order, pk=pk)
    if order.driver_id and order.driver_id != driver.id:
        return JsonResponse({'ok': False, 'error': 'Bu buyurtma sizga tegishli emas'}, status=403)
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


# ── Destination Mode ────────────────────────────────────────────────────────

@driver_login_required
@require_POST
def driver_destination(request, driver):
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False}, status=400)
    if data.get('clear'):
        driver.destination_mode = False
        driver.destination_lat = None
        driver.destination_lng = None
        driver.destination_address = ''
        driver.save(update_fields=['destination_mode', 'destination_lat', 'destination_lng', 'destination_address'])
        return JsonResponse({'ok': True, 'active': False})
    lat = data.get('lat')
    lng = data.get('lng')
    address = data.get('address', '').strip()
    if not lat or not lng:
        return JsonResponse({'ok': False, 'error': 'Koordinata kerak'}, status=400)
    driver.destination_mode = True
    driver.destination_lat = float(lat)
    driver.destination_lng = float(lng)
    driver.destination_address = address
    driver.save(update_fields=['destination_mode', 'destination_lat', 'destination_lng', 'destination_address'])
    return JsonResponse({'ok': True, 'active': True})
@driver_login_required
def driver_surge_info(request, driver):
    """Hozirgi surge (narx oshishi) ma'lumotini qaytaradi."""
    from .utils import get_surge_multiplier
    multiplier, reason = get_surge_multiplier()
    return JsonResponse({'ok': True, 'multiplier': multiplier, 'reason': reason})


# ── Group Chat ────────────────────────────────────────────────────────────────

@driver_login_required
def driver_group_chat_list(request, driver):
    last_id = int(request.GET.get('last_id', 0))
    msgs = GroupMessage.objects.select_related('driver').filter(id__gt=last_id).order_by('created_at')[:100]
    return JsonResponse({'messages': [
        {
            'id': m.id,
            'driver_id': m.driver_id,
            'driver_name': m.display_name,
            'car_number': m.display_sub,
            'text': m.text,
            'audio_url': request.build_absolute_uri(m.audio.url) if m.audio else None,
            'created_at': m.created_at.isoformat(),
        }
        for m in msgs
    ]})


@driver_login_required
@require_POST
def driver_group_chat_send(request, driver):
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
    except Exception:
        text = request.POST.get('text', '').strip()
    if not text:
        return JsonResponse({'ok': False}, status=400)
    msg = GroupMessage.objects.create(driver=driver, text=text)
    return JsonResponse({
        'ok': True, 'id': msg.id,
        'driver_id': driver.id, 'driver_name': driver.full_name,
        'car_number': driver.car_number,
        'text': msg.text, 'audio_url': None,
        'created_at': msg.created_at.isoformat(),
    })


@driver_login_required
@require_POST
def driver_group_chat_send_audio(request, driver):
    audio = request.FILES.get('audio')
    if not audio:
        return JsonResponse({'ok': False}, status=400)
    msg = GroupMessage.objects.create(driver=driver, audio=audio)
    return JsonResponse({
        'ok': True, 'id': msg.id,
        'driver_id': driver.id, 'driver_name': driver.full_name,
        'car_number': driver.car_number,
        'text': '', 'audio_url': request.build_absolute_uri(msg.audio.url),
        'created_at': msg.created_at.isoformat(),
    })


# ── Guruh jonli ovozli aloqa ("efir") — WebRTC P2P mesh signalizatsiya ────────
# Bitta markaziy media-server (SFU) o'rniga — bu hostingda alohida server
# ishga tushirish imkoni bo'lmagani uchun — har bir haydovchi qolgan barcha
# faol ishtirokchilar bilan to'g'ridan-to'g'ri (P2P) WebRTC ulanish o'rnatadi.
# Signalizatsiya (offer/answer/ICE candidate almashish) uchun alohida
# WebSocket server o'rniga mavjud HTTP polling infratuzilmasidan foydalaniladi
# (boshqa joylardagi chat_poll bilan bir xil uslub) — VoiceSignal jadvali
# navbat vazifasini o'taydi. Diqqat: ko'p ishtirokchi bir vaqtda "efir"da
# bo'lsa, mesh ulanishlar soni tezda ko'payadi (N ishtirokchi = har birida N-1
# ulanish) — shuning uchun bu yondashuv o'nlab emas, bir necha (~6-8) faol
# ishtirokchi uchun mo'ljallangan. Ishonchli NAT o'tish uchun TURN server yo'q
# (faqat bepul ochiq STUN) — juda cheklangan tarmoqlarda ulanish muvaffaqiyatsiz
# bo'lishi mumkin.
@driver_login_required
@require_POST
def driver_voice_join(request, driver):
    from .utils import voice_prune_stale, voice_participants_list
    voice_prune_stale()
    VoiceParticipant.objects.update_or_create(driver=driver)
    return JsonResponse({'ok': True, 'participants': voice_participants_list(f'd{driver.id}')})


@driver_login_required
@require_POST
def driver_voice_leave(request, driver):
    from .utils import voice_participants_list, voice_target_kwargs
    others = voice_participants_list(f'd{driver.id}')
    VoiceParticipant.objects.filter(driver=driver).delete()
    signals = []
    for o in others:
        kwargs = voice_target_kwargs('to', o['key'])
        if kwargs:
            signals.append(VoiceSignal(from_driver=driver, kind=VoiceSignal.KIND_LEAVE, payload='', **kwargs))
    VoiceSignal.objects.bulk_create(signals)
    return JsonResponse({'ok': True})


@driver_login_required
def driver_voice_heartbeat(request, driver):
    from .utils import voice_prune_stale, voice_participants_list, voice_signal_sender_info
    try:
        # last_seen `auto_now=True` bo'lgani uchun .save() chaqirilishi kerak —
        # queryset .update() bilan avtomatik yangilanmaydi (faqat model instance save()da ishlaydi)
        VoiceParticipant.objects.get(driver=driver).save(update_fields=['last_seen'])
    except VoiceParticipant.DoesNotExist:
        return JsonResponse({'ok': True, 'joined': False})
    voice_prune_stale()

    signals = list(VoiceSignal.objects.filter(to_driver=driver).select_related('from_driver', 'from_operator').order_by('created_at')[:50])
    signal_ids = [s.id for s in signals]
    if signal_ids:
        VoiceSignal.objects.filter(id__in=signal_ids).delete()

    return JsonResponse({
        'ok': True,
        'joined': True,
        'participants': voice_participants_list(f'd{driver.id}'),
        'signals': [
            dict(zip(('from', 'from_name'), voice_signal_sender_info(s)),
                 kind=s.kind, payload=json.loads(s.payload) if s.payload else None)
            for s in signals
        ],
    })


@driver_login_required
@require_POST
def driver_voice_signal(request, driver):
    from .utils import voice_target_kwargs
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'ok': False}, status=400)

    kind = data.get('kind')
    payload = data.get('payload')
    target_kwargs = voice_target_kwargs('to', data.get('to'))
    if not target_kwargs or kind not in dict(VoiceSignal.KIND_CHOICES):
        return JsonResponse({'ok': False, 'error': "Noto'g'ri so'rov"}, status=400)

    VoiceSignal.objects.create(
        from_driver=driver, kind=kind,
        payload=json.dumps(payload) if payload is not None else '',
        **target_kwargs,
    )
    return JsonResponse({'ok': True})
