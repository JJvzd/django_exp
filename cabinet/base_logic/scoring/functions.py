import datetime
import json
import logging
import re
from collections import Iterable

from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property

from accounting_report.models import Quarter
from bank_guarantee.bank_integrations.spb_bank.client_rating_calculator import (
    ClientRatingTranslator
)
from bank_guarantee.bank_integrations.spb_bank.helpers import (
    get_client_rating_calculator, SPBContractsInfo
)
from bank_guarantee.models import Request, ContractType
from cabinet.base_logic.bank_conclusions.rib import RIBConclusionForTH
from cabinet.base_logic.conclusions.check_passport import check_passport
from cabinet.base_logic.contracts.base import ContractsLogic
from cabinet.base_logic.helpers.check_data import check_in_regions
from cabinet.base_logic.scoring.base import ScoringItem, ScoringResult, ScoringLogic
from cabinet.constants.constants import TaxationType, Target, FederalLaw, OrganizationForm
from cabinet.models import System, PlacementPlace, EgrulData
from common.helpers import generate_choices
from conclusions_app.conclusions.common import (
    HasArrearsOnPaymentOfTaxesConclusion, DecisionToSuspendConclusion,
    RMSPConclusion, InTerroristListConclusion, DisqualifiedPersonConclusion,
    AddressOfManyRegistrationsConclusion, CheckPassportConclusion, IsBankrotConclusion
)
from conclusions_app.conclusions_logic import ConclusionsLogic
from external_api.clearspending_api import ClearsSpendingApi
from external_api.nalogru_api import NalogRu
from external_api.parsers_tenderhelp import ParsersApi
from external_api.rusprofile_api import RusProfile
from external_api.searchtenderhelp_api import SearchTenderhelpApi
from external_api.zachestniybiznes_api import ZaChestnyiBiznesApi
from utils.helpers import get_value_by_path

logger = logging.getLogger('django')

CHOICES_SCORING = []

"""
url: http://confluence.tenderhelp.ru/pages/viewpage.action?pageId=7897115
"""


def add_scoring(cls):
    fields = []
    if hasattr(cls, 'scoring_params'):
        for scoring_param in cls.scoring_params:
            field = {'name': scoring_param}
            if hasattr(cls, '%s_choices' % scoring_param):
                field.update({
                    'choices': getattr(cls, '%s_choices' % scoring_param)
                })
            if isinstance(getattr(cls, scoring_param), list):
                field.update({
                    'multiple': True
                })
            if isinstance(getattr(cls, scoring_param), bool):
                field.update({
                    'bool': True
                })
            fields.append(field)
    CHOICES_SCORING.append({
        'class_name': cls.__name__,
        'full_name': cls.full_name,
        'fields': fields
    })
    return cls


@add_scoring
class TrueScoring(ScoringItem):
    full_name = 'Скоринг пройден'

    def validate(self):
        return ScoringResult()


@add_scoring
class FailScoring(ScoringItem):
    full_name = 'Скоринг не пройден'

    def validate(self):
        return ScoringResult(self.error_message or 'FailScoringItem')


@add_scoring
class AllowedTenderLawsScoring(ScoringItem):
    """ проверка допустимых законов конкурса (Поле «ФЗ/ПП» в Заявке) """
    full_name = 'проверка допустимых законов конкурса (Поле «ФЗ/ПП» в Заявке)'
    laws = []
    laws_choices = generate_choices(
        list(FederalLaw.CHOICES) + [[ContractType.COMMERCIAL, 'коммерция']]
    )
    scoring_params = ['laws']
    error_message = 'Недопустимый ФЗ'

    def validate(self) -> ScoringResult:
        if ContractType.COMMERCIAL in self.laws \
            and self.request.contract_type == ContractType.COMMERCIAL:
            return ScoringResult()
        if self.request.tender.federal_law in self.laws:
            return ScoringResult()
        return ScoringResult(self.get_error_message())


@add_scoring
class FieldEqualScoring(ScoringItem):
    """ Универсальный скоринг проверки соответствия поля в заявке/анкете условию """
    full_name = 'Универсальный скоринг проверки соответствия поля в заявке/анкете условию'
    field = None
    value = None
    value2 = None
    operation = '='
    operation_choices = ['=', '!=', '>', '<', '>=', '<=', 'IN', 'BETWEEN']
    scoring_params = ['field', 'value', 'value2', 'operation']

    def get_error_message(self):
        if self.error_message:
            return self.error_message
        value = self.value
        if isinstance(value, Iterable):
            value = json.dumps(value)
        return "%s %s %s" % (self.field, self.operation, value)

    def get_value(self, field_name):
        field_value = None
        if field_name.startswith('request'):
            field_name = field_name[len('request') + 1:]
            field_value = get_value_by_path(self.request, field_name)
        if field_name.startswith('anketa'):
            field_name = field_name[len('anketa') + 1:]
            field_value = get_value_by_path(self.request.client.profile, field_name)
        if field_name.startswith('profile'):
            field_name = field_name[len('profile') + 1:]
            field_value = get_value_by_path(self.request.client.profile, field_name)
        return field_value

    def convert_control_value(self, inspected_value, control_value):
        """
        Преобразует control_value (Указанное в параметрах скоринга) в тип,
        который у inspected_value (взятое из модели)
        """
        if type(inspected_value) == type(control_value):
            return control_value
        if isinstance(inspected_value, int):
            return int(control_value)
        if isinstance(inspected_value, float):
            return float(control_value)
        return control_value

    def validate(self) -> ScoringResult:
        value = self.get_value(self.field)

        if self.operation == '=':
            self.value = self.convert_control_value(value, self.value)
            return ScoringResult() if value == self.value else ScoringResult(
                self.get_error_message()
            )

        if self.operation == '!=':
            self.value = self.convert_control_value(value, self.value)
            return ScoringResult() if value != self.value else ScoringResult(
                self.get_error_message()
            )

        if self.operation == '>=':
            self.value = self.convert_control_value(value, self.value)
            return ScoringResult() if value >= self.value else ScoringResult(
                self.get_error_message()
            )

        if self.operation == '<=':
            self.value = self.convert_control_value(value, self.value)
            return ScoringResult() if value <= self.value else ScoringResult(
                self.get_error_message()
            )

        if self.operation == '>':
            self.value = self.convert_control_value(value, self.value)
            return ScoringResult() if value > self.value else ScoringResult(
                self.get_error_message()
            )

        if self.operation == '<':
            self.value = self.convert_control_value(value, self.value)
            return ScoringResult() if value < self.value else ScoringResult(
                self.get_error_message()
            )

        if self.operation == 'IN':
            if isinstance(self.value, Iterable):
                if value in self.value:
                    return ScoringResult()
                else:
                    return ScoringResult(self.get_error_message())
            else:
                return ScoringResult('value not iterable')

        if self.operation == 'BETWEEN':
            if self.value <= value <= self.value2:
                return ScoringResult()
            else:
                return ScoringResult(self.get_error_message())

        self.value = self.convert_control_value(value, self.value)
        if value == self.value:
            return ScoringResult()
        else:
            return ScoringResult(self.get_error_message())


