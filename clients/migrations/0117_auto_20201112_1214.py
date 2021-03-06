# Generated by Django 2.1.7 on 2020-11-12 09:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0116_contractoffer__html'),
    ]

    operations = [
        migrations.AddField(
            model_name='banksettings',
            name='is_handle_bank',
            field=models.BooleanField(default=False, verbose_name='Ручной банк'),
        ),
        migrations.AddField(
            model_name='banksettings',
            name='referal_sign_from_amount',
            field=models.FloatField(default=0, verbose_name='Отправлять ссылку на подписание в чат от определённой суммы'),
        ),
        migrations.AddField(
            model_name='mfosettings',
            name='is_handle_bank',
            field=models.BooleanField(default=False, verbose_name='Ручной банк'),
        ),
        migrations.AddField(
            model_name='mfosettings',
            name='referal_sign_from_amount',
            field=models.FloatField(default=0, verbose_name='Отправлять ссылку на подписание в чат от определённой суммы'),
        ),
    ]
