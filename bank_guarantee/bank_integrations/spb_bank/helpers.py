import datetime

from django.utils import timezone
from django.utils.functional import cached_property
from sentry_sdk import capture_exception

from bank_guarantee.bank_integrations.spb_bank.client_rating_calculator import (
    QuarterData, AnotherCompanyData, ClientRatingCalculator
)
from clients.models import Client, logging
from external_api.blacklist_api import BlackListChecker
from external_api.zachestniybiznes_api import ZaChestnyiBiznesApi
from external_api.parsers_tenderhelp import ParsersApi
from dateutil.parser import parse

from utils.helpers import is_individual_entrepreneur_for_inn

logger = logging.getLogger('django')


def filter_contract(contract, date_from):
    date = contract.get('publishDate', contract.get('signDate'))

    if date:
        date = parse(date).date()
        return date >= date_from
    return False


class SPBContractsInfo:
    def __init__(self, request):
        self.request = request
        self.profile = request.client.profile
        self.api = ParsersApi()

    @cached_property
    def contracts(self):
        try:
            return self.api.zakupki.get_contracts(inn=self.profile.reg_inn)
        except Exception as e:
            capture_exception(e)
            return {
                '44fz': [],
                '223fz': []
            }

    @cached_property
    def last_3_year_contracts(self):
        fz_44 = self.api.zakupki.filter_last_years(
            contracts=self.contracts['44fz'], years=3
        )
        fz_223 = self.api.zakupki.filter_last_years(
            contracts=self.contracts['223fz'], years=3
        )
        return fz_44 + fz_223

    @cached_property
    def finished_last_3_year_contracts(self):
        return list(
            filter(
                lambda x: x.status == 'EC',
                self.last_3_year_contracts
            )
        )

    @cached_property
    def similar_contracts(self):
        contracts = list(filter(
            lambda x: x.price >= float(self.request.tender.price),
            self.last_3_year_contracts
        ))
        return contracts

    @cached_property
    def number_of_similar_contracts(self):
        return len(self.similar_contracts)


def get_number_changed_beneficiary_last_year(inn, now=None):
    if not now:
        now = datetime.datetime.now()
    count = 0
    if is_individual_entrepreneur_for_inn(inn):
        return count
    api = ZaChestnyiBiznesApi()
    data = api.method('card', inn)
    if data.get('body', {}).get('total'):
        data = data['body']['docs'][0]
        reg_state_data = datetime.datetime.strptime(
            data.get('ДатаОГРН', data.get('ДатаОГРНИП')), '%d.%m.%Y'
        ).date()
        persons = data['СвУчредит'].get('all', []) if isinstance(
            data['СвУчредит'],
            dict
        ) else data['СвУчредит'] or []
        for person in persons:
            try:
                person_start = datetime.datetime.strptime(
                    person['date'], '%Y-%m-%d'
                ).date()
            except ValueError:
                person_start = datetime.datetime.strptime(
                    person['date'], '%d.%m.%Y'
                ).date()

            if person_start > reg_state_data and (now.date() - person_start).days < 365:
                count += 1
    return count


def is_disqualified_person(inn):
    try:
        api = ParsersApi()
        return api.nalogRu.has_disqualified_person(inn)
    except Exception as error:
        logger.error(str(error))
        return None


def is_bankrupt(inn):
    # TODO Реализовать
    return None


def is_rnp(inn):
    return BlackListChecker().in_black_list(inn)


def get_principal_has_share_in_stop_factors_companies(inn, ogrn):
    try:
        api = ZaChestnyiBiznesApi()
        data = api.search('est_%s %s' % (ogrn, inn))
    except Exception:
        return []

    inns = []
    check_methods = [
        is_bankrupt,
        is_disqualified_person,
        is_rnp
    ]
    if data['body']['total']:
        data = data['body']['docs']

        for item in data:
            inns.append(item['ИНН'])

        for index, inn in enumerate(inns):
            if not any([check_method(inn) for check_method in check_methods]):
                del inns[index]
    return inns


def check_has_large_debt(inn):
    return False


def get_quarter_data_from_quarter(quarter):
    return QuarterData(
        **{'v%i' % code: quarter.get_value(code) * 1000 for code in
           [1100, 1200, 1300, 1400, 1410, 1500, 1510, 1530, 1600, 2110, 2300, 2320, 2330]}
    )


def get_another_company_data_from_client(client):
    return AnotherCompanyData(
        number_changed_beneficiary_last_year=int(
            get_number_changed_beneficiary_last_year(client.profile.reg_inn)
        ),
        principal_has_share_in_stop_factors_companies=get_principal_has_share_in_stop_factors_companies(  # noqa
            client.profile.reg_inn,
            client.profile.reg_ogrn,
        ),
        has_large_debt=check_has_large_debt(check_has_large_debt(client.profile.reg_inn))
    )


def get_company_age_months(reg_state_date):
    now = timezone.now().date()
    try:
        return int((now - reg_state_date).days / 30.5)
    except ValueError:
        return 0


def get_client_rating_calculator(request, analog_period=False):
    helper = SPBContractsInfo(request)
    tender_counts_total = list(filter(
        lambda x: x.status == 'EC',
        helper.last_3_year_contracts
    ))

    number_of_similar_contracts = list(
        filter(lambda x: x.status == 'EC', helper.similar_contracts))
    client: Client = request.client
    if not analog_period:

        year_quarter = client.accounting_report.get_year_quarter()
        quarter = client.accounting_report.get_last_closed_quarter()
    else:
        year_quarter = client.accounting_report.get_year_quarter()
        quarter = client.accounting_report.get_year_quarter()

    reg_state_date = request.client.profile.reg_state_date
    return ClientRatingCalculator(
            tender_start_price=request.tender.price,
            company_age_months=get_company_age_months(reg_state_date),
            tender_counts_total=len(tender_counts_total),
            number_of_similar_contracts=len(number_of_similar_contracts),
            year_data=get_quarter_data_from_quarter(year_quarter),
            last_quarter_data=get_quarter_data_from_quarter(quarter),
            another_company_data=get_another_company_data_from_client(request.client)
        )
