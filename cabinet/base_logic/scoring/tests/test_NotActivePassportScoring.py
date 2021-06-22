import pytest

from cabinet.base_logic.scoring.functions import NotActivePassportScoring

from questionnaire.models import ProfilePartnerIndividual, PassportDetails
from utils.functions_for_tests import create_request


@pytest.mark.django_db
def test_function(initial_data_db, rm):
    rm.register_uri(
        'GET',
        url='/api/passport_is_expired/?series=6704&number=007623',
        text='{"result":true}'
    )

    request = create_request(
        person_shareholders=[ProfilePartnerIndividual(
            first_name='1234',
            is_general_director=True,
            passport=PassportDetails(
                series='6704',
                number='007623'
            )
        )])
    assert request.client.profile.general_director.first_name == '1234'
    assert request.client.profile.general_director.passport.series == '6704'
    func = NotActivePassportScoring(
        bank=request.bank, request=request, settings={}
    )
    assert func.validate().result is False
