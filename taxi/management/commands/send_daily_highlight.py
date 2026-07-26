from django.core.management.base import BaseCommand

from taxi.utils import tg_daily_highlight_trip


class Command(BaseCommand):
    help = "Kunning eng uzoq/eng qimmat safarini haydovchilar guruhiga yuboradi (cron: har kuni 20:00)."

    def handle(self, *args, **options):
        tg_daily_highlight_trip()
        self.stdout.write(self.style.SUCCESS("Kunning yorqin lahzalari yuborildi."))
