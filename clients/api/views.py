from django.utils import timezone
from rest_framework import views
from rest_framework.response import Response

from clients.api.schemas import common_info
from clients.models import Agent, Company, Client, Bank, ContractOffer
from users.models import Role, User
from utils.requests import get_request


class SetContractStateView(views.APIView):

    def post(self, request, *args, **kwargs):
        data = dict(self.request.data)
        replaced_docs = None
        if data.get('replaced_docs'):
            replaced_docs = data.pop('replaced_docs')
        data = {
            key: {'true': True, 'false': False}.get(
                self.request.data.get(key),
                self.request.data.get(key)
            ) for key in data.keys() if self.request.data.get(key)
        }
        contract = ContractOffer.objects.create(**data)
        if replaced_docs:
            ContractOffer.objects.filter(id__in=replaced_docs).update(replaced=contract)
        return Response(self.list())

    def put(self, request, *args, pk=None, **kwargs):
        client = self.request.user.client.get_actual_instance
        error_response = Response({
            'errors': 'Доступ запрещен'
        })
        if isinstance(client, Agent):
            contract_offer = ContractOffer.objects.get(id=pk)
            agent_contract_offer = client.agentcontractoffer_set.filter(
                contract=contract_offer
            ).first()
            if self.request.user.has_role(Role.GENERAL_AGENT):
                if agent_contract_offer.accept_contract is None:
                    decision = self.request.data.get('decision')
                    if isinstance(decision, bool):
                        agent_contract_offer.accept_contract = decision
                        agent_contract_offer.accept_date = timezone.now()
                        agent_contract_offer.save()
                    else:
                        return error_response
                else:
                    return error_response
            else:
                return error_response
        return error_response

    @staticmethod
    def list():
        return {
            'documents': [
                {
                    'name': contract.name,
                    'start_date': contract.start_date.strftime('%d.%m.%Y'),
                    'file_url': contract.file.url,
                    'filename': contract.file.filename,
                    'id': contract.id,
                    'active': contract.is_active,
                    'required': contract.required
                } for contract in ContractOffer.objects.all().order_by('-start_date')
            ]
        }

    def get(self, request, *args, **kwargs):
        if kwargs.get('pk'):
            active_contract = ContractOffer.objects.get(id=kwargs.get('pk'))
            return Response({
                'contract_url': active_contract.file.url,
                'contract_html': active_contract.html,
                'cancel_text': active_contract.cancel_text,
                'accept_text': active_contract.accept_text,
            })
        return Response(self.list())


class CompanyContactsView(views.APIView):
    model = Company

    def get_company_data(self, inquirer, company, user: User = None) -> dict:
        return common_info(inquirer=inquirer, company=company, user=user)

    def has_access(self, company) -> bool:
        if self.request.user.has_role(Role.VERIFIER):
            return True
        if self.request.user.has_role(Role.SUPER_AGENT):
            return True
        if self.request.user.has_role(
            Role.MANAGER) or self.request.user.has_role(Role.HEAD_AGENT):
            return True
        if self.request.user.has_role(
            Role.GENERAL_AGENT) or self.request.user.has_role(Role.AGENT):
            if isinstance(company, Agent):
                return company.id == self.request.user.client_id
            if isinstance(company, Client):
                return company.agent_company_id == self.request.user.client_id
            if isinstance(company, Bank):
                return True
        if self.request.user.has_role(Role.BANK) or self.request.user.has_role(
            Role.GENERAL_BANK):
            if isinstance(company, Bank):
                return company.id == self.request.user.client_id
            if isinstance(company, Client):
                return True
            if isinstance(company, Agent):
                return True
        if self.request.user.has_role(Role.CLIENT):
            if isinstance(company, Client):
                return company.id == self.request.user.client_id
            return True
        return False

    def get_company_and_user(self, company_id, request_id, request_type, role):
        request = get_request(request_id=request_id,
                              request_type=request_type)
        if request:
            if role == 'client':
                return request.client, request.client.user_set.first()
            if role == 'agent':
                return request.agent, request.agent_user
            if role == 'bank' and request.bank_id:
                return request.bank, request.bank.user_set.first()
        company = Company.objects.filter(id=company_id).first()
        return company, company.user_set.first()

    def get(self, *args, **kwargs):
        request_id = self.request.query_params.get('request_id')
        request_type = self.request.query_params.get('request_type')
        role = self.request.query_params.get('role')

        allowed_request_types = ['request', 'loan', 'BG', 'LOAN']
        if request_type and request_type not in allowed_request_types:
            return Response({
                'errors': 'Недопустимый тип заявки'
            })
        company_id = self.request.query_params.get('id')
        company, user = self.get_company_and_user(
            company_id=company_id,
            request_id=request_id,
            role=role,
            request_type=request_type
        )
        company = company.get_actual_instance
        if company and self.has_access(company):
            return Response(
                self.get_company_data(
                    self.request.user.client.get_actual_instance, company, user
                )
            )
        return Response({
            'errors': 'Доступ запрещен'
        })


class ClientStatisticView(views.APIView):

    def get(self, *args, **kwargs):
        if isinstance(self.request.user.client.get_actual_instance, Bank):
            request_id = self.request.query_params.get('request_id')
            request_type = self.request.query_params.get('request_type')
            allowed_request_types = ['request', 'loan', 'BG', 'LOAN']
            if request_type and request_type not in allowed_request_types:
                return Response({
                    'errors': 'Недопустимый тип заявки'
                })

            client = None
            if request_id:
                request = get_request(request_id=request_id,
                                      request_type=request_type)
                if request:
                    client = request.client
            else:
                client_id = self.request.query_params.get('client')
                client = Client.objects.filter(id=client_id).first()
            if client:
                bank = self.request.user.client.get_actual_instance
                return Response(
                    bank.bank_integration.get_client_statistic(client)
                )

        return Response({
            'errors': 'Доступ запрещен'
        })
