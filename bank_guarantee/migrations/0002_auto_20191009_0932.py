# Generated by Django 2.1.7 on 2019-10-09 06:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('clients', '0001_initial'),
        ('bank_guarantee', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='requestprintform',
            name='bank',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='clients.Bank'),
        ),
        migrations.AddField(
            model_name='requesthistory',
            name='request',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bank_guarantee.Request'),
        ),
        migrations.AddField(
            model_name='requesthistory',
            name='status',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='bank_guarantee.RequestStatus'),
        ),
    ]
