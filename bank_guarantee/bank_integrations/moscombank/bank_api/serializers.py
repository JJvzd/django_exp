from django.core.cache import cache
from django.utils import timezone
from rest_framework import serializers

from bank_guarantee.models import (
    ContractPlacementWay, ContractType, Request, ExternalRequest
)
from cabinet.constants.constants import FederalLaw, TaxationType, OrganizationForm, Target
from clients.models import Client, EgrulData
from external_api.dadata_api import DaData
from questionnaire.models import (
    Profile, LicensesSRO, BankAccount, ProfilePartnerIndividual
)
from utils.helpers import change_phone


class RequestMosKomBank(serializers.ModelSerializer):
    number = serializers.CharField(source='tender.notification_id', read_only=True)
    sum = serializers.FloatField(source='required_amount', read_only=True)
    sum_proposed = serializers.FloatField(source='suggested_price_amount', read_only=True)
    bg_term_1 = serializers.DateField(
        source='interval_from', format='%d.%m.%Y', read_only=True
    )
    bg_term_2 = serializers.DateField(
        source='interval_to', format='%d.%m.%Y', read_only=True
    )
    date_c = serializers.DateField(source='final_date', format='%d.%m.%Y', read_only=True)
    indisputable_cancellation = serializers.SerializerMethodField(
        'get_indisputable_cancellation'
    )
    summary_protocol = serializers.SerializerMethodField('get_summary_protocol')  # noqa TODO уточнить
    number_report = serializers.SerializerMethodField('get_number_report')
    date_p = serializers.DateField(
        source='protocol_date', format='%d.%m.%Y', read_only=True
    )
    text_v_r = serializers.SerializerMethodField('get_text_v_r')
    source_financing = serializers.SerializerMethodField('get_source_financing')  # noqa TODO уточнить
    subcontractor_text = serializers.SerializerMethodField('get_subcontractor_text')  # noqa TODO уточнить
    type_contract = serializers.SerializerMethodField('get_type_contract')  # noqa TODO уточнить
    type_order = serializers.SerializerMethodField('get_type_order')  # TODO уточнить
    text_contract = serializers.CharField(source='tender.subject', read_only=True)
    contract_number = serializers.SerializerMethodField('get_contract_number')  # noqa TODO уточнить
    contract_date = serializers.SerializerMethodField('get_contract_date')  # noqa TODO уточнить
    contract_number_this = serializers.SerializerMethodField('get_contract_number_this')
    types_software = serializers.SerializerMethodField('get_types_software')  # noqa TODO уточнить
    text_software = serializers.SerializerMethodField('get_text_software')  # noqa TODO уточнить

    def get_number_report(self, profile):
        return 0

    def get_contract_number_this(self, request):
        return 1

    def get_text_software(self, request):
        return ''

    def get_types_software(self, request):
        return ''

    def get_contract_date(self, request):
        return ''

    def get_contract_number(self, request):
        return ''

    def get_type_order(self, request):
        if request.placement_way == ContractPlacementWay.COMPETITION:
            return 71
        elif request.placement_way == ContractPlacementWay.AUCTION:
            return 67
        elif request.placement_way == ContractPlacementWay.ELECTRONIC_AUCTION:
            return 68
        elif request.placement_way == ContractPlacementWay.CLOSED_BIDDING:
            return 70
        else:
            return ''

    def get_type_contract(self, request):
        if request.contract_type == ContractType.STATE:
            return 51
        elif request.contract_type == ContractType.MUNICIPAL:
            return 52
        elif request.contract_type == ContractType.COMMERCIAL:
            return 53
        else:
            return ''

    def get_subcontractor_text(self, request):
        return ''

    def get_summary_protocol(self, request):
        return 62

    def get_source_financing(self, request):
        return 56

    def get_text_v_r(self, request):
        if request.tender.beneficiary_address:
            region = cache.get('dadata_region_%s' % request.tender.beneficiary_address)
            if not region:
                api = DaData()
                region = api.get_address_suggest(
                    request.tender.beneficiary_address
                )['suggestions'][0]['data']['region_with_type']

                cache.set(
                    'dadata_region_%s' % request.protocol_territory,
                    region,
                    30 * 24 * 60 * 60
                )
            return region
        return 'РФ'

    def get_indisputable_cancellation(self, request):
        if request.downpay:
            return 49
        return 50

    class Meta:
        model = Request
        fields = (
            'number',
            'sum',
            'sum_proposed',
            'bg_term_1',
            'bg_term_2',
            'date_c',
            'indisputable_cancellation',
            'summary_protocol',
            'number_report',
            'date_p',
            'text_v_r',
            'source_financing',
            'subcontractor_text',
            'type_contract',
            'type_order',
            'text_contract',
            'contract_number',
            'contract_date',
            'contract_number_this',
            'types_software',
            'text_software',
        )