@add_scoring
class BeneficiarsAgeScoring(FieldEqualScoring):
    full_name = 'Проверка возраста участников'
    value = None
    operation = '='
    operation_choices = ['=', '!=', '>', '<', '>=', '<=', 'IN', 'BETWEEN']
    data_from_params = ['value', 'operation']
    scoring_params = ['value', 'operation']
    error_message = 'Недопустимый возраст участников'

    def validate(self) -> ScoringResult:
        beneficiars = self.request.client.profile.profilepartnerindividual_set.filter(
            share__gt=0
        )

        for beneficiar in beneficiars:
            birth_day = beneficiar.passport.date_of_birth
            if birth_day:
                age = (datetime.datetime.now() - birth_day).year

                if self.operation == '=':
                    if age != self.value:
                        return ScoringResult()

                if self.operation == '!=':
                    if age == self.value:
                        return ScoringResult()
                if self.operation == '>=':
                    if age < self.value:
                        return ScoringResult()
                if self.operation == '>=':
                    if age > self.value:
                        return ScoringResult()
                if self.operation == '>':
                    if age <= self.value:
                        return ScoringResult()
                if self.operation == '<':
                    if age >= self.value:
                        return ScoringResult()
        return ScoringResult(self.get_error_message())


@add_scoring
class BGSumLessContractSum(ScoringItem):
    disable_for_loans = True
    full_name = 'BGSumLessContractSum'

    def validate(self) -> ScoringResult:
        tender_price = self.request.suggested_price_amount
        if tender_price and tender_price > 0:
            if self.request.required_amount <= tender_price:
                return ScoringResult()
        return ScoringResult(self.get_error_message())


@add_scoring
class CleanActiveLessThenBG(ScoringItem):
    full_name = "Величина чистых активов БО 1300 меньше суммы банковской гарантии."
    error_message = "Величина чистых активов БО 1300 меньше суммы банковской гарантии."

    def validate(self) -> ScoringResult:
        quarter = self.request.client.accounting_report.get_quarters()[0]
        clean_active = quarter.get_value(1300) * 1000
        if clean_active < self.request.required_amount:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class ConditionalScoring(ScoringItem):
    """
        Условный скоринг, проверяет правила в секции if,
        если они вернули true - проверяет правила секции then,
        иначе проверяет секцию else
    """
    full_name = 'Условный блок'
    if_conditionals = []
    then_conditionals = []
    else_conditionals = []
    error_message = "Ошибка условного скоринга"
    scoring_params = ['if_conditionals', 'then_conditionals', 'else_conditionals']

    def validate(self) -> ScoringResult:
        if_conditionals = self.if_conditionals if self.if_conditionals else []
        result = ScoringLogic(
            bank=self.bank, request=self.request
        ).validate_rules(if_conditionals)

        if result.is_success:
            then_conditionals = self.then_conditionals if self.then_conditionals else []
            result = ScoringLogic(
                bank=self.bank, request=self.request
            ).validate_rules(then_conditionals)
            if result.is_success:
                return ScoringResult()
            else:
                self.error_message = result.get_first_error()
                return ScoringResult(self.get_error_message())
        else:
            if self.else_conditionals:
                result = ScoringLogic(
                    bank=self.bank, request=self.request
                ).validate_rules(self.else_conditionals)
                if result.is_success:
                    return ScoringResult()
                else:
                    self.error_message = result.get_first_error()
                    return ScoringResult(self.get_error_message())
            else:
                return ScoringResult()


@add_scoring
class CountContractsScoring(ScoringItem):
    full_name = "Проверка количества контрактов"
    min = 1
    scoring_params = ['min']
    disable_for_loans = True

    def get_error_message(self):
        if not self.error_message:
            return "Количество контрактов меньше, чем %s" % self.min
        return self.error_message

    def validate(self) -> ScoringResult:
        finished_contracts = ContractsLogic(
            self.request.client
        ).get_finished_contracts_count()

        if finished_contracts == 0:
            if self.request.experience_general_contractor:
                return ScoringResult()
        else:
            if int(finished_contracts) >= int(self.min):
                return ScoringResult()

        return ScoringResult(self.get_error_message())


@add_scoring
class DecisionSuspendScoring(ScoringItem):
    error_message = "У компании имеются приостановленные счета"
    full_name = "У компании имеются приостановленные счета"

    def validate(self) -> ScoringResult:
        result = ConclusionsLogic.get_conclusion_result(
            client=self.request.client,
            conclusion=DecisionToSuspendConclusion
        )
        if not result.result:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


class ExperienceScoring(CountContractsScoring):
    # TODO: проверить необходимость существования этой функции
    """
        Проверяет наличие исполненных контрактов без учета их количества.
        Смотрит на поле в анкете и информацию из внешних источников
    """
    disable_for_loans = True
    error_message = 'Нет опыта исполнения государственных контрактов ' \
                    'в качестве генподрядчика / субподрядчик'


@add_scoring
class FinanceScoring(ScoringItem):
    error_message = 'Величина чистых активов за последний завершенный квартал меньше ' \
                    'уставного капитала или отрицательная величина.'
    full_name = 'Величина чистых активов за последний завершенный квартал ' \
                'меньше уставного капитала'

    def validate(self) -> ScoringResult:
        quarter = self.request.client.accounting_report.get_quarters()[1]
        value = quarter.get_value(1600) - \
                (quarter.get_value(1400) +
                 quarter.get_value(1500) -
                 quarter.get_value(1530))
        if value < 0:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class FitLimitScoring(ScoringItem):
    """
    Проверка, лимита по сумме банковских гарантий в указаном банке
    """
    full_name = "Проверка, лимита по сумме банковских гарантий в указаном банке"
    disable_for_loans = True
    error_message = 'Превышен лимит по сумме банковских гарантий в данном банке'

    limit = 0
    scoring_params = ['limit']

    def __init__(self, bank, request, settings: dict):
        super().__init__(bank, request, settings)
        if not self.limit:
            self.limit = self.bank.settings.limit_for_client

    def fit_limit(self):
        if not self.limit:
            return ScoringResult()

        total = self.bank.bank_integration.fit_limit(self.request)

        if total > self.limit:
            return ScoringResult(self.get_error_message())
        return ScoringResult()

    def validate(self) -> ScoringResult:
        return self.fit_limit()


