# Generated by Django 2.1.7 on 2020-08-14 07:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0064_remove_agent_confirmed_documents'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='confirmed_documents',
            field=models.IntegerField(default=0),
        ),
    ]
