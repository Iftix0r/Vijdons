from django.core.management.base import BaseCommand

from taxi.utils import tg_night_greeting


class Command(BaseCommand):
    help = "Hozir navbatda turgan (tungi smena) haydovchilarga salomlashuv xabarini yuboradi (cron: har kuni 23:00)."

    def handle(self, *args, **options):
        tg_night_greeting()
        self.stdout.write(self.style.SUCCESS('Tungi salomlashuv yuborildi.'))
