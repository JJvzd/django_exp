# Generated by Django 2.1.7 on 2019-11-05 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0025_merge_20191105_1320'),
    ]

    operations = [
        migrations.AlterField(
            model_name='request',
            name='package_class',
            field=models.CharField(choices=[('ankor', 'ankor'), ('msb', 'msb'), ('rib', 'rib'), ('sgb', 'sgb'), ('baikal', 'baikal'), ('metall_invest', 'metall_invest'), ('rtbk', 'rtbk'), ('voronej', 'voronej'), ('east', 'east'), ('rus_nar_bank', 'rus_nar_bank'), ('qiwi_bank', 'qiwi_bank'), ('rus_micro_finance', 'rus_micro_finance'), ('gaz_trans_bank', 'gaz_trans_bank'), ('simple_finance', 'simple_finance'), ('zenit', 'zenit'), ('inbank', 'inbank'), ('inter_prom_bank', 'inter_prom_bank'), ('ros_euro_bank', 'ros_euro_bank'), ('mspbank', 'mspbank'), ('prom_svyaz_bank', 'prom_svyaz_bank'), ('tinkoff_bank', 'tinkoff_bank'), ('bks_bank', 'bks_bank'), ('moscombank', 'moscombank'), ('open_bank', 'open_bank')], max_length=255, verbose_name='Код банка, для которого собран пакет'),
        ),
    ]