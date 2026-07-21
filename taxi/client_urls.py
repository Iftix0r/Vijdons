from django.urls import path
from . import client_views

app_name = 'client'

urlpatterns = [
    path('',           client_views.client_login_view,    name='login'),
    path('logout/',    client_views.client_logout_view,   name='logout'),
    path('register/',  client_views.client_register_view, name='register'),

    path('home/',      client_views.client_home,          name='home'),
    path('order/create/',        client_views.client_order_create,      name='order_create'),
    path('order/poll/',          client_views.client_active_order_poll, name='order_poll'),
    path('order/<int:pk>/status/', client_views.client_order_status,    name='order_status'),
    path('order/<int:pk>/cancel/', client_views.client_order_cancel,    name='order_cancel'),

    path('history/',   client_views.client_history,       name='history'),

    path('profile/',            client_views.client_profile,          name='profile'),
    path('profile/update/',     client_views.client_profile_update,   name='profile_update'),
    path('profile/password/',   client_views.client_profile_password, name='profile_password'),
]
