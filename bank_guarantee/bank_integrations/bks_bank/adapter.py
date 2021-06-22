from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from .bank_api import SendRequest


class Adapter(BaseBankAdapter):

    @property
    def has_before_accept_offer(self):
        sender = SendRequest()
        return sender.check_enable_api() and sender.enabled

    def get_request_status_in_bank(self, request):
        sender = SendRequest()
        return sender.get_current_status(request)

    def get_data_for_send_request_to_bank(self, request):
        sender = SendRequest()
        return sender.get_data_for_send(request)

    def send_request_to_bank(self, request):
        sender = SendRequest()
        return sender.send_request(request)

    def after_client_offer_confirm(self, request):
        sender = SendRequest()
        return sender.send_request(request)

    def bank_amount_limit(self, request):
        quarter = request.client.accounting_report.get_quarters()[1]
        limit = quarter.get_value(2110) * 1000 * 0.5

        return limit

    # def before_accept_offer(self, request):
    #     sender = SendRequest()
    #     return sender.before_accept_offer(request)

    def check_and_update_status(self, request):
        sender = SendRequest()
        sender.check_and_update_status(request)
