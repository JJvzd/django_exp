import logging

from django.dispatch import receiver

from bank_guarantee.send_to_bank_logic.send_to_bank_handler import get_send_adapter_class
from bank_guarantee.signals import get_ask_on_query

from settings.configs.banks import BankCode


LIMIT_CHARS_IN_NUMBER = 6

logger = logging.getLogger('django')


@receiver(get_ask_on_query)
def send_to_bank_after_ask_on_query(sender, request, user, **kwargs):
    if request.bank and request.bank.code == BankCode.CODE_MOSCOMBANK:
        adapter = get_send_adapter_class(request=request)(
            user=user
        )
        result = adapter.send_via_bank_integration(request)
        if not result.result:
            logger.error(result.reason)
