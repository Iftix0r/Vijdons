from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0030_chatmessage_audio'),
    ]

    operations = [
        migrations.CreateModel(
            name='GroupMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(blank=True, default='', verbose_name='Xabar')),
                ('audio', models.FileField(blank=True, null=True, upload_to='group_audio/', verbose_name='Audio xabar')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Vaqt')),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='group_messages', to='taxi.driver', verbose_name='Haydovchi')),
            ],
            options={
                'verbose_name': 'Guruh xabari',
                'verbose_name_plural': 'Guruh xabarlari',
                'ordering': ['created_at'],
            },
        ),
    ]