class TenderMosKomBank(serializers.ModelSerializer):
    lot = serializers.SerializerMethodField('get_lot')
    tender_subject = serializers.CharField(source='tender.subject', read_only=True)
    url_tr = serializers.CharField(source='tender.tender_url', read_only=True)
    name = serializers.SerializerMethodField('get_name')
    determining_supplier = serializers.SerializerMethodField('get_determining_supplier')
    date_publication = serializers.DateField(
        source='tender.publish_date', format='%d.%m.%Y'
    )
    nmc = serializers.FloatField(source='tender.price', read_only=True)
    nmc_name = serializers.CharField(source='tender.subject', read_only=True)
    customer = serializers.CharField(source='tender.beneficiary_name', read_only=True)
    address = serializers.CharField(source='tender.beneficiary_address', read_only=True)
    inn = serializers.CharField(source='tender.beneficiary_inn', read_only=True)
    kpp = serializers.CharField(source='tender.beneficiary_kpp', read_only=True)
    orgn = serializers.CharField(source='tender.beneficiary_ogrn', read_only=True)

    def get_name(self, request):
        return request.tender.placement.name if request.tender.placement else ''

    def get_determining_supplier(self, request):
        return request.get_placement_way_display()

    def get_lot(self, request):
        if request.tender.federal_law == FederalLaw.LAW_44:
            return '44-Ф3'
        elif request.tender.federal_law == FederalLaw.LAW_223:
            return '223-ФЗ'
        elif request.tender.federal_law in [FederalLaw.LAW_615, FederalLaw.LAW_185]:
            return '615ПП(185ФЗ)'
        else:
            return ''

    class Meta:
        model = Request
        fields = (
            'lot',
            'tender_subject',
            'url_tr',
            'name',
            'determining_supplier',
            'date_publication',
            'nmc',
            'nmc_name',
            'customer',
            'address',
            'inn',
            'kpp',
            'orgn',
        )


class TenderGuaranteeMosKomBank(serializers.ModelSerializer):
    date_a = serializers.DateField(source='final_date', format='%d.%m.%Y')
    date_t = serializers.DateField(source='final_date', format='%d.%m.%Y')

    class Meta:
        model = Request
        fields = (
            'date_a',
            'date_t'
        )


class QualityGuaranteeMosKomBank(serializers.ModelSerializer):
    date_c = serializers.DateField(
        source='warranty_from', format='%d.%m.%Y', read_only=True
    )
    amount = serializers.SerializerMethodField('get_amount')

    def get_amount(self, request):
        try:
            return (request.warranty_to - request.warranty_from).days
        except Exception:
            return ''

    class Meta:
        model = Request
        fields = (
            'date_c',
            'amount',
        )


class AdvanceGuaranteeMosKomBank(serializers.ModelSerializer):
    date_c = serializers.DateField(
        source='term_of_work_from', format='%d.%m.%Y', read_only=True
    )
    amount = serializers.SerializerMethodField('get_amount')

    def get_amount(self, request):
        try:
            return float(
                request.prepaid_expense_amount * 100 / request.suggested_price_amount
            )
        except Exception:
            return ''

    class Meta:
        model = Request
        fields = (
            'date_c',
            'amount',
        )


