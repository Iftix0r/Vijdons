from django.urls import path
from . import views

app_name = 'system'

# Diqqat: bu — operator panelidan (taxi/urls.py, /panel/) butunlay ALOHIDA
# panel (/system/), o'z login/logout sahifasi bilan. Bu yerdagi barcha
# view'lar `system_login_required` bilan himoyalangan (is_staff VA
# is_superuser talab qiladi) — oddiy admin/operator hisoblari bu yerga
# kira olmaydi. Ko'rib turgan view funksiyalarining o'zi hali ham
# taxi/views.py da (biznes-logikani ko'chirish shart emas edi), faqat
# marshrutlash shu yerga ko'chirildi.
urlpatterns = [
    path('login/', views.system_login, name='system_login'),
    path('logout/', views.system_logout, name='system_logout'),

    path('', views.system_status, name='system_status'),
    path('audit/', views.system_audit_log, name='system_audit_log'),
    path('run/collectstatic/', views.run_collectstatic, name='run_collectstatic'),
    path('run/migrate/', views.run_migrate, name='run_migrate'),

    path('commands/', views.system_commands, name='system_commands'),
    path('commands/<str:name>/run/', views.system_run_command, name='system_run_command'),

    path('staff/', views.system_staff_list, name='system_staff_list'),
    path('staff/create/', views.system_staff_create, name='system_staff_create'),
    path('staff/<int:pk>/toggle-staff/', views.system_staff_toggle_staff, name='system_staff_toggle_staff'),
    path('staff/<int:pk>/toggle-superuser/', views.system_staff_toggle_superuser, name='system_staff_toggle_superuser'),
    path('staff/<int:pk>/toggle-active/', views.system_staff_toggle_active, name='system_staff_toggle_active'),
    path('staff/<int:pk>/reset-password/', views.system_staff_reset_password, name='system_staff_reset_password'),
    path('backup/create/', views.backup_create, name='backup_create'),
    path('backup/<str:filename>/download/', views.backup_download, name='backup_download'),
    path('backup/<str:filename>/delete/', views.backup_delete, name='backup_delete'),

    path('tariff/', views.tariff_settings, name='tariff_settings'),
    path('maps/', views.maps_settings, name='maps_settings'),
    path('sounds/', views.sound_settings, name='sound_settings'),

    path('tasks/', views.task_list, name='task_list'),
    path('tasks/<int:pk>/status/', views.task_set_status, name='task_set_status'),
    path('tasks/<int:pk>/delete/', views.task_delete, name='task_delete'),

    path('contract/', views.contract_settings, name='contract_settings'),
    path('contract/download/', views.contract_download_blank, name='contract_download_blank'),

    path('flyer/', views.flyer_page, name='flyer_page'),
    path('flyer/download/', views.flyer_download, name='flyer_download'),
    path('flyer/redeem/', views.flyer_redeem, name='flyer_redeem'),
    path('flyer/reward/', views.flyer_reward_bonus, name='flyer_reward_bonus'),

    path('bot/', views.bot_settings, name='bot_settings'),
    path('bot/set-webhook/', views.operator_bot_set_webhook, name='operator_bot_set_webhook'),
    path('bot/webhook-status/', views.bot_webhook_status, name='bot_webhook_status'),
    path('bot/admins/add/', views.bot_admin_add, name='bot_admin_add'),
    path('bot/admins/<int:pk>/delete/', views.bot_admin_delete, name='bot_admin_delete'),
    path('bot/admins/<int:pk>/toggle/', views.bot_admin_toggle, name='bot_admin_toggle'),

    path('sms/', views.sms_settings, name='sms_settings'),
    path('ai/', views.ai_settings, name='ai_settings'),
]
