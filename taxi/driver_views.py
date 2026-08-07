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
from django.utils.cache import add_never_cache_headers
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Driver, Order, ChatMessage, GroupMessage, TariffSettings, DriverActivityLog, BalanceLog, BalanceTopupRequest, PanelSound, VoiceParticipant, VoiceSignal, ContractSettings, DriverContractSignature, SavedAddress
from .utils import tg_order_accepted, tg_order_on_way, tg_order_arrived, tg_order_completed, tg_order_cancelled, tg_order_rejected, tg_driver_login, tg_duty_changed, tg_low_balance_alert, tg_topup_request, sms_order_status


# Haydovchi buyurtmani o'zi bekor qilganda tanlaydigan sabablar — har biriga
# mos matn va "boshqa haydovchilarga qayta ochiladimi" bayrog'i (True/False).
# Kalitlar taxi/templates/driver/base.html'dagi cancel-reason modali bilan
# BIR XIL bo'lishi shart (frontend shu kalitlarni yuboradi). "other" kaliti
# alohida ishlaydi — bepul matn (`custom_reason`) sifatida, doim reassign=False.
DRIVER_CANCEL_REASONS = {
    'car_broke':        ("Mashinam buzilib qoldi", True),
    'busy':             ("Band bo'lib qoldim / boshqa buyurtma oldim", True),
    'incident':         ("Yo'lda hodisa/muammo yuz berdi", True),
    'client_no_answer': ("Mijoz javob bermayapti", False),
    'client_cancelled': ("Mijoz bekor qildi", False),
    'client_not_found': ("Mijoz manzilda topilmadi", False),
}


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
        if driver.is_frozen:
            response = render(request, 'driver/frozen.html', {'driver': driver, 'tariff': TariffSettings.get()})
        elif driver.approval_status != Driver.APPROVAL_APPROVED:
            response = render(request, 'driver/pending.html', {'driver': driver})
        else:
            response = fn(request, driver, *args, **kwargs)
        # Bo'limlar orasida (Asosiy/Tarix/Chat/Profil) oddiy <a href> orqali
        # o'tilgani uchun (SPA emas), brauzer/WebView ba'zan sahifani HTTP
        # keshidan qaytarib berishi mumkin edi — bu holda Asosiy sahifadagi
        # ORDERS o'sha eski (masalan hali on_way bo'lmagan) holatda "muzlab"
        # qolib, taksometr qayta ishga tushmasdi (narx ko'rinardi, lekin
        # yangilanmasdi). Har bir haydovchi sahifasi doim jonli bo'lishi
        # shart bo'lgani uchun keshlashni butunlay o'chiramiz.
        add_never_cache_headers(response)
        return response
    return wrapper


def _chat_unread(driver):
    # Diqqat: operator bilan shaxsiy chat endi haydovchi ilovasi "Chat"
    # bo'limidan olib tashlangan (faqat guruh chat qoladi) — shu sababli
    # bu yerda ham faqat guruh xabarlari hisoblanadi. Operator ChatMessage
    # yozuvlari endi hech qachon ilovada "o'qilgan" deb belgilanmaydi,
    # shuning uchun ularni bu hisobga qo'shish belgi (badge) sonini
    # abadiy noto'g'ri/qotib qolgan holga keltirar edi.
    return GroupMessage.objects.exclude(driver=driver).filter(created_at__gt=driver.last_group_read_at).count()


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


