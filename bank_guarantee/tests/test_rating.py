import mock

import pytest

from bank_guarantee.rating import BankRatingResultData
from clients.models import Bank, BankRating
from settings.configs.banks import BankCode
from utils.functions_for_tests import create_request


@pytest.mark.django_db
def test_rating_generate(initial_data_db):
    request = create_request(bank=Bank(code=BankCode.CODE_SPB_BANK))

    rating_class = 'bank_guarantee.bank_integrations.spb_bank.bank_rating.BankRating'
    bank_rating, _ = BankRating.objects.update_or_create(credit_organization=request.bank, defaults={
        'rating_class': rating_class,
        'active': True
    })
    return_value = BankRatingResultData(
        data={'result': 'test_result'},
        score='1',
        finance_state='2',
        risk_level='3',
        rating='4',
    )
    with mock.patch('%s.calculate' % rating_class, return_value=return_value) as mocked_rating:
        data = bank_rating.get_rating(request)
        assert data.data == {'result': 'test_result'}
        assert data.score == return_value.score
        assert data.finance_state == return_value.finance_state
        assert data.risk_level == return_value.risk_level
        assert data.rating == return_value.rating
