# Generated by Django 2.1.7 on 2020-08-12 13:18

from django.db import migrations, models
import django.db.models.deletion
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0078_auto_20200730_1408'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='clientdocument',
            options={'verbose_name': 'Документ клиента', 'verbose_name_plural': 'Документы клиентов'},
        ),
        migrations.AlterModelOptions(
            name='documentlinktoperson',
            options={'verbose_name': 'Привязка документов к участникам в анкете', 'verbose_name_plural': 'Привязки документов к участникам в анкете'},
        ),
        migrations.AlterModelOptions(
            name='requestprintformrule',
            options={'verbose_name': 'Правило шаблона печатной формы', 'verbose_name_plural': 'Правила печатных форм'},
        ),
        migrations.AddField(
            model_name='offer',
            name='require_insurance',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='offerdocumentcategory',
            name='active',
            field=models.BooleanField(default=True, verbose_name='Активна'),
        ),
        migrations.AlterField(
            model_name='offerdocumentcategory',
            name='name',
            field=models.CharField(max_length=255, verbose_name='Название'),
        ),
        migrations.AlterField(
            model_name='offerdocumentcategory',
            name='need_sign',
            field=models.BooleanField(default=True, verbose_name='Требуется подписание клиентом'),
        ),
        migrations.AlterField(
            model_name='offerdocumentcategory',
            name='order',
            field=models.PositiveIntegerField(verbose_name='Порядок сортировки в списке категорий в системе'),
        ),
        migrations.AlterField(
            model_name='offerdocumentcategory',
            name='required',
            field=models.BooleanField(default=True, verbose_name='Требуется к заполнению'),
        ),
        migrations.AlterField(
            model_name='offerdocumentcategory',
            name='step',
            field=models.PositiveIntegerField(choices=[(1, 'Первый этап'), (2, 'Второй этап')], verbose_name='На каком этапе заполняется'),
        ),
        migrations.AlterField(
            model_name='offerprintform',
            name='type',
            field=models.CharField(choices=[('doc', 'doc'), ('html', 'html'), ('sf_agreement', 'sf_agreement'), ('sgb_excel', 'sgb_excel'), ('inbank_bg', 'inbank_bg'), ('sgb_bg', 'sgb_bg'), ('sgb_additional8', 'sgb_additional8'), ('sgb_additional8', 'sgb_additional8'), ('sgb_additional81', 'sgb_additional81'), ('metall_invest_anketa', 'metall_invest_anketa'), ('metall_invest_excel', 'metall_invest_excel'), ('metall_invest_conclusion', 'metall_invest_conclusion'), ('metall_invest_beneficiars', 'metall_invest_beneficiars'), ('voronej_excel', 'voronej_excel'), ('rtbk_anketa_excel', 'rtbk_anketa_excel'), ('rtbk_guarantor_excel', 'rtbk_guarantor_excel'), ('rib_th', 'rib_th'), ('rib', 'rib'), ('moscombank_execution', 'moscombank_execution'), ('moscombank_conclusion', 'moscombank_conclusion'), ('east_excel', 'east_excel'), ('east_conclusion', 'east_conclusion'), ('moscombank_anketa', 'moscombank_anketa'), ('inbank_conclusion', 'inbank_conclusion'), ('spb_guarantee', 'spb_guarantee'), ('spb_conclusion', 'spb_conclusion'), ('spb_extradition_decision', 'spb_extradition_decision'), ('egrul', 'egrul')], max_length=30),
        ),
        migrations.AlterField(
            model_name='requestprintform',
            name='active',
            field=models.BooleanField(default=True, help_text='Печатная форма генерируется для банков', verbose_name='Активна'),
        ),

        migrations.AlterField(
            model_name='requestprintform',
            name='download_name',
            field=models.CharField(help_text='Используется для понятного названия файлов при скачивании документа. Поддерживает подстановки {request_id} {request_number} {client_name} {client_inn} {client_ogrn}', max_length=300, verbose_name='Название при скачивании'),
        ),
        migrations.AlterField(
            model_name='requestprintform',
            name='enable_rules',
            field=models.BooleanField(default=False, help_text='Использовать правила для определения шаблона из базы', verbose_name='Включены правила'),
        ),
        migrations.AlterField(
            model_name='requestprintform',
            name='name',
            field=models.CharField(max_length=250, verbose_name='Название в системе'),
        ),
        migrations.AlterField(
            model_name='requestprintform',
            name='readonly',
            field=models.BooleanField(default=True, help_text='Печатная форма не доступна для редактирования пользователям системы', verbose_name='Только для чтения'),
        ),
        migrations.AlterField(
            model_name='requestprintform',
            name='roles',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('bank', 'Банк'), ('general_bank', 'Генеральный банк'), ('agent', 'Агент'), ('general_agent', 'Генеральный агент'), ('super_agent', 'Супер агент'), ('head_agent', 'Глава агент'), ('client', 'Клиент'), ('manager', 'manager'), ('mfo', 'оператор МФО'), ('verifier', 'Верификатор'), ('bank_underwriter', 'Андерайтер'), ('bank_decision_maker', 'ЛПР'), ('bank_issuer', 'Выпускающий'), ('bank_common', 'Контроль'), ('developer', 'Разработчик')], max_length=200, null=True, verbose_name='Видимо для ролей'),
        ),
        migrations.AlterField(
            model_name='requestprintform',
            name='type',
            field=models.CharField(choices=[('doc', 'doc'), ('html', 'html'), ('sf_agreement', 'sf_agreement'), ('sgb_excel', 'sgb_excel'), ('inbank_bg', 'inbank_bg'), ('sgb_bg', 'sgb_bg'), ('sgb_additional8', 'sgb_additional8'), ('sgb_additional8', 'sgb_additional8'), ('sgb_additional81', 'sgb_additional81'), ('metall_invest_anketa', 'metall_invest_anketa'), ('metall_invest_excel', 'metall_invest_excel'), ('metall_invest_conclusion', 'metall_invest_conclusion'), ('metall_invest_beneficiars', 'metall_invest_beneficiars'), ('voronej_excel', 'voronej_excel'), ('rtbk_anketa_excel', 'rtbk_anketa_excel'), ('rtbk_guarantor_excel', 'rtbk_guarantor_excel'), ('rib_th', 'rib_th'), ('rib', 'rib'), ('moscombank_execution', 'moscombank_execution'), ('moscombank_conclusion', 'moscombank_conclusion'), ('east_excel', 'east_excel'), ('east_conclusion', 'east_conclusion'), ('moscombank_anketa', 'moscombank_anketa'), ('inbank_conclusion', 'inbank_conclusion'), ('spb_guarantee', 'spb_guarantee'), ('spb_conclusion', 'spb_conclusion'), ('spb_extradition_decision', 'spb_extradition_decision'), ('egrul', 'egrul')], max_length=30, verbose_name='Тип рендера'),
        ),
        migrations.AlterField(
            model_name='requestprintformrule',
            name='policy',
            field=models.TextField(default='{}', verbose_name='Политика при которой сработает форма'),
        ),
        migrations.AlterField(
            model_name='requestprintformrule',
            name='print_form',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rules', to='bank_guarantee.RequestPrintForm', verbose_name='Печатная форма'),
        ),
    ]
