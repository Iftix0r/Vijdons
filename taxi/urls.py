from django.urls import path
from . import views

app_name = 'taxi'

urlpatterns = [
    path('', views.panel_dashboard, name='panel_dashboard'),
    path('orders/', views.order_list, name='order_list'),
    path('orders/add/', views.order_create, name='order_create'),
    path('drivers/', views.driver_list, name='driver_list'),
    path('drivers/add/', views.driver_create, name='driver_create'),
    path('clients/', views.client_list, name='client_list'),
    path('clients/add/', views.client_create, name='client_create'),
]
