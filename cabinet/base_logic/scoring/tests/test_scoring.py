from unittest import TestCase

import pytest
from django.core.cache import cache

from bank_guarantee.models import Request
from base_request.models import RequestTender
from cabinet.base_logic.scoring.base import ScoringLogic, ScoringResult
from cabinet.base_logic.scoring.functions import (
    FailScoring, BGSumLessContractSum, ConditionalScoring,
    CountContractsScoring, RegexFieldsMatch, FieldEqualScoring,
    AllowedTenderLawsScoring, TrueScoring, HasSimilarContracts, InBankBlackList
)
from cabinet.constants.constants import FederalLaw, Target
from clients.models import Bank, BankSettings, Client
from questionnaire.models import Profile
from external_api.parsers_tenderhelp import Contract44FZ
import datetime

@pytest.fixture()
def default_request():
    return Request(
        client=Client(
            profile=Profile(
                reg_inn='0527062463',
                reg_kpp='052701001',
            )
        ),
        interval=66,
        required_amount=10000,
        targets=[Target.EXECUTION],
        tender=RequestTender(
            federal_law=FederalLaw.LAW_44
        )
    )


class ScoringTestCase(TestCase):

    def test_load_class(self):
        class_name = 'TrueScoring'
        scoring_class = ScoringLogic.load_class(class_name)
        self.assertEqual(scoring_class.__name__, class_name)

    def test_simple_fail_scoring_result(self):
        fail_result = ScoringResult('error')
        self.assertEqual(fail_result.is_fail, True)
        self.assertEqual(fail_result.is_success, False)
        self.assertEqual(fail_result.get_errors(), ['error'])
        self.assertEqual(fail_result.get_first_error(), 'error')

    def test_simple_pass_scoring_result(self):
        pass_result = ScoringResult()
        self.assertEqual(pass_result.is_fail, False)
        self.assertEqual(pass_result.is_success, True)
        self.assertEqual(pass_result.get_errors(), [])
        self.assertEqual(pass_result.get_first_error(), None)

    def test_multiply_errors_scoring_result(self):
        errors = ['test1', 'test2']
        pass_result = ScoringResult(['test1', 'test2'])
        self.assertEqual(pass_result.is_fail, True)
        self.assertEqual(pass_result.is_success, False)
        self.assertEqual(pass_result.get_errors(), errors)
        self.assertEqual(pass_result.get_first_error(), 'test1')

    def test_bad_create_scoring_result(self):
        with self.assertRaises(ValueError):
            ScoringResult({1, 2})
        with self.assertRaises(ValueError):
            ScoringResult(True)
        with self.assertRaises(ValueError):
            ScoringResult(False)

    def test_simple_scoring(self):
        logic = ScoringLogic(Bank(), Request())
        result = logic.validate_rules([{
            'class': 'FailScoring',
            'active': True
        }])
        self.assertEqual(result.is_fail, True)


def test_true_scoring():
    f = TrueScoring(bank=Bank(), request=Request(), settings=dict())
    assert f.validate().is_success is True


def test_fail_scoring():
    f = FailScoring(bank=Bank(), request=Request(), settings=dict())
    assert f.validate().is_success is False


def test_bg_sum_less_contract_sum():
    request = Request(
        suggested_price_amount=100.00,
        required_amount=100.00,
    )
    f = BGSumLessContractSum(bank=Bank(), request=request, settings=dict())
    assert f.validate().is_success is True


def test_conditional_scoring():
    f = ConditionalScoring(bank=Bank(), request=Request(), settings=dict(
        if_conditionals=[{'class': "TrueScoring"}],
        then_conditionals=[{'class': 'TrueScoring'}],
    ))
    assert f.validate().is_success is True


def test_conditional_scoring2():
    f = ConditionalScoring(bank=Bank(), request=Request(), settings=dict(
        if_conditionals=[{'class': 'FailScoring'}],
        else_conditionals=[{'class': 'FailScoring'}],
    ))
    assert f.validate().is_fail is True


@pytest.mark.skip(reason="Логика изменилась, нужно переписать тест")
def test_count_contracts_scoring():
    client_inn = '0000000000'
    cache.set('contracts_%s' % client_inn,
              [{'state': 'EC'}, {'state': 'EC'}])
    request = Request(
        client=Client(inn=client_inn)
    )
    f = CountContractsScoring(bank=Bank(), request=request, settings=dict(
        min=1
    ))
    assert f.validate().is_success is True
    cache.delete('contracts_%s' % client_inn)


