import re

from django.core.cache import cache

from accounting_report.fields import QuarterData
from accounting_report.helpers import QuarterParameters
from bank_guarantee.models import ExternalRequest
from .common import BaseRequestAdapter
from external_api.dadata_api import DaData


class OldRequestAdapter(BaseRequestAdapter):

    def __init__(self, request):
        super(OldRequestAdapter, self).__init__(request)
        self.external_request = ExternalRequest.objects.filter(
            bank=request.bank, request=request
        ).first()

    def get_client_registration_data(self):
        return {
            'type': 1 if self.request.client.ip == 0 else 2,
            'inn': self.request.client.anketa.reg_inn,
            'name': self.request.client.anketa.short_name,
            'fio': self.request.client.anketa.contact_face_fio,
            'mail': self.request.client.anketa.contact_email,
            'tel': self.request.client.anketa.contact_phone,
        }

    def get_user_data(self):
        return {
            'name': self.request.client.anketa.short_name,
            'fio': self.request.client.anketa.contact_face_fio,
            'mail': self.request.client.anketa.contact_email,
            'tel': self.request.client.anketa.contact_phone,
        }

    def get_user_ul_data(self):
        return {
            'name': '',
            'name_eng': '',
            'okopf': '',
            'tax_system': '',
            'ogrn': '',
            'date_state_reg': '',
            'reg_authority': '',
            'kpp': '',
            'date_certificate': '',
            'okpo': '',
            'oktmo': '',
            'okato': '',
            'okved': '',
            'fax': '',
            'site': '',
            'email': '',
            'u_tel': '',
            'u_tel_d': '',
            'u_mail': '',
            'u_fio': '',
            'u_cp_position': '',
            'employees': '',
            'employees1': '',
            'numbem_ssch': '',
            'average_salary_fund': '',
            'dgoodw_exp': '',
            'id_dgoodw_fin_con': '',
            'is_file_of_unpaid_document': '',
            'sum_of_document': '',
            'is_overdue_loans': '',
            'is_overdue_payables': '',
            'sum_accounts_payable': '',
            'sum_receivables': '',
            'is_arrears_to_employees': '',
            'is_queue_of_orders_for_bank': '',
            'is_beneficiary_of_transaction': '',
            'id_otin_deponafp': '',
            'id_relationship_bank': '',
            'id_otin_gsb_source': '',
            'id_conf_cladv': '',
            'code_of_subject': '',
        }

    def get_licences_data(self, license_ids):
        data = []
        licenses = self.request.client.anketa.anketalicenziya_set.filter(
            id__in=license_ids
        )
        for license in licenses:
            data.append(self.get_license_data(license))
        return data

    def get_license_data(self, license):
        if license.endless == 1:
            date_s = 'Бессрочная'
        else:
            date_s = license.end_date
        return {
            'license': license.number,
            'date': license.date.strftime('%d.%m.%Y'),
            'id_view': license.deyatelnost,
            'hint': license.vidana,
            'date_s': date_s,
        }

    def get_bank_accounts_data(self, accounts):
        data = []
        for account in accounts:
            data.append(self.get_bank_account_data(account))
        return data

    def get_bank_account_data(self, account):
        return {
            'current': account.bank_schet,
            'bic': account.bank_bik,
            'name': account.bank,
            'correspondent': account.bank_corr,
        }

    def get_persons_data(self, persons):
        data = []
        for person in persons:
            data.append(self.get_person_data(person))
        return data

    def get_person_data(self, person):
        fio = ' '.join([
            person.short_passport.first_name,
            person.short_passport.second_name,
            person.short_passport.last_name,
        ])
        document_type = 66
        if person.has_russian_passport == 1:
            document_type = 63
        if 'Временное удостоверение личности' in person.another_passport:
            document_type = 64
        if 'Паспорт иностранного гражданина' in person.another_passport:
            document_type = 65

        person_passport = ''
        if person.has_russian_passport == 1:
            person_passport = '%s-%s № %s' % (
                person.short_passport.series,
                person.short_passport.num,
                person.short_passport.num,
            )
        fias_address_cache_key = 'dadata_fias_%s' % person.short_passport.registration
        address = cache.get(fias_address_cache_key)
        if not address:
            api = DaData()
            data = api.get_address_suggest(
                person.place_of_registration
            )['suggestions'][0]['data']
            address = data.get('fias_id', '')
            cache.set(fias_address_cache_key, 30 * 24 * 60 * 60)

        birthday_address = cache.get(
            'dadata_fias_%s' % person.short_passport.birthday_where
        )
        if not address:
            api = DaData()
            data = api.get_address_suggest(
                person.place_of_birth
            )['suggestions'][0]['data']
            birthday_address = data.get('fias_id', '')
            cache.set(birthday_address, 30 * 24 * 60 * 60)
        founder_affiliation = 50
        if person.another_country_citizen:
            founder_affiliation = 49
        return {
            'fio': fio,
            'inn': person.short_passport.inn,
            'document_type': document_type,
            'issued_by': person.short_passport.issued_who,
            'numb_p': person_passport,
            'date_p': person.short_passport.issued_when,
            'division_code': person.short_passport.issued_code,
            'date_birth': person.short_passport.birthday,
            'citizenship': person.citizenship,
            'place_of_birth': person.short_passport.birthday_where,
            'registration_address_fias_link': address,
            'living_address_fias_link': birthday_address,
            'is_pdl': '',
            'which_pdl': '',
            'founder_affiliation': founder_affiliation,
            'country': '',
            'is_pdl_arr': '',
        }

    def get_finance(self, actual_period):
        need_quarter = QuarterParameters(
            actual_period['quarters'],
            re.search(r'\d{4}', actual_period['name_reporting_date'])
        )
        need_year = QuarterParameters(
            4,
            re.search(r'\d{4}', actual_period['name_previous_year'])
        )
        need_quarter = self.request.client.accounting_report.get_quarter_by_params(
            need_quarter
        )
        need_year = self.request.client.accounting_report.get_quarter_by_params(need_year)
        result = {}
        for code in QuarterData.allowed_codes:
            result.update({
                str(code): [
                    need_quarter.get_value(code),
                    need_year.get_value(code)
                ]
            })
        return result

    def get_guarantee_data(self):
        return {
            'number': '',
            'sum': '',
            'sum_proposed': '',
            'bg_term_1': '',
            'bg_term_2': '',
            'date_c': '',
            'indisputable_cancellation': '',
            'summary_protocol': '',
            'number_report': '',
            'date_p': '',
            'text_v_r': '',
            'source_financing': '',
            'subcontractor_text': '',
            'type_contract': '',
            'type_order': '',
            'text_contract': '',
            'contract_number': '',
            'contract_date': '',
            'types_software': '',
            'text_software': '',
        }

    def get_guarantee_lot_data(self):
        return {
            'lot': '',
            'tender_subject': '',
            'url_tr': '',
            'name': '',
            'determining_supplier': '',
            'date_publication': '',
            'nmc': '',
            'nmc_name': '',
            'customer': '',
            'address': '',
            'inn': '',
            'kpp': '',
            'ogrn': '',
        }

    def get_guarantee_advance_data(self):
        return {
            'date_c': '',
            'amount': '',
        }

    def get_short_user_ul_data(self):
        anketa = self.request.client.anketa
        nalog_map = {
            'ОСН': 'osno',
            'УСН': 'usn',
            'ЕНВД': 'envd',
            'ПСН': 'pat',
            'ЕСХН': 'echn',
        }
        if anketa.nalog_system:
            nalog_system = nalog_map.get(anketa.nalog_system.name)
        else:
            nalog_system = ''
        return {
            'tax_system': nalog_system
        }

    def get_entity_founders_data(self, entity_founders):
        data = []
        for founder in entity_founders:
            data.append(self.get_entity_founder_data(founder))
        return data

    def get_entity_founder_data(self, entity_founder):
        return {
            'name_le': '',
            'name_de': '',
            'inn': '',
            'organ_field': '',
            'percentage': '',
            'organ': '',
        }

    def get_accountant_data(self, external_request):
        return {
            'person_id': '',
            'user_hash': '',
            'term_of_office': '',
            'base_action': '',
            'dover': '',
            'dover_name': '',
            'dover_date': '',
            'dover_sr': '',
        }

    def get_chief_data(self, external_request):
        return {
            'person_id': '',
            'user_hash': '',
            'term_of_office': '',
            'base_action': '',
            'dover': '',
            'dover_name': '',
            'dover_date': '',
            'dover_sr': '',
        }

    def get_address_data(self, external_request):
        return {
            'user_hash': '',
            'legal_fias_id': '',
            'state_fias_id': '',
        }