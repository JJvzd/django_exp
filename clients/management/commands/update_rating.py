from django.core.management import BaseCommand

from clients.models import Bank, BankRating
from settings.configs.banks import BankCode

RATING_CLASSES = {
    (
        BankCode.CODE_SPB_BANK,
        'bank_guarantee.bank_integrations.spb_bank.bank_rating.BankRating'
    ),
    # банк рейтинг по умолчанию
    (
        'null_bank',
        'bank_guarantee.bank_integrations.spb_bank.bank_rating.BankRating'
    )
}


class Command(BaseCommand):
    help = 'Установка рейтингов банков'

    def handle(self, *args, **options):

        for r in RATING_CLASSES:
            bank_code, rating_class = r
            if bank_code == 'null_bank':
                BankRating.objects.update_or_create(
                    credit_organization=None,
                    defaults=dict(rating_class=rating_class, active=True)
                )
                continue
            bank = Bank.objects.filter(code=bank_code).first()
            if bank_code and not bank:
                print(f'{bank_code} - Нет банка')
                continue
            BankRating.objects.update_or_create(
                credit_organization=bank,
                defaults=dict(rating_class=rating_class,
                              active=True)
            )
