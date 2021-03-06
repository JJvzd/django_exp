# Generated by Django 2.1.7 on 2020-08-17 09:53

from django.db import migrations
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0095_auto_20200817_1056'),
    ]

    operations = [
        migrations.AddField(
            model_name='agentinstructionsdocuments',
            name='roles',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('bank', 'Банк'), ('general_bank', 'Генеральный банк'), ('agent', 'Агент'), ('general_agent', 'Генеральный агент'), ('super_agent', 'Супер агент'), ('head_agent', 'Глава агент'), ('client', 'Клиент'), ('manager', 'manager'), ('mfo', 'оператор МФО'), ('verifier', 'Верификатор')], default='', max_length=200, verbose_name='Видимо для ролей'),
        ),
    ]