class RequestContractMosKomBank(serializers.ModelSerializer):
    presence_advance_text = serializers.FloatField(
        source='prepaid_expense_amount', read_only=True
    )
    commitment_from = serializers.DateField(source='warranty_from', format='%d.%m.%Y')
    commitment_to = serializers.DateField(source='warranty_to', format='%d.%m.%Y')
    sum_commitment = serializers.SerializerMethodField('get_sum_commitment')

    def get_presence_advance_text(self, request):
        if Target.AVANS_RETURN in request.targets:
            return (request.prepaid_expense_amount * 100) / request.suggested_price_amount

    def get_sum_commitment(self, request):
        if Target.WARRANTY in request.targets:
            return request.required_amount

    class Meta:
        model = Request
        fields = (
            'presence_advance_text',
            'commitment_from',
            'commitment_to',
            'sum_commitment',
        )


class ShortUserUlMosKomBank(serializers.ModelSerializer):
    tax_system = serializers.SerializerMethodField('get_tax_system')

    def get_tax_system(self, client):
        tax_system = client.profile.tax_system
        if tax_system == TaxationType.TYPE_OSN:
            return 'osno'
        elif tax_system == TaxationType.TYPE_ENVD:
            return 'envd'
        elif tax_system == TaxationType.TYPE_USN:
            return 'usn'
        elif tax_system == TaxationType.TYPE_ESHN:
            return 'echn'
        elif tax_system == TaxationType.TYPE_PSN:
            return 'pat'
        else:
            return ''

    class Meta:
        model = Client
        fields = (
            'tax_system',
        )


