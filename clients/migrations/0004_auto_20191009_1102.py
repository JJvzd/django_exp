# Generated by Django 2.1.7 on 2019-10-09 08:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0003_auto_20191009_1058'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agentdocumentcategory',
            name='type',
            field=models.CharField(max_length=150, unique=True, verbose_name='Уникальный код'),
        ),
    ]