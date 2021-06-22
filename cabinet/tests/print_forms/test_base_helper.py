from decimal import Decimal

from bank_guarantee.models import Request
from cabinet.base_logic.printing_forms.helpers.base import BaseHelper
from clients.models import Client
from questionnaire.models import Profile


def test_base_helper():
    request = Request(
        required_amount=Decimal('96397.83'),
        client=Client(
            profile=Profile()
        )
    )
    helper = BaseHelper(request=request, bank=None)
    assert helper.print_required_amount == 'девяносто шесть тысяч триста девяносто семь рублей 83 копейки'
