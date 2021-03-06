# Generated by Django 2.1.7 on 2019-10-09 06:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clients', '0001_initial'),
        ('files', '0001_initial'),
        ('cabinet', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='workrule',
            name='bank',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='clients.Bank'),
        ),
        migrations.AddField(
            model_name='signhistory',
            name='certificate',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='cabinet.Certificate'),
        ),
        migrations.AddField(
            model_name='signhistory',
            name='file',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='files.BaseFile'),
        ),
    ]
