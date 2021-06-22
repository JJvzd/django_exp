import os
from datetime import datetime

import pytest
import requests_mock
from mock import patch

from bank_guarantee.models import Request, RequestPrintForm, RequestStatus
from cabinet.base_logic.printing_forms.adapters.excel import MosComBankProfile
from clients.models import Client
from questionnaire.models import BankAccount, ProfilePartnerIndividual, PassportDetails, \
    LicensesSRO


def create_request():
    with requests_mock.mock() as m:
        client = Client.objects.create(inn='2636217250')
        client.profile.reg_state_date = datetime(year=2016, month=1, day=1).date()
        client.profile.save()
        request = Request.objects.create(
            required_amount=100000,
            client=client,
            status=RequestStatus.objects.get(code=RequestStatus.CODE_DRAFT))
        BankAccount.objects.create(
            profile=client.profile,
            bank_bik='123456',
            bank_account_number='asdgfdgfdg',
            bank='gdfgdfg'
        )

        ProfilePartnerIndividual.objects.create(
            profile=client.profile,
            is_general_director=True,
            is_booker=True,
            is_beneficiary=True,
            share=100,
            passport=PassportDetails.objects.create(
                date_of_birth=datetime(year=1992, month=1, day=1).date(),
                when_issued=datetime(year=2004, month=1, day=1).date(),
            )
        )
        LicensesSRO.objects.create(
            profile=client.profile,
            view_activity='gdfgsdfg',
            number_license='fdsgf/2334',
            date_issue_license=datetime(year=2004, month=1, day=1).date(),
            date_end_license=datetime(year=2024, month=1, day=1).date(),
        )
        LicensesSRO.objects.create(
            profile=client.profile,
            view_activity='gdgsdfgsdfgsdfg',
            number_license='fdsgf/2335',
            date_issue_license=datetime(year=2004, month=1, day=1).date(),
            date_end_license=datetime(year=2024, month=1, day=1).date(),
        )
    return request


@patch('cabinet.models.EgrulData._download_pdf',
       lambda x: os.path.join(os.path.dirname(__file__),
                              './files/ul-1192651015292-20201118121931.pdf'))
@pytest.mark.django_db
def test_base_moscombank_profile(initial_data_db, rm):
    request = create_request()
    print_form = RequestPrintForm(filename='moscombank_anketa')

    sth_resp = open(os.path.join(os.path.dirname(__file__),
                                 './files/client_2636217250_contracts.json')).read()
    rm.get(
        'http://search.tenderhelp.ru/api/v1/contracts/search/?supplierinn=2636217250&limit=1000',
        text=sth_resp)
    adapter = MosComBankProfile(request=request, print_form=print_form)
    file = adapter.generate()[0]
    assert os.path.exists(file)
    os.unlink(file)
