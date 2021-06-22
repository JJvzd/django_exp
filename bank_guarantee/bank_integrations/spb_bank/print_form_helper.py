from django.utils import timezone
from django.utils.functional import cached_property

from bank_guarantee.bank_integrations.spb_bank.client_rating_calculator import (
    ClientRatingTranslator
)
from bank_guarantee.bank_integrations.spb_bank.helpers import SPBContractsInfo
from base_request.logic.request_log import RequestLogger
from base_request.models import AbstractRequest
from cabinet.base_logic.printing_forms.helpers.base import BaseHelper
from cabinet.constants.constants import TaxationType, Target
from cabinet.models import EgrulData
from conclusions_app.conclusions.common import (
    RMSPConclusion, AddressOfManyRegistrationsConclusion
)
from conclusions_app.conclusions_logic import ConclusionsLogic
from external_api.zachestniybiznes_api import ZaChestnyiBiznesApi
from utils.helpers import number2string
import json


class SPBHelper(BaseHelper):
    pass_stop_factor = 'стоп фактор не выявлен'
    fail_stop_factor = 'стоп фактор выявлен'

    def __init__(self, request: AbstractRequest, bank):
        super().__init__(request, bank)
        self.contracts_info = SPBContractsInfo(request=request)
        self._zachestnyibiznes_data = None
        self._zachestnyibiznes_data_beneficiary = None

    @cached_property
    def get_bank_commission_percent(self):
        if self.request.banks_commissions:
            banks_commissions = json.loads(self.request.banks_commissions)
            if banks_commissions:
                banks_commissions = banks_commissions.get(self.bank.code, {})
                if isinstance(banks_commissions, dict):
                    banks_commissions = banks_commissions.get('percent', 0)
                return round(float(banks_commissions), 2)
        return None

    @cached_property
    def print_interval_to(self):
        return self.request.interval_to.strftime('«%d» %B %Y')

    @property
    def zachestnyibiznes_data_beneficiary(self):
        if self._zachestnyibiznes_data is None:
            for _ in range(3):
                try:
                    api = ZaChestnyiBiznesApi()
                    data = api.method('card', self.request.tender.beneficiary_inn)
                    if isinstance(data, dict):
                        data = data.get('body', {}).get('docs')
                        if isinstance(data, list) and len(data) > 0:
                            self._zachestnyibiznes_data_beneficiary = data[0]
                            break
                except Exception as error:
                    RequestLogger.log(self.request, str(error))
        return self._zachestnyibiznes_data_beneficiary

    @property
    def zachestnyibiznes_data(self):
        if self._zachestnyibiznes_data is None:
            for _ in range(3):
                try:
                    api = ZaChestnyiBiznesApi()
                    data = api.method('card', self.profile.reg_inn)
                    if isinstance(data, dict):
                        data = data.get('body', {}).get('docs')
                        if isinstance(data, list) and len(data) > 0:
                            self._zachestnyibiznes_data = data[0]
                            break
                except Exception as error:
                    RequestLogger.log(self.request, str(error))
        return self._zachestnyibiznes_data

    @cached_property
    def beneficiary_oktmo(self):
        return (self.zachestnyibiznes_data_beneficiary or {}).get('ОКТМО')

    @cached_property
    def beneficiary_okved(self):
        return (self.zachestnyibiznes_data_beneficiary or {}).get('ОКВЭДОснРОССТАТ')

    @cached_property
    def beneficiary_reg_date(self):
        return (self.zachestnyibiznes_data_beneficiary or {}).get('ДатаПостУч')

    @cached_property
    def beneficiary_reg_organ(self):
        return (self.zachestnyibiznes_data_beneficiary or {}).get('НаимНО')

    @cached_property
    def beneficiary_address(self):
        return self.zachestnyibiznes_data_beneficiary['Адрес']

    @cached_property
    def interval_from(self):
        return self.request.interval_from.strftime('%d.%m.%Y')

    @cached_property
    def interval_to(self):
        return self.request.interval_to.strftime('%d.%m.%Y')

    @cached_property
    def gen_dir_passport(self):
        if self.profile.general_director.has_russian_passport:
            return 'Паспорт'
        else:
            return self.profile.general_director.another_passport

    @cached_property
    def gen_dir_passport_number(self):
        if self.profile.general_director.has_russian_passport:
            return self.profile.general_director.passport.number
        return ''

    @cached_property
    def gen_dir_passport_series(self):
        if self.profile.general_director.has_russian_passport:
            return self.profile.general_director.passport.series
        return ''

    @cached_property
    def gen_dir_passport_issued_by(self):
        if self.profile.general_director.has_russian_passport:
            return self.profile.general_director.passport.issued_by
        return ''

    @cached_property
    def gen_dir_passport_when_issued(self):
        if self.profile.general_director.has_russian_passport:
            return self.profile.general_director.passport.when_issued.strftime('%d.%m.%Y')
        return ''

    @cached_property
    def gen_dir_passport_date_of_birth(self):
        general_director = self.profile.general_director
        if general_director.has_russian_passport:
            return general_director.passport.date_of_birth.strftime('%d.%m.%Y')
        return ''

    @cached_property
    def gen_dir_passport_place_of_birth(self):
        if self.profile.general_director.has_russian_passport:
            return self.profile.general_director.passport.place_of_birth
        return ''

    @cached_property
    def gen_dir_passport_place_of_registration(self):
        if self.profile.general_director.has_russian_passport:
            return self.profile.general_director.passport.place_of_registration
        return ''

    @cached_property
    def gen_dir_passport_issued_code(self):
        if self.profile.general_director.has_russian_passport:
            return self.profile.general_director.passport.issued_code
        return ''

    @cached_property
    def licenses(self):
        row = 'Вид деятельности: %s, Номер : %s, Кем выдана: %s, Дата выдачи: %s, ' \
              'Срок окончания: %s, Перечень видов деятельности:%s; '
        result = ''

        for license in self.profile.licenses:
            license_end = license.date_end_license.strftime(
                '%d.%m.%Y'
            ) if not license.is_indefinitely else 'Бессрочно'
            result += row % (
                license.view_activity,
                license.number_license,
                license.issued_by_license,
                license.date_issue_license.strftime('%d.%m.%Y'),
                license_end,
                license.list_of_activities
            )
        return result

    @cached_property
    def reg_organ(self):
        data = EgrulData.get_info(self.profile.reg_inn)
        return data['section-other']['registrator_name']

    @cached_property
    def print_commission(self):
        return number2string(self.get_bank_commission)

    @cached_property
    def doc_for_fact_address(self):
        if self.profile.fact_is_legal_address:
            if self.profile.legal_address_status:
                return 'Собственность'
            else:
                return 'Аренда от %s до %s' % (
                    self.profile.legal_address_from.strftime('%d.%m.%Y'),
                    self.profile.legal_address_to.strftime('%d.%m.%Y'),
                )
        if self.profile.fact_address_status:
            return 'Собственность'
        return 'Аренда от %s до %s' % (
            self.profile.fact_address_from.strftime('%d.%m.%Y'),
            self.profile.fact_address_to.strftime('%d.%m.%Y'),
        )

    @cached_property
    def rmsp_type(self):
        return ConclusionsLogic.get_conclusion_result(
            client=self.client,
            conclusion=RMSPConclusion,
        ).other_data['validation_result']

    @cached_property
    def rmsp(self):
        return ConclusionsLogic.get_conclusion_result(
            client=self.client,
            conclusion=RMSPConclusion,
        ).result

    @cached_property
    def stop_factor1(self):
        """
        Сумма гарантии > 50 000 000 руб. (для Принципалов, применяющих УСН:
            Сумма гарантии - >3 000 000 руб.,
        для Принципалов, со средним фин. положением отнесенных к сегменту МСП:
            сумма гарантии>10 000 000 руб.,
        для Принципалов, со средним фин. положением не отнесенных к сегменту МСП:
            сумма гарантии>1 000 000 руб.)
        """

        if self.profile.tax_system == TaxationType.TYPE_USN:
            result = self.request.required_amount > 3000000
        elif self.client_rating.finance_state == ['среднее']:
            if self.rmsp:
                result = self.request.required_amount > 10000000
            else:
                result = self.request.required_amount > 1000000
        else:
            result = self.request.required_amount > 50000000
        return self.fail_stop_factor if result else self.pass_stop_factor

    @cached_property
    def stop_factor2(self):
        """
        Отсутствие исполненных договоров/контрактов в рамках ФЗ 44-ФЗ и/или ФЗ №223-ФЗ
        по аналогичному направлению деятельности (не менее 1 исполненного надлежащим
        образом договора/контракта). (Применяется для Принципалов:
            (а) зарегистрированных в регионах отличных от регионов присутствия Банка
            (б) применяющих УСН
            (в) Принципалов-ИП)
        """
        # TODO добавить после обновленя парсеров
        return self.pass_stop_factor

    @cached_property
    def stop_factor3(self):
        """
            Совокупный объем обязательств Принципала по выданным гарантиям
            (с учетом суммы рассматриваемой гарантии) > 100 000 000 руб.
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor4(self):
        """
            Более 6 кал. месяцев (для тендерных гарантий)/более 60 кал. месяцев
            (для гарантий исполнения обязательств)
        """
        result = False
        if Target.PARTICIPANT in self.request.targets and self.request.interval > 186:
            result = True
        if Target.EXECUTION in self.request.targets and self.request.interval > 1860:
            result = True
        return self.fail_stop_factor if result else self.pass_stop_factor

    @cached_property
    def stop_factor5(self):
        """Нерезидент РФ"""
        if self.profile.general_director.resident:
            return self.pass_stop_factor
        else:
            return self.fail_stop_factor

    @cached_property
    def stop_factor6(self):
        """
            Принципал/Бенефициар зарегистрирован на территории субъекта РФ из списка
            запрещенных регионов
        """
        from cabinet.base_logic.scoring.functions import StopRegionsScoring
        return self.pass_stop_factor if StopRegionsScoring(
            self.request.bank, self.request, settings={}
        ).validate().is_success else self.fail_stop_factor

    @cached_property
    def stop_factor7(self):
        """Срок регистрации Принципала:
            -для Принципалов с регистрацией в регионе присутствия Банка - менее
            6 кал. месяцев
            - для Принципалов-ИП, Для Принципалов с регистрацией не в регионе присутствия
             Банка, а также Принципалов, применяющих УСН
             (вне зависимости от региона регистрации) - менее 12 кал. месяцев """
        if (timezone.now().date() - self.profile.reg_state_date).days >= 186:
            return self.pass_stop_factor
        else:
            return self.fail_stop_factor

    @cached_property
    def stop_factor8(self):
        """Регистрация по адресу массовой регистрации"""
        result = ConclusionsLogic.get_conclusion_result(
            client=self.client,
            conclusion=AddressOfManyRegistrationsConclusion
        )
        return self.pass_stop_factor if result.result else self.fail_stop_factor

    @cached_property
    def stop_factor9(self):
        """
        Принципал находится в списке организаций, связь с которыми по адресу,
        внесенному в ЕГРЮЛ, отсутствует
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor10(self):
        """
        Наличие сведений о Принципале, его представителях,бенефициарном владельце,
        исполнительном органе в реестре дисквалифицированных лиц
        """
        # result = all([NalogRu().is_disqualified_person(
        #     first_name=person.first_name,
        #     last_name=person.last_name,
        #     middle_name=person.middle_name,
        #     birthday=person.passport.date_of_birth if person.passport else None,
        #     organization_inn=self.profile.reg_inn,
        # ) for person in self.profile.persons])
        result = True
        return self.pass_stop_factor if result else self.fail_stop_factor

    @cached_property
    def stop_factor11(self):
        """Наличие сведений о Принципале в реестре недобросовестных поставщиков"""
        if not self.zachestnyibiznes_data['НедобросовПостав']:
            return self.pass_stop_factor
        else:
            return self.fail_stop_factor

    @cached_property
    def stop_factor12(self):
        """Наличие находящихся в производстве судебных дел (арбитражных производств),
        в которых Принципал выступает ответчиком, публичной информации о неисполненном
        судебном акте по взысканию денежных средств с Принципала (как с ответчика) на
        сумму более 25% от валюты баланса Принципала на последнюю отчетную дату. """
        return self.pass_stop_factor

    @cached_property
    def stop_factor13(self):
        """
        Наличие незавершенных исполнительных производств по кредитным
        обязательствам Принципала
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor14(self):
        """
        Наличие незавершенных исполнительных производств по иным  обязательствам
        Принципала на сумму более 25% от валюты баланса Принципала на последнюю
        отчетную дату.
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor15(self):
        """
        Недействительность паспорта граждан РФ Принципала/его
        представителей/руководителей/бенефициарных владельцев
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor16(self):
        """
        Сведения о Принципале, его представителях и бенефициарным владельце
        установлены в перечне организаций и физических лиц, в отношении которых имеются
        сведения об их причастности к экстремистской деятельности или терроризму
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor17(self):
        """
        Сведения о Принципале имеются в списках 193-Т (неблагонадежные участники ВЭД)
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor18(self):
        """
        Сведения о Принципале, его представителях и бенефициарным владельце имеются в
        перечне лиц,  в отношении которых имеются сведенья об их причастности к
        распространению оружия массового уничтожения
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor19(self):
        """
        Отраслевая принадлежность Принципала (по основному ОКВЭД) принадлежит одному
        из запрещенных по Продукту отраслей """
        return self.pass_stop_factor

    @cached_property
    def stop_factor20(self):
        """
        Предмет Контракта договора (ОКПД) принадлежит одному из запрещённых кодов
        экономической деятельности.
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor21(self):
        """
        Ликвидация, предстоящая ликвидация, любые формы реорганизации, банкротство,
        процедура банкротства, исключение из ЕГРЮЛ/ЕГРИП,  недействующее лицо
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor22(self):
        """
        Поручитель/его бенефициарный владелец является единственным участников
        (учредителе)поручителем в отношении юридического лица или ИП, в отношении
        которого введена процедура банкротства/ликвидации/приостановления
        деятельности
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor23(self):
        """Наличие убытков за последний завершенный финансовый год и/или на последнюю
        отчетную дату, не перекрытых прибылью за последний завершенный финансовый год
        (для Принципалов, применяющих ОСН)/Наличие убытков за последний завершенный
        финансовый год и/или на последнюю отчетную дату, не перекрытых прибылью за
        последний завершенный финансовый год (по бухгалтерской отчетности)и/или
        отсутствие дохода за последний завершенный финансовый год по налоговой декларации,
         оформляемой в соответствии с применяемой системой налогообложения (для
         Принципалов, применяющих УСН) """
        return self.pass_stop_factor

    @cached_property
    def stop_factor24(self):
        """
        Отрицательная величина чистых активов за последний завершенный год и/или
        последнюю отчетную дату, определяемая по данным формы по ОКУД 0710001
        «Бухгалтерский баланс» (1600 - (1400 + 1500 - 1530) за последний отчетный квартал.
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor25(self):
        """
        Выручка от реализации за последний завершенный финансовый год менее суммы
        контракта на заключение которого/в обеспечение обязательств по которому
        испрашивается гарантия (с учетом срока контракта)
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor26(self):
        """
        Наличие расхождений показателей налоговой декларации в соответствии с применяемой
        формой налогообложения (строки «Доходы от реализации», «Налоговая база для
        исчисления налога» и «Сумма исчисленного налога») саналогичными показателями формы
        «Отчет о финансовых результатах» за последний завершённый финансовый год
        (применяется для Принципалов, применяющих УСН)
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor27(self):
        """
        Отсутствие исполненных договоров/контрактов в рамках ФЗ 44-ФЗ и/или ФЗ №223-ФЗ
        по аналогичному направлению деятельности (не менее 1 исполненного надлежащим
        образом договора/контракта). (Применяется для Клиентов:
            (а) зарегистрированных в регионах отличных от регионов присутствия Банка
            (б) применяющих УСН (в) Клиентов-ИП
        )
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor28(self):
        """
        Финансовое положение на последнюю отчетную дату "Плохое"
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor29(self):
        """
        Наличие просроченной задолженности и/или отрицательной кредитной истории
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor30(self):
        """
        Наличие текущей картотеки неоплаченных расчетных документов к банковским счетам
        Принципала в сумме более 5,0 т.р.
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor31(self):
        """
        По Принципалу имеются действующие решения о приостановлении операций по счетам
        и переводам электронных ден. средств
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor32(self):
        """
        Наличие просроченной задолженности по налогам, сборам и иным обязательным
        платежам, а также срочной задолженности в стадии исполнительного производства
        в сумме более 1 000 руб.
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor33(self):
        """
        Наличие просроченной задолженности перед работниками по заработной плате
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor34(self):
        """
        Наличие скрытых потерь  в размере, равном или превышающем 25 процентов чистых
        активов Принципала на последнюю отчетную дату.
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor35(self):
        """
        Наличие у Принципала случаев неисполнения обязательств по иным договорам ,
        при условии, что их совокупная величина превышает 100,0 т.р.
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor36(self):
        """Не предусмотренное планом развития Принципала  существенное (на 25% и более)
        снижение его чистых активов на последнюю отчетную квартальное дату по сравнению с
        их значением за последний завершенный финансовый год
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor37(self):
        """
        Наличие текущего убытка (перекрытого прибылью последнего завершенного
        финансового года), приведшего к снижению (25%  и более) чистых активов по
        сравнению с их значением за последний завершенный финансовый год (при условии,
        что ЧА  имеют положительное значение).
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor38(self):
        """
        Наличие информации о представлении Принципалом формы № 1 с нулевыми значениями
        «Оборотные активы», «Краткосрочные обязательства»,  при наличии информации об
        оборотах по счетам в Банке или в других банках за последние 180 кал. дней
        (1 000,0 т.р. и более)
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor39(self):
        """
        Наличие просроченной дебиторской/кредиторской задолженности, просроченных
        собственных векселей длительностью свыше 3 месяцев, просроченных финансовых
        вложений в размере более 25% от величины чистых активов на последнюю отчетную дату
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor40(self):
        """
        Существенное (более чем на 50% увеличение дебиторской задолженности и/или
        кредиторской задолженности за период с 31 декабря предшествующего года по
        последнюю календарную квартальную дату при убыточной деятельности на последнюю
        квартальную дату
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor41(self):
        """
        Наличие у Принципала безнадежных активов/неликвидных запасов в размере, равном
        или превышаюшем 25% чистых активов на последнюю отчетную дату
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor42(self):
        """
        Наличие в балансе (форма №1) за последний завершенный финансовый год нулевых
        значений по разделам "Оборотные активы", "Краткосрочные обязательства"
        одновременнно при наличии оборота по счетам за последние 180 дн в размере
        1 000,0 тыс.руб. и более
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor43(self):
        """
        Смена единоличного исполнительного органа  Принципала  3 раза и более
        за последний год
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor44(self):
        """
        Неоднократная утрата Принципалом  правоустанавливающих, первичных учетных
        документов, оригиналов договоров контрактов за последние 3 года
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor45(self):
        """
        Наличие фактов изменения места постановки Принципала на налоговый учет
        более 2-х раз за календарный год
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor46(self):
        """
        Наличие фактов непредоставления Принципалом по запросам документов
        и/или информации
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor47(self):
        """
        Отсутствие у Принципала собственных либо находящихся в пользовании (аренде)
        основных средств или иного имущества, необходимого для осуществления деятельности
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor48(self):
        """
        Отсутствие в штате Принципала должности главного бухгалтера или бухгалтерской
        службы (за исключением случаев передачи ведения бухгалтерского учета на аутсорсинг
        или ведения бухгалтерского учета исполнительным органом принципала лично)
        (не применяется для Принципалов-субъектов МСП)
        """
        return self.pass_stop_factor

    @cached_property
    def stop_factor49(self):
        """
        В штате Принципала отсутствуют работники помимо единоличного исполнительного
        органа и главного бухгалтера (не применяется для Принципалов-субъектов МСП)
        """
        return self.pass_stop_factor

    @cached_property
    def quarters(self):
        return self.client.accounting_report.get_quarters()

    @cached_property
    def last_quarter(self):
        return self.client.accounting_report.get_last_closed_quarter()

    @cached_property
    def pre_year_quarter(self):
        return self.client.accounting_report.get_year_quarter()

    @cached_property
    def targets(self):
        return ','.join([dict(Target.CHOICES)[target] for target in self.request.targets])

    @cached_property
    def print_offer_commission(self):
        return number2string(self.request.offer.commission)

    @cached_property
    def commission_percent(self):
        offer_commission = float(self.request.offer.commission or 0)
        required_amount = float(self.request.required_amount)
        interval = self.request.interval

        commission = (offer_commission * 365.5 * 100) / (required_amount * interval)
        return round(commission, 2)

    @cached_property
    def contracts(self):
        return self.contracts_info.contracts

    @cached_property
    def last_3_year_contracts(self):
        return self.contracts_info.last_3_year_contracts

    @cached_property
    def similar_contracts(self):
        return self.contracts_info.similar_contracts

    @cached_property
    def number_of_similar_contracts(self):
        return len(self.similar_contracts)

    @cached_property
    def client_rating_calculator(self):
        from bank_guarantee.bank_integrations.spb_bank.helpers import get_client_rating_calculator  # noqa
        return get_client_rating_calculator(self.request)

    @cached_property
    def reverse_client_rating_calculator(self):
        from bank_guarantee.bank_integrations.spb_bank.helpers import get_client_rating_calculator  # noqa
        return get_client_rating_calculator(self.request, analog_period=True)

    @cached_property
    def client_rating(self):
        return ClientRatingTranslator.translate(
            self.client_rating_calculator.calculated_score
        )

    @cached_property
    def tender_count(self):
        return len(self.contracts)

    @cached_property
    def contract_count(self):
        return len(self.contracts)

    @cached_property
    def customer_count(self):
        names = []
        for fz in self.contracts.keys():
            for contract in self.contracts[fz]:
                name = contract.issuer_name
                if name:
                    names.append(name)
        return len(set(names))

    @cached_property
    def fz44_contracts(self):
        return list(filter(
            lambda x: x.law == '44fz',
            self.last_3_year_contracts
        ))

    @cached_property
    def fz223_contracts(self):
        return list(filter(
            lambda x: x.law == '223fz',
            self.last_3_year_contracts
        ))

    @cached_property
    def only_beneficiary(self):
        return []
        # TODO: Поправить
        # return list(filter(
        #     lambda x: x['customer']['inn'] == self.request.tender.beneficiary_inn,
        #     self.last_3_year_contracts
        # ))

    @cached_property
    def fz44_similar_contracts(self):
        return list(filter(
            lambda x: x.law == '44fz',
            self.similar_contracts
        ))

    @cached_property
    def fz223_similar_contracts(self):
        return list(filter(
            lambda x: x.law == '223fz',
            self.similar_contracts
        ))

    @cached_property
    def only_similar_beneficiary(self):
        return []
        # TODO: поправить
        # return list(filter(
        #     lambda x: x['customer']['inn'] == self.request.tender.beneficiary_inn,
        #     self.similar_contracts
        # ))

    @cached_property
    def average_percent(self):
        """Средний процент снижения на закупках"""
        return 0

    @cached_property
    def net_assets_last_quarter(self):
        """ЧА за прошлый квартал"""
        return self.last_quarter.get_value(1600) - (
                self.last_quarter.get_value(1400) +
                self.last_quarter.get_value(1500) -
                self.last_quarter.get_value(1530))

    @cached_property
    def net_assets_pre_year(self):
        """ЧА за прошлый год"""
        return self.pre_year_quarter.get_value(1600) - (
                self.pre_year_quarter.get_value(1400) +
                self.pre_year_quarter.get_value(1500) -
                self.pre_year_quarter.get_value(1530))

    @cached_property
    def signer_from_bank(self):
        """Подписант от банка"""
        return self.request.assigned

    @cached_property
    def doc_signer_from_bank(self):
        """Документ подписанта"""
        if self.signer_from_bank:
            return self.signer_from_bank.additional_data.get('doc')

    @cached_property
    def position_signer_from_bank(self):
        """Должность подписантв"""
        if self.signer_from_bank:
            return self.signer_from_bank.position

    @cached_property
    def fio_signer_from_bank(self):
        """ФИО подписанта"""
        if self.signer_from_bank:
            return self.signer_from_bank.full_name
