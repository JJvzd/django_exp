# Generated by Django 2.1.7 on 2020-02-28 16:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0025_auto_20200218_1406'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='created',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
