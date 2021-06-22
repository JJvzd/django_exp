import math
from functools import reduce

from django.utils.dateparse import parse_date
from django.utils.functional import cached_property

from accounting_report.helpers import QuarterParameters
from accounting_report.models import Quarter
from cabinet.base_logic.contracts.base import ContractsLogic
from cabinet.base_logic.printing_forms.helpers.base import BaseHelper
from cabinet.base_logic.scoring.base import ScoringResult, ScoringLogic
from cabinet.constants.constants import Target, FederalLaw
from cabinet.models import EgrulData
from clients.models import Bank
from conclusions_app.conclusions.common import (
    HasArrearsOnPaymentOfTaxesConclusion
)
from conclusions_app.conclusions_logic import ConclusionsLogic
from external_api.nalogru_api import NalogRu
from external_api.searchtenderhelp_api import SearchTenderhelpApi
from settings.configs.banks import BankCode


class InbankHelper(BaseHelper):

    def get_quarters(self):
        return self.client.accounting_report.get_quarters()

    def __init__(self, *args, **kwargs):
        super(InbankHelper, self).__init__(*args, **kwargs)
        self.finance = self.get_finance()

    def get_previous_year_quarter(self):
        return self.client.accounting_report.get_previous_year_quarter()

    @cached_property
    def bank(self):
        return Bank.objects.get(code=BankCode.CODE_INBANK)

    def physical_shareholders(self):
        output = []
        for person in self.profile.profilepartnerindividual_set.all():
            person_name = person.full_name
            text = '%s доля %s %%' % (person_name, person.share)
            output.append(text)
        return ', '.join(output)

    def getPropertyStatus(self):
        address = self.profile.fact_address_properies
        if address['status']:
            return 'Собственность'
        else:
            return 'Аренда с %s по %s' % (address['from'], address['to'])

    def suggested_price_procent(self):
        result = round(100 - self.request.suggested_price_percent, 2)
        return result

    def contract_type(self):
        return Target.PARTICIPANT in self.request.targets and \
               self.request.tender.federal_law in [FederalLaw.LAW_44, FederalLaw.LAW_223]

    def sro_licences(self):
        if self.profile.has_license_sro:
            return self.profile.licensessro_set.all()
        else:
            return []

    def get_target_display(self):
        if Target.PARTICIPANT in self.request.targets:
            return 'тендер'
        if Target.EXECUTION in self.request.targets:
            return 'контракт'
        return ''

    def get_need_more_display(self):
        return 'Да' if self.request.have_additional_requirement else 'Нет'

    @cached_property
    def isSmallSubject(self):
        category = NalogRu().get_subject_size(self.client.inn)
        return category in [1, 2]

    @cached_property
    def isMiddleSubject(self):
        category = NalogRu().get_subject_size(self.client.inn)
        return category in [3]

    @cached_property
    def isUnknownSubject(self):
        category = NalogRu().get_subject_size(self.client.inn)
        return category not in [1,2,3]

    def rule_answer(self, result):
        if isinstance(result, ScoringResult):
            return 1 if result.is_success else 0
        return 1 if result else 0

    def scoring(self):
        scoring = ScoringLogic(self.bank, self.request)
        sum = 0
        count = 0
        quarters = self.client.accounting_report.get_quarters_for_fill()
        for quarter in quarters:
            value = quarter.get_value(2110)
            if value != 0 and quarter.not_empty():
                sum += value
                count += 1
        quarters = self.get_quarters()
        last_period = quarters[0]
        if count > 0:
            test_9 = float(self.request.required_amount) / (sum / count) > 10
        else:
            test_9 = False
        test_10 = last_period.get_value(1150) <= 0
        return {
            'test_1': self.rule_answer(scoring.check_rules({
                'class': 'RegexFieldsMatch',
                'fields': ["request.client.inn"],
                'pattern': '01|05|06|07|09|15|20|91|92',
                'error_message': 'Банк не работает с клиентами из данного региона'
            })),
            'test_2': self.rule_answer(scoring.check_rules({
                'class': 'RegexFieldsMatch',
                'fields': ["request.tender.inn"],
                'pattern': '01|05|06|07|09|15|20|91|92',
                'error_message': 'Банк не работает с клиентами из данного региона'
            })),
            'test_3': self.rule_answer(scoring.check_rules({
                'class': 'OgrnScoring',
                'value': 183,
                'error_message': 'Компания зарегистрирована менее 6 месяцев назад'
            })),
            'test_4': self.rule_answer(scoring.check_rules({
                'class': 'NegativeQuartersValueScoring',
                'codes': [2400],
                'error_message': 'В строке 2400 бухгалтерской отчётности за завершенный'
                                 ' квартал имеют отрицательные значения.'
            })),
            'test_5': self.rule_answer(scoring.check_rules({
                'class': 'IsUnfairSupplierScoring',
                'error_message': 'Находится в реестре недобросовестных поставщиков'
            })),
            'test_6': self.rule_answer(scoring.check_rules({
                'class': 'DecisionSuspendScoring',
                'error_message': 'Имеются решения о приостановлении по счетам'
            })),
            'test_7': self.rule_answer(scoring.check_rules({
                'class': 'NalogStatusScoring',
                'error_message': 'Задолжности по налогам и сборам с сайта '
                                 'service.nalog.ru/zd.do'
            })),
            'test_8': self.rule_answer(scoring.check_rules({
                'class': 'IsBankrotScoring',
                'error_message': 'Задолжности по налогам и сборам с сайта '
                                 'service.nalog.ru/zd.do'
            })),
            'test_9': test_9,
            'test_10': test_10
        }

    def get_finance_test_1(self, period: Quarter):
        """
        Рентабельность деятельности Клиента
        (анализируется соотношение Чистой прибыли за Последний завершенный год
        к выручке за тот же период)
            - Низкая степень риска (1 балл) – рентабельность деятельности более 3%;
            - Умеренная степень риска (2 балла) – рентабельность деятельности
            от 1% до 3%;
            - Высокая степень риска (3 балла) – рентабельность деятельности
            от 0,5% до 1%;
            - Сверхвысокая степень риска (4 балла) – рентабельность деятельности
            от 0% до 0,5%.
        (Ф.2) (Стр.2400/Стр.2110)*100
        :param period:
        :return:
        """
        prev_value = period.get_value(2110)
        if prev_value != 0:
            value = period.get_value(2400) / period.get_value(2110) * 100
            percent = round(value, 2)
        else:
            value = 0
            percent = None

        if value > 3:
            score = 1
        elif 1 < value <= 3:
            score = 2
        elif 0.5 < value <= 1:
            score = 3
        else:
            score = 4

        return {
            'value1': period.get_value(2400),
            'value2': period.get_value(2110),
            'percent': percent,
            'result': score
        }

    def get_quarter_by_params(self, params):
        return self.client.accounting_report.get_quarter_by_params(params)

    def get_finance_test_2(self, last_year: Quarter):
        """
        Сокращение/прирост выручки (осуществляется сравнение выручки за Последний
        завершенный год с выручкой за предыдущий завершенный год)
            - Низкая степень риска (1 балл) – имеется рост выручки более 10 %;
            - Умеренная степень риска (2 балла) – отсутствует рост выручки или имеется
            рост выручки до 10 % включительно;
            - Высокая степень риска (3 балла) – имеется снижение выручки в диапазоне до
            20% включительно;
            - Сверхвысокая степень риска (4 балла) – имеется снижение выручки более
            чем на 20%.
        (Ф.2) (Стр.2110 последний ЗГ/Стр.2110 предыдущий ЗГ)*100
        :param last_year:
        :return:
        """
        prev_year = self.get_quarter_by_params(QuarterParameters(
            year=int(last_year.year) - 1,
            quarter=last_year.quarter
        ))

        if prev_year.not_empty() and last_year.not_empty():
            prev_value = prev_year.get_value(2110)
            if prev_value != 0:
                value = last_year.get_value(2110) / prev_value
            else:
                value = 0
            rost = value > 1
            value = math.fmod(value, 1) * 100
            if rost and value > 10:
                score = 1
            elif rost and 0 <= value <= 10:
                score = 2
            elif not rost and 0 <= value <= 20:
                score = 3
            else:
                score = 4
        else:
            score = 4

        return {
            'value1': last_year.get_value(2110),
            'value2': prev_year.get_value(2110),
            'result': score
        }

    def get_finance_test_3(self, last_period: Quarter):
        """
        Текущая прибыль/убыток (анализируется Чистая прибыль, рассчитанная нарастающим
        итогом, за последний завершенный квартал)
            - Низкая степень риска (1 балл) – имеется чистая прибыль;
            - Умеренная степень риска (2 балла) – чистая прибыль равна 0;
            - Высокая степень риска (4 балла) – имеются убытки в размере,
            не превышающем 5 % от выручки за тот же период;
            - Сверхвысокая степень риска (8 балла) – имеются убытки в размере,
            превышающем 5 % от выручки за тот же период.
        :return:
        """
        value = last_period.get_value(2110)
        value2 = last_period.get_value(2400)
        rost = abs(value) / value2 if value2 != 0 else 0
        if value > 0:
            score = 1
        elif value == 0:
            score = 2
        elif value < 0 and rost < 5:
            score = 4
        elif value < 0 and rost >= 5:
            score = 8
        else:
            score = 3
        return {
            'value1': value,
            'value2': value2,
            'result': score
        }

    def get_finance_test_4(self, last_year):
        """
        (анализируется доля Чистых активов за Последний завершенный год в
        валюте баланса за тот же период)
            - Низкая степень риска (1 балл) – доля > 30%;
            - Умеренная степень риска (2 балла) – доля в диапазоне от 15 до 30%;
            - Высокая степень риска (3 балла) – доля в диапазоне от 5 до 15%;
            - Сверхвысокая степень риска (4 балла) – доля < 5%.
        :param last_year:
        :return:
        """
        last_year_1600 = last_year.get_value(1600)
        v = last_year.get_value(1600) - (
                last_year.get_value(1400) +
                last_year.get_value(1500) +
                last_year.get_value(1530)
        )
        value = v / last_year_1600 * 100 if last_year_1600 != 0 else 0
        if value > 30:
            score = 1
        elif 15 < value <= 30:
            score = 2
        elif 5 < value <= 15:
            score = 3
        else:
            score = 4

        if last_year.get_value(1600) != 0:
            percent = round(v / last_year_1600 * 100, 2)
        else:
            percent = None
        return {
            'value1': v,
            'value2': last_year_1600,
            'percent': percent,
            'result': score
        }

    def get_finance_test_5(self):
        """
        Соответствие Контракта профильности деятельности
            - Низкая степень риска (1 балл) – контракт, в обеспечение которого
            запрашивается Гарантия, соответствует профильности деятельности Клиента,
            а так же имеется опыт исполнения контрактов аналогичного размера;
            - меренная степень риска (2 балла) – контракт, в обеспечение которого
            запрашивается Гарантия, соответствует профильности деятельности Клиента,
            при от-сутствии опыта исполнения контрактов аналогичного размера;
            - Высокая степень риска (4 балла) – контракт, в обеспечение которого
            запрашивается Гарантия,не соответствует профильности деятельности Клиента,
            но имеется опыт исполнения контрактов  аналогичного размера;
            - Сверхвысокая степень риска (6 балла) – контракт, в обеспечение которого
            запрашивается Гарантия, не соответствует профильности деятельности Клиента,
            при отсутствии опыта исполнения контрактов аналогичного размера.
        :return:
        """
        return {
            'value1': ' ',
            'value2': ' ',
            'result': 3
        }

    def get_finance_test_6(self):
        """
        Количество исполненных контрактов:
            - Низкая степень риска (1 балл) – более 7 исполненных контрактов;
            - Умеренная степень риска (2 балла) – от 5 до 7 исполненных контрактов;
            - Высокая степень риска (3 балла) – от 2 до 4 исполненных контрактов;
            - Сверхвысокая степень риска (6 баллов) – 1 исполненный контракт.
        :return:
        """
        finished_contracts = ContractsLogic(
            self.request.client
        ).get_finished_contracts_count()

        if finished_contracts > 7:
            score = 1
        elif 5 <= finished_contracts <= 7:
            score = 2
        elif 2 <= finished_contracts <= 4:
            score = 3
        else:
            score = 6

        return {
            'value1': finished_contracts,
            'value2': ' ',
            'result': score
        }

    def get_finance_test_7(self):
        """
        Кредитная история
            - Низкая степень риска (1 балл) – кредитная история положительная
            (факты просрочек отсутствуют);
            - Умеренная степень риска (2 балла) – кредитная история отсутствует
            либо имели место просрочки
            - платежей по кредитам сроком не более 30 дней (не более 1 раза);
            - Высокая степень риска (3 балла) – имели место просрочки платежей
            по кредитам (не более 2 раз);
            -Сверхвысокая степень риска (4 балла) – имели место просрочки платежей
            по кредитам (более 2 раз).
        :return:
        """
        return {
            'value1': ' ',
            'value2': ' ',
            'result': 3
        }

    @cached_property
    def finance_data(self):
        quarters = self.get_quarters()
        if quarters[0].id != quarters[1].id:
            return {
                'last_period': quarters[0],
                'last_year': quarters[1],
                'previous_year': self.get_previous_year_quarter()
            }
        return {
            'last_year': quarters[1],
            'previous_year': self.get_previous_year_quarter()

        }

    def get_last_period_name(self):
        if len(self.finance_data) > 2:
            return '%i кв %i' % (self.finance_data['last_period'].quarter,
                                 self.finance_data['last_period'].year)
        return ''

    def get_last_period_revenues(self):
        if len(self.finance_data) > 2:
            return self.finance_data['last_period'].get_value(2110)
        return ''

    def get_last_period_profit(self):
        if len(self.finance_data) > 2:
            return self.finance_data['last_period'].get_value(2400)
        return ''

    def get_last_year_name(self):
        return self.finance_data['last_year'].year

    def get_last_year_revenues(self):
        return self.finance_data['last_year'].get_value(2110)

    def get_last_year_profit(self):
        return self.finance_data['last_year'].get_value(2400)

    def get_previous_year_name(self):
        return self.finance_data['previous_year'].year

    def get_previous_year_revenues(self):
        return self.finance_data['previous_year'].get_value(2110)

    def get_previous_year_profit(self):
        return self.finance_data['previous_year'].get_value(2400)

    def get_analise_period_name(self):
        return '%i/ %s' % (self.get_previous_year_name(), self.get_last_period_name())


    def get_finance(self):
        quarters = self.get_quarters()
        last_period = quarters[0]
        last_year = quarters[1]
        data = {
            'test_1': self.get_finance_test_1(last_year),
            'test_2': self.get_finance_test_2(last_year),
            'test_3': self.get_finance_test_3(last_period),
            'test_4': self.get_finance_test_4(last_year),
            'test_5': self.get_finance_test_5(),
            'test_6': self.get_finance_test_6(),
            'test_7': self.get_finance_test_7(),
        }
        total_score = 0
        for d in data.values():
            total_score += d['result']

        if total_score > 25:
            finance_score = 'плохое'
            raiting = ''
        elif 14 < total_score <= 25:
            finance_score = 'хорошее'
            raiting = 'B'
        else:
            finance_score = 'хорошее'
            raiting = 'A'

        data['total_score'] = total_score
        data['finance_score'] = finance_score
        data['raiting'] = raiting
        return data

    @cached_property
    def executing_contracts(self):
        contracts = ContractsLogic(self.client).get_execution_contracts()
        data = {}
        for contract in contracts:
            d = parse_date(contract.get('start_date')).year
            data.setdefault(d, [])
            data[d].append(contract)

        data = [(k, data[k]) for k in sorted(data.keys())]
        result = []
        for year, d in data:
            result.append({
                'year': year,
                'count': len(d),
                'sum': reduce(lambda sum, el: sum + el.get('price'), d, 0)
            })
        return result

    @cached_property
    def _executing_contracts(self):
        return ContractsLogic(self.client).get_execution_contracts()

    def get_executing_contracts_count(self):
        return len(self._executing_contracts) or ''

    def get_executing_contracts_max(self):
        max_price = 0
        for contract in self._executing_contracts:
            if float(contract.price) > max_price:
                max_price = float(contract.price)
        return max_price or ''

    def get_executing_contracts_sum(self):
        return reduce(
            lambda sum, el: sum + float(el.price),
            self._executing_contracts, 0) or ''

    @cached_property
    def finished_contracts(self):
        contracts = ContractsLogic(self.client).get_finished_contracts()
        data = {}
        for contract in contracts:
            d = parse_date(contract.start_date).year
            data.setdefault(d, [])
            data[d].append(contract)

        data = [(k, data[k]) for k in sorted(data.keys())]
        result = []
        for year, d in data:
            result.append({
                'year': year,
                'count': len(d),
                'sum': reduce(lambda sum, el: sum + el.price, d, 0)
            })
        return result

    @cached_property
    def _finished_contracts(self):
        return ContractsLogic(self.client).get_finished_contracts()

    def get_finished_contracts_count(self):
        return len(self._finished_contracts) or ''

    def get_finished_contracts_max(self):
        max_price = 0
        for contract in self._finished_contracts:
            if float(contract.price) > max_price:
                max_price = float(contract.price)
        return max_price or ''

    def get_finished_contracts_sum(self):
        return reduce(
            lambda sum, el: sum + float(el.price),
            self._finished_contracts, 0) or ''

    def get_join_fl_shares(self):
        data = []
        for person in self.profile.profilepartnerindividual_set.filter(share__gt=0):
            data.append(person.full_name())
        return ', '.join(data)

    def has_dolg(self):
        result = ConclusionsLogic.get_conclusion_result(
            client=self.client,
            conclusion=HasArrearsOnPaymentOfTaxesConclusion
        )
        if result.result:
            return 'Негативные сведения отсутствуют'
        return 'найдены'

    def has_sro(self):
        return 1 if self.profile.has_license_sro or self.profile.is_member_sro else 0

    def last_contr_agents(self):
        limit = 3
        contracts = ContractsLogic(self.client).get_finished_contracts()
        count = 0
        output = []
        for contract in contracts:
            str = contract.issuer_name
            if str not in output:
                count += 1
                output.append(str + '\n')
            if count == limit:
                break
        return ', '.join(output)


    @property
    def organization_form(self):
        if self.client.is_individual_entrepreneur:
            return 'ИП'
        return self.profile.get_organization_form_display()

    def get_inn(self):
        return self.profile.reg_inn

    def get_reg_state_date(self):
        return self.profile.reg_state_date

    def get_authorized_capital_paid(self):
        return self.profile.authorized_capital_paid

    def get_notification_id(self):
        return self.request.tender.notification_id

    def get_federal_law(self):
        return self.request.tender.get_federal_law_display()[:-3]

    def get_interval_from(self):
        return self.request.interval_from

    def get_interval_to(self):
        return self.request.interval_to

    def get_interval(self):
        return self.request.interval

    def get_tender_subject(self):
        return self.request.tender.subject

    def get_suggested_price_amount(self):
        return '%.2f' % self.request.suggested_price_amount

    def get_suggested_price_percent(self):
        return '%.2f %%' % self.request.suggested_price_percent

    def get_beneficiar_full_name(self):
        egrul_data = EgrulData.get_info(self.request.tender.beneficiary_inn)
        if egrul_data:
            return egrul_data.get(
                'section-ur-lico', {}
            ).get('full-name-ur-lico', '') or self.profile.full_name
        return self.request.tender.beneficiary_name

    def get_beneficiar_name(self):
        return self.request.tender.beneficiary_name

    def getBeneficiars(self):
        return self.profile.beneficiars.filter(share__gte=21.5)

    def getPPersons(self):
        return self.profile.profilepartnerindividual_set.filter(share_gt=0)

    def getJPersons(self):
        return self.profile.profilepartnerlegalentities_set.filter(share_gt=0)

    def get_company_info(self):
        search = SearchTenderhelpApi()
        search_data = search.get_company_info(self.profile.reg_inn)
        fact_address = self.profile.fact_address_properies
        if not search_data:
            return {
                'inn': self.profile.reg_inn,
                'ogrn': self.profile.reg_ogrn,
                'kpp': self.profile.reg_kpp,
                'data': {
                    'inn': self.profile.reg_inn,
                    'kpp': self.profile.reg_kpp,
                    'OKPO': self.profile.reg_okpo,
                    'regNum': '',
                    'fullName': self.profile.full_name,
                    'legalForm': {},
                    'shortName': self.profile.short_name,
                    'factAddress': fact_address['address'],
                    'postAddress': self.profile.legal_address,
                    'customerCode': '',
                    'consRegistryNum': '',
                    'registrationDate': ''
                }
            }

        if not search_data['data']['fullName']:
            search_data['data']['fullName'] = self.profile.full_name
        if not search_data['data']['factAddress']:
            search_data['data']['factAddress'] = fact_address['address']
        if not search_data['data']['postAddress']:
            search_data['data']['factAddress'] = self.profile.legal_address
        return search_data

    def get_beneficiar_info(self):
        search = SearchTenderhelpApi()
        search_data = search.get_company_info(self.request.tender.beneficiary_inn)
        if not search_data:
            return {
                'inn': self.request.tender.beneficiary_inn,
                'ogrn': self.request.tender.beneficiary_ogrn,
                'kpp': self.request.tender.beneficiary_kpp,
                'data': {
                    'inn': self.request.tender.beneficiary_inn,
                    'kpp': self.request.tender.beneficiary_kpp,
                    'OKPO': '',
                    'regNum': '',
                    'fullName': self.request.tender.beneficiary_name,
                    'legalForm': {},
                    'shortName': self.request.tender.beneficiary_name,
                    'factAddress': self.request.tender.beneficiary_address,
                    'postAddress': self.request.tender.beneficiary_address,
                    'customerCode': '',
                    'consRegistryNum': '',
                    'registrationDate': ''
                }
            }

        if not search_data['data']['fullName']:
            search_data['data']['fullName'] = self.request.tender.beneficiary_name
        if not search_data['data']['factAddress']:
            search_data['data']['factAddress'] = self.request.tender.beneficiary_address
        if not search_data['data']['postAddress']:
            search_data['data']['factAddress'] = self.request.tender.beneficiary_address
        return search_data

    def getBenAddressFromEGRUL(self):
        egrul_data = EgrulData.get_info(self.request.tender.beneficiary_inn)
        if egrul_data:
            return egrul_data.get(
                'section-ur-adress', {}
            ).get('full_address', '') or self.request.tender.beneficiary_address
        return self.request.tender.beneficiary_address

    def date_last_finished_contract(self):
        max_end_date = None
        for contract in self._finished_contracts:
            end_date = contract.get('end_date')
            end_date = parse_date(end_date)
            if not max_end_date:
                max_end_date = end_date
            if end_date > max_end_date:
                max_end_date = end_date
        if max_end_date:
            return max_end_date.strftime('%d.%m.%Y')
        return ''

    def is_execution(self):
        return Target.EXECUTION in self.request.targets

    def is_participant(self):
        return Target.PARTICIPANT in self.request.targets

    def is_warranty(self):
        return Target.WARRANTY in self.request.targets

    def get_contract_type(self):
        return self.request.get_contract_type_display()

    def get_required_amount(self):
        return self.request.required_amount
