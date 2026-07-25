"""Ilova ichidagi kunlik/haftalik/oylik xabarlar rejalashtiruvchisi.

Serverning o'zi (background thread orqali) belgilangan vaqtda haydovchilar
guruhiga xabar yuboradi — buning uchun tashqi cron shart emas.
Har bir worker jarayoni o'z threadini ishga tushirsa ham, DB darajasidagi
atomik UPDATE orqali bir marta yuborilishi kafolatlanadi.
"""
import logging
import threading
import time

logger = logging.getLogger(__name__)

# (soat, BotSettings dagi "oxirgi yuborilgan sana" maydoni, utils.py dagi funksiya nomi)
# Har kuni shu soatning 00-daqiqasida tekshiriladi.
_DAILY_SCHEDULE = (
    (7,  'last_morning_greeting_date',        'tg_morning_greeting'),
    (10, 'last_inactive_drivers_report_date', 'tg_inactive_drivers_report'),
    (20, 'last_evening_top_drivers_date',     'tg_evening_top_drivers'),
    (23, 'last_night_greeting_date',          'tg_night_greeting'),
)

_WEEKLY_HOUR  = 21  # Yakshanba kuni shu soatda
_MONTHLY_HOUR = 21  # Oyning oxirgi kunida shu soatda

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


def _run_tick():
    from datetime import timedelta

    from django.utils import timezone

    from taxi import utils

    # Talab (surge) tekshiruvi — har tickda, soatidan qat'i nazar
    # (utils.tg_surge_alert_check o'zi cooldown/toggle bilan spam bo'lmasligini
    # ta'minlaydi).
    utils.tg_surge_alert_check()

    now = timezone.localtime()
    if now.minute != 0:
        return
    today = now.date()

    for hour, field, fn_name in _DAILY_SCHEDULE:
        if now.hour == hour:
            _claim_and_run(field, fn_name, today)

    if now.hour == _WEEKLY_HOUR and now.isoweekday() == 7:
        _claim_and_run('last_weekly_top_drivers_date', 'tg_weekly_top_drivers', today)

    if now.hour == _MONTHLY_HOUR and (today + timedelta(days=1)).day == 1:
        _claim_and_run('last_monthly_top_drivers_date', 'tg_monthly_top_drivers', today)


def _run_loop():
    while True:
        try:
            _run_tick()
        except Exception:
            logger.exception('Xabar scheduleri tick paytida xato berdi')
        time.sleep(_TICK_SECONDS)


def start():
    threading.Thread(target=_run_loop, name='vijdon-daily-scheduler', daemon=True).start()
