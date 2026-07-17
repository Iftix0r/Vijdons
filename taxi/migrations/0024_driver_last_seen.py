from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0023_add_tmx_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='last_seen',
            field=models.DateTimeField(blank=True, null=True, verbose_name="So'nggi faollik"),
        ),
    ]
