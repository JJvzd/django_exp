import datetime
from typing import Union

from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property

from multiselectfield import MultiSelectField

from cabinet.constants.constants import TaxationType
from clients.models import Company, Bank
from files.models import BaseFile, ExtendedFileField
from users.models import Role
from utils.validators import validate_number


class Agent(Company):
    document_number = models.CharField(max_length=20, null=True, blank=True)
    document_date = models.DateField(null=True, blank=True)
    document_name = models.CharField(max_length=200, null=True, blank=True)
    confirmed = models.BooleanField(default=True)
    confirmed_documents = models.IntegerField(default=0)
    fill_requisites = models.BooleanField(default=False)
    fill_documents = models.BooleanField(default=False)
    # банковские реквизиты
    taxation_type = models.CharField(
        max_length=10, choices=TaxationType.CHOICES, blank=True, null=True,
        verbose_name='Режим налогообложения',
    )

    bank_account_bik = models.CharField(
        max_length=10, blank=True, null=True, validators=[validate_number]
    )
    bank_account_bank = models.CharField(max_length=255, blank=True, null=True)
    bank_account_checking_account = models.CharField(
        max_length=30, blank=True, null=True, validators=[validate_number]
    )
    bank_account_correspondent_account = models.CharField(
        max_length=30, blank=True, null=True, validators=[validate_number]
    )
    bank_account_address = models.CharField(
        max_length=255, blank=True, null=True
    )

    # Контактная информация при регистрации

    fact_address = models.CharField(
        max_length=512, blank=True, null=True, verbose_name='Фактический адрес'
    )
    equal_fact_and_legal_address = models.BooleanField(
        default=False,
        verbose_name='Почтовый адрес отличается от юридического')

    position = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Должность'
    )
    document_for_position = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Документ на основании чего'
    )
    last_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Фамилия'
    )
    first_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Имя'
    )
    middle_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name='Отчество'
    )
    phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name='Телефон'
    )
    email = models.CharField(
        max_length=150, blank=True, null=True, verbose_name='E-mail'
    )
    # Паспортные данные
    series = models.CharField(
        max_length=15, verbose_name='Серия', blank=True, null=True
    )
    number = models.CharField(
        max_length=15, verbose_name='Номер', blank=True, null=True
    )
    issued_by = models.CharField(
        max_length=1000, verbose_name='Кем выдан', blank=True, null=True,
    )
    when_issued = models.DateField(
        blank=True, null=True, verbose_name='Когда выдан'
    )
    date_of_birth = models.DateField(
        blank=True, null=True, verbose_name='Дата рождения'
    )
    place_of_birth = models.CharField(
        max_length=1000, blank=True, null=True, verbose_name='Место рождения'
    )
    issued_code = models.CharField(
        max_length=15, blank=True, null=True, verbose_name='Код подразделения'
    )

    disabled_banks = models.ManyToManyField(to='clients.Bank')

    ruchnaya_korrect = models.CharField(
        max_length=512, blank=True, null=True, verbose_name='Ручная корректировка'
    )
    kv_previsheniya = models.CharField(
        max_length=512, blank=True, null=True, verbose_name='КВ превышения'
    )

    @property
    def active_contract_offer(self):
        active_contracts = ContractOffer.get_active()
        if active_contracts.exists():
            # Получения обязательных документов
            for active_contract in active_contracts.filter(
                required=True
            ):
                contract, created = self.agentcontractoffer_set.get_or_create(
                    contract=active_contract
                )
                if contract.accept_contract is not True:
                    return contract
            # Получения необязательных документов
            for active_contract in active_contracts.filter(
                required=False
            ):
                contract, created = self.agentcontractoffer_set.get_or_create(
                    contract=active_contract
                )
                if contract.accept_date is None:
                    return contract

    @property
    def accept_contract(self):
        result = self.active_contract_offer
        if result is not None:
            return result.accept_contract
        return True

    @property
    def is_active(self):
        return self.active and self.confirmed

    def check_confirmed(self) -> bool:
        from clients.serializers import (
            AgentProfileSerializer, AgentOrganizationSerializer
        )

        agent_profile = AgentProfile.objects.filter(agent=self).first()
        agent_profile_data = AgentProfileSerializer(agent_profile).data

        data = AgentOrganizationSerializer(self).data

        if AgentProfileSerializer(data=agent_profile_data).is_valid() and \
                AgentOrganizationSerializer(data=data).is_valid():
            self.confirmed = True
            self.save()
        return self.confirmed

    def check_requisites(self) -> bool:
        from clients.serializers import RequisitesSerializer
        data = RequisitesSerializer(self).data
        if RequisitesSerializer(data=data).is_valid():
            self.fill_requisites = True
            self.save()
        return self.fill_requisites

    def is_send_registration(self):
        """
        Проверят показыать кнопку 'отправить на регистрацию'
        :return:
        """
        from clients.serializers import (
            AgentIndividualEntrepreneurSerializer, AgentPhysicalPersonSerializer,
            AgentOrganizationSerializer, AgentProfileSerializer
        )

        if self.is_individual_entrepreneur:
            data = AgentIndividualEntrepreneurSerializer(self).data
            state_agent = AgentIndividualEntrepreneurSerializer(
                data=data).is_valid()
        elif self.is_physical_person:
            data = AgentPhysicalPersonSerializer(self).data
            state_agent = AgentPhysicalPersonSerializer(
                data=data).is_valid()
        elif self.is_organization:
            data = AgentOrganizationSerializer(self).data
            state_agent = AgentOrganizationSerializer(
                data=data
            ).is_valid()
        else:
            state_agent = False
        agent_profile = AgentProfile.objects.filter(agent=self).first()
        agent_profile_data = AgentProfileSerializer(agent_profile).data
        state_agent_profile = AgentProfileSerializer(data=agent_profile_data).is_valid()

        return state_agent_profile and state_agent

    class Meta:
        verbose_name = 'агент'
        verbose_name_plural = 'агенты'


