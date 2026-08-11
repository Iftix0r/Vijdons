from django.db import migrations

# O'zbekiston Respublikasining rasmiy hududiy-ma'muriy bo'linishi — 12
# viloyat + Qoraqalpog'iston Respublikasi + Toshkent shahri (14 ta yuqori
# daraja). Bu ro'yxat barqaror (kamdan-kam o'zgaradi), shu sabab bir
# martalik data-migratsiya orqali to'ldiriladi — operator "Manzillar"
# bo'limida buni qo'lda kiritishi shart emas. Tumanlar esa (200 dan ortiq,
# xotiradan xatosiz sanab bo'lmaydi) ataylab BO'SH qoldirilgan — operator
# "Viloyatlar" bo'limidan o'z hududidagi tumanlarni bir martalik qo'shadi.
REGIONS = [
    "Qoraqalpog'iston Respublikasi",
    'Andijon viloyati',
    'Buxoro viloyati',
    "Farg'ona viloyati",
    'Jizzax viloyati',
    'Xorazm viloyati',
    'Namangan viloyati',
    'Navoiy viloyati',
    'Qashqadaryo viloyati',
    'Samarqand viloyati',
    'Sirdaryo viloyati',
    'Surxondaryo viloyati',
    'Toshkent viloyati',
    'Toshkent shahri',
]


def seed_regions(apps, schema_editor):
    Region = apps.get_model('taxi', 'Region')
    for i, name in enumerate(REGIONS):
        Region.objects.get_or_create(name=name, defaults={'order': i})


def remove_regions(apps, schema_editor):
    Region = apps.get_model('taxi', 'Region')
    Region.objects.filter(name__in=REGIONS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0093_region_district_savedaddress_district'),
    ]

    operations = [
        migrations.RunPython(seed_regions, remove_regions),
    ]
