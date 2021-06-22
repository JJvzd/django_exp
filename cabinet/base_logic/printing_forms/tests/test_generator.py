import os

from mock import patch

from bank_guarantee.models import OfferPrintForm, Request, Offer
from cabinet.base_logic.printing_forms.generate import OfferPrintGenerator
from clients.models import Client
from questionnaire.models import Profile


@patch('cabinet.base_logic.printing_forms.generate.OfferPrintGenerator._get_category',
       lambda x, request, print_form: None)
def test_offer_print_form_generator():
    generator = OfferPrintGenerator()
    print_form = OfferPrintForm(type='doc', filename='bill.docx', active=True)
    request = Request(
        client=Client(profile=Profile()),
        offer=Offer()
    )
    files = generator._generate(request, print_form)
    assert len(files) == 1
    for file in files:
        os.remove(file)
