# Generated by Django 2.1.7 on 2020-08-17 06:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0092_auto_20200817_0912'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='fill_requisites',
            field=models.BooleanField(default=False),
        ),
    ]