@add_scoring
class FizDolScoring(ScoringItem):
    error_message = 'Физическое лицо в участниках (акционерах) ' \
                    'без российского гражданства'
    full_name = 'Физическое лицо в участниках (акционерах) без российского гражданства'

    def validate(self) -> ScoringResult:
        value = 'Россия'
        beneficiars = self.request.client.profile.profilepartnerindividual_set.filter(
            share__gt=0
        )
        for person in beneficiars:
            if value not in person.citizenship:
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class GuaranteeTargetScoring(ScoringItem):
    full_name = 'Недопустимый вид банковской гарантии'
    exclude = True
    targets = []
    scoring_params = ['targets', 'exclude']
    targets_choices = generate_choices(Target.CHOICES)
    error_message = 'Недопустимый вид банковской гарантии'
    disable_for_loans = True

    @cached_property
    def prepared_targets(self):
        """ из старого формата  в новый если требуется"""
        cleared_targets = []
        targets_map = {
            1: Target.PARTICIPANT,
            2: Target.EXECUTION,
            3: Target.WARRANTY,
            4: Target.AVANS_RETURN
        }
        for target in self.targets:
            if isinstance(target, int):
                cleared_targets.append(targets_map.get(target))
            else:
                cleared_targets.append(target)
        return cleared_targets

    def validate(self) -> ScoringResult:
        if self.exclude:
            if not any([target in self.request.targets for target in self.targets]):
                return ScoringResult(self.get_error_message())
        else:
            if any([target in self.request.targets for target in self.targets]):
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class HasClearActivesScoring(ScoringItem):
    full_name = 'Чистые активы меньше 0'
    only_yearly = False
    scoring_params = ['only_yearly']
    error_message = 'Чистые активы меньше 0'

    def validate(self) -> ScoringResult:
        quarters = self.request.client.accounting_report.get_quarters()
        for quarter in quarters:
            if quarter.no_data:
                continue
            if self.only_yearly and not quarter.is_yearly():
                continue
            value = quarter.get_clear_actives()
            if value < 0:
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class HasContractsScoring(CountContractsScoring):
    full_name = 'Нету исполненых контрактов'
    min = 1


@add_scoring
class HasNalogDebts(ScoringItem):
    """
    Проверка что отсутствует задолженоость и вовремя предоставлялась отчетность
    """
    full_name = 'Проверка что отсутствует задолженоость и вовремя предоставлялась ' \
                'отчетность'
    error_message = 'Имеет задолженность по налогам и/или не предоставлял налоговую ' \
                    'отчетность более года'

    def validate(self) -> ScoringResult:
        if NalogRu().is_nalog_debts(self.request.client.inn):
            return ScoringResult(self.get_error_message())
        else:
            return ScoringResult()


@add_scoring
class HasSimilarContracts(ScoringItem):
    full_name = 'Отсутствие опыта выполнения сопоставимых по сумме контрактов'
    error_message = 'Отсутствие опыта выполнения сопоставимых по сумме контрактов'
    percent = 60
    count = 1
    sum_count = 0
    last_contracts = False
    scoring_params = ['percent', 'count', 'last_contracts', 'sum_count']
    date_format = '%Y-%m-%dT%H:%M:%S'

    def get_finished_contracts(self):
        contracts = ContractsLogic(self.request.client).get_finished_contracts()
        if self.last_contracts:
            time_point = timezone.now() - datetime.timedelta(days=1095)
            contracts = list(filter(
                lambda x: datetime.datetime.strptime(
                    x.end_date,
                    self.date_format,
                ) >= time_point,
                contracts
            ))
        return contracts

    def date_from_string(self, s):
        return datetime.datetime.strptime(s, self.date_format)

    def filter(self, obj, start_date, end_date):
        temp_start_date = self.date_from_string(obj.start_date)
        temp_end_date = self.date_from_string(obj.end_date)
        return not ((temp_start_date > end_date) or
                    (temp_end_date < start_date))

    def validate_for_sum_count(self):
        finished_contracts = self.get_finished_contracts()
        finished_contracts = sorted(
            finished_contracts,
            key=lambda x: x.price
        )
        for index, contract in enumerate(finished_contracts):
            start_date = self.date_from_string(contract.start_date)
            end_date = self.date_from_string(contract.end_date)
            temp = list(filter(
                lambda x: self.filter(x, start_date, end_date),
                finished_contracts
            ))
            if len(temp) > self.sum_count:
                temp = temp[:self.sum_count]
            temp = [float(i.price) for i in temp if i.price]
            if sum(temp) >= self.amount:
                return ScoringResult()
        return ScoringResult(errors=self.get_error_message())

    @cached_property
    def amount(self):
        return float(self.request.required_amount) * (self.percent / 100)

    def validate_for_count(self) -> ScoringResult:
        finished_contracts = self.get_finished_contracts()
        similar = 0
        for contract in finished_contracts:
            contract_price = getattr(contract, 'price', 0)
            if float(contract_price) > self.amount:
                similar += 1

                if similar >= self.count:
                    return ScoringResult()

        return ScoringResult(self.get_error_message())

    def validate(self) -> ScoringResult:
        if self.sum_count:
            return self.validate_for_sum_count()
        return self.validate_for_count()


@add_scoring
class InBankBlackList(ScoringItem):
    """
    Проверка, что ИНН Заказчика (Поле «ИНН заказчика» в заявке) и ИНН исполнителя
    (Поле «ИНН» в Анкете клиента) в заявке не находятся в черном списке банка
    """
    full_name = 'Проверка, что ИНН Заказчика в заявке не находятся в черном списке банка'
    error_message = 'Значение ИНН находится в стоп-листе банка'

    def banks_stop_list_enabled(self):
        return System.get_setting('global_stop_inn')

    def inns_in_stop_lists(self, inns):
        self.bank.black_list.filter(inn__in=inns).exists()

    def validate(self) -> ScoringResult:
        if not self.banks_stop_list_enabled():
            return ScoringResult()
        inn = [
            self.request.tender.beneficiary_inn,
            self.request.client.inn,
        ]
        if self.inns_in_stop_lists(inn):
            return ScoringResult(self.get_error_message())
        else:
            return ScoringResult()


@add_scoring
class InBlackListScoring(ScoringItem):
    """
    Проверка на отсутствие в черном списке банка
    """
    full_name = 'Проверка на отсутствие в черном списке банка'
    error_message = 'Отказ Службы Безопасности'

    def validate(self) -> ScoringResult:
        inn = [
            self.request.client.inn,
        ]
        count = self.bank.black_list.filter(inn__in=inn).count()
        if count > 0:
            return ScoringResult(self.get_error_message())
        else:
            return ScoringResult()


