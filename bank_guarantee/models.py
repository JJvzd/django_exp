import json
import logging

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from multiselectfield import MultiSelectField
from sentry_sdk import capture_exception

from bank_guarantee.user_stories import validate_request
from base_request.models import (
    AbstractRequest, AbstractRequestStatus, AbstractRequestHistory,
    AbstractDiscuss, AbstractMessage, AbstractMessageFile, AbstractPrintForm,
    BankDocumentType, AbstractOfferPrintForm, AbstractRequestDocument,
    AbstractOfferDocumentCategory, AbstractOffer, AbstractOfferDocument,
    AbstractRequestComment, AbstractExternalRequest, AbstractRequestLog,
    AbstractPrintFormRule
)
from cabinet.constants.constants import FederalLaw, Target
from cabinet.models import WorkRule
from calculator.models import CalculatorRule
from calculator.serializers import CalculatorRuleSerializer
from clients.models import Bank
from clients.models.agents import Agent
from clients.models.clients import Client
from common.excel import BGCalculator
from common.helpers import get_month_text
from dynamic_forms.logic.fields import config_field, get_class_for_field
from dynamic_forms.logic.helpers import DictClass
from files.models import BaseFile
from settings.configs.banks import BankCode
from settings.configs.money import MoneyTypes
from users.models import Role, User
from utils.helpers import generate_log_tags

logger = logging.getLogger('django')


class RequestStatus(AbstractRequestStatus):
    CODE_ASSIGNED_TO_ANOTHER_AGENT = 'another_agent'
    CODE_FINISHED = 'bg_to_client'
    CODE_OFFER_PREPARE = 'bg_prepare'
    CODE_OFFER_CONFIRM = 'offer_paid_wait'
    CODE_CLIENT_SIGN = 'client_sign'
    CODE_SCORING_DENY = 'scoring_deny'
    CODE_BG_CLAIM = 'bg_claim'
    CODE_CREDIT_REVIEW = 'credit_review'
    CODE_SECURITY_REVIEW = 'security_review'
    CODE_SENDING_IN_BANK = 'sending_in_bank'
    CODE_VERIFICATION = 'verification'
    CODE_VERIFIER_REQUIRE_MORE_INFO = 'verifier_require_more_info'
    CODE_DENY_BY_VERIFIER = 'deny_by_verifier'

    def __str__(self):
        return '%s %s' % (self.id, self.name)

    class Meta:
        ordering = ['-id', ]
        verbose_name = 'Статус заявки'
        verbose_name_plural = 'Статус заявки'


class ContractPlacementWay:
    """
    Способ размещения государственного (муниципального) заказ
    """
    COMPETITION = 'competition'
    AUCTION = 'auction'
    ELECTRONIC_AUCTION = 'electronic_auction'
    CLOSED_BIDDING = 'closed_bidding'
    OTHER = 'other'
    CHOICES = (
        (COMPETITION, 'Конкурс'),
        (AUCTION, 'Аукцион'),
        (ELECTRONIC_AUCTION, 'Аукцион в электронной форме'),
        (CLOSED_BIDDING, 'Закрытые торги (закупки)'),
        (OTHER, 'Иное'),
    )


class ContractType:
    STATE = 'state'
    MUNICIPAL = 'municipal'
    COMMERCIAL = 'commercial'
    CHOICES = (
        (STATE, 'Государственный'),
        (MUNICIPAL, 'Муниципальный'),
        (COMMERCIAL, 'Коммерческий'),
    )


class RequestPrintForm(AbstractPrintForm):
    bank = models.ForeignKey(to=Bank, null=True, blank=True, on_delete=models.CASCADE)
    banks = models.ManyToManyField(Bank, related_name='allowed_print_forms')

    class Meta:
        verbose_name = 'печатная форма'
        verbose_name_plural = 'печатные формы'


class RequestPrintFormRule(AbstractPrintFormRule):
    print_form = models.ForeignKey(
        to=RequestPrintForm, on_delete=models.CASCADE, related_name='rules',
        verbose_name='Печатная форма'
    )


