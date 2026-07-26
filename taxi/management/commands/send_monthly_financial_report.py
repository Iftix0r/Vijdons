from django.core.management.base import BaseCommand

from taxi.utils import tg_monthly_financial_report


class Command(BaseCommand):
    help = "O'tgan oy bo'yicha moliyaviy hisobotni operatorlar guruhiga yuboradi (cron: oyning 1-kuni 09:00)."

    def handle(self, *args, **options):
        tg_monthly_financial_report()
        self.stdout.write(self.style.SUCCESS("Oylik moliyaviy hisobot yuborildi."))
