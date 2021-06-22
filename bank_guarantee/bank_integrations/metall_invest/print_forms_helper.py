from cabinet.base_logic.printing_forms.helpers.base import BaseHelper
from cabinet.constants.constants import Target, FederalLaw
from common.helpers import get_month_text


class MetallInvestHelper(BaseHelper):

    def getPropertyStatus(self):
        address = self.profile.fact_address_properies
        if address['status']:
            return 'Собственность'
        else:
            return 'Аренда с %s по %s' % (address['from'], address['to'])

    def contract_type(self):
        # todo: поправить, не правильное условие
        return Target.PARTICIPANT in self.request.targets and \
               self.request.tender.federal_law in [FederalLaw.LAW_44]

    def get_contract_text(self):
        if self.client.is_organization:
            return '%s в лице %s  действующего(ей) на основании Устава, ' % (
                self.profile.full_name, self.profile.general_director.full_name()
            )
        return 'Индивидуальный предприниматель %s  ' \
               '(Свидетельство серия _________ номер _________ о государственной ' \
               'регистрации физического лица ' \
               'в качестве индивидуального предпринимателя) ' % self.profile.full_name

    def main_okved(self):
        okved = self.profile.kindofactivity_set.first()
        if okved:
            return okved.split(' ')[0]
        return ''

    def fill_number(self, value, length):
        while len(value) <= length:
            value = '0' + value
        return value

    def get_ogrn_ul(self):
        return self.fill_number(self.profile.reg_ogrn, 13).split()

    def get_ogrn_ip(self):
        return self.fill_number(self.profile.reg_ogrn, 15).split()

    @property
    def get_inn_ul(self):
        return self.fill_number(self.profile.reg_inn, 10)

    def get_snils(self, snils=None):
        if not snils:
            snils = self.profile.general_director.snils
        return self.fill_number(snils, 11).split()

    def get_inn_ip(self, inn=None):
        if not inn:
            inn = self.profile.general_director.fiz_inn
        return self.fill_number(inn, 12).split()

    @property
    def get_okato(self):
        return self.fill_number(self.profile.reg_okato, 11)

    @property
    def get_okpo(self):
        return self.fill_number(self.profile.reg_okpo, 8)

    def get_birthday(self, person=None):
        if not person:
            person = self.profile.general_director
        if person.passport.date_of_birth:
            return [
                '',
                person.passport.date_of_birth.year,
                get_month_text(person.passport.date_of_birth.month),
                person.passport.date_of_birth.day,
                person.passport.place_of_birth
            ]
        else:
            return ['', '', '', '', '']
