# Generated by Django 2.1.7 on 2019-10-20 15:18

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base_request', '0005_auto_20191020_1755'),
        ('questionnaire', '0006_auto_20191020_1755'),
        ('bank_guarantee', '0014_auto_20191015_2230'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentLinkToPerson',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bank_guarantee.RequestDocument')),
                ('document_category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base_request.BankDocumentType')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='questionnaire.ProfilePartnerIndividual')),
                ('request', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bank_guarantee.Request')),
            ],
        ),
    ]