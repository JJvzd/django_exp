from django.core.management import BaseCommand

from bank_guarantee.models import Request
from clients.models import Bank


class Command(BaseCommand):
    help = 'Обновление статусов интеграционных банков'

    def handle(self, *args, **options):
        for bank in Bank.objects.filter(
            settings__date_from_update_status_via_integration__isnull=False
        ):
            for request in Request.objects.filter(
                bank=bank,
                created_date__gte=bank.settings.date_from_update_status_via_integration,
                externalrequest__isnull=False
            ):
                print(request)
                request.bank_integration.check_and_update_status(request)

