from django.core.management.base import BaseCommand

from taxi.utils import tg_daily_summary


class Command(BaseCommand):
    help = "Kompaniya bo'yicha kunlik umumiy hisobotni operatorlar guruhiga yuboradi (cron: har kuni 22:00)."

    def handle(self, *args, **options):
        tg_daily_summary()
        self.stdout.write(self.style.SUCCESS("Kunlik hisobot yuborildi."))