def test_regex_field_scoring():
    request = Request(
        tender=RequestTender(
            beneficiary_inn='051111'
        )
    )
    f1 = RegexFieldsMatch(bank=Bank(), request=request, settings={
        "fields": [
            "request.tender.beneficiary_inn"
        ],
        "pattern": "05|06|07|09|15|20|91|92"
    })
    assert f1.validate().result is False

    request.tender.beneficiary_inn = '213001001'
    f2 = RegexFieldsMatch(bank=Bank(), request=request, settings={
        "fields": [
            "request.tender.beneficiary_inn"
        ],
        "pattern": "05|06|07|09|15|20|91|92"
    })
    assert f1.validate().result is True


def test_interval():
    request = Request(
        interval=66
    )
    f1 = FieldEqualScoring(bank=Bank(), request=request, settings={
        "field": "request.interval",
        "operation": "<=",
        "value": 1140
    })
    assert f1.validate().result is True

    request = Request(
        interval=1200
    )
    f1 = FieldEqualScoring(bank=Bank(), request=request, settings={
        "field": "request.interval",
        "operation": "<=",
        "value": 1140
    })
    assert f1.validate().result is False


@pytest.mark.django_db
def test_common(initial_data_db):
    request = Request(
        tender=RequestTender(
            federal_law=FederalLaw.LAW_44
        )
    )
    scoring_logic = ScoringLogic(bank=Bank(
        settings=BankSettings(enable=True)
    ), request=request)
    scoring_logic = scoring_logic.check(use_common_rules=True)
    assert scoring_logic.result is True
    assert scoring_logic.is_fail is False
    assert scoring_logic.is_success is True


@pytest.mark.django_db
def test_validate_rules(initial_data_db):
    request = Request(
        client=Client(
            profile=Profile(
                reg_inn='0527062463',
                reg_kpp='052701001',
            )
        ),
        required_amount=10000,
        interval=66,
        targets=[Target.EXECUTION],
        tender=RequestTender(
            federal_law=FederalLaw.LAW_44
        )
    )
    l = ScoringLogic(bank=Bank(settings=BankSettings(enable=True)),
                     request=request)
    l = l.validate_rules([
        {
            "class": "FieldEqualScoring",
            "active": True,
            "error_message": "Срок БГ (дней) слишком большой",
            "field": "request.interval",
            "operation": "<=",
            "value": 1140
        },
        {
            "class": "GuaranteeTargetScoring",
            "active": True,
            "error_message": "Банк не принимает этот тип заявок",
            "targets": [
                Target.PARTICIPANT,
                Target.EXECUTION,
                Target.WARRANTY
            ]
        },
        {
            "class": "FieldEqualScoring",
            "active": True,
            "error_message": "Сумма БГ > 60 млн. руб., для индивидуального рассмотрения необходимо направить на почту письмо с номером заявки",
            "field": "request.required_amount",
            "value": 60000000,
            "operation": "<="
        },
        {
            "class": "RegexFieldsMatch",
            "active": True,
            "error_message": "Банк не работает с клиентами из данного региона",
            "fields": [
                "anketa.reg_inn"
            ],
            "pattern": "05|06|07|09|15|20|91|92"
        },
        {
            "class": "RegexFieldsMatch",
            "active": True,
            "error_message": "Банк не работает с клиентами из данного региона",
            "fields": [
                "anketa.reg_kpp"
            ],
            "pattern": "05|06|07|09|15|20|91|92"
        },
    ])
    assert l.errors == ['Банк не работает с клиентами из данного региона',
                        'Банк не работает с клиентами из данного региона']
    assert l.is_fail is True
    assert l.is_success is False


