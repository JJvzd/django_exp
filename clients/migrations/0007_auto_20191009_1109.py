# Generated by Django 2.1.7 on 2019-10-09 08:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0006_auto_20191009_1104'),
    ]

    operations = [
        migrations.AlterField(
            model_name='company',
            name='full_name',
            field=models.CharField(blank=True, max_length=512, null=True),
        ),
    ]