class UserUlMosKomBank(serializers.ModelSerializer):
    name = serializers.CharField(source='full_name', read_only=True)
    name_eng = serializers.SerializerMethodField('get_name_eng')
    okopf = serializers.SerializerMethodField('get_okopf')
    tax_system = serializers.SerializerMethodField('get_tax_system')
    ogrn = serializers.CharField(source='reg_ogrn', read_only=True)
    date_state_reg = serializers.DateField(
        source='reg_state_date', read_only=True, format='%d.%m.%Y'
    )
    reg_authority = serializers.SerializerMethodField('get_reg_authority')
    kpp = serializers.CharField(source='reg_kpp', read_only=True)
    date_certificate = serializers.SerializerMethodField('get_date_certificate')
    okpo = serializers.CharField(source='reg_okpo', read_only=True)
    oktmo = serializers.CharField(source='code_oktmo', read_only=True)
    okato = serializers.CharField(source='reg_okato', read_only=True)
    okved = serializers.SerializerMethodField('get_okved')
    fax = serializers.SerializerMethodField('get_fax')  # TODO уточнить
    site = serializers.SerializerMethodField('get_site')
    email = serializers.CharField(source='contact_email')  # TODO уточнить
    u_tel = serializers.SerializerMethodField('get_u_tel')
    u_mail = serializers.SerializerMethodField('get_email')
    u_fio = serializers.SerializerMethodField('get_fio')
    tel = serializers.SerializerMethodField('get_tel')
    u_tel_d = serializers.SerializerMethodField('get_tel')
    mail = serializers.CharField(source='contact_email')
    fio = serializers.CharField(source='general_director.get_name')
    u_cp_position = serializers.SerializerMethodField('get_u_cp_position')
    employees = serializers.CharField(source='number_of_employees', read_only=True)
    employees1 = serializers.CharField(source='number_of_employees', read_only=True)
    numbem_ssch = serializers.CharField(source='number_of_employees', read_only=True)
    average_salary_fund = serializers.CharField(source='salary_fund', read_only=True)
    dgoodw_exp = serializers.SerializerMethodField('get_dgoodw_exp')  # TODO уточнить
    id_dgoodw_fin_con = serializers.SerializerMethodField('get_id_dgoodw_fin_con')  # noqa TODO уточнить
    is_file_of_unpaid_document = serializers.SerializerMethodField('get_is_file_of_unpaid_document')  # noqa TODO уточнить
    sum_of_document = serializers.SerializerMethodField('get_sum_of_document')  # noqa TODO уточнить
    is_overdue_loans = serializers.SerializerMethodField('get_is_overdue_loans')  # noqa TODO уточнить
    is_overdue_payables = serializers.SerializerMethodField('get_is_overdue_payables')  # noqa TODO уточнить
    sum_accounts_payable = serializers.SerializerMethodField('get_sum_accounts_payable')  # noqa TODO уточнить
    sum_receivables = serializers.SerializerMethodField('get_sum_receivables')  # noqa TODO уточнить
    is_arrears_to_employees = serializers.SerializerMethodField('get_is_arrears_to_employees')  # noqa TODO уточнить
    is_queue_of_orders_for_bank = serializers.SerializerMethodField('get_is_queue_of_orders_for_bank')  # noqa TODO уточнить
    is_beneficiary_of_transaction = serializers.SerializerMethodField(
        'get_is_beneficiary_of_transaction')  # TODO уточнить
    id_otin_deponafp = serializers.SerializerMethodField('get_id_otin_deponafp')  # noqa TODO уточнить
    id_relationship_bank = serializers.SerializerMethodField('get_id_relationship_bank')  # noqa TODO уточнить
    id_otin_gsb_source = serializers.SerializerMethodField('get_id_otin_gsb_source')  # noqa TODO уточнить
    id_conf_cladv = serializers.SerializerMethodField('get_id_conf_cladv')  # noqa TODO уточнить
    code_of_subject = serializers.SerializerMethodField('get_code_of_subject')  # noqa TODO уточнить

    def get_u_tel(self, profile):
        tel = profile.client.agent_company.manager.first().manager.phone
        return change_phone(tel)

    def get_tel(self, profile):
        return change_phone(profile.contact_phone)

    def get_email(self, profile):
        return profile.client.agent_company.manager.first().manager.email

    def get_fio(self, profile):
        return profile.client.agent_company.manager.first().manager.full_name

    def get_fax(self, profile):
        return ''

    def get_is_beneficiary_of_transaction(self, profile):
        return ''

    def get_code_of_subject(self, profile):
        return ''

    def get_id_conf_cladv(self, profile):
        return 0

    def get_id_otin_gsb_source(self, profile):
        return 37

    def get_id_relationship_bank(self, profile):
        return 35

    def get_id_otin_deponafp(self, profile):
        return 0

    def get_is_queue_of_orders_for_bank(self, profile):
        return ''

    def get_is_arrears_to_employees(self, profile):
        return ''

    def get_sum_receivables(self, profile):
        return ''

    def get_sum_accounts_payable(self, profile):
        return ''

    def get_is_overdue_payables(self, profile):
        return ''

    def get_is_overdue_loans(self, profile):
        return ''

    def get_sum_of_document(self, profile):
        return ''

    def get_is_file_of_unpaid_document(self, profile):
        result = profile.profileaccounts.filter(has_unpaid_account=True).first()
        if result:
            return 0
        return 1

    def get_id_dgoodw_fin_con(self, profile):
        return 30

    def get_dgoodw_exp(self, profile):
        return int((timezone.now().date() - profile.reg_state_date).days / 365)

    def get_u_cp_position(self, profile):
        return 'Менеджер Tenderhelp'

    def get_u_tel_d(self, profile):
        return ''

    def get_site(self, profile):
        return 'Нет сайта'

    def get_okved(self, profile):
        try:
            data = EgrulData.get_info(profile.reg_inn)
            return data['section-vid-actions'][0].split(' ')[0]
        except Exception:
            return ''

    def get_date_certificate(self, profile):
        if profile.reg_state_date:
            return profile.reg_state_date.strftime('%d.%m.%Y')
        else:
            return ''

    def get_reg_authority(self, profile):
        try:
            data = EgrulData.get_info(profile.reg_inn)
            return data['section-other']['registrator_name']
        except Exception:
            return ''

    def get_tax_system(self, profile):
        dict_choices = {
            TaxationType.TYPE_OSN: 'osno',
            TaxationType.TYPE_USN: 'usn',
            TaxationType.TYPE_ENVD: 'envd',
            TaxationType.TYPE_ESHN: 'eshn',
            TaxationType.TYPE_PSN: 'pat',
        }
        return dict_choices.get(profile.tax_system, '')

    def get_okopf(self, profile):
        if profile.client.is_individual_entrepreneur:
            return '7'
        dict_choices = {
            OrganizationForm.TYPE_OOO: '1',
            OrganizationForm.TYPE_ZAO: '14',
            OrganizationForm.TYPE_PAO: '2',
            OrganizationForm.TYPE_AO: '5',
            OrganizationForm.TYPE_OAO: '12',
            OrganizationForm.TYPE_GUP: '10',
            OrganizationForm.TYPE_MUP: '11'
        }
        return dict_choices.get(profile.organization_form, '')

    def get_name_eng(self, profile):
        return ''

    class Meta:
        model = Profile
        fields = (
            'name',
            'name_eng',
            'okopf',
            'tax_system',
            'ogrn',
            'date_state_reg',
            'reg_authority',
            'kpp',
            'date_certificate',
            'okpo',
            'oktmo',
            'okato',
            'okved',
            'fax',
            'site',
            'email',
            'tel',
            'mail',
            'fio',
            'u_tel',
            'u_tel_d',
            'u_mail',
            'u_fio',
            'u_cp_position',
            'employees',
            'employees1',
            'numbem_ssch',
            'average_salary_fund',
            'dgoodw_exp',
            'id_dgoodw_fin_con',
            'is_file_of_unpaid_document',
            'sum_of_document',
            'is_overdue_loans',
            'is_overdue_payables',
            'sum_accounts_payable',
            'sum_receivables',
            'is_arrears_to_employees',
            'is_queue_of_orders_for_bank',
            'is_beneficiary_of_transaction',
            'id_otin_deponafp',
            'id_relationship_bank',
            'id_otin_gsb_source',
            'id_conf_cladv',
            'code_of_subject',
        )


