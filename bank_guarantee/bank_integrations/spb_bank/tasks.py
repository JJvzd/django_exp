import json
import logging

from bank_guarantee.models import ExternalRequest, RequestStatus
from bank_guarantee.bank_integrations.spb_bank.api import SPBApi
from clients.models import Bank
from settings.configs.banks import BankCode
from utils.helpers import generate_log_tags


logger = logging.getLogger('django')


def get_bank() -> Bank:
    return Bank.objects.filter(code=BankCode.CODE_SPB_BANK).first()


def send_request_to_bank(request):
    api = SPBApi()
    request_id = api.send_request(request=request)
    if request_id:
        external_request, _ = ExternalRequest.objects.get_or_create(
            request=request, defaults=dict(
                bank=Bank.objects.filter(code=BankCode.CODE_SPB_BANK).first(),
                external_id=request_id,
            )
        )
        return external_request
    return None


def check_status_from_bank(external_request: ExternalRequest):
    if external_request.status == 'deny':
        return
    print('Skip %s, already deny' % external_request.external_id)
    api = SPBApi()
    info = api.get_request(request_id=external_request.external_id)
    print(info)
    if info:
        external_request.other_data = json.dumps(info)
        external_request.save()
    from base_request.logic.request_log import RequestLogger
    RequestLogger.log(external_request.request, json.dumps(info))
    bank_user = get_bank().user_set.first()
    if 'lost' in info.keys():
        if info['lost']:
            reason = info.get('lostReason')
            from bank_guarantee.actions import RejectAction
            RequestLogger.log(
                external_request.request, 'Заявка отклонена с причиной %s' % reason
            )
            RejectAction(external_request.request, user=bank_user).execute({
                'reason': reason,
                'force': True,
            })
            external_request.status = 'deny'
            external_request.save()
            return
    from bank_guarantee.send_to_bank_logic.send_to_bank_handler import \
        get_send_adapter_class

    if external_request.request.status.code == RequestStatus.CODE_SENDING_IN_BANK:
        execution_percent = info.get('executionPercent', 0)
        if execution_percent >= 50:
            adapter = get_send_adapter_class(
                request=external_request.request
            )(user=bank_user)
            adapter.finish_send_to_bank(request=external_request.request)


def send_offer_ready(request):
    api = SPBApi()
    external_request = ExternalRequest.objects.filter(request=request).first()
    if external_request:
        api.send_offer_ready(request=request, request_id=external_request.external_id)
    else:
        logger.error(
            'Не найдена модель ExternalRequest для заявки %s' % generate_log_tags(
                request=request
            )
        )


def request_reject_by_client(request, reason):
    api = SPBApi()
    external_request = ExternalRequest.objects.filter(request=request).first()
    if external_request:
        api.request_reject(
            request=request, request_id=external_request.external_id, reason=reason
        )
    else:
        logger.error(
            'Не найдена модель ExternalRequest для заявки %s' % generate_log_tags(
                request=request
            )
        )
