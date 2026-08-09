from django.urls import path

from . import driverapp_views as v

app_name = 'driverapp'

urlpatterns = [
    path('auth/register/', v.register, name='register'),
    path('auth/login/',    v.login,    name='login'),
    path('me/',             v.me,       name='me'),
    path('config/',         v.app_config, name='config'),

    path('duty/toggle/', v.duty_toggle,    name='duty_toggle'),
    path('location/',    v.location_update, name='location_update'),
    path('fcm/',          v.fcm_sync,        name='fcm_sync'),

    path('orders/available/',       v.orders_available, name='orders_available'),
    path('orders/my/',              v.orders_my,         name='orders_my'),
    path('orders/create/',          v.order_create,      name='order_create'),
    # Diqqat: `meter/` kabi aniq yo'llar generik `<action>` naqshidan YO'Q —
    # bu yerda har bir amal alohida view, shu sabab tartib muammosi yo'q
    # (driver_urls.py'dagi eslatma shu loyihada dolzarb emas).
    path('orders/<int:pk>/accept/',   v.order_accept,   name='order_accept'),
    path('orders/<int:pk>/reject/',   v.order_reject,   name='order_reject'),
    path('orders/<int:pk>/on_way/',   v.order_on_way,   name='order_on_way'),
    path('orders/<int:pk>/arrived/',  v.order_arrived,  name='order_arrived'),
    path('orders/<int:pk>/complete/', v.order_complete, name='order_complete'),
    path('orders/<int:pk>/meter/',    v.order_meter,    name='order_meter'),
]
