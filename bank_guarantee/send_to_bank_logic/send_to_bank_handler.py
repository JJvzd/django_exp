import logging

from bank_guarantee.send_to_bank_logic.adapters.base import BaseSendToBankAdapter
from bank_guarantee.send_to_bank_logic.adapters.spb_bank import SPBSendToBankAdapter
from bank_guarantee.send_to_bank_logic.conclusion_logic import ConclusionsGenerator
from bank_guarantee.send_to_bank_logic.helpers import get_request_model
from bank_guarantee.send_to_bank_logic.print_form_logic import PrintFormsGenerator
from bank_guarantee.tasks import task_update_request_rating
from conclusions_app.conclusions_logic import ConclusionsLogic
from settings.configs.banks import BankCode

logger = logging.getLogger('django')
scoring_logger = logging.getLogger('scoring')


def get_send_adapter_class(request):
    return {
        BankCode.CODE_SPB_BANK: SPBSendToBankAdapter
    }.get(request.bank.code, BaseSendToBankAdapter)


class SendToBankHandler:
    conclusion_logic = ConclusionsLogic

    def __init__(self, user):
        self.user = user

    def start_send_to_bank_from_verification(self, request):
        """ Отправка в банк после верификации """
        task_update_request_rating(request_id=request.id)
        adapter = get_send_adapter_class(request=request)(user=self.user)
        adapter.send_to_bank(request=request, from_verification=True)

    def start_send_to_bank(self, base_request):
        """ Доотправка заявки в банк
        :param base_request: Базовая заявка, от которой копировались остальные
        """
        task_update_request_rating(request_id=base_request.id)
        model = get_request_model(base_request)
        requests_for_send = model.objects.filter(base_request=base_request).exclude(
            id=base_request.id
        )

        PrintFormsGenerator.generate_print_forms(base_request, requests_for_send)
        ConclusionsGenerator(conclusion_logic=self.conclusion_logic).generate_conclusions(
            base_request, requests_for_send
        )

        requests_for_send = [base_request] + list(requests_for_send)
        for request in requests_for_send:
            adapter = get_send_adapter_class(request=request)(user=self.user)
            adapter.send_to_bank(request=request)
