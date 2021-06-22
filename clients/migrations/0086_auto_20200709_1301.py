# Generated by Django 2.1.7 on 2020-07-09 10:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0085_merge_20200709_1301'),
    ]

    operations = [
        migrations.AlterField(
            model_name='agentdocumentcategory',
            name='help_text',
            field=models.TextField(blank=True, null=True, verbose_name='Всплывающая подсказка'),
        ),
        migrations.AlterField(
            model_name='agentprofile',
            name='experience',
            field=models.IntegerField(blank=True, max_length=15, null=True, verbose_name='Опыт работы агентом'),
        ),
        migrations.AlterField(
            model_name='mfo',
            name='code',
            field=models.CharField(choices=[('rus_micro_finance', 'rus_micro_finance'), ('simple_finance', 'simple_finance'), ('analiz_th', 'analiz_th')], max_length=20),
        ),
    ]