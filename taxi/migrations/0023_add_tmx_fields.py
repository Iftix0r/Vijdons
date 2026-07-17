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
            name='tmx_paused_ms',
            field=models.BigIntegerField(default=0, verbose_name='Taximetr pauza (ms)'),
        ),
        migrations.AddField(
            model_name='order',
            name='tmx_start_time',
            field=models.DateTimeField(null=True, blank=True, verbose_name='Taximetr boshlangan vaqt'),
        ),
    ]