@add_scoring
class InMSPRegistryScoring(ScoringItem):
    """ Компания не входит в реестр малого и среднего
    предпринимательства - это стоп-фактор """
    full_name = 'Компания не входит в реестр малого и среднего предпринимательства '
    error_message = "Отсутсвует в едином реестре субъетов малого и среднего " \
                    "предпренимательства"

    def validate(self) -> ScoringResult:
        result = ConclusionsLogic.get_conclusion_result(
            client=self.request.client,
            conclusion=RMSPConclusion
        )
        if not result.result:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


class InterPromBankScoring(ScoringItem):
    disable_for_loans = True

    def validate(self) -> ScoringResult:
        # TODO: реализовать
        pass


@add_scoring
class InTerroristListScoring(ScoringItem):
    full_name = 'Генеральный директор найден в перечне террористов и ' \
                'экстремистов (действующие)'
    error_message = 'Генеральный директор найден в перечне террористов и ' \
                    'экстремистов (действующие)'

    def validate(self) -> ScoringResult:
        result = ConclusionsLogic.get_conclusion_result(
            client=self.request.client,
            conclusion=InTerroristListConclusion
        )
        if not result.result:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class IsBankrotScoring(ScoringItem):
    """ К организации применяется процедура банкротства. """
    full_name = 'К организации применяется процедура банкротства'
    error_message = 'К организации применяется процедура банкротства'

    def validate(self) -> ScoringResult:
        result = ConclusionsLogic.get_conclusion_result(
            client=self.request.client,
            conclusion=IsBankrotConclusion
        )
        if not result.result:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class IsDisqualifiedPerson(ScoringItem):
    """ Проверка по списку "Дисквалифицированных лиц" """
    full_name = 'Проверка по списку "Дисквалифицированных лиц"'
    error_message = "Компания находится в реестре дисквалифицированных лиц"

    def validate(self) -> ScoringResult:
        result = ConclusionsLogic.get_conclusion_result(
            client=self.request.client,
            conclusion=DisqualifiedPersonConclusion
        )
        if not result.result:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class IsUnfairSupplierScoring(ScoringItem):
    """ Проверка по реестру недобросовестных поставщиков """
    full_name = 'Проверка по реестру недобросовестных поставщиков'
    error_message = 'Компания находится в реестре недобросовестных поставщиков'

    def validate(self) -> ScoringResult:
        api = ParsersApi()
        validation_result = api.zakupki.check_rnp(self.request.client.profile.reg_inn)
        include_date = None

        if isinstance(validation_result, dict):
            if 'include_date' in validation_result:
                include_date = validation_result['include_date']
                include_date = datetime.datetime.strptime(
                    include_date,
                    '%Y-%m-%dT%H:%M:%S'
                ).date()
            validation_result = validation_result['is_in_rnp']
        if validation_result:
            return ScoringResult(
                self.get_error_message() + ' (Дата включения: {include_date})'.format(
                    include_date=include_date
                ))
        return ScoringResult()


@add_scoring
class NalogDebtScoring(ScoringItem):
    full_name = 'Компания имеет задолженность по уплате налогов'
    error_message = 'Компания имеет задолженность по уплате налогов ' \
                    '(свыше 1000 р) и/или не представляющая налоговую ' \
                    'отчетность более года'

    def validate(self) -> ScoringResult:
        # только для юр лиц
        if len(self.request.client.profile.reg_inn) != 10:
            return ScoringResult()

        result = ConclusionsLogic.get_conclusion_result(
            client=self.request.client,
            conclusion=HasArrearsOnPaymentOfTaxesConclusion
        )

        if result.result:
            return ScoringResult()
        return ScoringResult(self.get_error_message())


@add_scoring
class NalogStatusScoring(ScoringItem):
    full_name = 'у генерального директора имеются приостановленные счета'
    error_message = 'у генерального директора имеются приостановленные счета'

    def validate(self) -> ScoringResult:
        result = ConclusionsLogic.get_conclusion_result(
            client=self.request.client,
            conclusion=DecisionToSuspendConclusion
        )
        if not result.result:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class NationalityNaturalPersonsScoring(ScoringItem):
    """ Проверка что у бенефициара имеется российское гражданство """
    full_name = 'Проверка что у бенефициара имеется российское гражданство'
    error_message = 'Бенефициар не имеет российское гражданство'

    def validate(self) -> ScoringResult:
        beneficiaries = self.profile.profilepartnerindividual_set.filter(
            share__gt=0
        )
        for ben in beneficiaries:
            if ben.citizenship != 'Россия':
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class NegativeQuartersValueScoring(ScoringItem):
    """ Проверка что указанные коды имеют положительное значение """
    full_name = 'Проверка что указанные коды имеют положительное значение'
    codes = [2400]
    quarters = ['last', 'last_year']
    quarters_choices = ['last', 'last_year']
    scoring_params = ['codes', 'quarters']
    error_message = 'В одном из двух столбцов заполненной бухгалтерской ' \
                    'отчётности строчка 2400 имеет отрицательное значение.'

    def has_negative_value(self, code):
        quarters = self.request.client.accounting_report.get_quarters()
        year_quarter = quarters[1]
        if 'last_year' in self.quarters:
            if year_quarter.is_yearly() and not year_quarter.no_data:
                if year_quarter.get_value(code) < 0 and year_quarter.is_need:
                    return True
        if 'last' in self.quarters:
            quarter = quarters[0]
            if quarter.get_value(code) < 0 and quarter.is_need:
                return True
        return False

    def validate(self) -> ScoringResult:
        for code in self.codes:
            if self.has_negative_value(code):
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class NotActivePassportScoring(ScoringItem):
    full_name = 'у генерального директора недействительный паспорт'
    error_message = 'у генерального директора недействительный паспорт'

    def validate(self) -> ScoringResult:
        result = ConclusionsLogic.get_conclusion_result(
            client=self.request.client,
            conclusion=CheckPassportConclusion
        )
        if not result.result:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class OgrnScoring(ScoringItem):
    full_name = 'С даты регистрации в ЕГРЮЛ качестве юридического лица ' \
                'должно пройти не менее'
    value = 0
    scoring_params = ['value']

    def get_error_message(self):
        if not self.error_message:
            return 'С даты регистрации в ЕГРЮЛ качестве юридического лица ' \
                   'должно пройти не менее %s дней' % self.value
        return self.error_message

    def validate(self) -> ScoringResult:
        if self.request.client.profile.reg_state_date:
            reg_state_date = self.request.client.profile.reg_state_date
            diff = (timezone.now().date() - reg_state_date).days
            if diff < int(self.value):
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class OKPD2Scoring(ScoringItem):
    full_name = 'Банк не принимает конкурсы с указанным ОКПД2'
    codes = []
    scoring_params = ['codes']
    error_message = 'Банк не принимает конкурсы с указанным ОКПД2'

    def validate(self) -> ScoringResult:
        if self.request.tender.okpd2:
            if self.request.tender.okpd2 in self.codes:
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class OKVEDScoring(FieldEqualScoring):
    full_name = 'Недопустимые виды деятельности'
    pattern = ''
    scoring_params = ['pattern']
    error_message = 'Недопустимые виды деятельности'

    def validate(self) -> ScoringResult:
        if self.pattern:
            for activity in self.profile.kindofactivity_set.all():
                if re.search(r'^(%s)' % self.pattern, activity.value):
                    return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class PassportScoring(NotActivePassportScoring):
    """
        Проверка действительности паспорта единоличного исполнительного органа
    """
    full_name = 'Проверка действительности паспорта единоличного ' \
                'исполнительного органа'
    error_message = 'Паспорт единоличного исполнительного органа не ' \
                    'действителен'


