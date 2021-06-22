# Generated by Django 2.1.7 on 2020-10-12 09:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clients', '0104_auto_20201001_1620'),
        ('bank_guarantee', '0095_request_tmp_manager'),
    ]

    operations = [
        migrations.CreateModel(
            name='AgentRewards',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(blank=True, null=True, verbose_name='Дата')),
                ('number', models.CharField(default='', max_length=250, verbose_name='Количество выданных заявок')),
                ('procent', models.CharField(default='', max_length=250, verbose_name='Проценты')),
                ('agent', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='agent_rewards', to=settings.AUTH_USER_MODEL)),
                ('bank', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='clients.Bank')),
            ],
        ),
    ]