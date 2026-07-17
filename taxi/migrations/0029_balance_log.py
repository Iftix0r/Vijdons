from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0028_client_is_blocked'),
    ]

    operations = [
        migrations.CreateModel(
            name='BalanceLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('add', "Qo'shildi"), ('deduct', 'Ayirildi')], max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('balance_after', models.DecimalField(decimal_places=2, max_digits=12)),
                ('note', models.CharField(blank=True, default='', max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='balance_logs', to='taxi.driver', verbose_name='Haydovchi')),
            ],
            options={'verbose_name': 'Balans tarixi', 'ordering': ['-created_at']},
        ),
    ]
