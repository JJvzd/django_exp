import logging
from collections import OrderedDict, Mapping

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import NOT_PROVIDED
from django.utils.functional import cached_property
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.fields import get_error_detail
from rest_framework.fields import set_value, SkipField
from rest_framework.settings import api_settings

from cabinet.models import OrganizationForms, Certificate, Region, System
from external_api.dadata_api import DaData
from files.models import BaseFile
from questionnaire.models import (
    Profile, BankAccount, KindOfActivity, LicensesSRO, PassportDetails,
    DocumentGenDir, ProfilePartnerIndividual, ProfilePartnerLegalEntities
)
from utils.helpers import ValidationErrors
from utils.validators import validate_checking_okpo, validate_checking_account

logger = logging.getLogger('django')


class SaveWithoutValidateMixin:
    @cached_property
    def default_values(self):
        default_values = {}
        for element in self.Meta.model._meta.concrete_fields:
            default_values.update({element.name: element.default})
        return default_values

    def is_empty(self, *args):
        default_values = self.default_values
        data = self.validated_data
        for field in data:
            if field in args or not data[field]:
                continue
            if isinstance(default_values[field], NOT_PROVIDED) and not bool(data[field]):
                continue
            elif default_values[field] == data[field]:
                continue
            else:
                return False
        return True

    def save(self, *args):
        self.is_valid(raise_exception=False)
        self._errors = []
        return super().save()


class Serializer(SaveWithoutValidateMixin, serializers.ModelSerializer):

    def to_internal_value(self, data):
        """
        Dict of native values <- Dict of primitive datatypes.
        """
        if not isinstance(data, Mapping):
            message = self.error_messages['invalid'].format(
                datatype=type(data).__name__
            )
            raise ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: [message]
            }, code='invalid')

        ret = OrderedDict()
        errors = OrderedDict()
        fields = self._writable_fields

        for field in fields:
            validate_method = getattr(self, 'validate_' + field.field_name, None)
            primitive_value = field.get_value(data)
            try:
                validated_value = field.run_validation(primitive_value)
                if validate_method is not None:
                    validated_value = validate_method(validated_value)
            except ValidationError as exc:
                if primitive_value:
                    set_value(ret, field.source_attrs, primitive_value)
                errors[field.field_name] = exc.detail
            except DjangoValidationError as exc:
                errors[field.field_name] = get_error_detail(exc)
            except SkipField:
                pass
            else:
                set_value(ret, field.source_attrs, validated_value)

        return ret

    def is_valid(self, raise_exception=False):
        assert not hasattr(self, 'restore_object'), (
                'Serializer `%s.%s` has old-style version 2 `.restore_object()` '
                'that is no longer compatible with REST framework 3. '
                'Use the new-style `.create()` and `.update()` methods instead.' %
                (self.__class__.__module__, self.__class__.__name__)
        )

        assert hasattr(self, 'initial_data'), (
            'Cannot call `.is_valid()` as no `data=` keyword argument was '
            'passed when instantiating the serializer instance.'
        )

        if not hasattr(self, '_validated_data'):
            try:
                self._validated_data = self.run_validation(self.initial_data)
            except ValidationError as exc:
                self._validated_data = {}
                self._errors = exc.detail
            else:
                self._errors = {}
                self._validated_data = self.to_internal_value(self.initial_data)

        if self._errors and raise_exception:
            raise ValidationError(self.errors)

        return not bool(self._errors)


class OrganizationFormsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationForms
        fields = (
            'id',
            'name',
            'code',
        )


