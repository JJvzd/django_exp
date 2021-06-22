import copy
import os

from django.core.files import File
from django.utils.functional import cached_property

from accounting_report.serializers import QuarterSerializer
from bank_guarantee.models import ContractPlacementWay, ContractType
from bank_guarantee.serializers import RequestSerializer
from base_request.models import AbstractRequest
from cabinet.constants.constants import Target, TaxationType, OrganizationForm
from cabinet.serializers import BankAccountSerializer, ProfilePartnerIndividualSerializer, LicensesSROSerializer, \
    ProfileSerializer, GeneralDirectorSerializer, PassportDetailsSerializer, DocumentGenDirSerializer, \
    ProfilePartnerLegalEntitiesSerializer, ProfileViewActivitySerializer
from questionnaire.models import BankAccount, ProfilePartnerIndividual, LicensesSRO, PassportDetails, \
    ProfilePartnerLegalEntities, KindOfActivity
from settings.settings import BASE_DIR


class DataForTest:

    def __init__(self, request=None, user=None, bank=None):
        self.request = request
        self.user = user
        self.bank = bank

    @cached_property
    def _data(self):
        return None

    def get_data(self):
        return copy.deepcopy(self._data)


class EditDataForTest(DataForTest):

    def get_change_data_request(self):
        return {
            "suggested_price_amount": 1100000,  # Предложенная цена контракта
            "suggested_price_percent": "97.27",  # В процентном соотношении
            "final_date": "2020-01-01",  # Крайний срок выдачи
            "contract_type": "state",  # Контракт государственный или муниципальный
            "interval_from": "2020-01-01",  # Дата выдачи
            "interval_to": "2020-01-31",  # Дата окончания
            "interval": 30,  # Дней
            "targets": [Target.PARTICIPANT, Target.AVANS_RETURN],  # Тип БГ
            "delivery_method": 1,  # Способ доставки
            "delivery_address": 'Test',  # Адрес получателя
            "delivery_fio": 'Test Test',  # ФИО получетля
            "delivery_phone": '89999999999',  # Телефон получателя
            "prepayment": True,  # Наличие беспорного списания
            "downpay": True,  # Наличие аванса
            'prepaid_expense_amount': 25000,  # Размер аванса
            'experience_general_contractor': True,  # Есть ли исполенные контракты
            'is_big_deal': True,  # Является ли сделка крупной
            'placement_way': ContractPlacementWay.COMPETITION,
            # 'profile': self.profile(),
            # 'quarters': self.quarters(),
        }

    def change_data_request(self):
        data = RequestSerializer(self.request).data
        for field in ['agent', 'agent_user_id', 'status', 'client']:
            del data[field]
        change_data_request = self.get_change_data_request()
        for key, value in change_data_request.items():
            data.update({key: value})
        return data

    def get_change_data_profile(self):
        return {
            "organization_form": OrganizationForm.TYPE_ZAO,
            "tax_system": TaxationType.TYPE_USN,
            "contact_name": "вфывфы фывфыв фывфывфвы",
            "contact_phone": "+7 (899) 999-9999",
            "contact_email": "sfsfd@sfsdf.ru",
            "authorized_capital_paid": 500000.00,
            "authorized_capital_announced": 500000.00,
            "number_of_employees": "50",
            "salary_fund": "50",
            'general_director': self.general_director(),
            'bank_accounts': self.bank_accounts(),
            'licenses_sro': self.licenses_sro(),
            'persons': self.persons(),
            'legal_shareholders': self.legal_shareholders(),
            'activities': self.activities(),
            'quarters': self.quarters()
        }

    def profile(self):
        data = ProfileSerializer(self.request.client.profile).data
        change_data_profile = self.get_change_data_profile()
        for key, value in change_data_profile.items():
            data.update({key: value})
        return data

    def get_change_data_general_director(self):
        return {
            "middle_name": "Тестов",
            "has_russian_passport": True,
            "passport": self.passport_general_director(),
            "fiz_inn": "502407703808",
            "snils": "15456588452",
            "document_gen_dir": self.document_gen_dir(),
            "experience_this_industry": "10",
        }

    def general_director(self):
        data = GeneralDirectorSerializer(self.request.client.profile.general_director).data
        general_director = self.get_change_data_general_director()
        for key, value in general_director.items():
            data.update({key: value})

        return data

    def get_change_data_passport_general_director(self):
        return {
            "series": "7777", "number": "777777", "issued_by": "Мной",
            "when_issued": "2019-11-01",
            "date_of_birth": "1995-08-24",
            "place_of_birth": "Дубна",
            "place_of_registration": "Дубна",
            "issued_code": "777-777",
        }

    def passport_general_director(self):
        passport_data = self.get_change_data_passport_general_director()
        data = PassportDetailsSerializer(self.request.client.profile.general_director.passport).data
        for key, value in passport_data.items():
            data.update({key: value})
        return data

    def get_change_data_document_gen_dir(self):
        return {
            "name_and_number": " Тест 445-ло",
            "date_protocol_EIO": "2019-12-06",
            "number_protocol_EIO": "444544фывф45",
            "expiration_date": None, "is_indefinitely": True,
        }

    def document_gen_dir(self):
        data = DocumentGenDirSerializer(
            self.request.client.profile.general_director.document_gen_dir).data
        change_data = self.get_change_data_document_gen_dir()
        for key, value in change_data.items():
            data.update({key: value})
        return data

    def get_change_data_bank_account(self):
        return {
            "profile": self.request.client.profile,
            "bank": "ЗАПАДНО-СИБИРСКОЕ ОТДЕЛЕНИЕ№8647 ПАО СБЕРБАНК",
            "bank_bik": "047102651",
            "correspondent_account": "30101810800000000651", "bank_account_number": "64634634343434",
            "has_unpaid_account": False,
        }

    def bank_accounts(self):
        data = BankAccountSerializer(self.request.client.profile.profileaccounts, many=True).data
        bank_account = self.get_change_data_bank_account()
        search_bank_account = self.find_dict('bank_account_number', bank_account['bank_account_number'], data)
        if search_bank_account != {}:
            search_bank_account.update(bank_account)
        else:
            data.append(BankAccountSerializer(BankAccount(**bank_account)).data)
        return data

    def get_change_data_license_sro(self):
        return {
            "profile": self.request.client.profile,
            "date_issue_license": "2019-12-20",
            "view_activity": "test",
            "is_indefinitely": True,
            "number_license": "343434",
            "list_of_activities": "test, test, test",
            "issued_by_license": "test"
        }

    def licenses_sro(self):
        data = LicensesSROSerializer(self.request.client.profile.licenses, many=True).data
        license_sro = self.get_change_data_license_sro()
        search_license = self.find_dict('number_license', license_sro['number_license'], data)
        if search_license != {}:
            search_license.update(license_sro)
        else:
            data.append(LicensesSROSerializer(LicensesSRO(**license_sro)).data)
        return data

    def get_change_data_passport_person(self):
        return {
            "date_of_birth": "1986-05-08", "place_of_birth": "Дубна",
            "place_of_registration": "Дубна",
            "when_issued": "2019-11-06",
            "issued_by": "Мной",
            "number": "666666",
            "series": "6666",
            "issued_code": "666-666"
        }

    def get_change_data_person(self):
        return {
            "profile": self.request.client.profile,
            "share": 30.00,
            "is_beneficiary": True,
            "citizenship": "Россия",
            "last_name": "ываываыва",
            "first_name": "ываываыва",
            "middle_name": "ываывааыв", "fiz_inn": "65555555555", "snils": "5555555555",
            "has_russian_passport": True
        }

    def persons(self):
        data = ProfilePartnerIndividualSerializer(
            self.request.client.profile.profilepartnerindividual_set.filter(
                is_general_director=False).order_by('id'), many=True).data
        passport_data = self.get_change_data_passport_person()
        person = self.get_change_data_person()
        search_person = self.find_dict('fiz_inn', person['fiz_inn'], data)
        if search_person != {}:
            search_person.update(person)
            search_person['passport'].update(passport_data)
        else:
            person_data = ProfilePartnerIndividualSerializer(
                ProfilePartnerIndividual(**person)
            ).data
            person_data.update({
                'passport': PassportDetailsSerializer(PassportDetails(**passport_data)).data
            })
            data.append(person_data)
        return data

    def get_change_data_legal_shareholder(self):
        return {
            "profile": self.request.client.profile,
            "share": 28.00,
            "inn": "5555555555",
            "name": "ываыавыва",
            "ogrn": "5445454544",
            "kpp": "545343434",
            "place": "Дубна",
            "citizenship": "Россия",
            "last_name": "ываываыва",
            "first_name": "ываываыва",
            "middle_name": "ываываыв",
        }

    def get_change_data_passport_legal_shareholder(self):
        return {
            "date_of_birth": "1996-05-09", "place_of_birth": "Дубна",
            "place_of_registration": "Дубна",
            "when_issued": "2020-01-01", "issued_by": "мной",
            "number": "777777",
            "series": "7777",
            "issued_code": "777-777"
        }

    def legal_shareholders(self):
        data = ProfilePartnerLegalEntitiesSerializer(self.request.client.profile.persons_entities, many=True).data
        passport_data = self.get_change_data_passport_legal_shareholder()
        legal_shareholder = self.get_change_data_legal_shareholder()
        search_legal_shareholder = self.find_dict('inn', legal_shareholder['inn'], data)
        if search_legal_shareholder != {}:
            search_legal_shareholder.update(legal_shareholder)
            search_legal_shareholder['passport'].update(passport_data)
        else:
            legal_shareholder_data = ProfilePartnerLegalEntitiesSerializer(
                ProfilePartnerLegalEntities(**legal_shareholder)
            ).data
            legal_shareholder_data.update({
                'passport': PassportDetailsSerializer(PassportDetails(**passport_data)).data
            })
            data.append(legal_shareholder_data)
        return data

    def get_change_data_activities(self):
        return {'profile': self.request.client.profile, 'value': "42.34 Тест"}

    def activities(self):
        data = ProfileViewActivitySerializer(self.request.client.profile.kindofactivitys, many=True).data
        activity_data = self.get_change_data_activities()
        search_activity = self.find_dict('value', activity_data['value'], data)
        if search_activity != {}:
            search_activity.update(activity_data)
        else:
            data.append(
                ProfileViewActivitySerializer(
                    KindOfActivity(**activity_data)
                ).data
            )
        return data

    def quarters(self):
        quarters = self.request.client.accounting_report.get_quarters_for_fill()
        change_data_quarters = QuarterSerializer(quarters, many=True).data
        for el in change_data_quarters:
            el['no_data'] = True
        return change_data_quarters

    def documents_link(self):
        return {}

    @cached_property
    def _data(self):
        """Генерация запроса сервера на изменения заявки"""
        return {
            'request': self.change_data_request(),
            'documents_link': self.documents_link()
        }

    def update_request(self):
        self.request = self.request.__class__.objects.get(id=self.request.id)

    @staticmethod
    def find_dict(field, value, data):
        try:
            return filter(lambda x: x[field] == value, data).__next__()
        except StopIteration:
            return {}

    def update_id(self, data):
        for person in self.request.client.profile.persons.exclude(id=self.request.client.profile.general_director.id):
            person_data = self.find_dict('fiz_inn', person.fiz_inn, data['persons'])
            person_data.update({'id': person.id})
            if person_data.get('passport') and isinstance(person_data['passport'], dict):
                person_data['passport'].update({'id': person.passport.id})
        # обновления id добавленных юр лиц
        for legal_shareholder in self.request.client.profile.persons_entities:
            legal_shareholder_data = self.find_dict('inn', legal_shareholder.inn, data['legal_shareholders'])
            legal_shareholder_data.update({'id': legal_shareholder.id})
            if legal_shareholder_data.get('passport') and isinstance(legal_shareholder_data['passport'], dict):
                legal_shareholder_data['passport'].update({'id': legal_shareholder.passport.id})
        # обновление id  добавленных банковских счетов
        for bank_account in self.request.client.profile.profileaccounts:
            bank_account_data = self.find_dict(
                'bank_account_number',
                bank_account.bank_account_number,
                data['bank_accounts']
            )
            bank_account_data.update({'id': bank_account.id})
        # обновления id добавленных лицензий
        for license_sro in self.request.client.profile.licenses:
            license_sro_data = self.find_dict(
                'number_license',
                license_sro.number_license,
                data['licenses_sro']
            )
            license_sro_data.update({'id': license_sro.id})
        # обновления id добавленных видов деятельности
        for activity in self.request.client.profile.kindofactivitys:
            activity_data = self.find_dict('value', activity.value, data['activities'])
            activity_data.update({
                'id': activity.id
            })
        return data

    @property
    def check_profile(self):
        """Генерация правильного ProfileSerializer(self.profile).data"""
        self.update_request()
        data = self.get_data()['request']['profile']
        del data['quarters']
        self.update_id(data)
        return data

    @property
    def check_quarters(self):
        return self.get_data()['request']['quarters']


