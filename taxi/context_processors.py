from .models import Driver


def active_drivers(request):
    """Inject active drivers into every template context for the order modal."""
    return {'active_drivers': Driver.objects.filter(is_active=True).only('pk', 'full_name', 'car_number')}
