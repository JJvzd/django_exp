from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from bank_guarantee.bank_integrations.baikal.print_forms_helper import BaikalHelper
from bank_guarantee.bank_integrations.baikal.settlement_act import BaicalInvestBank


class Adapter(BaseBankAdapter):

    def get_print_forms_helper(self):
        return BaikalHelper

    def get_settlement_act_generator(self):
        return BaicalInvestBank
