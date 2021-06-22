from django.core.management import BaseCommand

from bank_guarantee.models import Request
from cabinet.base_logic.scoring.functions import FieldEqualScoring


class Command(BaseCommand):
    help = 'Тест оповещения об ошибке скоринга'

    def handle(self, *args, **options):
        request = Request(required_amount=1000)
        FieldEqualScoring(None, request, {
            "error_message": "Ошибка",
            "field": "request.required_amount",
            "operation": "!=",
            "value": 'gdf'
        }).get_result()
