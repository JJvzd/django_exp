import base64

from django.core.files.base import ContentFile
from django.utils import timezone

from bank_guarantee.actions import SendOfferAction
from bank_guarantee.models import Request, ExternalRequest, RequestStatus, Offer, Discuss
from base_request.discuss_logic import get_discuss
from base_request.helpers import BeforeSendToBankResult
from base_request.logic.request_log import RequestLogger
from bank_guarantee.bank_integrations.api.base import BaseSendRequest
from bank_guarantee.bank_integrations.moscombank.bank_api.api import MoscombankApi
from cabinet.constants.constants import Target
from files.models import BaseFile
from settings.configs.banks import BankCode
from settings.settings import ENABLE_EXTERNAL_BANK_API
from users.models import Role
from .adapters.new_request import NewRequestAdapter
from .adapters.old_request import OldRequestAdapter
from .job import task_send_new_message
from cabinet.base_logic.printing_forms.adapters.base import get_temp_path


class MoscombankSendRequest(BaseSendRequest):
    update_profile_key = 'update_anketa_date'
    update_post_key = 'update_post_key'
    bank_code = BankCode.CODE_MOSCOMBANK
    enabled = True
    format_date = '%d.%m.%Y %H:%M'
    interval_update = 15
    active_statuses = [
        RequestStatus.CODE_IN_BANK,  # на рассмотрении в банке
        RequestStatus.CODE_SEND_TO_BANK,  # направлена в банк
        RequestStatus.CODE_REQUEST_CONFIRMED,  # Одобрена банком
        RequestStatus.CODE_SENT_REQUEST,  # Запрос
        RequestStatus.CODE_ASK_ON_REQUEST,  # Запрос отработан
        RequestStatus.CODE_CREDIT_REVIEW,  # На рассмотрении в кредитном комитете
        RequestStatus.CODE_SECURITY_REVIEW,  # На рассмотрении у службы безопасности
        RequestStatus.CODE_OFFER_CREATED,  # Предложение подготавливается банком / МФО
        RequestStatus.CODE_OFFER_SENT,  # Банк / МФО отправил предложение
        RequestStatus.CODE_OFFER_BACK,  # Предложение отозвано банком
        RequestStatus.CODE_OFFER_CONFIRM,  # Предложение принято, не оплачено
        RequestStatus.CODE_OFFER_PREPARE,  # Подготавливается банковская гарантия
    ]

    def __init__(self, *args, **kwargs):
        self.enabled = self.bank.settings.send_via_integration
        super(MoscombankSendRequest, self).__init__(*args, **kwargs)

    def integration_enable(self):
        return self.enabled

    @classmethod
    def get_adapter(cls, request):
        if isinstance(request, Request):
            return NewRequestAdapter(request)
        else:
            return OldRequestAdapter(request)

    def init_request(self, request):
        adapter = self.get_adapter(request)
        api = MoscombankApi(adapter)
        try:
            api.update_profile()
            api.update_contact_phone()
            api.update_address()
            api.update_all_accounts()
            api.update_all_licenses()
            api.update_all_persons()
            api.update_chief()
            api.update_all_individual_founder()
            api.update_all_entity_founder()
            api.update_all_beneficiaries()
            api.add_finance()
            type_guarantee_choices = {
                Target.PARTICIPANT: {
                    'add': api.add_guarantee_tender,
                    'update': api.update_guarantee_tender,
                },
                Target.WARRANTY: {
                    'add': api.add_guarantee_quality,
                    'update': api.update_guarantee_quality,
                },
                Target.AVANS_RETURN: {
                    'add': api.add_guarantee_advance,
                    'update': api.update_guarantee_advance,
                },
            }
            if Target.EXECUTION in request.targets:
                if adapter.external_request.external_id is None:
                    external_id = api.add_guarantee_contract()
                else:
                    external_id = api.update_guarantee_contract()
            else:
                if adapter.external_request.external_id is None:
                    external_id = type_guarantee_choices[request.targets[0]]['add']()
                else:
                    external_id = type_guarantee_choices[request.targets[0]]['update']()
            if external_id:
                api.update_all_similar_contracts()
                RequestLogger.log(request, str(api.logs))
                return external_id
            RequestLogger.log(request, str(api.logs))
        except Exception as error:
            RequestLogger.log(request, str(error))
            RequestLogger.log(request, str(api.logs))
            raise error

    def create_request(self, request):
        adapter = self.get_adapter(request)
        api = MoscombankApi(adapter)
        try:
            if adapter.external_request.external_id:
                api.update_all_similar_contracts()
                api.upload_all_document()
                self.update_chat_from_agent(request)
                api.set_status('Новая заявка')
            else:
                api.print_log('Заявка не создана')
                return BeforeSendToBankResult(
                    result=False, reason="Ошибка при отправке в банк"
                )
        except Exception as error:
            RequestLogger.log(request, str(api.logs))
            raise error
        RequestLogger.log(request, str(api.logs))
        return BeforeSendToBankResult(result=True)

    def update_chat_from_agent(self, request):
        discuss = get_discuss(request)
        messages = discuss.messages.filter(
            author__roles__name__in=[Role.AGENT, Role.CLIENT]
        )
        for message in messages:
            self.send_new_message(
                request,
                None,
                author=message.author,
                files=BaseFile.objects.filter(
                    id__in=message.files.all().values_list('file_id', flat=True)
                )
            )

    def send_request(self, request):
        request = Request.objects.get(id=request.id)
        if not ENABLE_EXTERNAL_BANK_API:
            return BeforeSendToBankResult(result=True)

        external_request = ExternalRequest.get_request_data(request, self.bank)
        if external_request and external_request.external_id:
            if request.status.code == RequestStatus.CODE_ASK_ON_REQUEST:
                return self.change_request(request, external_request)
            elif request.status.code == RequestStatus.CODE_OFFER_WAIT_PAID:
                return self.upload_documents(request)
            else:
                return self.additional_action(request)
        else:
            RequestLogger.log(request, 'Сгенерируйте необходимые печатные формы')
            return BeforeSendToBankResult(result=False, reason='Ошибка при отправке банк')

    def additional_action(self, request):
        adapter = self.get_adapter(request)
        api = MoscombankApi(adapter)
        api.upload_all_document()
        self.update_chat_from_agent(request)
        if request.status.code in [
            RequestStatus.CODE_SEND_TO_BANK,
            RequestStatus.CODE_SCORING_FAIL,
        ]:
            api.set_status('Новая заявка')
            RequestLogger.log(request, str(api.logs))
        return BeforeSendToBankResult(result=True)

    def upload_documents(self, request):
        adapter = self.get_adapter(request)
        api = MoscombankApi(adapter)
        api.upload_all_document()
        self.update_chat_from_agent(request)
        api.set_status('Клиентом утверждены макеты, ожидает оплаты')
        RequestLogger.log(request, str(api.logs))
        return BeforeSendToBankResult(result=True)

    def change_request(self, request, external_request):
        adapter = self.get_adapter(request)
        api = MoscombankApi(adapter)
        try:
            self.init_request(request)
            api.upload_all_document()
            api.set_status('Ответ Клиента на запрос Банка')
        except Exception as error:
            RequestLogger.log(request, str(api.logs))
            raise error
        RequestLogger.log(request, str(api.logs))
        return BeforeSendToBankResult(result=True)

    def get_current_status(self, request):
        external_request = request.externalrequest_set.filter(bank=self.bank).first()
        if external_request:
            self.update_status(external_request, force=True)
            return True
        return False

    def update_status(self, external_request: ExternalRequest, update_chat=False,
                      data=None, force=False):
        if not self.bank.settings.update_via_integration:
            return

        if not external_request.external_id or \
                external_request.request.status.code in [RequestStatus.CODE_FINISHED]:
            return
        api = MoscombankApi(self.get_adapter(external_request.request))
        if data is None:
            status = api.get_status()
        else:
            force = True
            status = data

        try:
            action = get_action_for_status(status['description'])
            action = action(api=api)
            if force or action.check_status():
                action.execute()
        except ExceptionAction:
            pass

        RequestLogger.log(external_request.request, str(api.logs))
        if update_chat:
            self.update_chat(external_request.request)

    def download_profile(self, request):
        adapter = self.get_adapter(request)
        api = MoscombankApi(adapter)
        document_list = api.get_document_list()
        profile_doc = next(filter(
            lambda x: x['name'] == 'Анкета-заявление',
            document_list
        ))

        download = api.download_document(profile_doc['id'], profile_doc['type'])
        if not download.get('file'):
            RequestLogger.log(request, str(api.logs))
            return None
        temp_path = get_temp_path('.%s' % download['ext'])
        with open(temp_path, 'wb') as f:
            f.write(base64.b64decode(download['file']))
        RequestLogger.log(request, str(api.logs))
        return temp_path

    def send_new_message(self, request, message, author=None, files=None):
        role = author.client.get_role()
        adapter = self.get_adapter(request)
        api = MoscombankApi(adapter)
        if (role in ['Agent', 'Client']) and message:
            api.push_post(message, is_agent=role == 'Agent')
        if files:
            for file in files:
                api.upload_free_document(file.file.filename, file.id)
        RequestLogger.log(request, str(api.logs))

    def sign_chat(self, request, files):
        task_send_new_message.delay(
            request_id=request.id,
            type='request' if isinstance(request, Request) else 'loan',
            user_id=request.client.user_set.first().id,
            message=None,
            files=files,
        )

    def single_update_chat(self, external_request, data):
        discuss = Discuss.objects.filter(
            request=external_request.request,
            bank=external_request.request.bank
        ).first()
        discuss.add_message(
            external_request.request.bank.get_first_user(),
            message=data['message']
        )
        update_post = external_request.get_other_data_for_key(self.update_post_key) or 0
        external_request.set_other_data_for_key(
            self.update_post_key, update_post + 1)

    def update_chat(self, request):
        adapter = self.get_adapter(request)
        api = MoscombankApi(adapter)
        all_posts = posts = api.get_posts()
        if all_posts:
            update_post = api.adapter.external_request.get_other_data_for_key(
                self.update_post_key
            )
            if update_post and isinstance(update_post, int):
                posts = all_posts[update_post:]
            if len(posts) > 0:
                discuss = Discuss.objects.filter(
                    request=request, bank=request.bank
                ).first()

                for post in posts:
                    discuss.add_message(
                        request.bank.get_first_user(),
                        message=post['message']
                    )
        api.adapter.external_request.set_other_data_for_key(
            self.update_post_key, len(all_posts))
        RequestLogger.log(request, str(api.logs))

    def reject_request(self, request):
        adapter = self.get_adapter(request)
        api = MoscombankApi(adapter)
        api.set_status('Отменена Клиентом')
        RequestLogger.log(request, str(api.logs))