class TestScoringFunction(TestCase):
    pass

    # def test_beneficiars_age_scoring(self):
    #     pk_passport = 1234567894613
    #     request = Request(
    #         client=Client(
    #             profile=Profile()
    #         )
    #     )
    #     request.client.profile.profilepartnerindividual_set.add(
    #         ProfilePartnerIndividual(
    #             profile=request.client.profile,
    #             share=30.00,
    #             passport=PassportDetails(
    #                 id=pk_passport,
    #                 date_of_birth=datetime.datetime.now() - datetime.timedelta(days=365 * 20 + 100)
    #             )
    #         ),
    #     )
    #     for value, op in [(20, '='), (21, '!='), (20, '>='), (20, '<='), (21, '<'), (19, '>')]:
    #         f = BeneficiarsAgeScoring(
    #             bank=Bank(),
    #             request=request,
    #             settings={'value': value, 'operation': op}
    #         )
    #         print(request.client.profile.profilepartnerindividual_set.all().first().passport.date_of_birth)
    #         self.assertTrue(f.validate().is_success)
    #     PassportDetails.objects.get(pk=pk_passport).delete()


def test_allowed_tender_laws_scoring():
    request = Request(
        tender=RequestTender(
            federal_law=FederalLaw.LAW_44
        )
    )
    error_message = 'test error message'
    f1 = AllowedTenderLawsScoring(bank=Bank(), request=request, settings={
        "error_message": error_message,
        "laws": [
            FederalLaw.LAW_44,
            FederalLaw.LAW_223
        ]
    })
    assert f1.validate().result is True
    f2 = AllowedTenderLawsScoring(bank=Bank(), request=request, settings={
        "error_message": error_message,
        "laws": [
            FederalLaw.LAW_615,
        ]
    })
    r2 = f2.validate()
    assert r2.is_fail is True
    assert error_message in r2.errors


def test_field_equals_scoring(default_request):
    func = FieldEqualScoring(None, None, {})
    func.value = {'t': 'est'}
    assert func.get_error_message() == 'None = {"t": "est"}'

    assert FieldEqualScoring(None, default_request, {
        "error_message": "Инн не равен заданному `0527062463` != `0527062463`",
        "field": "profile.reg_inn",
        "operation": "!=",
        "value": '0527062463'
    }).validate().is_success is False

    assert FieldEqualScoring(None, default_request, {
        "error_message": "Инн не равен заданному `0527062463` != `0527062463`",
        "field": "request.required_amount",
        "operation": "=",
        "value": '10000'
    }).validate().is_success is True

    assert FieldEqualScoring(None, default_request, {
        "error_message": "Проверка операций сравнения 66 > 70",
        "field": "request.interval",
        "operation": ">",
        "value": 70
    }).validate().is_success is False

    assert FieldEqualScoring(None, default_request, {
        "error_message": "Проверка операций сравнения 66 > 50",
        "field": "request.interval",
        "operation": ">",
        "value": 50
    }).validate().is_success is True

    assert FieldEqualScoring(None, default_request, {
        "error_message": "Проверка операций сравнения 66 < 50",
        "field": "request.interval",
        "operation": "<",
        "value": 50
    }).validate().is_success is False

    assert FieldEqualScoring(None, default_request, {
        "error_message": "Проверка операций сравнения 66 = 10",
        "field": "request.interval",
        "operation": "=",
        "value": 10
    }).validate().is_success is False


def test_has_similar_contracts(mocker, default_request):
    func = HasSimilarContracts(None, default_request, {
        'percent': 50
    })
    mocker.patch.object(func, 'get_finished_contracts')
    func.get_finished_contracts.return_value = []
    assert func.validate().is_success is False

    func.get_finished_contracts.return_value = [{
        'price': 100
    }]
    assert func.validate().is_success is False
    contract = {
        'price':100000,
        'number':'000000000001',
        'status':'EC',
        'issuer_url':'issuer_url',
        'issuer_name':'IssuerInc',
        'start_date':datetime.date(year=2019, month=5, day=31),
        'end_date':datetime.date(year=2020, month=1, day=25),
        'okpd2':['10','11']}
    func.get_finished_contracts.return_value = [Contract44FZ(**contract)]
    assert func.validate().is_success is True


def test_in_global_black_list(mocker, default_request):
    func = InBankBlackList(None, default_request, {})
    mocker.patch.object(func, 'banks_stop_list_enabled')
    mocker.patch.object(func, 'inns_in_stop_lists')

    func.banks_stop_list_enabled.return_value = False
    assert func.validate().is_success is True

    func.banks_stop_list_enabled.return_value = True
    func.inns_in_stop_lists.return_value = True
    assert func.validate().is_success is False

    func.banks_stop_list_enabled.return_value = True
    func.inns_in_stop_lists.return_value = False
    assert func.validate().is_success is True
