import pytest

from bank_guarantee.actions import EditAction, RequestActionHandler, SendToBankAction, InProcessAction, \
    RejectAction, SendRequestAction, AskOnRequestAction, ReturnToJobAction, \
    ConfirmRequestAction, CreateOfferAction, SendOfferAction, OfferBackAction, RejectOfferAction, ConfirmOfferAction, \
    RequestFinishedAction, AssignedToAnotherAgentAction
from base_request.actions import Action
from bank_guarantee.models import RequestStatus, Message, Offer, OfferDocument, Request
from .data_for_test_actions import EditDataForTest, DeleteEditData, SendToBankDataForTest, \
    InProcessDataForTest, RejectDataForTest, RejectDataForTest2, EmptyDataForTest, SendRequestDataForTest, \
    CreateOfferDataForTest
from base_request.logic.actions import ActionHandler
from clients.models import Client, Bank, Agent
from tests.conf.generate_request.base import REQUEST_STATUS_ACTIONS, RequestDraftFill
from tests.conf.load_db.load_agent import AGENT_INN, create_agent
from tests.conf.load_db.load_bank import BANK_INN, create_bank
from tests.conf.load_db.load_client import create_client, CLIENT_INN

ACTIONS_TEST = []


def add_action_test(f):
    ACTIONS_TEST.append(f)
    return f


class ActionHandlerTest:
    handler_class = ActionHandler
    action = Action
    data_class = EmptyDataForTest
    status_actions = {}
    check_status_code = None

    @classmethod
    def test_check_status(cls, handler_data=None, **kwargs):
        if cls.check_status_code:
            assert handler_data.request.status.code == cls.check_status_code

    def __init__(self, client, bank):
        self.client = client
        self.bank = bank

    def get_tests_name(self):
        return [name for name in dir(self) if name.startswith('test_')]

    def get_users(self):
        return {
            'client': self.client.user_set.all().first(),
            'agent': self.client.agent_user,
            'bank': self.bank.user_set.all().first()
        }

    def get_data_classes(self, name):
        if isinstance(self.data_class, list):
            return self.data_class
        if isinstance(self.data_class, dict):
            need_data_class = self.data_class.get(
                name,
                self.data_class['default']
            )
            if isinstance(need_data_class, list):
                return need_data_class
            return [need_data_class, ]
        return [self.data_class, ]

    def check_all(self):
        """Проверка всех action с заявкой во всех статусах и пользователей с разными полями"""
        for code, set_status in self.status_actions.items():
            users = self.get_users()
            for role, user in users.items():
                if not user:
                    continue
                for data_class in self.get_data_classes(set_status.get_name()):
                    request = set_status(self.client).get_request()
                    handler_data = data_class(
                        request=request,
                        user=user,
                        bank=self.bank
                    )
                    data = handler_data.get_data()
                    action_handler = self.handler_class(request, user)
                    allow_action = self.action(request, user).validate_access()
                    response = action_handler.call_action(self.action.code, params=data)
                    # Проверка выполнения action
                    assert allow_action == response['result']
                    # Прочие тесты
                    if allow_action:
                        for test_name in self.get_tests_name():
                            getattr(self, test_name)(
                                response=response,
                                handler_data=handler_data,
                            )
                    self.clear(request)
        return self.client, self.bank

    def clear(self, request):
        request.delete()


class RequestActionTest(ActionHandlerTest):
    handler_class = RequestActionHandler
    status_actions = REQUEST_STATUS_ACTIONS


@add_action_test
class EditTest(RequestActionTest):
    action = EditAction
    data_class = {
        'default': EditDataForTest,
        RequestDraftFill.get_name(): [DeleteEditData, ]
    }

    # @staticmethod
    # def test_change_profile(handler_data=None, **kwargs):
    #     data = handler_data.check_profile
    #     equal_data(data, ProfileSerializer(handler_data.request.client.profile).data, path=['profile'])

    # @staticmethod
    # def test_change_quarters(handler_data=None, **kwargs):
    #     if isinstance(handler_data, DeleteEditData):
    #         return
    #     data = handler_data.check_quarters
    #     assert data == QuarterSerializer(
    #         handler_data.request.client.accounting_report.get_quarters_for_fill(),
    #         many=True
    #     ).data

    def clear(self, request):
        super(EditTest, self).clear(request)
        agent = self.client.agent_company
        self.client.delete()
        self.client = create_client(agent_company=agent)


@add_action_test
class SendingInBankTest(RequestActionTest):
    action = SendToBankAction
    data_class = SendToBankDataForTest
    check_status_code = RequestStatus.CODE_SENDING_IN_BANK

    @staticmethod
    def test_change_bank(handler_data=None, **kwargs):
        assert Request.objects.filter(base_request=handler_data.request, bank=handler_data.bank).first()