ACTIONS_FOR_STATUS = []


def add_action_for_status(cls):
    ACTIONS_FOR_STATUS.append(cls)
    return cls


class ExceptionAction(Exception):

    def __init__(self, text):
        self.txt = text


def get_action_for_status(status):
    for action in ACTIONS_FOR_STATUS:
        if action.status == status:
            return action
    raise ExceptionAction('Не существующий статус %s' % status)


class ActionForStatus:
    from bank_guarantee.actions import Action
    status = ''
    status_id = None
    _action = Action
    need_status = None
    to_status = None

    def check_status(self):
        return self.request.status.code != self.to_status

    def __init__(self, api: MoscombankApi):
        self.api = api
        self.request = api.adapter.request
        self.user = api.adapter.request.bank.user_set.first()
        self.action = self._action(self.request, self.user)

    def before_set_status(self):
        if self.need_status is not None:
            self.request.status = RequestStatus.objects.get(code=self.need_status)
            self.request.save()

    def execute(self):
        self.before_set_status()
        self.action.execute(params=self.get_params())

    def get_params(self):
        return None


@add_action_for_status
class RequestDeny(ActionForStatus):
    from bank_guarantee.actions import RejectAction
    status = 'Отказ Банка'
    status_id = None
    _action = RejectAction
    need_status = RequestStatus.CODE_IN_BANK
    to_status = RequestStatus.CODE_REQUEST_DENY

    def get_params(self):
        last_post = self.api.get_last_post()
        if isinstance(last_post, dict):
            reason = last_post.get('message')
        else:
            reason = 'Отказ банка'
        return {
            'reason': reason
        }


