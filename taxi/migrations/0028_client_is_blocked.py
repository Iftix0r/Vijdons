from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0024_driver_last_seen'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='is_blocked',
            field=models.BooleanField(default=False, verbose_name='Bloklangan'),
        ),
    ]
