# Generated by Django 2.1.7 on 2020-07-07 06:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0080_auto_20200707_0934'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agentprofile',
            name='about_us',
            field=models.CharField(blank=True, max_length=300, null=True, verbose_name='Из каких источников узнали о нас'),
        ),
        migrations.AlterField(
            model_name='agentprofile',
            name='experience',
            field=models.CharField(blank=True, max_length=15, null=True, verbose_name='Опыт работы агентом'),
        ),
        migrations.AlterField(
            model_name='agentprofile',
            name='how_clients',
            field=models.ManyToManyField(blank=True, null=True, to='clients.HowClients', verbose_name='С какими клиентами работаете'),
        ),
        migrations.AlterField(
            model_name='agentprofile',
            name='our_banks',
            field=models.ManyToManyField(blank=True, null=True, to='clients.Bank', verbose_name='Какие банки на платформе Тендерхелп Вам интересны'),
        ),
        migrations.AlterField(
            model_name='agentprofile',
            name='your_banks',
            field=models.CharField(blank=True, max_length=300, null=True, verbose_name='С какими банками работаете'),
        ),
        migrations.AlterField(
            model_name='agentprofile',
            name='your_city',
            field=models.CharField(blank=True, max_length=300, null=True, verbose_name='Город проживания'),
        ),
    ]