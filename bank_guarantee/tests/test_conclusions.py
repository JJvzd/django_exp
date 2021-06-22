import json
import os

import requests_mock

from clients.models import Client
from conclusions_app.conclusions.base import ConclusionResult
from conclusions_app.conclusions.common import (
    GosContractsConclusion, CheckPassportConclusion
)
from conclusions_app.conclusions.zachestniybiznes import FSSPConclusion
from conclusions_app.conclusions_logic import ConclusionsLogic
from questionnaire.models import Profile, ProfilePartnerIndividual, PassportDetails


def test_get_gos_contracts():
    with requests_mock.mock() as m:
        response = open(os.path.join(
            os.path.dirname(__file__),
            './files/get_gos_contracts.html'
        ), 'r').read()
        m.get(
            'https://clearspending.ru/supplier/inn=6604018308&kpp=667801001',
            text=response
        )
        assert ConclusionsLogic.generate_conclusion(
            client=Client(inn='6604018308', kpp='667801001'),
            conclusion=GosContractsConclusion
        ) == ConclusionResult(
            result=True,
            other_data={
                'validation_result': 'Всего контрактов 21 на сумму 442 036 584 '
                                     'руб.<br>Контрактов 21 по Всего на сумму 4'
                                     '42 036 584 руб.<br>Контрактов 20  по  44/'
                                     '94-ФЗ на сумму 442 036 584  руб.'
            },
            file=None
        )


def test_passport_validate(rm):
    rm.register_uri(
        'GET',
        url='//parsers.tenderhelp.ru/api/passport_is_expired/',
        text='{"result":true}'
    )
    client = Client(profile=Profile())
    client.profile.general_director = ProfilePartnerIndividual(
        passport=PassportDetails(
            series='6704',
            number='007623'
        )
    )

    assert ConclusionsLogic.generate_conclusion(
        client=client,
        conclusion=CheckPassportConclusion
    ) == ConclusionResult(
        result=False,
        other_data={
            'validation_result': 'Паспорт не действителен'
        },
        file=None
    )


def test_fssp(rm):
    rm.register_uri(
        'GET',
        url='//zachestnyibiznesapi.ru/paid/data/fssp?id=1147746940802',
        text='{"status":"235","message":"По данному ОГРН не найдено исполнительных производств."}'
    )
    rm.register_uri(
        'GET',
        url='//zachestnyibiznesapi.ru/paid/data/fssp?id=1085047008474',
        text=json.dumps({
            "status": "200", "message": "Запрос выполнен успешно",
            "body": [
                {
                    "Должник": "ООО ПСО \"АЛЬЯНС\"",
                    "Адрес": "РОССИЯ,141407,МОСКОВСКАЯ ОБЛ,ХИМКИ Г,МОЛОДЕЖНАЯ УЛ,50,",
                    "НомИспПроизв": "25402/18/50043-ИП",
                    "ДатаВозбуждения": 1525640400,
                    "НомСводнИспПроизв": "",
                    "ТипИспДок": "Акт по делу об административном правонарушении",
                    "ДатаИспДок": 1433278800,
                    "НомИспДок": "1203-Ю",
                    "ТребИспДок": " Постановление о взыскании исполнительского сбора "
                                  "Постановление о взыскании расходов по совершению "
                                  "исполнительных действий",
                    "ПредметИсп": "Штраф иного органа",
                    "СуммаДолга": "150000",
                    "ОстатокДолга": "150000",
                    "ОтделСудебПрист": "Химкинский РОСП ",
                    "АдрОтделаСудебПрист": "141411, Московская область г.Химки, "
                                           "ул.Победы, д.3"
                }
            ]
        })
    )
    client = Client(ogrn=1147746940802)
    assert ConclusionsLogic.generate_conclusion(
        client=client,
        conclusion=FSSPConclusion
    ) == ConclusionResult(
        result=True,
        other_data={
            'validation_result': '<html><head></head><body><span style="font-'
                                 'size: 16px; font-weight: bold">Судебные дел'
                                 'а</span> Не найдено</body></html>'
        },
        file=None
    )

    client = Client(ogrn=1085047008474)
    assert ConclusionsLogic.generate_conclusion(
        client=client,
        conclusion=FSSPConclusion
    ) == ConclusionResult(
        result=False,
        other_data={
            'validation_result': '<html><head></head><body><span style="font-size: 16px; '
                                 'font-weight: bold">Судебные '
                                 'дела</span><table><thead><tr><th><b>Должник</b><br/> '
                                 '(юр. лицо: наименование, юр. '
                                 'адрес)</th><th><b>Исполнительное производство</b><br/> '
                                 '(номер, дата возбуждения)</th><th><b>Реквизиты '
                                 'исполнительного документа</b><br/> (вид, дата принятия, '
                                 'номер, наименование органа, выдавшего исполнительный '
                                 'документ)</th><th><b>Предмет исполнения, сумма '
                                 'непогашенной задолженности</b></th><th><b>Отдел '
                                 'судебных приставов</b><br/> (наименование, '
                                 'адрес)</th></tr></thead><tbody><tr><td>ООО ПСО '
                                 '"АЛЬЯНС"<br/> РОССИЯ,141407,МОСКОВСКАЯ ОБЛ,ХИМКИ '
                                 'Г,МОЛОДЕЖНАЯ УЛ,50,</td><td>25402/18/50043-ИП, '
                                 '07.05.2018</td><td>Акт по делу об административном '
                                 'правонарушении,03.06.2015, 1203-Ю, Постановление о '
                                 'взыскании исполнительского сбора Постановление о '
                                 'взыскании расходов по совершению исполнительных '
                                 'действий</td><td>Штраф иного органа, '
                                 '150000</td><td>Химкинский РОСП , 141411, Московская '
                                 'область г.Химки, ул.Победы, '
                                 'д.3</td></tr></tbody></table></body></html>'
        },
        file=None
    )