class DeleteEditData(EditDataForTest):

    def licenses_sro(self):
        return []

    def activities(self):
        return ProfileViewActivitySerializer(self.request.client.profile.kindofactivitys, many=True).data[:1]

    def bank_accounts(self):
        return []

    def persons(self):
        return []

    def legal_shareholders(self):
        return []

    @property
    def check_profile(self):
        data = self.get_data()['request']['profile']
        del data['quarters']
        return data


class ChangeEditData(EditDataForTest):

    def activities(self):
        """Доработать тест"""
        return ProfileViewActivitySerializer(self.request.client.profile.kindofactivitys, many=True).data

    @cached_property
    def _data(self):
        data = super(ChangeEditData, self)._data
        data['request']['profile'] = self.update_id(data['request']['profile'])
        return data

    @property
    def check_profile(self):
        data = self.get_data()['request']['profile']
        del data['quarters']
        return data

    def get_change_data_request(self):
        return {
            "suggested_price_amount": 565436.41,  # Предложенная цена контракта
            "suggested_price_percent": "50",  # В процентном соотношении
            "final_date": "2020-02-01",  # Крайний срок выдачи
            "contract_type": ContractType.COMMERCIAL,  # Контракт государственный или муниципальный
            "interval_from": "2020-02-01",  # Дата выдачи
            "interval_to": "2020-03-31",  # Дата окончания
            "interval": 59,  # Дней
            "targets": [Target.WARRANTY, Target.AVANS_RETURN],  # Тип БГ
            "delivery_method": AbstractRequest.DELIVERY_COURIER,  # Способ доставки
            "delivery_address": 'Tests',  # Адрес получателя
            "delivery_fio": 'Tests Tests',  # ФИО получетля
            "delivery_phone": '89999977999',  # Телефон получателя
            "prepayment": False,  # Наличие беспорного списания
            "downpay": False,  # Наличие аванса
            'prepaid_expense_amount': 0,  # Размер аванса
            'experience_general_contractor': False,  # Есть ли исполенные контракты
            'is_big_deal': False,  # Является ли сделка крупной
            'placement_way': ContractPlacementWay.ELECTRONIC_AUCTION,
            'profile': self.profile(),
            'quarters': self.quarters(),
        }

    def get_change_data_profile(self):
        return {
            "organization_form": OrganizationForm.TYPE_AO,
            "tax_system": TaxationType.TYPE_ENVD,
            "contact_name": "вфывфыфыв фывфывфыв фывфывфвывыф",
            "contact_phone": "+7 (889) 999-9999",
            "contact_email": "sfsf2d@sfsdf.ru",
            "authorized_capital_paid": "800000.00",
            "authorized_capital_announced": "800000.00",
            "number_of_employees": "70",
            "salary_fund": "70",
            'general_director': self.general_director(),
            'bank_accounts': self.bank_accounts(),
            'licenses_sro': self.licenses_sro(),
            'persons': self.persons(),
            'legal_shareholders': self.legal_shareholders(),
            'activities': self.activities(),
            'quarters': self.quarters()
        }

    def get_change_data_general_director(self):
        return {
            "middle_name": "Тестоввв",
            "has_russian_passport": True,
            "passport": self.passport_general_director(),
            "fiz_inn": "502407703808",
            "snils": "15456228452",
            "document_gen_dir": self.document_gen_dir(),
            "experience_this_industry": "13",
        }

    def get_change_data_passport_general_director(self):
        return {
            "series": "5555", "number": "555555", "issued_by": "НеМной",
            "when_issued": "2019-12-01",
            "date_of_birth": "1991-08-24",
            "place_of_birth": "Тюмень",
            "place_of_registration": "Тюмень",
            "issued_code": "555-555",
        }

    def get_change_data_document_gen_dir(self):
        return {
            "name_and_number": " Тесты 436-ло",
            "date_protocol_EIO": "2016-12-06",
            "number_protocol_EIO": "вапвапвап45ыв",
            "expiration_date": "2020-05-06", "is_indefinitely": False,
        }

    def get_change_data_license_sro(self):
        return {
            "date_issue_license": "2019-10-20",
            "view_activity": "test2",
            "is_indefinitely": True,
            "number_license": "34344334",
            "list_of_activities": "test2, test2, test2",
            "issued_by_license": "test2"
        }

    def get_change_data_passport_person(self):
        return {
            "date_of_birth": "1986-04-08", "place_of_birth": "Тюмень",
            "place_of_registration": "Тюмень",
            "when_issued": "2019-10-06",
            "issued_by": "НеМной",
            "number": "444444",
            "series": "4444",
            "issued_code": "444-444"
        }

    def get_change_data_person(self):
        return {
            "share": 35.00,
            "is_beneficiary": True,
            "citizenship": "Россия",
            "last_name": "ыаыукыу",
            "first_name": "ывапваываыва",
            "middle_name": "ываываапавыв", "fiz_inn": "65555555555", "snils": "4444444444",
            "has_russian_passport": True
        }

    def get_change_data_legal_shareholder(self):
        return {
            "share": 39.00,
            "inn": "5555555555",
            "name": "фывфывукцк",
            "ogrn": "7777777777",
            "kpp": "7777777",
            "place": "Тюмень",
            "citizenship": "Россия",
            "last_name": "фывфвыфывфцу",
            "first_name": "вфывфывцу",
            "middle_name": "фывфвыйцу",
        }

    def get_change_data_passport_legal_shareholder(self):
        return {
            "date_of_birth": "1993-05-09", "place_of_birth": "Тюмень",
            "place_of_registration": "Тюмень",
            "when_issued": "2019-01-01", "issued_by": "немной",
            "number": "888888",
            "series": "8888",
            "issued_code": "888-888"
        }

    def get_change_data_bank_account(self):
        return {
            "bank": "ЗАПАДНО-СИБИРСКОЕ ОТДЕЛЕНИЕ№8647 ПАО СБЕРБАНК",
            "bank_bik": "047102651",
            "correspondent_account": "30101810800000000651", "bank_account_number": "64634634343434",
            "has_unpaid_account": True,
        }


