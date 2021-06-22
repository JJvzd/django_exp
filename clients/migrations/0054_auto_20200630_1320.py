# Generated by Django 2.1.7 on 2020-06-30 10:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0053_auto_20200630_1309'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='agentprofile',
            name='our_banks',
        ),
        migrations.AddField(
            model_name='agentprofile',
            name='our_banks',
            field=models.CharField(blank=True, max_length=300, null=True, verbose_name='Какие банки на платформе Тендерхелп Вам интересны'),
        ),
    ]