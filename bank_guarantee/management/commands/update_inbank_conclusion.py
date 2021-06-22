from django.core.management import BaseCommand

from bank_guarantee.models import RequestPrintForm
from cabinet.base_logic.printing_forms.base import PrintForm
from clients.models import Bank
from settings.configs.banks import BankCode


class Command(BaseCommand):
    help = 'Обновление заключения ИНБАНК'

    def handle(self, *args, **options):
        bank = Bank.objects.filter(code=BankCode.CODE_INBANK).first()
        if bank:
            print_form = RequestPrintForm.objects.filter(
                bank=bank, filename='inbank_conclusion'
            ).first()
            if print_form:
                print_form.type = PrintForm.TYPE_INBANK_CONCLUSION
                print_form.save()
