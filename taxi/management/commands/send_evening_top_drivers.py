from django.core.management.base import BaseCommand

from taxi.utils import tg_evening_top_drivers


class Command(BaseCommand):
    help = "Haydovchilar guruhiga bugungi TOP-10 haydovchilar ro'yxatini yuboradi (cron: har kuni 20:00)."

    def handle(self, *args, **options):
        tg_evening_top_drivers()
        self.stdout.write(self.style.SUCCESS('TOP-10 haydovchilar ro\'yxati yuborildi.'))
