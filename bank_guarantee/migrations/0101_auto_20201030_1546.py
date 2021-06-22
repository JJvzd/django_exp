# Generated by Django 2.2 on 2020-10-30 12:46

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
            model_name='requestprintform',
            name='type',
            field=models.CharField(choices=[('doc', 'doc'), ('html', 'html'), ('sf_agreement', 'sf_agreement'), ('sgb_excel', 'sgb_excel'), ('inbank_bg', 'inbank_bg'), ('sgb_bg', 'sgb_bg'), ('sgb_additional8', 'sgb_additional8'), ('sgb_additional8', 'sgb_additional8'), ('sgb_additional81', 'sgb_additional81'), ('metall_invest_anketa', 'metall_invest_anketa'), ('metall_invest_excel', 'metall_invest_excel'), ('metall_invest_conclusion', 'metall_invest_conclusion'), ('metall_invest_beneficiars', 'metall_invest_beneficiars'), ('voronej_excel', 'voronej_excel'), ('rtbk_anketa_excel', 'rtbk_anketa_excel'), ('rtbk_guarantor_excel', 'rtbk_guarantor_excel'), ('rib_th', 'rib_th'), ('rib', 'rib'), ('moscombank_execution', 'moscombank_execution'), ('moscombank_conclusion', 'moscombank_conclusion'), ('east_excel', 'east_excel'), ('east_conclusion', 'east_conclusion'), ('moscombank_anketa', 'moscombank_anketa'), ('inbank_conclusion', 'inbank_conclusion'), ('spb_guarantee', 'spb_guarantee'), ('spb_conclusion', 'spb_conclusion'), ('spb_extradition_decision', 'spb_extradition_decision'), ('egrul', 'egrul'), ('absolut_generator', 'absolut_generator'), ('zip_absolut', 'zip_absolut')], max_length=30, verbose_name='Тип рендера'),
        ),
    ]