class ContractOffer(models.Model):
    file = ExtendedFileField(
        verbose_name='Договор',
        upload_to='contract_offer/%Y-%m-%d/',
    )
    start_date = models.DateField(verbose_name='Дата начала действия')
    _html = models.TextField(
        verbose_name='Текст модального окна',
        default="""Сотрудничество с компанией Тендерхелп действует на основании 
        публичной оферты, размещённой по <a target="_blank" 
        href="HREF">ссылке</a> и в разделе <a 
        href="https://tenderhelp.ru/docs">https://tenderhelp.ru/docs</a>. <br>
         <br>Прежде, чем выразить согласие, ознакомьтесь с
            условиями договора. <br>""",
    )
    replaced = models.ForeignKey(
        'self',
        on_delete=models.DO_NOTHING,
        verbose_name='Заменён',
        null=True,
        blank=True
    )
    name = models.CharField(
        max_length=300,
        verbose_name='Нзавание документа',
        default='Регламент'
    )
    help_text = models.TextField(
        verbose_name='Краткое описание',
        blank=True,
        null=True,
    )
    required = models.BooleanField(
        verbose_name='Обязательность принятия',
        default=True
    )
    accept_text = models.CharField(
        verbose_name='Текст кнопки принятия',
        max_length=50,
        default='Принять'
    )
    cancel_text = models.CharField(
        verbose_name='Текст кнопки отказа',
        max_length=50,
        default='Отказ'
    )

    @property
    def html(self):
        return self._html.replace('HREF', self.file.url)

    @property
    def is_active(self):
        now = timezone.now().date()
        if now >= self.start_date and (
            self.replaced is None or self.replaced.start_date > now
        ):
            return True
        return False

    @classmethod
    def get_active(cls):
        now = timezone.now().date()
        return cls.objects.filter(
            Q(start_date__lte=now) & (
                Q(replaced__isnull=True) |
                Q(replaced__start_date__gt=now)
            )
        )

    class Meta:
        ordering = ['start_date']


class AgentContractOffer(models.Model):
    contract = models.ForeignKey(ContractOffer, on_delete=models.CASCADE,
                                 verbose_name='Договор')
    accept_date = models.DateTimeField(verbose_name='Дата принятия договора',
                                       blank=True, null=True)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE)
    accept_contract = models.BooleanField(blank=True, null=True)

    @property
    def contract_name(self):
        return self.contract.name

    @property
    def contract_date(self):
        return self.contract.start_date


class AgentDepartament(models.Model):
    agent = models.ForeignKey(to='Agent', on_delete=models.CASCADE)
    name = models.CharField(max_length=250)

    def __str__(self):
        return '%s (%s)' % (self.agent, self.name)


class AgentDepartamentUser(models.Model):
    departament = models.ForeignKey(to=AgentDepartament, on_delete=models.CASCADE)
    user = models.ForeignKey(to='users.User', on_delete=models.CASCADE)


