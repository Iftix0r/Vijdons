from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0019_driver_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='push_subscription',
            field=models.TextField(blank=True, null=True, verbose_name='Web Push Subscription'),
        ),
    ]