class Request(AbstractRequest):
    tmp_manager = models.ForeignKey(
        to='users.User', blank=True, null=True, on_delete=models.SET_NULL,
        related_name='request_managers', verbose_name="Временный менеджер"
    )
    have_additional_requirement = models.BooleanField(
        verbose_name='Банковская гарантия предоставляется по форме Бенефициара',
        default=False)
    additional_requirement = models.BooleanField(
        verbose_name='Требования к БГ', default=False
    )
    suggested_price_amount = models.DecimalField(
        verbose_name='Предложенная вами цена контракта в рублях',
        max_digits=20, decimal_places=2, default=0
    )
    suggested_price_percent = models.DecimalField(
        verbose_name='Предложенная вами цена контракта в процентнах',
        max_digits=5, decimal_places=2, default=0
    )
    procuring_amount = models.DecimalField(
        verbose_name='Размер обеспечения исполнения контракта, руб.',
        max_digits=16, decimal_places=2, blank=True, null=True
    )
    prepaid_expense_amount = models.DecimalField(
        verbose_name='Размер аванса',
        max_digits=16, decimal_places=2, blank=True, null=True
    )
    downpay = models.BooleanField(
        verbose_name='Наличие бесспорного списания', default=False
    )
    term_of_work_to = models.DateField(
        verbose_name='Срок выполнения работ/услуг',
        blank=True, null=True
    )
    term_of_work_from = models.DateField(
        verbose_name='Срок выполнения работ/услуг',
        blank=True, null=True
    )
    final_date = models.DateField(
        verbose_name='Крайний срок выдачи', blank=True, null=True
    )

    contract_type = models.CharField(
        max_length=20, choices=ContractType.CHOICES, blank=True, null=True,
        verbose_name='Контракт государственный или муниципальный'
    )
    placement_way = models.CharField(
        max_length=20, choices=ContractPlacementWay.CHOICES, blank=True, null=True,
        verbose_name='Способ размещения государственного (муниципального) заказа'
    )
    placement_way_other = models.CharField(max_length=1000, blank=True, null=True)
    protocol_number = models.CharField(
        verbose_name='Номер', max_length=255, blank=True, null=True
    )
    protocol_date = models.DateField(verbose_name='Дата', blank=True, null=True)
    protocol_lot_number = models.CharField(
        verbose_name='№ лота', max_length=255, blank=True, null=True
    )
    protocol_territory = models.TextField(
        verbose_name="Территория производства работ / выполнения услуг по контракту",
        blank=True, null=True
    )

    delivery_email = models.CharField(
        verbose_name='Email получателя', max_length=255, blank=True, null=True
    )
    delivery_dop_phone = models.CharField(
        verbose_name='Дополнительный телефон получателя',
        max_length=255, blank=True, null=True
    )

    warranty_from = models.DateField(
        verbose_name='Гарантийные обязательства c',
        blank=True, null=True
    )
    warranty_to = models.DateField(
        verbose_name='Гарантийные обязательства по',
        blank=True, null=True
    )
    interval_from = models.DateField(
        verbose_name='Срок банковской гарантии c', blank=True, null=True
    )
    interval_to = models.DateField(
        verbose_name='Срок банковской гарантии до', blank=True, null=True
    )
    interval = models.IntegerField(
        verbose_name='Срок банковской гарантии (в днях)', blank=True, null=True
    )

    status = models.ForeignKey(
        RequestStatus, on_delete=models.SET_NULL, verbose_name='Текущий статус',
        blank=True, null=True
    )

    banks_commissions = models.TextField(blank=True, null=True)

    is_big_deal = models.BooleanField(
        verbose_name='Являлась ли сделка большой', default=False
    )

    need_bank = models.BooleanField(
        verbose_name='Требуются действия банка', default=False
    )
    power_of_attorney = models.BooleanField(
        verbose_name='Заполненно по доверенности', default=False
    )
    experience_general_contractor = models.BooleanField(
        verbose_name=(
            "Есть исполненные государственные контракты в качестве"
            "генподрядчика в рамках законов"
            "№ 94-ФЗ, 44-ФЗ, 223-ФЗ или 185-ФЗ"
        ),
        default=False
    )

    bank_reject_reason = models.CharField(
        verbose_name='Причина отклонения заявки банком',
        max_length=300, blank=True, null=True
    )
    targets = MultiSelectField(
        verbose_name='Цели', choices=Target.CHOICES, default='', max_length=200
    )
    assigned = models.ForeignKey(
        to='users.User', on_delete=models.SET_NULL, blank=True, null=True,
        related_name='assigned_requests'
    )
    verifier = models.ForeignKey(
        to='users.User', on_delete=models.SET_NULL, blank=True, null=True,
        related_name='verifier_requests'
    )
    additional_status = models.CharField(
        max_length=100, verbose_name='Подстатус', default='', blank=True
    )

    creator_name = models.CharField(max_length=250, blank=True, null=True)
    creator_phone_additional = models.CharField(max_length=10, blank=True, null=True)
    creator_phone = models.CharField(max_length=20, blank=True, null=True)
    creator_email = models.CharField(max_length=150, blank=True, null=True)

    sign_link_sent = models.BooleanField(
        verbose_name='Отправлялась ли ссылка на подписание (после верификации)',
        default=False
    )

    def get_last_message(self, roles: list):
        message = Message.objects.filter(
            discuss__request=self,
            author__roles__name__in=roles
        ).last()
        return message.message if message else None

    @cached_property
    def bank_integration(self):
        if self.bank:
            return self.bank.bank_integration
        else:
            cls = import_string(
                'bank_guarantee.bank_integrations.adapter.BaseBankAdapter')
            return cls(bank=self.bank)

    def get_offer_additional_fields(self):
        result = []
        if self.bank:
            for field in OfferAdditionalDataField.objects.filter(
                banks__code=self.bank.code
            ).iterator():
                result.append(config_field(field, request=self))
        return result

    @cached_property
    def rewards_from_work_rule(self):
        if self.bank is None:
            return None
        return WorkRule.get_rewards(self.bank_id, self.targets, self.required_amount)

    @cached_property
    def work_rule(self):
        if self.bank is None:
            return None
        return WorkRule.get_work_rule(self.bank_id, self.targets, self.required_amount)

    @cached_property
    def agent_reward_percent(self):
        return self.rewards_from_work_rule[0]

    @cached_property
    def agent_reward(self):
        reward = float(self.offer.commission) * self.agent_reward_percent / 100
        if self.offer.delta_commission > 0:
            kv = 0
            try:
                kv = float(self.rewards_from_work_rule[1])
            except Exception:
                pass
            reward += float(self.offer.delta_commission) * kv / 100
        return round(reward, 2)

    def get_current_bank_commission(self):
        if self.bank_id:
            return self.get_commission_for_bank_code(self.bank.code)

    def get_last_comments(self, limit=None):
        comments = RequestComment.objects.filter(
            request=self.base_request
        ).order_by('-id')
        if limit:
            comments = comments[:limit]
        return comments

    def add_comment(self, comment):
        all_requests = self.get_clones(exclude_self=False)
        for request in all_requests:
            request.save_last_comment(comment)
        return RequestComment.objects.create(
            request=self.base_request,
            text=comment,
            bank=self.bank,
        )

    @property
    def validate_request(self):
        return validate_request(self)

    def get_number(self) -> str:
        return str(self.request_number)

    def request_suffix(self) -> str:
        return ''.join(
            [Target.TARGETS_ABBREVIATION.get(target) for target in self.targets])

    def update_singed(self, user):
        documents_exists = self.requestdocument_set.exists()
        self.is_signed = documents_exists and all(
            [file.file.sign_set.filter(author_id=user.client_id).exists() for file in
             self.requestdocument_set.all()])
        self.save()
        return self.is_signed

    def calculate_commission(self):
        allowed_laws = [
            FederalLaw.LAW_44, FederalLaw.LAW_223, FederalLaw.LAW_185, FederalLaw.LAW_615
        ]
        if self.required_amount and self.interval and \
            self.tender.federal_law in allowed_laws:

            calculator = BGCalculator()
            default_commission = calculator.calculate(
                amount=self.required_amount,
                interval=self.interval,
                law=self.tender.federal_law,
                guarantee_type=set(self.targets),
            )

            banks_commissions = {}
            for d in default_commission:
                banks_commissions[d['bank_code']] = d
            self.banks_commissions = json.dumps(banks_commissions)
            self.save()
            return default_commission
        return []

    def get_clones(self, exclude_self=True):
        requests = self.__class__.objects.filter(base_request=self.base_request)
        if exclude_self:
            return requests.exclude(id=self.id)
        return requests

    def save(self, *args, **kwargs):
        # Высчитываем Срок банковской гарантии (в днях)
        if not self.status:
            self.status = RequestStatus.objects.get(code=RequestStatus.CODE_DRAFT)
        if not self.status_changed_date:
            self.status_changed_date = timezone.now()

        if self.interval_from and self.interval_to:
            self.interval = (self.interval_to - self.interval_from).days
        if not self.request_number:
            from cabinet.models import System
            request_number = System.get_setting('request_number')
            if not request_number:
                try:
                    request_number = Request.objects.order_by('-id').first().id
                except Exception as e:
                    logger.exception(e)
                    request_number = 0
            request_number += 1
            System.set_settings('request_number', request_number)
            self.request_number = request_number
        return super(Request, self).save(*args, **kwargs)

    def set_status(self, new_status_code, force=False):
        from .status_classes import get_status_class
        klass = get_status_class(new_status_code)
        status_machine_instance = klass(self)
        try:
            logger.info("Установка статуса %s=>%s %s" % (
                self.status.code if self.status else 'None', new_status_code,
                generate_log_tags(request=self)))
            status_machine_instance.run_change_status(force=force)
            return True
        except Exception as e:
            capture_exception(e)
            logger.exception(e)
            if settings.DEBUG:
                raise e
            return False

    def generate_print_forms(self):
        from cabinet.base_logic.printing_forms.generate import RequestPrintFormGenerator
        helper = RequestPrintFormGenerator()
        helper.generate_print_forms(self)
        user = self.client.user_set.all().first()
        if user:
            self.update_singed(user)

    def generate_request_number(self):
        counter = self.__class__.objects.filter(base_request=self).count()
        base_id = int(str(self.request_number).split('-')[0])
        while True:
            request_number = "%s-%s" % (base_id, counter)
            if self.__class__.objects.filter(request_number=request_number).exists():
                counter += 1
                continue
            return request_number

    def get_commission_for_bank_code(self, bank_code):
        if self.banks_commissions and self.bank:
            banks_commissions = json.loads(self.banks_commissions)
            if isinstance(banks_commissions, list):
                banks_commissions = {
                    el['bank_code']: el for el in banks_commissions
                }
                self.banks_commissions = banks_commissions
                self.save()
            q = Q()
            for target in self.targets:
                q &= Q(targets__contains=target)
            calculator = CalculatorRule.objects.filter(
                calculator__credit_organization_code=bank_code,
                law=self.tender.federal_law).filter(q).last()
            data = banks_commissions.get(bank_code, None)
            if data:
                serializer = CalculatorRuleSerializer(calculator)
                data['calculator'] = serializer.data
            return data

    def has_offer(self):
        try:
            return True if self.offer else False
        except Exception:
            return False

    @property
    def avg_sum(self):
        result = 0
        if self.interval:
            result = float(self.required_amount) / (self.interval / 30.5)
        return result

    @property
    def avg_bgs(self):
        result = 0
        if self.interval:
            result = self.interval / self.required_amount
        return result

    @property
    def avg_2110(self):
        # $last_quarter->getValue(2110) / 6,
        result = 0
        return result

    @property
    def has_avans(self):
        return bool(self.prepaid_expense_amount)

    @cached_property
    def calculate_commission_of_bank(self):
        calc = BGCalculator()
        result = calc.calculate(
            amount=float(self.required_amount),
            interval=int(self.interval),
            law=self.tender.federal_law,
            guarantee_type=self.targets
        )
        return result

    def get_allowed_assigned_users(self):
        from users.models import User
        users = User.objects.none()
        if self.bank and self.bank == BankCode.CODE_SPB_BANK:
            users = self.bank.user_set.all()
        elif self.bank:
            users = self.bank.user_set.all()
        return users

    def set_assigned(self, user, reason):
        self.assigned = user
        self.requestassignedhistory_set.create(assigner=user, reason=reason)
        self.save()

    def generate_rating(self, bank=None):
        if not bank:
            bank = self.bank

            from clients.models import BankRating
            rating = BankRating.objects.filter(bank=bank).first()
            if rating:
                return rating.get_rating(self)
        return None

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'


