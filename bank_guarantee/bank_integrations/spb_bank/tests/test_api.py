import datetime
import os

import pytest
from django.conf import settings

from bank_guarantee.bank_integrations.spb_bank.api import SPBApi
from bank_guarantee.models import Offer, Request
from clients.models import Client
from utils.functions_for_tests import create_request


@pytest.mark.django_db
def test_offer_ready_ur_org(initial_data_db, rm):
    response_path = 'clients/tests/spb_bank/files/zachestniy_card_response.json'
    rm.register_uri(
        'GET',
        '//zachestnyibiznesapi.ru/paid/data/card',
        text=open(os.path.join(settings.BASE_DIR, response_path)).read()
    )
    rm.get(
        'http://openapi.clearspending.ru/restapi/v3/contracts/search/'
        '?supplierinn=5010050218',
        text='Data not found', status_code=404)

    request = create_request(
        request=Request(
            interval_from=datetime.date(day=1, month=1, year=2010),
            interval_to=datetime.date(day=1, month=1, year=2015)),
        client=Client(inn='5010050218')
    )
    request.client.profile.reg_state_date = datetime.date(day=1, month=1,
                                                          year=2010)
    request.client.profile.profilepartnerindividual_set.create(
        is_general_director=True,
        share=10,
        first_name='gen',
        last_name='dir',
        middle_name='ector'
    )
    request.client.profile.profilepartnerlegalentities_set.create(
        share=10,
        name='ur1',
    )
    Offer.objects.create(
        request=request,
        commission_bank=1000,
        amount=10000,
    )
    api = SPBApi()

    data = api.offer_ready_data(request)
    assert data == {
        'agentId': 'TH',
        'amount': 10000.0,
        'commissionAmount': 1000.0,
        'commissionPercentRate': 0.1,
        'contractDate': '0000-00-00',
        'contractDocBase64': 'UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==',
        'contractNumber': None,
        'decisionProtocolDate': '0000-00-00',
        'decisionProtocolNumber': '0',
        'endDate': '2015-01-01',
        'federalLaw': 'FZ44',
        'guaranteePurpose': 'EXEC_CONTRACT',
        'obligationsStartDate': '2010-01-01',
        'principalParams': {
            'bankAccounts': [],
            'licences': [],
            'managementMembershipInfo': [
                {
                    'members': [
                        {'displayName': 'dir gen ector',
                         'identityDocument': {
                             'identityDocumentTypeRefId': 'passportRF',
                             'issuedDate': '0000-00-00',
                             'issuingAuthority': None,
                             'number': None,
                             'series': None,
                             'subCode': None
                         },
                         'inn': '',
                         'position': None,
                         'share': 10.0
                         }
                    ],
                    'membershipType': 'Генеральный директор'
                }, {
                    'members': [
                        {
                            'displayName': 'ur1',
                            'inn': '',
                            'share': 10.0
                        }
                    ],
                    'membershipType': 'Компании-учредители'
                }
            ], 'netAssetsAmount': 0,
            'netAssetsReportDate': datetime.datetime.now().strftime('%Y-%m-%d'),
            'rating': 'D',
            'relatedPersons': [
                {
                    'addresses': [
                        {'addressTypeCode': '100000000',
                         'fullAddress': None
                         }
                    ],
                    'birthDate': '0000-00-00',
                    'birthPlace': None,
                    'displayName': 'dir gen ector',
                    'firstName': 'gen',
                    'identityDocument': {
                        'identityDocumentTypeRefId': 'passportRF',
                        'issuedDate': '0000-00-00',
                        'issuingAuthority': None,
                        'number': None,
                        'series': None,
                        'subCode': None}, 'inn': '',
                    'lastName': 'dir',
                    'secondName': 'ector',
                    'sex': 'FEMALE',
                    'type': 'principalBeneficiary'
                }
            ],
            'telephone1': '',
            'valuationDate': datetime.datetime.now().strftime('%Y-%m-%d'),
        }, 'startDate': '2010-01-01'
    }


@pytest.mark.django_db
def test_offer_ready_ip_org(initial_data_db, rm):
    response_path = 'clients/tests/spb_bank/files/zachestniy_card_response.json'
    rm.register_uri(
        'GET',
        '//zachestnyibiznesapi.ru/paid/data/card',
        text=open(os.path.join(settings.BASE_DIR, response_path)).read()
    )
    rm.get(
        'http://openapi.clearspending.ru/restapi/v3/contracts/search/'
        '?supplierinn=780150302931',
        text='Data not found', status_code=404
    )

    request = create_request(
        request=Request(
            interval_from=datetime.date(day=1, month=1, year=2010),
            interval_to=datetime.date(day=1, month=1, year=2015)),
        client=Client(inn='780150302931')
    )
    request.client.profile.reg_state_date = datetime.date(day=1, month=1,
                                                          year=2010)
    request.client.profile.profilepartnerindividual_set.create(
        is_general_director=True,
        share=10,
        first_name='gen',
        last_name='dir',
        middle_name='ector'
    )
    Offer.objects.create(
        request=request,
        commission_bank=1000,
        amount=10000,
    )
    api = SPBApi()

    data = api.offer_ready_data(request)
    assert data == {
        'agentId': 'TH',
        'amount': 10000.0,
        'commissionAmount': 1000.0,
        'commissionPercentRate': 0.1,
        'contractDate': '0000-00-00',
        'contractDocBase64': 'UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==',
        'contractNumber': None, 'decisionProtocolDate': '0000-00-00',
        'decisionProtocolNumber': '0',
        'endDate': '2015-01-01',
        'federalLaw': 'FZ44',
        'guaranteePurpose': 'EXEC_CONTRACT',
        'obligationsStartDate': '2010-01-01',
        'principalParams': {
            'bankAccounts': [], 'licences': [],
            'managementMembershipInfo': [],
            'netAssetsAmount': 0,
            'netAssetsReportDate': str(datetime.date.today()), 'rating': 'D',
            'relatedPersons': [
                {
                    'addresses': [
                        {'addressTypeCode': '100000000',
                         'fullAddress': None
                         }
                    ],
                    'birthDate': '0000-00-00',
                    'birthPlace': None,
                    'displayName': 'dir gen ector',
                    'firstName': 'gen',
                    'identityDocument': {
                        'identityDocumentTypeRefId': 'passportRF',
                        'issuedDate': '0000-00-00',
                        'issuingAuthority': None,
                        'number': None,
                        'series': None,
                        'subCode': None}, 'inn': '',
                    'lastName': 'dir',
                    'secondName': 'ector',
                    'sex': 'FEMALE',
                    'type': 'entrepreneur'
                }
            ],
            'telephone1': '', 'valuationDate': str(datetime.date.today())
        },
        'startDate': '2010-01-01'
    }
