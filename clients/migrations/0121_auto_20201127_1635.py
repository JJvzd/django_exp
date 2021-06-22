# Generated by Django 2.2 on 2020-11-27 13:35

from django.db import migrations


def write_replaced(apps, schema_editor):
    ContractOffer = apps.get_model('clients', 'ContractOffer')
    contracts = ContractOffer.objects.all().order_by('start_date')
    length = contracts.count()
    if length:
        for index in range(1, length):
            contract = contracts[index - 1]
            contract.replaced = contracts[index]
            contract.save()


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0120_auto_20201127_1516'),
    ]

    operations = [
        migrations.RunPython(write_replaced)
    ]