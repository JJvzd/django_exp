from django.core.management import BaseCommand

from bank_guarantee.models import RequestPrintForm, OfferPrintForm
from clients.models import Bank


class Command(BaseCommand):
    """ команда в процессе разработки """
    help = 'Экспортирует конфиг банка по коду банка'

    def add_arguments(self, parser):
        parser.add_argument('bank_code', nargs='?', type=str, default=0)

    def pack_users(self, bank):
        return [
            {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'middle_name': user.middle_name,
                'email': user.email,
                'username': user.username,
                'is_active': user.is_active,
                'roles': [role.name for role in user.roles.all()]
            }
            for user in bank.user_set.all()
        ]

    def pack_print_forms(self, bank):
        result = []
        for pf in RequestPrintForm.objects.all():
            if bank in pf.banks.all():
                result.append({
                    'name': pf.name,
                    'download_name': pf.download_name,
                    'type': pf.type,
                    'filename': pf.filename,
                    'active': pf.active,
                    'readonly': pf.readonly,
                    'in_conclusions': pf.in_conclusions,
                    'roles': pf.roles,
                })
        return result

    def pack_offer_categories(self, bank):
        return [
            {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'middle_name': user.middle_name,
                'email': user.email,
                'username': user.username,
                'is_active': user.is_active,
                'roles': [role.name for role in user.roles.all()]
            }
            for user in bank.user_set.all()
        ]

    def pack_offer_print_forms(self, bank):
        return [{
            'name': pf.name,
            'filename': pf.filename,
            'type': pf.type,
            'download_name': pf.download_name,
            'active': pf.active,
        } for pf in OfferPrintForm.objects.all()]

    def handle(self, *args, **options):
        bank_code = options['bank_code'] or None
        print(bank_code)
        bank = Bank.objects.get(code=bank_code)
        data = {
            'full_name': bank.full_name,
            'short_name': bank.short_name,
            'inn': bank.inn,
            'ogrn': bank.ogrn,
            'settings': {
                '': ''
            },
            'users': self.pack_users(bank),
            'print_forms': self.pack_print_forms(bank),
            'offer_categories': self.pack_offer_categories(bank),
            'offer_print_forms': self.pack_offer_print_forms(bank)
        }
        print(data)
