import requests
from django.core.cache import cache
from lxml import html

URL_TERROR = r'http://fedsfm.ru/documents/terrorists-catalog-portal-act'

ANSWERS = [
    'NOT_FOUND',  # Не найден в реестре
    'FOUND_ONLY_FIO',  # Найдено по ФИО
    'FOUND_PARTICAL',  # Найдено по ФИО и дате
    'FOUND'  # Найден в реестре
]


class NotAvailableExternalResource(Exception):
    pass


class CheckInTerroristsList:
    RESULT_NOT_FOUND = 'NOT_FOUND'
    RESULT_FOUND_ONLY_FIO = 'FOUND_ONLY_FIO'
    RESULT_FOUND_PARTICAL = 'FOUND_PARTICAL'
    RESULT_FOUND = 'FOUND'
    RESULT_CHOICES = (
        (RESULT_NOT_FOUND, 'Не найден в реестре'),
        (RESULT_FOUND_ONLY_FIO, 'Найдено по ФИО'),
        (RESULT_FOUND_PARTICAL, 'Найдено по ФИО и дате'),
        (RESULT_FOUND, 'Найден в реестре'),
    )

    def get_terror_fl_list(self):
        terror_list_fl = []

        if cache.get('terror_list_fl') is None:
            response = requests.get(URL_TERROR)
            if response.status_code != 200:
                raise NotAvailableExternalResource

            tree = html.fromstring(response.content)
            for element in tree.xpath(r'//*[@id="russianFL"]/div/ol/li'):
                terror_list_fl.append(element.text_content())
            cache.set('terror_list_fl', terror_list_fl)

        terror_list_fl = cache.get('terror_list_fl')
        return terror_list_fl

    def check(self, last_name: str, first_name: str, middle_name: str,
              date_of_birth: str, place_of_birth: str) -> str:

        terror_list_fl = self.get_terror_fl_list()

        first_name = ' '.join([last_name, first_name, middle_name])
        first_name = first_name.upper()

        place_of_birth = place_of_birth.upper() if place_of_birth else place_of_birth

        answers = set()
        for element in terror_list_fl:
            if first_name in element:
                if date_of_birth in element:
                    if place_of_birth in element:
                        answers.add(3)
                    else:
                        answers.add(2)
                else:
                    answers.add(1)
            else:
                answers.add(0)
        return self.RESULT_CHOICES[max(answers)][0]


def check_terror_fl(surname, name, middle_name, date_of_birth, place_of_birth):
    set_answer = set()

    terror_list_fl = []

    if cache.get('terror_list_fl') is None:
        response = requests.get(URL_TERROR)
        if response.status_code != 200:
            return 'SERVER IS NOT AVAILABLE'
        tree = html.fromstring(response.content)
        for element in tree.xpath(r'//*[@id="russianFL"]/div/ol/li'):
            terror_list_fl.append(element.text_content())
        cache.set('terror_list_fl', terror_list_fl)
    else:
        terror_list_fl = cache.get('terror_list_fl')
    name = surname + ' ' + name + ' ' + middle_name
    name = name.upper()
    place_of_birth = place_of_birth.upper()
    for element in terror_list_fl:
        if name in element:
            if date_of_birth in element:
                if place_of_birth in element:
                    set_answer.add(3)
                else:
                    set_answer.add(2)
            else:
                set_answer.add(1)
        else:
            set_answer.add(0)
    return ANSWERS[max(set_answer)]
