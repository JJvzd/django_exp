from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from bank_guarantee.bank_integrations.spb_bank.adapter import Adapter
from bank_guarantee.models import Request
from clients.models import Bank
from settings.configs.banks import BankCode


def test_get_bank_integration():
    request = Request(bank=Bank(code=BankCode.CODE_SPB_BANK))
    assert isinstance(request.bank_integration, Adapter)
    request = Request(bank=Bank(code='asdgdfag'))
    assert isinstance(request.bank_integration, BaseBankAdapter)
