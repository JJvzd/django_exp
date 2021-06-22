from json import JSONDecodeError

import ujson
from time import sleep

from django.db import models
from django.db.models.query_utils import Q
from django.utils import timezone
from requests import Session
from sentry_sdk import capture_exception

from cabinet.constants.constants import Target
from external_api.egrul_parser import parse_file, parse_company_data, VERSION
from files.models import BaseFile

from utils.helpers import download_file
from utils.validators import validate_inn


def get_name_fields(value):
    names = []
    for element in value._meta.concrete_fields:
        name = element.name
        if name not in ['id', 'code']:
            names.append(name)
    return names


class PlacementPlace(models.Model):
    """Модель площадок размещения"""
    CODE_AKD = 'AKD'
    CODE_AGZRT = 'AGZRT'
    CODE_EETP = 'EETP'
    CODE_MMVB = 'MMVB'
    CODE_RTS = 'RTS'
    CODE_SBAST = 'SBAST'
    CODE_B2B = 'B2B'
    CODE_FABRIKANT = 'FABRIKANT'
    CODE_GPB = 'GPB'
    CODE_ONLINECONTRACT = 'ONLINECONTRACT'
    CODE_OTC = 'OTC'
    CODE_TENDER_PRO = 'TENDER_PRO'
    CODE_ZAKUPKI_GOV_RU = 'ZAKUPKI_GOV_RU'
    CODE_ZAKAZRF = 'ZAKAZRF'
    CODE_ETPRF = 'ETPRF'
    CODE_AVTODOR = 'AVTODOR'
    CODE_OTHER = 'OTHER'
    name = models.CharField(
        verbose_name='Название площадки',
        max_length=250,
    )
    alias = models.CharField(
        verbose_name='Код площадки, которая является основной',
        max_length=100,
        blank=True,
        null=True
    )
    code = models.CharField(
        verbose_name='Код площадки - только для базовых площадок',
        max_length=100,
        blank=True,
        null=True
    )

    def __str__(self):
        return '%s %s' % (self.id, self.name)

    @staticmethod
    def find_or_insert(name):
        placement = PlacementPlace.objects.filter(name=name).first()
        if placement:
            if placement.alias:
                placement.code = placement.alias
        else:
            PlacementPlace(name=name).save()
            placement = PlacementPlace.objects.filter(name=name).first()
        return placement

    class Meta:
        ordering = ['-id']
        verbose_name = 'Площадка размещения'
        verbose_name_plural = 'Площадки размещения'


class CertifyingCenter(models.Model):
    """Модель удостоверяющих центра"""
    inn = models.CharField(
        verbose_name='ИНН',
        max_length=12,
        validators=[validate_inn]
    )

    class Meta:
        ordering = ['-id']
        verbose_name = 'Список удостоверяющих центров'
        verbose_name_plural = 'Удостоверяющий центр'


class Certificate(models.Model):
    """Модель сертификата"""
    org_name = models.CharField(
        max_length=255, default='0', verbose_name='Название организации'
    )
    fio = models.CharField(
        max_length=255, default='0', verbose_name='Фамилия, имя и отчество'
    )
    number = models.CharField(max_length=255, default=0)
    date_granted = models.CharField(max_length=50, verbose_name='Дата выдачи сертификата')
    date_end = models.CharField(
        max_length=50, verbose_name='Дата окончания сертификата', blank=True, null=True
    )
    subject_name = models.CharField(
        max_length=1000, verbose_name='Полная строка SubjectName'
    )
    issuer_name = models.CharField(
        max_length=1000, verbose_name='Полная строка IssuerName'
    )
    algorithm = models.CharField(
        max_length=50, blank=True, null=True, verbose_name='Алгоритм'
    )
    export = models.TextField(
        blank=True, verbose_name='Base64 данные открытого ключа'
    )
    uc = models.CharField(max_length=500, blank=True, verbose_name='Издатель')

    class Meta:
        ordering = ['-id']
        verbose_name = 'Сертификаты'
        verbose_name_plural = 'Сертификат'


class Country(models.Model):
    name = models.CharField(max_length=128)

    class Meta:
        ordering = ['name']
        verbose_name = 'Страна'
        verbose_name_plural = 'Страны'


class OrganizationForms(models.Model):
    """ Модель Организационно-правовых форм"""
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)

    class Meta:
        ordering = ['-id']
        verbose_name = 'Организационно-правовая форма'
        verbose_name_plural = 'Организационно-правовые формы'


class TaxSystems(models.Model):
    """Модель систем налогообложения"""
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=255)

    class Meta:
        ordering = ['-id']
        verbose_name = 'Система налогообложения'
        verbose_name_plural = 'Системы налогообложения'