class AgentManager(models.Model):
    manager = models.ForeignKey('users.User', on_delete=models.CASCADE)
    agent = models.ForeignKey(
        to=Agent, on_delete=models.CASCADE, unique=True, related_name='manager'
    )

    @staticmethod
    def get_managers():
        from users.models import User, Role
        return User.objects.filter(roles__name=Role.MANAGER, is_active=True)

    @staticmethod
    def get_allowed_agents_for_manager(manager):
        already_busy_agents = AgentManager.objects.values_list('agent_id', flat=True)
        return Agent.objects.exclude(id__in=already_busy_agents)

    @staticmethod
    def get_manager_agents(manager):
        return Agent.objects.filter(
            id__in=AgentManager.objects.filter(manager=manager).values_list(
                'agent_id', flat=True
            )
        )

    @staticmethod
    def manager_has_client(manager, client):
        return manager.id == client.manager_id

    @staticmethod
    def get_manager_by_agent(agent_company: Union[Agent, int]):
        """
        :param agent_company:
        :return: users.models.User
        """
        manager = None
        if isinstance(agent_company, int):
            manager = AgentManager.objects.filter(agent_id=agent_company).first()
        if isinstance(agent_company, Agent):
            manager = agent_company.manager.first()

        if manager:
            return manager.manager
        return manager

    @staticmethod
    def set_manager_to_agent(manager, agent, reason=None, date_from=None, date_to=None):
        record = AgentManager.objects.filter(agent=agent).first()
        try:
            old_manager = agent.manager.first().manager.full_name
        except AttributeError:
            old_manager = ''
        if record and record.manager != manager:
            AgentManager.objects.filter(id=record.id).delete()
            record = None
        if not record:
            record = AgentManager.objects.create(agent=agent, manager=manager)
        from clients.models import Client
        Client.objects.filter(agent_company=agent).update(manager=manager)

        from notification.base import Notification
        for user in agent.user_set.all():
            if user.has_role(Role.GENERAL_AGENT):
                manager_data = {'FIO_MANAGER': manager.full_name,
                                'EMAIL': manager.email, 'PHONE1': manager.phone,
                                'PHONE2': manager.phone2}
                if date_from and date_to and reason == 'Отпуск':
                    Notification.trigger(
                        'new_manager_for_agent_vacation',
                        force_emails=[user.email], params={
                            'FIO_OLD_MANAGER': old_manager,
                            'DATE_FROM': datetime.datetime.strptime(date_from,
                                                                    '%Y-%m-%d').strftime(
                                '%d.%m.%Y'),
                            'DATE_TO': datetime.datetime.strptime(date_to,
                                                                  '%Y-%m-%d').strftime(
                                '%d.%m.%Y'),
                            **manager_data
                        })
                elif reason == 'Смена менеджера':
                    Notification.trigger(
                        'new_manager_for_agent',
                        force_emails=[user.email], params={
                            'DATE_NOW': datetime.datetime.now().strftime('%d.%m.%Y'),
                            **manager_data
                        })
        return record

    class Meta:
        unique_together = ('manager', 'agent')


class AgentDocumentCategory(models.Model):
    name = models.CharField(max_length=255, verbose_name='Название')
    active = models.BooleanField(default=True, verbose_name='Активный')
    for_individual_entrepreneur = models.BooleanField(
        default=False, verbose_name='Для индивидуальных предпринимателей'
    )
    for_physical_person = models.BooleanField(
        default=False, verbose_name='Для физических лиц'
    )
    for_organization = models.BooleanField(
        default=False, verbose_name='Для юридических лиц'
    )
    auto_generate = models.BooleanField(
        default=False, verbose_name='Автосоздаваемый документ'
    )
    type = models.CharField(
        max_length=150, blank=False, null=False, unique=True,
        verbose_name='Уникальный код'
    )
    order = models.PositiveIntegerField(
        default=9999, verbose_name='Порядок сортировки', help_text='По возрастанию'
    )
    help_text = models.TextField(
        blank=True, null=True, verbose_name='Всплывающая подсказка'
    )

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'категории документов агентов'
        verbose_name = 'категория документа агента'

    def __str__(self):
        return self.name


