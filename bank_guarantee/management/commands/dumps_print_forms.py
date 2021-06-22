import json

from django.core.management import BaseCommand

from bank_guarantee.models import RequestPrintForm


class Command(BaseCommand):
    help = 'Обновление шаблонов печатных форм'

    def handle(self, *args, **options):
        print(json.dumps([pf.export_as_json() for pf in RequestPrintForm.objects.all()]))
