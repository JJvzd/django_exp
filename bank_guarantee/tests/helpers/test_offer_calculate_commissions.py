import pytest

from bank_guarantee.helpers.offer_calculate_commission import OfferDefaultCalcCommission, InbankOfferCalcCommission
from bank_guarantee.models import Offer, Request


def test_default_calculate_commission():
    offer = Offer(default_commission_bank=1000, commission_bank=1100, delta_commission_bank=100)
    assert OfferDefaultCalcCommission.calculate(offer) == (1000, 100, 1100)

INBANK_TEST_DATA = [
    [Offer(request=Request(interval=360), amount=100000, default_commission_bank=1000, commission_bank=1000,
                  delta_commission_bank=0), (2958.9, -1958.9, 1000)],
    [Offer(request=Request(interval=360), amount=100000, default_commission_bank=3000, commission_bank=30000,
           delta_commission_bank=27000), (30000, 0, 30000)],
]
@pytest.mark.parametrize('offer, result', INBANK_TEST_DATA)
def test_inbank_calculate_commission(offer, result):
    assert InbankOfferCalcCommission.calculate(offer) == result


