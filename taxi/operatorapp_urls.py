from django.urls import path

from . import operatorapp_views as v

app_name = 'operatorapp'

urlpatterns = [
    path('auth/login/', v.login, name='login'),
    path('me/',          v.me,       name='me'),
    path('fcm/',          v.fcm_sync, name='fcm_sync'),

    path('dashboard/', v.dashboard, name='dashboard'),

    path('orders/',               v.order_list,   name='order_list'),
    path('orders/create/',        v.order_create, name='order_create'),
    path('orders/<int:pk>/',            v.order_detail,   name='order_detail'),
    path('orders/<int:pk>/status/',     v.order_status,   name='order_status'),
    path('orders/<int:pk>/dispatch/',   v.order_dispatch, name='order_dispatch'),
    path('orders/<int:pk>/cancel/',     v.order_cancel,   name='order_cancel'),
    path('orders/<int:pk>/delete/',     v.order_delete,   name='order_delete'),

    path('drivers/',               v.driver_list,  name='driver_list'),
    path('drivers/live/',          v.driver_live,  name='driver_live'),
    path('drivers/<int:pk>/',                v.driver_detail,        name='driver_detail'),
    path('drivers/<int:pk>/approve/',        v.driver_approve,       name='driver_approve'),
    path('drivers/<int:pk>/toggle_active/',  v.driver_toggle_active, name='driver_toggle_active'),
    path('drivers/<int:pk>/toggle_frozen/',  v.driver_toggle_frozen, name='driver_toggle_frozen'),
    path('drivers/<int:pk>/recharge/',       v.driver_recharge,      name='driver_recharge'),

    path('chat/drivers/',                    v.chat_driver_list, name='chat_driver_list'),
    path('chat/<int:driver_id>/messages/',   v.chat_messages,    name='chat_messages'),
    path('chat/<int:driver_id>/send/',       v.chat_send,        name='chat_send'),
    path('chat/unread/',                     v.chat_unread,      name='chat_unread'),
    path('chat/group/',                      v.chat_group_list,  name='chat_group_list'),
    path('chat/group/send/',                 v.chat_group_send,  name='chat_group_send'),

    path('balance/topups/',              v.topup_list,    name='topup_list'),
    path('balance/topups/<int:pk>/resolve/', v.topup_resolve, name='topup_resolve'),
    path('balance/log/',                 v.balance_log,   name='balance_log'),
]
