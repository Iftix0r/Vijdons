from django.core.management.base import BaseCommand

from taxi.utils import tg_monthly_top_drivers


class Command(BaseCommand):
    help = "Haydovchilar guruhiga shu oyning TOP-10 ro'yxatini yuboradi (cron: har oyning oxirgi kuni 21:00)."

    def handle(self, *args, **options):
        tg_monthly_top_drivers()
        self.stdout.write(self.style.SUCCESS("Oylik TOP-10 yuborildi."))
