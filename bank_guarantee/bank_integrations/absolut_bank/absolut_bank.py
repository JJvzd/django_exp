import logging
import os
import re
import time

import ujson
from django.utils import timezone
from django.utils.functional import cached_property

from accounting_report.logic import AccountingReport
from accounting_report.models import Quarter
from bank_guarantee.actions import CreateOfferAction, RequestFinishedAction, \
    SendOfferAction, SendRequestAction, \
    RejectAction, ReturnToJobAction, OfferPaidAction
from bank_guarantee.bank_integrations.api.base import push_rocket_chat, push_error
from bank_guarantee.bank_integrations.api.farzoom.base import FarzoomSendRequest
from bank_guarantee.helpers.referal_sign import ReferalSign
from bank_guarantee.models import ContractPlacementWay, ContractType, \
    RequestStatus, \
    LimitRequest
from bank_guarantee.status_classes import StatusNotFoundException
from base_request.logic.request_log import RequestLogger
from cabinet.base_logic.printing_forms.base import PrintForm
from cabinet.constants.constants import TaxationType, Target, FederalLaw
from common.helpers import format_decimal
from conclusions_app.conclusions.common import IsBankrotConclusion
from conclusions_app.conclusions_logic import ConclusionsLogic
from external_api.nalogru_api import NalogRu
from questionnaire.models import ProfilePartnerIndividual
from settings import settings
from settings.configs.banks import BankCode
from utils.helpers import IsoCountry, get_sex_by_middle_name, \
    generate_log_tags

logger = logging.getLogger('django')