class ProfileSerializer(serializers.ModelSerializer):
    bank_accounts = serializers.SerializerMethodField('get_bank_accounts')
    general_director = serializers.SerializerMethodField('get_general_director')
    booker = serializers.SerializerMethodField('get_booker')
    persons = serializers.SerializerMethodField('get_persons')
    activities = serializers.SerializerMethodField('get_activities')
    licenses_sro = serializers.SerializerMethodField('get_licenses_sro')
    legal_shareholders = serializers.SerializerMethodField('get_legal_shareholders')
    is_organization = serializers.BooleanField(
        source='client.is_organization', read_only=True
    )

    full_name = serializers.CharField(required=True)
    short_name = serializers.CharField(required=True)
    tax_system = serializers.CharField(required=True)
    reg_state_date = serializers.DateField(required=True)
    reg_inn = serializers.CharField(read_only=True)
    reg_ogrn = serializers.CharField(required=True)
    reg_okato = serializers.CharField(required=True)
    reg_okpo = serializers.CharField(required=True, validators=[validate_checking_okpo])
    code_oktmo = serializers.CharField(required=True)
    legal_address = serializers.CharField(required=True)
    contact_name = serializers.CharField(required=True)
    contact_phone = serializers.CharField(required=True)
    contact_email = serializers.CharField(required=True)
    # authorized_capital_paid = serializers.CharField(required=True)
    # authorized_capital_announced = serializers.CharField(required=True)
    number_of_employees = serializers.CharField(required=True)
    salary_fund = serializers.CharField(required=True)

    def validate(self, data):
        errors = ValidationErrors()
        if not data.get('legal_address_status'):
            if not data.get('legal_address_from'):
                errors.add_error('legal_address_from', 'Не указана дата начала аренды')
            if not data.get('legal_address_to'):
                errors.add_error('legal_address_to', 'Не указана дата окончания аренды')

        if not data.get('fact_is_legal_address'):
            if not data.get('fact_address'):
                errors.add_error('fact_address', 'Не указан фактический адрес')
            if not data.get('fact_address_status'):
                if not data.get('fact_address_from'):
                    errors.add_error('fact_address_from', 'Не указана дата начала аренды')
                if not data.get('fact_address_to'):
                    errors.add_error('fact_address_to',
                                     'Не указана дата окончания аренды')
        if data.get('is_organization'):
            if not data.get('reg_kpp'):
                errors.add_error('reg_kpp', 'Поле не может быть пустым')
            if not data.get('organization_form'):
                errors.add_error('organization_form',
                                 'Не указана организационно-правовая форма')
            if not data.get('authorized_capital_paid'):
                errors.add_error('authorized_capital_paid', 'Не указан Оплаченный УК')
            if not data.get('authorized_capital_announced'):
                errors.add_error('authorized_capital_announced',
                                 'Не указан Объявленный УК')
        errs = errors.get_errors()
        if errs:
            raise serializers.ValidationError(errs)
        return data

    def get_bank_accounts(self, profile):
        bank_accounts = profile.bankaccount_set.all().order_by('id')
        return BankAccountSerializer(bank_accounts, many=True).data

    def get_general_director(self, profile):
        general_director = profile.profilepartnerindividual_set.filter(
            is_general_director=True).first()
        if not general_director:
            general_director = profile.profilepartnerindividual_set.create(
                is_general_director=True
            )
        return GeneralDirectorSerializer(general_director).data

    def get_booker(self, profile):
        return ProfilePartnerIndividualSerializer(
            profile.profilepartnerindividual_set.filter(is_booker=True).first()).data

    def get_persons(self, profile):
        persons = profile.profilepartnerindividual_set.filter(
            is_general_director=False
        ).order_by('id')
        return ProfilePartnerIndividualSerializer(persons, many=True).data

    def get_legal_shareholders(self, profile):
        legal_shareholders = profile.profilepartnerlegalentities_set.all().order_by('id')
        return ProfilePartnerLegalEntitiesSerializer(legal_shareholders, many=True).data

    def get_activities(self, profile):
        activites = profile.kindofactivity_set.all().order_by('id')
        return ProfileViewActivitySerializer(activites, many=True).data

    def get_licenses_sro(self, profile):
        licenses = profile.licensessro_set.all().order_by('id')
        return LicensesSROSerializer(licenses, many=True).data

    class Meta:
        model = Profile
        fields = (
            'id',
            # Общие данные
            'full_name',
            'short_name',
            'organization_form',
            'tax_system',
            'reg_state_date',
            'reg_inn',
            'reg_kpp',
            'reg_ogrn',
            'reg_okato',
            'reg_okpo',
            'code_oktmo',
            # Юридический адрес
            'legal_address',
            'legal_address_status',
            'legal_address_from',
            'legal_address_to',
            'fact_is_legal_address',
            # Фактический адрес
            'fact_address',
            'fact_address_status',
            'fact_address_from',
            'fact_address_to',
            # Контакты организации
            'contact_name',
            'contact_phone',
            'contact_email',
            # Размер уставного капитала
            'authorized_capital_paid',
            'authorized_capital_announced',
            # Численность работников и фонд оплаты труда
            'number_of_employees',
            'salary_fund',
            # Наличие лицензий СРО
            'is_member_sro',
            'has_license_sro',

            'booker',
            'general_director',
            'bank_accounts',
            'persons',
            'activities',
            'licenses_sro',
            'legal_shareholders',

            'is_organization',

            # Дополнительные сведения
            'is_retail',
            'has_offense',
            'offense',
            'source_of_money',
            'is_strategic_enterprise',
            'has_debt_to_state_budget',
            'has_card_of_unpaid_bills',
            'has_arrears_more_25_net_assets',
            'is_bankrupt_or_liquidation',
            'has_active_product_from_SPB',
            'is_pdl',
            'is_rpdl',
            'has_debt_for_last_24_months',
            'debt_for_lat_24_months',
            'has_wage_arrears',
            'reason_wage_arrears',
            'has_tax_debt',
            'reason_tax_debt',
            'finance_state1',
            'finance_state2',
            'finance_state3',
            'finance_state4',
        )


