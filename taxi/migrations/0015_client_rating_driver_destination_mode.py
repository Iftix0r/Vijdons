from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0014_bot_settings'),
    ]

    operations = [
        # Client: reyting va safarlar soni
        migrations.AddField(
            model_name='client',
            name='rating',
            field=models.DecimalField(
                max_digits=3, decimal_places=2, default=5.00,
                verbose_name='Reyting (1–5)',
            ),
        ),
        migrations.AddField(
            model_name='client',
            name='trips_count',
            field=models.PositiveIntegerField(
                default=0, verbose_name='Jami safarlar soni',
            ),
        ),

        # Driver: destination mode
        migrations.AddField(
            model_name='driver',
            name='destination_mode',
            field=models.BooleanField(
                default=False, verbose_name="Destination mode (uyga yo'nalish)",
            ),
        ),
        migrations.AddField(
            model_name='driver',
            name='destination_lat',
            field=models.FloatField(
                null=True, blank=True, verbose_name='Yo\'nalish kenglik',
            ),
        ),
        migrations.AddField(
            model_name='driver',
            name='destination_lng',
            field=models.FloatField(
                null=True, blank=True, verbose_name='Yo\'nalish uzunlik',
            ),
        ),
        migrations.AddField(
            model_name='driver',
            name='destination_address',
            field=models.CharField(
                max_length=255, blank=True, default='',
                verbose_name='Yo\'nalish manzil',
            ),
        ),
    ]
