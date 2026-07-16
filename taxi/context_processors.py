from .models import Driver


def active_drivers(request):
    """Inject active drivers, pending driver count, VAPID key, and maps settings into every template context."""
    from django.conf import settings
    from .models import MapsSettings
    maps = MapsSettings.get()
    return {
        'active_drivers': Driver.objects.filter(
            is_active=True, approval_status=Driver.APPROVAL_APPROVED
        ).only('pk', 'full_name', 'car_number'),
        'pending_driver_count': Driver.objects.filter(
            approval_status=Driver.APPROVAL_PENDING
        ).count(),
        'VAPID_PUBLIC_KEY': getattr(settings, 'VAPID_PUBLIC_KEY', ''),
        'YANDEX_MAPKIT_KEY': maps.yandex_mapkit_key or '',
    }
