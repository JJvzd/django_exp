# Generated by Django 2.1.7 on 2020-09-01 19:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0084_merge_20200901_1256'),
    ]

    operations = [
        migrations.AlterField(
            model_name='requestedcategory',
            name='name',
            field=models.CharField(max_length=300, verbose_name='Наименование запрашиваемого документа'),
        ),
    ]
