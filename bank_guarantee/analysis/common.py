from sentry_sdk import capture_exception

from bank_guarantee.analysis.schema import (
    ProfessionalConclusionResult, Quarter, QuarterValue, RatingResult, BankGuarantee,
    ContractExperience, ContractsInfo, ContractsByLaw, MaxContractPriceExperience,
    CourtInfo
)
from bank_guarantee.models import Request
from clients.models import Client, Region, BankRating
from external_api.parsers_tenderhelp import ParsersApi

from django.utils import timezone
from external_api.zachestniybiznes_api import ZaChestnyiBiznesApi
from external_api.rusprofile_api import RusProfile


def fssp_info(ogrn):
    helper = ZaChestnyiBiznesApi()
    response = helper.method('fssp', ogrn)
    if response['status'] != '200':
        return 'Не найдено'
    else:
        return 'Найдено'


def court_arbitration(inn):
    api = RusProfile()
    data_not_finished = api.get_court_arbitration(
        inn=inn,
        common_type=1,
        level='not_finished',
    )
    data_finished = api.get_court_arbitration(
        inn=inn,
        common_type=1,
        level='finished',
    )
    total_sum_not_finished = sum(
        [float(i['sum'].replace(',', '.'))
            for i in data_not_finished if i and i.get('sum')]
    )
    total_sum_finished = sum(
        [float(i['sum'].replace(',', '.')) for i in data_finished if i and i.get('sum')]
    )
    return CourtInfo(
        total_sum_not_finished=total_sum_not_finished,
        total_sum_finished=total_sum_finished,
        data_not_finished=data_not_finished,
        data_finished=data_finished
    )


