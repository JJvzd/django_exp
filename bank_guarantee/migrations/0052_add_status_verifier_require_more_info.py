# Generated by Django 2.1.7 on 2020-04-22 14:34

from django.db import migrations

def add_new_status(apps, schema_editor):
    request_status = apps.get_model('bank_guarantee', 'RequestStatus')
    request_status.objects.get_or_create(code='verifier_require_more_info', defaults=dict(
        name='Доработка'
    ))

class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0051_add_verification_status'),
    ]

    operations = [
        migrations.RunPython(add_new_status)
    ]
