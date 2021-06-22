import pytest

from bank_guarantee.actions import RequestActionHandler, CreateOfferAction
from bank_guarantee.models import RequestStatus
from users.models import Role
from utils.functions_for_tests import create_request, create_user


@pytest.mark.django_db
def test_underwriter_work(initial_data_db):
    """ Андерайтер должен иметь возможность
        1. одобрить заявку, после чего создать предложение и передать заявку с
           оффером ЛПР
        2. отправить на дозапрос
        3. забрать заявку от ЛПР и изменить предложение
    """
    request = create_request(status=RequestStatus.CODE_IN_BANK)
    underwriter = create_user(
        client=request.bank, roles=[Role.BANK_UNDERWRITER]
    )
    lpr = create_user(client=request.bank, roles=[Role.BANK_DECISION_MAKER])
    common = create_user(client=request.bank, roles=[Role.BANK_COMMON])
    issuer = create_user(client=request.bank, roles=[Role.BANK_ISSUER])
    underwriter_and_lpr = create_user(
        client=request.bank,
        roles=[Role.BANK_UNDERWRITER, Role.BANK_DECISION_MAKER]
    )

    allowed_actions = RequestActionHandler(
        request=request, user=underwriter
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {
        'ASSIGNED_TO_ANOTHER_AGENT', 'CHANGE_ASSIGNED', 'BANK_CONFIRM_REQUEST',
        'CHANGE_REQUEST_NUMBER', 'REJECT', 'SEND_REQUEST'
    }

    allowed_actions = RequestActionHandler(
        request=request, user=lpr
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {'CHANGE_ASSIGNED', 'REJECT'}

    allowed_actions = RequestActionHandler(
        request=request, user=common
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {'CHANGE_ASSIGNED',
                                           'CHANGE_REQUEST_NUMBER'}

    allowed_actions = RequestActionHandler(
        request=request, user=issuer
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {'CHANGE_ASSIGNED'}

    request.set_status(RequestStatus.CODE_REQUEST_CONFIRMED)
    request.set_assigned(underwriter, '')

    allowed_actions = RequestActionHandler(
        request=request, user=underwriter
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {
        'ASSIGNED_TO_ANOTHER_AGENT', 'CHANGE_ASSIGNED', 'CREATE_OFFER',
        'CHANGE_REQUEST_NUMBER', 'REJECT', 'SEND_REQUEST'
    }

    request.set_assigned(underwriter_and_lpr, '')
    allowed_actions = RequestActionHandler(
        request=request, user=underwriter_and_lpr
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {
        'ASSIGNED_TO_ANOTHER_AGENT', 'CHANGE_ASSIGNED', 'CHANGE_REQUEST_NUMBER',
        'CREATE_OFFER', 'REJECT', 'SEND_REQUEST'
    }

    request.set_assigned(lpr, '')
    allowed_actions = RequestActionHandler(
        request=request, user=lpr
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {'REJECT', 'CHANGE_ASSIGNED'}

    request.set_assigned(common, '')
    allowed_actions = RequestActionHandler(
        request=request, user=common
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {'CHANGE_ASSIGNED',
                                           'CHANGE_REQUEST_NUMBER'}

    request.set_assigned(issuer, '')
    allowed_actions = RequestActionHandler(
        request=request, user=issuer
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {'CHANGE_ASSIGNED'}

    action = CreateOfferAction(request=request, user=underwriter)
    result = action.execute(params=dict(
        assigned_id=lpr.id, amount=10000,
        commission_bank=1000,
        contract_date_end='2020-01-01',
        default_commission_bank=1000,
        default_commission_bank_percent=3,
        commission_bank_percent=3,
        delta_commission_bank=0,
        offer_active_end_date='2020-01-01'))
    assert result['result'] is True
    assert request.status.code == RequestStatus.CODE_OFFER_CREATED

    request.set_assigned(underwriter, '')
    allowed_actions = RequestActionHandler(
        request=request, user=underwriter
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {
        'ASSIGNED_TO_ANOTHER_AGENT',
        'CHANGE_ASSIGNED',
        'CREATE_OFFER',
        'CHANGE_REQUEST_NUMBER',
        'REJECT',
        'SEND_REQUEST'
    }

    request.set_assigned(underwriter_and_lpr, '')
    allowed_actions = RequestActionHandler(
        request=request, user=underwriter_and_lpr
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {
        'ASSIGNED_TO_ANOTHER_AGENT',
        'CHANGE_ASSIGNED',
        'CHANGE_REQUEST_NUMBER',
        'REJECT',
        'SEND_OFFER',
        'CREATE_OFFER',
        'SEND_REQUEST'
    }

    request.set_assigned(lpr, '')
    allowed_actions = RequestActionHandler(
        request=request, user=lpr
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {
        'REJECT', 'SEND_OFFER', 'CREATE_OFFER', 'CHANGE_ASSIGNED'
    }

    request.set_assigned(common, '')
    allowed_actions = RequestActionHandler(
        request=request, user=common
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {
        'CHANGE_ASSIGNED', 'CHANGE_REQUEST_NUMBER'
    }

    request.set_assigned(issuer, '')
    allowed_actions = RequestActionHandler(
        request=request, user=issuer
    ).get_allowed_actions()
    assert set(allowed_actions.keys()) == {'CHANGE_ASSIGNED'}
