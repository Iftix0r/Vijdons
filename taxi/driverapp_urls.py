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

    path('history/', v.order_history, name='order_history'),
    path('rating/',  v.rating,        name='rating'),

    path('profile/photo/',    v.profile_photo,    name='profile_photo'),
    path('profile/password/', v.profile_password, name='profile_password'),

    path('balance/history/', v.balance_history, name='balance_history'),
    path('balance/topup/',   v.balance_topup,   name='balance_topup'),

    path('contract/',      v.contract_detail, name='contract_detail'),
    path('contract/sign/', v.contract_sign,   name='contract_sign'),

    path('addresses/',                        v.addresses_list,     name='addresses_list'),
    path('addresses/<int:pk>/queue/',         v.address_queue_position, name='address_queue_position'),
    path('addresses/<int:pk>/queue/drivers/', v.address_queue_drivers,  name='address_queue_drivers'),

    path('destination/', v.destination_set, name='destination_set'),
    path('sos/',          v.sos_send,        name='sos_send'),
    path('surge/',        v.surge_info,      name='surge_info'),
    path('nearby-drivers/', v.nearby_drivers, name='nearby_drivers'),
]