def _driver_month_rank(driver):
    """Joriy oy boshidan bugungacha yakunlangan buyurtmalar soni bo'yicha
    haydovchining reytingdagi o'rnini hisoblaydi (1 = eng ko'p ishlagan).
    Asosiy sahifadagi suzib turuvchi reyting tugmasi uchun — to'liq ro'yxatni
    emas, faqat o'z o'rnini bilish kifoya, shu sabab bitta hisoblovchi
    so'rov (COUNT) bilan chegaralanadi (butun ro'yxatni yuklamaymiz)."""
    from django.db.models import Count, Q as DQ
    from django.utils import timezone
    today = timezone.localdate()
    month_start = today.replace(day=1)
    own_completed = Order.objects.filter(
        driver=driver, status='completed',
        created_at__date__gte=month_start, created_at__date__lte=today,
    ).count()
    ahead = Driver.objects.filter(is_active=True).annotate(
        completed=Count('orders', filter=DQ(
            orders__status='completed',
            orders__created_at__date__gte=month_start,
            orders__created_at__date__lte=today,
        )),
    ).filter(completed__gt=own_completed).count()
    total = Driver.objects.filter(is_active=True).count()
    return ahead + 1, total, own_completed


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
    driver_rank, drivers_total, _ = _driver_month_rank(driver)
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
        'max_active_orders': Order.MAX_ACTIVE_PER_DRIVER,
        'driver_balance_int': int(driver.balance),
        'today_earned': int(today_stats['earned'] or 0),
        'today_trips': today_stats['trips'] or 0,
        'driver_rank': driver_rank,
        'drivers_total': drivers_total,
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
    low_balance = driver.balance < TariffSettings.get().commission

    return JsonResponse({
        'new_ids': ids, 'orders': orders_data,
        'low_balance': low_balance,
    })


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
                from .utils import dispatch_order, _resolve_dispatch_attempt, _requeue_driver_to_back
                from .models import DispatchAttempt
                _resolve_dispatch_attempt(order, driver.id, DispatchAttempt.RESULT_REJECTED)
                _requeue_driver_to_back(driver.id, order)
                tg_order_rejected(order, driver)
                dispatch_order(order)
        return JsonResponse({'ok': True})

    # Haydovchi qabul qilingan buyurtmani sababini ko'rsatib o'zi bekor qila
    # oladi (taxi/templates/driver/base.html'dagi cancel-reason modali orqali).
    # Haydovchidan kelib chiqqan sabablarda (mashina, band bo'lish, yo'ldagi
    # hodisa) mijoz mashinasiz qolmasligi uchun buyurtma darhol boshqa
    # haydovchilarga qayta ochiladi (DRIVER_CANCEL_REASONS'dagi reassign=True);
    # mijozga bog'liq sabablarda (javob bermayapti/bekor qildi/topilmadi) esa
    # to'liq yopiladi. Komissiya har ikkala holatda ham qaytariladi.
    if action == 'cancel':
        if order.status not in Order.ACTIVE_STATUSES:
            return JsonResponse({'ok': False, 'error': f"'{order.get_status_display()}' holatida bu amal mumkin emas"}, status=400)
        if order.driver_id != driver.id:
            return JsonResponse({'ok': False, 'error': 'Bu buyurtma sizga tegishli emas'}, status=403)

        reason_key = request.POST.get('reason', '').strip()
        custom_reason = request.POST.get('custom_reason', '').strip()
        if reason_key == 'other':
            if not custom_reason:
                return JsonResponse({'ok': False, 'error': "Sababni yozing"}, status=400)
            final_reason, should_reassign = custom_reason, False
        elif reason_key in DRIVER_CANCEL_REASONS:
            final_reason, should_reassign = DRIVER_CANCEL_REASONS[reason_key]
        else:
            return JsonResponse({'ok': False, 'error': "Bekor qilish sababini tanlang"}, status=400)

        from .views import _refund_order_commission
        _refund_order_commission(order, driver, f"haydovchi tomonidan bekor qilindi ({final_reason})")

        order.cancel_reason = final_reason
        if should_reassign:
            order.rejected_by.add(driver)
            order.driver = None
            order.dispatched_to = None
            order.dispatched_at = None
            order.status = 'pending'
            order.save(update_fields=['driver', 'dispatched_to', 'dispatched_at', 'status', 'cancel_reason', 'updated_at'])
        else:
            order.driver = None
            order.status = 'cancelled'
            order.save(update_fields=['driver', 'status', 'cancel_reason', 'updated_at'])
            sms_order_status(order, 'cancelled')

        _log_activity(driver, DriverActivityLog.ACTION_ORDER, f"Buyurtma #{order.id} bekor qilindi — {final_reason}", request)
        tg_order_cancelled(order, driver, reassigned=should_reassign)

        if should_reassign:
            tariff = TariffSettings.get()
            if order.from_lat and order.from_lng and tariff.auto_dispatch:
                from .utils import dispatch_order
                dispatch_order(order)

        return JsonResponse({'ok': True, 'new_balance': float(driver.balance), 'reassigned': should_reassign})

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
            from .utils import _resolve_dispatch_attempt
            from .models import DispatchAttempt, AddressQueueEntry
            from django.utils import timezone as _tz
            _resolve_dispatch_attempt(locked, driver.id, DispatchAttempt.RESULT_ACCEPTED)
            # Buyurtma qabul qilingandan keyin haydovchi endi band —
            # manzil navbatida (agar turgan bo'lsa) o'rnini bo'shatadi.
            AddressQueueEntry.objects.filter(driver=driver, left_at__isnull=True).update(left_at=_tz.now())
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
        # Tarmoq beqaror bo'lganda bu so'rov davriy /meter/ autosave'dan oldin
        # yetib kelishi mumkin — shu sabab qiymatlar hech qachon orqaga
        # qaytarilmasin (faqat bazadagidan katta/teng bo'lsa yoziladi)
        if tmx_dist and float(tmx_dist) > 0 and float(tmx_dist) >= float(order.tmx_dist_km or 0):
            order.distance_km = round(float(tmx_dist), 2)
            order.tmx_dist_km = round(float(tmx_dist), 2)
            update_fields.append('distance_km')
            update_fields.append('tmx_dist_km')
        if tmx_price and float(tmx_price) > 0 and float(tmx_price) >= float(order.price or 0):
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