class LicenseMosKomBank(serializers.ModelSerializer):
    license = serializers.CharField(source='number_license', read_only=True)
    date = serializers.DateField(
        source='date_issue_license', format='%d.%m.%Y', read_only=True
    )
    id_view = serializers.CharField(source='list_of_activities', read_only=True)
    hint = serializers.CharField(source='issued_by_license', read_only=True)
    date_s = serializers.SerializerMethodField('get_date_s')

    def get_date_s(self, license):
        if license.date_end_license is None or license.is_indefinitely:
            return 'Бессрочная'
        return license.date_end_license.strftime('%d.%m.%Y')

    class Meta:
        model = LicensesSRO
        fields = (
            'license',
            'date',
            'id_view',
            'hint',
            'date_s',
        )


class BankAccountMosKomBank(serializers.ModelSerializer):
    current = serializers.CharField(source='bank_account_number', read_only=True)
    bic = serializers.CharField(source='bank_bik', read_only=True)
    name = serializers.CharField(source='bank', read_only=True)
    correspondent = serializers.CharField(source='correspondent_account', read_only=True)

    class Meta:
        model = BankAccount
        fields = (
            'current',
            'bic',
            'name',
            'correspondent',
        )


class AddressMosKomBank(serializers.ModelSerializer):
    user_hash = serializers.SerializerMethodField('get_user_hash')
    legal_fias_id = serializers.SerializerMethodField('get_legal_fias_id')
    state_fias_id = serializers.SerializerMethodField('get_state_fias_id')
    state_registratio_с = serializers.SerializerMethodField('get_state_registratio_с')

    def get_state_registratio_с(self, external_request):
        return 1 if external_request.request.client.profile.fact_is_legal_address else ''

    def get_user_hash(self, external_request):
        return external_request.get_other_data_for_key('user_hash')

    def get_state_fias_id(self, external_request):
        if external_request.request.client.profile.fact_is_legal_address:
            return self.get_legal_fias_id(external_request)
        address = external_request.request.client.profile.fact_address
        address_fias = cache.get('dadata_fias_%s' % address)
        if not address_fias:
            api = DaData()
            data = api.get_address_suggest(address)['suggestions'][0]['data']
            address_fias = data.get('fias_id', '')
            cache.set('dadata_fias_%s' % address, address_fias, 30 * 24 * 60 * 60)
        return address_fias

    def get_legal_fias_id(self, external_request):
        address = external_request.request.client.profile.legal_address
        address_fias = cache.get('dadata_fias_%s' % address)
        if not address_fias:
            api = DaData()
            data = api.get_address_suggest(address)['suggestions'][0]['data']
            address_fias = data.get('fias_id', '')
            cache.set('dadata_fias_%s' % address, address_fias, 30 * 24 * 60 * 60)
        return address_fias

    class Meta:
        model = ExternalRequest
        fields = (
            'user_hash',
            'legal_fias_id',
            'state_fias_id',
            'state_registratio_с',
        )


