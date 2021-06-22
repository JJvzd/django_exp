from django.core.validators import validate_email
from rest_framework import serializers

from cabinet.models import WorkRule
from cabinet.serializers import FileSerializer, ProfileSerializerForClient
from calculator.models import Calculator
from calculator.serializers import CalculatorSerializer
from clients.models import (
    AgentDocument, AgentDocumentCategory, AgentProfile, HowClients, Bank,
    TenderHelpAgentComment, TemplateChatBank, TemplateChatMFO,
    RequestRejectionReasonTemplate, AgentInstructionsDocuments, TemplateChatAgent,
    BankStopInn
)
from clients.models.agents import Agent, AgentRewards
from clients.models.clients import Client
from clients.models.common import InternalNews, Company
from utils.validators import (
    validate_bik, validate_checking_account, validate_name, validate_middle_name,
    validate_first_name, validate_last_name, validate_issued_by,
    validate_passport_series, validate_passport_number)


class CompanySerializer(serializers.ModelSerializer):
    role = serializers.ReadOnlyField(source='get_role')

    class Meta:
        model = Company
        fields = [
            'id',
            'full_name',
            'short_name',
            'kpp',
            'ogrn',
            'inn',
            'role',
        ]


class ClientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Client"""
    phone = serializers.ReadOnlyField(source='agent_company.phone', read_only=True)
    email = serializers.ReadOnlyField(source='agent_company.email', read_only=True)
    last_login = serializers.ReadOnlyField(source='agent_user.last_login', read_only=True)
    legal_address_city = serializers.ReadOnlyField(
        source='agent_company.legal_address_city',
        read_only=True
    )
    profile = ProfileSerializerForClient(read_only=True)
    agent_user_id = serializers.ReadOnlyField(source='agent_user.id', read_only=True)
    agent_company_id = serializers.ReadOnlyField(
        source='agent_company.id', read_only=True
    )
    agent_company_inn = serializers.ReadOnlyField(
        source='agent_company.inn', read_only=True
    )
    agent_company_short_name = serializers.ReadOnlyField(
        source='agent_company.short_name', read_only=True
    )

    manager_fio = serializers.ReadOnlyField(
        source='manager.first_name', read_only=True
    )

    class Meta:
        model = Client
        fields = (
            'full_name',
            'short_name',
            'inn',
            'kpp',
            'ogrn',
            'need_sign_regulations',
            'id',
            'phone',
            'email',
            'last_login',
            'legal_address_city',
            'profile',
            'date_last_action',
            'region',
            'winner_notification',
            'agent_user_id',
            'agent_company_id',
            'agent_company_inn',
            'agent_company_short_name',
            'internal_news',
            'work_rules',
            'manager',
            'manager_fio',
        )


class AgentSerializer(serializers.ModelSerializer):
    active_contract_offer = serializers.SerializerMethodField('get_active_contract_offer')
    accept_contract = serializers.BooleanField()

    def get_active_contract_offer(self, obj):
        active_contract_offer = obj.active_contract_offer
        return active_contract_offer and active_contract_offer.contract_id

    class Meta:
        model = Agent
        fields = (
            'full_name',
            'short_name',
            'inn',
            'kpp',
            'ogrn',
            'id',
            'active',
            'confirmed',
            'confirmed_documents',
            'okpto',
            'taxation_type',
            'bank_account_bik',
            'bank_account_bank',
            'bank_account_checking_account',
            'bank_account_correspondent_account',
            'bank_account_address',
            'legal_address',
            'fact_address',
            'equal_fact_and_legal_address',
            'position',
            'document_for_position',
            'last_name',
            'first_name',
            'middle_name',
            'phone',
            'email',
            'series',
            'number',
            'issued_by',
            'when_issued',
            'date_of_birth',
            'place_of_birth',
            'issued_code',
            'internal_news',
            'work_rules',
            'accept_contract',
            'fill_requisites',
            'fill_documents',
            'active_contract_offer'
        )


class AgentIndividualEntrepreneurSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField()
    short_name = serializers.CharField()
    inn = serializers.CharField(read_only=True)
    ogrn = serializers.CharField(read_only=True)
    okpto = serializers.CharField(max_length=50)
    taxation_type = serializers.CharField(max_length=10)
    bank_account_bank = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    bank_account_bik = serializers.CharField(
        max_length=9, validators=[validate_bik]
    )
    bank_account_checking_account = serializers.CharField(
        max_length=20, validators=[validate_checking_account]
    )
    legal_address = serializers.CharField(max_length=512)
    equal_fact_and_legal_address = serializers.BooleanField(default=True)
    fact_address = serializers.CharField(max_length=512)
    middle_name = serializers.CharField(validators=[validate_middle_name], max_length=50)
    first_name = serializers.CharField(validators=[validate_first_name], max_length=50)
    last_name = serializers.CharField(validators=[validate_last_name], max_length=50)
    phone = serializers.CharField(max_length=20)
    email = serializers.CharField(validators=[validate_email], max_length=100)
    series = serializers.CharField(validators=[validate_passport_series])
    number = serializers.CharField(validators=[validate_passport_number])
    issued_by = serializers.CharField(validators=[validate_issued_by])
    when_issued = serializers.DateField()
    date_of_birth = serializers.DateField()
    place_of_birth = serializers.CharField(max_length=100)
    issued_code = serializers.CharField(max_length=8)

    class Meta:
        model = Agent
        fields = (
            'full_name',
            'short_name',
            'inn',
            'ogrn',
            'okpto',
            'taxation_type',
            'bank_account_bank',
            'bank_account_bik',
            'bank_account_checking_account',
            'legal_address',
            'equal_fact_and_legal_address',
            'fact_address',
            'middle_name',
            'first_name',
            'last_name',
            'phone',
            'email',
            'series',
            'number',
            'issued_by',
            'when_issued',
            'date_of_birth',
            'place_of_birth',
            'issued_code',
        )


class AgentPhysicalPersonSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(max_length=100)
    short_name = serializers.CharField(max_length=100)
    inn = serializers.CharField(read_only=True)
    bank_account_bank = serializers.CharField(required=False, allow_blank=True)
    bank_account_bik = serializers.CharField(
        max_length=9, validators=[validate_bik]
    )
    bank_account_checking_account = serializers.CharField(
        max_length=20, validators=[validate_checking_account]
    )
    legal_address = serializers.CharField(max_length=512)

    middle_name = serializers.CharField(validators=[validate_middle_name], max_length=50)
    first_name = serializers.CharField(validators=[validate_first_name], max_length=50)
    last_name = serializers.CharField(validators=[validate_last_name], max_length=50)
    series = serializers.CharField(validators=[validate_passport_series])
    number = serializers.CharField(validators=[validate_passport_number])
    issued_by = serializers.CharField(validators=[validate_issued_by], max_length=100)
    when_issued = serializers.DateField()
    date_of_birth = serializers.DateField()
    place_of_birth = serializers.CharField(max_length=50)
    issued_code = serializers.CharField(max_length=7)
    phone = serializers.CharField(max_length=17)
    email = serializers.CharField(validators=[validate_email], max_length=100)

    class Meta:
        model = Agent
        fields = (
            'full_name',
            'short_name',
            'inn',
            'bank_account_bank',
            'bank_account_bik',
            'bank_account_checking_account',
            'legal_address',
            'middle_name',
            'first_name',
            'last_name',
            'series',
            'number',
            'issued_by',
            'when_issued',
            'date_of_birth',
            'place_of_birth',
            'issued_code',
            'phone',
            'email',
        )


class AgentOrganizationSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField()
    short_name = serializers.CharField()
    inn = serializers.CharField(read_only=True)
    ogrn = serializers.CharField(read_only=True)
    okpto = serializers.CharField(max_length=50)
    taxation_type = serializers.CharField(max_length=10)
    fact_address = serializers.CharField(
        max_length=512, required=False, allow_blank=True, allow_null=True
    )
    legal_address = serializers.CharField(max_length=512)
    equal_fact_and_legal_address = serializers.BooleanField(default=True)
    position = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    document_for_position = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    middle_name = serializers.CharField(validators=[validate_name], max_length=50)
    first_name = serializers.CharField(validators=[validate_name], max_length=50)
    last_name = serializers.CharField(validators=[validate_name], max_length=50)
    phone = serializers.CharField(max_length=20)
    email = serializers.CharField(validators=[validate_email], max_length=100)

    class Meta:
        model = Agent
        fields = (
            'full_name',
            'short_name',
            'inn',
            'ogrn',
            'okpto',
            'taxation_type',
            'legal_address',
            'fact_address',
            'equal_fact_and_legal_address',
            'position',
            'document_for_position',
            'middle_name',
            'first_name',
            'last_name',
            'phone',
            'email',

        )


class CustomPKRelatedField(serializers.PrimaryKeyRelatedField):
    """A PrimaryKeyRelatedField derivative that uses named field for the display value."""

    def __init__(self, **kwargs):
        self.display_field = kwargs.pop("display_field", "name")
        super(CustomPKRelatedField, self).__init__(**kwargs)

    def display_value(self, instance):
        # Use a specific field rather than model stringification
        return getattr(instance, self.display_field)


class AgentProfileSerializer(serializers.ModelSerializer):
    experience = serializers.CharField()
    priority_conditions = serializers.CharField(style={'base_template': 'textarea.html'})
    how_clients = CustomPKRelatedField(queryset=HowClients.objects.all(), many=True)
    equal_fact_crutch = serializers.CharField()
    about_us = serializers.CharField()
    your_banks = serializers.CharField()
    our_banks = CustomPKRelatedField(queryset=Bank.objects.all(), many=True)
    your_city = serializers.CharField()

    def create(self, validate_data):
        data = {k: v for k, v in validate_data.items() if v}
        how_clients_data = None
        our_banks_data = None
        try:
            how_clients_data = data.pop('how_clients')
        except KeyError:
            pass
        try:
            our_banks_data = data.pop('our_banks')
        except KeyError:
            pass
        agent_profile = AgentProfile.objects.create()
        for field in data:
            if data[field]:
                setattr(agent_profile, field, data[field])
        if how_clients_data:
            if HowClients.objects.all().first() is None:
                for key in HowClients.CHOICES:
                    HowClients.objects.create()
            for i in how_clients_data:
                agent_profile.how_clients.add(i)
        if our_banks_data:
            for i in our_banks_data:
                agent_profile.our_banks.add(i)

        agent_profile.save()
        return agent_profile

    def update(self, instance, validate_data):
        data = {k: v for k, v in validate_data.items() if v}
        how_clients_data = None
        our_banks_data = None
        try:
            how_clients_data = data.pop('how_clients')
        except KeyError:
            pass
        try:
            our_banks_data = data.pop('our_banks')
        except KeyError:
            pass
        for field in data:
            setattr(instance, field, data[field])
        if how_clients_data:
            if HowClients.objects.all().first() is None:
                for key in HowClients.CHOICES:
                    HowClients.objects.create()
            instance.how_clients.clear()
            for i in how_clients_data:
                instance.how_clients.add(i)
        if our_banks_data:
            instance.our_banks.clear()
            for i in our_banks_data:
                instance.our_banks.add(i)
        instance.save()
        return instance

    class Meta:
        model = AgentProfile
        fields = (
            'agent',
            'experience',
            'priority_conditions',
            'about_us',
            'id',
            'how_clients',
            'equal_fact_crutch',
            'your_banks',
            'our_banks',
            'your_city'
        )


class BankSerializer(serializers.ModelSerializer):
    calculator = serializers.SerializerMethodField()

    class Meta:
        model = Bank
        fields = (
            'id',
            'full_name',
            'short_name',
            'inn',
            'kpp',
            'ogrn',
            'okpto',
            'legal_address',
            'code',
            'calculator',
        )

    def get_calculator(self, obj):
        try:
            calculator = Calculator.objects.get(credit_organization_code=obj.code)
        except Calculator.DoesNotExist:
            return None

        calculator_data = CalculatorSerializer(calculator, read_only=True).data
        return calculator_data


class RequestRejectionReasonTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestRejectionReasonTemplate
        ordering = ['-id']
        fields = ('id', 'name', 'reason')


class BankInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bank
        fields = (
            'short_name',
            'full_name',
            'id',
        )


class MFOSerializer(ClientSerializer):
    pass


class AgentDocumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentDocumentCategory
        fields = (
            'name',
            'help_text',
        )


class AgentInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = (
            'id',
            'short_name',
            'full_name',
            'inn',
            'ogrn',
            'kpp',
            'is_individual_entrepreneur',
            'is_physical_person',
            'is_organization',
            'last_name',
            'first_name',
            'middle_name',

        )


class CompanyDataAboutOrganizationSerializer(serializers.ModelSerializer):
    inn = serializers.CharField(read_only=True)
    kpp = serializers.CharField(read_only=True)
    ogrn = serializers.CharField(read_only=True)

    class Meta:
        model = Company
        fields = (
            'full_name',
            'inn',
            'kpp',
            'ogrn',
            'legal_address',
        )


class RequisitesSerializer(serializers.ModelSerializer):
    bank_account_bik = serializers.CharField()
    bank_account_bank = serializers.CharField()
    bank_account_checking_account = serializers.CharField()
    bank_account_correspondent_account = serializers.CharField()

    class Meta:
        model = Agent
        fields = (
            'bank_account_bik',
            'bank_account_bank',
            'bank_account_checking_account',
            'bank_account_correspondent_account',
        )


class AgentRequisitesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agent
        fields = (
            'bank_account_bik',
            'bank_account_bank',
            'bank_account_address',
            'bank_account_checking_account',
            'bank_account_correspondent_account',
        )


class AgentDocumentSerializer(serializers.ModelSerializer):
    file = FileSerializer(read_only=True)
    sign = FileSerializer(read_only=True)
    category = AgentDocumentCategorySerializer(read_only=True)

    class Meta:
        model = AgentDocument
        fields = (
            'id',
            'category',
            'file',
            'certificate',
            'sign',
            'signed',
            'comment',
            'document_status',
        )


class AgentInstructionsDocumentsSerializer(serializers.ModelSerializer):
    file = serializers.FileField()

    class Meta:
        model = AgentInstructionsDocuments
        fields = (
            'id',
            'name',
            'name2',
            'file',
            'roles',
            'active',
            'show',
        )


class InternalNewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalNews
        fields = (
            'title',
            'text',
            'created',
        )


class WorkRuleSerializer(serializers.ModelSerializer):
    bank = BankSerializer(read_only=True)

    class Meta:
        model = WorkRule
        fields = (
            'id',
            'text',
            'created',
            'updated',
            'bank',
            'get_bg_type_display',
            'bg_type',
            'limit_from',
            'limit_to',
            'commission',
            'commission_on_excess',
        )


class TenderHelpAgentCommentSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.get_name', read_only=True)

    class Meta:
        model = TenderHelpAgentComment
        fields = (
            'comment',
            'create_time',
            'user'
        )


class TemplateChatBankSerializer(serializers.ModelSerializer):
    files = FileSerializer(read_only=True, many=True)

    class Meta:
        model = TemplateChatBank
        fields = (
            'id',
            'name',
            'template',
            'bank',
            'files',
        )

class TemplateChatAgentSerializer(serializers.ModelSerializer):
    files = FileSerializer(read_only=True, many=True)

    class Meta:
        model = TemplateChatAgent
        fields = (
            'id',
            'name',
            'template',
            'user',
            'files',
        )

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class TemplateChatBankSerializerForItems(serializers.ModelSerializer):
    text = serializers.CharField(source='name')
    value = serializers.CharField(source='template')

    class Meta:
        model = TemplateChatBank
        fields = (
            'text',
            'value',
        )


class TemplateChatMFOSerializerForItems(serializers.ModelSerializer):
    text = serializers.CharField(source='name')
    value = serializers.CharField(source='template')

    class Meta:
        model = TemplateChatMFO
        fields = (
            'text',
            'value',
        )


class AgentSerializerForSelectInput(serializers.ModelSerializer):
    """Сериализатор для модели Агент для NewSelectInput.vue"""
    text = serializers.CharField(source='short_name', read_only=True)
    value = serializers.IntegerField(source='id', read_only=True)

    class Meta:
        model = Agent
        fields = (
            'text',
            'value',
        )

class AgentRewardsSerrializer(serializers.ModelSerializer):
    class Meta:
        model = AgentRewards
        fields = (
            'date',
            'agent_id',
            'bank_id',
            'number_requests',
            'percent',
        )


class BankBlackListSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankStopInn
        ordering = ['-id']
        fields = ('id', 'inn')
