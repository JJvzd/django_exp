# Generated by Django 2.1.7 on 2020-06-15 15:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0044_banksigner'),
    ]

    operations = [
        migrations.CreateModel(
            name='RequestRejectionReasonTemplate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, default='', max_length=100, verbose_name='Название шаблона')),
                ('reason', models.CharField(blank=True, max_length=300, null=True, verbose_name='Причина отклонения заявки банком')),
                ('bank', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='clients.Bank')),
            ],
            options={
                'verbose_name': 'Шаблон причины отклонения заявки банком',
                'verbose_name_plural': 'Шаблоны причин отклонения заявок банками',
            },
        ),
    ]