class PersonMosKomBank(serializers.ModelSerializer):
    fio = serializers.SerializerMethodField('get_fio')
    inn = serializers.CharField(source='fiz_inn', read_only=True)
    document_type = serializers.SerializerMethodField('get_document_type')
    issued_by = serializers.CharField(source='passport.issued_by', read_only=True)
    numb_p = serializers.SerializerMethodField('get_numb_p')
    date_p = serializers.DateField(
        source='passport.when_issued', format='%d.%m.%Y', read_only=True
    )
    division_code = serializers.CharField(source='passport.issued_code', read_only=True)
    date_birth = serializers.DateField(
        source='passport.date_of_birth', format='%d.%m.%Y', read_only=True
    )
    citizenship = serializers.CharField(read_only=True)
    place_of_birth = serializers.CharField(
        source='passport.place_of_birth', read_only=True
    )
    registration_fias_id = serializers.SerializerMethodField(
        'get_registration_address_fias_link'
    )
    living_fias_id = serializers.SerializerMethodField('get_living_address_fias_link')
    is_pdl = serializers.SerializerMethodField('get_is_pdl')  # TODO уточнить
    which_pdl = serializers.SerializerMethodField('get_which_pdl')  # TODO уточнить
    founder_affiliation = serializers.SerializerMethodField('get_founder_affiliation')
    country = serializers.SerializerMethodField('get_country')  # TODO уточнить
    is_pdl_arr = serializers.SerializerMethodField('get_is_pdl_arr')  # TODO уточнить
    living_registratio_c = serializers.SerializerMethodField('get_living_registratio_c')

    def get_living_registratio_c(self, person):
        return 1

    def get_is_pdl_arr(self, person):
        return ''

    def get_country(self, person):
        return ''

    def get_founder_affiliation(self, person):
        if person.another_country_citizen:
            return 49
        return 50

    def get_which_pdl(self, person):
        return ''

    def get_is_pdl(self, person):
        return ''

    def get_living_address_fias_link(self, person):
        return self.get_registration_address_fias_link(person)

    def get_registration_address_fias_link(self, person):
        address = cache.get('dadata_fias_%s' % person.passport.place_of_registration)
        if not address:
            api = DaData()
            data = api.get_address_suggest(
                person.passport.place_of_registration
            )['suggestions'][0]['data']
            address = data.get('fias_id', '')
            cache.set(
                'dadata_fias_%s' % person.passport.place_of_registration,
                address,
                30 * 24 * 60 * 60
            )
        return address

    def get_numb_p(self, person):
        if not person.passport:
            return ''
        series = person.passport.series
        number = person.passport.number
        return '%s-%s № %s' % (series[:2], series[2:], number)

    def get_document_type(self, person):
        if person.has_russian_passport:
            return 63
        if 'Временное удостоверение личности' in person.another_passport:
            return 64
        if 'Паспорт иностранного гражданина' in person.another_passport:
            return 65
        return 66

    def get_fio(self, person):
        return ' '.join([
            person.last_name,
            person.first_name,
            person.middle_name,
        ])

    class Meta:
        model = ProfilePartnerIndividual
        fields = (
            'fio',
            'inn',
            'document_type',
            'issued_by',
            'numb_p',
            'date_p',
            'division_code',
            'date_birth',
            'citizenship',
            'place_of_birth',
            'registration_fias_id',
            'living_fias_id',
            'is_pdl',
            'which_pdl',
            'founder_affiliation',
            'country',
            'is_pdl_arr',
            'living_registratio_c',
        )