class ProfileSerializerForClient(serializers.ModelSerializer):
    persons = serializers.SerializerMethodField('get_persons')

    def get_persons(self, obj):
        return [
            {
                'name': person.get_name,
                'share': person.share,
                'id': person.id
            } for person in obj.profilepartnerindividual_set.exclude(
                is_general_director=True
            ).order_by('-share')
        ]

    class Meta:
        model = Profile
        fields = (
            'id',
            # Юридический адрес
            'legal_address',
            # Контакты организации
            'contact_phone',
            'contact_email',
            'short_name',
            'persons',
        )


class BankAccountSerializer(serializers.ModelSerializer):
    bank = serializers.CharField(required=True)
    bank_bik = serializers.CharField(required=True)
    bank_account_number = serializers.CharField(
        required=True, validators=[validate_checking_account]
    )
    correspondent_account = serializers.CharField(required=True)
    has_unpaid_account = serializers.BooleanField()

    class Meta:
        model = BankAccount
        fields = (
            'bank',
            'bank_bik',
            'bank_account_number',
            'has_unpaid_account',
            'correspondent_account',
            'profile',
            'id',
        )


class ProfileViewActivitySerializer(serializers.ModelSerializer):
    value = serializers.CharField(required=True)

    class Meta:
        model = KindOfActivity
        fields = (
            'value',
            'profile',
            'id',
        )


class LicensesSROSerializer(serializers.ModelSerializer):
    view_activity = serializers.CharField(required=True)
    number_license = serializers.CharField(required=True)
    date_issue_license = serializers.DateField(required=True)
    issued_by_license = serializers.CharField(required=True)
    list_of_activities = serializers.CharField(required=True)

    def validate(self, data):
        errors = ValidationErrors()
        if not data.get('is_indefinitely') and not data.get('date_end_license'):
            errors.add_error('date_end_license', 'Не указана дата окончания лицензии')
        errs = errors.get_errors()
        if errs:
            raise serializers.ValidationError(errs)

        return super(LicensesSROSerializer, self).validate(data)

    class Meta:
        model = LicensesSRO
        fields = (
            'view_activity',
            'number_license',
            'date_issue_license',
            'is_indefinitely',
            'date_end_license',
            'issued_by_license',
            'list_of_activities',
            'profile',
            'id',
        )


class PassportDetailsSerializer(serializers.ModelSerializer):
    series = serializers.CharField(max_length=4, required=True)
    number = serializers.CharField(max_length=6, required=True)
    issued_by = serializers.CharField(required=True)
    when_issued = serializers.DateField(required=True)
    date_of_birth = serializers.DateField(required=True)
    place_of_birth = serializers.CharField(required=True)
    place_of_registration = serializers.CharField(required=True)
    issued_code = serializers.CharField(required=True)

    class Meta:
        model = PassportDetails
        fields = (
            'series',
            'number',
            'issued_by',
            'when_issued',
            'date_of_birth',
            'place_of_birth',
            'place_of_registration',
            'issued_code',
            'id',
        )


