# Generated by Django 2.1.7 on 2020-03-13 13:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0027_clientchangeagenthistory'),
    ]

    operations = [
        migrations.AddField(
            model_name='banksettings',
            name='limit_for_client',
            field=models.FloatField(default=0, verbose_name='Лимит на клиента'),
        ),
        migrations.AddField(
            model_name='mfosettings',
            name='limit_for_client',
            field=models.FloatField(default=0, verbose_name='Лимит на клиента'),
        ),
    ]