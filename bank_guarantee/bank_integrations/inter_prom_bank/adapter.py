from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from .bank_api import SendRequest


class Adapter(BaseBankAdapter):

    def get_request_status_in_bank(self, request):
        return {}

    def get_data_for_send_request_to_bank(self, request):
        sender = SendRequest()
        return sender.get_data_for_send(request)

    def send_request_to_bank(self, request):
        sender = SendRequest()
        return sender.send_request(request)
