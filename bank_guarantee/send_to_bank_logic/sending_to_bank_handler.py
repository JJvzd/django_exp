import logging
from typing import List

from django.conf import settings
from django.utils import timezone


from bank_guarantee.models import Request, RequestStatus
from bank_guarantee.send_to_bank_logic.helpers import get_request_model
from base_request.models import AbstractRequest
from base_request.tasks import task_send_to_bank
from cabinet.base_logic.scoring.base import ScoringLogic, ScoringResult
from utils.helpers import generate_log_tags

logger = logging.getLogger('django')


class SendingToBanksHandler:

    def fix_before_sending(self, request: AbstractRequest):
        now = timezone.now()

        request.sent_to_bank_date = now

        if isinstance(request, Request) and request.interval_from < now.date():
            request.interval_from = now.date()

            if request.final_date and request.final_date < now.date():
                request.final_date = now.date()
        request.save()
        return request

    def __init__(self, user):
        self.user = user

    def send_to_many_banks(self, request: AbstractRequest, banks: List):
        sending_result = []
        model = get_request_model(request)

        request = self.fix_before_sending(request)

        base_request = request
        if not base_request.is_sent_to_many_banks():
            base_request.base_request = base_request
            base_request.save()

        for bank in banks:
            logger.info(
                'Отправка заявки в %s. %s' % (bank.short_name, generate_log_tags(
                    request=base_request, user=self.user
                ))
            )
            current_request = model.objects.filter(
                bank=bank, base_request=base_request
            ).first()

            if current_request:
                if not current_request.request_number:
                    current_request.request_number = current_request.generate_request_number()  # noqa
                    current_request.save()
            else:
                if not bank.settings.enable:
                    logger.info('Принятие заявок в банк %s выключено. %s' % (
                        bank.short_name, generate_log_tags(request=current_request)))
                    continue
                scoring = ScoringLogic(bank=bank, request=request)
                if bank.settings.scoring_enable:
                    result = scoring.check(use_common_rules=True)
                else:
                    result = ScoringResult()

                if result.is_fail:
                    logger.info(
                        'Результат проверки скоринг в банк %s - false (%s). %s' % (
                        bank.short_name, result.get_errors(), generate_log_tags(
                            request=base_request, user=self.user
                        ))
                    )
                    continue
                else:
                    current_request = self.get_request_for_send_to_bank(base_request)

            sending_to_bank_request = self.start_send_in_bank(current_request, bank)
            sending_result.append(sending_to_bank_request)
        base_request.refresh_from_db()
        if model.objects.filter(base_request=base_request.base_request).count() == 1:
            base_request.request_number = base_request.request_number.split('-')[0]
            base_request.save()

        if not settings.TESTING:
            task_send_to_bank.delay(
                request_id=base_request.id,
                type='request' if isinstance(base_request, Request) else 'loan',
                user_id=self.user.id
            )
        return sending_result

    def get_request_for_send_to_bank(self, request):
        if not request.bank:
            work_request = request
            work_request.base_request = request
            if '-' not in str(work_request.request_number):
                work_request.request_number = request.generate_request_number()
        else:
            work_request = request.clone_request()

        return work_request

    def start_send_in_bank(self, request, bank):
        """ Событие успешно пройденного скоринга при отправке заявки в банк """
        request.set_status(RequestStatus.CODE_SENDING_IN_BANK)
        request.set_bank(bank)

        if request.request_type == AbstractRequest.TYPE_BG:
            commission = (request.get_commission_for_bank_code(bank.code) and
                          request.get_commission_for_bank_code(bank.code)['commission'])
            request.commission = float(commission or 0)
        request.save()
        return request
