import os

import pytest
from django.conf import settings
from django.core.files import File

from bank_guarantee.bank_integrations.spb_bank.data_translators.offer_ready import \
    OfferReadyDataTranslator
from bank_guarantee.models import RequestDocument
from base_request.models import BankDocumentType
from clients.models import Bank, BaseFile
from settings.configs.banks import BankCode
from utils.functions_for_tests import create_request

BASE64_DATA = 'wAAAAkAAAAjAAAA0LTQvtC60YPQ'


@pytest.mark.django_db
def test_export_zip_as_base64(initial_data_db):
    request = create_request(bank=Bank(code=BankCode.CODE_SPB_BANK))
    with open(os.path.join(settings.BASE_DIR, 'bank_guarantee/bank_integrations/spb_bank/tests/files/test_doc'), 'rb') as f:
        base_file = BaseFile.objects.create(
            author=request.client,
            file=File(f, name='test_doc')
        )
        RequestDocument.objects.create(
            request=request,
            category=BankDocumentType.objects.create(),
            file=base_file
        )
    assert request.requestdocument_set.count() == 1
    api = OfferReadyDataTranslator()
    data = api.encode_archive_to_base64(api.pack_request_documents_to_archive(request))
    assert len(data) > 100
