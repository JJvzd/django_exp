import json
import logging
from collections import Iterable

from django.conf import settings
from django.core.cache import cache
from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from base_request.models import AbstractRequest
from cabinet.models import System
from clients.models import Bank
from tender_loans.models import LoanRequest


logger = logging.getLogger('scoring')


class ScoringResult:
    SCORING_PASS = True
    SCORING_FAIL = False

    def __init__(self, errors=None, errors_index=None):
        self.errors_index = errors_index
        self.errors = None
        self.result = None
        if errors is None:
            self.errors = []
            self.result = self.SCORING_PASS
        elif type(errors) == str:
            self.errors = [errors]
            self.result = self.SCORING_FAIL
        elif isinstance(errors, Iterable) and any(
                [type(i) == str for i in errors]):
            self.errors = errors
            self.result = self.SCORING_FAIL
        else:
            raise ValueError("Неверный параметр errors: %s" % errors)

    @property
    def is_success(self):
        return self.result == self.SCORING_PASS

    @property
    def is_fail(self):
        return self.result == self.SCORING_FAIL

    def get_errors(self):
        return self.errors

    def get_first_error(self):
        return self.errors[0] if self.errors else None


class ScoringItem(object):
    error_message = None
    disable_for_loans = False
    scoring_params = []
    full_name = None

    def params_to_dict(self):
        return {
            param: getattr(self, param)
            for param in self.scoring_params
        }

    def get_result(self):
        if isinstance(self.request, LoanRequest) and self.disable_for_loans:
            return ScoringResult()
        try:
            return self.validate()
        except Exception as e:
            params = ', '.join([
                '%s=%s' % (k, v) for k, v in self.params_to_dict().items()
            ])
            logger.info("Ошибка в скоринге %s -> %s (%s)" % (
                self.request, self.bank, params
            ))
            logger.exception(e)
            if settings.DEBUG:
                raise e
            return ScoringResult('Непредвиденная ошибка в скоринге')

    def get_error_message(self):
        return self.error_message

    def __init__(self, bank: Bank, request: AbstractRequest, settings: dict):
        self.bank = bank
        self.request = request
        self.settings = settings

        params = self.scoring_params + ['error_message', 'disable_for_loans']
        for param in params:
            value = settings.get(param, None)
            if value is None:
                value = getattr(self, param, None)
            setattr(self, param, value)

    @property
    def client(self):
        return self.request.client

    @property
    def profile(self):
        return self.request.client.profile

    def validate(self) -> ScoringResult:
        return ScoringResult()


class ScoringLogic:

    @classmethod
    def clear_cache_all_requests(cls, client):
        from bank_guarantee.models import Request
        from tender_loans.models import LoanRequest

        for request in Request.objects.filter(client=client):
            cache.delete(ScoringLogic.get_cache_name(request))

        for request in LoanRequest.objects.filter(client=client):
            cache.delete(ScoringLogic.get_cache_name(request))

    @classmethod
    def get_cache_name(cls, request):
        return 'send_to_bank_%s_%s' % (request.id, request.__class__.__name__)

    def __init__(self, bank: Bank, request):
        self.bank = bank
        self.request = request
        self.reason = None

    @cached_property
    def active_functions(self):
        """
        Возвращает словарь с описанием активных функций скоринга
        :return:
        """
        return {
            'TrueScoring': True,
            'FailScoring': True,
        }

    def is_active(self, scoring_item: dict) -> bool:
        """
        Проверяет активна ли функция скоринга
        :param scoring_item:
        :return:
        """
        # TODO: проверку активности
        return scoring_item.get('active', True)

    def get_scoring_settings(self):
        scoring_settings = json.loads(self.bank.settings.scoring_settings)
        if not len(scoring_settings):
            return []
        return scoring_settings

    def check_rules(self, rules):
        if isinstance(rules, dict):
            rules = [rules]
        return self.validate_rules(rules)

    def check(self, use_common_rules=False) -> ScoringResult:
        if not settings.TESTING and (
                not System.objects.all().first().scoring_on or
                not self.bank.settings.scoring_enable):

            if self.bank.settings.scoring_enable:
                log_message = 'Скоринг отключен глобально'
            else:
                log_message = 'Скоринг для банка отключен'
            logger.warning(log_message)
            return ScoringResult()

        scoring_settings = self.get_scoring_settings() or []
        if use_common_rules:
            scoring_settings += json.loads(
                System.get_setting('default_scoring_rules'))
        if not scoring_settings:
            return ScoringResult()

        result = self.validate_rules(scoring_settings)
        if result.is_fail:
            self.reason = result.get_first_error()
        return result

    def validate_rules(self, scoring_settings, as_agent=True) -> ScoringResult:
        errors = []
        errors_index = []
        index = 0
        for scoring_item in scoring_settings:
            index += 1
            scoring_class_name = scoring_item.get('class')
            if self.is_active(scoring_item):
                scoring_class = self.load_class(scoring_class_name)
                if scoring_class:
                    scoring_obj = scoring_class(self.bank, self.request,
                                                scoring_item)
                    result = scoring_obj.get_result()
                    if result.is_fail:
                        if as_agent:
                            errors.append(result.get_first_error())
                            errors_index.append(index)
                        else:
                            return result
        if errors:
            return ScoringResult(errors=errors, errors_index=errors_index)
        return ScoringResult()

    @staticmethod
    def load_class(scoring_class_name):
        return import_string(
            'cabinet.base_logic.scoring.functions.%s' % scoring_class_name)
