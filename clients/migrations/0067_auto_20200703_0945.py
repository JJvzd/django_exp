# Generated by Django 2.1.7 on 2020-07-03 06:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0066_auto_20200702_1436'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='agentprofile',
            name='our_banks',
        ),
        migrations.AddField(
            model_name='agentprofile',
            name='our_banks',
            field=models.CharField(blank=True, max_length=1024, null=True, verbose_name='Какие банки на платформе Тендерхелп Вам интересны'),
        ),
    ]
