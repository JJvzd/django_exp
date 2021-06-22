import datetime
import json

from dateutil import parser
from django.conf import settings

from bank_guarantee.models import (
    ExternalRequest, ContractType, DocumentLinkToPerson, Offer
)
from base_request.helpers import BeforeSendToBankResult
from bank_guarantee.bank_integrations.api.farzoom.base import FarzoomSendRequest
from cabinet.constants.constants import FederalLaw, Target, OrganizationForm
from cabinet.models import EgrulData
from settings.configs.banks import BankCode


class SendRequest(FarzoomSendRequest):
    bank_code = BankCode.CODE_EAST
    enabled = True

    def __init__(self, *args, **kwargs):
        self.enabled = self.bank.settings.send_via_integration
        self.production_endpoint = settings.EAST_ENDPOINT
        self.east_api_key = settings.EAST_KEY
        self.east_token = settings.EAST_TOKEN
        super(SendRequest, self).__init__(*args, **kwargs)

    def integration_enable(self):
        return self.enabled

    def get_headers(self):
        return {
            'cache-control': 'no-cache',
            'Content-Type': 'application/json',
            'postman-token': self.east_token,
            'x-api-key': self.east_api_key
        }

    def get_documents_types(self):
        response = self.get_data_from_bank('/doc/types')
        return response

    def send_request(self, request):
        if self.enabled:
            return super().send_request(request)
        else:
            return BeforeSendToBankResult(result=True)

    def change_request(self, request, external_request):
        """
        Изменения уже отправленной заявки в банк
        :param Request || LoanRequest request:
        :param external_request:
        :return: BeforeSendToBankResult
        """

        response = self.send_data_in_bank(
            '/order/%i' % external_request.id,
            self.get_data_for_send(request),
            method='PUT'
        )
        if not response:
            if self.write_to_log:
                pass
            return BeforeSendToBankResult(True)
        else:
            if self.write_to_log:
                pass
            return BeforeSendToBankResult(False, reason='Банк отклонил заявку')

    def get_current_status(self, request):
        external_request = ExternalRequest.get_request_data(request, self.bank)

        if self.bank.settins.update_via_integration and external_request:
            response = self.get_data_from_bank(
                '/order/%i' % external_request.id
            )
            data = json.loads(external_request.other_data)
            events = data.get('orderStatus', [])

            need_add_event = True
            if len(events) > 0:
                event = events[-1]
                if event != response['comments']:
                    need_add_event = True
            else:
                need_add_event = True

            if need_add_event:
                data.update({'events': response['comments']})
                data.update({'status': response['orderStatus']})
                external_request.other_data = json.dumps(data)
                external_request.save()
                return response

        return None

    @staticmethod
    def period_formatted_date(period):

        months = {
            4: 12,
            1: 3,
            2: 6,
            3: 9,
        }
        year = period.year
        date = datetime.datetime(year, months[period.quarter], 1)

        return date.strftime('%Y-%m')

    def get_principalBuh(self, request):
        """
        Возвращает данные бухгалтерской отчётности
        :param request:
        :return:
        """
        quarters = request.client.accounting_report.get_quarters()
        last_period = quarters[0]

        periods = {}
        codes = [
            1100, 1110, 1120, 1130, 1140, 1150, 1160, 1170, 1180, 1190, 1200, 1210,
            1220, 1230, 1240, 1250, 1260, 1300, 1310, 1320, 1340, 1350, 1360, 1370,
            1400, 1410, 1420, 1430, 1450, 1500, 1510, 1520, 1530, 1540, 1550, 1600,
            1700, 1700, 2100, 2110, 2120, 2200, 2210, 2220, 2300, 2310, 2320, 2330,
            2340, 2350, 2400, 2410, 2430, 2450, 2460, 5640
        ]

        for quarter in quarters:
            data = {}
            for code in codes:
                value = quarter.get_value(code)
                if (1110 <= code <= 1170 or
                        1210 <= code <= 1260 or
                        1340 <= code <= 1360 or
                        1510 <= code <= 1550 or
                        2310 <= code <= 2350 or
                        code in [
                            1190, 1200, 1310, 1400, 1410, 1430, 1450, 1500, 1600, 1700,
                            2110, 2120, 2210, 2410
                        ]
                ):
                    value = abs(value)
                data.update({
                    'b%i' % code: value
                })
            periods.update({
                self.period_formatted_date(quarter): data
            })
        return {
            'latestPeriod': self.period_formatted_date(last_period),
            'periods': periods,
            'taxationType': 'osn' if request.client.profile.is_OSN() else 'usn'
        }

    @staticmethod
    def get_beneficiares(request):

        data = {
            'fullName': request.tender.beneficiary_name,
            'inn': request.tender.beneficiary_inn.strip(),
            'kpp': request.tender.beneficiary_kpp.strip(),
            'ogrn': request.tender.beneficiary_ogrn.strip(),
            'purchaseAmount': request.tender.price,
            'amount': request.tender.suggested_price_amount,
        }

        return data

    @staticmethod
    def get_address(anketa):

        ur_status = 'property' if anketa.ur_address_status else 'rent'
        fact_status = 'property' if anketa.fact_address_status else 'rent'

        return [
            {
                'address': anketa.get_fact_address(),
                'addressOwnType': fact_status,
                'addressType': 'actual',
            },
            {
                'address': anketa.get_ur_address(),
                'addressOwnType': ur_status,
                'addressType': 'legal',
            }
        ]

    @staticmethod
    def get_person_attributes(person):
        citizen = person.citizenship
        citizen_other = ''
        if citizen == 'Россия':
            citizen = 643
        elif citizen == 'Беларусь':
            citizen = 112
        else:
            citizen = 'other'
            citizen_other = person.citizenship

        return {
            'isIpdl': '',  # TODO обатить внимание, убраны поля
            'isIpdlRelative': '',  # TODO обратить внимание, убраны поля
            'citizenship': citizen,
            'otherCitizenship': citizen_other,
        }

    def get_company_head(self, anketa):
        general_director = anketa.general_director
        general_director_passport = general_director.passport
        position = ['Генеральный директор']
        if not general_director.is_booker:
            position.append('бухгалтер')
        return {
            'inn': general_director.fiz_inn,
            'lastName': general_director.last_name,
            'firstName': general_director.first_name,
            'secondName': general_director.middle_name,
            'sex': self.detect_gender(general_director.middle_name),
            'snils': self.format_snils(general_director.snils),
            'nuresident': general_director.resident,
            'nuCurrencyResident': general_director.resident,
            'contacts': [
                {
                    'email': anketa.contact_email,
                    'phone': anketa.contact_phone,
                }
            ],
            'identityDocument': {
                'number': general_director_passport.number,
                'series': general_director_passport.series,
                'identityDocumentType': 'passportRF',
                'issuedDate': self.convert_date(general_director_passport.when_issued),
                'issuingAuthority': general_director_passport.issued_by,
                'issuingAuthorityCode': general_director_passport.issued_code,
                'validTillDate': '',
            },
            'authorizingDoc': general_director.document_gen_dir and (
                    general_director.document_gen_dir.gen_dir_doc_right() or '-'),
            'birthDate': self.convert_date(general_director_passport.date_of_birth),
            'birthPlace': general_director_passport.place_of_birth,
            'relationAttributes': {
                'authorizationStartDate': '',
                'authorizationExpirationDate': '',
            },
            'personAttributes': self.get_person_attributes(general_director),
            'position': ','.join(position),
            'actualAddress': general_director_passport.place_of_registration,
            'registrationAddress': general_director_passport.place_of_registration,
            'accountant': general_director.is_booker,
        }

    def get_accountant(self, anketa):
        accountant = anketa.booker
        accountant_passport = accountant.passport
        return {
            'inn': accountant.fiz_inn,
            'lastName': accountant.last_name,
            'firstName': accountant.first_name,
            'secondName': accountant.middle_name,
            'sex': self.detect_gender(accountant.middle_name),
            'shils': accountant.snils,
            'nuresident': accountant.resident,
            'nuCurrencyResident': accountant.resident,
            'identityDocument': {
                'number': accountant_passport.number,
                'series': accountant_passport.series,
                'identityDocumentType': 'passportRF',
                'issuedDate': self.convert_date(accountant_passport.when_issued),
                'issuingAuthority': accountant_passport.issued_by,
                'issuingAuthorityCode': accountant_passport.issued_code,
                'validTillDate': '',
            },
            'authorizingDoc': accountant.booker_document or '-',
            'birthDate': self.convert_date(accountant_passport.date_of_birth),
            'birthPlace': accountant_passport.place_of_birth,
            'contacts': {
                'email': anketa.contact_email,
                'phone': anketa.contact_phone,
            },
            'relationAttributes': {
                'authorizationStartDate': '',
                'authorizationExpirationDate': '',
            },
            'personAttributes': self.get_person_attributes(accountant),
            'position': 'other',
            'otherPosition': accountant.booker_post,
            'actualAddress': accountant_passport.place_of_registration,
            'registrationAddress': accountant_passport.place_of_registration,
            'companyHead': accountant.is_general_director,
        }

    @staticmethod
    def get_federal_law(request):
        return {
            FederalLaw.LAW_44: '2',
            FederalLaw.LAW_223: '1',
            FederalLaw.LAW_185: '3',
        }.get(request.tender.federal_law, 'commercial')

    def get_data_for_send(self, request):
        anketa = request.client.profile
        guarantee_target = request.targets
        guarantee_type_choices = {
            Target.EXECUTION: '1',
            Target.PARTICIPANT: '2',
            Target.WARRANTY: '3',  # TODO уточнить
            Target.AVANS_RETURN: '4',  # TODO уточнить
        }
        bank_guarantee_type = [guarantee_type_choices[i] for i in guarantee_target]
        warranty = Target.WARRANTY in guarantee_target
        if warranty:
            warranty_duration = (request.warranty_from - request.warranty_to).days
        else:
            warranty_duration = 0
        if request.contract_type == ContractType.STATE:
            contract_type = 'state'
        else:
            contract_type = 'municipal'
        data = {
            'principal': {
                'inn': anketa.reg_inn,
                'ogrn': anketa.reg_ogrn,
                'questionary': {
                    'employeeDebt': False,
                    'taxOverdue': False,
                    'changeOwner2': False,
                    'unpayeDocs': False,
                    'debtToTolDebt25': False,

                    'debOrCredUp25': False,
                    'debOrCredUp100': False,
                    'activeDown25': False,
                    'activeDown75': False,
                },
                'accountant': self.get_accountant(anketa),
                'addresses': self.get_address(anketa),
                'CompanyBeneficiaries': self.pack_beneficiaries(anketa),
                'companyHead': self.get_company_head(anketa),
                'ContactPerson': {
                    'email': anketa.contact_email,
                    'cellPhone': self.convert_phone(anketa.contact_phone),
                },
                'founders': {
                    'foundersCompanies': self.get_foundersCompanies(anketa),
                    'foundersPersons': self.get_foundersPersons(anketa),
                },
                'fullName': anketa.full_name,

                'principalBuh': self.get_principalBuh(request),
                'principalSigner': self.get_company_head(anketa),
                'bankAccounts': self.get_bankAccounts(anketa),
                'liabilities': [],
                'mainCustomers': [],
                'mainProviders': [],
                'staffInfo': {
                    'averageNumber': anketa.number_of_employees,
                    'staffDebts': 100,
                    'wageFund': float(anketa.salary_fund),
                },
            },
            'bankGuarantee': {
                'bankGuaranteeSum': request.tender.price,  # TODO уточнить
                'bankGuaranteeType': bank_guarantee_type,
                'beneficiaries': self.get_beneficiares(request),
                'startDate': self.convert_date(request.interval_from),
                'endDate': self.convert_date(request.interval_to),
                'durationDays': request.interval,
                'contractOfferPrice': request.suggested_price_amount,
                'federalLaw': self.get_federal_law(request),
                'tenderType': request.tender.placement.name,  # TODO уточнить
                'assessmentProtocolName': '',
                'assessmentProtocolDate': '',
                'assessmentProtocolNumber': '',
                'securityForGuaranteePeriodDays': warranty_duration,
                'guaranteeReceivingWay': 'bankOffice',
                'isCommercial': '',
                'isContractConcluded': Target.EXECUTION not in guarantee_target,
                'isIncludedForfeit': False,
                'isRequiredIndisputableDebiting': request.downpay,
                'isRequiredSecurityForGuaranteePeriod': warranty,
                'lotNumber': '1',
                'marketPlace': 'test',
                'ContractMaxPrice': request.tender.price,
                'prepaymentAmount': request.prepaid_expense_amount,
                'prepaid_expense_amount': request.prepaid_expense_amount > 0,
                'purchaseNumber': request.tender.notification_id,  # TODO уточнить,
                'purchasePublishedDate': self.convert_date(request.tender.publish_date),
                'requiredExecutionDate': self.convert_date(request.tender.tender_date),
                'isPrivateTender': False,  # TODO уточнить
                'subject': request.tender.predmet,
                'tenderContractType': contract_type,
                'url': request.tender.tender_url,
                'tenderSubjectSegmentRefId': self.get_subject_segement(request),
            },
            'documents': [
                {
                    'type': 'doc_finReport',
                    'files': self.pack_files(
                        request, [73, 48, 24, 129]
                    ) + self.pack_print_form(request, 3),
                },
                {
                    'type': 'doc_otherClientDocs',
                    'files': self.pack_files(
                        request, [77, 18, 139, 62]
                    ) + self.pack_print_form(request, 2),
                },
                {
                    'type': 'doc_Certificate1',
                    'files': self.pack_files(request, [75]),
                },
                {
                    'type': 'doc_LeaseContract1',
                    'files': self.pack_files(request, [75])
                },
                {
                    'type': 'doc_AcceptanceProtocol1',
                    'files': self.pack_files(request, [75])
                },
                {
                    'type': 'doc_passportScan',
                    'files': self.pack_files(request, [4, 63, 22])
                },
            ],
            'orderComments': 'Заявка на получение банковской гарантии',
        }
        organization_form = request.client.profile.organization_form
        allowed_org_forms = [
            OrganizationForm.TYPE_OAO, OrganizationForm.TYPE_AO,
            OrganizationForm.TYPE_PAO, OrganizationForm.TYPE_ZAO
        ]
        if request.client.is_organization and organization_form in allowed_org_forms:
            data['documents'].append({
                'type': 'doc_ExtractRegistry',
                'files': self.pack_files(request.request, [19])
            })

            data['documents'].append({
                'type': 'doc_Charter',
                'files': self.pack_files(request, [2])
            })

            data['documents'].append({
                'type': 'doc_Precept',
                'files': self.pack_files(request, [61])
            })

            data['documents'].append({
                'type': 'doc_EmploymentContract',
                'files': self.pack_files(request, [61])
            })

            data['documents'].append({
                'type': 'doc_PowerOfAttorney',
                'files': self.pack_files(request, [61])
            })

            data['documents'].append({
                'type': 'doc_MinutesGeneralMeeting',
                'files': self.pack_files(request, [61])
            })

            if Target.PARTICIPANT not in bank_guarantee_type:  # TODO уточнить
                data['bankGuarantee'].update({
                    'assessmentProtocolName': 'Протокол',
                    'assessmentProtocolDate': self.convert_date(request.protocol_date),
                    'assessmentProtocolNumber': request.protocol_number,
                    'lotNumber': request.protocol_lot_number,
                })

            if request.client.is_organization:
                data['principal'].update({
                    'kpp': anketa.reg_kpp
                })

        return data

    def create_request(self, request):
        response = self.send_data_in_bank(r'/order', self.get_data_for_send(request))
        # TODO логирование по заявке надо?
        external_id = response.get('orderId')
        if external_id:
            ExternalRequest.save_record(
                request,
                self.bank,
                external_id,
                None,
                {}
            )
            if self.write_to_log:
                pass
            return BeforeSendToBankResult(True)
        else:
            if self.write_to_log:
                pass
            external_exception = 'ru.vostbank.api.process.integration.exception.' \
                                 'NonUniqueCompanyException'
            if response.get('exception') == external_exception:
                return BeforeSendToBankResult(
                    False, reason='Заявка закреплена за другим агентом'
                )
            return BeforeSendToBankResult(False, reason='Банк отклонил заявку')

    def get_foundersCompanies(self, anketa):
        data = []
        egrul = EgrulData.get_info(anketa.reg_inn)
        dates = {}
        for company in egrul['section-akcionery_yur']['akcionery_yur']:
            dates.update({
                company['inn_yur']: company['added'].split(' ')[1]
            })

        for company in anketa.persons_entities:
            date = dates.get(company.inn)
            data.append({
                'date': self.convert_date(date),
                'fullName': company.name,
                'inn': company.inn,
                'kpp': company.kpp,
                'ogrn': company.ogrn,
                'ahsrePercent': company.share,
                'shareSum': self.calculate_share_sum(anketa, company.share)
            })
        return data

    def get_foundersPersons(self, anketa):
        egrul = EgrulData.get_info(anketa.reg_inn)
        dates = {}
        for person in egrul['section-akcionery_fiz']['akcionery_fiz']:
            dates.update({
                person['fio'].lower(): person['added'].split(' ')[1]
            })

        data = []
        for person in anketa.persons:
            person_passport = person.passport
            date = dates.get(person.full_name.lower())
            data.append({
                'inn': person.fiz_inn,
                'lastName': person.last_name,
                'firstName': person.first_name,
                'ssecondName': person.middle_name,
                'sex': self.detect_gender(person.middle_name),
                'snils': person.snils,
                'nuresident': person.resident,
                'nuCurrencyResident': person.resident,
                'identityDocument': {
                    'number': person_passport.number,
                    'series': person_passport.series,
                    'identityDocumentType': 'passportRF',
                    'issuedDate': self.convert_date(person.when_issued),
                    'issuingAuthority': person_passport.issued_by,
                    'issuingAuthorityCode': person_passport.issued_code,
                },
                'birthDate': self.convert_date(person_passport.date_of_birth),
                'date': self.convert_date(date),
                'birthPlace': person_passport.place_of_birth,
                'contacts': [],
                'personAttributes': self.get_person_attributes(person),
                'sharePercent': person.share,
                'shareSum': self.calculate_share_sum(anketa, person),
                'actualAddress': person_passport.place_of_registration,
                'registrationAddress': person_passport.place_of_registration,
            })
        return data

    @staticmethod
    def calculate_share_sum(anketa, percent):
        if anketa.authorized_capital_announced and percent:
            return anketa.authorized_capital_announced * percent
        return 0

    def pack_beneficiaries(self, anketa):
        data = []
        for beneficiar in anketa.beneficiars:
            person_passport = beneficiar.passport
            data.append({
                'inn': beneficiar.fiz_inn,
                'lastName': beneficiar.last_name,
                'firstName': beneficiar.first_name,
                'secondName': beneficiar.middle_name,
                'sex': self.detect_gender(beneficiar.middle_name),
                'snils': self.format_snils(beneficiar.sneils),
                'nuresident': beneficiar.resident,
                'nuCurrencyResident': beneficiar.resident,
                'identityDocument': {
                    'number': person_passport.number,
                    'series': person_passport.series,
                    'identityDocumentType': 'passportRF',
                    'issuedDate': self.converte_date(person_passport.when_issued),
                    'issuingAuthority': person_passport.issued_by,
                    'issuingAuthorityCode': person_passport.issued_code,
                },
                'birthDate': self.convert_date(person_passport.date_of_birth),
                'birthPlace': person_passport.place_of_birth,
                'contacts': [],
                'personAttributes': self.get_person_attributes(beneficiar),
                'sharePercent': beneficiar.share,
                'shareSum': self.calculate_share_sum(anketa, beneficiar.share),
                'actualAddress': person_passport.place_of_registration,
                'registrationAddress': person_passport.place_of_registration,
            })

        return data

    @staticmethod
    def get_bankAccounts(anketa):
        data = []
        use_in_documents = True
        for account in anketa.profileaccounts:
            bank_info = {
                'bank': {
                    'bik': account.bank_bik,
                    'corrNumber': account.correspondent_account,
                    'name': account.bank
                },
                'cardFile2': account.has_unpaid_account,
                'number': account.bank_account_number,
                'useInDocuments': use_in_documents
            }
            use_in_documents = False
            data.append(bank_info)

        return data

    @staticmethod
    def detect_gender(middle_name):
        middle_name = middle_name.lower()
        if middle_name.endswith('ич') or middle_name.endswith('лы'):
            return 'М'
        if middle_name.endswith('на') or middle_name.endswith('зы'):
            return 'Ж'
        return 'М'

    @staticmethod
    def format_snils(snils):
        snils = snils.replace('-', '')
        if len(snils) == 11:
            return snils[:3] + '-' + snils[3:6] + '-' + snils[6:9] + '-' + snils[9:]
        return '000-000-000-00'

    @staticmethod
    def convert_phone(phone):
        phone = phone.replace('+7', '').replace('(', '').replace(')', '').replace('-', '')
        if len(phone) != 10:
            return '9000000000'
        return phone

    @staticmethod
    def convert_date(date):
        if isinstance(date, str):
            date = parser.parse(date)
        return date.strftime('%Y-%m-%d')

    def clear_output_data_for_log(self, data):
        for document in data['documents']:
            for file in document['files']:
                file['values'] = '...'

        return data

    @staticmethod
    def pack_print_form(request, print_from_id):
        doc = request.requestdocument_set.filter(print_form__id=print_from_id).first()
        if not doc:
            request.generate_print_forms()
            doc = request.requestdocument_set.filter(print_form__id=print_from_id).first()

        doc_data = {
            'fileName': doc.file.file.filename,
            'mimeType': doc.file.file.mimetype,
            'value': doc.file.file.get_base64,
        }
        return [doc_data, ]

    @staticmethod
    def pack_files(request, docs_ids):
        data = []
        docs = request.requestdocument_set.filter(category__id__in=docs_ids)
        for doc in docs:
            doc_data = {
                'fileName': doc.file.file.filename,
                'mimeType': doc.file.file.mimetype,
                'value': doc.file.file.get_base64,
            }
            if doc.category.id == 63:
                link = DocumentLinkToPerson.get_link(request.id, 63, doc.id)
                if link:
                    doc_data.update({
                        'innFL': link.persons.passport.fiz_inn
                    })
            if doc.category.id == 4:
                doc_data.update({
                    'innFL': request.client.profile.general_director.fiz_inn
                })
            if doc.category.id == 22:
                doc_data.update({
                    'innFL': request.client.profile.booker.fiz_inn,
                })
            data.append(doc_data)
        return data

    @staticmethod
    def get_subject_segement(request):
        if (request.tender.predmet.find('услуга') != -1) or \
                (request.tender.predmet.find('оказания услуг') != -1):
            return 2
        return 1

    def update_status(self, external_request):
        from bank_guarantee.actions import OfferBackAction, RejectAction
        if external_request.status in ['RejectedByBank', 'Executed', 'Failed']:
            return
        data = self.get_data_from_bank('/order/%s' % external_request.external_id)
        status = data.get('orderStatus', '')
        comment = data.get('statusDescription', '')
        bank_comment = data.get('bankComment', '')
        author = self.bank.get_first_user()
        if status != external_request.status:
            if self.write_to_log:
                pass
            external_request.status = status
            external_request.save()
            offer = Offer.objects.filter(
                request__id=external_request.request.id, bank=self.bank
            ).first()

            if status == 'RejectedByBank':
                if offer:
                    OfferBackAction(
                        request=external_request.request, user=author
                    ).execute()
                else:
                    RejectAction(
                        request=external_request.request, user=author
                    ).execute({
                        'reason': '%s %s' % (comment, bank_comment),
                        'force': True
                    })

    def get_request_status_data(self, external_request):
        return self.get_data_from_bank('/order/%s' % external_request.external_id, {})
