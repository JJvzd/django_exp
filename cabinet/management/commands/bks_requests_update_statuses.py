from django.core.management import BaseCommand

from bank_guarantee.bank_integrations.bks_bank.bank_api import SendRequest
from bank_guarantee.models import ExternalRequest

from clients.models import BankCode


class Command(BaseCommand):
    help = 'Обновление статусов заявок в БКС'

    def handle(self, *args, **options):
        external_requests = ExternalRequest.objects.filter(
            bank__code=BankCode.CODE_BKS_BANK
        )
        bank_api = SendRequest()
        for external_request in external_requests:
            bank_api.update_status(external_request)
