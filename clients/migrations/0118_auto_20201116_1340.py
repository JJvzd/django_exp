# Generated by Django 2.1.7 on 2020-11-16 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0117_auto_20201112_1214'),
    ]

    operations = [
        migrations.AddField(
            model_name='banksettings',
            name='date_from_update_status_via_integration',
            field=models.DateField(blank=True, null=True, verbose_name='Дата с которой заявки обновляются'),
        ),
        migrations.AddField(
            model_name='mfosettings',
            name='date_from_update_status_via_integration',
            field=models.DateField(blank=True, null=True, verbose_name='Дата с которой заявки обновляются'),
        ),
    ]