import pytest

from bank_guarantee.models import Request
from cabinet.base_logic.package.base import ValidateBlock
from clients.models import Bank


@pytest.mark.parametrize('f', [
    'OrgValidationBlock',
    'hasBeneficiars',
    'hasContractsExperience',
    'hasLicencies',
    'hasPoA',
    'isAO',
    'isBigDeal',
    'isENVD',
    'isESHN',
    'isGenBuhNotGenDir',
    'isIpOrg',
    'isUrOrg',
    'isOAO',
    'isOOO',
    'isOSN',
    'isOtherOrg',
    'isPAO',
    'isZAO',
    'isPSN',
    'isUSN',
    'sumInRange',
])
def test_get_package_function(f):
    assert ValidateBlock.get_class(f).__name__ == f


def test_sumInRange():
    """ Тестирование функции sumInRange """
    result_true = ValidateBlock('sumInRange', [10, 12]).validate(Request(
        required_amount=10
    ), Bank())
    assert result_true is True

    result_false = ValidateBlock('sumInRange', [10, 12]).validate(Request(
        required_amount=7
    ), Bank())
    assert result_false is False

    result_false = ValidateBlock('sumInRange', [10, 12]).validate(Request(
        required_amount=13
    ), Bank())
    assert result_false is False


def test_sumNotInRange():
    """ Тестирование функции sumNotInRange """
    result_true = ValidateBlock('sumNotInRange', [10, 12]).validate(Request(
        required_amount=10
    ), Bank())
    assert result_true is False

    result_false = ValidateBlock('sumNotInRange', [10, 12]).validate(Request(
        required_amount=7
    ), Bank())
    assert result_false is True

    result_false = ValidateBlock('sumNotInRange', [10, 12]).validate(Request(
        required_amount=13
    ), Bank())
    assert result_false is True
