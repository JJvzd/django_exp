# Generated by Django 2.1.7 on 2020-10-14 06:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0098_auto_20201013_0914'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='kv_previsheniya',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='КВ Превышения'),
        ),
        migrations.AddField(
            model_name='offer',
            name='ruchnaya_korrect',
            field=models.CharField(default='', max_length=250, verbose_name='Ручная корректировка'),
        ),
    ]
