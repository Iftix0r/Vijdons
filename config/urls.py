"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from taxi import views as taxi_views

admin.site.site_header = "Vijdon Taxi Boshqaruv Paneli"
admin.site.site_title = "Vijdon Taxi Admin"
admin.site.index_title = "Tizimga Xush Kelibsiz"


def android_asset_links(request):
    """Android App Links tasdiqlash fayli — driver ilovasi (uz.vijdon.vijdon_driver)
    https://vijdontaxi.uz/driver/... havolalarini brauzer o'rniga to'g'ridan-to'g'ri
    o'zida ochishi uchun kerak. https://developers.google.com/digital-asset-links"""
    return JsonResponse([
        {
            'relation': ['delegate_permission/common.handle_all_urls'],
            'target': {
                'namespace': 'android_app',
                'package_name': 'uz.vijdon.vijdon_driver',
                'sha256_cert_fingerprints': [
                    '98:AA:D8:94:F2:79:EB:DE:DC:E1:3F:46:46:22:1D:62:03:C9:AD:3A:32:91:B7:0F:80:71:B6:73:7A:91:5C:32',
                ],
            },
        },
    ], safe=False)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('.well-known/assetlinks.json', android_asset_links),
    # Reklama flayeridagi QR kod shu qisqa manzilga ishora qiladi (osonroq
    # skanerlanishi uchun /panel/ prefiksisiz) — taxi/views.py:flyer_verify
    path('flayer/<str:code>/', taxi_views.flyer_verify, name='flyer_verify'),
    path('panel/', include('taxi.urls')),
    path('system/', include('taxi.system_urls')),
    path('driver/', include('taxi.driver_urls')),
    path('client/', include('taxi.client_urls')),
    path('', RedirectView.as_view(url='/panel/', permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