class AgentDocument(models.Model):
    agent = models.ForeignKey(to='Agent', on_delete=models.CASCADE)
    category = models.ForeignKey(to='AgentDocumentCategory', on_delete=models.PROTECT)
    file = models.ForeignKey(to=BaseFile, on_delete=models.CASCADE, null=True, blank=True)
    certificate = models.ForeignKey(
        to='cabinet.Certificate', on_delete=models.SET_NULL, null=True, blank=True
    )
    comment = models.CharField(max_length=1000, blank=True, null=True, default=None)
    document_status = models.IntegerField(default=2)

    @cached_property
    def sign(self):
        if self.file:
            return self.file.sign_set.filter(author=self.agent).first()
        return None

    def signed(self):
        return self.sign is not None

    def __str__(self):
        return 'Агент %s - %s' % (self.agent.short_name, self.category)

    class Meta:
        verbose_name_plural = 'документы агента'
        verbose_name = 'документ агента'


class HowClients(models.Model):
    BIG = 1
    MIDDLE = 2
    LITTLE = 3
    CHOICES = (
        (1, 'Крупными'),
        (2, 'Средними'),
        (3, 'Малыми')
    )


class AgentProfile(models.Model):
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, null=True, blank=True)
    experience = models.CharField(
        verbose_name='Опыт работы агентом', null=True, blank=True, max_length=15
    )
    priority_conditions = models.TextField(
        verbose_name='Какие условия считаете приоритетными в работе', null=True,
        blank=True
    )
    how_clients = models.ManyToManyField(
        HowClients, verbose_name='С какими клиентами работаете', blank=True
    )
    equal_fact_crutch = models.CharField(
        max_length=20, blank=True, null=True,
        verbose_name='Почтовый адрес отличается от юридического Костыль'
    )
    about_us = models.CharField(
        max_length=300, null=True, blank=True,
        verbose_name='Из каких источников узнали о нас'
    )
    your_banks = models.CharField(
        max_length=300, null=True, blank=True,
        verbose_name='С какими банками работаете'
    )
    our_banks = models.ManyToManyField(
        Bank, blank=True, verbose_name='Какие банки на платформе Тендерхелп Вам интересны'
    )
    your_city = models.CharField(
        max_length=300, null=True, blank=True,
        verbose_name='Город проживания'
    )


class AgentVerification(models.Model):
    STATUS_IN_PROCESS = 'in_process'
    STATUS_SUCCESS = 'success'
    STATUS_FAIL = 'fail'
    STATUS_CHOICES = (
        (STATUS_IN_PROCESS, 'В процессе'),
        (STATUS_SUCCESS, 'Верификация пройдена'),
        (STATUS_FAIL, 'Верификация не пройдена'),
    )
    agent = models.ForeignKey(to=Agent, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROCESS
    )
    created = models.DateTimeField(editable=False)
    updated = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.created:
            self.created = timezone.now()
        self.updated = timezone.now()
        return super(AgentVerification, self).save(*args, **kwargs)


class AgentVerificationComment(models.Model):
    verification = models.ForeignKey(to='AgentVerification', on_delete=models.CASCADE)
    comment = models.TextField()
    created = models.DateTimeField(auto_now_add=True)


class AgentInstructionsDocuments(models.Model):
    CHOICES_NAME = (
        ('bank', 'Банк'),
        ('general_bank', 'Генеральный банк'),
        ('agent', 'Агент'),
        ('general_agent', 'Генеральный агент'),
        ('super_agent', 'Супер агент'),
        ('head_agent', 'Глава агент'),
        ('client', 'Клиент'),
        ('manager', 'manager'),
        ('mfo', 'оператор МФО'),
        ('verifier', 'Верификатор')
    )

    name = models.CharField(max_length=255, verbose_name='Название докумнета')
    name2 = models.CharField(max_length=255, verbose_name='Название документа в кабинете')
    file = models.FileField(upload_to='instructions/%Y-%m-%d/',  null=True, blank=True)
    roles = MultiSelectField(verbose_name='Видимо для ролей', choices=CHOICES_NAME,
                             default='', max_length=200, null=True, blank=True)
    active = models.BooleanField(default=True, verbose_name='Активный')
    show = models.BooleanField(default=True, verbose_name='Отображение в кабинете')


class AgentRewards(models.Model):
    date = models.DateField(
        verbose_name='Дата',
        blank=True, null=True
    )
    agent = models.ForeignKey(to=Agent, on_delete=models.CASCADE)
    bank = models.ForeignKey(to=Bank, null=True, blank=True, on_delete=models.CASCADE)
    number_requests = models.DecimalField(
        max_digits=30, decimal_places=2, default=0, blank=False,
        verbose_name='Количество выданных заявок'
    )
    percent = models.DecimalField(
        max_digits=30, decimal_places=2, default=0, blank=False,
        verbose_name='Проценты',
    )
