# Generated by Django 2.1.7 on 2019-10-10 14:18

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0008_remove_requestdocument_created'),
    ]

    operations = [
        migrations.AddField(
            model_name='requestdocument',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
