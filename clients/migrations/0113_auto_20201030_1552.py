# Generated by Django 2.2 on 2020-10-30 12:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0112_auto_20201030_1546'),
    ]

    operations = [
        migrations.RenameField(
            model_name='agentcontractoffer',
            old_name='sign_date',
            new_name='accept_date',
        ),
    ]
