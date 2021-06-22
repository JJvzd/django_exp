# Generated by Django 2.1.7 on 2020-01-20 21:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0020_auto_20191204_1801'),
        ('cabinet', '0005_auto_20191009_1057'),
    ]

    operations = [
        migrations.AddField(
            model_name='system',
            name='default_agent',
            field=models.ForeignKey(blank=True, db_column='default_agent', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='clients.Agent'),
        ),
    ]
