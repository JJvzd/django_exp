# Generated by Django 2.1.7 on 2020-10-27 14:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0110_auto_20201020_1154'),
    ]

    operations = [
        migrations.RenameField(
            model_name='agent',
            old_name='ruch_correct',
            new_name='ruchnaya_korrect',
        ),
        migrations.RemoveField(
            model_name='agentrewards',
            name='number',
        ),
        migrations.RemoveField(
            model_name='agentrewards',
            name='procent',
        ),
        migrations.AddField(
            model_name='agentrewards',
            name='number_requests',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=30, verbose_name='Количество выданных заявок'),
        ),
        migrations.AddField(
            model_name='agentrewards',
            name='percent',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=30, verbose_name='Проценты'),
        ),
    ]
