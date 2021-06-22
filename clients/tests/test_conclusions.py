import json

import requests_mock
from django.test import TestCase

from clients.client_conclusion import ClientConclusionManagement
from common.helpers import mock_requests

NALOG_FALSE_RESULT = {
    "queryType": "FINDPRS",
    "bikPRS": "044525225",
    "innPRS": "2465190460",
    "formToken": "5678E5BBC7E48B03225214702130572BBC2E617EAE3A041549814DFB37E9B4D698F93B84255B35987DDA5E572E163E12B1A8A33CEA677B1862286DE31D34A9E7",
    "datePRS": "05.12.2019 12:02:43",
    "captchaRequired": False
}

NALOG_TRUE_RESULT = {
    "queryType": "FINDPRS",
    "bikPRS": "044525225",
    "innPRS": "2464075377",
    "formToken": "CA732C5F5875620202063FC5CB5C58EEDDA60C8C046FE921C9FA7A20F396650DF235834CFE255141551A72D8F56A07E7A0D838A5FCD1F30B34A291884FB30CDC",
    "datePRS": "05.12.2019 12:06:32",
    "captchaRequired": True,
    "rows": [
        {
            "R": 1,
            "INN": "2464075377",
            "NAIM": "АКЦИОНЕРНОЕ ОБЩЕСТВО \"КРАСНОЯРСКГРАФИТ\"",
            "IFNS": "2464",
            "DATA": "02.12.2019",
            "BIK": "040407595",
            "NOMER": "32505",
            "DATABI": "03.12.2019 05:26:29",
            "TOKEN": "CEE0B03481C68C9E4CF6102C83190225D3D7034C839993B6945F73A340F8C10D25EA89F008E39DCA464E85B5276E5E96",
            "ID": -1
        },
        {
            "R": 2,
            "INN": "2464075377",
            "NAIM": "АКЦИОНЕРНОЕ ОБЩЕСТВО \"КРАСНОЯРСКГРАФИТ\"",
            "IFNS": "2464",
            "DATA": "03.12.2019",
            "BIK": "040407595",
            "NOMER": "32772",
            "DATABI": "03.12.2019 18:32:53",
            "TOKEN": "8566C46E651669C7B22145C63299E87D3FA5AB6A0F6E2E36ECEFD6EDDAE3C44E9BE90999387FCD57A388F7B94C4AE614",
            "ID": -1
        },
        {
            "R": 3,
            "INN": "2464075377",
            "NAIM": "АКЦИОНЕРНОЕ ОБЩЕСТВО \"КРАСНОЯРСКГРАФИТ\"",
            "IFNS": "2464",
            "DATA": "02.12.2019",
            "BIK": "040407627",
            "NOMER": "32507",
            "DATABI": "03.12.2019 05:26:29",
            "TOKEN": "AAB473D3B5BF7EA36FC2D87D1F3A02EC88342E3F395BB658023E62ABCD29803C7B6B012D630438AAD8B9A5B42DC48D26",
            "ID": -1
        },
        {
            "R": 4,
            "INN": "2464075377",
            "NAIM": "АКЦИОНЕРНОЕ ОБЩЕСТВО \"КРАСНОЯРСКГРАФИТ\"",
            "IFNS": "2464",
            "DATA": "03.12.2019",
            "BIK": "040407627",
            "NOMER": "32774",
            "DATABI": "03.12.2019 14:26:34",
            "TOKEN": "4BD92F8ABF966B6707B8026ED3DCF4ABC213E14DD901E6ABB77411CD365A4075A36D9073CEDF15FFF98A6429F035A916",
            "ID": -1
        },
        {
            "R": 5,
            "INN": "2464075377",
            "NAIM": "АКЦИОНЕРНОЕ ОБЩЕСТВО \"КРАСНОЯРСКГРАФИТ\"",
            "IFNS": "2464",
            "DATA": "02.12.2019",
            "BIK": "045004774",
            "NOMER": "32506",
            "DATABI": "03.12.2019 05:26:29",
            "TOKEN": "D91864333D8347C9B9B7DE593FC8F20DFC5CFEADC2CAB4774CEEBBA7D813F9A5",
            "ID": -1
        },
        {
            "R": 6,
            "INN": "2464075377",
            "NAIM": "АКЦИОНЕРНОЕ ОБЩЕСТВО \"КРАСНОЯРСКГРАФИТ\"",
            "IFNS": "2464",
            "DATA": "03.12.2019",
            "BIK": "045004774",
            "NOMER": "32773",
            "DATABI": "03.12.2019 14:26:34",
            "TOKEN": "44349399B51A7E7B2C6B03D15E25B7701EEBBFE0AD8D6DABCA68B186AD27005FDDC729C524962B8E5BDAE7E60ECA3B015356D0479C3ACB68C28867B4C80D5A5A",
            "ID": -1
        },
        {
            "R": 7,
            "INN": "2464075377",
            "NAIM": "АКЦИОНЕРНОЕ ОБЩЕСТВО \"КРАСНОЯРСКГРАФИТ\"",
            "IFNS": "2464",
            "DATA": "02.12.2019",
            "BIK": "045004867",
            "NOMER": "32508",
            "DATABI": "03.12.2019 05:26:29",
            "TOKEN": "2C7D37CE6573E3677E3CF543C86E3A22D71A1FBFB504A0D6F16631266E08B8265E233262AEEEC7471B22289547EFA0BC",
            "ID": -1
        },
        {
            "R": 8,
            "INN": "2464075377",
            "NAIM": "АКЦИОНЕРНОЕ ОБЩЕСТВО \"КРАСНОЯРСКГРАФИТ\"",
            "IFNS": "2464",
            "DATA": "03.12.2019",
            "BIK": "045004867",
            "NOMER": "32775",
            "DATABI": "03.12.2019 14:26:34",
            "TOKEN": "FAE8AA49E0DD41BA555D5F6EE7AF947AA4EBF1971C1B91089BF99ECB8215AC40584FDF5170C5A32088EBBADC772DEB1F",
            "ID": -1
        }
    ]
}


