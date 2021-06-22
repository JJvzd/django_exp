from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from bank_guarantee.bank_integrations.metall_invest.print_forms_helper import (
    MetallInvestHelper
)
from bank_guarantee.bank_integrations.metall_invest.settlement_act import (
    MetallInvestBank
)


class Adapter(BaseBankAdapter):

    def get_print_forms_helper(self):
        return MetallInvestHelper

    def get_settlement_act_generator(self):
        return MetallInvestBank
