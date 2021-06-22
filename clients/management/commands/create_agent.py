import random

from django.core.management import BaseCommand

from clients.user_stories.common import create_agent_company
from users.models import Role
from users.user_stories import create_user_via_email


class Command(BaseCommand):
    help = 'Создание компании-агента с пользователем'

    def handle(self, *args, **options):
        inn = input("ИНН? ")
        email = input("Email? ")
        password = input('Пароль пользователя? ')

        company = create_agent_company(inn=inn)
        company.confirmed = True
        company.save()
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
