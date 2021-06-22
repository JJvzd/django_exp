from typing import Union

from external_api.parsers_tenderhelp import ParsersApi


def check_passport(series: str, number: str) -> Union[bool, None]:
    """
        None: 'Данные не заполнены',
        False: 'Паспорт действительный',
        True: 'Паспорт не действителен'
    """
    return ParsersApi().passports.check_passport(
        series=series,
        number=number,
    )
