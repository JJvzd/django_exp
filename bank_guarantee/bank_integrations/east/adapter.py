from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from bank_guarantee.bank_integrations.east.print_forms_helper import EastHelper
from bank_guarantee.bank_integrations.east.settlement_act import EastBank
from .bank_api import SendRequest


class Adapter(BaseBankAdapter):

    def get_print_forms_helper(self):
        return EastHelper

    def get_settlement_act_generator(self):
        return EastBank

    def get_request_status_in_bank(self, request):
        sender = SendRequest()
        return sender.get_current_status(request)

    def get_data_for_send_request_to_bank(self, request):
        sender = SendRequest()
        return sender.clear_output_data_for_log(sender.get_data_for_send(request))

    def send_request_to_bank(self, request):
        sender = SendRequest()
        return sender.send_request(request)