class SendToBankDataForTest(DataForTest):

    @cached_property
    def _data(self):
        return {
            'banks': [self.bank.id, ]
        }


class InProcessDataForTest(DataForTest):

    @cached_property
    def _data(self):
        return {
            'request_number_in_bank': '54646'
        }


class RejectDataForTest(DataForTest):
    reason = 'reject_by_service_security'

    @cached_property
    def _data(self):
        return {
            'reason': self.reason
        }


class RejectDataForTest2(RejectDataForTest):

    @cached_property
    def _data(self):
        return {
            'reason': self.reason,
            'force': True
        }


class EmptyDataForTest(DataForTest):

    @cached_property
    def _data(self):
        return {}


class SendRequestDataForTest(DataForTest):

    @cached_property
    def _data(self):
        return {
            'request_text': 'test'
        }


class CreateOfferDataForTest(DataForTest):

    @cached_property
    def _data(self):
        data = {
            'amount': 50000.00,
            'commission_bank': 1000.00,
            'default_commission_bank': 500.00,
            'delta_commission_bank': 500.00,
            'offer_active_end_date': '2020-05-01',
            'contract_date_end': '2020-05-01',
        }
        for category in self.request.bank.bankofferdocumentcategory_set.filter(category__active=True,
                                                                               category__step=1):
            file_input_name = 'category_%s' % category.id
            with open(os.path.join(BASE_DIR, r'tests/conf/generate_request/test.pdf'), 'rb') as f:
                data.update({
                    file_input_name: File(f, name=file_input_name)
                })

        return data
