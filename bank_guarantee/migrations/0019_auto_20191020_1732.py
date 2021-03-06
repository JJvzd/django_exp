# Generated by Django 2.1.7 on 2019-10-20 14:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0018_auto_20191020_1615'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='discuss',
            name='must_read',
        ),
        migrations.AlterField(
            model_name='message',
            name='agent_read',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='message',
            name='bank_read',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='message',
            name='client_read',
            field=models.BooleanField(default=False),
        ),
    ]
