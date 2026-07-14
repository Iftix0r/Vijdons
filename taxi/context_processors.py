from .models import Driver


def active_drivers(request):
    """Inject active drivers and pending driver count into every template context."""
    return {
        'active_drivers': Driver.objects.filter(
            is_active=True, approval_status=Driver.APPROVAL_APPROVED
        ).only('pk', 'full_name', 'car_number'),
        'pending_driver_count': Driver.objects.filter(
            approval_status=Driver.APPROVAL_PENDING
        ).count(),
    }
