# Generated by Django 2.1.7 on 2020-04-15 13:46

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0047_auto_20200327_1652'),
    ]

    operations = [
        migrations.CreateModel(
            name='RequestedCategory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Наименование запрашиваемого документа')),
            ],
        ),
        migrations.AlterField(
            model_name='request',
            name='package_class',
            field=models.CharField(blank=True, choices=[('ankor', 'ankor'), ('msb', 'msb'), ('rib', 'rib'), ('sgb', 'sgb'), ('baikal', 'baikal'), ('metall_invest', 'metall_invest'), ('rtbk', 'rtbk'), ('voronej', 'voronej'), ('east', 'east'), ('rus_nar_bank', 'rus_nar_bank'), ('qiwi_bank', 'qiwi_bank'), ('rus_micro_finance', 'rus_micro_finance'), ('gaz_trans_bank', 'gaz_trans_bank'), ('simple_finance', 'simple_finance'), ('zenit', 'zenit'), ('inbank', 'inbank'), ('inter_prom_bank', 'inter_prom_bank'), ('ros_euro_bank', 'ros_euro_bank'), ('mspbank', 'mspbank'), ('prom_svyaz_bank', 'prom_svyaz_bank'), ('tinkoff_bank', 'tinkoff_bank'), ('bks_bank', 'bks_bank'), ('moscombank', 'moscombank'), ('open_bank', 'open_bank'), ('eksobank', 'eksobank'), ('lokobank', 'lokobank'), ('spb_bank', 'spb_bank')], max_length=255, null=True, verbose_name='Код банка, для которого собран пакет'),
        ),
        migrations.AddField(
            model_name='requestedcategory',
            name='request',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bank_guarantee.Request'),
        ),
        migrations.AddField(
            model_name='requestdocument',
            name='requested_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='bank_guarantee.RequestedCategory'),
        ),
    ]