class RequestAssignedHistory(models.Model):
    request = models.ForeignKey(to=Request, on_delete=models.CASCADE)
    assigner = models.ForeignKey(to='users.User', on_delete=models.CASCADE)
    reason = models.TextField(blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)


class RequestedCategory(models.Model):
    """Модель запрашиваемых документов"""
    name = models.CharField(
        max_length=300, verbose_name='Наименование запрашиваемого документа'
    )
    request = models.ForeignKey(to=Request, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now=True)


class RequestDocument(AbstractRequestDocument):
    request = models.ForeignKey(to=Request, on_delete=models.CASCADE)
    print_form = models.ForeignKey(
        RequestPrintForm, on_delete=models.SET_NULL, blank=True, null=True
    )
    requested_category = models.ForeignKey(
        to=RequestedCategory, on_delete=models.CASCADE, blank=True, null=True
    )

    class Meta:
        unique_together = (('request', 'file'),)


class ClientDocument(models.Model):
    client = models.ForeignKey(to=Client, on_delete=models.CASCADE)
    file = models.ForeignKey(to=BaseFile, on_delete=models.CASCADE)
    category = models.ForeignKey(BankDocumentType, on_delete=models.CASCADE)

    def __str__(self):
        return '%s for %s' % (self.client, self.category)

    class Meta:
        verbose_name = 'Документ клиента'
        verbose_name_plural = 'Документы клиентов'


