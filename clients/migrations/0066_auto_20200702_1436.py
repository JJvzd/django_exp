# Generated by Django 2.1.7 on 2020-07-02 11:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0065_auto_20200702_1419'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='agentprofile',
            name='our_banks',
        ),
        migrations.AddField(
            model_name='agentprofile',
            name='our_banks',
            field=models.ManyToManyField(blank=True, null=True, to='clients.Bank', verbose_name='Какие банки на платформе Тендерхелп Вам интересны'),
        ),
    ]
