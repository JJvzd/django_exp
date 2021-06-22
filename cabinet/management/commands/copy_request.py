from django.core.management import BaseCommand

from bank_guarantee.helpers.copy_request import CopyRequest


class Command(BaseCommand):
    help = 'Копирование заявки'

    def add_arguments(self, parser):
        parser.add_argument('request_id', nargs='+', type=int)

    def handle(self, *args, **options):
        for i in options['request_id']:
            helper = CopyRequest(i)
            helper.copy_request()
