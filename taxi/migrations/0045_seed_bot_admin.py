from django.db import migrations

ADMIN_CHAT_ID = '2114098498'


def add_admin(apps, schema_editor):
    BotAdmin = apps.get_model('taxi', 'BotAdmin')
    BotAdmin.objects.get_or_create(chat_id=ADMIN_CHAT_ID)


def remove_admin(apps, schema_editor):
    BotAdmin = apps.get_model('taxi', 'BotAdmin')
    BotAdmin.objects.filter(chat_id=ADMIN_CHAT_ID).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0044_botadmin'),
    ]

    operations = [
        migrations.RunPython(add_admin, remove_admin),
    ]
