import pytest
from mock import patch

from bank_guarantee.bank_integrations.bks_bank.bank_api import SendRequest
from bank_guarantee.models import RequestStatus
from bank_guarantee.send_to_bank_logic.send_to_bank_handler import SendToBankHandler
from bank_guarantee.send_to_bank_logic.sending_to_bank_handler import \
    SendingToBanksHandler
from bank_guarantee.tests.test_bank_integrations_api.data_for_bks import DOCUMENTS
from bank_guarantee.tests.test_bank_integrations_api.mixins import MixinTestApi
from clients.models import BankCode


class TestBKSApi(MixinTestApi):
    sender_class = SendRequest
    code_bank = BankCode.CODE_BKS_BANK

    @patch('bank_guarantee.bank_integrations.api.base.BaseSendRequest.check_enable_api',
           lambda x: True)
    @pytest.mark.django_db
    def test_api(self, rm, setup_db, initial_data_db):
        client = self.get_client(setup_db)
        self.update_bank()
        request = self.get_request(client)
        sender = SendRequest()
        rm.register_uri(
            'POST',
            url=sender.get_bank_endpoint() + '/order',
            json={"orderId": "test"}
        )
        rm.register_uri(
            'GET',
            url='https://test_bks_api.ru/doc/types',
            json=DOCUMENTS
        )
        helper = SendingToBanksHandler(request.agent_user)
        helper.send_to_many_banks(
            request,
            [self.bank]
        )
        request.refresh_from_db()
        assert request.status.code == RequestStatus.CODE_SENDING_IN_BANK
        helper = SendToBankHandler(request.agent_user)
        helper.start_send_to_bank(request)
        request.refresh_from_db()
        assert request.status.code == RequestStatus.CODE_SEND_TO_BANK
        assert request.externalrequest_set.first().external_id == 'test'
