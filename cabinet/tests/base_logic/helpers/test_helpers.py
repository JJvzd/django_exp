import pytest

from cabinet.base_logic.helpers.check_data import check_in_regions


@pytest.mark.parametrize('inn, kpp, regions, result', [
    ['12345', '67890', ['12'], True],
    ['12345', '67890', ['123'], True],
    ['12345', '67890', ['67'], True],
    ['12345', '12890', ['67'], False],
    ['12345', None, ['12'], True],
])
def test_check_in_regions(inn, kpp, regions, result):
    assert check_in_regions(inn, regions, kpp) == result
