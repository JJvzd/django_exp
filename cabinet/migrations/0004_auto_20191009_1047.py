# Generated by Django 2.1.7 on 2019-10-09 07:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cabinet', '0003_signhistory_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='placementplace',
            name='name',
            field=models.CharField(max_length=250, verbose_name='Название площадки'),
        ),
    ]