class ChiefMosKomBank(serializers.ModelSerializer):
    person_id = serializers.SerializerMethodField('get_person_id')  # TODO уточнить
    user_hash = serializers.SerializerMethodField('get_user_hash')  # TODO уточнить
    term_of_office = serializers.SerializerMethodField('get_term_of_office')  # noqa TODO уточнить
    base_action = serializers.SerializerMethodField('get_base_action')  # TODO уточнить
    dover = serializers.SerializerMethodField('get_dover')  # TODO уточнить
    dover_name = serializers.SerializerMethodField('get_dover_name')  # TODO уточнить
    dover_date = serializers.SerializerMethodField('get_dover_date')  # TODO уточнить
    dover_sr = serializers.SerializerMethodField('get_dover_sr')  # TODO уточнить

    def get_term_of_office(self, external_request):
        profile = external_request.request.client.profile
        date_from = profile.general_director.document_gen_dir.date_protocol_EIO
        if date_from is None:
            date_from = profile.reg_state_date
        days = (timezone.now().date() - date_from).days
        year = str(int(days / 365))
        month = str(int((days % 365) / 31))
        text = ''
        if year != '0':
            if year[-1] == '1' and len(year) > 1 and year[-2:] != '11':
                text += '%s год' % year
            elif year[-1] in [2, 3, 4] and len(year) > 1 and \
                    year[-2:] not in [12, 13, 14]:
                text += '%s года' % year
            else:
                text += '%s лет' % year
        if month != '0':
            if text != '':
                text += ' '
            if month[-1] == '1':
                text += '%s месяц' % month
            elif month[-1] in [2, 3, 4]:
                text += '%s месяца' % month
            else:
                text += '%s месяцев' % month
        if text == '':
            text = 'Меньше месяца'
        return text

    def get_dover_sr(self, external_request):
        return ''

    def get_dover_date(self, external_request):
        return ''

    def get_dover_name(self, external_request):
        return ''

    def get_dover(self, external_request):
        return ''

    def get_base_action(self, external_request):
        dict_choices = {
            'Устав': 27,
            'Доверенност': 28,
            'Инное': 29,
        }
        return dict_choices['Устав']

    def get_user_hash(self, external_request):
        return external_request.get_other_data_for_key('user_hash')

    def get_person_id(self, external_request):
        key = external_request.get_other_data_for_key('general_director_id')
        return external_request.get_other_data_for_key('dict_persons')[str(key)]

    class Meta:
        model = ExternalRequest
        fields = (
            'user_hash',
            'person_id',
            'term_of_office',
            'base_action',
            'dover',
            'dover_name',
            'dover_date',
            'dover_sr',
        )


