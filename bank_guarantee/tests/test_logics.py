import pytest
from django.core.cache import cache
from django.utils import timezone
from mock import patch, Mock

from bank_guarantee.actions import (
    SendToBankAction, RequestActionHandler, RequestDenyByVerifier
)
from bank_guarantee.models import Request, RequestStatus
from base_request.logic.user_stories import get_banks_for_send
from base_request.models import RequestTender
from base_request.tasks import task_send_to_bank, task_send_to_bank_from_verification
from clients.models import Bank
from settings.configs.banks import BankCode
from users.models import User, Role
from utils.functions_for_tests import create_request

pytestmark = pytest.mark.base_workflow


@pytest.fixture
def bank_for_send(setup_db):
    def __bank_for_send(with_verification=False, need_sign=False):
        bank = setup_db['bank']
        bank.settings.verification_enable = with_verification
        bank.settings.allow_request_only_with_ecp = need_sign
        bank.settings.save()
        bank.refresh_from_db()
        return bank

    return __bank_for_send


@patch('conclusions_app.settings.CONCLUSIONS', [])
@pytest.mark.parametrize('with_verification,need_sign,status', [
    [False, False, RequestStatus.CODE_SEND_TO_BANK],
    [False, True, RequestStatus.CODE_CLIENT_SIGN],
    [True, False, RequestStatus.CODE_VERIFICATION],
    [True, True, RequestStatus.CODE_VERIFICATION]
])
def test_send_in_bank(setup_db, bank_for_send, with_verification, need_sign,
                      status):
    """ Тестирование отправки заявки в банк при разных настройках банка """
    client = setup_db['client']
    bank = bank_for_send(with_verification=with_verification,
                         need_sign=need_sign)
    tender = RequestTender.objects.create()
    request = Request.objects.create(
        client=client,
        required_amount=100000,
        tender=tender,
        interval_from=timezone.now().date()
    )
    result = SendToBankAction(request=request,
                              user=client.user_set.first()).execute({
        'banks': [bank.id]
    })

    assert result['result'] is True, "Результат отправки должен быть равен True"
    assert len(result['requests_list']) == 1
    assert request.bank_id is not None
    assert request.bank.id == bank.id
    assert request.status == RequestStatus.objects.get(
        code=RequestStatus.CODE_SENDING_IN_BANK)
    assert '-' not in request.request_number
    request.set_status(RequestStatus.CODE_DRAFT, force=True)
    assert request.status.code == RequestStatus.CODE_DRAFT
    action = SendToBankAction(request=request, user=client.user_set.first())
    result = action.execute({'banks': [bank.id]})
    assert result['result'] is True
    assert len(result['requests_list']) == 1
    assert request.bank_id is not None
    assert request.bank.id == bank.id
    assert request.status == RequestStatus.objects.get(
        code=RequestStatus.CODE_SENDING_IN_BANK)
    user = client.agent_company.user_set.first()
    task_send_to_bank(request_id=request.id, user_id=user.id, type='request')
    request.refresh_from_db()
    assert request.status.code == status


def test_allowed_actions_for_verifier(setup_db):
    """ Проверка доступных действий для верификатора """
    client = setup_db['client']
    user = User.objects.create_user(username='verificator',
                                    email='verificator@tendehelp.ru',
                                    password='12345')
    user.roles.add(Role.objects.get(name=Role.VERIFIER))

    tender = RequestTender.objects.create()
    request = Request.objects.create(
        client=client,
        required_amount=100000,
        tender=tender,
        interval_from=timezone.now().date()
    )
    request.set_status(RequestStatus.CODE_VERIFICATION, force=True)
    action_handler = RequestActionHandler(
        request=request, user=user
    ).get_allowed_actions()
    assert set(action_handler.keys()) == {
        'CHANGE_ASSIGNED',
        'CHANGE_VERIFIER',
        'EDIT',
        'VERIFIER_REQUIRE_MORE_INFO',
        'VERIFIER_APPROVED_REQUEST',
        'VERIFIER_DENY',
        'REQUEST_ANALYSIS'
    }


@patch('conclusions_app.settings.CONCLUSIONS', [])
def test_allowed_actions_for_client(rm, setup_db):
    """ Проверка доступных действий для верификатора """
    client = setup_db['client']
    tender = RequestTender.objects.create()
    request = Request.objects.create(
        client=client,
        required_amount=100000,
        tender=tender,
        interval_from=timezone.now().date(),
        agent=client.agent_company,
        agent_user=client.agent_user,
    )
    request.set_status(RequestStatus.CODE_VERIFIER_REQUIRE_MORE_INFO,
                       force=True)

    client_user = client.user_set.first()
    action_handler = RequestActionHandler(request=request,
                                          user=client_user).get_allowed_actions()
    assert set(action_handler.keys()) == {
        'EDIT', 'RETURN_TO_VERIFIER', 'CLONE_REQUEST'
    }

    agent_user = setup_db['client'].agent_company.user_set.first()
    action_handler = RequestActionHandler(request=request,
                                          user=agent_user).get_allowed_actions()
    assert set(action_handler.keys()) == {
        'EDIT', 'RETURN_TO_VERIFIER', 'CLONE_REQUEST'
    }


