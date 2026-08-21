import time

from django.conf import settings


class DriverFakeSlowMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        delay = getattr(settings, 'DRIVER_FAKE_DELAY_SECONDS', 0)
        driver_prefixes = (
            '/driver/',
            '/api/driverapp/',
            '/api/driver/',
            '/api/orders/',
            '/api/chat/',
            '/api/sos/',
        )
        is_driver_request = request.path.startswith(driver_prefixes)
        if delay and is_driver_request:
            time.sleep(max(0, float(delay)))
        return self.get_response(request)
