from django_rq import job

from base_request.logic.request_log import RequestLogger
from base_request.tasks import get_request_by_type
from bank_guarantee.bank_integrations.moscombank.bank_api.api import MoscombankApi
from users.models import User


@job
def task_send_new_message(request_id, type, user_id, message=None, files=None):
    author = User.objects.get(id=user_id)
    request = get_request_by_type(request_id, type)
    role = author.client.get_role()
    from bank_guarantee.bank_integrations.moscombank.bank_api.base import (
        MoscombankSendRequest
    )
    adapter = MoscombankSendRequest.get_adapter(request)
    api = MoscombankApi(adapter)
    if (role in ['Agent', 'Client']) and message:
        api.push_post(message, is_agent=role == 'Agent')
    if files:
        for file in files:
            api.upload_free_document(file.file.filename, file.id)
    RequestLogger.log(request, str(api.logs))
