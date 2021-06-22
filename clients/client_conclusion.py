import re

import requests
import ujson
from django.core.cache import cache
from django.core.exceptions import ValidationError


class ClientConclusionManagement:

    def __init__(self, inn_or_ogrn):
        self.inn_or_ogrn = self._validate_inn_or_ogrn(inn_or_ogrn)

    def _validate_inn_or_ogrn(self, value):
        '''
        Валидатор для inn_or_ogrn
        '''
        p = re.compile('^[0-9]{9,15}$')
        if not p.match(value):
            raise ValidationError('Вы ввели не ИНН/ОГРН')
        return value

    def _get_value_from_caches(self, key):
        '''
        Метод возращает значение из кэша.
        Если ключ не найден возращает None
        '''
        return cache.get(str(key)) or None

    def _set_value_in_caches(self, key, value):
        cache.add(str(key), value)

    def check_in_vestnik(self):
        """
        Проверка организации в списке журнала
        "Вестник государственной регистрации"
        Возращает true или false
        Если вернуло true значит организация есть в списке и её
        хотят или уже исключили
        """
        url = 'https://www.vestnik-gosreg.ru/publ/fz83/'
        result = False
        value_from_cache = self._get_value_from_caches(self.inn_or_ogrn)
        if value_from_cache is None:
            post_fields = {
                'query': str(self.inn_or_ogrn),
            }
            request = requests.post(url, post_fields)
            # Пробуем найти 'Информации не обнаружено' в ответе
            # Если не получается, значит организация есть в списках
            if re.search('Информации не обнаружено', request.text) is not None:
                result = True
            self._set_value_in_caches(self.inn_or_ogrn, result)

        else:
            result = value_from_cache
        return result

    def check_in_service_nalog(self, inn: str, bik: str) -> bool:
        '''
        Проверка организации на рессурсе
        https://service.nalog.ru/bi.do
        Если вернуло true значит у организация есть
        Действующие решения о приостановленых операций
        по счетам налогоплательщика
        '''
        url = 'https://service.nalog.ru/bi.do/bi2-proc.json'
        post_fields = {
            'requestType': 'FINDPRS',
            'captcha': True,
            'innPRS': str(inn),
            'bikPRS': str(bik),
        }
        request = requests.post(url, post_fields)
        jdata = ujson.loads(request.text)
        # Если в словаре есть ключ rows, значит поиск что-то нашел
        # и у организации есть действующие решения о приостановленых
        # операций
        result = 'rows' in jdata
        return result