class RequestHistory(AbstractRequestHistory):
    request = models.ForeignKey(to=Request, on_delete=models.CASCADE)
    status = models.ForeignKey(
        to='RequestStatus', on_delete=models.SET_NULL, null=True, blank=True
    )


class Discuss(AbstractDiscuss):
    request = models.ForeignKey(
        to=Request, on_delete=models.CASCADE, related_name='discusses'
    )
    bank = models.ForeignKey(
        to='clients.Bank', on_delete=models.CASCADE, blank=True, null=True
    )

    def can_write(self, user):
        company = user.client.get_actual_instance
        if isinstance(company, Bank):
            return self.bank == company
        if isinstance(company, Agent):
            if user.has_role(Role.SUPER_AGENT):
                return True
            if user.has_role(Role.VERIFIER):
                return True
            return self.agent == company
        if isinstance(company, Client):
            return self.request.client == company
        return False

    def add_message(self, author, message=None, files=None, notification_name=None,
                    files_id=None):
        base_files = []
        if message or files:
            request_message = Message.objects.create(
                discuss=self,
                message=message or '',
                author=author
            )
            if files:
                for file in files:
                    base_file = BaseFile.objects.create(
                        file=file,
                        author_id=author.client_id
                    )
                    base_files.append(base_file)
                    MessageFile.objects.create(
                        message=request_message,
                        file=base_file
                    )
            if files_id:
                for id in files_id:
                    base_file = BaseFile.objects.get(pk=id)
                    base_files.append(base_file)
                    MessageFile.objects.create(
                        message=request_message,
                        file=base_file
                    )
            self.request.bank_integration.new_message_in_discuss(
                self.request, message,
                author=author,
                files=base_files
            )
        if not notification_name:
            if not self.request.bank:
                notification_name = 'discuss_agent'
            roles_notifications = {
                'Client': 'client_send_message',
                'Agent': 'agent_send_message',
                'Bank': 'bank_send_message',
                'MFO': 'bank_send_message',
            }
            if not notification_name:
                notification_name = roles_notifications.get(author.client.get_role())

        params = self.request.collect_notification_parameters()
        params.update({
            'discuss': self,
            'discuss_message': message,
            'verifier': self.request.verifier
        })
        from notification.base import Notification
        Notification.trigger(notification_name, params=params)


