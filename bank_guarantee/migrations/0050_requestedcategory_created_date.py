# Generated by Django 2.1.7 on 2020-04-20 12:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bank_guarantee', '0049_merge_20200420_1443'),
    ]

    operations = [
        migrations.AddField(
            model_name='requestedcategory',
            name='created_date',
            field=models.DateTimeField(auto_now=True),
        ),
    ]