# Generated by Django 2.1.7 on 2020-03-27 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0046_auto_20200326_1659'),
    ]

    operations = [
        migrations.AlterField(
            model_name='request',
            name='delivery_phone',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Телефон получателя'),
        ),
    ]
