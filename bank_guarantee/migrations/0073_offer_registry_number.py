# Generated by Django 2.1.7 on 2020-07-10 07:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0072_auto_20200708_1721'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='registry_number',
            field=models.CharField(blank=True, max_length=250, null=True, verbose_name='Реестровый номер'),
        ),
    ]