# Generated by Django 2.1.7 on 2020-05-28 13:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0061_offeradditionaldata_offeradditionaldatafield'),
    ]

    operations = [
        migrations.AddField(
            model_name='offeradditionaldatafield',
            name='label',
            field=models.CharField(default='', max_length=250),
        ),
    ]