class Message(AbstractMessage):
    discuss = models.ForeignKey(to=Discuss, on_delete=models.CASCADE,
                                related_name='messages')


class MessageFile(AbstractMessageFile):
    message = models.ForeignKey(to=Message, on_delete=models.CASCADE,
                                related_name='files')


class OfferAdditionalData(models.Model):
    offer = models.ForeignKey(to='Offer', on_delete=models.CASCADE)
    field = models.ForeignKey('OfferAdditionalDataField', on_delete=models.CASCADE)
    value = models.CharField(max_length=1000)

    @property
    def handler_field(self):
        return get_class_for_field(self.field, request=self.offer.request)

    def get_value(self):
        return self.handler_field.get_value(self.value)

    def get_full_value(self):
        return self.handler_field.get_full_value(self.value)

    def save_value(self, value):
        self.value = self.handler_field.from_value(value)
        self.save()

    class Meta:
        unique_together = (('field', 'offer'),)


class OfferAdditionalDataField(models.Model):
    banks = models.ManyToManyField(to='clients.Bank',
                                   related_name='offer_additional_fields')
    field_name = models.CharField(max_length=100)
    label = models.CharField(max_length=250, default='', blank=False)
    default_value = models.CharField(max_length=1000)
    config = models.TextField(default='{}')

    def get_full_value(self, request):
        if request.has_offer():
            offer_additional_data = request.offer.offeradditionaldata_set.filter(
                field=self
            ).first()
            if offer_additional_data:
                return offer_additional_data.get_full_value()
        handler_field = get_class_for_field(self, request=request)
        return handler_field.get_full_value(self.default_value)

    def get_value(self, request):
        if request.has_offer():
            offer_additional_data = request.offer.offeradditionaldata_set.filter(
                field=self
            ).first()
            if offer_additional_data:
                return offer_additional_data.get_value()
        handler_field = get_class_for_field(self, request=request)
        return handler_field.get_value(self.default_value)

    def save_value(self, request, value):
        offer_additional, create = request.offer.offeradditionaldata_set.get_or_create(
            field=self
        )
        offer_additional.save_value(value)


