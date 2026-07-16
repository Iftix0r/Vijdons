from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0011_maps_settings'),
    ]

    operations = [
        migrations.AddField(
            model_name='mapssettings',
            name='yandex_mapkit_key',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Mobil ilova xaritasi uchun (haydovchi va mijoz ilovasi)',
                max_length=255,
                verbose_name='Yandex MapKit API kalit',
            ),
        ),
        migrations.AlterField(
            model_name='mapssettings',
            name='api_key',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Nominatim uchun shart emas',
                max_length=255,
                verbose_name='Geocoding API kalit',
            ),
        ),
    ]
