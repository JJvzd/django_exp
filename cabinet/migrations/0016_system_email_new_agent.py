# Generated by Django 2.1.7 on 2020-03-30 10:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cabinet', '0015_auto_20200327_1322'),
    ]

    operations = [
        migrations.AddField(
            model_name='system',
            name='email_new_agent',
            field=models.CharField(blank=True, default='', max_length=2000),
        ),
    ]
