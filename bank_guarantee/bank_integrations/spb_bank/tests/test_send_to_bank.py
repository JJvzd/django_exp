import datetime

import pytest

from bank_guarantee.actions import SendToBankAction
from bank_guarantee.models import RequestStatus, ExternalRequest
from bank_guarantee.send_to_bank_logic.send_to_bank_handler import get_send_adapter_class
from base_request.tasks import task_send_to_bank_from_verification
from clients.models import Bank, Client
from questionnaire.models import ProfilePartnerIndividual, Profile
from settings.configs.banks import BankCode
from utils.functions_for_tests import create_request

pytestmark = pytest.mark.base_workflow

@pytest.fixture
def mocked_requests(rm):
    rm.register_uri(
        'GET',
        '//openapi.clearspending.ru/restapi/v3/contracts/search/',
        text='Data not found'
    )
    rm.register_uri('POST', '//egrul.nalog.ru/', text='', status_code=500)
    rm.register_uri(
        'GET', '//service.nalog.ru/static/captcha.html',
        text='', status_code=500
    )
    rm.register_uri(
        'GET',
        '//fedsfm.ru/documents/terrorists-catalog-portal-act',
        text='', status_code=500
    )
    rm.register_uri(
        'POST',
        '//chat.tenderhelp.ru/hooks/5AEkYXYG98iysjvKw/dKyFrDsPZCJTv6g9GgE9BHxhfYEK6Bsr49Pe33im2eGDdxdT',
        text='', status_code=200
    )
    rm.register_uri(
        'GET',
        '//zachestnyibiznesapi.ru/paid/data/card',
        text='{"status":"223","message":"По данному ИНН не найдено информации."}',
        status_code=200
    )
    return rm


@pytest.mark.django_db
def test_send_to_bank_fail(initial_data_db, mocked_requests):
    mocked_requests.register_uri(
        'POST',
        'http://127.0.0.1:8998/counterparty/order/',
        text='{"timestamp": "2020-09-15T10:05:31.980+0000", "status": 404, "error": '
             '"Not Found", "message": "No message available", "path": "/counterparty'
             '/order/"}'
    )
    request = create_request(
        client=Client(
            profile=Profile(
                reg_state_date=datetime.datetime(year=2009, month=1, day=1).date()
            )
        ),
        bank=Bank(code=BankCode.CODE_SPB_BANK),
        person_shareholders=[ProfilePartnerIndividual(
            is_general_director=True
        )]
    )
    user = request.client.user_set.first()

    SendToBankAction(
        request=request, user=user
    ).execute(params={
        'banks': [request.bank.id]
    })

    task_send_to_bank_from_verification(
        request_id=request.id, user_id=user.id, type='request'
    )
    request.refresh_from_db()
    assert request.status.code == RequestStatus.CODE_SCORING_FAIL


@pytest.mark.django_db
def test_send_to_bank_success(initial_data_db, mocked_requests):
    mocked_requests.register_uri(
        'POST',
        'http://127.0.0.1:8998/counterparty/order/',
        text='{"id": "12345"}'
    )

    request = create_request(
        client=Client(
            profile=Profile(
                reg_state_date=datetime.datetime(year=2009, month=1, day=1).date()
            )
        ),
        bank=Bank(code=BankCode.CODE_SPB_BANK),
        person_shareholders=[ProfilePartnerIndividual(
            is_general_director=True
        )]
    )
    user = request.client.user_set.first()

    SendToBankAction(
        request=request, user=user
    ).execute(params={
        'banks': [request.bank.id]
    })

    task_send_to_bank_from_verification(
        request_id=request.id, user_id=user.id, type='request'
    )
    request.refresh_from_db()
    assert request.status.code == RequestStatus.CODE_SENDING_IN_BANK
    adapter = get_send_adapter_class(request=request)(user=user)
    adapter.finish_send_to_bank(request=request)
    assert request.status.code == RequestStatus.CODE_SEND_TO_BANK
    assert ExternalRequest.get_request_data(
        request=request, bank=request.bank
    ).external_id == '12345'
