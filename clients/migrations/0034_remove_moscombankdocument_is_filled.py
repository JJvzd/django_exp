# Generated by Django 2.1.7 on 2020-03-27 08:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0033_auto_20200327_1116'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='moscombankdocument',
            name='is_filled',
        ),
    ]
