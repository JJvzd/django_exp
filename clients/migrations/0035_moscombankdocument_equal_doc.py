# Generated by Django 2.1.7 on 2020-04-09 12:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0034_remove_moscombankdocument_is_filled'),
    ]

    operations = [
        migrations.AddField(
            model_name='moscombankdocument',
            name='equal_doc',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='clients.MoscombankDocument'),
        ),
    ]
