from django.urls import path
from . import driver_views

app_name = 'driver'

urlpatterns = [
    path('',           driver_views.driver_login_view,    name='login'),
    path('logout/',    driver_views.driver_logout_view,   name='logout'),
    path('register/',  driver_views.driver_register_view, name='register'),

    path('home/',      driver_views.driver_home,          name='home'),
    path('history/',   driver_views.driver_history,       name='history'),
    path('chat/',      driver_views.driver_chat,          name='chat'),
    path('chat/send/', driver_views.driver_chat_send,     name='chat_send'),
    path('chat/poll/', driver_views.driver_chat_poll,     name='chat_poll'),
    path('profile/',   driver_views.driver_profile,       name='profile'),
    path('profile/photo/',    driver_views.driver_profile_photo,    name='profile_photo'),
    path('profile/password/', driver_views.driver_profile_password, name='profile_password'),

    path('orders/json/',              driver_views.driver_orders_json,   name='orders_json'),
    path('orders/<int:pk>/<str:action>/', driver_views.driver_order_action, name='order_action'),

    path('sync/fcm/',      driver_views.driver_fcm_sync,        name='fcm_sync'),
    path('sync/location/', driver_views.driver_location_sync,   name='location_sync'),
    path('sync/push/',     driver_views.driver_push_subscribe,  name='push_subscribe'),
    path('duty/',          driver_views.driver_duty_toggle,     name='duty_toggle'),

    # Yandex-style funksiyalar
    path('orders/<int:pk>/eta/',    driver_views.driver_order_eta,    name='order_eta'),
    path('orders/<int:pk>/meter/',  driver_views.driver_meter_update, name='order_meter'),
    path('orders/<int:pk>/rate/',   driver_views.driver_order_rate,   name='order_rate'),
    path('surge/',                  driver_views.driver_surge_info,   name='surge_info'),
    path('sos/',                     driver_views.driver_sos_send,     name='sos_send'),
]