class Offer(AbstractOffer):
    amount = models.DecimalField(verbose_name='Сумма БГ', max_digits=16, decimal_places=2)
    request = models.OneToOneField(
        Request, on_delete=models.CASCADE, verbose_name='Заявка', related_name='offer'
    )
    bank = models.ForeignKey(
        Bank, verbose_name='Банк', on_delete=models.CASCADE, blank=True, null=True
    )
    offer_active_end_date = models.DateField(
        verbose_name='Срок действия предложения', blank=True, null=True
    )
    currency = models.CharField(
        verbose_name='Валюта кредита / обязательства', max_length=300,
        choices=MoneyTypes.CHOICES, default=MoneyTypes.TYPE_RUB
    )

    contract_date_end = models.DateField(
        verbose_name='Срок действия БГ', blank=True, null=True
    )
    contract_number = models.CharField(
        verbose_name='№ договора между Принципалом и Клиентом',
        max_length=250, blank=True, null=True
    )
    contract_date = models.DateField(verbose_name='Дата договора', blank=True, null=True)

    registry_number = models.CharField(
        verbose_name='Реестровый номер', max_length=250, blank=True, null=True
    )

    commission = models.DecimalField(
        verbose_name='Коммиссия', max_digits=16, decimal_places=2, default=0
    )
    default_commission = models.DecimalField(
        verbose_name='Стандартная комиссия', max_digits=16, decimal_places=2, default=0
    )
    delta_commission = models.DecimalField(
        verbose_name='Превышение/Понижение комиссии',
        max_digits=16, decimal_places=2, default=0
    )
    reduction_agent = models.DecimalField(
        verbose_name='Превышение/снижение от агента', max_digits=16,
        decimal_places=2, default=0
    )

    # _bank - это означает что эти поля для банка
    commission_bank = models.DecimalField(
        verbose_name='Коммиссия', max_digits=16, decimal_places=2, default=0
    )
    default_commission_bank = models.DecimalField(
        verbose_name='Стандартная комиссия', max_digits=16, decimal_places=2, default=0
    )
    default_commission_bank_percent = models.DecimalField(
        verbose_name='Стандартная комиссия, %', max_digits=16,
        decimal_places=2, default=0
    )
    delta_commission_bank = models.DecimalField(
        verbose_name='Превышение/Понижение комиссии', max_digits=16,
        decimal_places=2, default=0
    )
    commission_bank_percent = models.DecimalField(
        verbose_name='Комиссия, %', max_digits=16, decimal_places=2, default=0
    )
    reduction_bank = models.DecimalField(
        verbose_name='Снижение/корректировка за счет банка', max_digits=16,
        decimal_places=2, default=0
    )

    created = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated = models.DateTimeField(
        auto_now=True, verbose_name='Время последнего изменения объекта'
    )
    is_signed = models.BooleanField(default=False)

    require_insurance = models.BooleanField(default=False)

    # дополнительные поля
    ruchnaya_korrect = models.CharField(
        max_length=250, default='', blank=True, verbose_name='Ручная корректировка'
    )
    kv_previsheniya = models.DecimalField(
        max_digits=20, decimal_places=2, default=0, blank=True,
        verbose_name='КВ Превышения'
    )

    @cached_property
    def additional_fields(self):
        return self.request.bank.offer_additional_fields.all()

    @cached_property
    def get_additional_data(self):
        return {
            field.field_name: field.get_value(
                self.request
            ) for field in self.additional_fields
        }

    @cached_property
    def full_additional_data(self):
        return DictClass(**{
            field.field_name: field.get_full_value(
                self.request
            ) for field in self.additional_fields
        })

    def get_additional_value(self, field_name):
        field = self.additional_fields.filter(field_name=field_name).first()
        return field.get_value(self.request)

    def save_additional_data(self, field_name, value):
        field = self.additional_fields.filter(field_name=field_name).first()
        field.save_value(self.request, value)

    def update_signed(self, user):
        file_signs = []
        for file in self.offerdocument_set.all():
            file_signs.append(
                file.file.sign_set.filter(author_id=user.client_id).exists() and
                file.file.separatedsignature_set.filter(author_id=user.client_id)
            )
        self.is_signed = all(file_signs)
        self.save()
        return self.is_signed

    def generate_template_forms(self):
        templates = self.get_templates()
        today = timezone.now()
        for template in templates:
            context = {  # noqa: F841
                'offer': self,
                'day': today.day,
                'month': today.strftime('%m'),
                'month_text': get_month_text(today.strftime('%m')).lower(),
                'year': today.year
            }

    def update_agent_commissions(self):
        calculator_class = self.request.bank_integration.get_calculator_commission_class()

        default_commission, delta_commission, commission = calculator_class.calculate(
            self)
        self.default_commission = default_commission
        self.delta_commission = delta_commission
        self.commission = commission

    @classmethod
    def get_categories(cls, bank, step=None, has_offer=False):
        """

        :param has_offer:
        :param Bank bank:
        :param int step:
        :return:
        """
        categories = bank.bankofferdocumentcategory_set.filter(category__active=True)
        if not has_offer:
            categories = categories.filter(print_form__isnull=True)
        if step:
            categories = categories.filter(category__step=step)
        result = []
        for category in categories.order_by('category__order'):
            result.append(category.category)
        return result

    def __str__(self):
        return '%s' % self.id

    def generate_print_forms(self, step=None, exclude_categories=None):
        from cabinet.base_logic.printing_forms.generate import OfferPrintGenerator
        categories = self.get_categories(self.request.bank, step=step, has_offer=True)
        if exclude_categories:
            categories = list(
                filter(lambda x: x.id not in exclude_categories, categories))
        for category in categories:
            print_form = BankOfferDocumentCategory.objects.filter(
                category=category, bank=self.request.bank).first().print_form
            if print_form:
                OfferPrintGenerator().generate_print_form(self.request, print_form)

    class Meta:
        ordering = ['-id', ]
        verbose_name = 'Предложение заявки'
        verbose_name_plural = 'Предложения заявок'

    def get_templates(self):
        return []


