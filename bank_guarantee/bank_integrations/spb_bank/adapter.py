import random

from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from bank_guarantee.bank_integrations.spb_bank.api import SPBApi
from bank_guarantee.bank_integrations.spb_bank.print_form_helper import SPBHelper
from bank_guarantee.bank_integrations.spb_bank.tasks import (
    send_offer_ready, send_request_to_bank, request_reject_by_client
)
from bank_guarantee.models import ExternalRequest
from base_request.helpers import BeforeSendToBankResult


class Adapter(BaseBankAdapter):
    LIMIT_CHARS_IN_NUMBER = 6

    def get_print_forms_helper(self):
        return SPBHelper

    def get_request_status_in_bank(self, request):
        external_request = ExternalRequest.get_request_data(
            request=request, bank=request.bank
        )
        if external_request:
            api = SPBApi()
            return api.get_request(request_id=external_request.external_id)
        else:
            return {
                'error': 'Не найдена внешняя заявка, возможно '
                         'заявка еще '
                         'не была отправлена'
            }

    def set_number_in_bank(self, request, number=None):
        request_number = ('%s%s' % (
            request.get_number().replace('-', ''),
            random.randint(10000, 99999)
        ))
        request_number = request_number[:self.LIMIT_CHARS_IN_NUMBER]
        request.request_number_in_bank = request_number

    def send_offer_to_bank(self, request):
        send_offer_ready(request=request)

    def get_data_for_send_request_to_bank(self, request):
        api = SPBApi()
        return api.get_request_data(request=request)

    def send_request_to_bank(self, request):
        request_id = send_request_to_bank(request)
        if request_id:
            return BeforeSendToBankResult(result=True)
        else:
            return BeforeSendToBankResult(reason='Ошибка отправки в банк', result=False)

    def after_request_reject_by_client(self, request, reason):
        request_reject_by_client(request=request, reason=reason)

    def after_reject_request(self, request, reason=None):
        request_reject_by_client(request=request, reason=reason)

    def bank_amount_limit(self, request):
        quarter = request.client.accounting_report.get_last_closed_quarter()
        amount_limit = quarter.get_balance() * 12/quarter.get_end_date().month
        default_amount_limit = super().bank_amount_limit(request)
        if amount_limit < default_amount_limit:
            return amount_limit
        return default_amount_limit
