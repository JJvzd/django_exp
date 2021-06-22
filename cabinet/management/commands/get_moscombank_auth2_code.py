import requests
from django.core.management import BaseCommand

from bank_guarantee.bank_integrations.moscombank.bank_api.api import MoscombankApi


class Command(BaseCommand):
    help = 'Получение кода авторизации для москомбанка'

    def handle(self, *args, **options):
        api = MoscombankApi(adapter=None)
        api.get_token()
        response = requests.get(
            'https://tenderhelp.ru/async/get_moscom_oauth2', verify=False
        ).json()
        self.stdout.write(response)