class DocumentGenDirSerializer(serializers.ModelSerializer):
    name_and_number = serializers.CharField(required=True)
    date_protocol_EIO = serializers.DateField(required=True)
    number_protocol_EIO = serializers.CharField(required=True)
    is_indefinitely = serializers.BooleanField(allow_null=False)

    def validate(self, data):
        errors = ValidationErrors()
        if data.get('is_indefinitely') is False and not data.get('expiration_date'):
            errors.add_error('expiration_date', 'Не указана дата окончания полномочий')
        if data.get('is_indefinitely') is None:
            errors.add_error('is_indefinitely', 'Не указана дата окончания полномочий')

        errs = errors.get_errors()
        if errs:
            raise serializers.ValidationError(errs)

        return data

    class Meta:
        model = DocumentGenDir
        fields = (
            'name_and_number',
            'date_protocol_EIO',
            'number_protocol_EIO',
            'expiration_date',
            'is_indefinitely',
            'id',
        )


class ProfilePartnerIndividualSerializer(serializers.ModelSerializer):
    passport = PassportDetailsSerializer(required=False)
    document_gen_dir = DocumentGenDirSerializer(required=False)
    last_name = serializers.CharField(required=True)
    first_name = serializers.CharField(required=True)
    middle_name = serializers.CharField(required=True)
    citizenship = serializers.CharField(required=True)
    another_country_citizen = serializers.BooleanField(required=True)
    resident = serializers.BooleanField(required=True)
    fiz_inn = serializers.CharField(required=True)

    def validate(self, data):
        errors = ValidationErrors()
        if data.get('is_beneficiary') and not data.get('share'):
            errors.add_error('share', 'Не указана доля')
        if data.get('has_russian_passport') is False and not data.get('another_passport'):
            errors.add_error('passport', 'Не указаны паспортные данные')

        if data.get('is_general_director'):
            if not data.get('experience_this_industry'):
                errors.add_error('experience_this_industry',
                                 'Не указан опыт в данной должности')
            if not data.get('gen_dir_post'):
                errors.add_error('gen_dir_post', 'Не указана Должность(согласно уставу)')
        errs = errors.get_errors()
        if errs:
            raise serializers.ValidationError(errs)
        return data

    def to_internal_value(self, data):

        if data.get('has_russian_passport') is False and 'passport' in data.keys():
            del data['passport']
        if data.get('is_general_director') is False and 'document_gen_dir' in data.keys():
            del data['document_gen_dir']
        return super(ProfilePartnerIndividualSerializer, self).to_internal_value(data)

    class Meta:
        model = ProfilePartnerIndividual
        fields = (
            'last_name',
            'first_name',
            'middle_name',
            'has_russian_passport',
            'passport',
            'another_passport',
            'citizenship',
            'another_country_citizen',
            'resident',
            'fiz_inn',
            'snils',
            'share',
            'is_general_director',
            'is_beneficiary',
            'is_booker',
            'document_another_country',
            'migration_card_number',
            'migration_card_date_from',
            'migration_card_date_to',
            'foreign_citizenship_number',
            'foreign_citizenship_date_from',
            'foreign_citizenship_date_to',
            'visa_card_number',
            'visa_card_date_from',
            'visa_card_date_to',
            'gen_dir_post',
            'document_gen_dir',
            'experience_this_industry',
            'profile',
            'id',
        )


class GeneralDirectorSerializer(ProfilePartnerIndividualSerializer):
    document_gen_dir = DocumentGenDirSerializer(required=True)
    experience_this_industry = serializers.CharField(required=True)
    share = serializers.FloatField(required=False, allow_null=True)

    def __init__(self, *args, **kwargs):
        super(GeneralDirectorSerializer, self).__init__(*args, **kwargs)
        self.fields['share'].required = False

    def create(self, validate_data):
        doc_data = validate_data.pop('document_gen_dir', {})
        instance = super(GeneralDirectorSerializer, self).create(validate_data)
        try:
            doc_data.pop('id')
            DocumentGenDir.objects.filter(
                id=instance.document_gen_dir.id
            ).update(**doc_data)
        except Exception as e:
            logger.exception(e)
            DocumentGenDir.objects.create(person=instance, **doc_data)

    def update(self, instance, validated_data):
        doc_data = validated_data.pop('document_gen_dir', {})
        if instance.document_gen_dir:
            doc_data.pop('id', None)
            DocumentGenDir.objects.filter(
                id=instance.document_gen_dir.id
            ).update(**doc_data)
        else:
            DocumentGenDir.objects.create(person=instance, **doc_data)
        return super(GeneralDirectorSerializer, self).update(instance, validated_data)


