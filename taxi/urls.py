from django.urls import path
from . import views, api_views

app_name = 'taxi'

urlpatterns = [
    # ── Web panel ──
    path('', views.panel_dashboard, name='panel_dashboard'),

    path('orders/', views.order_list, name='order_list'),
    path('orders/add/', views.order_create, name='order_create'),
    path('orders/<int:pk>/status/', views.order_update_status, name='order_update_status'),
    path('orders/<int:pk>/delete/', views.order_delete, name='order_delete'),

    path('drivers/', views.driver_list, name='driver_list'),
    path('drivers/add/', views.driver_create, name='driver_create'),
    path('drivers/<int:pk>/delete/', views.driver_delete, name='driver_delete'),
    path('drivers/<int:pk>/toggle/', views.driver_toggle_active, name='driver_toggle_active'),
    path('drivers/<int:pk>/approve/', views.driver_approve, name='driver_approve'),
    path('drivers/<int:pk>/recharge/', views.driver_recharge, name='driver_recharge'),
    path('chat/', views.operator_chat, name='operator_chat'),
    path('chat/unread/', views.operator_chat_unread, name='operator_chat_unread'),
    path('maps/', views.maps_settings, name='maps_settings'),
    path('tariff/', views.tariff_settings, name='tariff_settings'),
    path('drivers/map/', views.driver_map, name='driver_map'),
    path('drivers/api/locations/', views.active_drivers_locations, name='active_drivers_locations'),

    path('clients/', views.client_list, name='client_list'),
    path('clients/add/', views.client_create, name='client_create'),
    path('clients/<int:pk>/delete/', views.client_delete, name='client_delete'),

    # ── Mobile API ──
    path('api/driver/register/',  api_views.driver_register,    name='api_driver_register'),
    path('api/driver/login/',     api_views.driver_login,       name='api_driver_login'),
    path('api/driver/profile/',   api_views.driver_profile,     name='api_driver_profile'),
    path('api/driver/duty/',      api_views.driver_duty_toggle, name='api_driver_duty'),
    path('api/driver/fcm/',       api_views.driver_fcm_update,  name='api_driver_fcm'),
    path('api/driver/location/',  api_views.driver_location_update, name='api_driver_location'),
    path('api/geocode/reverse/',   api_views.reverse_geocode,        name='api_reverse_geocode'),

    path('api/orders/available/', api_views.available_orders, name='api_orders_available'),
    path('api/orders/my/',        api_views.my_orders,        name='api_orders_my'),
    path('api/orders/<int:pk>/reject/',   api_views.order_reject,   name='api_order_reject'),
    path('api/orders/<int:pk>/accept/',   api_views.order_accept,   name='api_order_accept'),
    path('api/orders/<int:pk>/on_way/',   api_views.order_on_way,   name='api_order_on_way'),
    path('api/orders/<int:pk>/arrived/',  api_views.order_arrived,  name='api_order_arrived'),
    path('api/orders/<int:pk>/complete/', api_views.order_complete, name='api_order_complete'),
    path('api/orders/<int:pk>/cancel/',   api_views.order_cancel,   name='api_order_cancel'),
    path('api/chat/messages/', api_views.chat_messages,    name='api_chat_messages'),
    path('api/chat/send/',     api_views.chat_send,         name='api_chat_send'),
    path('api/chat/unread/',   api_views.chat_unread_count, name='api_chat_unread'),
]
