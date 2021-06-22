from django.db.models import Sum
from django.utils import timezone
from django.utils.functional import cached_property

from bank_guarantee.bank_integrations.settlement_act import OtherBank
from bank_guarantee.helpers.offer_calculate_commission import \
    OfferDefaultCalcCommission
from bank_guarantee.models import Request, RequestStatus
from base_request.helpers import BeforeSendToBankResult
from cabinet.base_logic.printing_forms.helpers.base import BaseHelper


class BaseBankAdapter:

    def __init__(self, bank):
        self.bank = bank

    def before_accept_offer(self, request):
        return {'result': True, 'errors': ''}

    @cached_property
    def api(self):
        return None

    def get_external_request(self, request):
        return request.externalrequest_set.filter(bank=request.bank).first()

    def get_calculator_commission_class(self):
        return OfferDefaultCalcCommission

    def get_print_forms_helper(self):
        return BaseHelper

    def get_settlement_act_generator(self):
        return OtherBank

    def set_number_in_bank(self, request, number=None):
        pass

    def send_offer_to_bank(self, request):
        pass

    def send_request_to_bank(self, request):
        return BeforeSendToBankResult(result=True)

    def get_data_for_send_request_to_bank(self, request):
        return {
            'result': 'У банка нет внешней интеграции'
        }

    def get_request_status_in_bank(self, request):
        return {
            'result': 'У банка нет внешней интеграции'
        }

    def update_request_by_new_status(self, request, data=None):
        pass

    def new_message_in_discuss(self, request, message, author, files=None):
        pass

    def after_client_offer_confirm(self, request):
        pass

    def after_reject_request(self, request, reason=None):
        pass

    def after_reject_offer(self, request):
        pass

    def after_request_reject_by_client(self, request, reason):
        pass

    def init_request(self, request):
        return None

    def after_sign_chat(self, request, files):
        pass

    def after_update_chat(self, request):
        pass

    def get_client_limit(self, client, required_amount: float = None) -> float:
        total = (Request.objects.select_related('status', 'offer').filter(
            bank=self.bank,
            status__code=RequestStatus.CODE_FINISHED,
            client=client,
            offer__contract_date_end__gt=timezone.now()
        ).aggregate(total=Sum('offer__amount'))['total'] or 0)

        if required_amount:
            total += required_amount

        limit = self.bank.settings.limit_for_client

        return limit - total

    def get_client_statistic(self, client):
        finished_requests = Request.objects.filter(
            client=client,
            bank=self.bank,
            status__code=RequestStatus.CODE_FINISHED
        )
        rejected_requests = Request.objects.filter(
            client=client,
            bank=self.bank,
            status__code=RequestStatus.CODE_REQUEST_DENY
        )
        requested_requests = Request.objects.filter(
            client=client,
            bank=self.bank,
            status__code=RequestStatus.CODE_SENT_REQUEST
        )
        in_work_requests = Request.objects.filter(
            client=client,
            bank=self.bank,
        ).exclude(
            status__code__in=[
                RequestStatus.CODE_FINISHED,
                RequestStatus.CODE_REQUEST_DENY,
                RequestStatus.CODE_SENT_REQUEST,
                RequestStatus.CODE_IN_BANK, RequestStatus.CODE_OFFER_CREATED,
                RequestStatus.CODE_OFFER_PREPARE,
                RequestStatus.CODE_SENDING_IN_BANK,
            ]
        )

        return {
            'limit': self.get_client_limit(client=client),
            'finished_requests': [{
                'request': {
                    'id': request.id,
                    'request_number': request.request_number,
                },
                'number_in_bank': request.request_number_in_bank,
                'amount': request.required_amount,
                'interval': request.interval,
            } for request in finished_requests],
            'rejected_requests': [{
                'request': {
                    'id': request.id,
                    'request_number': request.request_number,
                },
                'number_in_bank': request.request_number_in_bank,
                'amount': request.required_amount,
                'interval': request.interval,
                'reason': request.bank_reject_reason
            } for request in rejected_requests],
            'requested_requests': [{
                'request': {
                    'id': request.id,
                    'request_number': request.request_number,
                },
                'number_in_bank': request.request_number_in_bank,
                'amount': request.required_amount,
                'interval': request.interval,
            } for request in requested_requests],
            'in_work_requests': [{
                'request': {
                    'id': request.id,
                    'request_number': request.request_number,
                },
                'number_in_bank': request.request_number_in_bank,
                'status': request.status.name,
                'amount': request.required_amount,
                'interval': request.interval,
            } for request in in_work_requests]
        }

    def request_limit(self, request):
        return request.required_amount

    def bank_amount_limit(self, request):
        return self.bank.settings.amount_limit

    def fit_limit(self, request):
        total = (Request.objects.select_related('status', 'offer').filter(
            bank=self.bank,
            status__code='bg_to_client',
            client=request.client,
            offer__contract_date_end__gt=timezone.now()
        ).aggregate(
            total=Sum('offer__amount')
        )['total'] or 0) + request.required_amount

        return total

    def sum_bg(self, request):
        return request.__class__.objects.filter(
            request__status__code=RequestStatus.CODE_FINISHED,
            client=request.client,
            bank=self.bank,
        ).aggregate(sum_amount=Sum('required_amount'))['sum_amount'] or 0

    def change_project_bg(self, request, file=None, message=None):
        return True

    def change_commission(self, request, commission, reason=None, files=None):
        return True

    def check_and_update_status(self, request):
        pass
