from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0013_driver_activity_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='BotSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('bot_token',   models.CharField(blank=True, default='', max_length=200, verbose_name='Bot Token', help_text='@BotFather dan olingan token')),
                ('group_id',    models.CharField(blank=True, default='', max_length=50,  verbose_name='Guruh Chat ID', help_text='Operatorlar Telegram guruhi chat_id')),
                ('notify_new_order',       models.BooleanField(default=True,  verbose_name='Yangi buyurtma')),
                ('notify_dispatched',      models.BooleanField(default=True,  verbose_name='Buyurtma yuborildi')),
                ('notify_accepted',        models.BooleanField(default=True,  verbose_name='Buyurtma qabul qilindi')),
                ('notify_on_way',          models.BooleanField(default=True,  verbose_name="Haydovchi yo'lda")),
                ('notify_arrived',         models.BooleanField(default=True,  verbose_name='Haydovchi yetib keldi')),
                ('notify_completed',       models.BooleanField(default=True,  verbose_name='Buyurtma yakunlandi')),
                ('notify_cancelled',       models.BooleanField(default=True,  verbose_name='Buyurtma bekor qilindi')),
                ('notify_rejected',        models.BooleanField(default=False, verbose_name='Buyurtma rad etildi')),
                ('notify_driver_register', models.BooleanField(default=True,  verbose_name="Yangi haydovchi ro'yxatdan o'tdi")),
                ('notify_driver_approved', models.BooleanField(default=True,  verbose_name='Haydovchi tasdiqlandi')),
                ('notify_driver_rejected', models.BooleanField(default=True,  verbose_name='Haydovchi rad etildi')),
                ('notify_driver_blocked',  models.BooleanField(default=True,  verbose_name='Haydovchi bloklandi/ochildi')),
                ('notify_driver_login',    models.BooleanField(default=False, verbose_name='Haydovchi kirdi (login)')),
                ('notify_duty_changed',    models.BooleanField(default=False, verbose_name="Navbat holati o'zgardi")),
                ('notify_balance_changed', models.BooleanField(default=True,  verbose_name="Balans o'zgardi")),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Bot sozlamalari',
                'verbose_name_plural': 'Bot sozlamalari',
            },
        ),
    ]
