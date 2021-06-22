import json
import logging

from django.db import models
from django.utils.functional import cached_property
from django.utils.module_loading import import_string
from sentry_sdk import capture_exception

from clients.models.common import Company
from files.models import BaseFile
from settings.configs.banks import BankCode
from settings.configs.mfo import MFOCode
from users.models import User
from utils.helpers import get_value_by_path

logger = logging.getLogger('django')


class CreditOrganizationAbstract(Company):
    CODES = []
    code = models.CharField(
        max_length=20, blank=False, null=False, choices=CODES, unique=True
    )

    class Meta:
        abstract = True


class CreditOrganizationSettings(models.Model):
    priority = models.PositiveIntegerField(default=1, db_index=True)
    enable = models.BooleanField(default=False, verbose_name='Банк принимает заявки')
    amount_limit = models.FloatField(default=0)
    limit_for_client = models.FloatField(default=0, verbose_name='Лимит на клиента')
    scoring_enable = models.BooleanField(
        default=True, verbose_name='Проверять ли скоринг'
    )
    send_via_integration = models.BooleanField(
        default=False, verbose_name='Отправлять заявки через интеграцию'
    )
    date_from_update_status_via_integration = models.DateField(
        verbose_name='Дата с которой заявки обновляются',
        blank=True,
        null=True
    )
    update_via_integration = models.BooleanField(
        default=False, verbose_name='Обновлять отправленные заявки через интеграцию'
    )
    verification_enable = models.BooleanField(default=False)
    scoring_settings = models.TextField(default='{}')
    allow_request_only_with_ecp = models.BooleanField(default=False)
    work_without_ecp = models.BooleanField(default=False)
    credit_organization = models.OneToOneField(
        CreditOrganizationAbstract, on_delete=models.DO_NOTHING, related_name='settings'
    )
    hide_user_names = models.BooleanField(
        default=False,
        verbose_name='Скрыть ФИО сотрудников в чате'
    )
    is_handle_bank = models.BooleanField(
        default=False, verbose_name='Ручной банк'
    )
    referal_sign_from_amount = models.FloatField(
        default=0,
        verbose_name='Отправлять ссылку на подписание в чат от определённой суммы'
    )
    archive_days = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='Через сколько дней отправлять в архив'
    )

    class Meta:
        abstract = True


class CreditOrganizationBlackList(models.Model):
    credit_organization = models.ForeignKey(to=CreditOrganizationAbstract,
                                            on_delete=models.CASCADE)
    inn = models.CharField(max_length=15)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class CreditOrganizationPackage(models.Model):
    credit_organization = models.ForeignKey(
        to=CreditOrganizationAbstract, on_delete=models.CASCADE
    )
    document_type = models.ForeignKey(
        to='base_request.BankDocumentType', on_delete=models.CASCADE
    )
    required = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    conditionals = models.TextField(default='{}')

    def __str__(self):
        return "Условия для %s | %s | %s" % (
            self.document_type, self.required, self.active)

    class Meta:
        abstract = True


class Bank(CreditOrganizationAbstract):
    CODES = BankCode.CHOICES

    @cached_property
    def bank_integration(self):
        try:
            cls = import_string(
                'bank_guarantee.bank_integrations.%s.adapter.Adapter' % self.code
            )
        except ImportError:
            cls = import_string(
                'bank_guarantee.bank_integrations.adapter.BaseBankAdapter'
            )
        return cls(self)

    class Meta:
        verbose_name = 'банк'
        verbose_name_plural = 'банки'

    def __str__(self):
        return 'Bank %s (%s)' % (self.short_name, self.code)


class BankRating(models.Model):
    """
    credit_organization null - это банк по умолчанию для рейтинга черновиков,
    создается в update_rating
    """
    credit_organization = models.ForeignKey(to=Bank, on_delete=models.CASCADE, null=True)
    rating_class = models.CharField(max_length=256)
    active = models.BooleanField(default=True)

    @classmethod
    def get_default_rating(cls, request, force: bool = False):
        bank_rating = BankRating.objects.filter(
            credit_organization__isnull=True
        ).first()
        if bank_rating:
            return bank_rating.get_rating(request=request, force=force)
        else:
            return None

    def get_rating(self, request, force: bool = False):
        rating = None
        if not force:
            rating = self.bankratingresult_set.filter(
                request_id=request.id
            ).order_by('-id').first()

        if not rating:
            try:
                rating = self.__generate_rating(request)
            except Exception as e:
                capture_exception(e)
                logger.exception(e)
                return None
        return rating

    def __generate_rating(self, request):
        rating_class = import_string(self.rating_class)()
        data = rating_class.calculate(request)
        rating = self.bankratingresult_set.create(
            request=request,
            data=data.data,
            rating=data.rating,
            finance_state=data.finance_state,
            score=data.score,
            risk_level=data.risk_level,
        )
        return rating

    def update_rating(self, request):
        rating_result = request.bankratingresult_set.all()
        rating_class = import_string(self.rating_class)()
        data = rating_class.calculate(request)
        rating_result.update(
            bank_rating=self,
            data=data.data,
            rating=data.rating,
            finance_state=data.finance_state,
            score=data.score,
            risk_level=data.risk_level,
        )


