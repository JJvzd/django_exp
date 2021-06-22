import os

import requests_mock

from bank_guarantee.models import Request
from bank_guarantee.bank_integrations.spb_bank.print_form_helper import SPBHelper
from clients.models import Client
from questionnaire.models import Profile


def test_spb_helper_last_3_year_contracts():
    with requests_mock.mock() as m:
        path = os.path.join(
            os.path.dirname(__file__), 'files/contracts_7734240231.json'
        )
        response_data = open(path, 'r').read()
        m.get(
            'http://openapi.clearspending.ru/restapi/v3/contracts/search/'
            '?supplierinn=7734240231',
            text=response_data
        )
        helper = SPBHelper(
            request=Request(client=Client(
                inn='7734240231', profile=Profile(reg_inn='7734240231'))
            ),
            bank=None
        )
        assert len(helper.last_3_year_contracts) == 0