# ── Buyurtma yaratish (haydovchi ilova orqali o'zi ro'yxatga oladi) ───────────
# Ko'chada to'g'ridan-to'g'ri (dispetcherlik orqali emas) topilgan mijoz uchun.
# `mustaqil taksometr`dan farqi — bu yerda buyurtma darhol 'completed' emas,
# oddiy pending/accepted -> ... -> completed jarayonidan o'tadi (haydovchi
# o'zi ushlab qolishi yoki boshqa haydovchilarga ochib qo'yishi mumkin).
# Diqqat: avval bu yerda yakunlanganda ro'yxatga olgan haydovchiga qo'shimcha
# bonus to'lanardi — so'rov bo'yicha olib tashlandi, endi oddiy komissiya
# qoidasi bilan bir xil ishlaydi.

@driver_login_required
def driver_order_create(request, driver):
    if request.method != 'POST':
        from .models import SavedAddress
        return render(request, 'driver/order_create.html', {
            'driver': driver,
            'active_tab': 'home',
            'chat_unread': _chat_unread(driver),
            'pending_orders_count': _pending_orders_count(driver),
            'active_orders_count': _active_orders_count(driver),
            'saved_addresses': SavedAddress.objects.all(),
        })

    from .models import Client, SavedAddress
    from .utils import tg_new_order, dispatch_order

    phone_number  = request.POST.get('phone_number', '').strip()
    customer_name = request.POST.get('customer_name', '').strip()
    to_address    = request.POST.get('to_address', '').strip()
    assign_to     = request.POST.get('assign_to', 'self')  # 'self' | 'others'
    saved_address_id = request.POST.get('saved_address_id')

    # "Qayerdan" — operator panel > Manzillar'dan tanlangan bo'lsa o'sha
    # manzilning aniq koordinatasi ishlatiladi (dispatch_order() shu orqali
    # navbat — kim birinchi kelgan — tartibida yubora oladi). "Boshqa"
    # tanlansa (qo'lda yozilgan, ro'yxatda yo'q joy) — haydovchining hozirgi
    # GPS joylashuvi ishlatiladi va pastda umumiy tabloga tashlab yuboriladi
    # (individual dispatch qilinmaydi).
    saved_address = SavedAddress.objects.filter(pk=saved_address_id).first() if saved_address_id else None
    if saved_address:
        from_address = saved_address.address or saved_address.name
        from_lat, from_lng = saved_address.lat, saved_address.lng
    else:
        from_address = request.POST.get('from_address', '').strip()
        from_lat, from_lng = driver.latitude, driver.longitude

    if not phone_number or not from_address:
        return JsonResponse({'ok': False, 'error': "Mijoz raqami va manzil kiritilishi shart"}, status=400)

    tariff = TariffSettings.get()
    client, _created = Client.objects.get_or_create(phone_number=phone_number)
    if client.is_blocked:
        return JsonResponse({'ok': False, 'error': "Bu mijoz bloklangan"}, status=400)
    if customer_name and not client.full_name:
        client.full_name = customer_name
        client.save(update_fields=['full_name'])

    if assign_to == 'self':
        active_count = Order.objects.filter(driver=driver, status__in=Order.ACTIVE_STATUSES).count()
        if active_count >= Order.MAX_ACTIVE_PER_DRIVER:
            return JsonResponse({
                'ok': False,
                'error': f"Bir vaqtda ko'pi bilan {Order.MAX_ACTIVE_PER_DRIVER} ta faol buyurtma olish mumkin. Avval joriy buyurtma(lar)ni yakunlang.",
            }, status=400)
        commission = tariff.commission
        if driver.balance < commission:
            return JsonResponse({'ok': False, 'error': f'Balans yetarli emas. Komissiya: {commission} UZS'}, status=400)

        order = Order.objects.create(
            client=client, driver=driver,
            from_address=from_address, from_lat=from_lat, from_lng=from_lng,
            to_address=to_address,
            payment_type=Order.PAYMENT_CASH, car_type=driver.car_type,
            commission=commission,
            status='accepted',
            created_by_driver=driver,
        )
        driver.balance -= Decimal(str(commission))
        driver.save(update_fields=['balance'])
        _log_activity(driver, DriverActivityLog.ACTION_ORDER,
                       f"Ilova orqali buyurtma #{order.id} yaratdi va o'zi qabul qildi, -{commission} UZS komissiya", request)
        tg_order_accepted(order, driver)
        tg_low_balance_alert(driver)
        return JsonResponse({'ok': True, 'order_id': order.id, 'new_balance': float(driver.balance)})

    order = Order.objects.create(
        client=client,
        from_address=from_address, from_lat=from_lat, from_lng=from_lng,
        to_address=to_address,
        payment_type=Order.PAYMENT_CASH, car_type=driver.car_type,
        commission=tariff.commission,
        status='pending',
        created_by_driver=driver,
    )
    _log_activity(driver, DriverActivityLog.ACTION_ORDER,
                   f"Ilova orqali buyurtma #{order.id} yaratdi — boshqa haydovchilarga ochiq", request)
    tg_new_order(order)
    # Faqat ro'yxatdagi manzil tanlangan bo'lsa individual taqsimlanadi
    # (dispatch_order() manzil navbatini avtomatik aniqlaydi). "Boshqa"
    # tanlansa — umumiy tabloda qoladi (dispatched_to=None, standart holat).
    if saved_address and from_lat and from_lng:
        dispatch_order(order)
    return JsonResponse({'ok': True, 'order_id': order.id})


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


