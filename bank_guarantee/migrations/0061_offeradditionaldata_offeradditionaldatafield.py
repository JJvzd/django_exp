# Generated by Django 2.1.7 on 2020-05-27 14:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0043_fill_managers'),
        ('bank_guarantee', '0060_fill_new_pf_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='OfferAdditionalData',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field', models.CharField(max_length=100)),
                ('value', models.CharField(max_length=1000)),
                ('offer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bank_guarantee.Offer')),
            ],
        ),
        migrations.CreateModel(
            name='OfferAdditionalDataField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(max_length=100)),
                ('default_value', models.CharField(max_length=1000)),
                ('config', models.TextField(default='{}')),
                ('banks', models.ManyToManyField(related_name='offer_additional_fields', to='clients.Bank')),
            ],
        ),
    ]
