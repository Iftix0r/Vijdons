from django.core.management.base import BaseCommand

from taxi.utils import tg_morning_greeting


class Command(BaseCommand):
    help = "Haydovchilar guruhiga ertalabki salomlashuv xabarini yuboradi (cron: har kuni 07:00)."

    def handle(self, *args, **options):
        tg_morning_greeting()
        self.stdout.write(self.style.SUCCESS('Ertalabki salomlashuv yuborildi.'))
