import json
import logging

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from bank_guarantee.actions import OfferPaidAction
from bank_guarantee.models import RequestStatus, Request
from clients.models import Bank, BankCode

logger = logging.getLogger('django')


@method_decorator(csrf_exempt, name='dispatch')
class ConfirmPayView(View):

    def post(self, request, request_id, *args, **kwargs):
        data = json.loads(self.request.body)
        logger.info("Полученные данные автоквитовки %s, номер заявки %s" % (
            json.dumps(data), request_id
        ))
        request = Request.objects.filter(request_number_in_bank=request_id).first()
        if not request:
            return JsonResponse({
                "err_code": 1,
                "err_text": "Не найдена заявка по orderId для банка"
            }, safe=False, json_dumps_params={'ensure_ascii': False})

        if not request.has_offer() or \
                request.status.code != RequestStatus.CODE_OFFER_WAIT_PAID:
            return JsonResponse({
                "err_code": 3,
                "err_text": "Некорректный статус заявки"
            })
        if request.client.inn != data.get('inn') or \
                float(data.get("commission")) != float(request.offer.commission_bank):
            return JsonResponse({
                "err_code": 4,
                "err_text": "Заявка, требующая подтверждение платежа, не найдена "
                            "с заданным ИНН клиента и комиссией для банка",
            })
        OfferPaidAction(
            request=request,
            user=Bank.objects.filter(code=BankCode.CODE_SPB_BANK).first().user_set.first()
        ).execute()
        return JsonResponse({
            "err_code": 0,
            "err_text": "Ошибок нет"
        }, safe=False, json_dumps_params={'ensure_ascii': False})
