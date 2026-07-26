from django.core.management.base import BaseCommand

from taxi.utils import tg_high_rejection_report


class Command(BaseCommand):
    help = "Ko'p buyurtmani rad etgan haydovchilar haqida operatorlar guruhiga xabar yuboradi (cron: har kuni 19:00)."

    def handle(self, *args, **options):
        tg_high_rejection_report()
        self.stdout.write(self.style.SUCCESS("Rad etish hisoboti yuborildi."))
