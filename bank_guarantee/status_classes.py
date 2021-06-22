from django.utils import timezone

from bank_guarantee.models import RequestStatus
from bank_guarantee.signals import request_sent_in_bank


class StatusNotFoundException(Exception):
    def __init__(self, status_class, current_status):
        message = '%s не был найден в can_go_from_statuses %s' % \
                  (current_status, status_class.__class__.__name__)
        super().__init__(message)


ALLOWED_STATUSES = []


def register(cls):
    if cls not in ALLOWED_STATUSES:
        ALLOWED_STATUSES.append(cls)
    return cls


class AbstractStatusMachine:
    can_go_from_statuses = ()
    status_class = None
    status_code = None

    def __init__(self, request_instance):
        self.request_instance = request_instance

    def check_changing_status(self):
        current_status_code = None
        if self.request_instance.status:
            current_status_code = self.request_instance.status.code
        if current_status_code not in self.can_go_from_statuses:
            raise StatusNotFoundException(self, current_status_code)

    def get_object_status(self):
        return self.status_class.objects.get(code=self.status_code)

    def change_status(self):
        self.request_instance.status = self.get_object_status()
        self.request_instance.status_changed_date = timezone.now()

        if self.request_instance.status.code == RequestStatus.CODE_CLIENT_SIGN:
            request_sent_in_bank.send_robust(
                sender=self.__class__, request=self.request_instance, wait_sign=True
            )
        if self.request_instance.status.code == RequestStatus.CODE_SEND_TO_BANK:
            request_sent_in_bank.send_robust(
                sender=self.__class__, request=self.request_instance, wait_sign=False
            )
        self.request_instance.save()

    def run_change_status(self, force=False):
        if not force:
            self.check_changing_status()
        self.change_status()


class BaseRequestStatus(AbstractStatusMachine):
    status_class = RequestStatus


@register
class ClientDraftRequestStatus(BaseRequestStatus):
    status_code = 'draft'
    can_go_from_statuses = (
        None,
        'draft',
        RequestStatus.CODE_SEND_TO_BANK,
        'bank_send_offer',
        'offer_paid_wait',
        'bg_prepare',
        'bank_back',
        'offer_created',
        'credit_approve',
        'in_bank',
    )


@register
class AgentDraftRequestStatus(BaseRequestStatus):
    status_code = 'draft'
    can_go_from_statuses = (
        None,
    )


@register
class AgentDraftReadyRequestStatus(BaseRequestStatus):
    status_code = 'draft'
    can_go_from_statuses = (
        'draft',
    )


@register
class AgentDraftToEditRequestStatus(BaseRequestStatus):
    status_code = 'draft'
    can_go_from_statuses = (
        'draft',
        'scoring_fail',
        'request_back',
        'request_deny',
        'bank_return',
        'client_sign',
        'another_agent',
    )


@register
class ScoringFailRequestStatus(BaseRequestStatus):
    status_code = 'scoring_fail'
    can_go_from_statuses = (
        RequestStatus.CODE_SEND_TO_BANK,
        RequestStatus.CODE_SENDING_IN_BANK,
    )


@register
class SendingInBankRequestStatus(BaseRequestStatus):
    status_code = 'sending_in_bank'
    can_go_from_statuses = (
        'draft',
        'scoring_fail',
        'request_back',
        'request_deny',
        'not_actual',
        'bank_return',
        'client_sign',
        'another_agent',
        'sending_in_bank',
        'verification',
    )


@register
class SendToBankRequestStatus(BaseRequestStatus):
    status_code = RequestStatus.CODE_SEND_TO_BANK
    can_go_from_statuses = (
        RequestStatus.CODE_SENDING_IN_BANK,
        RequestStatus.CODE_CLIENT_SIGN,
        RequestStatus.CODE_ASK_ON_REQUEST,
        RequestStatus.CODE_VERIFICATION,
        RequestStatus.CODE_SEND_TO_BANK,
    )


@register
class RevokeByClientRequestStatus(BaseRequestStatus):
    status_code = 'request_back'
    can_go_from_statuses = (
        'draft',
        'scoring_fail',
        RequestStatus.CODE_SEND_TO_BANK,
        'request_back',
        'request_deny',
        'bank_send_offer',
        'offer_paid_wait',
        'bg_prepare',
        'bg_to_client',
        'bg_claim',
        'not_actual',
        'bank_return',
        'bank_back',
        'offer_created',
        'credit_approve',
        'client_sign',
        'another_agent',
        'in_bank',
        RequestStatus.CODE_VERIFICATION,
        RequestStatus.CODE_VERIFIER_REQUIRE_MORE_INFO,
        RequestStatus.CODE_DENY_BY_VERIFIER,
    )


