import logging

from sentry_sdk import capture_exception

from bank_guarantee.helpers.referal_sign import need_sign_url, add_sign_url_for_request
from bank_guarantee.models import RequestStatus, Request
from base_request.helpers import BeforeSendToBankResult
from base_request.logic.request_log import RequestLogger
from notification.base import Notification
from tender_loans.models import LoanRequest, LoanStatus
from utils.helpers import generate_log_tags

logger = logging.getLogger('django')


class BaseSendToBankAdapter:

    def __init__(self, user):
        self.user = user

    def finish_send_to_bank(self, request):
        already_sent = self._check_already_send(request)
        if not already_sent:
            request.copy_documents()
        self._notify_success_send_to_bank(request)

    def send_to_bank(self, request, from_verification: bool = False):
        self.prepare_request_for_bank(request, from_verification)
        if request.status.code not in [RequestStatus.CODE_VERIFICATION,
                                       RequestStatus.CODE_CLIENT_SIGN]:
            before_send_result = self.send_via_bank_integration(request)
            if before_send_result.result:
                self.finish_send_to_bank(
                    request=request
                )
            else:
                request.scoring_reject_reason = before_send_result.reason
                request.set_status(RequestStatus.CODE_SCORING_FAIL)

    def prepare_request_for_bank(self, request, from_verification=False) -> bool:
        """ Событие отправки заявки на рассмотрение в банк
        Тут выполняются действия, которые нужно выполнить когда заявка отправлена в
        любой банк - подготовить данные, создать обсуждения, поставить статусы.

        Любая заявка независимо от того, что с ней будет дальше, должна пройти
        через это действие

        :return: bool - была ли заявка отправлена повторно или первый раз
        """
        logger.info("Подговка к отправке в банк. Установка статусов %s" %
                    generate_log_tags(request=request))

        already_sent = self._check_already_send(request=request)
        if not request.bank:
            raise ValueError('Не указан банк, на этот момент должен быть %s' %
                             generate_log_tags(request=request))

        if not from_verification and request.bank.settings.verification_enable:
            self.set_request_in_verification(request=request)
        elif request.bank.settings.allow_request_only_with_ecp and not request.is_signed:
            self.set_request_to_sign_status(request=request)
        else:
            self.set_request_in_bank(request=request)

        request.log(
            action="Заявка %s отправлена в банк %s" % (
                request.get_number(), request.bank.short_name
            ),
            user=self.user)
        logger.info("Заявке присвоен статус %s %s" % (
            request.status.code, generate_log_tags(request=request)
        ))
        return already_sent

    def set_request_in_verification(self, request):
        logger.info("Перевод в статус верификации %s" %
                    generate_log_tags(request=request))
        request.set_status(RequestStatus.CODE_VERIFICATION)
        request.log(
            action="Заявка %s на верификации в банк %s" % (
                request.get_number(), request.bank.short_name
            ),
            user=self.user
        )

    def set_request_to_sign_status(self, request):
        logger.info("Перевод в статус на подписании у клиента %s" % generate_log_tags(
            request=request
        ))
        request.set_status(RequestStatus.CODE_CLIENT_SIGN)
        request.log(
            action='Заявка возвращена на подпись клиенту',
            user=self.user,
        )

        if need_sign_url(request):
            add_sign_url_for_request(request=request, user=self.user)

    def set_request_in_bank(self, request):
        logger.info("Перевод в статус отправки в банк %s" % generate_log_tags(
            request=request
        ))
        request.set_status(RequestStatus.CODE_SEND_TO_BANK)

    @staticmethod
    def _check_already_send(request):
        already_sent = False
        if isinstance(request, Request):
            status_codes = [
                RequestStatus.CODE_IN_BANK,
                RequestStatus.CODE_CLIENT_SIGN,
                RequestStatus.CODE_VERIFICATION
            ]
            already_sent = request.requesthistory_set.filter(
                status__code__in=status_codes
            ).exists()
        if isinstance(request, LoanRequest):
            already_sent = request.loanhistory_set.filter(
                status__code=LoanStatus.CODE_IN_BANK
            ).exists()
        return already_sent

    @staticmethod
    def _notify_success_send_to_bank(request):
        params = {
            'requests': [request],
            'need_sign': not request.is_signed,
        }
        Notification.trigger('request_client_to_bank', params=params)

    @staticmethod
    def send_via_bank_integration(request) -> BeforeSendToBankResult:
        """
        Проводит дополнительные действия для отправки заявки в банк,
        например отправляет через апи данные
        :param request:
        :return:
        """
        try:
            return request.bank_integration.send_request_to_bank(request=request)
        except Exception as error:
            capture_exception(error)
            RequestLogger.log(request, error)
            return BeforeSendToBankResult(
                result=False, reason="Ошибка при отправке в банк"
            )
