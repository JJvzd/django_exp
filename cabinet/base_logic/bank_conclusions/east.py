from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property

from base_request.models import AbstractRequest
from cabinet.base_logic.printing_forms.helpers.base import BaseHelper
from cabinet.base_logic.scoring.base import ScoringResult, ScoringLogic
from clients.models import Bank, BankCode
from utils.validators import validate_passport


class BaseEastConclusionHelper:
    def __init__(self, request: AbstractRequest):
        self.request = request
        self.scoring = ScoringLogic(
            Bank.objects.get(code=BankCode.CODE_EAST), self.request
        )

    def get_data(self):
        pass

    def rule_answer(self, result):
        if isinstance(result, ScoringResult):
            return 1 if result.is_success else 0
        return 1 if result else 0


class RequiredScoringFactors(BaseEastConclusionHelper):

    def get_data(self):
        data = {
            'p1': {'scoring': self.get_p1()},
            'p2': {'scoring': self.get_p2()},
            'p3': {'scoring': self.get_p3()},
            'p4': {'scoring': self.get_p4()},
            'p5': {'scoring': self.get_p5()},
            'p6': {'scoring': self.get_p6()},
            'p7': {'scoring': self.get_p7()},
            'p8': {'scoring': self.get_p8()},
            'p9': {'scoring': self.get_p9()},
            'p10': {'scoring': self.get_p10()},
            'p11': {'scoring': self.get_p11()},
            'p12': {'scoring': self.get_p12()},
            'total': 0,
        }
        return data

    def get_p1(self):
        return self.rule_answer(self.scoring.check_rules({
            'class': 'IsBankrotScoring'
        }))

    def get_p2(self):
        return self.rule_answer(self.scoring.check_rules({
            'class': 'IsDisqualifiedPerson'
        }))

    def get_p3(self):
        return self.rule_answer(self.scoring.check_rules({
            'class': 'IsUnfairSupplierScoring'
        }))

    def get_p4(self):
        return self.rule_answer(self.scoring.check_rules({
            'class': 'RegexFieldsMatch',
            'fields': [
                'profile.reg_inn'
            ],
            'pattern': '05|06|09|20|07|15|91|92',
            'error_message': 'Банк не работает с клиентами из данного региона'
        }))

    def get_p5(self):
        return 0

    def get_p6(self):
        return self.rule_answer(self.scoring.check_rules({
            'class': 'FinanceScoring'
        }))

    def get_p7(self):
        return 0

    def get_p8(self):
        return self.rule_answer(self.scoring.check_rules({
            'class': 'FieldEqualScoring',
            'field': 'request.interval',
            'value': 930,
            'operation': '<=',
            'error_message': 'Срок БГ (дней) слишком большой'
        }))

    @cached_property
    def nalog_status_scoring(self):
        return self.rule_answer(self.scoring.check_rules({
            'class': 'NalogStatusScoring'
        }))

    def get_p9(self):
        return self.nalog_status_scoring

    def get_p10(self):
        return self.nalog_status_scoring

    def get_p11(self):
        return self.nalog_status_scoring

    def get_p12(self):
        profile = self.request.client.profile
        passports_data = [
            [
                profile.general_director.passport.series,
                profile.general_director.passport.number
            ],
        ]

        all_verified = True
        for data in passports_data:
            try:
                validate_passport(*data)
            except ValidationError:
                all_verified = False
                break
        return self.rule_answer(all_verified)


class PrincipalBO(BaseEastConclusionHelper):

    def get_p1(self):
        return {'scoring': None, 'value': None}

    def get_p2(self):
        return {'scoring': None, 'value': None}

    def get_p3(self):
        return {'scoring': None, 'value': None}

    def get_p4(self):
        return {'scoring': None, 'value': None}

    def get_p5(self):
        return {'scoring': None, 'value': None}

    def get_p6(self):
        return {'scoring': None, 'value': None}

    def get_data(self):
        data = {
            'p1': self.get_p1(),
            'p2': self.get_p2(),
            'p3': self.get_p3(),
            'p4': self.get_p4(),
            'p5': self.get_p5(),
            'p6': self.get_p6(),
            'avg': 0
        }
        return data


class CriticalFactors(BaseEastConclusionHelper):

    def get_p1(self):
        return {'scoring': None, 'value': None}

    def get_p2(self):
        return {'scoring': None, 'value': None}

    def get_p3(self):
        return {'scoring': None, 'value': None}

    def get_data(self):
        data = {
            'p1': self.get_p1(),
            'p2': self.get_p2(),
            'p3': self.get_p3(),
            'avg': 0
        }
        return data


