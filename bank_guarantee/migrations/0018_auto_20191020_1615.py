# Generated by Django 2.1.7 on 2019-10-20 13:15

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0017_auto_20191020_1517'),
    ]

    operations = [
        migrations.AlterField(
            model_name='discuss',
            name='must_read',
            field=models.ManyToManyField(blank=True, to=settings.AUTH_USER_MODEL),
        ),
    ]
