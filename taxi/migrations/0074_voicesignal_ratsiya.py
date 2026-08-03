from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0073_order_created_by_driver'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='voicesignal',
            name='kind',
        ),
        migrations.RemoveField(
            model_name='voicesignal',
            name='payload',
        ),
        migrations.AddField(
            model_name='voicesignal',
            name='audio',
            field=models.FileField(default='', upload_to='voice_clips/', verbose_name='Ovozli xabar'),
            preserve_default=False,
        ),
        migrations.AlterModelOptions(
            name='voicesignal',
            options={'ordering': ['created_at'], 'verbose_name': 'Efir ovozli xabari', 'verbose_name_plural': 'Efir ovozli xabarlari'},
        ),
    ]
