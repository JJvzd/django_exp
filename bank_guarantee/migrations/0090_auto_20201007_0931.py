# Generated by Django 2.1.7 on 2020-10-07 06:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0089_auto_20201006_1110'),
    ]

    operations = [
        migrations.AlterField(
            model_name='request',
            name='tmp_manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='request_managers', to=settings.AUTH_USER_MODEL, verbose_name='Временный менеджер'),
        ),
    ]
