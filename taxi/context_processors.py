from .models import Driver, SavedAddress


def active_drivers(request):
    """Inject active drivers, pending driver count, VAPID key, and maps settings into every template context."""
    import json
    from datetime import timedelta
    from django.conf import settings
    from django.db.models import Max, Count, Q
    from django.utils import timezone
    from .models import MapsSettings, TariffSettings, PanelEvent, PanelSound, BalanceLog, BalanceTopupRequest, SecurityIncident, Order
    from .constants import DRIVER_SOUND_EVENTS
    maps = MapsSettings.get()
    tariff = TariffSettings.get()
    today = timezone.now().date()

    # Yangi buyurtma oynasida "Top hududlar" chiplari — so'nggi 30 kunda eng
    # ko'p buyurtma tushgan manzillar (Statistika sahifasidagi top_addresses
    # bilan bir xil mantiq, faqat qisqaroq oyna va chiplar uchun cheklangan soni)
    top_pickup_areas = list(
        Order.objects.filter(created_at__gte=timezone.now() - timedelta(days=30))
        .exclude(from_address='')
        .values('from_address')
        .annotate(c=Count('id'), lat=Max('from_lat'), lng=Max('from_lng'))
        .order_by('-c')[:8]
    )

    sounds = PanelSound.get_map()
    driver_sounds = {}
    for key, _label in DRIVER_SOUND_EVENTS:
        snd = sounds.get(key)
        driver_sounds[key] = {
            'enabled': snd.enabled if snd else True,
            'url': snd.resolve_url() if snd else None,
        }

    latest_balance_log_id = 0
    try:
        driver = request.user.driver_profile
        latest_balance_log_id = BalanceLog.objects.filter(driver=driver).aggregate(m=Max('id'))['m'] or 0
    except Exception:
        pass

    # Sidebardagi "Ping" belgisi — hozir navbatda turgan, aloqasi sekin
    # haydovchilar soni (taxi/views.py'dagi ping_dashboard bilan bir xil
    # chegaralar)
    ping_stale_cutoff = timezone.now() - timedelta(minutes=5)
    bad_ping_driver_count = Driver.objects.filter(
        is_active=True, is_on_duty=True,
        last_ping_at__gte=ping_stale_cutoff, last_ping_ms__gte=700,
    ).count()

    return {
        # Yangi buyurtma oynasida haydovchini tanlashda "bugun nechta buyurtma
        # oldi" ko'rinib tursin — operator kam zakaz olganlarga ham teng
        # taqsimlab bera olsin.
        'active_drivers': Driver.objects.filter(
            is_active=True, approval_status=Driver.APPROVAL_APPROVED
        ).annotate(
            today_orders_count=Count(
                'orders', filter=Q(orders__created_at__date=today) & ~Q(orders__status='cancelled')
            )
        ).only('pk', 'full_name', 'car_number'),
        'pending_driver_count': Driver.objects.filter(
            approval_status=Driver.APPROVAL_PENDING
        ).count(),
        'pending_topup_count': BalanceTopupRequest.objects.filter(
            status=BalanceTopupRequest.STATUS_PENDING
        ).count(),
        'open_security_incident_count': SecurityIncident.objects.exclude(
            status=SecurityIncident.STATUS_RESOLVED
        ).count(),
        'VAPID_PUBLIC_KEY': getattr(settings, 'VAPID_PUBLIC_KEY', ''),
        'YANDEX_MAPKIT_KEY': maps.yandex_mapkit_key or '',
        # Haydovchi paneli taxi metri barcha sahifalarda (base.html) ishlashi uchun
        'tariff_base_price': int(tariff.base_price),
        'tariff_per_km':     int(tariff.price_per_km),
        'tariff_waiting_per_min': int(tariff.waiting_price_per_minute),
        'operator_phone': tariff.operator_phone,
        'car_type_choices': Driver.CAR_TYPE_CHOICES,
        # Yangi buyurtma oynasidagi tezkor manzil chiplari uchun — eng ko'p
        # ishlatilgani birinchi chiqadi (SavedAddress.Meta.ordering)
        'saved_addresses': SavedAddress.objects.all()[:20],
        'top_pickup_areas': top_pickup_areas,
        # Ovozli bildirishnomalar
        'latest_event_id': PanelEvent.objects.aggregate(m=Max('id'))['m'] or 0,
        'driver_sounds_json': json.dumps(driver_sounds),
        'latest_balance_log_id': latest_balance_log_id,
        'bad_ping_driver_count': bad_ping_driver_count,
    }
