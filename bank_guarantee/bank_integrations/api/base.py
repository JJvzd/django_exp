import os
import traceback

import requests
import ujson
from django.conf import settings
from django.utils.functional import cached_property

from bank_guarantee.models import ExternalRequest
from base_request.helpers import BeforeSendToBankResult
from base_request.logic.request_log import RequestLogger
from clients.models import Bank
from settings.settings import BASE_DOMAIN
from utils.helpers import equal_obj


def push_rocket_chat(text):
    url = os.environ.get('ROCKET_CHAT_HOST_FOR_INTEGRATION_BANK')
    if url:
        requests.post(
            url=url,
            json={
                'text': text,
                'attachments': []
            }
        )


def push_error(return_value=None):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as error:
                request = args[1]
                if isinstance(request, ExternalRequest):
                    request = request.request
                formatted_lines = traceback.format_exc()
                RequestLogger.log(request, {
                    'args': args,
                    'kwargs': kwargs,
                    'traceback': formatted_lines
                })
                if 'cabinet' in BASE_DOMAIN:
                    msg = 'bank: %s ID заявки %i\n\n' % (request.bank.code, request.id)
                    msg += 'args - %s\n' % str(args)
                    msg += 'kwargs - %s\n' % str(kwargs)
                    msg += str(formatted_lines)
                    push_rocket_chat(msg)
                if return_value:
                    return return_value
                raise error

        return wrapper

    return decorator


class BaseSendRequest:
    bank_code = None
    key_status_response = 'status_response'

    @cached_property
    def bank(self):
        return Bank.objects.filter(code=self.bank_code).first()

    def integration_enable(self):
        return True

    def check_enable_api(self):
        return settings.ENABLE_EXTERNAL_BANK_API and self.integration_enable()

    @push_error(return_value=BeforeSendToBankResult(
        result=False,
        reason='Банк отклонил заявку'
    ))
    def send_request(self, request):
        if not self.check_enable_api():
            return BeforeSendToBankResult(result=True)
        external_request = ExternalRequest.get_request_data(request, self.bank)
        if external_request and external_request.external_id:
            return self.change_request(request, external_request)
        else:
            return self.create_request(request)

    def change_request(self, request, external_request):
        return BeforeSendToBankResult(result=True)

    def create_request(self, request):
        return BeforeSendToBankResult(result=True)

    def _update_status(self, external_request, data):
        pass

    def get_request_status_data(self, external_request):
        pass

    def get_external_request(self, request):
        result, created = ExternalRequest.objects.get_or_create(request=request,
                                                                bank=self.bank)
        return result

    @push_error()
    def check_and_update_status(self, request):
        external_request = self.get_external_request(request)
        if self.bank.settings.update_via_integration and external_request:
            response = self.get_request_status_data(external_request)
            if response:
                self.update_status(external_request, response, force=False)

    def get_current_status(self, request):
        external_request = self.get_external_request(request)
        if self.bank.settings.update_via_integration and external_request:
            response = self.get_request_status_data(external_request)
            RequestLogger.log(request, 'Ответ из банка %s: %s' % (
                self.bank_code, ujson.dumps(response)))
            if response:
                self.update_status(external_request, response, force=True)
            return response
        return None

    @push_error()
    def update_status(self, external_request, data, force=False):
        if not equal_obj(data, external_request.get_other_data_for_key(
            self.key_status_response)
        ) or force:
            old_status = external_request.get_other_data_for_key(self.key_status_response)
            external_request.set_other_data_for_key(self.key_status_response, data)
            try:
                self._update_status(external_request, data)
            except Exception as error:
                external_request.set_other_data_for_key(
                    self.key_status_response,
                    old_status
                )
                raise error

    def send_new_message(self, request, message, author=None, files=None):
        pass

    def update_chat(self, request):
        pass

    def sign_chat(self, request, files):
        pass

    def reject_request(self, request):
        pass

    def init_request(self, request):
        pass
