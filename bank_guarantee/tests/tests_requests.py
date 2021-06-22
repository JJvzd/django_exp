import pytest

from bank_guarantee.models import Request, Offer
from bank_guarantee.user_stories import change_request_archive_state
from clients.models import Bank
from tests.conf.load_db.load_request import create_bg_request


@pytest.mark.django_db
def test_send_archive(setup_db):
    request = create_bg_request(setup_db.get('client'))
    assert request.in_archive is False
    change_request_archive_state(request=request, archive=True, user=setup_db['client'].user_set.first())
    assert request.in_archive is True
    change_request_archive_state(request=request, archive=True, user=setup_db['client'].user_set.first())
    assert request.in_archive is True
    change_request_archive_state(request=request, archive=False, user=setup_db['client'].user_set.first())
    assert request.in_archive is False


def test_calculate_offer_commission():
    offer = Offer(
        request=Request(interval=360, bank=Bank(code='test')),
        amount=100000,
        default_commission_bank=3000,
        commission_bank=30000,
        delta_commission_bank=27000
    )
    offer.update_agent_commissions()
    assert offer.default_commission == offer.default_commission_bank
    assert offer.commission == offer.commission_bank
    assert offer.delta_commission == offer.delta_commission_bank
