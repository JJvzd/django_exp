import json

import pytest


@pytest.mark.django_db
def test_confirm_pay(client):
    response = client.post('/12343/confirm-pay', data=json.dumps({}), content_type='application/json').json()
    assert response == {'err_code': 1, 'err_text': 'Не найдена заявка по orderId для банка'}
