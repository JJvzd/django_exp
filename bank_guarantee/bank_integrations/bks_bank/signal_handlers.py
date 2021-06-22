import logging

from django.dispatch import receiver

from bank_guarantee.send_to_bank_logic.send_to_bank_handler import SendToBankHandler
from bank_guarantee.signals import get_ask_on_query
from settings.configs.banks import BankCode

logger = logging.getLogger('django')


@receiver(get_ask_on_query)
def set_to_bank_after_ask_on_query(sender, request, user, **kwargs):
    if request.bank and request.bank.code == BankCode.CODE_BKS_BANK:
        external_request = request.externalrequest_set.filter(
            bank__code=BankCode.CODE_BKS_BANK
        ).first()
        if external_request.status != 'PendingClient':
            helper = SendToBankHandler(user)
            result = helper.before_send_to_bank(request)
            if not result.result:
                logger.error(result.reason)
