# Generated by Django 2.1.7 on 2020-11-13 06:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0106_auto_20201112_1010'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='sign_url',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='Ссылка на подпись'),
        ),
    ]