class RequestRejectionReasonTemplate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    name = models.CharField(
        verbose_name='Название шаблона', max_length=100, blank=True, default=''
    )
    reason = models.CharField(
        verbose_name='Причина отклонения заявки банком', max_length=300,
        blank=True, null=True
    )

    def __str__(self):
        return self.name or f'Шаблон №{self.id}'

    class Meta:
        verbose_name = 'Шаблон причины отклонения заявки банком'
        verbose_name_plural = 'Шаблоны причин отклонения заявок банками'


class BankSigner(models.Model):
    credit_organization = models.ForeignKey(
        to=Bank, on_delete=models.CASCADE, related_name='signers'
    )
    first_name = models.CharField(max_length=30, verbose_name='Имя')
    last_name = models.CharField(max_length=30, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=30, verbose_name='Отчетство')
    additional_data = models.TextField(default='{}')

    @cached_property
    def json_additional_data(self):
        return json.loads(self.additional_data)

    def get_additional_data(self, path):
        return get_value_by_path(self.json_additional_data, path)

    @cached_property
    def name(self):
        return '%s %s %s' % (self.last_name, self.first_name, self.middle_name)


class BankPackage(CreditOrganizationPackage):
    credit_organization = models.ForeignKey(
        to=Bank, on_delete=models.CASCADE, related_name='package'
    )


class BankSettings(CreditOrganizationSettings):
    credit_organization = models.OneToOneField(
        Bank, on_delete=models.CASCADE, related_name='settings'
    )


class BankStopInn(CreditOrganizationBlackList):
    credit_organization = models.ForeignKey(
        to=Bank, on_delete=models.CASCADE, related_name='black_list'
    )


class MFO(Company):
    code = models.CharField(
        max_length=20, blank=False, null=False, choices=MFOCode.CHOICES
    )

    @cached_property
    def bank_integration(self):
        try:
            cls = import_string(
                'tender_loans.bank_integrations.%s.adapter.Adapter' % self.code)
        except ImportError:
            cls = import_string('tender_loans.bank_integrations.adapter.BaseBankAdapter')
        return cls(self)

    class Meta:
        verbose_name = 'МФО'
        verbose_name_plural = 'МФО'


class MFOPackage(CreditOrganizationPackage):
    credit_organization = models.ForeignKey(
        to=MFO, on_delete=models.CASCADE, related_name='package'
    )


class MFOSettings(CreditOrganizationSettings):
    credit_organization = models.OneToOneField(
        'MFO', on_delete=models.DO_NOTHING, related_name='settings'
    )


class MFOBlackList(CreditOrganizationBlackList):
    credit_organization = models.OneToOneField(
        'MFO', on_delete=models.DO_NOTHING, related_name='black_list'
    )


class TemplateChat(models.Model):
    name = models.CharField(max_length=100)
    template = models.TextField()
    files = models.ManyToManyField(to=BaseFile, default=None)

    class Meta:
        abstract = True


class TemplateChatBank(TemplateChat):
    bank = models.ForeignKey(to=Bank, on_delete=models.CASCADE, blank=True, null=True)


class TemplateChatAgent(TemplateChat):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE, blank=True,
                             null=True)


class TemplateChatMFO(TemplateChat):
    bank = models.ForeignKey(to=MFO, on_delete=models.CASCADE, blank=True, null=True)


class MoscombankDocument(models.Model):
    doc_id = models.PositiveIntegerField()
    doc_type = models.CharField(max_length=50)
    name = models.CharField(max_length=500)
    category = models.ManyToManyField('base_request.BankDocumentType', blank=True)
    print_form = models.ManyToManyField(
        'bank_guarantee.RequestPrintForm',
        blank=True
    )
    equal_doc = models.ForeignKey(
        'self', on_delete=models.DO_NOTHING, blank=True, null=True
    )


class MoscomIntergration(models.Model):
    request_id = models.PositiveIntegerField(null=True, blank=True)
    date_from = models.DateTimeField(null=True, blank=True)
