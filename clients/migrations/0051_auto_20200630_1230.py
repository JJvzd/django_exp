# Generated by Django 2.1.7 on 2020-06-30 09:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0050_auto_20200630_1211'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agent',
            name='equal_fact_and_legal_address',
            field=models.BooleanField(default=False, verbose_name='Почтовый адрес отличается от юридического'),
        ),
    ]