class ProfilePartnerLegalEntitiesSerializer(Serializer):
    passport = PassportDetailsSerializer(required=False)
    name = serializers.CharField(required=True)
    inn = serializers.CharField(required=True)
    ogrn = serializers.CharField(required=True)
    kpp = serializers.CharField(required=True)
    place = serializers.CharField(required=True)
    share = serializers.FloatField(required=True)

    class Meta:
        model = ProfilePartnerLegalEntities
        fields = (
            'name',
            'inn',
            'ogrn',
            'kpp',
            'place',
            'share',
            'last_name',
            'first_name',
            'middle_name',
            'passport',
            'citizenship',
            'another_country_citizen',
            'document_another_country',
            'profile',
            'id',
        )

    def validate(self, data):
        errors = ValidationErrors()
        if data.get('inn') is None:
            errors.add_error('inn', 'Поле не может быть пустым')
        if data.get('name') is None:
            errors.add_error('name', 'Поле не может быть пустым')
        if data.get('ogrn') is None:
            errors.add_error('ogrn', 'Поле не может быть пустым')
        if data.get('kpp') is None:
            errors.add_error('kpp', 'Поле не может быть пустым')
        if data.get('place') is None:
            errors.add_error('place', 'Поле не может быть пустым')
        if data.get('share') is None:
            errors.add_error('share', 'Поле не может быть пустым')

        errs = errors.get_errors()
        if errs:
            raise serializers.ValidationError(errs)

        return data


class CertificateSerializer(serializers.ModelSerializer):
    """Сериализатор модели сертификатов"""

    class Meta:
        model = Certificate
        fields = (
            'org_name',
            'fio',
            'number',
            'date_granted',
            'date_end',
            'subject_name',
            'issuer_name',
            'algorithm',
            'uc',
        )


class FileSerializer(serializers.ModelSerializer):
    file_name = serializers.ReadOnlyField(source='file.filename')
    file_url = serializers.SerializerMethodField(method_name='get_file_url')
    file_pretty_size = serializers.ReadOnlyField(source='file.pretty_size')
    download_name = serializers.ReadOnlyField(source='get_download_name')
    sign = serializers.SerializerMethodField(method_name='get_sign')
    old_sign = serializers.SerializerMethodField(method_name='get_old_sign')

    def get_signer(self, object, signer=None):
        if not signer:
            signer = object.author
        # TODO: Неочевидный код, нужно переделать
        request_document = object.requestdocument_set.all().first()
        if request_document:
            signer = request_document.request.client
        return signer

    def get_sign(self, object):
        author = self.get_signer(object, self.context.get('signer', None))

        request_document = object.requestdocument_set.all().first()
        if request_document:
            author = request_document.request.client
        sign = object.sign_set.filter(author=author).first()

        if sign:
            return {
                'sign_file': sign.signed_file.url,
                'sign_name': sign.signed_file.filename,
                'created': sign.signed_date,
                'certificate': CertificateSerializer(sign.certificate).data
            }
        return {}

    def get_old_sign(self, object):
        author = self.get_signer(object, self.context.get('signer', None))
        sign = object.separatedsignature_set.filter(
            author_id=author.id
        ).first()
        if sign:
            return {
                'sign_file': sign.sign,
                'created': sign.created,
                'certificate': CertificateSerializer(sign.certificate).data
            }
        return {}

    def get_file_url(self, obj):
        url = obj.file.url
        url = url.replace('%20', ' ')
        wrong_path = '/media%s' % settings.BASE_DIR
        if wrong_path in url:
            url = url.replace(wrong_path, '')
            return url
        return obj.file.url

    class Meta:
        model = BaseFile
        fields = (
            'id',
            'created',
            'file_name',
            'file_url',
            'file_pretty_size',
            'download_name',
            'sign',
            'old_sign',
        )


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = (
            'name'
        )


"""Сериализационные модели для ИНБАНКА"""


