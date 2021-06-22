from django.db import models
from django.utils.functional import cached_property

from external_api.dadata_api import DaData


class CompanyConstants:
    IE_INN_LEN = 12  # идивидуальный предприниматель
    FP_INN_LEN = 12  # физическое лицо
    UO_INN_LEN = 10  # организация


class Company(models.Model):
    inn = models.CharField(max_length=15, null=True, blank=False)
    kpp = models.CharField(max_length=15, null=True, blank=False)
    ogrn = models.CharField(max_length=15, null=True, blank=False)
    okpto = models.CharField(max_length=20, null=True, blank=True)
    need_sign_regulations = models.BooleanField(
        default=True,
        verbose_name='Необходимость подписи регламента перед первым входом.'
    )
    full_name = models.CharField(max_length=512, null=True, blank=True)
    short_name = models.CharField(max_length=512, null=True, blank=True)

    active = models.BooleanField(default=True)
    region = models.CharField(max_length=100, blank=True, null=True)
    legal_address = models.CharField(
        max_length=512, blank=True, null=True, verbose_name='Юридический адрес'
    )

    internal_news = models.PositiveIntegerField(default=0)
    work_rules = models.PositiveIntegerField(default=0)

    created = models.DateTimeField(blank=True, null=True, auto_now_add=True)

    def get_first_user(self):
        return self.user_set.first()

    @cached_property
    def is_individual_entrepreneur(self):
        return self.inn and self.ogrn and len(self.inn) == CompanyConstants.IE_INN_LEN

    @cached_property
    def is_physical_person(self):
        return self.inn and not self.ogrn and len(self.inn) == CompanyConstants.FP_INN_LEN

    @cached_property
    def is_organization(self):
        return self.inn and self.ogrn and len(self.inn) == CompanyConstants.UO_INN_LEN

    @cached_property
    def get_actual_instance(self):
        if not isinstance(self, Company):
            return self
        for attr in ['bank', 'mfo', 'agent', 'client']:
            if hasattr(self, attr):
                return getattr(self, attr)

    def get_role(self):
        return self.get_actual_instance.__class__.__name__

    def fill(self):
        filled = self.inn and self.kpp and self.ogrn
        filled = filled and self.short_name and self.full_name

        if not filled:
            api = DaData()
            data = api.get_company(self.inn).get('suggestions')[0]
            data = dict(
                short_name=data.get('data', {}).get('name', {}).get('short_with_opf', ''),
                full_name=data.get('data', {}).get('name', {}).get('full_with_opf', ''),
                inn=data.get('data', {}).get('inn', ''),
                kpp=data.get('data', {}).get('kpp', ''),
                ogrn=data.get('data', {}).get('ogrn', ''),
            )

            for field, value in data.items():
                if not getattr(self, field):
                    setattr(self, field, value)
            self.save()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return '%s %s (%s/%s, %s)' % (
            self.__class__.__name__, self.short_name, self.inn, self.kpp, self.ogrn
        )


class InternalNews(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVE = 'archive'
    title = models.CharField(max_length=256)
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=(
        (STATUS_DRAFT, 'Черновик'),
        (STATUS_PUBLISHED, 'Опубликовано'),
        (STATUS_ARCHIVE, 'В архиве'),
    ), default=STATUS_DRAFT)
    for_agents = models.BooleanField(default=False)
    for_clients = models.BooleanField(default=False)
    for_banks = models.BooleanField(default=False)
    for_mfo = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Новость в кабинетах'
        verbose_name_plural = 'Новости в кабинетах'



