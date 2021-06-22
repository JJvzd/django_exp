import pytest
from mock import patch

from bank_guarantee.bank_integrations.absolut_bank.absolut_bank import SendRequest
from bank_guarantee.models import RequestStatus
from bank_guarantee.send_to_bank_logic.send_to_bank_handler import SendToBankHandler
from bank_guarantee.send_to_bank_logic.sending_to_bank_handler import \
    SendingToBanksHandler
from bank_guarantee.tests.test_bank_integrations_api.data_for_absolut import DOCUMENTS, \
    STATUS_FOR_SIGN_REQUEST_LIMIT, LIMIT_CLIENT, LIMIT_MESSAGE, STATUS_SEND_OFFER, \
    STATUS_WAIT_PAID, STATUS_FINISHED
from bank_guarantee.tests.test_bank_integrations_api.mixins import MixinTestApi
from clients.models import Bank, BankCode, Role
from files.views import SignHelpersMixin


class TestAbsolutApi(MixinTestApi):
    sender_class = SendRequest
    code_bank = BankCode.CODE_ABSOLUT

    @patch('bank_guarantee.bank_integrations.api.base.BaseSendRequest.check_enable_api',
           lambda x: True)
    @pytest.mark.django_db
    def test_api(self, rm, setup_db, initial_data_db):
        client = self.get_client(setup_db)
        self.update_bank()
        request = self.get_request(client)
        sender = self.sender_class()
        rm.register_uri(
            'POST',
            url=sender.get_bank_endpoint() + '/order',
            json={"orderId": "test"}
        )
        rm.register_uri(
            'GET',
            url='https://test_absolut_api.ru/doc/types',
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
        rm.register_uri(
            'GET',
            url=sender.get_bank_endpoint() + '/order/test',
            json={'orderId': 'test', 'orderStatus': 'inProcess'}
        )
        sender.get_current_status(request)
        request.refresh_from_db()
        assert request.status.code == RequestStatus.CODE_IN_BANK

        rm.register_uri(
            'GET',
            url=sender.get_bank_endpoint() + '/order/test',
            json=STATUS_FOR_SIGN_REQUEST_LIMIT
        )
        self.mock_file_download(rm, STATUS_FOR_SIGN_REQUEST_LIMIT)
        sender.get_current_status(request)
        request.refresh_from_db()
        assert request.status.code == RequestStatus.CODE_CLIENT_SIGN
        rm.register_uri(
            'PUT',
            url=sender.get_bank_endpoint() + '/order/test',
            json={}
        )
        self.sign_request(request)
        signer = SignHelpersMixin()
        signer.after_sign_request(request, request.client.user_set.first())
        request.refresh_from_db()
        assert request.status.code == RequestStatus.CODE_SEND_TO_BANK
        rm.register_uri(
            'GET',
            url=sender.get_bank_endpoint() + '/order/test',
            json={'orderId': 'test', 'orderStatus': 'inProcess'}
        )
        sender.get_current_status(request)
        request.refresh_from_db()
        assert request.status.code == RequestStatus.CODE_IN_BANK
        rm.register_uri(
            'GET',
            url=sender.get_bank_endpoint() + '/order/test',
            json={'orderId': 'test', 'orderStatus': 'inProcess',
                  'statusDescription': 'Согласование выдачи БГ'}
        )
        rm.register_uri(
            'GET',
            url=sender.get_bank_endpoint() + '/limit?INN=5017117944&OGRN=1185000004309',
            json=LIMIT_CLIENT
        )
        sender.get_current_status(request)
        request.refresh_from_db()
        assert request.get_last_message([Role.BANK,
                                         Role.GENERAL_BANK]) == LIMIT_MESSAGE
        default_commission = 30000
        rm.register_uri(
            'GET',
            url=sender.get_bank_endpoint() + '/order/test',
            json={'orderId': 'test', 'orderStatus': 'inProcess',
                  'statusDescription': 'Согласование выдачи БГ',
                  'commission': default_commission}
        )
        sender.get_current_status(request)
        request.refresh_from_db()
        rm.register_uri(
            'GET',
            url=sender.get_bank_endpoint() + '/order/test',
            json=STATUS_SEND_OFFER
        )
        self.mock_file_download(rm, STATUS_SEND_OFFER)
        sender.get_current_status(request)
        request.refresh_from_db()
        assert request.status.code == RequestStatus.CODE_OFFER_SENT
        assert float(request.offer.default_commission) == default_commission
        assert float(request.offer.commission) == STATUS_SEND_OFFER['commission']
        assert request.offer.offerdocument_set.count() == 2
        request.bank_integration.before_accept_offer(request)
        self.sign_offer(request)
        signer.confirm_offer(request, request.client.user_set.first())
        request.refresh_from_db()
        assert request.status.code == RequestStatus.CODE_OFFER_WAIT_PAID
        rm.register_uri(
            'GET',
            url=sender.get_bank_endpoint() + '/order/test',
            json={'orderStatus': 'InProcess', 'statusDescription': 'Согласование БГ',
                  'orderId': 'test'}
        )
        sender.get_current_status(request)
        request.refresh_from_db()
        assert request.status.code == RequestStatus.CODE_OFFER_WAIT_PAID
        rm.register_uri(
            'GET',
            url=sender.get_bank_endpoint() + '/order/test',
            json=STATUS_WAIT_PAID
        )
        sender.get_current_status(request)
        assert request.status.code == RequestStatus.CODE_OFFER_WAIT_PAID
        rm.register_uri(
            'GET',
            url=sender.get_bank_endpoint() + '/order/test',
            json={'orderStatus': 'InProcess', 'statusDescription': 'Выпуск БГ',
                  'orderId': 'test'}
        )
        sender.get_current_status(request)
        request.refresh_from_db()
        assert request.status.code == RequestStatus.CODE_OFFER_PREPARE
        rm.register_uri(
            'GET',
            url=sender.get_bank_endpoint() + '/order/test',
            json=STATUS_FINISHED
        )
        self.mock_file_download(rm, STATUS_FINISHED)
        sender.get_current_status(request)
        request.refresh_from_db()
        assert request.status.code == RequestStatus.CODE_FINISHED
        assert request.offer.offerdocument_set.count() == 3
