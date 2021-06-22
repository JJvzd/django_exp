import pytest

from bank_guarantee.models import RequestStatus
from clients.models import Bank
from settings.configs.banks import BankCode
from utils.functions_for_tests import create_request


@pytest.mark.django_db
def test_set_number_in_spb_bank(initial_data_db):
    request = create_request(bank=Bank(code=BankCode.CODE_SPB_BANK))
    request.set_status(RequestStatus.CODE_SEND_TO_BANK, force=True)
    request.refresh_from_db()
    assert str(request.get_number()) in request.request_number_in_bank
    assert len(request.request_number_in_bank) == 6