@add_action_test
class InProcessTest(RequestActionTest):
    action = InProcessAction
    data_class = InProcessDataForTest
    check_status_code = RequestStatus.CODE_IN_BANK

    @staticmethod
    def test_change_number_in_bank(handler_data=None, **kwargs):
        assert handler_data.request.request_number_in_bank == handler_data.get_data['request_number_in_bank']


@add_action_test
class RejectTest(RequestActionTest):
    action = RejectAction
    data_class = [RejectDataForTest, RejectDataForTest2]
    response = "Отказ службы безопасности"
    check_status_code = RequestStatus.CODE_REQUEST_DENY

    @classmethod
    def test_add_discuss(cls, handler_data=None, user=None, **kwargs):
        request = handler_data.request
        discuss = request.discusses.filter(bank=request.bank, agent=request.agent).first()
        message = 'Отклонение заявки по причине: %s' % cls.response
        find_message = Message.objects.filter(
            discuss=discuss,
            author=user,
            message=message,
        )
        assert find_message.first()

    @classmethod
    def test_reject_reason(cls, handler_data=None, **kwargs):
        assert handler_data.request.bank_reject_reason == cls.response


@add_action_test
class AssignedToAnotherAgentTest(RejectTest):
    action = AssignedToAnotherAgentAction
    response = 'Закреплен за другим агентом'
    check_status_code = RequestStatus.CODE_ASSIGNED_TO_ANOTHER_AGENT


@add_action_test
class SendRequestTest(ActionHandlerTest):
    action = SendRequestAction
    data_class = SendRequestDataForTest
    check_status_code = RequestStatus.CODE_SENT_REQUEST

    @staticmethod
    def test_change_message(handler_data=None, user=None, **kwargs):
        request = handler_data.request
        discuss = request.discuss_set.filter(bank=request.bank, agent=request.agent).first()
        find_messages = Message.objects.filter(
            author=user,
            message=handler_data.get_data['request_text'],
            discuss=discuss
        )
        assert find_messages.first()


@add_action_test
class AskOnRequestTest(ActionHandlerTest):
    action = AskOnRequestAction
    check_status_code = RequestStatus.CODE_ASK_ON_REQUEST


@add_action_test
class ReturnToJobTest(ActionHandlerTest):
    action = ReturnToJobAction
    check_status_code = RequestStatus.CODE_IN_BANK


@add_action_test
class ConfirmRequestTest(ActionHandlerTest):
    action = ConfirmRequestAction
    check_status_code = RequestStatus.CODE_REQUEST_CONFIRMED


@add_action_test
class CreateOfferTest(ActionHandlerTest):
    action = CreateOfferAction
    data_class = CreateOfferDataForTest
    check_status_code = RequestStatus.CODE_OFFER_CREATED

    @staticmethod
    def test_create_offer(handler_data=None, **kwargs):
        request = handler_data.request
        offer = Offer.objects.filter(request=request, **handler_data.get_data).first()
        assert offer
        categories = Offer.get_categories(request.bank, step=1)
        for category in categories:
            file_input_name = 'category_%s' % category.id
            assert OfferDocument.objects.filter(
                offer=offer,
                category=category,
            ).first()


@add_action_test
class SendOfferTest(RequestActionTest):
    action = SendOfferAction
    check_status_code = RequestStatus.CODE_OFFER_SENT


@add_action_test
class OfferBackTest(RequestActionTest):
    action = OfferBackAction
    check_status_code = RequestStatus.CODE_OFFER_BACK


@add_action_test
class RejectOfferTest(RequestActionTest):
    action = RejectOfferAction
    check_status_code = RequestStatus.CODE_OFFER_REJECTED


@add_action_test
class ConfirmOfferTest(RequestActionTest):
    action = ConfirmOfferAction
    check_status_code = RequestStatus.CODE_OFFER_CONFIRM

    @staticmethod
    def test_check_other_request(handler_data=None, **kwargs):
        request = handler_data.request
        for request in Request.objects.filter(base_request=request.base_request).exclude(id=request.id):
            if request.has_offer():
                assert request.status.code == RequestStatus.CODE_OFFER_REJECTED


# @add_action_test
# class OfferPaidTest(RequestActionTest):
#     action = OfferPaidAction
#     check_status_code = RequestStatus.CODE_OFFER_PREPARE


@add_action_test
class RequestFinishedTest(RequestActionTest):
    action = RequestFinishedAction
    check_status_code = RequestStatus.CODE_FINISHED


def get_client_and_bank():
    client = Client.objects.filter(inn=CLIENT_INN).first()
    if not client:
        agent_company = Agent.objects.filter(inn=AGENT_INN).first()
        if not agent_company:
            agent_company = create_agent()
        client = create_client(agent_company=agent_company)
    bank = Bank.objects.filter(inn=BANK_INN).first()
    if not bank:
        bank = create_bank()
    return client, bank


@pytest.mark.base_workflow
def test_actions(setup_db):
    client = setup_db['client']
    bank = setup_db['bank']
    for test in ACTIONS_TEST:
        client, bank = test(client, bank).check_all()
