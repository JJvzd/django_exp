# Generated by Django 2.1.7 on 2020-10-06 08:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bank_guarantee', '0087_merge_20200925_1053'),
    ]

    operations = [
        migrations.AddField(
            model_name='request',
            name='manager',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='request_managers', to=settings.AUTH_USER_MODEL, verbose_name='Временный менеджер'),
        ),
    ]
