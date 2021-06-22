from django.core.management import BaseCommand
from django.utils import timezone

from bank_guarantee.models import Request, RequestStatus
from base_request.models import RequestTender
from clients.models import Client, Agent, User, Bank
from settings.configs.banks import BankCode
from settings.configs.contract import ContractTypes
from settings.settings import DEBUG


class Command(BaseCommand):
    help = 'Ининцализация документов агента'

    def handle(self, *args, **options):
        if DEBUG:
            agent = Agent.objects.filter(inn='0000000000').first()
            if not agent:
                agent = Agent.objects.create(inn="0000000000", confirmed=True)
                agent_user = User.objects.create_user(
                    'john', 'lennon@thebeatles.com', 'johnpassword'
                )
                agent_user.client = agent
                agent_user.save()
            now = timezone.now()
            bank = Bank.objects.create(name='taki bank')
            for i in range(50):
                request_tender = RequestTender.objects.create(
                    subject='test',
                    notification_id='242%i' % i,
                )
                client = Client.objects.create(
                    inn="00000000%i" % i if i > 9 else '000000000%i' % i,
                    name='client#%i' % i, agent_user=agent.user_set.all().first(),
                    agent_company=agent
                )
                statuses = RequestStatus.objects.all()
                Request.objects.create(
                    request_number=str(i),
                    request_number_in_bank=str(i),
                    tender=request_tender,
                    contract_type=ContractTypes.CHOICES[i % 2][0],
                    required_amount=float(i),
                    client=client,
                    agent=agent,
                    agent_user=agent.user_set.all().first(),
                    package_class=BankCode.CHOICES[i % 22][0],
                    package_categories='1,2,3',
                    commission=10.0,
                    suggested_price_amount=float(i),
                    suggested_price_percent=float(i),
                    downpay=True,
                    status=statuses[i % len(statuses)],
                    status_changed_date=now,
                    protocol_date=now,
                    interval=i,
                    bank=bank,
                    is_signed=bool(i % 2),
                )
