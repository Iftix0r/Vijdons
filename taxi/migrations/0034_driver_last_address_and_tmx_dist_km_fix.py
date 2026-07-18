from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0033_order_status_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='driver',
            name='last_address',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name="So'nggi manzil"),
        ),
        # tmx_dist_km hozircha NULL bo'lishi mumkin edi (0020-migratsiya); NOT NULL
        # qilishdan oldin mavjud NULL qatorlarni 0 ga to'ldiramiz — aks holda
        # productionda bu o'zgarish (agar NULL qator bo'lsa) muvaffaqiyatsiz tugaydi.
        migrations.RunSQL(
            sql="UPDATE taxi_order SET tmx_dist_km = 0 WHERE tmx_dist_km IS NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name='order',
            name='tmx_dist_km',
            field=models.FloatField(default=0, verbose_name='Taximetr masofa (km)'),
        ),
    ]
