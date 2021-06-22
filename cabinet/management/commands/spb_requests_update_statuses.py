from django.core.management import BaseCommand

from bank_guarantee.models import ExternalRequest
from bank_guarantee.bank_integrations.spb_bank.tasks import check_status_from_bank
from clients.models import BankCode


class Command(BaseCommand):
    help = 'Обновление статусов заявок в СПб'

    def handle(self, *args, **options):
        external_requests = ExternalRequest.objects.filter(
            bank__code=BankCode.CODE_SPB_BANK
        )
        for external_request in external_requests:
            print(external_request.external_id)
            check_status_from_bank(external_request)