class OfferPrintForm(AbstractOfferPrintForm):
    class Meta:
        abstract = False
        verbose_name = 'печатная форма предложения'
        verbose_name_plural = 'печатные формы предложений'


class OfferTemplate(models.Model):
    name = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    bank = models.ForeignKey(to=Bank, on_delete=models.CASCADE, blank=True, null=True)


class OfferTemplateDocument(models.Model):
    offer = models.ForeignKey(to=Offer, on_delete=models.CASCADE)
    template = models.ForeignKey(to=OfferTemplate, on_delete=models.CASCADE)
    file = models.ForeignKey(to=BaseFile, on_delete=models.CASCADE)


class OfferDocumentCategory(AbstractOfferDocumentCategory):
    pass


class BankOfferDocumentCategory(models.Model):
    bank = models.ForeignKey(
        to='clients.Bank', verbose_name='Банк', on_delete=models.CASCADE
    )
    category = models.ForeignKey(
        to='OfferDocumentCategory', verbose_name='Категория', on_delete=models.CASCADE
    )
    print_form = models.ForeignKey(
        to=OfferPrintForm, verbose_name='Печатная форма', on_delete=models.SET_NULL,
        blank=True, null=True
    )

    def __str__(self):
        return '%s -> %s' % (self.bank, self.category)

    class Meta:
        verbose_name = 'Привязка банка к категории документов предложения'
        verbose_name_plural = 'Привязки банка к категории документов предложения'


