import datetime
import os

from django.conf import settings

from bank_guarantee.bank_integrations.spb_bank.helpers import (
    get_number_changed_beneficiary_last_year
)


def test_get_number_changed_beneficiary_last_year(rm):
    response_path = 'clients/tests/spb_bank/files/zachestniy_card_response.json'
    rm.register_uri(
        'GET',
        '//zachestnyibiznesapi.ru/paid/data/card',
        text=open(os.path.join(settings.BASE_DIR, response_path)).read()
    )
    count = get_number_changed_beneficiary_last_year(
        5010050218,
        now=datetime.datetime(year=2020, month=7, day=29)
    )
    assert count == 1


# def test_get_principal_has_share_in_stop_factors_companies():
#     with requests_mock.mock() as m:
#         url = 'https://zachestnyibiznesapi.ru/paid/data/search?string=est_1117746043381+7710881860' \
#               '&api_key=ofRq2wwSCkW16Kp36JbdMzfSo7-9PCX5&_format=json'
#         response_path = 'clients/tests/spb_bank/files/zachestniy_search_response.json'
#         m.get(url, text=open(os.path.join(settings.BASE_DIR, response_path)).read())
#
#         count = get_principal_has_share_in_stop_factors_companies(7710881860, 1117746043381)
#         assert count == 1
