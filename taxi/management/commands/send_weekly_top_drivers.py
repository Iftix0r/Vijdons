from django.core.management.base import BaseCommand

from taxi.utils import tg_weekly_top_drivers


class Command(BaseCommand):
    help = "Haydovchilar guruhiga shu haftaning TOP-10 ro'yxatini yuboradi (cron: har yakshanba 21:00)."

    def handle(self, *args, **options):
        tg_weekly_top_drivers()
        self.stdout.write(self.style.SUCCESS("Haftalik TOP-10 yuborildi."))
