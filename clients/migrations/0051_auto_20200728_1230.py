# Generated by Django 2.1.7 on 2020-07-28 09:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0050_agentverificationcomments_legal_address_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentverificationcomments',
            name='about_us_comment',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AddField(
            model_name='agentverificationcomments',
            name='experience_comment',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AddField(
            model_name='agentverificationcomments',
            name='how_clients_comment',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
        migrations.AddField(
            model_name='agentverificationcomments',
            name='priority_conditions_comment',
            field=models.CharField(blank=True, max_length=1000, null=True),
        ),
    ]
