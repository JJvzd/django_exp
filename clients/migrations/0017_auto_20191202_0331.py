# Generated by Django 2.1.7 on 2019-12-02 00:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0016_templatechatbank'),
    ]

    operations = [
        migrations.AlterField(
            model_name='templatechatbank',
            name='template',
            field=models.TextField(),
        ),
    ]