@register
class RejectByBankRequestStatus(BaseRequestStatus):
    status_code = 'request_deny'
    can_go_from_statuses = (
        RequestStatus.CODE_SEND_TO_BANK,
        'offer_paid_wait',
        'bg_prepare',
        'offer_created',
        'credit_approve',
        'client_sign',
        'in_bank',
        'query_finished',
        RequestStatus.CODE_VERIFICATION,
    )


@register
class BankSendOfferRequestStatus(BaseRequestStatus):
    status_code = 'bank_send_offer'
    can_go_from_statuses = (
        'bank_back',
        'offer_created',
    )


@register
class OfferPendingPaymentRequestStatus(BaseRequestStatus):
    status_code = 'offer_paid_wait'
    can_go_from_statuses = (
        'bank_send_offer',
    )


@register
class PreparesBankGuaranteeRequestStatus(BaseRequestStatus):
    status_code = 'bg_prepare'
    can_go_from_statuses = (
        'offer_paid_wait',
    )


@register
class BankGuaranteeSentToClientRequestStatus(BaseRequestStatus):
    status_code = 'bg_to_client'
    can_go_from_statuses = (
        'bg_prepare',
    )


@register
class OfferRejectByClientRequestStatus(BaseRequestStatus):
    status_code = 'not_actual'
    can_go_from_statuses = (
        'bank_send_offer',
        'offer_paid_wait',
        'bg_prepare',
        'offer_created',
    )


@register
class QuestionFromBankRequestStatus(BaseRequestStatus):
    status_code = 'bank_return'
    can_go_from_statuses = (
        RequestStatus.CODE_SEND_TO_BANK,
        'credit_approve',
        'in_bank',
        'query_finished',
    )


@register
class OfferRevokeByBankRequestStatus(BaseRequestStatus):
    status_code = 'bank_back'
    can_go_from_statuses = (
        'bank_send_offer',
        'offer_paid_wait',
        'bg_prepare',
        'offer_created',
    )


@register
class PreparesOfferRequestStatus(BaseRequestStatus):
    status_code = 'offer_created'
    can_go_from_statuses = (
        None,
        'credit_approve',
        status_code,
        RequestStatus.CODE_OFFER_BACK,
    )


@register
class RequestApproveRequestStatus(BaseRequestStatus):
    status_code = 'credit_approve'
    can_go_from_statuses = (
        'in_bank',
        'query_finished',
    )


@register
class RequestSignedByClientRequestStatus(BaseRequestStatus):
    status_code = 'client_sign'
    can_go_from_statuses = (
        'draft',
        'scoring_fail',
        RequestStatus.CODE_SEND_TO_BANK,
        'request_deny',
        'not_actual',
        'bank_return',
        RequestStatus.CODE_SENDING_IN_BANK,
        RequestStatus.CODE_VERIFICATION,
    )


@register
class AssignedToAnotherAgentRequestStatus(BaseRequestStatus):
    status_code = 'another_agent'
    can_go_from_statuses = (
        RequestStatus.CODE_SEND_TO_BANK,
        'credit_approve',
        'in_bank',
        'query_finished',
    )


@register
class UnderConsiderationRequestStatus(BaseRequestStatus):
    status_code = 'in_bank'
    can_go_from_statuses = (
        RequestStatus.CODE_SEND_TO_BANK,
        'query_finished',
    )


@register
class ReceivedResponseToQuestionRequestStatus(BaseRequestStatus):
    status_code = 'query_finished'
    can_go_from_statuses = (
        'bank_return',
    )


@register
class VerificationRequestStatus(BaseRequestStatus):
    status_code = RequestStatus.CODE_VERIFICATION
    can_go_from_statuses = (
        RequestStatus.CODE_CLIENT_SIGN,
        RequestStatus.CODE_SENDING_IN_BANK,
        RequestStatus.CODE_VERIFIER_REQUIRE_MORE_INFO,
    )


@register
class VerifierRequireMoreInfoStatus(BaseRequestStatus):
    status_code = RequestStatus.CODE_VERIFIER_REQUIRE_MORE_INFO
    can_go_from_statuses = (
        RequestStatus.CODE_VERIFICATION,
    )


@register
class DenyByVerifierStatus(BaseRequestStatus):
    status_code = RequestStatus.CODE_DENY_BY_VERIFIER
    can_go_from_statuses = (
        RequestStatus.CODE_VERIFICATION,
    )


def get_status_class(status_code):
    for klass in ALLOWED_STATUSES:
        if klass.status_code == status_code:
            return klass
    raise ValueError('Не найден в ALLOWED_STATUSES')
