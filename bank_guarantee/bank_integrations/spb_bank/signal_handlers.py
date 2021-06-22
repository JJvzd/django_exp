from constance import config
from django.dispatch import receiver

from bank_guarantee.signals import (
    request_sent_in_bank, finish_request, request_confirm_pay
)
from users.models import User, Role


@receiver(request_sent_in_bank)
def set_number_in_bank(sender, request, wait_sign, **kwargs):
    request.bank_integration.set_number_in_bank(request)


@receiver(finish_request)
def send_offer_to_spb(sender, request, **kwargs):
    request.bank_integration.send_offer_to_bank(request)


@receiver(request_confirm_pay)
def set_issuer_user(sender, request, **kwargs):
    issuer_id = config.SPB_INTEGRATION_DEFAULT_ISSUER
    user = User.objects.filter(id=issuer_id).first()
    if user and user.has_role(Role.BANK_ISSUER):
        request.set_assigned(user, 'Оплата подтверждена')