class SignHistory(models.Model):
    file = models.ForeignKey(to=BaseFile, on_delete=models.CASCADE)
    certificate = models.ForeignKey(
        to=Certificate, on_delete=models.SET_NULL, null=True, blank=True
    )
    user = models.ForeignKey(
        to='users.User', on_delete=models.SET_NULL, null=True, blank=True
    )
    sign_date = models.DateTimeField(auto_now_add=True)
    sign = models.TextField()


class EgrulData(models.Model):
    inn = models.CharField(max_length=20)
    data = models.TextField(blank=True, null=True, default='{}')
    last_updated = models.DateTimeField(blank=True, null=True, auto_now=True)
    version = models.CharField(max_length=5, blank=False, null=False, default='')

    @classmethod
    def _need_update(cls, data: 'EgrulData') -> bool:
        if not data.data or not ujson.loads(data.data):
            return True
        if cls._get_version() != data.version:
            return True
        if (timezone.now() - data.last_updated).seconds > 60 * 60 * 24:
            return True

        return False

    @classmethod
    def get_info(cls, inn):
        data = EgrulData.objects.filter(inn=inn).first()
        if not data:
            data = EgrulData(inn=inn)
        if cls._need_update(data):
            parsed_data = cls._parse_file(inn)
            if parsed_data:
                data.data = ujson.dumps(parsed_data)
                data.version = cls._get_version()
                data.save()
        return ujson.loads(data.data)

    @classmethod
    def _get_version(cls):
        return VERSION

    @classmethod
    def _download_pdf(cls, inn, retries=0):
        if retries > 5:
            return None
        form_data = {
            "vyp3CaptchaToken": "",
            "query": inn,
            "region": "",
            "PreventChromeAutocomplete": "",
        }
        client = Session()
        try:
            response = client.post('https://egrul.nalog.ru', data=form_data)
        except ConnectionError as e:
            sleep(2)
            capture_exception(e)
            return cls._download_pdf(inn, retries=retries + 1)
        if response.status_code == 200:
            response = response.json()
        else:
            return cls._download_pdf(inn, retries=retries + 1)
        if not response.get('captchaRequired', False):
            try:
                token = response.get('t')
                if token:
                    response = client.get(
                        'https://egrul.nalog.ru/search-result/' + token
                    ).json()
                    tokens = response.get('rows') or [{'t': None}]
                    token = tokens[0].get('t', None) or token
                    if token:
                        client.get('https://egrul.nalog.ru/vyp-request/' + token)
                        for _ in range(4):
                            sleep(2)
                            response = client.get(
                                'https://egrul.nalog.ru/vyp-status/' + token
                            ).json()
                            if response.get('status') == 'ready':
                                download_url = 'https://egrul.nalog.ru/vyp-download/' + \
                                               token
                                return download_file(download_url)

                else:
                    return cls._download_pdf(inn, retries=retries + 1)
            except JSONDecodeError:
                return cls._download_pdf(inn, retries=retries + 1)

        if response.get('ERRORS', {}).get('captcha', [None])[0]:
            return cls._download_pdf(inn, retries=retries + 1)

        return None

    @classmethod
    def _parse_file(cls, inn):
        file = cls._download_pdf(inn)
        if file:
            data = parse_file(file)
            return parse_company_data(data)
        return None


class WorkRule(models.Model):
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    bg_type = models.CharField(
        max_length=30, choices=Target.CHOICES, blank=False, null=False
    )
    bank = models.ForeignKey(to='clients.Bank', on_delete=models.CASCADE)
    limit_from = models.PositiveIntegerField(blank=True, null=True)
    limit_to = models.PositiveIntegerField(blank=True, null=True)
    commission = models.FloatField()
    commission_on_excess = models.CharField(max_length=100, blank=True, null=True)

    @staticmethod
    def get_work_rule(bank_id, bg_type, amount):
        work_rule = WorkRule.objects.filter(
            bank_id=bank_id,
            bg_type=bg_type,
            limit_from__gte=amount,
            limit_to__lte=amount,
        ).order_by('-updated').first()
        if work_rule is None:
            work_rule = WorkRule.objects.filter(
                bank_id=bank_id,
                bg_type=bg_type,
                limit_from__gte=amount,
            ).order_by('-updated').first()
        if work_rule is None:
            work_rule = WorkRule.objects.filter(
                bank_id=bank_id,
                bg_type=bg_type,
            ).order_by('-updated').first()
        return work_rule

    @staticmethod
    def get_rewards(bank_id, bg_types, amount):
        commissions = []
        commissions_on_excess = []
        for bg_type in bg_types:
            work_rule = WorkRule.get_work_rule(bank_id, bg_type, amount)
            if work_rule is not None:
                commissions.append(work_rule.commission or -1)
                commissions_on_excess.append(work_rule.commission_on_excess or -1)

        commission = max(commissions)
        if float(commission) <= 0:
            commission = None
        commission_on_excess = max(commissions_on_excess)
        if float(commission_on_excess) <= 0:
            commission_on_excess = None

        return commission, commission_on_excess