def test_deny_by_verifier(setup_db):
    """ Проверка доступных действий для верификатора """
    client = setup_db['client']
    tender = RequestTender.objects.create()
    request = Request.objects.create(
        client=client,
        required_amount=100000,
        tender=tender,
        interval_from=timezone.now().date(),
        agent=client.agent_company,
        agent_user=client.agent_user,
    )
    request.set_status(RequestStatus.CODE_VERIFICATION, force=True)
    user = User.objects.create_user(username='verificator',
                                    email='verificator@tendehelp.ru',
                                    password='12345')
    user.roles.add(Role.objects.get(name=Role.VERIFIER))

    RequestDenyByVerifier(request=request, user=user).execute({
        'reason': 'test_reason'
    })
    request.refresh_from_db()
    assert request.status.code == RequestDenyByVerifier.status_code


@pytest.mark.parametrize('need_sign,status', [
    [False, RequestStatus.CODE_SEND_TO_BANK],
    [True, RequestStatus.CODE_CLIENT_SIGN],
])
def test_send_bank_from_verification(setup_db, bank_for_send, need_sign,
                                     status):
    """ Тестирование отправки заявки в банк при разных настройках банка """
    client = setup_db['client']
    bank = bank_for_send(with_verification=True, need_sign=need_sign)
    tender = RequestTender.objects.create()
    request = Request.objects.create(
        client=client,
        required_amount=100000,
        tender=tender,
        bank=bank,
        interval_from=timezone.now().date()
    )

    request.set_status(RequestStatus.CODE_VERIFICATION, force=True)
    user = client.agent_company.user_set.first()
    task_send_to_bank_from_verification(request_id=request.id, type='request',
                                        user_id=user.id)
    request.refresh_from_db()
    assert request.status.code == status


@patch('conclusions_app.settings.CONCLUSIONS', [])
def test_generate_print_forms(setup_db):
    """ Тестирование что генерируется печатная форма """
    client = setup_db['client']
    bank = setup_db['bank']
    bank.allowed_print_forms.create(
        active=True,
        name='test print form',
        type='html',
        filename='request'
    )
    tender = RequestTender.objects.create()
    request = Request.objects.create(
        client=client,
        required_amount=100000,
        tender=tender,
        bank=bank,
        interval_from=timezone.now().date()
    )

    request.set_status(RequestStatus.CODE_SENDING_IN_BANK, force=True)
    user = client.agent_company.user_set.first()
    task_send_to_bank(request_id=request.id, type='request', user_id=user.id)
    request.refresh_from_db()
    try:
        assert request.status.code == RequestStatus.CODE_SEND_TO_BANK
        assert request.requestdocument_set.filter(
            print_form__isnull=False).count() > 0
    finally:
        bank.allowed_print_forms.all().delete()


@patch('conclusions_app.settings.CONCLUSIONS', [])
@pytest.mark.django_db
def test_sent_to_bank_with_disabled_banks_as_agent(initial_data_db, rm):
    rm.get(
        'http://openapi.clearspending.ru/restapi/v3/contracts/search/'
        '?supplierinn=5010050218',
        text='Data not found', status_code=404
    )
    commission_return = [
        {
            'bank_name': 'ИНБАНК',
            'bank_code': 'inbank',
            'commission': 1800,
            'percent': 18.0
        },
    ]

    request = create_request(
        request=Request(required_amount=10000, interval=365),
        bank=Bank(code=BankCode.CODE_INBANK)
    )
    request.calculate_commission = Mock(return_value=commission_return)
    request.bank.settings.active = True
    request.bank.settings.enable = True
    request.bank.settings.save()
    cache.clear()
    result = get_banks_for_send(
        request=request,
        user=request.agent_user,
        bank_model=Bank,
    )
    assert result == {
        'list': [
            {
                'bank_id': 18,
                'bank_name': 'ИНБАНК',
                'commission': {
                    'bank_code': 'inbank',
                    'bank_name': 'ИНБАНК',
                    'commission': 1800,
                    'percent': 18.0
                },
                'errors': [],
                'is_disabled': False,
                'label': 'Самый комфортный банк',
                'scoring': True
            }
        ],
        'send_to': 18
    }
    cache.clear()

    request.agent.disabled_banks.add(request.bank)
    result = get_banks_for_send(
        request=request,
        user=request.agent_user,
        bank_model=Bank,
    )
    assert result == {
        'list': [],
        'send_to': 18
    }