class SendRequest(FarzoomSendRequest):
    bank_code = BankCode.CODE_ABSOLUT
    null = 'NON_FIELD'
    print_form_type = PrintForm.TYPE_ABSOLUT_GENERATOR
    print_form_zip_type = PrintForm.TYPE_ZIP_ABSOLUT

    def __init__(self, *args, **kwargs):
        if not settings.TESTING:
            self.production_endpoint = settings.ABSOLUTE_ENDPOINT
            self.x_api_login = settings.TH_ABSOLUT_API_LOGIN
            self.x_api_password = settings.TH_ABSOLUT_API_PASSWORD
            self.async_server = os.environ.get('ASYNC_DOMAIN_NAME') + r'/absolut_api'
        else:
            self.production_endpoint = 'https://test_absolut_api.ru'
            self.x_api_login = 'test_absolut_login'
            self.x_api_password = 'test_absolut_password'
            self.async_server = 'test_async/absolut_api'
        super(SendRequest, self).__init__(*args, **kwargs)

    def convert_date(self, date):
        if hasattr(date, 'strftime'):
            return date.strftime(self.default_date_format)
        return self.null

    def get_identity_document(self, person):
        passport = person.passport
        if passport:
            return {
                'number': passport.number,
                'series': passport.series,
                'identityDocumentType': 'passportRf',
                'issuedDate': self.convert_date(passport.when_issued),
                'issuingAuthority': passport.issued_by,
                'issuingAuthorityCode': passport.issued_code,
            }
        return self.null

    def get_contacts(self, partner_individual):
        return [{
            'email': partner_individual.profile.contact_email,
            'phone': self.convert_phone(partner_individual.profile.contact_phone),
        }]

    def get_position_doc(self, partner_individual):
        if partner_individual.is_general_director:
            return partner_individual.document_gen_dir.gen_dir_doc_right() or 'ИП'
        elif partner_individual.is_booker:
            return partner_individual.booker_document
        logger.error(
            'Получения документов должности у лица не '
            'являющегося Ген.Дир или Гл.Бух: %s' % partner_individual.get_name
        )
        return self.null

    def get_string_position(self, partner_individual):
        if partner_individual.is_general_director:
            return partner_individual.gen_dir_post
        elif partner_individual.is_booker:
            return partner_individual.booker_post
        logger.error(
            'Получения должности у лица не '
            'являющегося Ген.Дир или Гл.Бух: %s' % partner_individual.get_name
        )
        return self.null

    def get_position(self, partner_individual):
        choices = [
            ('actingCeo', [
                'врио генерального директора',
                'временно исполняющий обязанности генерального директора',
                'ио генерального директора',
                'исполняющий обязанности генерального директора',
            ]),
            ('ceo', ['генеральный директор']),
            ('director', ['директор']),
            ('president', ['президент']),
        ]
        result = self.get_string_position(partner_individual)
        for key, values in choices:
            for value in values:
                if value in result.lower():
                    return key
        return 'other'

    def get_other_position(self, partner_individual):
        if self.get_position(partner_individual) == 'other':
            return self.get_string_position(partner_individual)
        return self.null

    def check_gender(self, partner_individual):
        return 'female' if get_sex_by_middle_name(
            partner_individual.middle_name) == 'F' else 'male'

    def get_ipdl_employer_address(self, partner_individual):
        return self.null

    def get_ipdl_employer_name(self, partner_individual):
        return self.null

    def get_ipdl_relation(self, partner_individual):
        return self.null

    def is_pdl(self, partner_individual):
        return False

    def is_mpdl(self, partner_individual):
        return False

    def is_rpdl(self, partner_individual):
        return False

    def get_mpdl_employer_address(self, partner_individual):
        return self.null

    def get_mpdl_employer_name(self, partner_individual):
        return self.null

    def get_mpdl_position(self, partner_individual):
        return self.null

    def get_mpdl_relation(self, partner_individual):
        return self.null

    def get_rpdl_employer_address(self, partner_individual):
        return self.null

    def get_rpdl_employer_name(self, partner_individual):
        return self.null

    def get_rpdl_position(self, partner_individual):
        return self.null

    def get_rpdl_relation(self, partner_individual):
        return self.null

    def get_person_attributes(self, partner_individual):
        return {
            'citizenship': (IsoCountry.get_info_country(
                partner_individual.citizenship) or {}).get('alpha3'),
            'countryOfResidence': (IsoCountry.get_info_country(
                partner_individual.citizenship) or {}).get('alpha3'),
            'gender': self.check_gender(partner_individual),
            'ipdlEmployerAddress': self.get_ipdl_employer_address(partner_individual),
            'ipdlEmployerName': self.get_ipdl_employer_name(partner_individual),
            'ipdlRelation': self.get_ipdl_relation(partner_individual),
            'isIpdl': self.is_pdl(partner_individual),
            'isMpdl': self.is_mpdl(partner_individual),
            'isRpdl': self.is_rpdl(partner_individual),
            'mpdlEmployerAddress': self.get_mpdl_employer_address(partner_individual),
            'mpdlEmployerName': self.get_mpdl_employer_name(partner_individual),
            'mpdlPosition': self.get_mpdl_position(partner_individual),
            'mpdlRelation': self.get_mpdl_relation(partner_individual),
            'rpdlEmployerAddress': self.get_rpdl_employer_address(partner_individual),
            'rpdlEmployerName': self.get_rpdl_employer_name(partner_individual),
            'rpdlPosition': self.get_rpdl_position(partner_individual),
            'rpdlRelation': self.get_rpdl_relation(partner_individual),
            'snils': partner_individual.snils if hasattr(
                partner_individual,
                'snils'
            ) else self.null,
        }

    def get_authorization_expiration_date(self, partner_individual):
        if partner_individual.is_general_director:
            if partner_individual.document_gen_dir.is_indefinitely:
                return self.null
            if partner_individual.document_gen_dir.expiration_date:
                return partner_individual.document_gen_dir.expiration_date.strftime(
                    '%Y-%m-%d'
                )
        return self.null

    def get_authorizaton_start_date(self, gen_dir):
        if gen_dir.document_gen_dir.date_protocol_EIO:
            return gen_dir.document_gen_dir.date_protocol_EIO.strftime(
                '%Y-%m-%d'
            )
        return self.null

    def get_relation_attributes(self, partner_individual):
        if partner_individual.is_general_director:
            return {
                'authorizationStartDate': self.get_authorizaton_start_date(
                    partner_individual
                ),
                'authorizationExpirationDate': self.get_authorization_expiration_date(
                    partner_individual
                )
            }

    def get_actual_address(self, partner_individual):
        return partner_individual.passport.place_of_registration

    def get_registration_address(self, partner_individual: ProfilePartnerIndividual):
        if partner_individual.has_russian_passport:
            return partner_individual.passport.place_of_registration
        return self.null

    def get_birth_place(self, person):
        if person.has_russian_passport:
            return person.passport.place_of_birth
        return self.null

    def get_accountant(self, request):
        accountant = request.client.profile.booker
        if accountant:
            return {
                'inn': accountant.fiz_inn,
                'lastName': accountant.last_name,
                'firstName': accountant.first_name,
                'secondName': accountant.middle_name,
                'identityDocument': self.get_identity_document(accountant),
                'authorizingDoc': self.get_position_doc(accountant),
                'birthDate': accountant.passport.date_of_birth.strftime(
                    '%Y-%m-%d') if accountant.has_russian_passport else self.null,
                'birthPlace': self.get_birth_place(accountant),
                'contacts': self.get_contacts(accountant),
                'otherPosition': self.get_other_position(accountant),
                'personAttributes': self.get_person_attributes(accountant),
                'position': self.get_position(accountant),
                'relationAttributes': self.get_relation_attributes(accountant),
                'actualAddress': self.get_actual_address(accountant),
                'registrationAddress': self.get_registration_address(accountant),
            }

    def get_legal_address_property(self, request):
        if request.client.profile.legal_address_status:
            return {
                'certIssueDate': None,
                'certNumber': None,
                'occupiedArea': None,
            }
        return self.null

    def get_legal_address_rent(self, request):
        profile = request.client.profile
        if not profile.legal_address_status:
            return {
                'amount': self.null,
                'contractEndDate': profile.legal_address_to.strftime('%Y-%m-%d'),
                'contractNumber': self.null,
                'contractStartDate': profile.legal_address_from.strftime('%Y-%m-%d'),
                'landlordBankAccount': self.null,
                'landlordBankReq': self.null,
                'landlordInn': self.null,
                'landlordName': self.null,
                'landlordPhone': self.null,
                'occupiedArea': self.null,
            }
        return self.null

    def get_legal_address_principal(self, request):
        profile = request.client.profile
        return {
            'address': profile.legal_address,
            'addressOwnType': 'property' if profile.legal_address_status else 'rent',
            'addressType': 'legal',
            'property': self.get_legal_address_property(request),
            'rent': self.get_legal_address_rent(request),
        }

    def get_actual_address_property(self, request):
        if request.client.profile.fact_address_status:
            return {
                'certIssueDate': None,
                'certNumber': None,
                'occupiedArea': None,
            }
        return self.null

    def get_actual_address_rent(self, request):
        profile = request.client.profile
        if not profile.fact_address_status:
            return {
                'amount': self.null,
                'contractEndDate': profile.fact_address_to.strftime('%Y-%m-%d'),
                'contractNumber': self.null,
                'contractStartDate': profile.fact_address_to.strftime('%Y-%m-%d'),
                'landlordBankAccount': self.null,
                'landlordBankReq': self.null,
                'landlordInn': self.null,
                'landlordName': self.null,
                'landlordPhone': self.null,
                'occupiedArea': self.null,
            }
        return self.null

    def get_actual_address_principal(self, request):
        profile = request.client.profile
        if profile.fact_is_legal_address:
            temp = self.get_legal_address_principal(request)
            temp['addressType'] = 'actual'
            return temp
        return {
            'address': profile.fact_address,
            'addressOwnType': 'property' if profile.fact_address_status else 'rent',
            'addressType': 'actual',
            'property': self.get_actual_address_property(request),
            'rent': self.get_actual_address_rent(request),
        }

    def get_postal_address_principal(self, request):
        temp = self.get_actual_address_principal(request)
        temp['addressType'] = 'postal'
        return temp

    def get_bank_accounts(self, request):
        result = []
        for bank_account in request.client.profile.profileaccounts:
            result.append({
                'bank': {
                    'bik': bank_account.bank_bik,
                    'corrNumber': bank_account.correspondent_account,
                    'name': bank_account.bank
                },
                'cardFile2': self.null,
                'cardFile2Amount': self.null,
                'number': bank_account.bank_account_number
            })
        return result if len(result) != 0 else self.null

    def get_commercial_contracts(self, request):
        return self.null

    def beneficiars(self, request):
        result = []
        for beneficiar in request.client.profile.persons:
            result.append({
                'inn': beneficiar.fiz_inn,
                'lastName': beneficiar.last_name,
                'firstName': beneficiar.first_name,
                'secondName': beneficiar.middle_name,
                'identityDocument': self.get_identity_document(beneficiar),
                'beneficiaryReason': self.null,
                'birthDate': beneficiar.passport.date_of_birth.strftime(
                    '%Y-%m-%d') if beneficiar.has_russian_passport else self.null,
                'birthPlace': self.get_birth_place(beneficiar),
                'contacts': self.get_contacts(beneficiar),
                'personAttributes': self.get_person_attributes(beneficiar),
                'sharePercent': beneficiar.share,
                'shareSum': self.null,
                'actualAddress': self.get_actual_address(beneficiar),
                'registrationAddress': self.get_registration_address(beneficiar),
            })
        for beneficiar in request.client.profile.persons_entities:
            helper = NalogRu()
            if beneficiar.passport:
                result.append({
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
                    'identityDocument': self.get_identity_document(beneficiar),
                    'beneficiaryReason': self.null,
                    'birthDate': beneficiar.passport.date_of_birth.strftime(
                        '%Y-%m-%d') if beneficiar.passport else self.null,
                    'contacts': self.get_contacts(beneficiar),
                    'personAttributes': self.get_person_attributes(beneficiar),
                    'sharePercent': beneficiar.share,
                    'shareSum': self.null,
                    'actualAddress': beneficiar.passport.place_of_registration if (
                        beneficiar.passport
                    ) else self.null,
                    'registrationAddress': beneficiar.passport.place_of_registration if (
                        beneficiar.passport
                    ) else self.null,
                })

        return result if len(result) != 0 else self.null

    def get_company_head(self, request):
        general_director = request.client.profile.general_director
        return {
            'lastName': general_director.last_name,
            'firstName': general_director.first_name,
            'secondName': general_director.middle_name,
            'identityDocument': self.get_identity_document(general_director),
            'authorizingDoc': self.get_position_doc(general_director),
            'birthDate': general_director.passport.date_of_birth.strftime(
                self.default_date_format
            ) if general_director.has_russian_passport else self.null,
            'birthPlace': self.get_birth_place(general_director),
            'contacts': self.get_contacts(general_director),
            'eioProtocolDate': self.get_eio_protocol_date(general_director),
            'eioProtocolNumber': self.get_eio_protocol_number(general_director),
            'inn': general_director.fiz_inn,
            'otherPosition': self.get_other_position(general_director),
            'personAttributes': self.get_person_attributes(general_director),
            'position': self.get_position(general_director),
            'relationAttributes': self.get_relation_attributes(general_director),
            'actualAddress': self.get_actual_address(general_director),
            'registrationAddress': self.get_registration_address(general_director),
        }

    def get_eio_protocol_number(self, gen_dir):
        return gen_dir.document_gen_dir.number_protocol_EIO or self.null

    def get_eio_protocol_date(self, gen_dir):
        if gen_dir.document_gen_dir.date_protocol_EIO:
            return gen_dir.document_gen_dir.date_protocol_EIO.strftime(
                '%Y-%m-%d'
            )
        return self.null

    def get_accounting_type(self, request):
        return self.null

    def get_beneficiars_info(self, request):
        result = []
        for beneficiar in self.beneficiars(request):
            result.append('%s %s %s' % (
                beneficiar['lastName'],
                beneficiar['firstName'],
                beneficiar['secondName']
            ))
        return ','.join(result) if len(result) != 0 else self.null

    def get_finance_position(self, request):
        return self.null

    def get_financial_reviews_contragents(self, request):
        return 'missing'

    def get_financial_reviews_credit(self, request):
        return 'missing'

    def get_fund_sources(self, request):
        return 'own'

    def get_fund_sources_other(self, request):
        return self.null

    def get_has_assets(self, request):
        return self.null

    def get_has_bankruptcy_court_decisions(self, request):
        result = ConclusionsLogic.get_conclusion_result(
            request.client,
            IsBankrotConclusion,
        )
        return bool(result.result)

    def get_has_bankruptcy_cases(self, request):
        return self.null

    def get_has_bankruptcy_procedures(self, request):
        return self.null

    def get_has_banks_feedback(self, request):
        return self.null

    def get_has_beneficiaries_info(self, request):
        return len(self.beneficiars(request)) > 0

    def get_has_budget_overdue(self, request):
        return self.null

    def get_has_card_file2(self, request):
        return self.null

    def get_has_credit_decision(self, request):
        return self.null

    def has_defendant_court_cases(self, request):
        return self.null

    def get_has_employees(self, request):
        return float(request.client.profile.number_of_employees) > 0

    def get_has_funds_overdue(self, request):
        return self.null

    def get_has_hidden_losses(self, request):
        return self.null

    def get_has_incorrect_accounting_reports(self, request):
        return self.null

    def get_has_liquidation_procedures(self, request):
        return self.null

    def get_company_info(self, request):
        profile = request.client.profile
        return {
            'accountingType': self.get_accounting_type(request),
            'authorizedShareCapital': profile.authorized_capital_announced,
            'bankBusinessRelationsType': 'obtainingBankGuarantee',
            'bankBusinessRelationsTypeOther': self.null,
            'beneficiariesInfo': self.get_beneficiars_info(request),
            'bigReceivables': self.null,
            'creditHistory': 'noHistory',
            'debtToBudget': self.null,
            'debtToBudgetAmount': self.null,
            'egrDocLegalAddress': profile.legal_address,
            'financialAndEconomicActivityType': self.null,
            'financialAndEconomicActivityTypeOther': self.null,
            'financialPosition': self.get_finance_position(request),
            'financialReviewsContragents': self.get_financial_reviews_contragents(
                request),
            'financialReviewsCredit': self.get_financial_reviews_credit(request),
            'fundsSources': self.get_fund_sources(request),
            'fundsSourcesOther': self.get_fund_sources_other(request),
            'hasAssets': self.get_has_assets(request),
            'hasBankruptcyCases': self.get_has_bankruptcy_cases(request),
            'hasBankruptcyCourtDecisions': self.get_has_bankruptcy_court_decisions(
                request),
            'hasBankruptcyProcedures': self.get_has_bankruptcy_procedures(request),
            'hasBanksFeedback': self.get_has_banks_feedback(request),
            'hasBeneficiariesInfo': self.get_has_beneficiaries_info(request),
            'hasBudgetOverdue': self.get_has_budget_overdue(request),
            'hasCardFile2': self.get_has_card_file2(request),
            'hasCreditDecision': self.get_has_credit_decision(request),
            'hasDefendantCourtCases': self.has_defendant_court_cases(request),
            'hasEmployees': self.get_has_employees(request),
            'hasFundsOverdue': self.get_has_funds_overdue(request),
            'hasHiddenLosses': self.get_has_hidden_losses(request),
            'hasIncorrectAccountingReports': self.get_has_incorrect_accounting_reports(
                request),
            'hasLicense': request.client.profile.has_license_sro,
            'hasLiquidationProcedures': self.get_has_liquidation_procedures(request),
            # пропустил поля
            'paidShareCapital': request.client.profile.authorized_capital_paid,
            # доработать
            'hasRelations': False,
        }

    def get_company_management(self, request):
        return {
            'soleExecutiveBody': 'companyHead',
            'supremeGoverningBody': request.client.profile.general_director.gen_dir_post,
        }

    def get_contact_person(self, request):
        profile = request.client.profile
        name = profile.contact_name.split(' ')
        return {
            'lastName': name[0],
            'firstName': name[1] if (len(name) > 1) and name[1] else 'Без имени',
            'secondName': name[2] if (len(name) > 2) and name[2] else 'Без отчества',
            'cellPhone': self.convert_phone(profile.contact_phone),
            'email': profile.contact_email,
            'workPhone': self.convert_phone(profile.contact_phone),
        }

    def get_founders_companies(self, request):
        result = []
        for company in request.client.profile.persons_entities:
            result.append({
                'fullName': company.name,
                'inn': company.inn,
                'kpp': company.kpp,
                'ogrn': company.ogrn,
                'sharePercent': company.share,
            })
        return result if len(result) > 0 else self.null

    def get_founders_persons(self, request):
        result = []
        for person in request.client.profile.persons:
            result.append({
                'inn': person.fiz_inn,
                'lastName': person.last_name,
                'firstName': person.first_name,
                'secondName': person.middle_name,
                'identityDocument': self.get_identity_document(person),
                'birthDate': person.passport.date_of_birth.strftime(
                    '%Y-%m-%d') if person.has_russian_passport else self.null,
                'birthPlace': self.get_birth_place(person),
                'contacts': self.get_contacts(person),
                'personAttributes': self.get_person_attributes(person),
                'sharePercent': person.share,
                'registrationAddress': self.get_registration_address(person),
                'actualAddress': self.get_actual_address(person),
            })
        return result if len(result) > 0 else self.null

    def period_formatted_date(self, period):
        months = {
            4: 12, 1: 3, 2: 6, 3: 9
        }
        year = period.year
        date = timezone.datetime(year, months.get(period.quarter), 1)
        return date.strftime('%Y-%m')

    def get_principal_buh(self, request):
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
            1230, 1240, 1250, 1260, 1300,
            1310, 1320, 1340, 1350, 1360, 1370, 1400, 1410, 1420, 1430, 1450, 1500, 1510,
            1520, 1530, 1540, 1550, 1600,
            1700, 1700, 2100, 2110, 2120, 2200, 2210, 2220, 2300, 2310, 2320, 2330, 2340,
            2350, 2400, 2410, 2430, 2450,
            2460, 5640
        ]
        for quarter in quarters:
            data = {}
            for code in codes:
                if quarter or quarter.not_empty():
                    value = quarter.get_value(code) * 1000
                    if code in [
                        2110, 2120, 2210, 2220, 2310, 2320, 2330, 2340, 2350, 2410
                    ]:
                        value = abs(value)
                else:
                    value = 1
                data['b%s' % code] = value

            periods[self.period_formatted_date(quarter)] = data
        return {
            'latestPeriod': self.period_formatted_date(last_period),
            'periods': periods,
            'taxationAccountingType': 'f1f2',
            'taxationType': 'osn' if (
                request.client.profile.tax_system == TaxationType.TYPE_OSN
            ) else 'usn'
        }

    def get_staff_info(self, request):
        return {
            'averageNumber': request.client.profile.number_of_employees,
        }

    def get_guarantee_type(self, request):
        guarantee_type = None
        if Target.PARTICIPANT in request.targets:
            guarantee_type = 'participation'
        if Target.EXECUTION in request.targets:
            guarantee_type = 'execution'
        if not guarantee_type:
            if Target.WARRANTY in request.targets:
                guarantee_type = 'period'
            if Target.AVANS_RETURN in request.targets:
                guarantee_type = 'returnAdvance'
        return guarantee_type

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

    def get_federal_law(self, request):
        return {
            FederalLaw.LAW_44: '44',
            FederalLaw.LAW_223: '223',
            FederalLaw.LAW_185: '185-615',
            FederalLaw.LAW_615: '185-615',
        }.get(request.tender.federal_law, '')

    def get_bank_guarantee(self, request):
        return {
            'auctionType': 'private' if (
                request.placement_way == ContractPlacementWay.CLOSED_BIDDING
            ) else 'public',
            'bankGuaranteeSum': self.convert_float(request.required_amount),
            'bankGuaranteeType': self.get_guarantee_type(request),
            'beneficiaries': self.get_beneficiares(request),
            'contractMaxPrice': self.convert_float(request.tender.price),
            'endDate': self.convert_date(request.interval_to),
            'federalLaw': self.get_federal_law(request),
            'finalAmount': self.convert_float(request.suggested_price_amount),
            'guaranteeReceivingWay': 'bankOffice',
            'lotNumber': request.protocol_lot_number or '1',
            'purchaseNumber': request.tender.notification_id,
            'purchasePublishedDate': self.convert_date(request.tender.publish_date),
            'requiredExecutionDate': self.convert_date(request.final_date),
            'startDate': self.convert_date(request.interval_from),
            'subject': request.tender.subject,
            'tenderContractType': 'state' if (
                request.contract_type == ContractType.STATE
            ) else 'municipal',
            'tenderContractSubject': request.tender.subject,
            'tenderType': request.get_placement_way_display(),
            'url': request.tender.tender_url,
        }

    def get_documents_list(self):
        return self.send_data_in_bank('/doc/types', {}, 'GET')

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

    def get_principal_signer(self, request):
        person = request.client.profile.general_director
        return {
            'inn': person.fiz_inn,
            'lastName': person.last_name,
            'firstName': person.first_name,
            'secondName': person.middle_name,
            'identityDocument': self.get_identity_document(person),
            'authorizingDoc': self.get_position_doc(person),
            'birthDate': self.convert_date(
                person.passport.date_of_birth
            ) if person.has_russian_passport else self.null,
            'birthPlace': self.get_birth_place(person),
            'personAttributes': self.get_person_attributes(person),
            'position': self.get_position(person),
            'otherPosition': self.get_other_position(person),
            'registrationAddress': self.get_registration_address(person),
            'contacts': self.get_contacts(person),
            'actualAddress': self.get_actual_address(person)
        }

    def get_principal_info(self, request):
        profile = request.client.profile
        commercial_contracts = self.get_commercial_contracts(request)
        return {
            'accountant': self.get_accountant(request),
            'addresses': [
                self.get_legal_address_principal(request),
                self.get_actual_address_principal(request),
                self.get_postal_address_principal(request),
            ],
            'bankAccounts': self.get_bank_accounts(request),
            'commercialContracts': commercial_contracts,
            'commercialContractsNumber': len(commercial_contracts) if isinstance(
                commercial_contracts,
                list) else 0,
            'companyBeneficiaries': self.beneficiars(request),
            'companyHead': self.get_company_head(request),
            'companyInfo': self.get_company_info(request),
            'companyManagement': self.get_company_management(request),
            'contactPerson': self.get_contact_person(request),
            'founders': {
                'foundersCompanies': self.get_founders_companies(request),
                'foundersPersons': self.get_founders_persons(request),
            },
            'fullName': profile.full_name,
            'inn': profile.reg_inn,
            'kpp': profile.reg_kpp or '0' * 9,
            'ogrn': profile.reg_ogrn,
            'principalBuh': self.get_principal_buh(request),
            'staffInfo': self.get_staff_info(request),
            'principalSigner': self.get_principal_signer(request),
        }

    def get_data_for_send(self, request):
        external_request = self.get_external_request(request)
        status = self.get_need_status(external_request)
        need_profile = True
        need_documents = True
        if not external_request.external_id:
            need_callback_url = True
        else:
            need_callback_url = False
        data = {}
        if need_profile:
            data['principal'] = self.get_principal_info(request)
            data['bankGuarantee'] = self.get_bank_guarantee(request)
            if not external_request.external_id:
                data['orderComments'] = 'Заявка на получение банковской гарантии'
            else:
                message = external_request.request.get_last_message(
                    ['client', 'agent', 'general_agent'])
                if message:
                    data['orderComments'] = message
        if need_documents:
            data['documents'] = self.get_documents(request)
        if need_callback_url:
            data['callbackUrl'] = self.async_server
        decision_code = None
        if external_request.external_id:
            if 'SEND_TO_BANK' not in list(
                map(lambda x: x['code'], status.get('decisionOptions') or [])
            ):
                decision_code = 'ACCEPT'
            else:
                decision_code = 'SEND_TO_BANK'
        data['decision'] = {'resultCode': decision_code}
        return data

    def get_headers(self):
        return {
            'cache-control': 'no-cache',
            'Content-Type': 'application/json',
            'x-api-login': self.x_api_login,
            'x-api-password': self.x_api_password,
        }

    def convert_phone(self, value):
        cleared_phone = re.sub(r'(\+7|[ ()-])', '', value)
        if len(cleared_phone) == 11:
            cleared_phone = cleared_phone[1:]
        if len(cleared_phone) == 10:
            return cleared_phone

    def init_request(self, request):
        self.create_request(request)

    def get_limit_status_data(self, limit_request):
        result = self.get_data_from_bank('/order/' + limit_request.request_id)
        return result

    @staticmethod
    def in_process_action(external_request):
        from bank_guarantee.actions import AskOnRequestAction, \
            InProcessAction
        user = external_request.request.client.user_set.first()
        author = external_request.request.bank.user_set.first()
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

    def _update_status(self, external_request, data):  # noqa: MC0001
        """
        :param data:
        :param ExternalRequest external_request:
        """
        if external_request.status in ['Executed']:
            return

        status = data.get('orderStatus', '')

        if external_request.request.status.code not in [
            RequestStatus.CODE_OFFER_REJECTED,
            RequestStatus.CODE_REQUEST_BACK,
        ]:
            # фиксирование лимитных заявок
            if data.get('uncompletedLimitOrderId'):
                limit_request, created = LimitRequest.objects.get_or_create(
                    request_id=data['uncompletedLimitOrderId'],
                    client=external_request.request.client,
                    bank=self.bank
                )
                if created:
                    limit_status = self.get_limit_status_data(limit_request)
                    limit_request.status_data = ujson.dumps(limit_status)
                    limit_request.request_number = limit_status.get('orderNumber')

            # установка стандарнтной комиссии
            if (data.get(
                'commission'
            ) and external_request.get_other_data_for_key('default_commission') is None):
                external_request.set_other_data_for_key(
                    'default_commission', data.get('commission'))

            # установка номер заявки
            if data.get('orderNumber') != external_request.request.request_number_in_bank:
                request = external_request.request
                request.request_number_in_bank = data.get('orderNumber')
                request.save()

            # обновления статуса
            self.generate_print_forms(data, external_request)
            if not external_request.get_other_data_for_key('wait_bank'):
                self.in_process_action(external_request)
                for action in ACTION_LIST:
                    if action.check_status(data):
                        action(external_request.request, data=data, adapter=self).run()

            # сохранения статуса
            external_request.status = status
            external_request.save()

        elif status != 'RejectedByBank':
            # отклонения заявки
            self.reject_request(external_request.request)

    @property
    def offer_map(self):
        return {
            'doc_guaranteeLot': 1,
            'doc_bill': 3,
            'doc_bgScanLot': 2,
        }

    def checK_accept_offer(self, request):
        return request.requestdocument_set.filter(
            print_form__filename='doc_orderParamsGeneratedLot',
            print_form__type=PrintForm.TYPE_ABSOLUT_GENERATOR,
        ).exists()

    @push_error()
    def before_accept_offer(self, request):
        external_request = self.get_external_request(request)
        if external_request.external_id:
            if not self.checK_accept_offer(request):
                external_request.set_other_data_for_key('wait_bank', True)
                self.send_data_in_bank(
                    '/order/' + external_request.external_id,
                    {
                        "decision": {
                            "resultCode": "ACCEPT",
                        }
                    },
                    method='PUT'
                )
                for _ in range(10):
                    request.refresh_from_db()
                    if self.checK_accept_offer(request):
                        external_request.set_other_data_for_key('wait_bank', False)
                        return {'result': True}
                    time.sleep(2)
                external_request.set_other_data_for_key('wait_bank', False)
                return {
                    'result': False,
                    'errors': 'Получены не все документы от банка, обратитесь в '
                              'Тех.поддержку'
                }
        return {'result': True}

    def change_project_bg(self, request, file=None, message=None):
        if request.status.code != RequestStatus.CODE_OFFER_SENT:
            return 'Заявка должна быть в статусе %s' % RequestStatus.CODE_OFFER_SENT
        external_request = self.get_external_request(request)
        data = {
            'documents': [
                {
                    'type': 'doc_guaranteeLot',
                    'files': self.pack_files([file.id])
                }
            ],
            "decision": {
                "resultCode": "REWORK",
                'comment': message or ''
            }
        }
        return self.send_data_in_bank(
            '/order/' + external_request.external_id,
            data,
            method='PUT'
        )

    @push_error()
    def change_commission(self, request, commission, reason=None, files=None):
        external_request = self.get_external_request(request)
        data = {
            'commission': {
                'amount': commission,
                'changeReason': reason,
            }
        }
        if files:
            data['documents'] = [{
                'files': self.pack_files(files),
                'type': 'doc_comDecreaseReason',
            }]
        return self.send_data_in_bank(
            '/commission/' + external_request.external_id,
            data,
            method='POST'
        )

    def get_limit_for_client(self, client):
        response = self.get_data_from_bank(
            '/limit',
            params={
                'INN': client.profile.reg_inn,
                'OGRN': client.profile.reg_ogrn
            }
        )
        return response[0] if len(response) else None

    @push_error()
    def update_limit_status(self, limit_request: LimitRequest, data: dict):
        if data.get('orderStatus') == 'Executed':
            requests = limit_request.client.request_set.filter(
                bank=self.bank,
                external_request__external_id__isnull=False
            ).exclude(status__code__in=[
                RequestStatus.CODE_OFFER_REJECTED,
                RequestStatus.CODE_REQUEST_BACK,
                RequestStatus.CODE_ASSIGNED_TO_ANOTHER_AGENT,
                RequestStatus.CODE_REQUEST_DENY,
                RequestStatus.CODE_FINISHED
            ])
            limit_data = self.get_limit_for_client(limit_request.client)
            if limit_data:
                for request in requests:
                    self.push_message_limit(request, limit_data)
        else:
            if data.get('orderStatus') == 'Failed':
                push_rocket_chat(
                    'bank: %s ИНН клиента %s\n%s' % (
                        limit_request.bank.code,
                        limit_request.client.profile.reg_inn,
                        str(data)
                    )
                )

            limit_request.status_data = ujson.dumps(data)

    def push_message_limit(self, request, data):
        constraints = []
        if data is None:
            return
        if data.get('constraints'):
            constraints = data.pop('constraints')
        limit_request = LimitRequest.objects.filter(
            bank=self.bank,
            client=request.client
        ).first()
        if (limit_request and
            ujson.loads(
                limit_request.status_data
            ).get('orderId') != 'EXECUTED'):
            message = 'Лимит в процессе установки\n' \
                      'Текущий лимит:\n'
        else:
            message = 'Лимит установлен\n'
        message += 'Общая сумма установленного лимита - %s руб.\n' \
                   'Заявки на банковскую гарантию на сумму - %s руб. \n' \
                   'Действующие банковские гарантии на сумму - %s ' \
                   'руб. \n' \
                   'Свободный лимит, сумма - %s' % (
                       format_decimal(data['totalAmount']),
                       format_decimal(data['frozenAmount']),
                       format_decimal(data['utilizedAmount']),
                       format_decimal(data['freeAmount'])
                   )
        if len(constraints) > 0:
            message += '\n'
            message += 'Ограничения: '
            for constraint in constraints:
                max_sum = 'без ограничения по сумме гарантии'
                if constraint['limitAmount'] > constraint['maxOrderAmount']:
                    max_sum = 'с суммой не более %s руб.' % format_decimal(
                        constraint['maxOrderAmount']
                    )
                options = 'без ограничения НМЦ и Аванса'
                if constraint['startMaxOrderAmount'] and constraint['prepaidPercent']:
                    options = 'с ограничением НМЦ не более %s руб. и ' \
                              'Аванса не более %i%%' % (
                                  format_decimal(constraint['startMaxOrderAmount']),
                                  int(constraint['prepaidPercent'] * 100))
                elif constraint['startMaxOrderAmount']:
                    options = 'с ограничением НМЦ не более %s руб. ' % (
                        format_decimal(constraint['startMaxOrderAmount'])
                    )
                elif constraint['prepaidPercent']:
                    options = 'с ограничением Аванса не более %i%%' % (int(
                        constraint['prepaidPercent'] * 100)
                    )
                message += '\n*\tГарантии %s, %s могут быть предоствлены на ' \
                           'общую сумму не более %s рублей (свободный ' \
                           'лимит для ограничения - %s руб.)' % (
                               max_sum,
                               options,
                               format_decimal(constraint['limitAmount']),
                               format_decimal(constraint['freelimitAmount'])
                           )
        self.push_message(request, message)