class OtherFactors(BaseEastConclusionHelper):

    def get_p1(self):
        return {'value': None}

    def get_p2(self):
        return {'value': None}

    def get_p3(self):
        return {'value': None}

    def get_p4(self):
        return {'value': None}

    def get_p5(self):
        return {'value': None}

    def get_p6(self):
        return {'value': None}

    def get_data(self):
        data = {
            'p1': self.get_p1(),
            'p2': self.get_p2(),
            'p3': self.get_p3(),
            'p4': self.get_p4(),
            'p5': self.get_p5(),
            'p6': self.get_p6(),
            'total': None
        }
        return data


class ConditionalStopFactors(BaseEastConclusionHelper):

    def get_p1(self):
        return {'scoring': None, 'value': None}

    def get_p2(self):
        return {'scoring': None, 'value': None}

    def get_p3(self):
        return {'scoring': None, 'value': None}

    def get_p4(self):
        return {'scoring': None, 'value': None}

    def get_data(self):
        data = {
            'p1': self.get_p1(),
            'p2': self.get_p2(),
            'p3': self.get_p3(),
            'p4': self.get_p4(),
            'total': 0,
        }
        return data


class PrincipalExperience(BaseEastConclusionHelper):

    def get_p1(self):
        return {'scoring': None, 'value': None}

    def get_p2(self):
        return {'scoring': None, 'value': None}

    def get_data(self):
        data = {
            'p1': self.get_p1(),
            'p2': self.get_p2(),
            'avg': 0,
        }
        return data


class GeneratorConclusion(BaseHelper):

    def __init__(self, *args, **kwargs):
        super(GeneratorConclusion, self).__init__(*args, **kwargs)
        self.data = self.get_data()

    def get_data(self):
        data = {
            # безусловные стоп факторы
            "stop_factors": self.get_required_stop_factors(),
            # Расчет баллов по  отчетности принципала
            "principal_bo": self.get_principal_accounting_report(),
            # Критические факторы
            "critical_factors": self.get_critical_factors(),
            # Прочие параметры оценки Принципала
            "other_factors": self.get_others_factors(),
            # условные стоп  факторы
            "conditional_factors": self.get_conditional_stop_factors(),
            # Опыт принципала
            "principal_experience": self.get_principal_experience(),
        }
        data['conclusion'] = self.get_conclusion(data)
        cache.set('east_conclusion_%s' % self.request.id, data, 60 * 60 * 24 * 5)
        return data

    def get_required_stop_factors(self):
        helper = RequiredScoringFactors(self.request)
        return helper.get_data()

    def get_principal_accounting_report(self):
        helper = PrincipalBO(self.request)
        return helper.get_data()

    def get_critical_factors(self):
        helper = CriticalFactors(self.request)
        return helper.get_data()

    def get_others_factors(self):
        helper = OtherFactors(self.request)
        return helper.get_data()

    def get_conditional_stop_factors(self):
        helper = ConditionalStopFactors(self.request)
        return helper.get_data()

    def get_principal_experience(self):
        helper = PrincipalExperience(self.request)
        return helper.get_data()

    def get_conclusion(self, data):
        # TODO: доделать
        finance_scoring = 0
        finance_scoring += data['principal_bo']['avg']
        finance_scoring += data['critical_factors']['avg']
        if finance_scoring >= 0.5 and data['other_factors']['total'] == 0:
            finance_state = 'хорошее'
        else:
            finance_state = 'плохое'

        total_scoring = round(finance_scoring, 2)
        total_scoring += data['stop_factors']['total']
        total_scoring += data['principal_experience']['avg']
        total_scoring = round(total_scoring, 2)

        quarters = self.request.client.accounting_report.get_quarters()
        avg2110 = quarters[0].get_value(2110) * 12 / 3
        max2110 = max(avg2110, quarters[1].get_value(2110))
        max_limit_bg = max2110 - quarters[0].get_value(1520)
        if total_scoring > 4.76:
            category = 'A1'
            max_limit_bg = 0.7 * max_limit_bg
        elif 3.75 <= total_scoring <= 4.75:
            category = 'A2'
            max_limit_bg = 0.5 * max_limit_bg
        elif 3.25 <= total_scoring <= 3.74:
            category = 'A3'
            max_limit_bg = 0.3 * max_limit_bg
        else:
            category = '-'
            max_limit_bg = 0
        return {
            'finance_scoring': finance_scoring,
            'finance_state': finance_state,
            'category': category,
            'total_scoring': total_scoring,
            'limit': max_limit_bg * 1000,
            'max_bg_limit': max_limit_bg * 1000,
            'bg_limit': round(avg2110 / 12 * 1000, 2)
        }
