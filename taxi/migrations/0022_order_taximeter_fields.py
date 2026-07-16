from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0021_driver_rating_order_client_rating'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='tmx_start_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Taximetr boshlangan vaqt'),
        ),
        migrations.AddField(
            model_name='order',
            name='tmx_dist_km',
            field=models.FloatField(default=0, verbose_name='Taximetr masofa (km)'),
        ),
        migrations.AddField(
            model_name='order',
            name='tmx_paused',
            field=models.BooleanField(default=False, verbose_name='Taximetr pauza'),
        ),
        migrations.AddField(
            model_name='order',
            name='tmx_paused_ms',
            field=models.BigIntegerField(default=0, verbose_name='Jami pauza vaqti (ms)'),
        ),
    ]
