import random

from django.core.management import BaseCommand

from cabinet.constants.constants import Target
from cabinet.models import WorkRule
from clients.models import Bank
from settings.configs.banks import BankCode


class Command(BaseCommand):
    help = 'Тестовые данные для WorkRule'

    def handle(self, *args, **options):
        for bank, code in BankCode.CHOICES:
            if bank in ['rus_micro_finance', 'simple_finance']:
                continue
            print(bank)
            for target, name in Target.CHOICES:
                WorkRule.objects.create(
                    bank=Bank.objects.filter(code=bank).first(),
                    text='$TEST$',
                    bg_type=target,
                    commission=float(random.randint(1, 10)),
                    commission_on_excess=float(random.randint(1, 40)),
                )
