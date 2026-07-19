from .models import Driver


def active_drivers(request):
    """Inject active drivers, pending driver count, VAPID key, and maps settings into every template context."""
    import json
    from django.conf import settings
    from django.db.models import Max
    from .models import MapsSettings, TariffSettings, PanelEvent, PanelSound, BalanceLog
    from .constants import DRIVER_SOUND_EVENTS
    maps = MapsSettings.get()
    tariff = TariffSettings.get()

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

    return {
        'active_drivers': Driver.objects.filter(
            is_active=True, approval_status=Driver.APPROVAL_APPROVED
        ).only('pk', 'full_name', 'car_number'),
        'pending_driver_count': Driver.objects.filter(
            approval_status=Driver.APPROVAL_PENDING
        ).count(),
        'VAPID_PUBLIC_KEY': getattr(settings, 'VAPID_PUBLIC_KEY', ''),
        'YANDEX_MAPKIT_KEY': maps.yandex_mapkit_key or '',
        # Haydovchi paneli taxi metri barcha sahifalarda (base.html) ishlashi uchun
        'tariff_base_price': int(tariff.base_price),
        'tariff_per_km':     int(tariff.price_per_km),
        # Ovozli bildirishnomalar
        'latest_event_id': PanelEvent.objects.aggregate(m=Max('id'))['m'] or 0,
        'driver_sounds_json': json.dumps(driver_sounds),
        'latest_balance_log_id': latest_balance_log_id,
    }
