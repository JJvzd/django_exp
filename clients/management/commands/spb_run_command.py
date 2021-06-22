from django.core.management import BaseCommand

from bank_guarantee.models import Request
from bank_guarantee.bank_integrations.spb_bank.tasks import send_offer_ready


class Command(BaseCommand):
    help = 'Загружает заявки из старой базы'

    def add_arguments(self, parser):
        parser.add_argument('request_id', nargs='?', type=int, default=0)
        parser.add_argument('command', choices=['send_offer_ready'], default=None)

    def handle(self, *args, **options):
        request_id = options['request_id'] or None
        command = options['command'] or None
        if not (request_id and command):
            return

        request = Request.objects.get(id=request_id)
        if command == 'send_offer_ready':
            send_offer_ready(request=request)
