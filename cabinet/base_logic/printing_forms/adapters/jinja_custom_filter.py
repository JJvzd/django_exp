import datetime
import inspect

from num2words import num2words

from common.helpers import get_month_text
from external_api.dadata_api import DaData


class Jinja_custom_filter:
    '''
        Класс внутри которогохранятся кастомные jinja фильтры
        для DocxTemplate
    '''
    dict_filter = {}
    black_list = (
        '__init__',
        '__set_dict_filter',
        '__split_address'
    )

    def __init__(self, *args, **kwargs):
        self.__set_dict_filter()

    def __set_dict_filter(self):
        '''
            Метод берет все существующие методы из данного класса,
            кроме методов которые лежат в self.black_list
            и запаковывает их в dict_filter
        '''
        for meth in inspect.getmembers(self, predicate=inspect.ismethod):
            if meth[0] not in self.black_list:
                self.dict_filter[meth[0]] = getattr(self, meth[0])

    def __split_address(self, value: str):
        tmp = value.split(',')
        return {'index': tmp[0], 'city': tmp[1], 'street': tmp[2]}

    def get_checkbox(self, value: bool):
        '''
            Возращает чекбокс в зависимости от value
        '''
        result = '\u2610'  # '☐'
        if value:
            result = '\u2612'  # '☒'
        return result

    def get_checkbox_comparison(self, value, comparable_value):
        '''
            :params comparable_value
            сравнивает два значения и возращает чекбокс
        '''
        return self.get_checkbox(value == comparable_value)

    def get_integer_part_number(self, value):
        '''
            Возращает целую часть от числа
        '''
        return int(float(value) // 1) if value else None

    def get_fractional_part_number(self, value):
        '''
            Возращает остаток от числа
        '''
        temp = str(value).split('.')
        if len(temp) > 1:
            if len(temp[1]) < 2:
                return '%s0' % temp[1]
            return temp[1][:2]
        return '00'

    def format_decimal(self, value):
        '''
            Форматирование числа
            разделитель дробной части и пробел между тысячными
        '''
        n = float(value)
        result = '{0:,.2f}'.format(n).replace(',', ' ').replace('.', ',')
        return result

    def get_number_in_words(self, value):
        """ Возращает целую часть от числа """
        if value:
            return num2words(self.get_integer_part_number(value), lang='ru')
        return None

    def number_and_in_words(self, value):
        """ Преображает число в вид:
            10 000 (десять тысяч) рублей 50 копеек
        """
        amount = self.get_integer_part_number(value)
        amount = '{0:,}'.format(amount).replace(',', ' ')
        amount_words = self.get_number_in_words(value)
        pennies = self.get_fractional_part_number(value)
        result = '%s (%s) рублей %s копеек' % (amount, amount_words, pennies)
        return result

    def number_and_in_words_not_cop(self, value):
        """ Преображает число в вид:
                    10 000 (десять тысяч) рублей
                """
        amount = self.get_integer_part_number(value)
        amount = '{0:,}'.format(amount).replace(',', ' ')
        amount_words = self.get_number_in_words(value)
        result = '%s (%s) рублей' % (amount, amount_words)
        return result

    def print_summa_client(self, value):
        # TODO:  Удалить, убрать из печаток, заменить на `number_and_in_words`
        return self.number_and_in_words(value)

    def date_heading_style(self, value, month, year):
        '''
        :value - день
        :month - месяц
        :year - год
        Формаитирует дату в вид:
        '«10» ноября 2019 г'
        '''
        return "«%s» %s %s г" % (value, get_month_text(month), year)

    def date_format(self, value):
        '''
        :value - день
        Формаитирует дату в вид:
        '10 ноября 2019 г'
        '''
        if not value:
            return ''
        if isinstance(value, str):
            date = datetime.datetime.strptime(value, '%d.%m.%Y')
        else:
            date = value
        return "%s %s %s" % (date.day, get_month_text(date.month), date.year)

    def date_format2(self, value):
        '''
        :value - день
        Формаитирует дату в вид:
        '10.11.2020 г.'
        '''
        if not value:
            return ''
        if isinstance(value, str):
            date = datetime.datetime.strptime(value, '%d.%m.%Y')
        else:
            date = value
        return date.strftime('%d.%m.%Y')

    def address_format(self, value):
        if value:
            api = DaData()
            result = api.clean_address(value)
            return '%s, %s' % (result[0]['postal_code'], result[0]['result'])
        return ''

    def add_russian_federation(self, value):
        '''
        Добавляет в адресс Российская федерация
        '''
        return "Российская федерация, %s" % (value)

    def get_index_adresse(self, value):
        return self.__split_address(value)['index']

    def get_city_adresse(self, value):
        return self.__split_address(value)['city']

    def get_street_adresse(self, value):
        return self.__split_address(value)['street']

    def format_adresse_to_delivery(self, value):
        return '; Почтой по адресу %s' % (value)

    def bollean_display(self, value):
        result = 'Нет'
        if value:
            result = 'Да'
        return result
