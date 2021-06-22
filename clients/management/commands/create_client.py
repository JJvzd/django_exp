import random

from django.core.management import BaseCommand

from clients.user_stories.common import create_client_company
from users.models import Role, User
from users.user_stories import create_user_via_email


class Command(BaseCommand):
    help = 'Создание компании-клиента с пользователем'

    def handle(self, *args, **options):
        inn = input("ИНН? ")
        email = input("Email? ")
        password = input('Пароль пользователя? ')

        company = create_client_company(
            inn=inn, agent_user=User.objects.filter(roles__name=Role.SUPER_AGENT).first()
        )
        create_user_via_email(
            first_name='TestFirst',
            last_name='TestLast',
            middle_name='TestMiddle',
            position='Director',
            phone=''.join([str(random.randint(1, 9)) for _ in range(11)]),
            email=email.strip(),
            password=password,
            company=company,
            permissions=[Role.CAN_VIEW_ALL_REQUESTS]
        )