@add_scoring
class QuartersValueScoring(ScoringItem):
    full_name = 'QuartersValueScoring'
    code = None
    quarter = None
    quarter_choices = ['last', 'last_year', 'prev_year']
    min = None
    max = None
    scoring_params = ['code', 'quarter', 'min', 'max']

    def validate(self) -> ScoringResult:
        allowed_quarters = ['last', 'last_year', 'prev_year']
        if self.quarter not in allowed_quarters:
            return ScoringResult("Квартал должен принимать значение в ")
        if self.quarter == 'last':
            params = Quarter.manager_accounting_report.get_last_closed_quarter_and_year()
            quarter = self.client.accounting_report.get_quarter_by_params(params)
        if self.quarter == 'last_year':
            params = Quarter.manager_accounting_report.get_last_year_quarter()
            quarter = self.client.accounting_report.get_quarter_by_params(params)
        if self.quarter == 'prev_year':
            params = Quarter.manager_accounting_report.get_previous_year_quarter()
            quarter = self.client.accounting_report.get_quarter_by_params(params)
        if quarter:
            if not quarter.is_need:
                return ScoringResult()
            value = quarter.get_value(self.code)
            valid = True
            if self.min and valid:
                valid = value > float(self.min)
            if self.max and valid:
                valid = value <= float(self.max)

            if not valid:
                return ScoringResult(self.get_error_message())
            return ScoringResult()
        return ScoringResult('Не найден квартал с нужными параметрами')


@add_scoring
class RegexFieldsMatch(FieldEqualScoring):
    full_name = 'Первые два символа ИНН равны недопустимым символам'
    fields = ['request.client.inn']
    pattern = ''
    scoring_params = ['fields', 'pattern']
    error_message = 'Первые два символа ИНН равны недопустимым символам'

    def validate(self) -> ScoringResult:
        if self.pattern:
            for field in self.fields:
                value = self.get_value(field)
                if value and re.match('^%s' % self.pattern, value):
                    return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class RegexFieldsNotMatch(FieldEqualScoring):
    fields = ['request.client.inn']
    pattern = ''
    scoring_params = ['fields', 'pattern']
    error_message = 'Первые два символа ИНН не входят в перечень допустимых ' \
                    'символов'
    full_name = 'Первые два символа ИНН не входят в перечень допустимых ' \
                'символов'

    def validate(self) -> ScoringResult:
        if self.pattern:
            for field in self.fields:
                if re.findall('^%s' % self.pattern, self.get_value(field)):
                    return ScoringResult()
        return ScoringResult(self.get_error_message())


@add_scoring
class RIBTHScoring(ScoringItem):
    full_name = 'RIBTHScoring'
    scoring_params = ['minimal_scoring']
    minimal_scoring = 15
    disable_for_loans = True

    def get_error_message(self):
        if not self.error_message:
            return "У клиента меньше %s баллов по скорингу ТХ" % self.minimal_scoring
        return super().get_error_message()

    def validate(self) -> ScoringResult:
        helper = RIBConclusionForTH(self.request, print_form=None)
        if helper.get_result() < self.minimal_scoring:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class SFAllowedPlacementsScoring(ScoringItem):
    full_name = 'Площадка, с которой сотрудничает МФО, не из списка'
    error_message = 'Площадка, с которой сотрудничает МФО, не из списка ' \
                    '(Сбербанк-АСТ - 44ФЗ и 223ФЗ, АО «ЕЭТП» – 44ФЗ, ' \
                    'ЭТП ММВБ – 44ФЗ)'
    scoring_params = ['placements']
    placements = [
        PlacementPlace.CODE_EETP,
        PlacementPlace.CODE_SBAST,
        PlacementPlace.CODE_MMVB,
        PlacementPlace.CODE_ZAKAZRF,
        PlacementPlace.CODE_ETPRF,
        PlacementPlace.CODE_AVTODOR
    ]

    def validate(self) -> ScoringResult:
        if self.request.tender.placement.code in self.placements:
            return ScoringResult()
        return ScoringResult(self.get_error_message())


@add_scoring
class SFSumProfit(ScoringItem):
    full_name = 'Сумма займа превышает 20% от суммы выручки за последний ' \
                'отчетный год'
    error_message = 'Сумма займа превышает 20% от суммы выручки за последний ' \
                    'отчетный год'

    def validate(self) -> ScoringResult:
        quarter = self.request.client.accounting_report.get_year_quarter()
        if quarter:
            value = quarter.get_value(2110) * 1000
            if self.request.required_amount > value * 0.2:
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class SGBFinanceScoring(ScoringItem):
    disable_for_loans = True
    full_name = 'Величина чистых активов за последний завершенный квартал ' \
                'меньше уставного капитала'
    error_message = 'Величина чистых активов за последний завершенный квартал' \
                    ' меньше уставного капитала или отрицательная величина.'

    def validate(self) -> ScoringResult:
        quarter = self.request.client.accounting_report.get_quarters()[0]
        value = quarter.get_value(1600) - \
                (quarter.get_value(1400) +
                 quarter.get_value(1500) -
                 quarter.get_value(1530))
        tax_system = self.client.profile.tax_system
        if self.client.is_organization and tax_system == TaxationType.TYPE_OSN:
            if value <= self.profile.authorized_capital_announced / 1000:
                return ScoringResult(self.get_error_message())
            else:
                return ScoringResult()
        else:
            if value < 0:
                return ScoringResult(self.get_error_message())
            else:
                return ScoringResult()


@add_scoring
class SGBHasContractsScoring(HasContractsScoring):
    full_name = 'SGBHasContractsScoring'
    disable_for_loans = True
    error_message = 'Нет исполненных государственные контракты в качестве ' \
                    'генподрядчика в рамках законов №94-ФЗ, ' \
                    '44-ФЗ, 223-ФЗ или 185-ФЗ'


