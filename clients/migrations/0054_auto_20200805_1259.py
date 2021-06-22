# Generated by Django 2.1.7 on 2020-08-05 09:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0053_auto_20200729_0958'),
    ]

    operations = [
        migrations.AddField(
            model_name='agent',
            name='confirmed_documents',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='agentdocument',
            name='comment',
            field=models.CharField(blank=True, default=None, max_length=1000, null=True),
        ),
    ]
