from django.core.management.base import BaseCommand

from taxi.utils import tg_weekly_summary


class Command(BaseCommand):
    help = "Kompaniya bo'yicha haftalik umumiy hisobotni operatorlar guruhiga yuboradi (cron: har yakshanba 22:00)."

    def handle(self, *args, **options):
        tg_weekly_summary()
        self.stdout.write(self.style.SUCCESS("Haftalik hisobot yuborildi."))
