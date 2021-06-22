# Generated by Django 2.1.7 on 2020-04-30 10:34
from datetime import datetime

from django.db import migrations
from django.utils import timezone


def fill_contract_accept(apps, schema_editor):
    agent_model = apps.get_model('clients', 'Agent')
    agent_model.objects.filter(
        created__lte=timezone.make_aware(datetime(year=2020, month=5, day=1))).update(
        accept_contract=True,
        accept_contract_date=timezone.make_aware(datetime(year=2020, month=4, day=30))
    )


class Migration(migrations.Migration):
    dependencies = [
        ('clients', '0037_auto_20200430_1334'),
    ]

    operations = [
        migrations.RunPython(fill_contract_accept)
    ]