@add_scoring
class SumBGScoring(ScoringItem):
    """ Проверка размера требуемой суммы БГ меньше, чем лимит банка """
    full_name = 'Проверка размера требуемой суммы БГ меньше, чем лимит банка'
    error_message = 'Требуемая сумма БГ превышает допустимый размер'
    error_message_limit_for_client = 'Сумма выданных БГ на клиента превышена'

    @property
    def sum_bg(self):
        return self.bank.bank_integration.sum_bg(self.request)

    def validate(self) -> ScoringResult:
        limit = self.bank.bank_integration.bank_amount_limit(self.request)

        if self.bank.bank_integration.request_limit(self.request) > limit:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class SumScoring(ScoringItem):
    full_name = 'SumScoring'
    amount = 0
    limit = 0
    scoring_params = ['amount', 'limit']

    def get_error_message(self):
        return '%s больше, чем %s' % (self.amount, self.limit)

    def validate(self) -> ScoringResult:
        if get_value_by_path(self, self.amount) > self.limit:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class TenderHasStopWords(ScoringItem):
    full_name = 'TenderHasStopWords'
    stop_words = []
    scoring_params = ['stop_words']

    def validate(self) -> ScoringResult:
        for stop_word in self.stop_words:
            if re.findall(stop_word, self.request.tender.subject):
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class YearBOScoring(ScoringItem):
    full_name = 'Отсутствует годовая бухгалтерская отчетность'
    error_message = 'Отсутствует годовая бухгалтерская отчетность'
    value = 365
    scoring_params = ['value']

    def validate(self) -> ScoringResult:
        year_quarter = self.request.client.accounting_report.get_year_quarter()
        delta = (datetime.datetime.now() - self.profile.reg_state_date).days
        if delta > self.value:
            if year_quarter and year_quarter.not_empty():
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class ActualCompanyStateScoring(ScoringItem):
    """ Проверка текущего состояния компания"""

    def validate(self) -> ScoringResult:
        egrul_data = EgrulData.get_info(self.request.client.inn)
        if egrul_data:
            reason = egrul_data['section-terminated']['reason']
            if reason:
                return ScoringResult(self.get_error_message())

        return ScoringResult()


@add_scoring
class SPBExperienceScoring(ScoringItem):
    """ Проверка опыта компании """
    error_message = 'Опыт клиента не удовлетворяет требованиям'

    def check_in_bank_regions(self, inn, kpp, regions):
        return check_in_regions(inn=inn, kpp=kpp, regions=regions)

    def validate(self) -> ScoringResult:
        banks_regions = [
            '47', '78, 98, 178', '77', '97', '99', '177', '199', '197', '777'
        ]
        diff_days = (
            timezone.now().date() - self.request.client.profile.reg_state_date
        ).days
        in_bank_regions = self.check_in_bank_regions(
            self.request.client.inn,
            self.request.client.kpp,
            banks_regions
        )
        year_quarter = self.client.accounting_report.get_year_quarter()
        if in_bank_regions:
            is_organization = self.request.client.is_organization
            tax_system = self.profile.tax_system

            if is_organization and tax_system == TaxationType.TYPE_OSN:
                has_year_quarter = year_quarter.not_empty()
                age_more_6_mounth = diff_days > (6 * 30)
                if age_more_6_mounth and has_year_quarter:
                    return ScoringResult()
                else:
                    return ScoringResult(self.get_error_message())
            else:
                return ScoringResult(self.get_error_message())
        else:
            has_year_quarter = year_quarter.not_empty()
            diff = (timezone.now().date() - self.client.profile.reg_state_date).days
            age_more_12_mounth = diff > (12 * 30)
            if age_more_12_mounth and has_year_quarter:
                return ScoringResult()

        return ScoringResult(self.get_error_message())


@add_scoring
class StopRegionsScoring(ScoringItem):
    regions = ['91', '05', '20', '06', '15', '07', '92', '09', '26']
    scoring_params = ['regions']

    def validate(self) -> ScoringResult:
        result = check_in_regions(
            inn=self.client.inn,
            kpp=self.client.kpp,
            regions=self.regions
        )
        if result:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class SPBValidatePassportsScoring(ScoringItem):

    def validate(self) -> ScoringResult:
        passports = self.get_passports()

        total_result = True
        for passport in passports:
            result = check_passport(*passport)
            total_result = total_result and (result is not None and result is not True)
        if total_result:
            return ScoringResult()
        else:
            return ScoringResult(self.get_error_message())

    def get_passports(self):
        general_director = self.request.client.profile.general_director
        passports = [
            [general_director.passport.series, general_director.passport.number]
        ]
        for person in self.profile.profilepartnerindividual_set.filter(share__gte=0):
            passports.append([person.passport.series, person.passport.number])
        return passports


@add_scoring
class SPBClientRatingScoring(ScoringItem):
    scoring_params = [
        'finance_state', 'risk_level', 'category', 'score1', 'score2',
        'score_operator'
    ]
    finance_state = []
    finance_state_choices = ['плохое', 'среднее', 'хорошее']
    risk_level = []
    risk_level_choices = [
        'Высокий', 'Допустимый', 'Несущественный', 'Минимальный'
    ]
    category = []
    category_choices = ['D', 'C2', 'C1', 'B2', 'B1', 'B', 'A2', 'A1']
    score1 = 0
    score2 = 0
    score_operator = ''
    score_operator_choices = ['=', '!=', '>', '<', '>=', '<=', 'BETWEEN']
    error_message = 'Финансовое состояние клиента не соответствует требования'

    @cached_property
    def client_rating(self):
        helper = get_client_rating_calculator(self.request)
        return ClientRatingTranslator.translate(helper.calculated_score)

    def validate_finance_state(self):
        if self.finance_state:
            return self.client_rating.finance_state in self.finance_state

    def validate_risk_level(self):
        if self.risk_level:
            return self.client_rating.level_risk in self.risk_level

    def validate_category(self):
        if self.category:
            return self.client_rating.category in self.category

    def validate_score(self):
        if self.score_operator not in self.score_operator_choices:
            return True
        value = self.client_rating.score
        score1 = float(self.score1)
        if self.score_operator == '=':
            return value == score1

        if self.score_operator == '!=':
            return value != score1

        if self.score_operator == '>=':
            return value >= score1

        if self.score_operator == '<=':
            return value <= score1

        if self.score_operator == '>':
            return value > score1

        if self.score_operator == '<':
            return value < score1

        if self.score_operator == 'BETWEEN':
            return score1 <= value <= float(self.score2)

        return True

    def validate(self) -> ScoringResult:
        for validate in [
            'validate_finance_state',
            'validate_risk_level',
            'validate_category',
            'validate_score',
        ]:
            if getattr(self, validate)() is False:
                return ScoringResult(self.get_error_message())

        return ScoringResult()


