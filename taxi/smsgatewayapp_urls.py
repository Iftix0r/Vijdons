from django.urls import path

from . import smsgatewayapp_views as v

app_name = 'smsgatewayapp'

urlpatterns = [
    path('fcm/',              v.fcm_sync,      name='fcm_sync'),
    path('pending/',          v.pending,       name='pending'),
    path('<int:pk>/result/',  v.report_result, name='report_result'),
]