class AccountantMosKomBank(serializers.ModelSerializer):
    person_id = serializers.SerializerMethodField('get_person_id')
    user_hash = serializers.SerializerMethodField('get_user_hash')
    term_of_office = serializers.SerializerMethodField('get_term_of_office')
    base_action = serializers.SerializerMethodField('get_base_action')
    dover = serializers.SerializerMethodField('get_dover')
    dover_name = serializers.SerializerMethodField('get_dover_name')
    dover_date = serializers.SerializerMethodField('get_dover_date')
    dover_sr = serializers.SerializerMethodField('get_dover_sr')

    def get_dover_sr(self, external_request):
        return ''

    def get_dover_date(self, external_request):
        return ''

    def get_dover_name(self, external_request):
        return ''

    def get_dover(self, external_request):
        return ''

    def get_base_action(self, external_request):
        return ''

    def get_term_of_office(self, external_request):
        return ''

    def get_person_id(self, external_request):
        return external_request.get_other_data_for_key('booker_id')

    def get_user_hash(self, external_request):
        return external_request.get_other_data_for_key('user_hash')

    class Meta:
        model = ExternalRequest
        fields = (
            'person_id',
            'user_hash',
            'term_of_office',
            'base_action',
            'dover',
            'dover_name',
            'dover_date',
            'dover_sr',
        )


class LoggingMosKomBank(serializers.ModelSerializer):
    type = serializers.SerializerMethodField('get_type')
    inn = serializers.CharField(source='profile.reg_inn', read_only=True)
    name = serializers.CharField(source='profile.short_name', read_only=True)
    fio = serializers.CharField(source='profile.contact_name', read_only=True)
    mail = serializers.SerializerMethodField('get_mail')
    tel = serializers.SerializerMethodField('get_tel')

    def get_mail(self, client):
        return client.agent_company.manager.first().manager.email

    def get_type(self, client):
        if client.is_organization:
            return 1
        else:
            return 2

    def get_tel(self, client):
        tel = client.profile.contact_phone
        return change_phone(tel)

    class Meta:
        model = Client
        fields = (
            'type',
            'inn',
            'name',
            'fio',
            'mail',
            'tel',
        )


class UpdateLoggingMosKomBank(LoggingMosKomBank):
    tel = serializers.SerializerMethodField('get_tel')
    mail = serializers.SerializerMethodField('get_mail')

    def get_mail(self, profile):
        return profile.client.agent_company.manager.first().manager.email

    def get_tel(self, profile):
        tel = profile.client.profile.contact_phone
        return change_phone(tel)

    class Meta:
        model = Client
        fields = (
            'name',
            'fio',
            'mail',
            'tel',
        )


class EntityFounder(serializers.ModelSerializer):
    name_le = serializers.CharField(source='name', read_only=True)
    name_de = serializers.SerializerMethodField('get_name_de')
    inn = serializers.CharField(read_only=True)
    organ_field = serializers.CharField(source='ogrn', read_only=True)
    percentage = serializers.FloatField(source='share', read_only=True)
    organ = serializers.SerializerMethodField('get_organ')
    location = serializers.SerializerMethodField('get_location')

    def get_location(self, person):
        try:
            data = EgrulData.get_info(person.inn)['section-boss-data']
            return '%s %s' % (data['positionboss'], data['fio'])
        except Exception:
            return ''

    def get_name_de(self, person):
        try:
            data = EgrulData.get_info(person.inn)
            return data['section-vid-actions'][0].split(' ')[0]
        except Exception:
            return ''

    def get_organ(self, person):
        try:
            data = EgrulData.get_info(person.inn)
            text = ''
            for fiz in data['section-akcionery_fiz']['akcionery_fiz']:
                if fiz['percents']:
                    text += '%s,%s;' % (fiz['fio'], fiz['percents'])
            for ur in data['section-akcionery_yur']['akcionery_yur']:
                if ur['percents']:
                    text += '%s,%s;' % (ur['name_yur'], ur['percents'])
            return text
        except Exception:
            return ''

    class Meta:
        model = ProfilePartnerIndividual
        fields = (
            'name_le',
            'name_de',
            'inn',
            'organ_field',
            'percentage',
            'organ',
            'location',
        )
