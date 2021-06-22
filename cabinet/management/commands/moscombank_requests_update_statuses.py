from django.core.management import BaseCommand
from django.utils import timezone

from bank_guarantee.models import ExternalRequest
from bank_guarantee.bank_integrations.moscombank.bank_api.base import (
    MoscombankSendRequest
)
from clients.models import BankCode
from common.helpers import get_logger

logger = get_logger()


class Command(BaseCommand):
    help = 'Обновление статусов заявок в Москомбанке'

    def handle(self, *args, **options):
        from_date = timezone.datetime.strptime('10.07.2020', '%d.%m.%Y')
        external_requests = ExternalRequest.objects.filter(
            request__bank__code=BankCode.CODE_MOSCOMBANK
        )
        external_requests = external_requests.filter(
            request__created_date__gte=from_date
        )
        bank_api = MoscombankSendRequest()
        for external_request in external_requests:
            try:
                bank_api.update_status(external_request)
            except Exception as error:
                logger.error(str(error))
