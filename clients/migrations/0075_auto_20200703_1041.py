# Generated by Django 2.1.7 on 2020-07-03 07:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0074_auto_20200703_1008'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agentprofile',
            name='our_banks',
            field=models.ManyToManyField(null=True, to='clients.Bank', verbose_name='Какие банки на платформе Тендерхелп Вам интересны'),
        ),
    ]
