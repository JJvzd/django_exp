# Generated by Django 2.1.7 on 2019-10-20 12:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0016_discuss_must_read'),
    ]

    operations = [
        migrations.AlterField(
            model_name='message',
            name='agent_read',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='message',
            name='bank_read',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='message',
            name='client_read',
            field=models.BooleanField(default=True),
        ),
    ]
