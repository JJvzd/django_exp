# Generated by Django 2.1.7 on 2020-07-23 06:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0044_banksigner'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mfo',
            name='code',
            field=models.CharField(choices=[('rus_micro_finance', 'rus_micro_finance'), ('simple_finance', 'simple_finance'), ('analiz_th', 'analiz_th')], max_length=20),
        ),
    ]