@add_action_for_status
class InBank(ActionForStatus):
    from bank_guarantee.actions import InProcessAction
    status = 'Принято в рассмотрение Банком'
    status_id = None
    _action = InProcessAction
    need_status = RequestStatus.CODE_SEND_TO_BANK
    to_status = RequestStatus.CODE_IN_BANK

    def get_request_number_in_bank(self):
        return self.request.external_request.first().external_id

    def get_params(self):
        return {
            'request_number_in_bank': self.api.adapter.external_request.external_id
        }


@add_action_for_status
class BankReturn(ActionForStatus):
    from bank_guarantee.actions import SendRequestAction
    status = 'Дополнительный запрос от Банка'
    status_id = None
    _action = SendRequestAction
    need_status = RequestStatus.CODE_IN_BANK
    to_status = RequestStatus.CODE_SENT_REQUEST

    def update_requested_document(self):
        from bank_guarantee.models import RequestedCategory
        doc_list = self.api.get_document_list()
        requested_categories = self.api.adapter.external_request.get_other_data_for_key(
            'requested_categories'
        )
        if requested_categories is None:
            requested_categories = {}
        docs = filter(
            lambda x: x['type'] == 'additional' and
                      x['document_id'] not in requested_categories.keys(),  # noqa
            doc_list
        )
        for doc in docs:
            requested_category = RequestedCategory.objects.create(
                name=doc['name'],
                request=self.api.adapter.external_request.request
            )
            requested_categories[doc['document_id']] = requested_category.id
        self.api.adapter.external_request.set_other_data_for_key(
            'requested_categories', requested_categories
        )

    def execute(self):
        self.update_requested_document()
        super(BankReturn, self).execute()

    def get_request_text(self):
        last_post = self.api.get_last_post()
        if isinstance(last_post, dict):
            reason = last_post.get('message')
        else:
            reason = 'Запрос банка'
        return reason

    def get_params(self):
        return {
            'request_text': self.get_request_text()
        }


