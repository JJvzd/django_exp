from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from bank_guarantee.bank_integrations.inbank.print_forms_helper import InbankHelper
from bank_guarantee.bank_integrations.inbank.settlement_act import Inbank
# from bank_guarantee.helpers.offer_calculate_commission import InbankOfferCalcCommission


class Adapter(BaseBankAdapter):

    def get_calculator_commission_class(self):
        return super(Adapter, self).get_calculator_commission_class()
        # return InbankOfferCalcCommission Временно отключен

    def get_print_forms_helper(self):
        return InbankHelper

    def get_settlement_act_generator(self):
        return Inbank

    def get_request_status_in_bank(self):
        pass
