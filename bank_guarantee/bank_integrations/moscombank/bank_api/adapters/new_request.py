import re

from accounting_report.fields import QuarterData
from accounting_report.helpers import QuarterParameters
from .common import BaseRequestAdapter
from bank_guarantee.models import ExternalRequest

from bank_guarantee.bank_integrations.moscombank.bank_api.serializers import (
    LoggingMosKomBank, UpdateLoggingMosKomBank,  UserUlMosKomBank, LicenseMosKomBank,
    BankAccountMosKomBank, PersonMosKomBank, RequestMosKomBank, TenderMosKomBank,
    AdvanceGuaranteeMosKomBank, ShortUserUlMosKomBank, EntityFounder,
    AccountantMosKomBank, ChiefMosKomBank,  AddressMosKomBank, RequestContractMosKomBank,
    TenderGuaranteeMosKomBank, QualityGuaranteeMosKomBank
)
from questionnaire.models import LicensesSRO


class NewRequestAdapter(BaseRequestAdapter):

    def __init__(self, request):
        super(NewRequestAdapter, self).__init__(request)
        self.external_request, created = ExternalRequest.objects.get_or_create(
            bank=request.bank, request=request
        )

    @property
    def client(self):
        return self.request.client

    @property
    def profile(self):
        return self.request.client.profile

    @property
    def agent(self):
        return self.request.agent

    def get_client_registration_data(self):
        return LoggingMosKomBank(self.request.client).data

    def get_user_data(self):
        return UpdateLoggingMosKomBank(self.request.client).data

    def get_user_ul_data(self):
        return UserUlMosKomBank(self.request.client.profile).data

    def get_licences_data(self, license_ids):
        return LicenseMosKomBank(
            LicensesSRO.objects.filter(id__in=license_ids),
            many=True,
        ).data

    def get_license_data(self, license):
        return LicenseMosKomBank(license).data

    def get_bank_accounts_data(self, accounts):
        return BankAccountMosKomBank(accounts, many=True).data

    def get_bank_account_data(self, account):
        return BankAccountMosKomBank(account).data

    def get_persons_data(self, persons):
        return PersonMosKomBank(persons, many=True).data

    def get_person_data(self, person):
        return PersonMosKomBank(person).data

    def get_finance(self, actual_period):
        need_quarter = QuarterParameters(
            actual_period['quarters'],
            re.search(r'\d{4}', actual_period['name_reporting_date']).group(0)
        )
        need_year = QuarterParameters(
            4,
            re.search(r'\d{4}', actual_period['name_previous_year ']).group(0)
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
        return RequestMosKomBank(self.request).data

    def get_guarantee_lot_data(self):
        return TenderMosKomBank(self.request).data

    def get_guarantee_advance_data(self):
        return AdvanceGuaranteeMosKomBank(self.request).data

    def get_guarantee_quality_data(self):
        return QualityGuaranteeMosKomBank(self.request).data

    def get_short_user_ul_data(self):
        return ShortUserUlMosKomBank(self.request.client).data

    def get_entity_founders_data(self, entity_founders):
        return EntityFounder(entity_founders, many=True).data

    def get_entity_founder_data(self, entity_founder):
        return EntityFounder(entity_founder).data

    def get_accountant_data(self):
        return AccountantMosKomBank(self.external_request).data

    def get_chief_data(self):
        return ChiefMosKomBank(self.external_request).data

    def get_address_data(self):
        return AddressMosKomBank(self.external_request).data

    def get_guarantee_contract_data(self):
        return RequestContractMosKomBank(self.request).data

    def get_guarantee_tender_data(self):
        return TenderGuaranteeMosKomBank(self.request).data
