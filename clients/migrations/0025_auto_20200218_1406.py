# Generated by Django 2.1.7 on 2020-02-18 11:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0024_auto_20200211_1717'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bank',
            name='code',
            field=models.CharField(max_length=20, unique=True),
        ),
    ]
