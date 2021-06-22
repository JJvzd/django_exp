import pytest

from bank_guarantee.user_stories import change_request_archive_state, validate_request, \
    can_view_request
from base_request.exceptions import RequestWrongAccessException
from utils.functions_for_tests import create_request, create_client


@pytest.mark.django_db
def test_change_request_archive_state(initial_data_db):
    request = create_request()
    another_user = create_client().user_set.first()
    assert change_request_archive_state(
        request=request, archive=True, user=request.client.user_set.first()
    ) is True
    assert change_request_archive_state(
        request=request, archive=False, user=request.client.user_set.first()
    ) is True
    with pytest.raises(RequestWrongAccessException):
        assert change_request_archive_state(
            request=request, archive=False, user=another_user
        )


@pytest.mark.django_db
def test_validate_request(initial_data_db):
    request = create_request()
    assert validate_request(request) == {
        'agree': ['Отсутствует согласие на обработку персональных данных'],
        'contract_type': ['Не указано контракт государственный или муниципальный'],
        'final_date': ['Не указан крайний срок выдачи'],
        'request.creator_email': ['Не указан Email исполнителя'],
        'request.creator_name': ['Неверно указано Имя исполнителя'],
        'request.creator_phone': ['Не указан Телефон исполнителя'],
        'request.protocol_date': ['Не указана дата протокола'],
        'request.protocol_lot_number': ['Не указан номер лота'],
        'suggested_price_amount': ['Не указана предложенная цена контракта'],
        'tender.beneficiary_address': ['Не указан адрес заказчика'],
        'tender.beneficiary_inn': ['Не указан ИНН заказчика'],
        'tender.beneficiary_kpp': ['Не указан КПП заказчика'],
        'tender.beneficiary_name': ['Не указано наименование заказчика'],
        'tender.beneficiary_ogrn': ['Не указан ОГРН заказчика'],
        'tender.notification_id': ['Не указан номер извещения'],
        'tender.publish_date': ['Не указана дата размещения извещения'],
        'tender.subject': ['Не указан предмет контракта'],
        'placement_way': ['Не указан способ определения поставщика'],
        'rules': {
            'agree': "val => !!val || 'Отсутствует согласие на обработку "
                     "персональных данных'",
            'beneficiary_address': "val => !!val || 'Не указан адрес заказчика'",
            'beneficiary_inn': "val => !!val || 'Не указан ИНН заказчика'",
            'beneficiary_kpp': "val => !!val || 'Не указан КПП заказчика'",
            'beneficiary_name': "val => !!val || 'Не указано наименование "
                                "заказчика'",
            'beneficiary_ogrn': "val => !!val || 'Не указан ОГРН заказчика'",
            'contract_type': "val => !!val || 'Не указано контракт "
                             "государственный или муниципальный'",
            'creator_email': 'val => /(^|\\s)[-a-zA-Z0-9_.]+@([-a-zA-Z0-9]+\\.)+[a-z]'
                             '{2,6}(\\s|$)/.test(val) '
                             "|| 'Не указан Email исполнителя'",
            'creator_name': "val => !!val || 'Неверно указано Имя исполнителя'",
            'creator_phone': "val => !!val || 'Не указан Телефон исполнителя'",
            'final_date': "val => !!val || 'Не указан крайний срок выдачи'",
            'notification_id': "val => !!val || 'Не указан номер извещения'",
            'placement_way': "val => !!val || 'Не указан способ определения "
                             "поставщика'",
            'protocol_date': "val => !!val || 'Не указана дата протокола'",
            'protocol_lot_number': "val => !!val || 'Не указан номер лота'",
            'publish_date': "val => !!val || 'Не указана дата размещения "
                            "извещения'",
            'subject': "val => !!val || 'Не указан предмет контракта'",
            'suggested_price_amount': "val => val != 0 || 'Не указана "
                                      "предложенная цена контракта', val => "
                                      "!!val || 'Не указана предложенная цена "
                                      "контракта'"
        },
    }


@pytest.mark.django_db
def test_can_view_request(initial_data_db):
    request = create_request()
    another_user = create_client().user_set.first()
    assert can_view_request(
        request=request, user=request.client.user_set.first()
    ) is True
    assert can_view_request(
        request=request, user=another_user
    ) is False
