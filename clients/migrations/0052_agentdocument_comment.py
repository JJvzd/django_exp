# Generated by Django 2.1.7 on 2020-07-29 06:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0051_auto_20200728_1230'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentdocument',
            name='comment',
            field=models.CharField(default='', max_length=1000),
        ),
    ]
