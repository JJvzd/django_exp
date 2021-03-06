# Generated by Django 2.1.7 on 2020-04-29 12:27

from django.db import migrations


def add_deny_by_verifier_status(apps, schema_editor):
    request_status = apps.get_model('bank_guarantee', 'RequestStatus')
    request_status.objects.get_or_create(code='deny_by_verifier', defaults=dict(
        name='Отклонено верификатором'
    ))


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0053_merge_20200424_1214'),
    ]

    operations = [
        migrations.RunPython(add_deny_by_verifier_status)
    ]
