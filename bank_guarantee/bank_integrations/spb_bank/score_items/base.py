from typing import Any, Tuple

import attr
from django.utils.functional import cached_property


@attr.s
class ScoreItemValidator:
    score = attr.ib(kw_only=True)
    from_value = attr.ib(default=0)
    to_value = attr.ib(default=99999999)
    check_bool = attr.ib(default=False)


class BaseScoreItem:
    score_map = []
    default_score = 0
    score_if_exception = 0
    value_if_exception = 0

    def __init__(self, data):
        self.data = data

    def get_value(self):
        return None

    def __get_score(self, value):
        if self.score_map:
            score_item: ScoreItemValidator
            for score_item in self.score_map:
                if not score_item.check_bool:
                    if value is None:
                        value = 0
                    if score_item.from_value <= value < score_item.to_value:
                        return score_item.score
                else:
                    if bool(value) is True:
                        return score_item.score

        return self.default_score

    @cached_property
    def value(self) -> Tuple[Any, bool]:
        """ Возвращает значение по формуле и информацию, произошло ли исключение
            при расчете
        """
        try:
            return self.get_value(), True
        except ZeroDivisionError:
            return self.value_if_exception, False

    @cached_property
    def score(self):
        """ Возвращает баллы в соответствии с value при условии, что не было исключений
        """
        value, without_exception = self.value
        if without_exception:
            return self.__get_score(value)
        else:
            return self.score_if_exception

    def data(self):
        value, _ = self.value
        return {
            'value': value,
            'score': self.score
        }
