# Generated by Django 2.1.7 on 2020-08-11 07:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0057_auto_20200807_1128'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agent',
            name='confirmed_documents',
            field=models.IntegerField(default=2),
        ),
    ]
