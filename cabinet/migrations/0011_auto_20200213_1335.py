# Generated by Django 2.1.7 on 2020-02-13 10:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cabinet', '0010_auto_20200213_1323'),
    ]

    operations = [
        migrations.AlterField(
            model_name='system',
            name='scoring_on',
            field=models.BooleanField(default=True, verbose_name='Скоринг во всех банках'),
        ),
    ]