class ClientConsolutionsManagementTestCase(TestCase):
    def setUp(self):
        self.client_consolutions_management_1 = ClientConclusionManagement(
            '0902038605'
        )
        self.client_consolutions_management_2 = ClientConclusionManagement(
            '0902038606'
        )
        self.client_consolutions_management_1._set_value_in_caches(
            '0902038607',
            True
        )

    def test_check_in_vestnik(self):
        with requests_mock.mock() as m:
            m.post('https://www.vestnik-gosreg.ru/publ/fz83/', text=' ')
            self.assertFalse(
                self.client_consolutions_management_1.check_in_vestnik()
            )
            self.assertFalse(
                self.client_consolutions_management_1.check_in_vestnik()
            )
            self.assertFalse(
                self.client_consolutions_management_2.check_in_vestnik()
            )

    def test_get_value_from_caches(self):
        self.assertEqual(
            None,
            self.client_consolutions_management_1._get_value_from_caches(
                '0902038605'
            )
        )
        self.client_consolutions_management_1._set_value_in_caches('0902038605', True)
        self.assertEqual(
            True,
            self.client_consolutions_management_1._get_value_from_caches(
                '0902038607'
            )
        )

    def test_check_in_service_nalog(self):
        with requests_mock.mock() as m:
            m.post('https://service.nalog.ru/bi.do/bi2-proc.json', text=json.dumps(NALOG_TRUE_RESULT))
            assert self.client_consolutions_management_1.check_in_service_nalog(
                '2464075377',
                '044525225'
            ) is True


    @mock_requests(json=NALOG_FALSE_RESULT)
    def test_check_in_service_nalog_false(self):
        with requests_mock.mock() as m:
            m.post('https://service.nalog.ru/bi.do/bi2-proc.json', text=json.dumps(NALOG_FALSE_RESULT))
            self.assertFalse(
                self.client_consolutions_management_1.check_in_service_nalog(
                    '2465190460',
                    '044525225'
                )
            )
