# Generated by Django 2.1.7 on 2020-08-25 07:36

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0094_auto_20200825_1024'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agentmanager',
            name='agent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='manager', to='clients.Agent', unique=True),
        ),
    ]