class Region(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=20, blank=True, null=True)

    @staticmethod
    def get_region(inn=None, kpp=None):
        value = kpp or inn
        assert value and len(value) >= 4
        region = Region.objects.filter(Q(code=value[:4]) | Q(code=value[:3])).first()
        if region:
            return region.name
        return ''


class System(models.Model):
    from clients.models import Agent

    site_on = models.BooleanField(
        default=True, verbose_name='Доступ в личные кабинеты открыт'
    )
    scoring_on = models.BooleanField(
        default=True, verbose_name='Скоринг во всех банках'
    )
    auto_save = models.PositiveIntegerField(
        default=500, verbose_name='Время автосохранения анкеты'
    )
    strong_check = models.BooleanField(
        default=True, verbose_name='УКЭП: Осуществлять проверку на соответствие УКЭП'
    )
    inn_check = models.BooleanField(
        default=True,
        verbose_name="УКЭП: Наличие ИНН УЦ в xml-списке e-trust.gosuslugi.ru"
    )
    cnt_right = models.BooleanField(default=True)
    archive_days = models.PositiveIntegerField(default=30)
    bank_stop_inn = models.BooleanField(default=True)
    global_stop_inn = models.BooleanField(default=True)
    algorithm = models.BooleanField(
        default=True,
        verbose_name='УКЭП: Алгоритм подписи сертификата ГОСТ Р 34.11-94/34.10-2001 '
                     '(1.2.643.2.2.3)'
    )
    ogrn = models.BooleanField(
        default=True,
        verbose_name="УКЭП: Наличие атрибута ОГРН в поле 'Issuer'"
    )
    subject_sign_tool = models.BooleanField(
        default=False,
        verbose_name="УКЭП: Наличие дополнения SubjectSignTool (1.2.643.100.111)"
    )
    issuer_sign_tool = models.BooleanField(
        default=False,
        verbose_name="УКЭП: Наличие дополнения IssuerSignTool (1.2.643.100.112)"
    )
    certificate_policies = models.BooleanField(
        default=True,
        verbose_name="УКЭП: Наличие дополнения CertificatePolicies (2.5.29.32)"
    )
    uc = models.BooleanField(
        default=True,
        verbose_name="Проверка центра выдавщего сертификат"
    )
    check_profile = models.IntegerField(blank=True, null=True)
    limit_file_size = models.DecimalField(max_digits=4, decimal_places=1, default=40)
    static_pages = models.TextField(blank=True, null=True)
    notifications_enabled = models.BooleanField(default=True)
    default_agent = models.ForeignKey(
        Agent, models.DO_NOTHING, db_column='default_agent', blank=True, null=True
    )
    admin_email = models.CharField(max_length=255, blank=True, default='')
    email_new_agent = models.CharField(max_length=2000, blank=True, default='')
    email_support = models.CharField(max_length=2000, blank=True, default='')
    email_calculator = models.CharField(max_length=2000, blank=True, default='')
    email_callback = models.CharField(max_length=2000, blank=True, default='')
    agents_counter = models.PositiveIntegerField(default=0)
    msp_notify = models.CharField(max_length=2000, blank=True, default='')
    validate_sign = models.BooleanField(
        default=True,
        verbose_name="Проверка корректности подписи на стороне сервера"
    )
    request_number = models.PositiveIntegerField(blank=True, null=True)
    cert_valid = models.BooleanField(
        default=True,
        verbose_name="Проверка валидности сертификата на сайте ГосУслуги"
    )
    tenderhelp_loan_offer_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0
    )
    one_package_documents = models.BooleanField(
        default=True,
        verbose_name='Использовать один пакет документов для всех банков'
                     '(Инбак/СимлФинанс)'
    )
    default_scoring_rules = models.TextField(default='[]')

    @classmethod
    def get_setting(cls, name, for_update=False, default=None):
        System.objects.get_or_create(id=1)
        if for_update:
            settings = System.objects.select_for_update().filter(id=1).first()
            return getattr(settings, name) or default
        else:
            return getattr(System.objects.filter(id=1).first(), name) or default

    @classmethod
    def set_settings(cls, name, value):
        System.objects.get_or_create(id=1)
        System.objects.filter(id=1).update(**{name: value})