@add_scoring
class IsIndividualEntrepreneur(ScoringItem):
    error_message = 'Является Индивидуальным предпринимателем'

    def validate(self) -> ScoringResult:
        if not self.client.is_individual_entrepreneur:
            return ScoringResult()
        else:
            return ScoringResult(self.get_error_message())


@add_scoring
class CountContractsForLaw(ScoringItem):
    error_message = 'Отсутствует опыт исполненных гос. контрактов'
    laws = []
    laws_choices = generate_choices((('44', '44-ФЗ'), ('223', '223-ФЗ')))
    min = 0
    scoring_params = ['laws', 'min']

    @cached_property
    def contracts(self):
        for _ in range(3):
            try:
                api = ClearsSpendingApi()
                return api.get_contracts_info(
                    self.request.client.profile.reg_inn,
                    self.request.client.profile.reg_kpp)
            except Exception as error:
                return []

    def validate(self) -> ScoringResult:
        result = len(list(filter(
            lambda x: x['fz'] in self.laws,
            self.contracts
        ))) >= self.min
        if result:
            return ScoringResult()
        else:
            return ScoringResult(self.get_error_message())


@add_scoring
class OrganizationFormScoring(ScoringItem):
    error_message = 'Форма правления не удовлетворяет требованиям'
    organization_forms = []
    organization_forms_choices = generate_choices(
        list(OrganizationForm.CHOICES) + [('ip', 'ИП')]
    )
    scoring_params = ['organization_forms']

    def validate(self) -> ScoringResult:
        result = False
        if 'ip' in self.organization_forms:
            result = self.request.client.is_individual_entrepreneur
        for form in self.organization_forms:
            if form == self.request.client.profile.organization_form:
                result = True
        if result:
            return ScoringResult()
        else:
            return ScoringResult(self.get_error_message())


@add_scoring
class SPBResidentScoring(ScoringItem):
    error_message = 'Директор или учередители с долей более 25% не являются ' \
                    'резидентами РФ'

    def validate(self) -> ScoringResult:
        result = True
        for el in self.request.client.profile.profilepartnerindividual_set.filter(
            Q(is_general_director=True) | Q(share__gte=25)
        ):
            if not el.resident:
                result = False
        return ScoringResult() if result else ScoringResult(self.get_error_message())


@add_scoring
class SPBNegativeNetAssetsLastQuarter(ScoringItem):
    error_message = 'Убыток за последнюю дату или год'

    @cached_property
    def last_quarters(self):
        return self.request.client.accounting_report.get_quarters()[:2]

    def net_assets_last_quarter(self, quarter):
        try:
            return quarter.get_value(1600) - (
                quarter.get_value(1400) +
                quarter.get_value(1500) -
                quarter.get_value(1530))
        except ZeroDivisionError:
            return 0

    def validate(self) -> ScoringResult:
        for quarter in self.last_quarters:
            if self.net_assets_last_quarter(quarter) < 0:
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class ManyRegistrationAddressScoring(ScoringItem):
    error_message = 'Юридический адрес является адресом массовой регистрации'

    def validate(self) -> ScoringResult:
        result = ConclusionsLogic.get_conclusion_result(
            client=self.request.client,
            conclusion=AddressOfManyRegistrationsConclusion
        )
        if not result.result:
            return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class SPBCheckBalance(ScoringItem):
    error_message = 'Наличия арбитражных производств на дату рассмотрения заявки ' \
                    'Принципала в общей сумме, превышающей 25% от валюты баланса ' \
                    'Принципала на последнюю отчетную дату '

    @cached_property
    def last_quarter_balance(self):
        return self.request.client.accounting_report.get_quarters()[0].get_value(1600)

    @cached_property
    def sum_court_arbitration(self):
        api = RusProfile()
        data = api.get_court_arbitration(
            self.request.client.profile.reg_inn,
            common_type=1,
            level='not_finished',
        )
        return sum(
            [float(i['sum'].replace(',', '.')) for i in data if i and i.get('sum')]
        )

    def validate(self) -> ScoringResult:
        if self.sum_court_arbitration <= (self.last_quarter_balance * 250):
            return ScoringResult()
        else:
            return ScoringResult(self.get_error_message())


class CheckCourtBalance(ScoringItem):
    percent = 25
    scoring_params = ['percent']

    def get_error_message(self):
        return 'Наличия арбитражных производств на дату рассмотрения заявки ' \
               'Принципала в общей сумме, превышающей %s% от валюты баланса ' \
               'Принципала на последнюю отчетную дату' % (self.percent)

    @cached_property
    def last_quarter_balance(self):
        return self.request.client.accounting_report.get_quarters()[0].get_value(1600)

    @cached_property
    def sum_court_arbitration(self):
        api = RusProfile()
        data = api.get_court_arbitration(
            self.request.client.profile.reg_inn,
            common_type=1,
            level='not_finished',
        )
        return sum(
            [float(i['sum'].replace(',', '.')) for i in data if i and i.get('sum')]
        )

    def validate(self) -> ScoringResult:
        if self.sum_court_arbitration <= (self.last_quarter_balance * self.percent * 10):
            return ScoringResult()
        else:
            return ScoringResult(self.get_error_message())


@add_scoring
class FSSPScoring(ScoringItem):
    limit = 300000
    scoring_params = ['limit']

    def get_fssp_sum(self):
        api = ZaChestnyiBiznesApi()
        data = api.method('fssp', self.request.client.profile.reg_inn)
        if data and isinstance(data, dict):
            if data['status'] == '200':
                data = data['body']
                return sum(map(
                    lambda x: float(x['ОстатокДолга']),
                    data
                ))
            if data['status'] == '235':
                return 0
        return None

    def validate(self) -> ScoringResult:
        fssp_sum = self.get_fssp_sum()
        if fssp_sum is None:
            return ScoringResult(errors='Произошла ошибка при запросе данных ФССП')
        if fssp_sum < self.limit:
            return ScoringResult()
        else:
            return ScoringResult(self.get_error_message())


@add_scoring
class CheckCommission(ScoringItem):
    operator = '>'
    value = 0
    scoring_params = ['operator', 'value']
    operation_choices = ['=', '!=', '>', '<', '>=', '<=']

    def get_error_message(self):
        return self.error_message

    def validate(self) -> ScoringResult:
        value = json.loads(
            self.request.banks_commissions
        ).get(self.bank.code, {}).get('commission')

        if value is None:
            return ScoringResult(errors='Не расчиталась комиссия')

        value = float(value)
        self.value = float(self.value)

        if self.operator == '=':
            return ScoringResult() if value == self.value else ScoringResult(
                self.get_error_message()
            )

        if self.operator == '!=':
            return ScoringResult() if value != self.value else ScoringResult(
                self.get_error_message()
            )

        if self.operator == '>=':
            return ScoringResult() if value >= self.value else ScoringResult(
                self.get_error_message()
            )

        if self.operator == '<=':
            return ScoringResult() if value <= self.value else ScoringResult(
                self.get_error_message()
            )

        if self.operator == '>':
            return ScoringResult() if value > self.value else ScoringResult(
                self.get_error_message()
            )

        if self.operator == '<':
            return ScoringResult() if value < self.value else ScoringResult(
                self.get_error_message()
            )

        return ScoringResult() if value == self.value else ScoringResult(
            self.get_error_message()
        )


