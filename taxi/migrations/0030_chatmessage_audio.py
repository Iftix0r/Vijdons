from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0029_balance_log'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='audio',
            field=models.FileField(blank=True, null=True, upload_to='chat_audio/', verbose_name='Audio xabar'),
        ),
        migrations.AlterField(
            model_name='chatmessage',
            name='text',
            field=models.TextField(blank=True, default='', verbose_name='Xabar'),
        ),
    ]
