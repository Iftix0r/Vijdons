from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0018_add_extra_group_ids'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to='driver_photos/', verbose_name='Profil rasmi'),
        ),
    ]
