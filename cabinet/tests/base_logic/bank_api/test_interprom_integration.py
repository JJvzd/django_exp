import pytest


@pytest.mark.django_db
def test_send_to_bank(initial_data_db, settings):
    pass  # TODO: сделать тесты на основе данных с боевого
    # settings.ENABLE_EXTERNAL_BANK_API = True
    # request = create_request(bank=Bank(code=BankCode.CODE_INTER_PROM_BANK))
    # request.bank.settings.send_via_integration = True
    # request.bank.settings.save()
    # api = SendRequest()
    # api.send_request(request=request)
    # assert ExternalRequest.objects.filter(request=request).exists()