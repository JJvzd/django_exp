# Generated by Django 2.1.7 on 2020-10-13 07:14

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0106_auto_20201013_0959'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agentrewards',
            name='agent',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='clients.Agent'),
        ),
    ]
