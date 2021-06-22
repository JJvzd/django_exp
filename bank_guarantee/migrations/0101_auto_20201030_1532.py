# Generated by Django 2.1.7 on 2020-10-30 12:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0100_auto_20201014_0949'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offerprintform',
            name='type',
            field=models.CharField(choices=[('doc', 'doc'), ('html', 'html'), ('sf_agreement', 'sf_agreement'), ('sgb_excel', 'sgb_excel'), ('inbank_bg', 'inbank_bg'), ('sgb_bg', 'sgb_bg'), ('sgb_additional8', 'sgb_additional8'), ('sgb_additional8', 'sgb_additional8'), ('sgb_additional81', 'sgb_additional81'), ('metall_invest_anketa', 'metall_invest_anketa'), ('metall_invest_excel', 'metall_invest_excel'), ('metall_invest_conclusion', 'metall_invest_conclusion'), ('metall_invest_beneficiars', 'metall_invest_beneficiars'), ('voronej_excel', 'voronej_excel'), ('rtbk_anketa_excel', 'rtbk_anketa_excel'), ('rtbk_guarantor_excel', 'rtbk_guarantor_excel'), ('rib_th', 'rib_th'), ('rib', 'rib'), ('moscombank_execution', 'moscombank_execution'), ('moscombank_conclusion', 'moscombank_conclusion'), ('east_excel', 'east_excel'), ('east_conclusion', 'east_conclusion'), ('moscombank_anketa', 'moscombank_anketa'), ('inbank_conclusion', 'inbank_conclusion'), ('spb_guarantee', 'spb_guarantee'), ('spb_conclusion', 'spb_conclusion'), ('spb_extradition_decision', 'spb_extradition_decision'), ('egrul', 'egrul'), ('absolut_generator', 'absolut_generator'), ('zip_absolut', 'zip_absolut')], max_length=30),
        ),
        migrations.AlterField(
            model_name='request',
            name='package_class',
            field=models.CharField(blank=True, choices=[('ankor', 'ankor'), ('msb', 'msb'), ('rib', 'rib'), ('sgb', 'sgb'), ('baikal', 'baikal'), ('metall_invest', 'metall_invest'), ('rtbk', 'rtbk'), ('voronej', 'voronej'), ('east', 'east'), ('rus_nar_bank', 'rus_nar_bank'), ('qiwi_bank', 'qiwi_bank'), ('rus_micro_finance', 'rus_micro_finance'), ('gaz_trans_bank', 'gaz_trans_bank'), ('simple_finance', 'simple_finance'), ('zenit', 'zenit'), ('inbank', 'inbank'), ('inter_prom_bank', 'inter_prom_bank'), ('ros_euro_bank', 'ros_euro_bank'), ('mspbank', 'mspbank'), ('prom_svyaz_bank', 'prom_svyaz_bank'), ('tinkoff_bank', 'tinkoff_bank'), ('bks_bank', 'bks_bank'), ('moscombank', 'moscombank'), ('open_bank', 'open_bank'), ('eksobank', 'eksobank'), ('lokobank', 'lokobank'), ('spb_bank', 'spb_bank'), ('alfa', 'alfa'), ('mpb', 'mpb'), ('rus_bank', 'rus_bank')], max_length=255, null=True, verbose_name='Код банка, для которого собран пакет'),
        ),
        migrations.AlterField(
            model_name='requestprintform',
            name='type',
            field=models.CharField(choices=[('doc', 'doc'), ('html', 'html'), ('sf_agreement', 'sf_agreement'), ('sgb_excel', 'sgb_excel'), ('inbank_bg', 'inbank_bg'), ('sgb_bg', 'sgb_bg'), ('sgb_additional8', 'sgb_additional8'), ('sgb_additional8', 'sgb_additional8'), ('sgb_additional81', 'sgb_additional81'), ('metall_invest_anketa', 'metall_invest_anketa'), ('metall_invest_excel', 'metall_invest_excel'), ('metall_invest_conclusion', 'metall_invest_conclusion'), ('metall_invest_beneficiars', 'metall_invest_beneficiars'), ('voronej_excel', 'voronej_excel'), ('rtbk_anketa_excel', 'rtbk_anketa_excel'), ('rtbk_guarantor_excel', 'rtbk_guarantor_excel'), ('rib_th', 'rib_th'), ('rib', 'rib'), ('moscombank_execution', 'moscombank_execution'), ('moscombank_conclusion', 'moscombank_conclusion'), ('east_excel', 'east_excel'), ('east_conclusion', 'east_conclusion'), ('moscombank_anketa', 'moscombank_anketa'), ('inbank_conclusion', 'inbank_conclusion'), ('spb_guarantee', 'spb_guarantee'), ('spb_conclusion', 'spb_conclusion'), ('spb_extradition_decision', 'spb_extradition_decision'), ('egrul', 'egrul'), ('absolut_generator', 'absolut_generator'), ('zip_absolut', 'zip_absolut')], max_length=30, verbose_name='Тип рендера'),
        ),
    ]