class OfferDocument(AbstractOfferDocument):
    offer = models.ForeignKey(to=Offer, on_delete=models.CASCADE)
    category = models.ForeignKey(
        to=OfferDocumentCategory, on_delete=models.PROTECT, blank=True, null=True
    )


class ExternalRequest(AbstractExternalRequest):
    request = models.ForeignKey(to=Request, on_delete=models.CASCADE)
    bank = models.ForeignKey(to='clients.Bank', on_delete=models.CASCADE)


class DocumentLinkToPerson(models.Model):
    request = models.ForeignKey(to=Request, on_delete=models.CASCADE)
    document_category = models.ForeignKey(to=BankDocumentType, on_delete=models.CASCADE)
    person = models.ForeignKey(
        'questionnaire.ProfilePartnerIndividual', on_delete=models.CASCADE
    )
    document = models.ForeignKey(RequestDocument, on_delete=models.CASCADE)

    @classmethod
    def get_link(cls, request_id, document_category_id, document_id):
        return DocumentLinkToPerson.objects.filter(
            request_id=request_id,
            document_category_id=document_category_id,
            document_id=document_id
        ).first()

    @classmethod
    def set_link(cls, request_id, document_category_id, document_id, person_id):
        link = cls.get_link(
            request_id=request_id,
            document_category_id=document_category_id,
            document_id=document_id
        )
        if not link:
            link = DocumentLinkToPerson()
        link.request_id = request_id
        link.document_category_id = document_category_id
        link.document_id = document_id
        link.person_id = person_id
        link.save()
        return link

    class Meta:
        verbose_name = 'Привязка документов к участникам в анкете'
        verbose_name_plural = 'Привязки документов к участникам в анкете'


class RequestComment(AbstractRequestComment):
    bank = models.ForeignKey(to='clients.Bank', on_delete=models.CASCADE, null=True)
    request = models.ForeignKey(to=Request, on_delete=models.CASCADE)


class RequestLog(AbstractRequestLog):
    request = models.ForeignKey(to=Request, on_delete=models.CASCADE, related_name='logs')


class BankRatingResult(models.Model):
    bank_rating = models.ForeignKey(to='clients.BankRating', on_delete=models.CASCADE)
    request = models.ForeignKey(to=Request, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    data = JSONField()
    score = models.CharField(max_length=10)
    rating = models.CharField(max_length=56)
    risk_level = models.CharField(max_length=56)
    finance_state = models.CharField(max_length=56)


class TempOfferDoc(models.Model):
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE)
    print_form = models.ForeignKey(OfferPrintForm, on_delete=models.CASCADE)
    file = models.ForeignKey(BaseFile, on_delete=models.CASCADE)


class LimitRequest(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE,
                               related_name='limit_request')
    bank = models.ForeignKey(Bank, on_delete=models.CASCADE)
    request_id = models.CharField(max_length=50)
    request_number = models.CharField(max_length=50)
    status_data = models.TextField()


class RequestedDocNameUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             related_name='requested_docs_names')
    name = models.CharField(max_length=500)
