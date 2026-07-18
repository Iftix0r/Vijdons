from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0032_groupmessage_operator_support'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status', 'driver'], name='taxi_order_status_driver_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status', 'dispatched_to'], name='taxi_order_status_dispatch_idx'),
        ),
    ]
