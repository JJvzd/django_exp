# Generated by Django 2.1.7 on 2020-08-17 06:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0077_auto_20200722_1634'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bankofferdocumentcategory',
            options={'verbose_name': 'Привязка банка к категории документов предложения', 'verbose_name_plural': 'Привязки банка к категории документов предложения'},
        ),
        migrations.AlterModelOptions(
            name='offerdocumentcategory',
            options={'verbose_name': 'Категория документов предложения', 'verbose_name_plural': 'Категории документов предложения'},
        ),
        migrations.AlterField(
            model_name='bankofferdocumentcategory',
            name='bank',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='clients.Bank', verbose_name='Банк'),
        ),
        migrations.AlterField(
            model_name='bankofferdocumentcategory',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bank_guarantee.OfferDocumentCategory', verbose_name='Категория'),
        ),
        migrations.AlterField(
            model_name='bankofferdocumentcategory',
            name='print_form',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='bank_guarantee.OfferPrintForm', verbose_name='Печатная форма'),
        ),
    ]