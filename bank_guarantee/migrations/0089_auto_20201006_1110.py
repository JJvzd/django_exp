# Generated by Django 2.1.7 on 2020-10-06 08:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0088_request_manager'),
    ]

    operations = [
        migrations.RenameField(
            model_name='request',
            old_name='manager',
            new_name='tmp_manager',
        ),
    ]