@add_action_for_status
class CreditApprove(ActionForStatus):
    from bank_guarantee.actions import ConfirmRequestAction
    status = 'Предварительно одобрено'
    status_id = None
    _action = ConfirmRequestAction
    need_status = RequestStatus.CODE_IN_BANK
    to_status = RequestStatus.CODE_REQUEST_CONFIRMED


@add_action_for_status
class OfferSent(ActionForStatus):
    from bank_guarantee.actions import CreateOfferAction
    status = 'Направлено на согласование макетов'
    status_id = None
    create_action = CreateOfferAction
    send_action = SendOfferAction
    need_status = RequestStatus.CODE_REQUEST_CONFIRMED
    to_status = RequestStatus.CODE_OFFER_SENT

    def get_params_for_create(self):
        commission = self.api.get_status()['commission']
        if not self.request.warranty_to:
            contract_date = self.request.interval_to.strftime('%d.%m.%Y')
        else:
            contract_date = self.request.warranty_to.strftime('%d.%m.%Y')
        data = {
            'amount': self.request.required_amount,  # Сумма БГ
            'commission_bank': commission['total_price_client'],  # Комиссия банка
            'default_commission_bank': commission['bank_price'],  # Стандартная комиссия
            # Понижение/Превышение
            'delta_commission_bank': commission['excess_decrease'] or 0,
            # Срок действия предложения
            'offer_active_end_date': self.request.final_date.strftime('%d.%m.%Y'),

            'contract_date_end': contract_date,  # Cрок действия БГ
            'default_commission_bank_percent': round(
                float(commission['bank_price']) * 365 *
                100 / self.request.interval / float(self.request.required_amount),
                2),
            'commission_bank_percent': round(
                float(commission['total_price_client']) * 365 *
                100 / self.request.interval / float(self.request.required_amount), 2),
        }
        document_list = self.api.upload_document_from_bank()
        for category in Offer.get_categories(self.request.bank, step=1):
            data.update({
                'category_%i' % category.id: self.get_file_for_category(
                    category.id, document_list
                )
            })
        return data

    def get_file_for_category(self, category_id, document_list):
        # сопоставление документов у нас: у их
        choices_documents = {
            1: '2',
            2: '3',
            3: '2',
            4: '1',
        }
        file = list(filter(
            lambda x: x['id'] == choices_documents[category_id],
            document_list
        ))[0]

        return ContentFile(
            base64.b64decode(file['file']),
            name='%s.%s' % (file['name'], file['ext'])
        )

    def create(self):
        action = self.create_action(self.request, self.user)
        action.execute(params=self.get_params_for_create())

    def send(self):
        action = self.send_action(self.request, self.user)
        action.execute(params={})

    def execute(self):
        self.before_set_status()
        self.create()
        self.request = Request.objects.get(id=self.request.id)
        self.send()


@add_action_for_status
class ReOfferSent(OfferSent):
    status = 'Повторное согласование макетов от Банка'


@add_action_for_status
class OfferPaid(ActionForStatus):
    from bank_guarantee.actions import OfferPaidAction
    status = 'Оплата получена, выпуск БГ'
    status_id = None
    _action = OfferPaidAction
    need_status = RequestStatus.CODE_OFFER_CONFIRM
    to_status = RequestStatus.CODE_OFFER_PREPARE


@add_action_for_status
class Finished(ActionForStatus):
    from bank_guarantee.actions import RequestFinishedAction
    status = 'Выдача завершена'
    status_id = None
    _action = RequestFinishedAction
    need_status = RequestStatus.CODE_OFFER_PREPARE
    to_status = RequestStatus.CODE_FINISHED

    def get_params(self):
        data = {
            'contract_number': 'test_number',
            'contract_date': timezone.now().strftime('%d.%m.%Y')
        }
        documents_list = self.api.upload_document_from_bank()
        for category in Offer.get_categories(self.request.bank, step=2):
            data.update({
                'category_%i' % category.id: self.get_file_for_category(
                    category.id, documents_list
                )
            })
        return data

    def get_file_for_category(self, category_id, document_list):
        # сопоставление документов у нас: у их
        choices_documents = {
            1: '2',
            2: '3',
            3: '2',
            4: '1',
        }
        file = list(filter(
            lambda x: x['id'] == choices_documents[category_id],
            document_list
        ))[0]

        return ContentFile(
            base64.b64decode(file['file']),
            name='%s.%s' % (file['name'], file['ext'])
        )
