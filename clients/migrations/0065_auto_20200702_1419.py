# Generated by Django 2.1.7 on 2020-07-02 11:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0064_auto_20200702_1255'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='agentprofile',
            name='our_banks',
        ),
        migrations.AddField(
            model_name='agentprofile',
            name='our_banks',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='clients.Bank', verbose_name='Какие банки на платформе Тендерхелп Вам интересны'),
        ),
    ]
