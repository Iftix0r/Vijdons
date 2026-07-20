from django.urls import path
from . import driver_views

app_name = 'driver'

urlpatterns = [
    path('sw.js',      driver_views.driver_service_worker, name='sw_js'),
    path('',           driver_views.driver_login_view,    name='login'),
    path('logout/',    driver_views.driver_logout_view,   name='logout'),
    path('register/',  driver_views.driver_register_view, name='register'),

    path('home/',      driver_views.driver_home,          name='home'),
    path('history/',   driver_views.driver_history,       name='history'),
    path('chat/',      driver_views.driver_chat,          name='chat'),
    path('chat/send/', driver_views.driver_chat_send,       name='chat_send'),
    path('chat/send-audio/', driver_views.driver_chat_send_audio, name='chat_send_audio'),
    path('chat/poll/', driver_views.driver_chat_poll,       name='chat_poll'),
    path('balance/poll/', driver_views.driver_balance_poll, name='balance_poll'),
    path('profile/',   driver_views.driver_profile,       name='profile'),
    path('profile/photo/',    driver_views.driver_profile_photo,    name='profile_photo'),
    path('profile/password/', driver_views.driver_profile_password, name='profile_password'),

    path('orders/json/',              driver_views.driver_orders_json,   name='orders_json'),

    # Diqqat: bu aniq (specific) yo'llar quyidagi umumiy
    # `orders/<int:pk>/<str:action>/` naqshidan OLDIN turishi shart — aks holda
    # Django URL resolver ularni doim o'sha umumiy naqshga moslashtirib yuborardi
    # (masalan /orders/1/meter/ ham "action=meter" sifatida driver_order_action'ga
    # tushib, "Noto'g'ri amal" xatosini qaytarardi — taximetr avtosaqlashi,
    # ETA va reyting endpointlari shu sababli hech qachon ishlamas edi).
    path('orders/<int:pk>/eta/',    driver_views.driver_order_eta,    name='order_eta'),
    path('orders/<int:pk>/meter/',  driver_views.driver_meter_update, name='order_meter'),
    path('orders/<int:pk>/rate/',   driver_views.driver_order_rate,   name='order_rate'),
    path('orders/<int:pk>/<str:action>/', driver_views.driver_order_action, name='order_action'),

    path('sync/fcm/',      driver_views.driver_fcm_sync,        name='fcm_sync'),
    path('sync/location/', driver_views.driver_location_sync,   name='location_sync'),
    path('sync/push/',     driver_views.driver_push_subscribe,  name='push_subscribe'),
    path('duty/',          driver_views.driver_duty_toggle,     name='duty_toggle'),

    path('surge/',                  driver_views.driver_surge_info,   name='surge_info'),
    path('sos/',                     driver_views.driver_sos_send,     name='sos_send'),
    path('destination/',             driver_views.driver_destination,  name='destination'),

    path('group-chat/',             driver_views.driver_group_chat_list,       name='group_chat_list'),
    path('group-chat/send/',        driver_views.driver_group_chat_send,       name='group_chat_send'),
    path('group-chat/send-audio/',  driver_views.driver_group_chat_send_audio, name='group_chat_send_audio'),

    path('voice/join/',      driver_views.driver_voice_join,      name='voice_join'),
    path('voice/leave/',     driver_views.driver_voice_leave,     name='voice_leave'),
    path('voice/heartbeat/', driver_views.driver_voice_heartbeat, name='voice_heartbeat'),
    path('voice/signal/',    driver_views.driver_voice_signal,    name='voice_signal'),
]
