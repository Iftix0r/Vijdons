from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0022_merge_tmx_and_rating'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='tmx_paused',
            field=models.BooleanField(default=False, verbose_name='Taximetr pauza'),
        ),
        migrations.AddField(
            model_name='order',
            name='tmx_fare',
            field=models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='Taximetr narxi'),
        ),
        migrations.AddField(
            model_name='order',
            name='tmx_duration',
            field=models.PositiveIntegerField(null=True, blank=True, verbose_name='Taximetr vaqti (sekund)'),
        ),
    ]
