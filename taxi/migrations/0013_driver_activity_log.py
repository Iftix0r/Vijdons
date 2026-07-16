from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0012_add_yandex_mapkit_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='DriverActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[
                    ('login',    'Kirish'),
                    ('logout',   'Chiqish'),
                    ('block',    'Bloklandi'),
                    ('unblock',  'Blok ochildi'),
                    ('balance',  "Balans o'zgardi"),
                    ('duty_on',  'Navbatga kirdi'),
                    ('duty_off', 'Navbatdan chiqdi'),
                    ('order',    'Buyurtma'),
                ], max_length=20, verbose_name='Amal')),
                ('detail',     models.CharField(blank=True, default='', max_length=500, verbose_name='Tafsilot')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP manzil')),
                ('user_agent', models.TextField(blank=True, default='', verbose_name='Qurilma / Brauzer')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Vaqt')),
                ('driver', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='activity_logs',
                    to='taxi.driver',
                    verbose_name='Haydovchi',
                )),
            ],
            options={
                'verbose_name': 'Faollik logi',
                'verbose_name_plural': 'Faollik loglari',
                'ordering': ['-created_at'],
            },
        ),
    ]
