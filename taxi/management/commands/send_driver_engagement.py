from django.core.management.base import BaseCommand

from taxi.utils import tg_driver_engagement


class Command(BaseCommand):
    help = "Haydovchilar guruhiga tasodifiy motivatsion/maslahat/hazil xabar yuboradi (cron: kuniga 2 marta, masalan 12:00 va 18:00)."

    def handle(self, *args, **options):
        tg_driver_engagement()
        self.stdout.write(self.style.SUCCESS('Motivatsion/maslahat xabari yuborildi.'))
