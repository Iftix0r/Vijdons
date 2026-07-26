from django.core.management.base import BaseCommand

from taxi.utils import tg_top_hours_drivers


class Command(BaseCommand):
    help = "Haydovchilar guruhiga bugun eng ko'p soat navbatda turgan haydovchilar ro'yxatini yuboradi (cron: har kuni 21:00)."

    def handle(self, *args, **options):
        tg_top_hours_drivers()
        self.stdout.write(self.style.SUCCESS("Eng ko'p soat ishlagan haydovchilar ro'yxati yuborildi."))