UZ_MONTHS = [
    '', 'Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun',
    'Iyul', 'Avgust', 'Sentyabr', 'Oktyabr', 'Noyabr', 'Dekabr',
]


# ── Reyting ──────────────────────────────────────────────────────────────────

@driver_login_required
def driver_rating(request, driver):
    """Joriy oy uchun yakunlangan buyurtmalar soni bo'yicha barcha faol
    haydovchilarning reytingi — haydovchini rag'batlantirish uchun (o'z
    o'rnini va oldinga chiqish uchun necha buyurtma kerakligini ko'radi)."""
    from django.db.models import Count, Sum, Q as DQ
    from django.utils import timezone

    today = timezone.localdate()
    month_start = today.replace(day=1)

    leaderboard = list(
        Driver.objects.filter(is_active=True)
        .annotate(
            completed=Count('orders', filter=DQ(
                orders__status='completed',
                orders__created_at__date__gte=month_start,
                orders__created_at__date__lte=today,
            )),
            earned=Sum('orders__price', filter=DQ(
                orders__status='completed',
                orders__created_at__date__gte=month_start,
                orders__created_at__date__lte=today,
            )),
        )
        .order_by('-completed', '-earned', 'full_name')
    )

    rows = []
    my_row = None
    for i, d in enumerate(leaderboard, start=1):
        row = {
            'rank': i,
            'full_name': d.full_name,
            'completed': d.completed,
            'earned': int(d.earned or 0),
            'is_me': d.id == driver.id,
        }
        rows.append(row)
        if row['is_me']:
            my_row = row

    gap_to_next = None
    if my_row and my_row['rank'] > 1:
        ahead_row = rows[my_row['rank'] - 2]
        gap_to_next = max(1, ahead_row['completed'] - my_row['completed'] + 1)

    return render(request, 'driver/rating.html', {
        'driver': driver,
        'active_tab': 'rating',
        'chat_unread': _chat_unread(driver),
        'pending_orders_count': _pending_orders_count(driver),
        'active_orders_count': _active_orders_count(driver),
        'rows': rows,
        'my_row': my_row,
        'gap_to_next': gap_to_next,
        'month_label': UZ_MONTHS[today.month],
    })



