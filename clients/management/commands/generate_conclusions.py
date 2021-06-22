from django.core.management import BaseCommand

from conclusions_app.conclusions_logic import ConclusionsLogic
from clients.models import Client
from conclusions_app.settings import CONCLUSIONS


class Command(BaseCommand):
    help = 'Загружает заявки из старой базы'

    def add_arguments(self, parser):
        parser.add_argument('client_id', nargs='?', type=int, default=0)

    def handle(self, *args, **options):
        client_id = options['client_id'] or None
        if not client_id:
            return

        client = Client.objects.filter(id=client_id).first()
        self.stdout.write(self.style.SUCCESS(
            'Generate conclusions for client %s' % client.inn))

        for conclusion in CONCLUSIONS:
            result = ConclusionsLogic.generate_conclusion(
                client=client,
                conclusion=conclusion
            )
            ConclusionsLogic.save_conclusion(
                client=client,
                conclusion=conclusion,
                conclusion_result=result
            )
