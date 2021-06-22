import json
import os

import pytest
from django.core.files import File

from bank_guarantee.models import RequestPrintForm, Request
from cabinet.base_logic.printing_forms.base import PrintForm
from cabinet.constants.constants import Target
from clients.models import Bank


@pytest.mark.django_db
def test_select_rule(initial_data_db):
    print_form = RequestPrintForm.objects.create(
        type=PrintForm.TYPE_DOC,
        enable_rules=True
    )
    f = open(os.path.join(os.path.dirname(__file__), 'files/test.doc'), 'rb')

    print_form.rules.create(
        template=File(f, name='test.doc'),
        policy=json.dumps({
            'alghoritm': 'DenyUnlessPermit',
            'description': 'Только на исполнение',
            'target': [],
            'rules': [],
            'policies': [
                {
                    'alghoritm': 'DenyUnlessPermit',
                    'description': '',
                    'target': [
                        {
                            'attribute': 'request.targets',
                            'operation': 'AnyIn',
                            'value': [Target.EXECUTION]
                        }

                    ],
                }
            ]
        })
    )
    print_form.rules.create(
        template=File(f, name='test1.doc'),
        policy=json.dumps({
            'alghoritm': 'DenyUnlessPermit',
            'description': 'Только на участие',
            'target': [],
            'rules': [],
            'policies': [
                {
                    'alghoritm': 'DenyUnlessPermit',
                    'description': '',
                    'target': [
                        {
                            'attribute': 'request.targets',
                            'operation': 'AnyIn',
                            'value': [Target.PARTICIPANT]
                        }

                    ],
                }
            ]
        })
    )
    request1 = Request(bank=Bank(), targets=[Target.EXECUTION, Target.WARRANTY])
    request2 = Request(bank=Bank(), targets=[Target.PARTICIPANT])
    template = print_form.get_template(request=request1, bank=request1.bank)
    assert template is not None
    assert template.endswith('test.doc')
    template = print_form.get_template(request=request2, bank=request2.bank)
    assert template is not None
    assert template.endswith('test1.doc')
    print_form.delete()
