from django.core.management.base import BaseCommand

from taxi.utils import tg_inactive_drivers_report


class Command(BaseCommand):
    help = "Uzoq faol bo'lmagan haydovchilar ro'yxatini operatorlar guruhiga yuboradi (cron: har kuni 10:00)."

    def handle(self, *args, **options):
        tg_inactive_drivers_report()
        self.stdout.write(self.style.SUCCESS("Faol bo'lmagan haydovchilar hisoboti yuborildi."))
