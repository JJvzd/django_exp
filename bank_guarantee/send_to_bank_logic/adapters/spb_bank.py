import logging

from bank_guarantee.models import RequestStatus
from bank_guarantee.send_to_bank_logic.adapters.base import BaseSendToBankAdapter

logger = logging.getLogger('django')


class SPBSendToBankAdapter(BaseSendToBankAdapter):

    def finish_send_to_bank(self, request):
        already_sent = self._check_already_send(request)
        self.set_request_in_bank(request=request)
        if not already_sent:
            request.copy_documents()
        self._notify_success_send_to_bank(request)

    def send_to_bank(self, request, from_verification: bool = False):
        if not from_verification:
            if request.bank.settings.verification_enable:
                self.set_request_in_verification(request=request)
        elif request.bank.settings.allow_request_only_with_ecp and not request.is_signed:
            self.set_request_to_sign_status(request=request)
        else:
            request.set_status(RequestStatus.CODE_SENDING_IN_BANK)

        if request.status.code not in [RequestStatus.CODE_VERIFICATION,
                                       RequestStatus.CODE_CLIENT_SIGN]:
            before_send_result = self.send_via_bank_integration(request)
            if before_send_result.result:
                pass
            else:
                request.scoring_reject_reason = before_send_result.reason
                request.set_status(RequestStatus.CODE_SCORING_FAIL)
