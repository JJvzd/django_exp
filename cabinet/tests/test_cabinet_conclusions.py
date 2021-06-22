import os

import pytest
import requests_mock
from django.conf import settings

from cabinet.base_logic.conclusions.check_terror import CheckInTerroristsList
from clients.models import Client
from conclusions_app.conclusions.base import ConclusionResult
from conclusions_app.conclusions.common import GosContractsConclusion
from conclusions_app.conclusions_logic import ConclusionsLogic


@pytest.mark.parametrize("data,result", [
    ({'last_name': 'АРХАГОВ', 'first_name': 'РУСТАМЭЛО',
      'middle_name': 'РУСЛАНОВИЧ',
      'date_of_birth': '07.01.1966',
      'place_of_birth': 'Г. ГРОЗНЫЙ'}, 'NOT_FOUND'),
    ({'last_name': 'БАКАНАЕВ', 'first_name': 'РУСТАМ',
      'middle_name': 'РУСЛАНОВИЧ',
      'date_of_birth': '07.01.1966',
      'place_of_birth': 'Г. ГРОЗНЫЙ'}, 'FOUND_ONLY_FIO'),
    ({'last_name': 'НАКОНЕЧНЫЙ', 'first_name': 'ИГОРЬ',
      'middle_name': 'ЕВГЕНЬЕВИЧ',
      'date_of_birth': '07.01.1966',
      'place_of_birth': 'Г. ГРОЗНЫЙ'}, 'FOUND_PARTICAL'),
    ({'last_name': 'АЛЕКСЕЕВ', 'first_name': 'КИРИЛЛ',
      'middle_name': 'МИХАЙЛОВИЧ',
      'date_of_birth': '18.12.1999',
      'place_of_birth': 'Г. ЛИПЕЦК ЛИПЕЦКОЙ ОБЛАСТИ'}, 'FOUND'),
])
def test_check_terror_fl(data, result):
    helper = CheckInTerroristsList()
    with requests_mock.mock() as m:
        m.get('http://fedsfm.ru/documents/terrorists-catalog-portal-act',
              text=open(os.path.join(os.path.dirname(__file__),
                                     'files/terrorists_list.html'), 'r').read())

        assert helper.check(**data) == result


def test_get_contracts_count_common_variant():
    inn = '6670278073'
    kpp = '667001001'

    response = open(os.path.join(
        settings.BASE_DIR,
        'external_api/files/clearspending_response_web.html')
    ).read()
    with requests_mock.mock() as m:
        m.get(
            'https://clearspending.ru/supplier/inn=%s&kpp=%s' % (inn, kpp),
            text=response
        )

        assert ConclusionsLogic.generate_conclusion(
            client=Client(inn=inn, kpp=kpp),
            conclusion=GosContractsConclusion
        ) == ConclusionResult(
            result=True,
            other_data={
                'validation_result': 'Всего контрактов 61 на сумму 44 872 948 '
                                     'руб.<br>Контрактов 61 по Всего на сумму'
                                     ' 44 872 948 руб.<br>Контрактов 58  по  '
                                     '44/94-ФЗ на сумму 44 154 737  руб.<br>К'
                                     'онтрактов 3  по  223-ФЗ на сумму 718 21'
                                     '1  руб.'
            },
            file=None
        )
