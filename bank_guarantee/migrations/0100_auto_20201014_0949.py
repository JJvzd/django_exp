# Generated by Django 2.1.7 on 2020-10-14 06:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0099_auto_20201014_0944'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offer',
            name='kv_previsheniya',
            field=models.DecimalField(blank=True, decimal_places=2, default=0, max_digits=20,  verbose_name='КВ Превышения'),
        ),
        migrations.AlterField(
            model_name='offer',
            name='ruchnaya_korrect',
            field=models.CharField(blank=True, default='', max_length=250, verbose_name='Ручная корректировка'),
        ),
    ]