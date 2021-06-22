import logging
import os
import re
import time
from time import sleep

from django.conf import settings
from django.utils import timezone

from accounting_report.logic import AccountingReport
from accounting_report.models import Quarter
from bank_guarantee.actions import ReturnToJobAction
from bank_guarantee.bank_integrations.api.farzoom.base import FarzoomSendRequest
from bank_guarantee.helpers.referal_sign import ReferalSign
from bank_guarantee.models import (
    ContractType, ContractPlacementWay, Offer, RequestStatus
)
from cabinet.base_logic.contracts.base import ContractsLogic
from cabinet.base_logic.printing_forms.base import PrintForm
from cabinet.constants.constants import TaxationType, Target, FederalLaw, OrganizationForm
from cabinet.models import EgrulData
from external_api.nalogru_api import NalogRu
from external_api.parsers_tenderhelp import ParsersApi
from files.models import BaseFile
from questionnaire.models import Profile
from settings.configs.banks import BankCode
from settings.settings import TESTING
from utils.helpers import IsoCountry, generate_log_tags

logger = logging.getLogger('django')


class SendRequest(FarzoomSendRequest):
    bank_code = BankCode.CODE_BKS_BANK
    print_form_type = PrintForm.TYPE_BKS_GENERATOR
    print_form_zip_type = PrintForm.TYPE_ZIP_BKS
    null = None

    def __init__(self, *args, **kwargs):
        if not TESTING:
            self.production_endpoint = settings.BKS_ENDPOINT
            self.bks_api_login = settings.BKS_API_LOGIN
            self.bks_api_password = settings.BKS_API_PASSWORD
            self.async_server = os.environ.get(
                'ASYNC_DOMAIN_NAME') + r'/update_status_from_bks'
        else:
            self.production_endpoint = 'https://test_bks_api.ru'
            self.bks_api_login = 'test_bks_login'
            self.bks_api_password = 'test_bks_password'
            self.async_server = 'test_async/bks_api'
        super(SendRequest, self).__init__(*args, **kwargs)

    def integration_enable(self):
        return self.enabled

    def period_formatted_date(self, period):
        months = {
            4: 12, 1: 3, 2: 6, 3: 9
        }
        year = period.year
        date = timezone.datetime(year, months.get(period.quarter), 1)
        return date.strftime('%Y-%m')

    def get_principalBuh(self, request):
        params = [
            Quarter.manager_accounting_report.get_last_closed_quarter_and_year(),
            Quarter.manager_accounting_report.get_last_year_quarter(),
            Quarter.manager_accounting_report.get_last_closed_quarter_and_year(),
        ]
        params[2].year -= 1

        quarters = []
        for param in params:
            quarter = AccountingReport(request.client).get_quarter_by_params(param)
            quarters.append(quarter)

        last_period = quarters[0]

        periods = {}
        codes = [
            1100, 1110, 1120, 1130, 1140, 1150, 1160, 1170, 1180, 1190, 1200, 1210, 1220,
            1230, 1240, 1250, 1260, 1300, 1310, 1320, 1340, 1350, 1360, 1370, 1400, 1410,
            1420, 1430, 1450, 1500, 1510, 1520, 1530, 1540, 1550, 1600, 1700, 1700, 2100,
            2110, 2120, 2200, 2210, 2220, 2300, 2310, 2320, 2330, 2340, 2350, 2400, 2410,
            2430, 2450, 2460, 5640
        ]
        for quarter in quarters:
            data = {}
            for code in codes:
                if quarter or quarter.not_empty():
                    value = quarter.get_value(code) * 1000
                    if code in [2120, 2220, 2330, 2350, 2410]:
                        value = abs(value)
                else:
                    value = 1
                data['b%s' % code] = value

            periods[self.period_formatted_date(quarter)] = data
        return {
            'latestPeriod': self.period_formatted_date(last_period),
            'periods': periods,
            'taxationAccountingType': 'f1f2',
            'taxationType': self.get_tax_type(request)
        }

    @staticmethod
    def get_tax_type(request):
        if request.client.profile.tax_system == TaxationType.TYPE_OSN:
            return 'osn'
        return 'usn'

    def get_beneficiares(self, request):
        return [{
            'fullName': request.tender.beneficiary_name,
            'inn': request.tender.beneficiary_inn,
            'kpp': request.tender.beneficiary_kpp,
            'ogrn': request.tender.beneficiary_ogrn,
            'legalAddress': request.tender.beneficiary_address,
            'actualAddress': request.tender.beneficiary_address,
            'purchaseAmount': self.convert_float(request.tender.price),
            'amount': self.convert_float(request.required_amount),
        }]

    def convert_date(self, value):
        try:
            return value.strftime(self.default_date_format)
        except Exception:
            return '0000-00-00'

    def __pack_address(self, address, address_type, status, rent_from, rent_to, area):
        data = {
            'address': address,
            'addressOwnType': status,
            'addressType': address_type,
            status: {
                'occupiedArea': self.convert_float(area)
            }
        }
        if status == 'rent':
            data['rent'].update({
                'contractEndDate': self.convert_date(rent_to),
                'contractStartDate': self.convert_date(rent_from),
            })
        return data

    def get_addresses(self, profile):
        """

        :param Profile profile:
        """
        legal_address_data = self.__pack_address(
            address=profile.legal_address,
            address_type='legal',
            status='property' if profile.legal_address_status else 'rent',
            rent_from=profile.legal_address_from,
            rent_to=profile.legal_address_to,
            area=0
        )
        if profile.fact_is_legal_address:
            fact_address_data = legal_address_data.copy()
            fact_address_data['addressType'] = 'actual'
        else:
            fact_address_data = self.__pack_address(
                address=profile.fact_address,
                address_type='actual',
                status='property' if profile.fact_address_status else 'rent',
                rent_from=profile.fact_address_from,
                rent_to=profile.fact_address_to,
                area=0
            )

        post_address_data = fact_address_data.copy()
        post_address_data['addressType'] = 'postal'

        return [
            fact_address_data,
            legal_address_data,
            post_address_data
        ]

    @staticmethod
    def get_personAttributes(person):
        citizen = person.citizenship
        citizen_other = ''
        iso = IsoCountry.get_info_country(citizen)
        if iso:
            citizen = iso['alpha3']
        else:
            citizen_other = citizen
            citizen = 'other'

        data = {
            'isIpdl': False,
            'isRpdl': False,
            'isMpdl': False,
            'citizenship': citizen,
            'otherCitizenship': citizen_other,
        }
        if hasattr(person, 'snils') and person.snils:
            data['snils'] = person.snils
        return data

    def get_authorizationExpirationDate(self, profile):
        if profile.general_director.document_gen_dir.expiration_date:
            return self.convert_date(
                profile.general_director.document_gen_dir.expiration_date)
        else:
            return (timezone.now() + timezone.timedelta(days=365 * 5)).strftime(
                self.default_date_format)

    def get_companyHead(self, profile):
        general_director = profile.general_director
        general_director_passport = general_director.passport
        if general_director.document_gen_dir.expiration_date:
            eioProtocolDate = self.convert_date(
                general_director.document_gen_dir.date_protocol_EIO)
        else:
            eioProtocolDate = self.convert_date(profile.reg_state_date)
        return {
            'inn': general_director.fiz_inn,
            'lastName': general_director.last_name,
            'firstName': general_director.first_name,
            'secondName': general_director.middle_name,
            'identityDocument': {
                'number': general_director_passport.number,
                'series': general_director_passport.series,
                'identityDocumentType': 'passportRf',
                'issuedDate': self.convert_date(general_director_passport.when_issued),
                'issuingAuthority': general_director_passport.issued_by,
                'issuingAuthorityCode': general_director_passport.issued_code,
                'validTillDate': '',
            },
            'eioProtocolDate': eioProtocolDate,
            'eioProtocolNumber': (general_director.document_gen_dir.number_protocol_EIO or
                                  profile.reg_ogrn),
            'authorizingDoc': general_director.document_gen_dir.name_and_number or 'ИП',
            'birthDate': self.convert_date(general_director_passport.date_of_birth),
            'birthPlace': general_director_passport.place_of_birth,
            'contacts': [
                {
                    'email': profile.contact_email,
                    'phone': self.convert_phone(profile.contact_phone)
                }
            ],
            'relationAttributes': {
                'authorizationExpirationDate': self.get_authorizationExpirationDate(
                    profile),
            },
            'personAttributes': self.get_personAttributes(general_director),
            'position': 'ceo',
            'actualAddress': general_director_passport.place_of_registration,
            "registrationAddress": general_director_passport.place_of_registration,
        }

    @staticmethod
    def convert_phone(value):
        cleared_phone = re.sub(r'(\+7|[ ()-])', '', value)
        if len(cleared_phone) == 11:
            cleared_phone = cleared_phone[1:]
        if len(cleared_phone) == 10:
            groups = re.match(r'(\d{3})(\d{3})(\d{2})(\d{2})', cleared_phone).groups()
            if len(groups) == 4 and all(groups):
                return '+7(%s)%s-%s-%s' % groups

    def get_accountant(self, profile: Profile):
        booker = profile.booker
        booker_passport = booker.passport
        return {
            'inn': booker.fiz_inn,
            'lastName': booker.last_name,
            'firstName': booker.first_name,
            'secondName': booker.middle_name,
            'identityDocument': {
                'number': booker_passport.number,
                'series': booker_passport.series,
                'identityDocumentType': 'passportRf',
                'issuedDate': self.convert_date(booker_passport.when_issued),
                'issuingAuthority': booker_passport.issued_by,
                'issuingAuthorityCode': booker_passport.issued_code,
            },
            'authorizingDoc': booker.booker_document or '-',
            'birthDate': self.convert_date(booker_passport.date_of_birth),
            'birthPlace': booker_passport.place_of_birth,
            'contacts': [
                {
                    'email': profile.contact_email,
                    'phone': self.convert_phone(profile.contact_phone)
                }
            ],
            'personAttributes': self.get_personAttributes(booker),
            'position': 'other',
            'otherPosition': booker.booker_post or '-',
            'actualAddress': booker_passport.place_of_registration,
            'registrationAddress': booker_passport.place_of_registration,
        }

    def get_commercial_contracts_number(self, request):
        """Сопостовимые контракты"""
        need_sum = request.required_amount / 2
        helper = ParsersApi()
        contracts = helper.zakupki.get_contracts(request.client.profile.reg_inn)
        all_contracts = (contracts.get('fz44') or []) + (contracts.get('fz223') or [])
        execute_end = list(
            filter(lambda x: x.status == 'Исполнение завершено', all_contracts))
        result = len(list(filter(lambda x: x.price > need_sum, execute_end)))
        if result:
            return result
        all_contracts = list(map(lambda x: x.price, all_contracts))
        if len(all_contracts) > 5:
            all_contracts = sorted(all_contracts)[-5:]
        return 5 if sum(all_contracts) > (float(request.required_amount) * 0.6) else 0

    @property
    def documents_map(self):
        return {
            'doc_finReportQ': [73, 48],
            'doc_finReportConfirm': [48],
            'doc_guarantorDocumentEIO': [4],
            'doc_principalDocumentConfirming': [75],
            'doc_principalDocumentEIO': [61],
            'doc_principalExtractRegistry': [19],
            'doc_principalFinReport': [73],
            'doc_principalPassport': [4, 63],
            'doc_taxForm': [129, 24],
            'doc_principalLicense': [62],
        }

    def get_data_for_send(self, request):
        """

        :param bank_guarantee.models.Request request:
        """
        external_request = self.get_external_request(request)
        need_profile = True
        need_documents = True
        if not external_request.external_id:
            need_callback_url = True
        else:
            need_callback_url = False
        need_check_similar = need_documents or need_profile
        data = {}
        similar = 0
        if need_check_similar:
            finished_contracts = ContractsLogic(request.client).get_finished_contracts()
            for contract in finished_contracts:
                if (contract.price or 0) >= float(
                    request.required_amount
                ) * 0.6:
                    similar += 1
        if need_profile:
            profile = request.client.profile
            guarantee_type = None
            if Target.PARTICIPANT in request.targets:
                guarantee_type = 'participation'
            if Target.EXECUTION in request.targets:
                guarantee_type = 'execution'
            if not guarantee_type:
                if Target.WARRANTY in request.targets:
                    guarantee_type = 'period'
            contact_person_fio_parts = profile.contact_name.split(' ')
            if len(contact_person_fio_parts) == 3:
                fio = {
                    'firstName': contact_person_fio_parts[1] or 'Без имени',
                    'secondName': contact_person_fio_parts[0],
                    'lastName': contact_person_fio_parts[2] or 'Без отчества',
                }
            elif len(contact_person_fio_parts) == 2:
                fio = {
                    'firstName': contact_person_fio_parts[1] or 'Без имени',
                    'secondName': contact_person_fio_parts[0],
                    'lastName': 'Без отчества',
                }
            else:
                fio = {
                    'firstName': contact_person_fio_parts[0],
                    'secondName': 'Без имени',
                    'lastName': 'Без отчества',
                }

            egrul_data = EgrulData().get_info(profile.reg_inn)
            reg_before_2002 = egrul_data.get('section-register', {}).get(
                'gos-number-before-2002', '')
            contacts = {
                'email': profile.contact_email,
                'workPhone': self.convert_phone(profile.contact_phone),
                'cellPhone': self.convert_phone(profile.contact_phone),
            }
            contacts.update(fio)

            try:
                wageFund = float(profile.salary_fund) * 12
            except ValueError:
                wageFund = 0

            if request.contract_type == ContractType.STATE:
                tender_contract_type = 'state'
            else:
                tender_contract_type = 'municipal'
            is_warranty = Target.WARRANTY in request.targets
            if request.placement_way == ContractPlacementWay.CLOSED_BIDDING:
                auction_type = 'private'
            else:
                auction_type = 'public'
            data = {
                'principal': {
                    'commercialContractsNumber': self.get_commercial_contracts_number(
                        request),
                    'addresses': self.get_addresses(profile),
                    'companyBeneficiaries': self.pack_beneficiaries(profile),
                    'companyHead': self.get_companyHead(profile),
                    'companyInfo': {
                        'egrDocLegalAddress': profile.legal_address,
                    },
                    'companyManagement': {
                        'soleExecutiveBody': 'companyHead',
                        'supremeGoverningBody': self.get_supremeGoverningBody(
                            request.client),
                    },
                    'contactPerson': contacts,
                    'founders': {
                        'foundersCompanies': self.get_foundersCompanies(profile),
                        'foundersPersons': self.get_foundersPersons(profile),
                    },
                    'fullName': profile.full_name,
                    'inn': profile.reg_inn,
                    'kpp': profile.reg_kpp or None,
                    'ogrn': profile.reg_ogrn,
                    'principalBuh': self.get_principalBuh(request),
                    'principalSigner': self.get_companyHead(profile),
                    'bankAccounts': self.get_bankAccounts(profile),
                    'liabilities': [],
                    'mainCustomers': [],
                    'mainProviders': [],
                    'staffInfo': {
                        'averageNumber': profile.number_of_employees,
                        'staffDebts': 0,
                        'wageFund': wageFund
                    },
                    'regBefore01072002': reg_before_2002 != '',
                    'regNumberBefore01072002': reg_before_2002,
                },
                'bankGuarantee': {
                    'tenderContractNumber': request.protocol_number or '0',
                    'tenderContractRegNumber': request.protocol_number or '0',
                    'tenderContractSignedDate': self.convert_date(request.protocol_date),
                    'lotNumber': self.get_lot_number(request),
                    'similarContractsNumber': similar,
                    'bankGuaranteeSum': self.convert_float(request.required_amount),
                    'bankGuaranteeType': guarantee_type,
                    'beneficiaries': self.get_beneficiares(request),
                    'endDate': self.convert_date(request.interval_to),
                    'federalLaw': self.get_federal_law(request),
                    'finalAmount': self.convert_float(request.suggested_price_amount),
                    'guaranteeReceivingWay': 'bankOffice',
                    'isCommercial': '',
                    'isContractConcluded': guarantee_type != 'participation',
                    'isIncludedForfeit': False,
                    'isRequiredIndisputableDebiting': request.downpay is True,
                    'isRequiredSecurityForGuaranteePeriod': is_warranty,
                    'marketPlace': 'test',
                    'contractMaxPrice': self.convert_float(request.tender.price),
                    'prepaymentAmount': self.convert_float(
                        request.tender.prepayment_amount),
                    'prepaymentExists': bool(request.tender.has_prepayment),
                    'purchaseNumber': request.tender.notification_id,
                    'purchasePublishedDate': self.convert_date(
                        request.tender.publish_date),
                    'requiredExecutionDate': self.convert_date(request.final_date),
                    'startDate': self.convert_date(request.interval_from),
                    'subject': request.tender.subject,
                    'tenderContractType': tender_contract_type,
                    'tenderType': request.get_placement_way_display(),
                    'url': request.tender.tender_url,
                    'auctionType': auction_type,
                    'tenderContractSubject': request.tender.subject,
                },
                'orderComments': (request.get_last_message([
                    'client',
                    'agent',
                    'general_agent'
                ]) or 'Заявка на получение банковской гарантии'),
            }
            if profile.booker:
                data['principal']['accountant'] = self.get_accountant(profile)
        if need_callback_url:
            data['callbackUrl'] = self.async_server
        if need_documents:
            data['documents'] = self.get_documents(request)
        result_code = 'SEND_TO_BANK'
        if external_request and external_request.external_id:
            status = external_request.get_other_data_for_key(self.key_status_response)
            if status.get('decisionOptions'):
                if result_code not in list(
                    map(lambda x: x['code'], status['decisionOptions'])
                ):
                    result_code = 'ACCEPT'
            else:
                result_code = None
        if result_code:
            data['decision'] = {"resultCode": result_code}
        data = self.clear_data(data)
        return data

    @staticmethod
    def get_lot_number(request):
        result = '1'
        try:
            temp = str(int(request.protocol_lot_number))
            if temp != '0':
                result = temp
        except Exception:
            pass
        return result

    def get_foundersCompanies(self, profile):
        data = []
        for company in profile.profilepartnerlegalentities_set.all():
            data.append({
                'fullName': company.name,
                'inn': company.inn,
                'kpp': company.kpp,
                'ogrn': company.ogrn,
                'sharePercent': self.convert_float(company.share),
            })
        return data

    def get_foundersPersons(self, profile):
        data = []
        for person in profile.profilepartnerindividual_set.filter(share__gt=0):
            data.append({
                'inn': person.fiz_inn,
                'lastName': person.last_name,
                'firstName': person.first_name,
                'secondName': person.middle_name,
                'identityDocument': {
                    'number': person.passport.number,
                    'series': person.passport.series,
                    'identityDocumentType': 'passportRf',
                    'issuedDate': self.convert_date(person.passport.when_issued),
                    'issuingAuthority': person.passport.issued_by,
                    'issuingAuthorityCode': person.passport.issued_code,
                },
                'birthDate': self.convert_date(person.passport.date_of_birth),
                'birthPlace': person.passport.place_of_birth,
                'contacts': [
                    {
                        'email': profile.contact_email,
                        'phone': self.convert_phone(profile.contact_phone),
                    }
                ],
                'personAttributes': self.get_personAttributes(person),
                'sharePercent': self.convert_float(person.share),
                'actualAddress': person.passport.place_of_registration,
                'registrationAddress': person.passport.place_of_registration
            })
        return data

    def get_headers(self):
        return {
            'cache-control': 'no-cache',
            'Content-Type': 'application/json',
            'x-api-login': self.bks_api_login,
            'x-api-password': self.bks_api_password,
        }

    def get_bankAccounts(self, profile):
        data = []
        use_in_documents = True
        for account in profile.bankaccount_set.all():
            data.append({
                'bank': {
                    'bik': account.bank_bik.strip(),
                    'corrNumber': account.correspondent_account.strip(),
                    'name': account.bank.strip(),
                },
                'cardFile2': account.has_unpaid_account is True,
                'number': account.bank_account_number.strip(),
                'useInDocuments': use_in_documents
            })
            use_in_documents = False
        return data

    def get_federal_law(self, request):
        return {
            FederalLaw.LAW_44: '44',
            FederalLaw.LAW_223: '223',
            FederalLaw.LAW_185: '185',
            FederalLaw.LAW_615: '615',
        }.get(request.tender.federal_law, '')

    def get_supremeGoverningBody(self, client):
        if not client.is_organization:
            return 'Индивидуальный предприниматель'

        if client.profile.organization_form == OrganizationForm.TYPE_AO:
            return 'Обще собрание акционеров'
        return 'Общее собрание участников'

    def pack_beneficiaries(self, profile):
        data = []
        for beneficiar in profile.persons:
            beneficiary_reason = 'directCapitalParticipation'
            if beneficiar.is_general_director:
                beneficiary_reason = 'companyHead'
            data.append({
                'inn': beneficiar.fiz_inn,
                'lastName': beneficiar.last_name,
                'firstName': beneficiar.first_name,
                'secondName': beneficiar.middle_name,
                'identityDocument': {
                    'number': beneficiar.passport.number if beneficiar.passport else '',
                    'series': beneficiar.passport.series if beneficiar.passport else '',
                    'identityDocumentType': 'passportRf',
                    'issuedDate': (self.convert_date(beneficiar.passport.when_issued)
                                   if beneficiar.passport else ''),
                    'issuingAuthority': (beneficiar.passport.issued_by
                                         if beneficiar.passport else ''),
                    'issuingAuthorityCode': (beneficiar.passport.issued_code
                                             if beneficiar.passport else ''),
                },
                "birthDate": (self.convert_date(beneficiar.passport.date_of_birth)
                              if beneficiar.passport else ''),
                'birthPlace': (beneficiar.passport.place_of_birth
                               if beneficiar.passport else ''),
                'contacts': [
                    {
                        'email': profile.contact_email,
                        'phone': self.convert_phone(profile.contact_phone)
                    }
                ],
                'personAttributes': self.get_personAttributes(beneficiar),
                'sharePercent': self.convert_float(beneficiar.share),
                'actualAddress': (beneficiar.passport.place_of_registration
                                  if beneficiar.passport else ''),
                'registrationAddress': (beneficiar.passport.place_of_registration
                                        if beneficiar.passport else ''),
                'beneficiaryReason': beneficiary_reason,
            })

        for beneficiar in profile.persons_entities:
            beneficiary_reason = 'directCapitalParticipation'
            helper = NalogRu()
            if beneficiar.passport:
                data.append({
                    'inn': helper.get_inn(
                        beneficiar.last_name,
                        beneficiar.first_name,
                        beneficiar.middle_name,
                        beneficiar.passport.series.replace("'", ''),
                        beneficiar.passport.number.replace("'", ''),
                        beneficiar.passport.date_of_birth
                    ),
                    'lastName': beneficiar.last_name,
                    'firstName': beneficiar.first_name,
                    'secondName': beneficiar.middle_name,
                    'identityDocument': {
                        'number': beneficiar.passport.number.replace("'", ''),
                        'series': beneficiar.passport.series.replace("'", ''),
                        'identityDocumentType': 'passportRf',
                        'issuedDate': self.convert_date(beneficiar.passport.when_issued),
                        'issuingAuthority': beneficiar.passport.issued_by,
                        'issuingAuthorityCode': beneficiar.passport.issued_code.replace(
                            "'",
                            ''
                        ),
                    },
                    "birthDate": self.convert_date(beneficiar.passport.date_of_birth),
                    'birthPlace': beneficiar.passport.place_of_birth,
                    'contacts': [
                        {
                            'email': profile.contact_email,
                            'phone': self.convert_phone(profile.contact_phone)
                        }
                    ],
                    'personAttributes': self.get_personAttributes(beneficiar),
                    'sharePercent': self.convert_float(beneficiar.share),
                    'actualAddress': (beneficiar.passport.place_of_registration
                                      if beneficiar.passport else ''),
                    'registrationAddress': (beneficiar.passport.place_of_registration
                                            if beneficiar.passport else ''),
                    'beneficiaryReason': beneficiary_reason,
                })

        return data

    @property
    def offer_map(self):
        return {
            'doc_guarantee': 1,
            'doc_bill': 4,
            'doc_bgScan': 2,
        }

    def in_process_action(self, external_request):
        from bank_guarantee.actions import AskOnRequestAction, \
            InProcessAction
        user = external_request.request.client.user_set.first()
        author = external_request.request.bank.user_set.first()
        if external_request.request.status.code == RequestStatus.CODE_CLIENT_SIGN:
            request = external_request.request
            request.status = RequestStatus.objects.get(
                code=RequestStatus.CODE_IN_BANK
            )
            request.save()
        ask_on_request_action = AskOnRequestAction(
            request=external_request.request, user=user)
        if ask_on_request_action.validate_access():
            ask_on_request_action.execute()
        in_proccess_action = InProcessAction(
            request=external_request.request, user=author)
        if in_proccess_action.validate_access():
            in_proccess_action.execute()

        return_to_job = ReturnToJobAction(
            request=external_request.request,
            user=author
        )
        if return_to_job.validate_access():
            return_to_job.execute()

    def to_sign_client_status(self, request):
        url = ReferalSign.generate_url(request.id, 'sign')
        self.push_message(
            request,
            'Добрый день!\n'
            'Просьба подписать заявку по ссылке '
            '<a href="{url}">{url}</a> '
            'ссылка действительна в течении 24-х часов'.format(url=url)
        )
        request.status = RequestStatus.objects.get(
            code=RequestStatus.CODE_CLIENT_SIGN
        )
        request.save()
        logger.info("Перевод в статус на подписании у клиента %s" % generate_log_tags(
            request=request
        ))

    def _update_status(self, external_request, data):  # noqa: MC0001
        """
        :param data:
        :param ExternalRequest external_request:
        """
        from bank_guarantee.actions import OfferBackAction, RejectAction, \
            SendRequestAction, ConfirmRequestAction, CreateOfferAction, SendOfferAction, \
            RequestFinishedAction

        if external_request.status in ['RejectedByBank', 'Executed', 'Failed']:
            return
        task_code = data.get('taskDefinitionKey', '')
        status = data.get('orderStatus', '')
        comment = data.get('statusDescription', '')
        bank_comment = data.get('bankComment', '')
        url = data.get('url', '')
        author = self.bank.user_set.first()
        # установка стандарнтной комиссии
        if (data.get(
            'commission'
        ) and external_request.get_other_data_for_key('default_commission') is None):
            external_request.set_other_data_for_key(
                'default_commission', data.get('commission'))
        if external_request.request.status.code not in [
            RequestStatus.CODE_OFFER_REJECTED,
            RequestStatus.CODE_REQUEST_BACK,
        ]:

            offer = Offer.objects.filter(
                request_id=external_request.request_id
            ).first()
            if status == 'RejectedByBank':
                if offer:
                    OfferBackAction(
                        request=external_request.request,
                        user=author
                    ).execute()
                else:
                    reason = bank_comment or comment
                    reason = reason or 'Отказ'
                    if 'Дубликат заявки' in reason:
                        reason = 'reject_assigned_by_another_agent'

                    RejectAction(
                        request=external_request.request,
                        user=author
                    ).execute({
                        'reason': reason,
                        'force': True
                    })
            elif status == 'PendingClient':
                if url:
                    if offer:
                        self.create_offer_doc(external_request, self.get_offer_doc(data))
                    else:
                        self.generate_print_forms(data, external_request)
                        self.to_sign_client_status(
                            external_request.request
                        )
            elif status == 'PendingAgent':
                if task_code == 'UserTask_ClientSignTime':
                    self.send_resend_decision(external_request)
                    sleep(2)
                    self.update_status(external_request)
                else:
                    confirm_request_action = ConfirmRequestAction(
                        request=external_request.request, user=author)
                    if confirm_request_action.validate_access():
                        confirm_request_action.execute()
                    external_request.refresh_from_db()
                    if task_code == 'UserTask_InitiatorApproveDocs':
                        commission = data.get('commission', 0)
                        date_active = timezone.now() + timezone.timedelta(days=2)
                        default_commission = external_request.get_other_data_for_key(
                            'default_commission'
                        ) or 0
                        delta = commission - default_commission

                        create_offer_action = CreateOfferAction(
                            request=external_request.request,
                            user=author
                        )
                        create_offer_action.execute({
                            'amount': external_request.request.required_amount,
                            'commission_bank': commission,
                            'commission_bank_percent': self.get_commission_percent(
                                commission,
                                external_request.request.interval,
                                external_request.request.required_amount
                            ),
                            'default_commission_bank': default_commission,
                            'default_commission_bank_percent': \
                                self.get_commission_percent(
                                # noqa E501
                                default_commission,
                                external_request.request.interval,
                                external_request.request.required_amount
                            ),
                            'delta_commission_bank': delta,
                            'offer_active_end_date': date_active.date(),
                            'contract_date_end': external_request.request.interval_to,
                            'not_documents': True,
                        })
                        self.create_offer_doc(external_request, self.get_offer_doc(data))
                        send_offer_action = SendOfferAction(
                            request=external_request.request,
                            user=author
                        )
                        if send_offer_action.validate_access():
                            send_offer_action.execute()
                    else:
                        message = '\n'.join(
                            self.get_errors(external_request.request, data)
                        )
                        SendRequestAction(
                            request=external_request.request,
                            user=author
                        ).execute({
                            'request_text': message
                        })

            elif status == 'InProcess':
                self.in_process_action(external_request)

            elif status == 'Executed':
                self.create_offer_doc(
                    external_request,
                    self.get_offer_docs_for_generate(data)
                )
                external_request.request.set_status(RequestStatus.CODE_OFFER_PREPARE)

                RequestFinishedAction(
                    request=external_request.request,
                    user=author
                ).execute({
                    'contract_number': data.get('orderNumber'),
                    'contract_date': timezone.now().date(),
                    'not_documents': True
                })

        elif status != 'RejectedByBank':
            self.reject_request(request=external_request.request)

    @staticmethod
    def get_commission_percent(total, interval, required_amount):
        total = float(total)
        required_amount = float(required_amount)
        interval = float(interval)
        result = total * 365 * 100 / interval / required_amount
        return round(result, 2)

    def send_resend_decision(self, external_request, comment=''):
        self.send_data_in_bank(url='/order/%s' % external_request.external_id, data={
            'decision': {
                'comment': comment,
                'isCommentRequired': False,
                'resultCode': 'RESEND'
            }
        }, method='PUT')

    def before_accept_offer(self, request):
        external_request = self.get_external_request(request)
        if external_request.status == 'PendingAgent':
            self.change_request(request, external_request)
        for _ in range(10):
            if external_request.status == 'PendingClient':
                return {'result': True}
            time.sleep(1)
            external_request.refresh_from_db()
        return {
            'result': False,
            'errors': 'Вышло время ожидания, обратитесь в тех. поддержку или попробуйте '
                      'повторить действие позже '
        }

    def pack_files(self, file_ids, signer=None):
        """

        :param doc:
        :param bank_guarantee.models.Request request:
        :param document_ids:
        """
        data = []
        files = BaseFile.objects.filter(id__in=file_ids)
        for file in files:
            file_name = file.get_download_name()
            sign = None
            if signer:
                sign = file.sign_set.filter(author__client=signer).first()
            if sign:
                file_name += '.sig'
                file = sign.signed_file
            else:
                file = file.file
            try:
                data.append({
                    'fileName': file_name,
                    'mimeType': file.mimetype,
                    'value': file.get_base64(),
                })
            except Exception as e:
                raise e
        return data
