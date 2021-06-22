import pytest
from django.urls import reverse

from users.models import User
from utils.functions_for_tests import random_string


@pytest.fixture
def api_client():
   from rest_framework.test import APIClient
   return APIClient()

@pytest.fixture
def api_test_user():
    user = User.objects.create_user(
        username=random_string(10),
        email='%s@tenderhelp.ru' % random_string(6),
        password='test123456',
    )
    return user


@pytest.mark.skip
def test_get_without_auth(api_client):
    response = api_client.get(reverse('change_password'))

    assert response.status_code == 403


@pytest.mark.django_db
def test_get_with_auth(api_client, initial_data_db, api_test_user):
    api_client.force_authenticate(user=api_test_user)
    response = api_client.get(reverse('change_password'))

    assert response.status_code == 405
    assert response.data == {"detail": "Метод \"GET\" не разрешен."}


@pytest.mark.django_db
def test_post_with_auth(api_client, initial_data_db, api_test_user):
    api_client.force_authenticate(user=api_test_user)
    response = api_client.post(reverse('change_password'))

    assert response.status_code == 405
    assert response.data == {"detail": "Метод \"POST\" не разрешен."}



@pytest.mark.django_db
@pytest.mark.parametrize(
   'old_password, new_password1, new_password2, status_code', [
        (None, None, None, 400),
        (None, 'test', None, 400),
        (None, 'test','test', 400),
        ('test123456', 'test','test1', 400),
        ('test123456', 'test','test1', 400),
        ('test123456', '1234567','1234567', 400),
        ('test1234567', '12345678','12345678', 400),
        ('test123456', '12345678','12345678', 200),
   ]
)
def test_put_data_validation(
    api_client,
    initial_data_db,
    api_test_user,
    old_password,
    new_password1,
    new_password2,
    status_code
):
    api_client.force_authenticate(user=api_test_user)
    data = {
        "old_password": old_password,
        "new_password1": new_password1,
        "new_password2": new_password2,
    }
    response = api_client.put(reverse('change_password'), data=data)

    assert response.status_code == status_code
