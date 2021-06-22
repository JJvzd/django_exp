from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from bank_guarantee.bank_integrations.inbank.print_forms_helper import InbankHelper
from bank_guarantee.bank_integrations.mspbank.settlement_act import MspBank


class Adapter(BaseBankAdapter):

    def get_print_forms_helper(self):
        return InbankHelper

    def get_settlement_act_generator(self):
        return MspBank