class PassportSerializerInbank(serializers.ModelSerializer):
    series = serializers.CharField(read_only=True)
    number = serializers.CharField(read_only=True)
    issued_who = serializers.CharField(source='issued_by', read_only=True)
    issued_when = serializers.DateField(
        source='when_issued', read_only=True, format='%d.%m.%Y'
    )
    issued_code = serializers.CharField(source='issued_code_format', read_only=True)
    registration = serializers.CharField(source='place_of_registration', read_only=True)
    birthday = serializers.DateField(
        source='date_of_birth', read_only=True, format='%d.%m.%Y'
    )
    birthday_place = serializers.CharField(source='place_of_birth', read_only=True)

    class Meta:
        model = PassportDetails
        fields = (
            'series',
            'number',
            'issued_who',
            'issued_when',
            'issued_code',
            'registration',
            'birthday',
            'birthday_place'
        )


class LegalShareholderSerializerInbank(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    inn = serializers.CharField(read_only=True)
    ogrn = serializers.CharField(read_only=True)
    placement = serializers.CharField(source='place', read_only=True)
    share = serializers.DecimalField(read_only=True, max_digits=5, decimal_places=2)

    class Meta:
        models = ProfilePartnerLegalEntities
        fields = (
            'name',
            'inn',
            'ogrn',
            'placement',
            'share'
        )


class PhysicalShareholderSerializerInbank(serializers.ModelSerializer):
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    middle_name = serializers.CharField(read_only=True)
    share = serializers.DecimalField(read_only=True, max_digits=5, decimal_places=2)
    inn = serializers.CharField(source='fiz_inn', read_only=True)
    snils = serializers.CharField(read_only=True, source='format_snils')
    citizenship = serializers.CharField(read_only=True)
    document_type = serializers.SerializerMethodField('is_passport')
    passport = PassportSerializerInbank(read_only=True)
    passport_details = serializers.CharField(source='another_passport', read_only=True)

    def is_passport(self, shareholder):
        if shareholder.has_russian_passport:
            return 'Паспорт'
        else:
            return 'Иное'

    @property
    def data(self):
        data = super(PhysicalShareholderSerializerInbank, self).data
        if data['document_type'] == 'Паспорт':
            data.pop('passport_details')
        else:
            data.pop('passport')
        return data

    class Meta:
        model = ProfilePartnerIndividual
        fields = (
            'first_name',
            'last_name',
            'middle_name',
            'share',
            'inn',
            'snils',
            'citizenship',
            'document_type',
            'passport',
            'passport_details',
        )


class BankAccountSerializerInbank(serializers.ModelSerializer):
    bank = serializers.CharField(read_only=True)
    bik = serializers.CharField(source='bank_bik', read_only=True)
    account = serializers.CharField(source='bank_account_number', read_only=True)
    correspondent_account = serializers.CharField(read_only=True)
    have_unpaid_bills = serializers.SerializerMethodField('have_unpaid')

    def have_unpaid(self, account):
        if account.has_unpaid_account:
            return '1'
        else:
            return '0'

    class Meta:
        model = BankAccount
        fields = (
            'bank',
            'bik',
            'account',
            'correspondent_account',
            'have_unpaid_bills',
        )


class LicenseSROSerializerInbank(serializers.ModelSerializer):
    name = serializers.CharField(source='view_activity', read_only=True)
    number = serializers.CharField(source='number_license', read_only=True)
    date_from = serializers.DateField(
        source='date_issue_license', format='%d.%m.%Y', read_only=True
    )
    date_to = serializers.SerializerMethodField('get_date_to')
    issued_by = serializers.CharField(source='issued_by_license', read_only=True)
    activites = serializers.CharField(source='list_of_activities', read_only=True)

    def get_date_to(self, license):
        if license.is_indefinitely:
            return 'Бессрочная'
        else:
            return license.date_end_license.strftime('%d.%m.%Y')

    class Meta:
        model = LicensesSRO
        fields = (
            'name',
            'number',
            'date_from',
            'date_to',
            'issued_by',
            'activites',
        )


class GeneralDirectorSerializerInbank(serializers.ModelSerializer):
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    middle_name = serializers.CharField(read_only=True)
    post = serializers.CharField(source='document_gen_dir.gen_dir_doc_right')
    share = serializers.DecimalField(read_only=True, max_digits=5, decimal_places=2)
    document_type = serializers.SerializerMethodField('is_passport')
    citizenship = serializers.CharField(read_only=True)
    is_general_accountant = serializers.SerializerMethodField('get_is_general_accountant')
    passport = PassportSerializerInbank(read_only=True)
    passport_details = serializers.CharField(source='another_passport', read_only=True)
    snils = serializers.CharField(read_only=True, source='format_snils')

    def get_is_general_accountant(self, shareholder):
        if shareholder.is_booker:
            return 1
        else:
            return 0

    def is_passport(self, shareholder):
        if shareholder.has_russian_passport:
            return 'Паспорт'
        else:
            return 'Иное'

    @property
    def data(self):
        data = super(GeneralDirectorSerializerInbank, self).data
        if data['document_type'] == 'Паспорт':
            data.pop('passport_details')
        else:
            data.pop('passport')
        return data

    class Meta:
        model = ProfilePartnerIndividual
        fields = (
            'first_name',
            'last_name',
            'middle_name',
            'post',
            'share',
            'document_type',
            'citizenship',
            'is_general_accountant',
            'passport',
            'passport_details',
            'snils',

        )


class BookerSerializerInbank(serializers.ModelSerializer):
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    middle_name = serializers.CharField(read_only=True)
    post = serializers.CharField(source='booker_document')
    citizenship = serializers.CharField(read_only=True)
    document_type = serializers.SerializerMethodField('is_passport')
    passport = PassportSerializerInbank(read_only=True)
    passport_details = serializers.CharField(source='another_passport', read_only=True)

    def is_passport(self, shareholder):
        if shareholder.has_russian_passport:
            return 'Паспорт'
        else:
            return 'Иное'

    @property
    def data(self):
        data = super(BookerSerializerInbank, self).data
        if data['document_type'] == 'Паспорт':
            data.pop('passport_details')
        else:
            data.pop('passport')
        return data

    class Meta:
        model = ProfilePartnerIndividual
        fields = (
            'first_name',
            'last_name',
            'middle_name',
            'post',
            'citizenship',
            'document_type',
            'passport',
            'passport_details',
        )


class ProfileSerializerInbank(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    short_name = serializers.CharField(read_only=True)
    inn = serializers.CharField(source='reg_inn', read_only=True)
    ogrn = serializers.CharField(source='reg_ogrn', read_only=True)
    kpp = serializers.CharField(source='reg_kpp', read_only=True)
    okato = serializers.CharField(source='reg_okato', read_only=True)
    okpo = serializers.CharField(source='reg_okpo', read_only=True)
    oktmo = serializers.CharField(source='reg_oktmo', read_only=True)
    registration_date = serializers.DateField(
        source='reg_state_date', format='%d.%m.%Y', read_only=True
    )
    organization_form = serializers.CharField(
        read_only=True, source='get_organization_form_display'
    )
    nalog_system = serializers.CharField(source='get_tax_system_display', read_only=True)
    paid_share_capital = serializers.DecimalField(
        source='authorized_capital_paid', read_only=True, max_digits=19, decimal_places=2
    )
    announced_share_capital = serializers.DecimalField(
        source='authorized_capital_announced', read_only=True,
        max_digits=19, decimal_places=2
    )
    number_of_employees = serializers.CharField(read_only=True)
    salary_fund = serializers.CharField(read_only=True)
    contacts = serializers.SerializerMethodField('get_contacts')
    licenses = LicenseSROSerializerInbank(read_only=True, many=True)
    beneficiaries = PhysicalShareholderSerializerInbank(source='beneficiars', many=True)
    legal_address = serializers.SerializerMethodField('get_legal_address')
    fact_address = serializers.SerializerMethodField('get_fact_address')
    general_director = GeneralDirectorSerializerInbank(read_only=True)
    general_accountant = BookerSerializerInbank(source='booker', read_only=True)
    legal_shareholders = LegalShareholderSerializerInbank(
        source='persons_entities', read_only=True, many=True
    )
    physical_shareholders = PhysicalShareholderSerializerInbank(
        source='persons', read_only=True, many=True
    )
    bank_accounts = BankAccountSerializerInbank(
        source='profileaccounts', read_only=True, many=True
    )

    def get_fact_address(self, profile):
        if profile.fact_address:
            dict_address = cache.get('dadata_address:%s' % profile.fact_address)
            if not dict_address:
                api = DaData()
                data = api.get_address_suggest(profile.fact_address)['suggestions'][0][
                    'data']
                street = '%s %s, %s, %s' % (
                    data['street_type_full'], data['street'], data['house'], data['flat'])
                if data['flat_area']:
                    street += ', %s' % data['flat_area']
                dict_address = {
                    'index': data['postal_code'],
                    'city': ('%s %s' % (data['city_type_full'], data['city'])).upper(),
                    'street': street,
                    'status': 'Собственность' if profile.fact_address_status else 'Аренда'
                }
                cache.add('dadata_address:%s' % profile.fact_address, dict_address,
                          60 * 60 * 24 * 30)
            if not profile.fact_address_status:
                dict_address.update({
                    'arenda_from': profile.fact_address_from.strftime('%d.%m.%Y'),
                    'arenda_to': profile.fact_address_to.strftime('%d.%m.%Y'),
                })
            return dict_address
        else:
            return {
                'index': '',
                'city': '',
                'street': '',
                'status': '',
            }

    def get_legal_address(self, profile):
        legal_address = profile.legal_address
        if not legal_address:
            legal_address = profile.getAddressFromEGRUL
            if not legal_address:
                return {
                    'index': '',
                    'city': '',
                    'street': '',
                    'status': '',
                    'equal_fact_address': '',
                }
            dict_address = cache.get('dadata_address:%s' % legal_address)
            if not dict_address:
                api = DaData()
                data = api.get_address_suggest(legal_address)['suggestions'][0]['data']
                street = '%s %s, %s, %s' % (
                    data['street_type_full'], data['street'], data['house'], data['flat'])
                if data['flat_area']:
                    street += ', %s' % data['flat_area']

                status = 'Собственность' if profile.legal_address_status else 'Аренда'
                dict_address = {
                    'index': data['postal_code'],
                    'city': ('%s %s' % (data['city_type_full'], data['city'])).upper(),
                    'street': street,
                    'status': status
                }
                cache.add('dadata_address:%s' % legal_address, dict_address,
                          60 * 60 * 24 * 30)
            if not profile.legal_address_status:
                dict_address.update({
                    'arenda_from': profile.legal_address_from.strftime('%d.%m.%Y'),
                    'arenda_to': profile.legal_address_to.strftime('%d.%m.%Y'),
                })
            dict_address.update({
                'equal_fact_address': '1' if profile.fact_is_legal_address else '0'
            })
            return dict_address

    def get_contacts(self, profile):
        return {
            'person_name': profile.contact_name,
            'phone': profile.get_contact_phone,
            'email': profile.contact_email,
        }

    class Meta:
        model = Profile
        fields = (
            'id',
            'full_name',
            'short_name',
            'inn',
            'ogrn',
            'kpp',
            'okato',
            'okpo',
            'oktmo',
            'registration_date',
            'organization_form',
            'nalog_system',
            'paid_share_capital',
            'announced_share_capital',
            'number_of_employees',
            'salary_fund',
            'contacts',
            'licenses',
            'beneficiaries',
            'legal_address',
            'fact_address',
            'general_director',
            'general_accountant',
            'legal_shareholders',
            'physical_shareholders',
            'bank_accounts',
        )


class SystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = System
        fields = (
            'id', 'site_on', 'scoring_on', 'auto_save', 'strong_check', 'inn_check',
            'cnt_right', 'archive_days', 'bank_stop_inn', 'global_stop_inn', 'algorithm',
            'ogrn', 'subject_sign_tool', 'issuer_sign_tool', 'certificate_policies', 'uc',
            'check_profile', 'limit_file_size', 'static_pages', 'notifications_enabled',
            'admin_email', 'email_support', 'email_calculator', 'email_callback',
            'agents_counter', 'msp_notify', 'validate_sign', 'request_number',
            'cert_valid', 'tenderhelp_loan_offer_percent', 'default_agent',
            'one_package_documents', 'default_scoring_rules', 'email_new_agent'
        )


class SystemCheckCertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = System
        fields = (
            "algorithm",
            "ogrn",
            "uc",
            "subject_sign_tool",
            "issuer_sign_tool",
            "certificate_policies",
            "cert_valid",
        )


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password1 = serializers.CharField(required=True)
    new_password2 = serializers.CharField(required=True)