ACTION_LIST = []


def add_action_list(cls):
    ACTION_LIST.append(cls)
    return cls


class ActionForResponse:
    params = {}

    @classmethod
    def check_status(cls, data):
        for key, value in cls.params.items():
            if data.get(key) != value:
                return False
        return True

    def __init__(self, request, data, adapter: SendRequest):
        self.request = request
        self.data = data
        self.adapter = adapter

    @cached_property
    def external_request(self):
        return self.request.externalrequest_set.filter(
            bank__code=BankCode.CODE_ABSOLUT).first()

    def run(self):
        pass


@add_action_list
class PrepareForSignDocs(ActionForResponse):
    params = {"taskName": "Подписать документы"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def run(self):
        # перевод статуса
        if self.request.get_documents_for_sign_by_client().exclude(
            sign__author=self.request.client
        ).exists():
            self.request.is_signed = False
            logger.info("Перевод в статус на подписании у клиента %s" % generate_log_tags(
                request=self.request
            ))
            self.request.status = RequestStatus.objects.get(
                code=RequestStatus.CODE_CLIENT_SIGN)
            self.request.save()
            discuss = self.request.discusses.filter(
                bank=self.request.bank,
                agent=self.request.agent
            ).first()
            user = self.adapter.bank.get_first_user()
            if discuss and discuss.can_write(user):
                url = ReferalSign.generate_url(self.request.id, 'sign')
                discuss.add_message(
                    author=user,
                    message='Добрый день!\n'
                            'Просьба подписать заявку по ссылке '
                            '<a href="{url}">{url}</a> '
                            'ссылка действительна в течении 5 дней,'
                            ' после истечения срока действия ссылки,'
                            ' заявка будет автоматически отклонена'.format(url=url)
                )
            self.request.log(
                action='Заявка возвращена на подпись клиенту',
                user=user,
            )
        else:
            self.adapter.change_request(self.request, self.external_request)


@add_action_list
class ApproveCommission(ActionForResponse):
    params = {"taskName": "Согласовать параметры БГ"}

    def create_offer(self):
        action = CreateOfferAction(
            request=self.request,
            user=self.adapter.bank.user_set.first(),
        )
        total = float(self.data['commission'])
        default = float(
            self.external_request.get_other_data_for_key('default_commission')
        )
        delta = total - default
        action.execute(params={
            'amount': self.request.required_amount,
            'commission_bank': total,
            'default_commission_bank': default,
            'default_commission_bank_percent': round(default * 365 *
                                                     100 / self.request.interval / float(
                self.request.required_amount
            ),
                                                     2),
            'delta_commission_bank': delta,
            'commission_bank_percent': round(total * 365 *
                                             100 / self.request.interval / float(
                self.request.required_amount
            ),
                                             2),
            'offer_active_end_date': self.request.final_date.strftime('%d.%m.%Y'),
            'contract_date_end': self.request.interval_to.strftime('%d.%m.%Y'),
            'not_documents': True,
        })

    def set_status(self, status):
        try:
            self.request.set_status(status)
            self.request.refresh_from_db()
        except StatusNotFoundException:
            pass

    def run(self):
        self.adapter.change_request(self.request, self.external_request)


@add_action_list
class AcceptOffer(PrepareForSignDocs):
    params = {"taskName": "Согласовать текст и форму гарантии"}

    def create_offer(self):
        action = CreateOfferAction(
            request=self.request,
            user=self.adapter.bank.user_set.first(),
        )
        total = float(self.data['commission'])
        default = float(
            self.external_request.get_other_data_for_key('default_commission')
        )
        delta = total - default
        action.execute(params={
            'amount': self.request.required_amount,
            'commission_bank': total,
            'default_commission_bank': default,
            'default_commission_bank_percent': round(default * 365 *
                                                     100 / self.request.interval / float(
                self.request.required_amount
            ),
                                                     2),
            'delta_commission_bank': delta,
            'commission_bank_percent': round(total * 365 *
                                             100 / self.request.interval / float(
                self.request.required_amount
            ),
                                             2),
            'offer_active_end_date': self.request.final_date.strftime('%d.%m.%Y'),
            'contract_date_end': self.request.interval_to.strftime('%d.%m.%Y'),
            'not_documents': True,
        })

    def set_status(self, status):
        try:
            self.request.set_status(status)
            self.request.refresh_from_db()
        except StatusNotFoundException:
            pass

    def run(self):
        self.set_status(RequestStatus.CODE_IN_BANK)
        self.set_status(RequestStatus.CODE_REQUEST_CONFIRMED)
        self.request.refresh_from_db()
        self.create_offer()
        self.adapter.create_offer_doc(
            self.external_request,
            self.adapter.get_offer_docs_for_generate(self.data)
        )
        # обновления статуса
        self.request.update_signed(self.request.client.user_set.first())
        # перевод статуса
        send_offer = SendOfferAction(self.request, self.request.bank.user_set.first())
        send_offer.execute()


@add_action_list
class TestPaidOffer(ActionForResponse):
    params = {'taskDefinitionKey': 'UserTaskInitiatorPayCommission'}

    def run(self):
        from settings.settings import DEBUG
        if DEBUG:
            self.adapter.change_request(self.request, self.external_request)


@add_action_list
class Finished(ActionForResponse):
    params = {"statusDescription": "БГ выдана"}

    def run(self):
        self.request.status = RequestStatus.objects.get(
            code=RequestStatus.CODE_OFFER_PREPARE
        )
        self.request.save()
        action = RequestFinishedAction(
            request=self.request,
            user=self.adapter.bank.user_set.first(),
        )
        data = {
            'contract_number': self.data.get('orderNumber', 'test_number'),
            'contract_date': timezone.now().strftime('%d.%m.%Y'),
            'not_documents': True
        }
        self.adapter.create_offer_doc(
            self.external_request,
            self.adapter.get_offer_docs_for_generate(self.data)
        )
        try:
            action.execute(data)
        except Exception as error:
            RequestLogger.log(self.request, str(error))


@add_action_list
class SentRequest(ActionForResponse):
    params = {"taskName": "Сообщить доп сведения / приложить документы"}

    def run(self):
        self.request.status = RequestStatus.objects.get(code=RequestStatus.CODE_IN_BANK)
        self.request.save()
        action = SendRequestAction(
            request=self.request,
            user=self.adapter.bank.user_set.first(),
        )
        errors = self.adapter.get_errors(self.request, self.data)
        if not len(errors):
            errors.append(self.data.get('bankComment'))
        action.execute(params={'request_text': '\n'.join(errors)})


@add_action_list
class RejectedByBank(ActionForResponse):
    params = {'orderStatus': 'RejectedByBank'}

    def run(self):
        reason = self.data.get(
            'bankComment'
        ) or self.data.get('statusDescription')
        reason = reason or 'Отказ'
        if 'Дубликат заявки' in reason:
            reason = 'reject_assigned_by_another_agent'
        action = RejectAction(
            request=self.request,
            user=self.adapter.bank.user_set.first()
        )
        if action.validate_access():
            action.execute(params={'reason': reason})


@add_action_list
class SentRequestFromVerificator(SentRequest):
    params = {'taskDefinitionKey': 'UserTaskInitiatorInput'}


@add_action_list
class ApproveBG(ActionForResponse):
    params = {'statusDescription': 'Согласование выдачи БГ'}

    def run(self):
        data = self.adapter.get_limit_for_client(self.request.client)
        if data:
            self.adapter.push_message_limit(
                self.request,
                data
            )


@add_action_list
class OfferPaid(ActionForResponse):
    params = {'statusDescription': 'Выпуск БГ'}

    def run(self):
        action = OfferPaidAction(self.request, self.adapter.bank.user_set.first())
        if action.validate_access():
            action.execute()
