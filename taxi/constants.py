# Ovozli bildirishnoma hodisalari — operator panel va haydovchi paneli uchun
# yagona ro'yxat. `taxi.models.PanelSound` shu kalitlar bo'yicha qator yaratadi,
# `sound_settings` sahifasi shu ro'yxatni ko'rsatadi.

PANEL_SOUND_EVENTS = [
    ('panel_new_order',        '🚨 Yangi buyurtma'),
    ('panel_order_deleted',    '🗑 Buyurtma o\'chirildi'),
    ('panel_order_cancelled',  '❌ Buyurtma bekor qilindi'),
    ('panel_order_rejected',   '🔄 Buyurtma rad etildi'),
    ('panel_driver_registered','🆕 Yangi haydovchi qo\'shildi'),
    ('panel_sos_alert',        '🆘 SOS signal'),
]

DRIVER_SOUND_EVENTS = [
    ('driver_new_order', '🚨 Yangi buyurtma'),
    ('driver_accept',    '✅ Buyurtma qabul qilindi'),
    ('driver_reject',    '❌ Rad etish / bekor qilish'),
    ('driver_complete',  '🏁 Buyurtma yakunlandi'),
    ('driver_online',    '🟢 Navbatga kirdi'),
    ('driver_offline',   '🔴 Navbatdan chiqdi'),
]

SOUND_EVENT_LABELS = dict(PANEL_SOUND_EVENTS + DRIVER_SOUND_EVENTS)
SOUND_EVENT_KEYS = [k for k, _ in PANEL_SOUND_EVENTS + DRIVER_SOUND_EVENTS]

# Fayl yuklanmagan bo'lsa ishlatiladigan standart statik ovoz (faqat ba'zilarida bor —
# qolganlari uchun frontend JS o'zining sintez qilingan (Web Audio) standart ohangini chaladi).
DEFAULT_SOUND_URLS = {
    'panel_new_order':  '/static/driver/sounds/new_order.wav',
    'driver_new_order': '/static/driver/sounds/new_order.wav',
}
