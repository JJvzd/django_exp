from django.core.management import BaseCommand

from bank_guarantee.models import RequestStatus
from settings.settings import DEBUG


class Command(BaseCommand):
    help = 'Ининцализация документов агента'

    def handle(self, *args, **options):
        if DEBUG:
            data = [
                {
                    'name': 'Агентский черновик',
                    'color': '#cccccc',
                },
                {
                    'name': 'Одобрено банком',
                    'color': '#dda8dd',
                },
                {
                    'name': 'Заявка на подписании у клиента',
                    'color': '#f6acaa',
                },
                {
                    'name': 'Банк выстовил предложение',
                    'color': '#f6f672',
                },
                {
                    'name': 'Заявка на рассмотрении в банке',
                    'color': '#99cad7',
                },
                {
                    'name': 'Предлжение принято, но не оплачено',
                    'color': '#a4d174',
                },
                {
                    'name': 'Запрос',
                    'color': '#f0c6a4',
                },
                {
                    'name': 'Подготавливается банковская гарантия',
                    'color': '#bbce95',
                },
                {
                    'name': 'Запрос обработан',
                    'color': '#896c9f',
                },
                {
                    'name': 'Банковская гарантия выдана',
                    'color': '#3ed482',
                },
            ]
            for element in data:
                RequestStatus.objects.create(**element)
            for element in RequestStatus.objects.all():
                element.code = element.id
                element.save()
