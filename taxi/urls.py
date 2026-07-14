from django.urls import path
from . import views

app_name = 'taxi'

urlpatterns = [
    path('', views.panel_dashboard, name='panel_dashboard'),

    # Orders
    path('orders/', views.order_list, name='order_list'),
    path('orders/add/', views.order_create, name='order_create'),
    path('orders/<int:pk>/status/', views.order_update_status, name='order_update_status'),
    path('orders/<int:pk>/delete/', views.order_delete, name='order_delete'),

    # Drivers
    path('drivers/', views.driver_list, name='driver_list'),
    path('drivers/add/', views.driver_create, name='driver_create'),
    path('drivers/<int:pk>/delete/', views.driver_delete, name='driver_delete'),
    path('drivers/<int:pk>/toggle/', views.driver_toggle_active, name='driver_toggle_active'),

    # Clients
    path('clients/', views.client_list, name='client_list'),
    path('clients/add/', views.client_create, name='client_create'),
    path('clients/<int:pk>/delete/', views.client_delete, name='client_delete'),
]
