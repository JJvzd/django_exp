from datetime import datetime

from django.utils.functional import cached_property

from bank_guarantee.models import ContractType, ContractPlacementWay
from cabinet.base_logic.conclusions.check_terror import CheckInTerroristsList
from cabinet.base_logic.printing_forms.helpers.base import BaseHelper
from cabinet.constants.constants import Target
from external_api.blacklist_api import BlackListChecker
from external_api.clearspending_api import ClearSpendingWeb
from external_api.nalogru_api import NalogRu
from external_api.searchtenderhelp_api import SearchTenderhelpApi
from external_api.zachestniybiznes_api import ZaChestnyiBiznesApi
from external_api.parsers_tenderhelp import ParsersApi
from settings.configs.banks import BankCode
from utils.helpers import number2string

FACTOR_SUCCESS = 'Стоп-фактор не выявлен'
FACTOR_FAILED = 'Выявлен стоп-фактор'


class MoscombankHelper(BaseHelper):

    def format_date(self, value):
        if value:
            return value.strftime('%d.%m.%Y')
        return ''

    @cached_property
    def interval_to(self):
        return self.format_date(self.request.interval_to)

    @cached_property
    def protocol_date(self):
        return self.format_date(self.request.protocol_date)

    @cached_property
    def tender_date(self):
        return self.format_date(self.request.tender.tender_date)

    @cached_property
    def warranty_from(self):
        return self.format_date(self.request.warranty_from)

    @cached_property
    def warranty_to(self):
        return self.format_date(self.request.warranty_to)

    @cached_property
    def publish_date(self):
        return self.format_date(self.request.tender.publish_date)

    @cached_property
    def targets(self):
        choices = {
            Target.PARTICIPANT: 'обеспечение участия в торгах',
            Target.EXECUTION: 'обеспечение исполнения контракта',
            Target.AVANS_RETURN: 'обеспечение возврата аванса',
            Target.WARRANTY: 'обеспечение исполнения гарантийных обязательств',
        }
        return ','.join([choices[i] for i in self.request.targets])

    @cached_property
    def has_unpaid_card(self):
        result = self.profile.profileaccounts.filter(has_unpaid_account=True).first()
        return 'Есть' if result else 'Отсутствует'

    @cached_property
    def experience(self):
        return '%2.f' % ((datetime.now().date() - self.profile.reg_state_date).days / 365)

    @cached_property
    def type_bg(self):
        return {
            ContractType.STATE: 'государственному контракту',
            ContractType.MUNICIPAL: 'муниципальному контракту',
            ContractType.COMMERCIAL: 'коммерческий (223-ФЗ) контракту',
        }.get(self.request.contract_type)

    @cached_property
    def get_bg2(self):
        return {
            ContractType.STATE: 'государственного контракта',
            ContractType.MUNICIPAL: 'муниципального контракта',
            ContractType.COMMERCIAL: 'коммерческого контракта',
        }.get(self.request.contract_type)

    @cached_property
    def placement_way(self):
        return {
            ContractPlacementWay.COMPETITION: 'конкурсе',
            ContractPlacementWay.AUCTION: 'аукционе',
            ContractPlacementWay.ELECTRONIC_AUCTION: 'аукционе в электронной форме',
            ContractPlacementWay.CLOSED_BIDDING: 'закрытых торгах (закупки)'
        }.get(self.request.placement_way, 'конкурсе')

    @cached_property
    def placement_way2(self):
        return {
            ContractPlacementWay.COMPETITION: 'конкурса',
            ContractPlacementWay.AUCTION: 'аукциона',
            ContractPlacementWay.ELECTRONIC_AUCTION: 'аукциона в электронной форме',
            ContractPlacementWay.CLOSED_BIDDING: 'закрытых торгов (закупок)'
        }.get(self.request.placement_way, 'конкурса')

    @cached_property
    def commission(self):
        result = self.request.get_commission_for_bank_code(BankCode.CODE_MOSCOMBANK)
        return result and result['percent']

    @cached_property
    def okved(self):
        # TODO
        return ''

    @cached_property
    def contact_position(self):
        """Должность контактного лица"""
        # TODO
        return ''

    @cached_property
    def first_license(self):
        return self.profile.licenses.first() or ''

    @cached_property
    def second_license(self):
        return self.profile.licenses[1] if self.profile.licenses.count() > 1 else None

    @cached_property
    def third_license(self):
        return self.profile.licenses[2] if self.profile.licenses.count() > 2 else None

    @cached_property
    def four_license(self):
        return self.profile.licenses[3] if self.profile.licenses.count() > 3 else None

    @cached_property
    def account_first(self):
        return self.profile.profileaccounts.first()

    @cached_property
    def summa_client(self):
        return number2string(self.request.required_amount, 'money2')

    @cached_property
    def today(self):
        return datetime.now().strftime('%d.%m.%Y')

    @cached_property
    def full_name(self):
        return self.profile.full_name or self.profile.short_name

    @cached_property
    def get_quarters(self):
        return self.client.accounting_report.get_quarters()

    @cached_property
    def last_year_quarter_client(self):
        return self.get_quarters[1]

    @cached_property
    def last_quarter_client(self):
        return self.get_quarters[0]

    @cached_property
    def last_quarter(self):
        return self.last_quarter_client.quarter

    @cached_property
    def quarter_date_end(self):
        return self.last_quarter_client.get_end_date().strftime('%d.%m.%Y')

    @cached_property
    def last_nalog_declaration(self):
        """
        Выручка по декларации по налогу на прибыль, тыс. руб. за последний отчетный период
        :return:
        """
        # TODO реализовать
        return 0

    @cached_property
    def last_year_nalog_declaration(self):
        """Выручка по декларации по налогу на прибыль, тыс. руб.
        за последний отчетный год
        """
        # TODO реализовать
        return 0

    @cached_property
    def last_year_revenue_scrin(self):
        """Выручка по сведениям интернет-сервиса "СКРИН" за последний отчетный год"""
        # TODO реализовать если надо
        return 0

    @cached_property
    def last_revenue_scrin(self):
        """Выручка по сведениям интернет-сервиса "СКРИН" за последний отчетный период"""
        # TODO реализовать если надо
        return 0

    @cached_property
    def sum_court_cases(self):
        """Сумма судебных дел, по которым Клиент выступает ответчиком
        ("СКРИН"), тыс. руб.
        """
        helper = ZaChestnyiBiznesApi()
        response = helper.method('court-arbitration', self.client.inn)
        if response['status'] != '200':
            return None
        if not isinstance(response['body']['docs'][0]['точно'], dict):
            return 0
        data = response['body']['docs'][0]['точно']['дела']
        data = filter(
            lambda x: x.get('Ответчик', [{}])[0].get('ИНН', '') == self.client.inn,
            data.values()
        )
        return sum([i.get('СуммаИска') or 0 for i in data])

    @cached_property
    def unfinished_executing_proceeding(self):
        """Сумма незавершенных исполнительных производств ("СКРИН"), тыс. руб."""
        # TODO реализовать
        return 0

    @cached_property
    def arrears_debit(self):
        """Просроченная дебиторская задолженность, тыс. руб."""
        # TODO реализовать
        return 0

    @cached_property
    def arrears_credit(self):
        """Просроченная кредиторская задолженность, тыс. руб."""
        # TODO реализовать
        return 0

    @cached_property
    def count_executing_contracts(self):
        """Количество исполненных контрактов"""
        helper = ClearSpendingWeb()
        data = helper.get_contracts_info(self.client.inn, self.client.kpp)
        if not data or not data['counts']:
            return 0
        return data['counts'][0][0]

    @cached_property
    def kind_of_activity(self):
        """Деятельность клиента"""
        # TODO реализовать
        return 'Сезонность не свойственна'

    @cached_property
    def is_small_business(self):
        """Клиент относится к малому бизнесу"""
        validation_result = NalogRu().get_subject_size(self.client.profile.reg_inn)
        return FACTOR_SUCCESS if validation_result not in [1, 2] else FACTOR_FAILED

    @cached_property
    def stop_amount_bg(self):
        """Сумма БГ >= 5 000 000 руб."""
        return FACTOR_SUCCESS if self.request.required_amount < 5000000 else FACTOR_FAILED

    @cached_property
    def stop_limit_principal(self):
        """Лимит на приципиала >= 5 000 000 руб."""
        # TODO реализовать
        return FACTOR_SUCCESS

    @cached_property
    def stop_term_guarantee(self):
        """Сумма гарантии более 910 дней"""
        return FACTOR_SUCCESS if self.request.interval < 910 else FACTOR_FAILED

    @cached_property
    def stop_resident_rf(self):
        """Не резидент РФ"""
        if not self.client.profile.general_director.has_russian_passport:
            return FACTOR_SUCCESS
        else:
            return FACTOR_FAILED

    @cached_property
    def unreliability_egrul(self):
        """Сведения о недостоверности в ЕГРЮЛ"""
        return FACTOR_SUCCESS

    @cached_property
    def has_any_debt(self):
        """
        Наличие просроченной дебиторской и/или кредиторской задолжности,
        просроченных собственных векселей длительностью свыше 3-х мес. в размере
        более 25% от общего объема соответствующей задолжнности
        """
        return FACTOR_SUCCESS

    @cached_property
    def stop_liquidation(self):
        """ Ликвидация, предстоящая ликвидация, любые формы реорганизации """
        # TODO реализовать
        return FACTOR_SUCCESS

    @cached_property
    def stop_term_registration(self):
        """ Срок регистрации менее 90 дней """
        if (datetime.now().date() - self.client.profile.reg_state_date).days < 90:
            return FACTOR_SUCCESS
        else:
            return FACTOR_FAILED

    @cached_property
    def stop_many_registration(self):
        """ Регистрация клиента по адресу массовой регистрации """
        validation_result = NalogRu().address_of_many_registrations(
            self.client.profile.legal_address
        )
        return FACTOR_SUCCESS if not validation_result else FACTOR_FAILED

    @cached_property
    def disqualified_person(self):
        """
        Наличие сведений о Клиенте, его представителях и бенефициарном владельце
        в реестре дисквалифицированных лиц
        """
        birthday = self.client.profile.general_director.passport.date_of_birth
        if birthday:
            birthday = birthday.strftime('%d.%m.%Y')
        api = ParsersApi()
        validation_result = api.nalogRu.is_disqualified_person(
            first_name=self.client.profile.general_director.first_name,
            last_name=self.client.profile.general_director.last_name,
            middle_name=self.client.profile.general_director.middle_name,
            birthday=birthday,
        )
        return FACTOR_SUCCESS if not validation_result else FACTOR_FAILED

    @cached_property
    def inability_to_lead(self):
        """
        Наличие сведений о представителях Клиентам, в отношении которых установлен факт
        невозможности участия (осуществления руководства) в организации в судебном порядке
         """
        # TODO реализовать
        return FACTOR_SUCCESS

    @cached_property
    def unscrupulous_supplier(self):
        """ Наличие сведений о Клиенте в реестре недобросовестных поставщиков """
        validation_result = BlackListChecker().in_black_list(self.client.profile.reg_inn)
        return FACTOR_SUCCESS if not validation_result else FACTOR_FAILED

    @cached_property
    def invalid_documents(self):
        """
        Недействительны документы, удостоверяющие личность представителей и/или
        бенефициарного владельца (кроме случая представления временного документа,
        удостоверяющего личность)
        """
        validation_result = ParsersApi().passports.check_passport(
            series=self.client.profile.general_director.passport.series,
            number=self.client.profile.general_director.passport.number,
        )
        return FACTOR_SUCCESS if not validation_result else FACTOR_FAILED

    @cached_property
    def false_accounting(self):
        """
        Наличие информации о представлении Клиентом формы № 1 с нулевыми значениями
        «Оборотные активы», «Краткосрочные обязательства»,  при наличии информации об
        оборотах по счетам в Банке или в других банках
        """
        # TODO реализовать
        return FACTOR_SUCCESS

    @cached_property
    def terror_check(self):
        """
        Сведения о клиенте, его представителях и бенефициарном владельце установлены в
        перечне организаций и физических лиц, в отношении которых имеются сведения об
        их причастности к экстрмистской деятельности или терроризму
        """
        general_director = self.client.profile.general_director

        validation_result = CheckInTerroristsList().check(
            first_name=general_director.first_name or '',
            last_name=general_director.last_name or '',
            middle_name=general_director.middle_name or '',
            date_of_birth=general_director.passport.date_of_birth or '',
            place_of_birth=general_director.passport.place_of_birth or '',
        )
        if validation_result == CheckInTerroristsList.RESULT_NOT_FOUND:
            return FACTOR_SUCCESS
        else:
            return FACTOR_FAILED

    @cached_property
    def info_193_t(self):
        """Сведения о Клиенте имеются в списках 193-Т"""
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def in_list_693_p(self):
        """
        Сведения о Клиенте имеются в списках 639-П, при этом в соответствии с ПВК
        по ПОД/ФТ рейтинг Клиента >= 8
        """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def criminal_is_gen_dir(self):
        """
        Наличие публичных фактов привлечения к уголовной ответственности единоличного
        исполнительного органа, бенефициарного владельца
        """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def is_casino(self):
        """ Игорный бизнес """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def is_show_business(self):
        """ шоу-бизнес """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def is_activity_stock(self):
        """ операции на фондовом и валютном рынке """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def is_sport_business(self):
        """ спортивный менеджмент и скаутинг """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def is_rare_animal_trade(self):
        """ торговля редкими видами животных и растений """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def is_prohibited_products(self):
        """
        производство и/или продажа запрещенных видов продукции
        (оружие, наркотические средства и т.д.)
        """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def is_credit_company(self):
        """
        плизинговые компании, кредитные кооперативы, микрофинансовые компании,
        кредитные организации, страховые компании
        """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def is_religious_organization(self):
        """ религиозные организации и объединения """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def is_building_company(self):
        """ Капитальное строительство зданий и сооружений """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def is_rent_property(self):
        """ Аренда недвижимости """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def buy_property(self):
        """ Покупка недвижимости """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def bankrupt(self):
        """
        В отношении Клиента, единоличного исполнительного органа, бенефициарного
        владельца введена процедура банкротства
        """
        validation_result = SearchTenderhelpApi().company_is_bankrupt(
            self.client.profile.reg_inn
        )
        return FACTOR_SUCCESS if not validation_result else FACTOR_FAILED

    @cached_property
    def beneficiars_bankrupt(self):
        """
        В отношении единоличного исполнительного органа, бенефициарных владельцах Клиента,
        которые являлись  либо единоличным исполнительным органом или бенефициарным
        владельцем юридических лиц или ИП, в отношении которых введена
        процедура банкротства
        """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def guarantor_bankrupt(self):
        """
        Клиент является поручителем в отношении юридического лица или ИП, в отношении
        которого введена процедура банкротства
        """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def negative_credit_history(self):
        """
        Сведения об отрицательной кредитной истории у Клиента по выданным (погашенным)
        кредитам в течение последних 180 дней (просрочка более 29 календарных дней)
        """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def credit_history_delay_5_day(self):
        """
        В отношении кредитной истории в Банке – просрочка более 5 дней включительно
        """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def other_warranty_depreciated(self):
        """
        У Клиента в Банке имеется иная гарантия или ссуда, по которой выявлены
         индивидуальные признаки обесценения
         """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def has_unpaid_billing(self):
        """
        Наличие текущей картотеки неоплаченных расчетных документов к банковским счетам
        Клиента перед Банком ( включая рассматриваемую заявку на гарантию) и (или)
        сроком свыше 5 рабочих дней.
        """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def suspension_decision(self):
        """ Имеются действующие решения о приостановлении """
        validation_result = NalogRu().decision_to_suspend(self.client.profile.reg_inn)
        return FACTOR_SUCCESS if not validation_result else FACTOR_FAILED

    @cached_property
    def debt_fot(self):
        """
        Наличие задолженности в размере более 1 ФОТ (фонда оплаты труда предприятия
        за месяц) в течение 30 дней и более
        """
        # TODO
        return FACTOR_SUCCESS

    @cached_property
    def position_gen_dir(self):
        """ Должность генерального директора по уставу только для юр.лиц """
        if not self.client.is_organization:
            return ''
        return self.profile.general_director.gen_dir_post

    @cached_property
    def doc_gen_dir(self):
        """ Документ генерального директора """
        if not self.client.is_organization:
            return ''
        return self.profile.general_director.document_gen_dir.gen_dir_doc_right()

    @cached_property
    def need_booker(self):
        """ нужен ли бухгалтер """
        return self.client.is_organization and self.profile.booker and \
               not self.profile.booker.is_general_director

    @cached_property
    def position_booker(self):
        """ Должность бухгалтера согласнго уставу, только для юр. лиц """
        return self.profile.booker.booker_post if self.need_booker else ''

    @cached_property
    def doc_booker(self):
        """ Документ главного бухгалтера """
        return self.profile.booker.booker_document if self.need_booker else ''

    @cached_property
    def first_beneficiar(self):
        return self.profile.beneficiars.first() or ''

    @cached_property
    def second_beneficiar(self):
        return self.profile.beneficiars[1] if self.profile.beneficiars.count() > 1 else ''

    @cached_property
    def tax_year(self):
        """ Сведения об уплаченных налогах за последние 4 квартала, тыс.руб. """
        return 0

    @cached_property
    def discrepancy_tender_and_request(self):
        """Установление фактов несоответствия юридического лица заявленным в конкурсной
        документации требованиям, размещенным на официальном информационном ресурсе
        в сети Интернет
        """
        return FACTOR_SUCCESS
