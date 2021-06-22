import datetime

import pytest

from bank_guarantee.models import RequestStatus, Request, RequestPrintForm
from base_request.models import RequestTender
from cabinet.base_logic.printing_forms.generate import RequestPrintFormGenerator
from cabinet.constants.constants import Target, FederalLaw
from clients.models import Bank, Client
from questionnaire.models import ProfilePartnerLegalEntities, ProfilePartnerIndividual
from settings.configs.banks import BankCode
from utils.functions_for_tests import create_request, random_number_string


@pytest.mark.parametrize('base_request', [
    Request(required_amount=12000000, targets=Target.EXECUTION, tender=RequestTender(federal_law=FederalLaw.LAW_44)),
    Request(required_amount=12000000, targets=Target.PARTICIPANT, tender=RequestTender(federal_law=FederalLaw.LAW_44)),
    Request(required_amount=12000000, targets=Target.PARTICIPANT, tender=RequestTender(federal_law=FederalLaw.LAW_223)),
    Request(required_amount=12000000, targets=Target.EXECUTION, tender=RequestTender(federal_law=FederalLaw.LAW_223)),
    Request(required_amount=12000000, targets=Target.AVANS_RETURN,
            tender=RequestTender(federal_law=FederalLaw.LAW_223)),
    Request(required_amount=12000000, targets=Target.WARRANTY, tender=RequestTender(federal_law=FederalLaw.LAW_223)),
])
@pytest.mark.django_db
def test_spb_forms_bg_project(base_request, rm, initial_data_db):
    rm.register_uri('GET', url='//search.tenderhelp.ru/api/v1/contracts/search/', text='{}')
    print_form_type = 'spb_guarantee'
    request = create_request(
        request=base_request,
        bank=Bank.objects.get(code=BankCode.CODE_INBANK),
        status=RequestStatus.CODE_SEND_TO_BANK
    )
    print_form, _ = RequestPrintForm.objects.get_or_create(type=print_form_type, defaults=dict(
        name=print_form_type,
        download_name=print_form_type,
    ))
    helper = RequestPrintFormGenerator()
    helper.generate_print_form(request=request, print_form=print_form)
    doc = request.requestdocument_set.filter(print_form__type=print_form_type).first()
    assert doc is not None
    doc.delete()


@pytest.mark.django_db
def test_spb_forms_profile(initial_data_db):
    print_form_type = 'doc'
    request = create_request(
        request=Request(
            required_amount=12000000, targets=Target.EXECUTION,
            interval_from=datetime.datetime(year=2020, month=1, day=1),
            interval_to=datetime.datetime(year=2020, month=1, day=1) + datetime.timedelta(days=20),
            tender=RequestTender(
                federal_law=FederalLaw.LAW_44,
                beneficiary_inn='7727276879'
            )
        ),
        client=Client(
            inn='1659167645',
        ),
        legal_shareholders=[ProfilePartnerLegalEntities(name='test', share=100, inn=random_number_string(10))],
        person_shareholders=[
            ProfilePartnerIndividual(
                first_name='test', last_name='test', middle_name='test', share=100,
                fiz_inn=random_number_string(10), is_general_director=True)],
        bank=Bank(code=BankCode.CODE_SPB_BANK),
        status=RequestStatus.CODE_SEND_TO_BANK
    )
    print_form, _ = RequestPrintForm.objects.get_or_create(type=print_form_type, filename='spb_profile.docx', defaults=dict(
        name=print_form_type,
        download_name=print_form_type,
        bank=request.bank,
    ))
    helper = RequestPrintFormGenerator()
    helper.generate_print_form(request=request, print_form=print_form)
    doc = request.requestdocument_set.filter(print_form__filename='spb_profile.docx').first()
    assert doc is not None
    doc.delete()
