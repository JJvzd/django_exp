# Generated by Django 2.1.7 on 2020-09-28 11:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0101_merge_20200925_1029'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='disabled_banks',
            field=models.ManyToManyField(to='clients.Bank'),
        ),
    ]
