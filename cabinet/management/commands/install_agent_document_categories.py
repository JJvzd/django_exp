from django.core.management import BaseCommand

from clients.models import AgentDocumentCategory


class Command(BaseCommand):
    help = 'Ининцализация документов агента'

    def handle(self, *args, **options):
        data = [
            {
                'name': 'Согласие на обработку персональных данных.',
                'for_physical_person': True,
                'for_individual_entrepreneur': True,
                'for_organization': True,
                'type': 'doc_ConfirmPersonalData',
            },
            {
                'name': 'Устав',
                'for_organization': True,
                'type': 'doc_Charter',
            },
            {
                'name': 'Копия паспорта',
                'for_individual_entrepreneur': True,
                'for_physical_person': True,
                'type': 'doc_Passport',
            },
            {
                'name': 'Скан свидетельства ИНН',
                'for_individual_entrepreneur': True,
                'for_organization': True,
                'for_physical_person': True,
                'type': 'doc_ScanINN',
            },
            {
                'name': 'Скан свидетельства ОГРН.',
                'for_individual_entrepreneur': True,
                'for_organization': True,
                'type': 'doc_ScanOGRN',
            },
            {
                'name': 'Решение о назначение или приказ о заключение крупных сделок',
                'for_organization': True,
                'type': 'doc_BigDeal',
            },
            {
                'name': 'Документ, подтверждающий применение режима налогообложения',
                'for_individual_entrepreneur': True,
                'for_organization': True,
                'type': 'doc_ConfirmTax',
            },
            {
                'name': 'Документ, подтверждающий применение режима налогообложения',
                'for_individual_entrepreneur': True,
                'for_organization': True,
                'type': 'doc_ConfirmTax',
            },
            {
                'name': 'Карточка компании.',
                'for_individual_entrepreneur': True,
                'for_organization': True,
                'for_physical_person': True,
                'type': 'doc_CompanyInfo',
            },
            {
                'name': 'Договор ТХ для ознакомления.',
                'for_individual_entrepreneur': True,
                'for_organization': True,
                'for_physical_person': True,
                'auto_generate': True,
                'type': 'doc_ContractExample',
            },
            {
                'name': 'Договор ТХ',
                'for_individual_entrepreneur': True,
                'for_organization': True,
                'for_physical_person': True,
                'auto_generate': True,
                'type': 'doc_Contract',
            },
        ]
        for (order, params) in enumerate(data):
            AgentDocumentCategory.objects.update_or_create(
                type=params.pop('type'),
                defaults=dict(order=order, **params),
            )