@add_scoring
class InbankSumScoring(ScoringItem):
    error_message = 'Сумма БГ превышает допустимую'
    YEAR_DAYS = 366

    @property
    def revenue_mul_1_2(self):
        client = self.request.client
        return client.accounting_report.get_year_quarter().get_value(
            2110
        ) * 1.2 * 1000

    @property
    def revenue_mul_2(self):
        client = self.request.client
        return client.accounting_report.get_year_quarter().get_value(
            2110
        ) * 2 * 1000

    @cached_property
    def interval(self):
        self.request: Request
        if self.request.term_of_work_from and self.request.term_of_work_to:
            return (self.request.term_of_work_to - self.request.term_of_work_from).days
        return 0

    @cached_property
    def contract_amount_division_interval_year(self):
        amount = float(self.request.tender.price)
        interval = self.interval
        if interval < self.YEAR_DAYS:
            return amount
        else:
            return amount / (interval / self.YEAR_DAYS)

    def validate(self) -> ScoringResult:
        if self.request.required_amount > 3000000:
            amount = self.contract_amount_division_interval_year

            if Target.EXECUTION in self.request.targets and amount > self.revenue_mul_1_2:
                return ScoringResult(self.get_error_message())
            if Target.PARTICIPANT in self.request.targets and amount > self.revenue_mul_2:
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class AlfaSumScoring(ScoringItem):
    error_message = 'Сумма БГ превышает допустимую'
    YEAR_DAYS = 366

    @property
    def revenue_mul_1_3(self):
        client = self.request.client
        return client.accounting_report.get_year_quarter().get_value(
            2110
        ) * 1.3 * 1000

    @cached_property
    def interval(self):
        self.request: Request
        if self.request.term_of_work_from and self.request.term_of_work_to:
            return (self.request.term_of_work_to - self.request.term_of_work_from).days
        return 0

    @cached_property
    def contract_amount_division_interval_year(self):
        amount = float(self.request.tender.price)
        interval = self.interval
        if interval < self.YEAR_DAYS:
            return amount
        else:
            return amount / (interval / self.YEAR_DAYS)

    def validate(self) -> ScoringResult:
        if self.request.required_amount > 3000000:
            amount = self.contract_amount_division_interval_year

            if amount > self.revenue_mul_1_3:
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class SPBSimilarContracts(ScoringItem):
    full_name = "Проверка количества контрактов для СПБ"
    min = 1
    scoring_params = ['min']
    disable_for_loans = True

    def validate(self) -> ScoringResult:
        helper = SPBContractsInfo(self.request)
        if len(helper.similar_contracts) < int(self.min):
            ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class CheckRZDCustomer(ScoringItem):
    full_name = 'Бенефициар закупки не относится к РЖД'
    inns = [
        '1435073060', '2221055435', '7606028688', '3808218300', '5047066172',
        '278168302', '278168302', '5007077604', '7708669867', '7701527126',
        '7708737517', '7708737490', '7722648033', '1516613186', '7717596862',
        '5022067103', '5257111223', '3444130430', '6315376946', '3525183007',
        '3808004442', '7808032704', '6659209750', '7701660262', '3666082428',
        '3808060983', '3907027095', '2466083905', '5257047955', '5407212431',
        '3666082428', '6311047066', '7826720069', '6450042805', '2721086167',
        '7451088836', '7536043552', '7708155798', '7715729877', '7708639622',
        '7506002527', '7536123166', '7536003172', '7708645993', '3448049540',
        '7708102193', '7709859170', '4029032450', '4707005410', '3905614482',
        '2460069630', '7708182801', '7709219099', '2309121212', '4205048280',
        '7723791660', '4024016776', '7720579828', '7709733628', '6950104591',
        '3307001803', '6513012267', '5257004599', '7709752846', '7707424367',
        '5409231687', '5505034152', '7701414235', '9701104646', '9701104660',
        '9701104653', '7717130165', '5042060280', '5906029110', '277057744',
        '4516009163', '4707025208', '3664108409', '6501243453', '7816055208',
        '2721068560', '7707616615', '7703715816', '7708587205', '7708587910',
        '7708542765', '6312098345', '6452950802', '7839330845', '7708609931',
        '6162051289', '2465080066', '7840389730', '7726389076', '7604192971',
        '2511006824', '4707032950', '7708063900', '8610006907', '7718182166',
        '5190179176', '7327012462', '6608001305', '7718200111', '7708709686',
        '7708166126', '7717287173', '7708166126', '6311032158', '3911011203',
        '2538092524', '5407193789', '7716523950', '3662231260', '7723305871',
        '4658975', '7451316641', '8904042048'
    ]

    def validate(self) -> ScoringResult:
        if self.request.tender.beneficiary_inn in self.inns:
            return ScoringResult()
        return ScoringResult(self.get_error_message())


@add_scoring
class IsOrgReorganization(ScoringItem):
    full_name = "Организация находится на стадии реорганизации"

    def is_organization_on_reorganization(self):
        api = ZaChestnyiBiznesApi()
        data = api.method('card', self.request.client.profile.reg_inn)
        if data and isinstance(data, dict):
            if data['status'] == '200':
                data = data['body']['docs'][0]
                if ("реорганизации" in data.get('Активность', '')):
                    return True
        return False

    def validate(self) -> ScoringResult:
        result = self.is_organization_on_reorganization()
        if result:
            return ScoringResult(self.get_error_message())
        else:
            return ScoringResult()


@add_scoring
class HasPersonsBankrupt(ScoringItem):
    error_message = "Учредитель банкрот"

    def validate(self) -> ScoringResult:
        for person in self.client.profile.all_beneficiaries:
            validation_result = SearchTenderhelpApi().company_is_bankrupt(
                person['inn']
            )
            if validation_result:
                return ScoringResult(self.get_error_message())
        return ScoringResult()


@add_scoring
class IsLiquidationScoring(ScoringItem):
    error_message = 'Компания в стадии ликвидации'

    def validate(self) -> ScoringResult:
        helper = ZaChestnyiBiznesApi()
        result = helper.method('card', self.client.profile.reg_inn)
        if 'в стадии ликвидации' in result.get('body').get('Активность', '').lower():
            return ScoringResult(self.get_error_message())
        return ScoringResult()