class ProfessionalConclusionGenerator:

    @classmethod
    def get_contracts_statistic(cls, client: Client, starting_price: float):
        api = ParsersApi()
        try:
            contracts = api.zakupki.get_contracts(inn=client.inn)
        except Exception as e:
            capture_exception(e)
            return None

        today = timezone.now()
        for year in range(today.year, today.year - 5, -1):
            pass

        count_wins = len(contracts['223fz']) + len(contracts['44fz'])
        years = range(today.year, today.year - 5, -1)
        periods = []
        for year in years:
            periods.append({
                'year': year,
                'fz44_start': api.zakupki.filter_by_year(
                    contracts=contracts['44fz'], year=year
                ),
                'fz44_end': api.zakupki.filter_by_year(
                    contracts=api.zakupki.filter_by_status(contracts['44fz'], 'EC'),
                    year=year, field='end_date'
                ),
                'fz223_start': api.zakupki.filter_by_year(
                    contracts=contracts['223fz'], year=year
                ),
                'fz223_end': api.zakupki.filter_by_year(
                    contracts=api.zakupki.filter_by_status(contracts['223fz'], 'EC'),
                    year=year, field='end_date'
                ),
            })
        periods.append({
            'year': 'Последние 3 года',
            'fz44_start': api.zakupki.filter_last_years(
                contracts=contracts['44fz'], years=3
            ),
            'fz44_end': api.zakupki.filter_last_years(
                contracts=api.zakupki.filter_by_status(contracts['44fz'], 'EC'),
                years=3, field='end_date'
            ),
            'fz223_start': api.zakupki.filter_last_years(
                contracts=contracts['223fz'], years=3
            ),
            'fz223_end': api.zakupki.filter_last_years(
                contracts=api.zakupki.filter_by_status(contracts['223fz'], 'EC'),
                years=3, field='end_date'
            ),
        })
        periods.append({
            'year': 'Последние 2 года',
            'fz44_start': api.zakupki.filter_last_years(
                contracts=contracts['44fz'], years=2
            ),
            'fz44_end': api.zakupki.filter_last_years(
                contracts=api.zakupki.filter_by_status(contracts['44fz'], 'EC'),
                years=2, field='end_date'
            ),
            'fz223_start': api.zakupki.filter_last_years(
                contracts=contracts['223fz'], years=2
            ),
            'fz223_end': api.zakupki.filter_last_years(
                contracts=api.zakupki.filter_by_status(contracts['223fz'], 'EC'),
                years=2, field='end_date'
            ),
        })
        percents = [30, 50, 70]
        return ContractExperience(
            count_participant_in_contracts=count_wins,
            count_win_in_contracts=count_wins,
            statistic=[
                ContractsInfo(
                    period=str(period['year']),
                    law_44fz=ContractsByLaw(
                        sum_created=api.zakupki.sum_contracts(period['fz44_start']),
                        count_created=len(period['fz44_start']),
                        sum_finished=api.zakupki.sum_contracts(period['fz44_end']),
                        count_finished=len(period['fz44_end']),
                    ),
                    law_223fz=ContractsByLaw(
                        sum_created=api.zakupki.sum_contracts(period['fz223_start']),
                        count_created=len(period['fz223_start']),
                        sum_finished=api.zakupki.sum_contracts(period['fz223_end']),
                        count_finished=len(period['fz223_end']),
                    ),
                )
                for period in periods
            ],
            max_contract_price_experience=[
                MaxContractPriceExperience(
                    percent=percent,
                    count=api.zakupki.max_contract_price_experience(
                        contracts['223fz'] + contracts['44fz'],percent, starting_price
                    ),
                )
                for percent in percents
            ],
        )

    @classmethod
    def get_data(cls, client: Client,
                 request: Request = None) -> ProfessionalConclusionResult:
        if request:
            assert client == request.client
        else:
            request = client.request_set.last()
        last_quarter = client.accounting_report.get_last_closed_quarter()
        year_quarter = client.accounting_report.get_year_quarter()
        codes = [1300, 1310, 1370, 1400, 1500, 1530, 1600, 2110, 2400, 2410]

        rating = BankRating.get_default_rating(request=request)

        in_work_bank_guarantee = Request.objects.filter(
            client=client,
            offer__contract_date_end__gt=timezone.now()
        )
        finished_bank_guarantee = Request.objects.filter(
            client=client,
            offer__contract_date_end__lte=timezone.now()
        )
        contract_interval = 0
        if request.term_of_work_from and request.term_of_work_to:
            contract_interval = (request.term_of_work_to - request.term_of_work_from).days
        fssp = fssp_info(client.ogrn)
        try:
            court = court_arbitration(client.inn)
        except Exception as e:
            capture_exception(e)
            court = None
        return ProfessionalConclusionResult(
            company_name=client.full_name,
            company_inn=client.inn,
            company_region=client.region,

            beneficiary_region=Region.get_region(
                inn=request.tender.beneficiary_inn,
                kpp=request.tender.beneficiary_kpp,
            ),
            federal_law=request.tender.get_federal_law_display(),
            required_amount=float(request.required_amount),
            suggested_price=float(request.suggested_price_amount),
            price=float(request.tender.price),
            interval=request.interval,
            last_quarter=Quarter(
                period=last_quarter.get_label(),
                values=[QuarterValue(
                    code=code,
                    value=last_quarter.get_value(code)
                ) for code in codes]
            ),
            year_quarter=Quarter(
                period=year_quarter.get_label(),
                values=[QuarterValue(
                    code=code,
                    value=year_quarter.get_value(code)
                ) for code in codes]
            ),
            rating=RatingResult(
                created=rating.created,
                data=rating.data,
                score=rating.score,
                rating=rating.rating,
                risk_level=rating.risk_level,
                finance_state=rating.finance_state
            ),
            bank_guarantees_in_work=[
                BankGuarantee(
                    amount=request.offer.amount,
                    date_from=request.offer.contract_date,
                    date_to=request.offer.contract_date_end,
                    bank=request.bank.short_name,
                    beneficiary=request.tender.beneficiary_name,
                    notification=request.tender.notification_id,
                ) for request in in_work_bank_guarantee
            ],
            bank_guarantees_finished=[
                BankGuarantee(
                    amount=request.offer.amount,
                    date_from=request.offer.contract_date,
                    date_to=request.offer.contract_date_end,
                    bank=request.bank.short_name,
                    beneficiary=request.tender.beneficiary_name,
                    notification=request.tender.notification_id,
                ) for request in finished_bank_guarantee
            ],
            contracts=cls.get_contracts_statistic(
                client=client,
                starting_price=float(request.tender.price)
            ),
            tax_system=request.client.profile.tax_system,
            contract_interval=contract_interval,
            fssp=fssp,
            court_info=court,
            beneficiary_inn_region=request.tender.beneficiary_inn[:2],
            starting_price=float(request.tender.price)
        )
