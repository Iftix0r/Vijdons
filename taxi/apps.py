import os
import sys
import time

from django.apps import AppConfig

# Diqqat: bu jarayon (worker) qachon ishga tushganini eslab qolamiz — panel
# ichidagi "Tizim holati" sahifasi shuni ko'rsatadi ("ilova qachondan beri
# ishlayapti", worker yaqinda qulab qayta ko'tarilganmi degan savolga javob).
# Har bir Passenger/WSGI worker o'zining `ready()`sini chaqirgani uchun bu
# aynan JORIY workerning boshlanish vaqti, butun serverning emas.
PROCESS_STARTED_AT = time.time()


class TaxiConfig(AppConfig):
    name = 'taxi'

    def ready(self):
        if not self._should_start_scheduler():
            return
        from . import scheduler
        scheduler.start()

    @staticmethod
    def _should_start_scheduler():
        """`manage.py migrate/shell/send_*` kabi bir martalik buyruqlarda
        scheduler ishga tushmasin — faqat haqiqiy serverda (runserver yoki
        WSGI/Passenger orqali) ishga tushsin."""
        if len(sys.argv) > 1 and sys.argv[0].endswith('manage.py'):
            if sys.argv[1] != 'runserver':
                return False
            # runserver avtomatik qayta yuklanadi (autoreload) — faqat
            # haqiqiy ishchi jarayonda ishga tushirish uchun tekshiruv.
            return os.environ.get('RUN_MAIN') == 'true'
        return True
