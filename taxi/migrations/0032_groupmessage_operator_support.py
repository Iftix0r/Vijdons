from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0031_add_group_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupmessage',
            name='sender_name',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='Yuboruvchi ismi'),
        ),
        migrations.AlterField(
            model_name='groupmessage',
            name='driver',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='group_messages', to='taxi.driver', verbose_name='Haydovchi'),
        ),
    ]
