from django.utils.functional import cached_property

from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from bank_guarantee.bank_integrations.moscombank.print_forms_helper import (
    MoscombankHelper
)
from bank_guarantee.bank_integrations.moscombank.bank_api.base import (
    MoscombankSendRequest
)


class Adapter(BaseBankAdapter):
    @cached_property
    def api(self):
        return MoscombankSendRequest()

    def get_print_forms_helper(self):
        return MoscombankHelper

    def get_request_status_in_bank(self, request):
        return self.api.get_current_status(request)

    def get_data_for_send_request_to_bank(self, request):
        # нет единых данных, разная отправка для разных структур, реализовать потом
        return {}

    def send_request_to_bank(self, request):
        return self.api.send_request(request)

    def update_request_by_new_status(self, request, data=None):
        return self.api.update_status(self.get_external_request(request))

    def after_reject_request(self, request, reason=None):
        external_request = self.get_external_request(request)
        if external_request and external_request.external_id:
            return self.api.reject_request(request)

    def after_reject_offer(self, request, reason=None):
        return self.after_reject_request(request, reason)

    def init_request(self, request):
        return self.api.init_request(request)

    def new_message_in_discuss(self, request, message, author, files=None):
        external_request = self.get_external_request(request)
        if external_request and external_request.external_id:
            return self.api.send_new_message(request, message, author=author, files=files)

    def after_update_chat(self, request):
        external_request = self.get_external_request(request)
        if external_request and external_request.external_id:
            return self.api.update_chat(request)

    def after_sign_chat(self, request, files):
        external_request = self.get_external_request(request)
        if external_request and external_request.external_id:
            return self.api.sign_chat(request, files=files)
