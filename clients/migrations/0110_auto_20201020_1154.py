# Generated by Django 2.1.7 on 2020-10-20 08:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0109_merge_20201020_1132'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='kv_previsheniya',
            field=models.CharField(blank=True, max_length=512, null=True, verbose_name='КВ превышения'),
        ),
        migrations.AddField(
            model_name='agent',
            name='ruch_correct',
            field=models.CharField(blank=True, max_length=512, null=True, verbose_name='Ручная корректировка'),
        ),
    ]