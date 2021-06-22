import attr
from django.utils.functional import cached_property

from bank_guarantee.bank_integrations.spb_bank.score_items.negative_factors import (
    NegativeFactorFormula4, NegativeFactorFormula3, NegativeFactorFormula2,
    NegativeFactorFormula1
)
from .score_items.accounting_report import (
    AccountingReportFormula1, AccountingReportFormula2, AccountingReportFormula3,
    AccountingReportFormula4, AccountingReportFormula5, AccountingReportFormula6
)
from .score_items.principal_experience import (
    PrincipalExperienceFormula1, PrincipalExperienceFormula2, PrincipalExperienceFormula3
)


@attr.s
class QuarterData:
    v1100 = attr.ib(kw_only=True, converter=float)
    v1200 = attr.ib(kw_only=True, converter=float)
    v1300 = attr.ib(kw_only=True, converter=float)
    v1400 = attr.ib(kw_only=True, converter=float)
    v1410 = attr.ib(kw_only=True, converter=float)
    v1500 = attr.ib(kw_only=True, converter=float)
    v1510 = attr.ib(kw_only=True, converter=float)
    v1530 = attr.ib(kw_only=True, converter=float)
    v1600 = attr.ib(kw_only=True, converter=float)
    v2110 = attr.ib(kw_only=True, converter=float)
    v2300 = attr.ib(kw_only=True, converter=float)
    v2320 = attr.ib(kw_only=True, converter=float)
    v2330 = attr.ib(kw_only=True, converter=float)


@attr.s
class AnotherCompanyData:
    number_changed_beneficiary_last_year = attr.ib(kw_only=True)
    principal_has_share_in_stop_factors_companies = attr.ib(kw_only=True)
    has_large_debt = attr.ib(kw_only=True)


class ClientRatingCalculator:

    def __init__(self, tender_start_price, company_age_months: int,
                 tender_counts_total: int, number_of_similar_contracts: int,
                 year_data: QuarterData,  last_quarter_data: QuarterData,
                 another_company_data: AnotherCompanyData):

        self.tender_start_price = float(tender_start_price)
        self.company_age_months = company_age_months
        self.tender_counts_total = tender_counts_total
        self.number_of_similar_contracts = number_of_similar_contracts
        self.year_data = year_data
        self.last_quarter_data = last_quarter_data
        self.another_company_data = another_company_data

    def __get_formulas_result(self, score_items):
        result = {}
        for key, value in score_items.items():
            score_item = value(data=self)
            result[key] = {
                'value': score_item.value,
                'score': score_item.score,
            }
        return result

    @cached_property
    def accounting_report_data(self):
        return {
            'formula_1': AccountingReportFormula1,
            'formula_2': AccountingReportFormula2,
            'formula_3': AccountingReportFormula3,
            'formula_4': AccountingReportFormula4,
            'formula_5': AccountingReportFormula5,
            'formula_6': AccountingReportFormula6,
        }

    @cached_property
    def calculated_accounting_report_rating(self):
        return self.__get_formulas_result(self.accounting_report_data)

    @cached_property
    def principal_experience_rating(self):
        return {
            'formula_1': PrincipalExperienceFormula1,
            'formula_2': PrincipalExperienceFormula2,
            'formula_3': PrincipalExperienceFormula3,
        }

    @cached_property
    def calculated_principal_experience_rating(self):
        return self.__get_formulas_result(self.principal_experience_rating)

    @cached_property
    def negative_factors_data(self):
        return {
            'formula_1': NegativeFactorFormula1,
            'formula_2': NegativeFactorFormula2,
            'formula_3': NegativeFactorFormula3,
            'formula_4': NegativeFactorFormula4,
        }

    @cached_property
    def calculated_negative_factors_rating(self):
        return self.__get_formulas_result(self.negative_factors_data)

    @cached_property
    def calculated_score(self):
        total_score = 0
        for key, value in self.calculated_accounting_report_rating.items():
            total_score += value['score']
        if total_score > 6:
            for key, value in self.calculated_principal_experience_rating.items():
                total_score += value['score']
            for key, value in self.calculated_negative_factors_rating.items():
                total_score += value['score']
        return total_score


@attr.s
class ClientRatingResult:
    score = attr.ib(kw_only=True)
    category = attr.ib(kw_only=True)
    level_risk = attr.ib(kw_only=True)
    finance_state = attr.ib(kw_only=True)


class ClientRatingTranslator:
    translate_score_map = [
        {
            'from': 0, 'to': 7.5, 'category': 'D',
            'risk_level': 'Высокий', 'finance_state': 'плохое'
        },
        {
            'from': 7.5, 'to': 10, 'category': 'C2',
            'risk_level': 'Допустимый', 'finance_state': 'среднее'
        },
        {
            'from': 10, 'to': 12.5, 'category': 'C1',
            'risk_level': 'Допустимый', 'finance_state': 'среднее'
        },
        {
            'from': 12.5, 'to': 15, 'category': 'B2',
            'risk_level': 'Несущественный', 'finance_state': 'хорошее'
        },
        {
            'from': 15, 'to': 17.5, 'category': 'B1',
            'risk_level': 'Несущественный', 'finance_state': 'хорошее'
        },
        {
            'from': 17.5, 'to': 20, 'category': 'B',
            'risk_level': 'Несущественный', 'finance_state': 'хорошее'
        },
        {
            'from': 20, 'to': 22, 'category': 'A2',
            'risk_level': 'Минимальный', 'finance_state': 'хорошее'
        },
        {
            'from': 22, 'to': 9999, 'category': 'A1',
            'risk_level': 'Минимальный', 'finance_state': 'хорошее'
        },
    ]

    @classmethod
    def translate(cls, score) -> ClientRatingResult:
        for variant in cls.translate_score_map:
            if variant['from'] <= score < variant['to']:
                return ClientRatingResult(
                    score=score,
                    level_risk=variant['risk_level'],
                    finance_state=variant['finance_state'],
                    category=variant['category'],
                )
        raise ValueError('Не нашлось подходящего варианта')
