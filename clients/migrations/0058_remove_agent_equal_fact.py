# Generated by Django 2.1.7 on 2020-07-02 07:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0057_auto_20200702_1001'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='agent',
            name='equal_fact',
        ),
    ]