# ── Chat ──────────────────────────────────────────────────────────────────────

@driver_login_required
def driver_chat(request, driver):
    # Diqqat: operator bilan shaxsiy chat "Chat" bo'limidan olib tashlangan
    # — endi bu sahifa faqat guruh chatini ko'rsatadi. Guruh xabarlari
    # "o'qilgan" deb belgilanishi (`last_group_read_at`) client tomonda
    # `driver_group_chat_list` chaqirilganda avtomatik sodir bo'ladi.
    driver_count = Driver.objects.filter(approval_status=Driver.APPROVAL_APPROVED, is_active=True).count()
    return render(request, 'driver/chat.html', {
        'driver':       driver,
        'active_tab':   'chat',
        'chat_unread':  0,
        'driver_count': driver_count,
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
def driver_ping(request, driver):
    """Asosiy sahifadagi tarmoq tezligi (ping) ko'rsatkichi shu yerga
    davriy so'rov yuborib, round-trip vaqtini o'lchaydi. Javobning o'zi
    hech qanday DB yozuvisiz — faqat oldingi o'lchovning natijasi (`ms`
    query parametri, bir intervaldan keyin) operator panelidagi "Ping"
    bo'limi uchun Driver'ga saqlanadi (aloqasi yomon haydovchilarni
    topib, ularga yordam berish uchun)."""
    ms = request.GET.get('ms')
    if ms:
        try:
            ms_int = int(ms)
        except (TypeError, ValueError):
            ms_int = None
        if ms_int is not None and 0 < ms_int < 60000:
            from django.utils import timezone
            Driver.objects.filter(pk=driver.pk).update(last_ping_ms=ms_int, last_ping_at=timezone.now())
    return JsonResponse({'ok': True})


@driver_login_required
def driver_address_queue(request, driver):
    """Haydovchi biror saqlangan manzilga (SavedAddress) yaqinlashganda —
    o'sha manzil navbatida (AddressQueueEntry, "kim birinchi kelgan"
    tartibida) nechinchi o'rinda turganini qaytaradi.

    Diqqat: `lat`/`lng` berilgan bo'lsa, navbat a'zoligi shu yerning o'zida
    ham yangilanadi (update_address_queue_membership) — faqat
    driver_location_sync'ga (50m harakat cheklovi bilan) tayanib qolmaslik
    uchun. Aks holda: haydovchi manzilga kelib to'xtab tursa-yu, oldingi
    GPS nuqtasi allaqachon shu 50m ichida bo'lsa (masalan sahifa qayta
    ochilganda), location_sync umuman yubormay, navbatga hech qachon
    "yozilmay" qolib ketardi — masofa (client tomonida hisoblangan)
    to'g'ri ko'rinsa ham, o'rin har doim bo'sh chiqardi."""
    from .models import AddressQueueEntry
    from .utils import update_address_queue_membership
    addr_id = request.GET.get('addr_id')
    try:
        addr_id = int(addr_id)
    except (TypeError, ValueError):
        return JsonResponse({'ok': False}, status=400)

    lat = request.GET.get('lat')
    lng = request.GET.get('lng')
    if lat and lng:
        try:
            update_address_queue_membership(driver, float(lat), float(lng))
        except (TypeError, ValueError):
            pass

    # ADDRESS_QUEUE_STALE_MINUTES ichida faol bo'lmagan (uzoq vaqt
    # oflayn/ilovani yopib qo'ygan) haydovchilar — garchi masofa jihatidan
    # hali navbat radiusida bo'lsa ham — "hozir turgan" deb hisoblanmaydi.
    from django.utils import timezone
    from .utils import ADDRESS_QUEUE_STALE_MINUTES
    stale_cutoff = timezone.now() - timezone.timedelta(minutes=ADDRESS_QUEUE_STALE_MINUTES)
    queue_ids = list(
        AddressQueueEntry.objects.filter(
            address_id=addr_id, left_at__isnull=True,
            driver__is_active=True, driver__is_on_duty=True,
            driver__approval_status='approved',
            driver__last_seen__gte=stale_cutoff,
        )
        .order_by('joined_at')
        .values_list('driver_id', flat=True)
    )
    position = queue_ids.index(driver.id) + 1 if driver.id in queue_ids else None
    return JsonResponse({'ok': True, 'position': position, 'total': len(queue_ids)})


@driver_login_required
def driver_all_addresses(request, driver):
    """Barcha saqlangan manzillar (SavedAddress) ro'yxati, har biriga bugun
    tushgan buyurtmalar soni VA hozir shu manzil navbatida turgan
    haydovchilar soni bilan — "yaqin manzil" belgisi bosilganda
    ochiladigan to'liq ro'yxat uchun. Masofa hisobi bu yerda YO'Q — u
    haydovchining joriy GPS'iga bog'liq, shuning uchun frontendda
    (JS, SAVED_ADDRESSES) hisoblanadi."""
    from .models import SavedAddress
    from .utils import find_matching_saved_address, ADDRESS_QUEUE_STALE_MINUTES
    from django.utils import timezone
    from django.db.models import Count, Q as DQ
    import datetime

    today = timezone.localdate()
    today_orders = Order.objects.filter(
        created_at__date=today, from_lat__isnull=False, from_lng__isnull=False,
    ).exclude(status='cancelled').values_list('from_lat', 'from_lng')

    counts = {}
    for lat, lng in today_orders:
        addr = find_matching_saved_address(lat, lng)
        if addr:
            counts[addr.id] = counts.get(addr.id, 0) + 1

    stale_cutoff = timezone.now() - datetime.timedelta(minutes=ADDRESS_QUEUE_STALE_MINUTES)
    addresses = SavedAddress.objects.annotate(
        queue_count=Count(
            'queue_entries',
            filter=DQ(
                queue_entries__left_at__isnull=True,
                queue_entries__driver__is_active=True,
                queue_entries__driver__is_on_duty=True,
                queue_entries__driver__approval_status='approved',
                queue_entries__driver__last_seen__gte=stale_cutoff,
            ),
        )
    )
    data = [
        {
            'id': a.id, 'name': a.name, 'lat': a.lat, 'lng': a.lng,
            'today_orders': counts.get(a.id, 0),
            'queue_count': a.queue_count,
        }
        for a in addresses
    ]
    return JsonResponse({'ok': True, 'addresses': data})


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
    contract = ContractSettings.get()
    signed = driver.contract_signatures.filter(version=contract.version).exists()

    return render(request, 'driver/profile.html', {
        'driver':      driver,
        'active_tab':  'profile',
        'chat_unread': _chat_unread(driver),
        'pending_orders_count': _pending_orders_count(driver),
        'active_orders_count': _active_orders_count(driver),
        'contract_needs_signature': not signed,
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
def driver_balance_history(request, driver):
    """Balans o'tkazmalari tarixi (kirim/chiqim) — Asosiy sahifadagi balans
    tugmasi shu yerga olib keladi.

    Diqqat: buyurtma qabul qilinganda yechiladigan komissiya `BalanceLog`ga
    umuman yozilmaydi (driver_order_action'da to'g'ridan-to'g'ri
    driver.balance'dan ayiriladi — CLAUDE.md'dagi ma'lum bo'shliq). Shu
    sabab faqat BalanceLog ko'rsatilsa, haydovchi eng ko'p uchraydigan
    xarajatini ("nega balansim kamaydi?") tarixda umuman ko'rmas edi —
    shuning uchun komissiya hali qaytarilmagan (ya'ni bekor qilinmagan)
    buyurtmalar alohida so'rovdan qo'shilib, vaqt bo'yicha birlashtiriladi."""
    logs = driver.balance_logs.all()[:100]
    entries = [{
        'is_income':  log.action == BalanceLog.ACTION_ADD,
        'amount':     log.amount,
        'note':       log.note or ("Balans to'ldirildi" if log.action == BalanceLog.ACTION_ADD else 'Balansdan yechildi'),
        'created_at': log.created_at,
    } for log in logs]

    commission_orders = Order.objects.filter(
        driver=driver, status__in=Order.ACTIVE_STATUSES + ('completed',)
    ).order_by('-updated_at')[:100]
    entries += [{
        'is_income':  False,
        'amount':     o.commission,
        'note':       f"Komissiya — buyurtma #{o.id}",
        'created_at': o.updated_at,
    } for o in commission_orders]

    entries.sort(key=lambda e: e['created_at'], reverse=True)
    entries = entries[:100]

    return render(request, 'driver/balance_history.html', {
        'driver': driver,
        'active_tab': 'balance',
        'chat_unread': _chat_unread(driver),
        'pending_orders_count': _pending_orders_count(driver),
        'active_orders_count': _active_orders_count(driver),
        'entries': entries,
        'driver_balance_int': int(driver.balance),
    })


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
        from .utils import update_address_queue_membership
        data = json.loads(request.body)
        lat = float(data.get('lat', 0))
        lng = float(data.get('lng', 0))
        driver.latitude  = lat
        driver.longitude = lng
        driver.last_seen = timezone.now()
        update_fields = ['latitude', 'longitude', 'last_seen']
        if driver.freeze_warning_sent_at:
            driver.freeze_warning_sent_at = None
            update_fields.append('freeze_warning_sent_at')
        driver.save(update_fields=update_fields)
        # Manzil (Manzillar) navbatiga a'zolikni yangilash — dispatch_order()
        # shu manzilga tushgan buyurtmalarni "kim birinchi kelgan" tartibida
        # taqsimlashi uchun.
        update_address_queue_membership(driver, lat, lng)
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
        'id':          d.id,
        'full_name':   d.full_name,
        'car_type':    d.car_type,
        'car_model':   d.car_model,
        'car_number':  d.car_number,
        'photo_url':   d.photo.url if d.photo else '',
        'latitude':    d.latitude,
        'longitude':   d.longitude,
        'trips_count': d.trips_count,
        'rating':      float(d.rating),
        'level':       d.level,
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
    if not driver.is_on_duty:
        # Navbatdan chiqsa, manzil navbatida (bor bo'lsa) o'rnini ham bo'shatadi.
        from django.utils import timezone
        from .models import AddressQueueEntry
        AddressQueueEntry.objects.filter(driver=driver, left_at__isnull=True).update(left_at=timezone.now())
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

    update_fields = ['tmx_paused', 'updated_at']
    order.tmx_paused = waiting

    # Internet uzilib-ulanib turganda avtosaqlash so'rovlari tartibsiz
    # (eskisi keyinroq) yetib kelishi mumkin — shu sabab bu kumulyativ
    # qiymatlar hech qachon orqaga qaytarilmasin (faqat oshsin), aks holda
    # taximetr vaqtincha ko'p ko'rsatib, keyin kamayib qolganday tuyular edi.
    if dist_km >= float(order.tmx_dist_km or 0):
        order.tmx_dist_km = round(dist_km, 2)
        update_fields.append('tmx_dist_km')
        if dist_km > 0:
            order.distance_km = round(dist_km, 2)
            update_fields.append('distance_km')
    if wait_ms >= (order.tmx_paused_ms or 0):
        order.tmx_paused_ms = max(0, wait_ms)
        update_fields.append('tmx_paused_ms')
    if price > 0 and price >= float(order.price or 0):
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
    from django.utils import timezone
    last_id = int(request.GET.get('last_id', 0))
    msgs = GroupMessage.objects.select_related('driver').filter(id__gt=last_id).order_by('created_at')[:100]
    driver.last_group_read_at = timezone.now()
    driver.save(update_fields=['last_group_read_at'])
    return JsonResponse({'messages': [
        {
            'id': m.id,
            'driver_id': m.driver_id,
            'driver_name': m.display_name,
            'car_number': m.display_sub,
            'photo_url': request.build_absolute_uri(m.driver.photo.url) if m.driver and m.driver.photo else None,
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
        'photo_url': request.build_absolute_uri(driver.photo.url) if driver.photo else None,
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
        'photo_url': request.build_absolute_uri(driver.photo.url) if driver.photo else None,
        'text': '', 'audio_url': request.build_absolute_uri(msg.audio.url),
        'created_at': msg.created_at.isoformat(),
    })


# ── Guruh jonli ovozli aloqa ("efir") — ratsiya uslubi ────────────────────────
# Mikrofon tugmasi bosib turilganda ovoz yoziladi, qo'yib yuborilganda audio
# fayl serverga yuklanadi va shu payt "efir"da turgan har bir boshqa
# ishtirokchiga alohida navbat qatori sifatida (VoiceSignal, HTTP polling
# orqali — boshqa joylardagi chat_poll bilan bir xil uslub) yetkaziladi, u esa
# darhol avtomatik ijro etadi. Ilgari shu yerda WebRTC P2P mesh (real vaqtda
# uzatish) ishlatilgan edi, lekin ba'zi qurilmalar/tarmoqlarda TURN server
# yo'qligi sabab ulanish o'rnatilmay, "kimdirga eshitilib, kimdirga
# eshitilmaydi" muammosi chiqargan — oddiy yozib-yuborish esa oddiy HTTP fayl
# yuklash bo'lgani uchun ancha ishonchli.
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
    VoiceParticipant.objects.filter(driver=driver).delete()
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

    signals = list(VoiceSignal.objects.filter(to_driver=driver).select_related('from_driver', 'from_operator').order_by('created_at')[:10])
    signal_ids = [s.id for s in signals]
    if signal_ids:
        VoiceSignal.objects.filter(id__in=signal_ids).delete()

    return JsonResponse({
        'ok': True,
        'joined': True,
        'participants': voice_participants_list(f'd{driver.id}'),
        'clips': [
            dict(zip(('from', 'from_name'), voice_signal_sender_info(s)),
                 audio_url=request.build_absolute_uri(s.audio.url))
            for s in signals
        ],
    })


@driver_login_required
@require_POST
def driver_voice_send_audio(request, driver):
    from .utils import voice_prune_stale, voice_broadcast_audio
    audio = request.FILES.get('audio')
    if not audio:
        return JsonResponse({'ok': False, 'error': 'Audio fayl kerak'}, status=400)
    voice_prune_stale()
    delivered = voice_broadcast_audio({'from_driver': driver}, f'd{driver.id}', audio)
    return JsonResponse({'ok': True, 'delivered': delivered})
