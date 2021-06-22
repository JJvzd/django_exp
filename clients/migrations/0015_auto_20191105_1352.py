# Generated by Django 2.1.7 on 2019-11-05 10:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0014_merge_20191105_1320'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='agent',
            name='internal_news',
        ),
        migrations.RemoveField(
            model_name='agent',
            name='work_rules',
        ),
        migrations.AddField(
            model_name='company',
            name='internal_news',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='company',
            name='work_rules',
            field=models.PositiveIntegerField(default=0),
        ),
    ]