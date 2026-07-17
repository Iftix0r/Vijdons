from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0019_driver_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='tmx_dist_km',
            field=models.FloatField(blank=True, default=0, null=True, verbose_name='Taximetr masofa (km)'),
        ),
    ]
