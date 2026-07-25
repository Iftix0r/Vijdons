"""Ilova ichidagi kunlik xabarlar rejalashtiruvchisi.

Serverning o'zi (background thread orqali) har kuni belgilangan soatda
haydovchilar guruhiga xabar yuboradi — buning uchun tashqi cron shart emas.
Har bir worker jarayoni o'z threadini ishga tushirsa ham, DB darajasidagi
atomik UPDATE orqali kuniga faqat bitta jarayon xabarni haqiqatda yuboradi.
"""
import logging
import threading
import time

logger = logging.getLogger(__name__)

# (soat, BotSettings dagi "oxirgi yuborilgan sana" maydoni, utils.py dagi funksiya nomi)
_SCHEDULE = (
    (7,  'last_morning_greeting_date',    'tg_morning_greeting'),
    (20, 'last_evening_top_drivers_date', 'tg_evening_top_drivers'),
    (23, 'last_night_greeting_date',      'tg_night_greeting'),
)

_TICK_SECONDS = 30


def _claim_and_run(field, fn_name, today):
    """Shu kun uchun `field` hali belgilanmagan bo'lsa, atomik ravishda
    egallab oladi va True qaytaradi — faqat shunda xabar yuboriladi."""
    from django.db.models import Q

    from taxi import utils
    from taxi.models import BotSettings

    claimed = BotSettings.objects.filter(pk=1).filter(
        Q(**{f'{field}__isnull': True}) | Q(**{f'{field}__lt': today})
    ).update(**{field: today})

    if claimed:
        getattr(utils, fn_name)()


def _run_loop():
    from django.utils import timezone

    while True:
        try:
            now = timezone.localtime()
            if now.minute == 0:
                today = now.date()
                for hour, field, fn_name in _SCHEDULE:
                    if now.hour == hour:
                        _claim_and_run(field, fn_name, today)
        except Exception:
            logger.exception('Kunlik xabar scheduleri tick paytida xato berdi')
        time.sleep(_TICK_SECONDS)


def start():
    threading.Thread(target=_run_loop, name='vijdon-daily-scheduler', daemon=True).start()
