# Generated by Django 2.1.7 on 2020-02-28 06:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cabinet', '0011_auto_20200213_1335'),
    ]

    operations = [
        migrations.AddField(
            model_name='system',
            name='one_package_documents',
            field=models.BooleanField(default=True, verbose_name='Использовать один пакет документов для всех банков(Инбак/СимлФинанс)'),
        ),
    ]