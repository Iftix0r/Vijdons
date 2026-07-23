from django.db import migrations

ADMIN_CHAT_ID = '2114098498'


def add_admin_chat_id(apps, schema_editor):
    BotSettings = apps.get_model('taxi', 'BotSettings')
    bot, _ = BotSettings.objects.get_or_create(pk=1)
    ids = [line.strip() for line in bot.admin_chat_ids.splitlines() if line.strip()]
    if ADMIN_CHAT_ID not in ids:
        ids.append(ADMIN_CHAT_ID)
        bot.admin_chat_ids = '\n'.join(ids)
        bot.save(update_fields=['admin_chat_ids'])


def remove_admin_chat_id(apps, schema_editor):
    BotSettings = apps.get_model('taxi', 'BotSettings')
    bot = BotSettings.objects.filter(pk=1).first()
    if not bot:
        return
    ids = [line.strip() for line in bot.admin_chat_ids.splitlines() if line.strip() and line.strip() != ADMIN_CHAT_ID]
    bot.admin_chat_ids = '\n'.join(ids)
    bot.save(update_fields=['admin_chat_ids'])


class Migration(migrations.Migration):

    dependencies = [
        ('taxi', '0044_botsettings_admin_chat_ids'),
    ]

    operations = [
        migrations.RunPython(add_admin_chat_id, remove_admin_chat_id),
    ]
