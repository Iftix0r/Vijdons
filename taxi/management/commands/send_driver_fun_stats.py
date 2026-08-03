from django.core.management.base import BaseCommand

from taxi.utils import tg_driver_fun_stats


class Command(BaseCommand):
    help = "Haydovchilar guruhiga kunlik qiziqarli statistikani yuboradi (cron: har kuni 16:00)."

    def handle(self, *args, **options):
        tg_driver_fun_stats()
        self.stdout.write(self.style.SUCCESS('Kunlik qiziqarli statistika yuborildi.'))
