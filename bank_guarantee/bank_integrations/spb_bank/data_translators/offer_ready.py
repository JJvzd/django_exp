import base64

from django.utils import timezone

from bank_guarantee.bank_integrations.spb_bank.client_rating_calculator import \
    ClientRatingTranslator
from bank_guarantee.bank_integrations.spb_bank.helpers import get_client_rating_calculator
from bank_guarantee.export_data import ExportRequest
from cabinet.constants.constants import FederalLaw, Target
from utils.helpers import convert_date, get_sex_by_middle_name


class OfferReadyDataTranslator:

    def get_federal_law(self, request):
        federal_law = None
        if request.tender.federal_law == FederalLaw.LAW_44:
            federal_law = 'FZ44'
        if request.tender.federal_law == FederalLaw.LAW_223:
            federal_law = 'FZ223'
        if request.tender.federal_law in [FederalLaw.LAW_185,
                                          FederalLaw.LAW_615]:
            federal_law = 'GR_FZ_185 (615_PP)'
        if not federal_law:
            raise ValueError('Unsupported law')
        return federal_law

    def get_targets(self, request):
        targets = ''
        if Target.EXECUTION in request.targets:
            targets = 'EXEC_CONTRACT'
        if Target.WARRANTY in request.targets:
            targets = 'EXEC_WARANTY'
        if Target.PARTICIPANT in request.targets:
            targets = 'PARTICIPATION'
        if Target.AVANS_RETURN in request.targets:
            targets = 'REFUND'
        return targets

    def encode_archive_to_base64(self, archive) -> str:
        return base64.b64encode(archive.getvalue()).decode('utf-8')

    def get_rating(self, request):
        data = get_client_rating_calculator(
            request=request,
        )
        rating = ClientRatingTranslator.translate(data.calculated_score)
        return rating

    def pack_request_documents_to_archive(self, request):
        helper = ExportRequest()
        mem_zip = helper.export_as_zip(request, request.bank.user_set.first(),
                                       export_separated_signs=False)
        return mem_zip

    def _pack_member(self, person, person_type):
        return {
            'type': person_type,
            'lastName': person.last_name,
            'firstName': person.first_name,
            'secondName': person.middle_name,
            'displayName': person.get_name,
            'sex': 'FEMALE' if get_sex_by_middle_name(
                person.middle_name) == 'F' else 'MALE',
            'birthDate': convert_date(
                person.passport.date_of_birth),
            'birthPlace': person.passport.place_of_registration,
            'inn': person.fiz_inn,
            'identityDocument': {
                'identityDocumentTypeRefId': 'passportRF',
                'issuedDate': convert_date(person.passport.when_issued),
                'issuingAuthority': person.passport.issued_by,
                'subCode': person.passport.issued_code,
                'number': person.passport.number,
                'series': person.passport.series,
            },
            'addresses': [
                {
                    'addressTypeCode': '100000000',
                    'fullAddress': person.passport.place_of_registration
                }
            ]
        }

    def get_members(self, request):
        members = []
        persons = request.client.profile.profilepartnerindividual_set.filter(
            share__gt=1
        ).exclude(is_general_director=True)
        for person in persons:
            members.append(self._pack_member(person, 'principalBeneficiary'))

        general_director = request.client.profile.general_director
        if request.client.is_individual_entrepreneur:
            members.append(self._pack_member(general_director, 'entrepreneur'))
        elif general_director.share > 0:
            members.append(self._pack_member(general_director, 'principalBeneficiary'))
        return members

    def get_management_membership_info(self, request):
        management_membership_info = []
        general_director = request.client.profile.general_director
        if request.client.is_organization:
            management_membership_info.append({
                'membershipType': 'Генеральный директор',
                'members': [
                    {
                        'displayName': general_director.get_name,
                        'position': general_director.gen_dir_post,
                        'share': float(general_director.share),
                        'inn': general_director.fiz_inn,
                        'identityDocument': {
                            'identityDocumentTypeRefId': 'passportRF',
                            'issuedDate': convert_date(
                                general_director.passport.when_issued),
                            'issuingAuthority': general_director.passport.issued_by,
                            'subCode': general_director.passport.issued_code,
                            'number': general_director.passport.number,
                            'series': general_director.passport.series,
                        }
                    }
                ]
            })
            persons = request.client.profile.profilepartnerindividual_set.filter(
                share__gt=1).exclude(is_general_director=True)
            if persons.exists():
                management_membership_info.append({
                    'membershipType': 'Физ-лица учредители',
                    'members': [
                        {
                            'displayName': person.get_name,
                            'inn': person.fiz_inn,
                            'identityDocument': {
                                'identityDocumentTypeRefId': 'passportRF',
                                'issuedDate': convert_date(
                                    person.passport.when_issued),
                                'issuingAuthority': person.passport.issued_by,
                                'subCode': person.passport.issued_code,
                                'number': person.passport.number,
                                'series': person.passport.series,
                            }
                        }
                        for person in persons
                    ]

                })
            companies = request.client.profile.profilepartnerlegalentities_set.all()
            if companies.exists():
                management_membership_info.append({
                    'membershipType': 'Компании-учредители',
                    'members': [
                        {
                            'displayName': company.name,
                            'share': float(company.share),
                            'inn': company.inn,
                        }
                        for company in companies]
                })
        return management_membership_info

    def get_data(self, request):
        rating = self.get_rating(request)
        last_quarter = request.client.accounting_report.get_last_closed_quarter()
        data = {
            'contractNumber': request.offer.contract_number,
            'contractDate': convert_date(request.offer.contract_date),
            'guaranteePurpose': self.get_targets(request),
            'startDate': convert_date(request.interval_from),
            'obligationsStartDate': convert_date(request.interval_from),
            'endDate': convert_date(request.interval_to),
            'commissionAmount': float(request.offer.commission_bank),
            'commissionPercentRate': round(
                float(request.offer.commission_bank) / float(
                    request.offer.amount), 2),
            'decisionProtocolDate': convert_date(request.protocol_date),
            'decisionProtocolNumber': '0',
            'federalLaw': self.get_federal_law(request),
            'contractDocBase64': self.encode_archive_to_base64(
                self.pack_request_documents_to_archive(request)),
            'agentId': 'TH',
            'principalParams': {
                'rating': rating.category,
                'bankAccounts': [
                    {
                        'bankName': account.bank,
                        'bik': account.bank_bik,
                        'number': account.bank_account_number,
                    } for account in
                    request.client.profile.bankaccount_set.all()
                ],
                'relatedPersons': self.get_members(request),
                'valuationDate': timezone.now().strftime('%Y-%m-%d'),
                'netAssetsAmount': last_quarter.get_clear_actives() or 0,
                'netAssetsReportDate': timezone.now().strftime('%Y-%m-%d'),
                'telephone1': request.client.profile.contact_phone,
                'managementMembershipInfo': self.get_management_membership_info(request),
                'licences': [
                    {
                        'date': convert_date(license.date_issue_license),
                        'expiredDate': convert_date(
                            license.date_end_license),
                        'kindOfActivity': license.list_of_activities,
                        'number': license.number_license,
                        'issuer': license.issued_by_license
                    } for license in
                    request.client.profile.licensessro_set.all()
                ] if request.client.profile.has_license_sro else [],

            },

            'amount': float(request.offer.amount),
        }
        return data
