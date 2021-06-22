import os

from django.conf import settings

from bank_guarantee.bank_integrations.spb_bank.print_form_helper import SPBHelper
from bank_guarantee.models import Request
from clients.models import Client
from questionnaire.models import Profile


def test_contracts_request(rm):
    rm.register_uri(
        'GET', '//parsers.tenderhelp.ru/api/zakupki/contracts_44fz/',
        text=open(os.path.join(
            settings.BASE_DIR,
            'bank_guarantee/bank_integrations/spb_bank/tests/files/',
            'contracts_2460083169.json'
        ), 'r').read()
    )
    rm.register_uri(
        'GET', '//parsers.tenderhelp.ru/api/zakupki/contracts_223fz/',
        text=open(os.path.join(
            settings.BASE_DIR,
            'bank_guarantee/bank_integrations/spb_bank/tests/files/',
            'contracts_2460083169_223fz.json'
        ), 'r').read()
    )
    inn = '2460083169'
    helper = SPBHelper(
        request=Request(client=Client(inn=inn, profile=Profile(reg_inn=inn))),
        bank=None
    )
    assert helper.customer_count == 46
