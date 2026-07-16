from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0020_driver_push_subscription'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='rating',
            field=models.DecimalField(decimal_places=2, default=5.0, max_digits=3, verbose_name='Reyting (1–5)'),
        ),
        migrations.AddField(
            model_name='driver',
            name='trips_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Jami safarlar soni'),
        ),
        migrations.AddField(
            model_name='driver',
            name='rating_count',
            field=models.PositiveIntegerField(default=0, verbose_name='Reytinglar soni'),
        ),
        migrations.AddField(
            model_name='order',
            name='client_rating',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Mijoz reytingi (1-5)'),
        ),
    ]
