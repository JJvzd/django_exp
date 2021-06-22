import base64
import datetime
import logging
import os

import dateutil
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator, PageNotAnInteger
from django.db import transaction
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action as drf_action
from rest_framework.response import Response

from bank_guarantee.models import Request
from cabinet.base_logic.printing_forms.adapters.doc import DocBasePrintFormGenerator
from cabinet.models import EgrulData, WorkRule
from cabinet.serializers import ProfileSerializer, FileSerializer
from clients.helpers import ChangeAgentValidator
from clients.models import Bank, AgentDocument, BankStopInn
from clients.models import (
    Client, Company, Agent, HowClients, AgentProfile, AgentManager,
    RequestRejectionReasonTemplate, AgentInstructionsDocuments, AgentRewards
)
from clients.models.common import InternalNews
from clients.serializers import (
    ClientSerializer, AgentProfileSerializer, AgentIndividualEntrepreneurSerializer,
    AgentOrganizationSerializer, AgentPhysicalPersonSerializer, AgentSerializer,
    AgentInfoSerializer, CompanyDataAboutOrganizationSerializer,
    AgentRequisitesSerializer, AgentDocumentSerializer, WorkRuleSerializer,
    InternalNewsSerializer, CompanySerializer, BankSerializer,
    RequestRejectionReasonTemplateSerializer, AgentInstructionsDocumentsSerializer,
    AgentRewardsSerrializer, BankBlackListSerializer
)
from clients.user_stories.client import update_contact_info_profile_by_user
from clients.user_stories.common import (
    get_company_info, CompanyNotFound, create_client_company, create_agent_company
)
from external_api.dadata_api import DaData
from files.models import BaseFile
from tender_loans.models import LoanRequest
from users.models import Role, User
from users.permissions import allowed_roles
from users.serializers import UserFIOSerializer, UserSerializer
from users.user_stories import validate_user_data, create_user_via_email
from utils.serializaters import generate_serializer
from utils.validators import validate_inn

logger = logging.getLogger('django')


class ClientsViewSet(viewsets.ViewSet):
    """
    Создание и просмотр клиентов, приязанных к агенту
    """

    def get_converted_date(self, date):
        date = date.split('.')
        date = datetime.date(
            year=int(date[2]),
            month=int(date[1]),
            day=int(date[0])
        )
        return date

    def filter_queryset(self, request_get, queryset):
        if 'client' in request_get:
            if request_get['client'] != 'null':
                try:
                    inn = int(request_get['client'])
                except ValueError:
                    queryset = queryset.filter(name__istartswith=request_get['client'])
                except Exception as e:
                    logger.exception(e)
                else:
                    queryset = queryset.filter(inn=inn)
        if 'legal_address_city' in request_get:
            if request_get['legal_address_city'] != 'null':
                query = request_get['legal_address_city']
                queryset = queryset.filter(
                    agent_company__legal_address_city__istartswith=query
                )
        if 'last_login_from' in request_get:
            if request_get['last_login_from'] != 'null':
                date_from = request_get['last_login_from']
                date_from = self.get_converted_date(date_from)
                queryset = queryset.filter(agent_user__last_login__gte=date_from)
        if 'last_login_to' in request_get:
            if request_get['last_login_to'] != 'null':
                date_to = request_get['last_login_to']
                date_to = self.get_converted_date(date_to)
                queryset = queryset.filter(agent_user__last_login__lte=date_to)
        return queryset

    def get_queryset(self):
        user = self.request.user
        queryset = Client.objects.filter(agent_company_id=user.client.id)
        queryset = self.filter_queryset(self.request.GET, queryset)
        return queryset

    def list(self, request):
        user = request.user
        if user.has_role(Role.SUPER_AGENT):
            clients = Client.objects.all()
        else:
            clients = Client.objects.filter(agent_company_id=user.client.id)
        regions = clients.values_list('region', flat=True).distinct()
        if request.GET.get('inn_or_name'):
            name = request.GET.get('inn_or_name')
            if not name.isnumeric():
                name = name.upper()
            clients = clients.filter(
                Q(profile__full_name__icontains=name) |
                Q(profile__short_name__icontains=name) |
                Q(inn__icontains=name)
            )
        if request.GET.get('region'):
            clients = clients.filter(region=request.GET.get('region'))
        if request.GET.get('date_to'):
            date_to = request.GET.get('date_to')
            date_to = dateutil.parser.parse(date_to)
            clients = clients.filter(date_last_action__gte=date_to)
        if request.GET.get('date_from'):
            date_from = request.GET.get('date_from')
            date_from = dateutil.parser.parse(date_from)
            clients = clients.filter(date_last_action__lte=date_from)

        page_limit = 10
        page = self.request.GET.get('page', 1)
        if request.GET.get('page_limit'):
            page_limit = request.GET.get('page_limit')
            if request.GET.get('page_limit_init'):
                page = 1
        paginator = Paginator(clients, page_limit)
        paginated_clients = []
        if clients:
            try:
                paginated_clients = paginator.page(page)
            except PageNotAnInteger:
                paginated_clients = paginator.page(1)

        return Response({
            'clients': ClientSerializer(paginated_clients, many=True).data,
            'page_count': paginator.num_pages if clients else 0,
            'regions': regions,
        })

    def generate_reattach_document(self, request, actual_company):
        data = dict()
        file = self.get_print_form_fixing(request.user.client.get_actual_instance,
                                          actual_company)
        data['error_code'] = 'ANOTHER_AGENT'
        data['error'] = 'Клиент закреплен за другим агентом. Для перезакрепления ' \
                        'отправьте <a href="data:application/msword;base64,%s" ' \
                        'download="форма перезакрепления.docx">письмо</a> на почту <a ' \
                        'href="mailto:dev2@tenderhelp.ru">dev2@tenderhelp.ru</a> или ' \
                        'обращайтесь по номеру +7 (800) 700-65-56 ' \
                        'для уточнения о перезакрепление. ' % file
        return data

    @drf_action(detail=False)
    def search_by_inn(self, request):
        inn = request.query_params.get('search').strip()
        try:
            if inn and validate_inn(inn) is None:
                company = Client.objects.filter(inn=inn).first()
                if company:
                    company.fill()
                    data = {
                        'result': {
                            'full_name': company.full_name,
                            'short_name': company.short_name,
                            'legal_address': company.profile.legal_address,
                            'inn': company.inn,
                            'ogrn': company.ogrn,
                            'kpp': company.kpp,
                            'id': company.id
                        }
                    }

                    actual_company = company.get_actual_instance
                    if actual_company.agent_company \
                            and actual_company.agent_company_id != request.user.client_id:

                        if ChangeAgentValidator(actual_company).is_not_free():
                            data.update(self.generate_reattach_document(
                                request=request,
                                actual_company=actual_company,
                            ))
                        else:
                            logger.info(
                                "Auto change agent for client %s" % actual_company
                            )
                            actual_company.change_agent(
                                request.user.client.get_actual_instance,
                                request.user
                            )
                    return Response(data)

                else:
                    api = DaData()

                    data = api.get_company(inn).get('suggestions')[0]
                    data = data.get('data', {})
                    legal_address = data.get('address', {}).get('value', '')
                    short_name = data.get('name', {}).get('short_with_opf', '')
                    full_name = data.get('name', {}).get('full_with_opf', '')
                    inn = data.get('inn', '')
                    kpp = data.get('kpp', '')
                    ogrn = data.get('ogrn', '')
                    return Response({
                        'error_code': "CLIENT_DONT_EXISTS",
                        'error': 'Клиента можно создать',
                        'result': {
                            'full_name': full_name,
                            'short_name': short_name,
                            'legal_address': legal_address,
                            'inn': inn,
                            'ogrn': ogrn,
                            'kpp': kpp,
                        }
                    })
        except ValidationError:
            pass
        return Response({
            'error_code': 'INCORRECT_QUERY',
            'error': 'Некорректный параметр поиска'
        })

    @staticmethod
    def get_print_form_fixing(agent, client) -> str:
        data = {
            'client': client,
            'agent': agent
        }
        adapter = DocBasePrintFormGenerator()
        adapter.set_template(r'system_files/print_forms_templates/re_fixing.docx')
        adapter.set_data(data)
        for path in adapter.generate():
            with open(path, 'rb') as file:
                file = '%s' % base64.b64encode(file.read()).decode()
                os.unlink(path)
                return file

    @drf_action(detail=False)
    def get_from_egrul(self, request, *args, **kwargs):
        inn = request.query_params.get('inn')
        if inn:
            data = EgrulData.get_info(inn)
            return Response(data)
        return Response({
            'errors': 'Не указан параметр inn'
        })

    @drf_action(detail=True)
    def update_from_egrul(self, request, pk, *args, **kwargs):
        client = Client.objects.filter(id=pk).first()
        with transaction.atomic():
            client.fill_questionnaire()
            return Response({
                'profile': ProfileSerializer(client.profile).data
            })
        return Response({
            'errors': 'Ошибка при обновлении анкеты'
        }, status=400)

    @drf_action(detail=False)
    def check_inn(self, request, *args, **kwargs):
        inn = self.request.query_params.get('inn')
        try:
            if inn:
                validate_inn(inn)
                if not Client.objects.filter(inn=inn).first():
                    try:
                        result = get_company_info(inn)
                        return Response({
                            'result': result
                        })
                    except CompanyNotFound:
                        return Response({
                            'error': 'Не найдена компания с ИНН %s' % inn
                        })

                else:
                    return Response({
                        'error': 'Пользователь уже сущетсвует в системе'
                    })
        except ValidationError:
            return Response({
                'error': 'Введен неккоректный ИНН'
            })

    @drf_action(methods=['post'], detail=False,
                permission_classes=[allowed_roles([Role.AGENT, Role.MANAGER])])
    def registration_client(self, request):
        user = request.data.pop('new_user')
        inn = user.get('inn')
        # address = user['address']
        first_name = user['first_name']
        last_name = user['last_name']
        middle_name = user['middle_name']
        email = user['email']
        position = user['position']
        phone = user['phone']
        errors = validate_user_data(
            inn=inn,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            phone=phone,
            email=email,
            position=position
        )
        if errors:
            return Response({
                'errors': errors
            })
        client = create_client_company(inn=inn, agent_user=request.user)
        user = create_user_via_email(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            position=position,
            phone=phone,
            email=email,
            company=client,
            permissions=[]
        )
        update_contact_info_profile_by_user(company=client, user=user)
        return Response({
            'registration': True
        })

    @drf_action(methods=['post'], detail=False,
                permission_classes=[allowed_roles([Role.SUPER_AGENT])])
    def registration_agent(self, request):
        user = request.data.pop('new_user')
        inn = user.get('inn')
        first_name = user['first_name']
        last_name = user['last_name']
        middle_name = user['middle_name']
        email = user['email']
        position = user['position']
        phone = user['phone']
        errors = validate_user_data(
            inn=inn,
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            phone=phone,
            email=email,
            position=position,
        )

        if errors:
            return Response({
                'errors': errors
            })

        agent = create_agent_company(inn=inn)
        create_user_via_email(
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            position=position,
            phone=phone,
            email=email,
            company=agent,
            permissions=[Role.GENERAL_AGENT]
        )
        return Response({
            'registration': True
        })

    @drf_action(detail=True, methods=['GET'])
    def get_agent_user(self, request, pk=None):
        client = Client.objects.filter(id=pk).first()
        if client:
            return Response({
                'agent_user': client.agent_user and client.agent_user.id
            })
        return Response({
            'error': 'Клиент не найден'
        })

    @drf_action(detail=True, methods=["GET"])
    def get_client_users(self, request, pk=None):
        client = Client.objects.filter(id=pk).first()
        if client:
            return Response({
                'users': UserFIOSerializer(client.user_set.all(), many=True).data
            })
        return Response({
            'error': 'Клиент не найден'
        })

    @drf_action(detail=True, methods=['GET'])
    def get_manager(self, request, pk=None):
        client = Client.objects.filter(id=pk).first()
        if client:
            return Response({
                'manager': client.manager and client.manager.id
            })
        return Response({
            'error': 'Клиент не найден'
        })

    @drf_action(detail=True, methods=['POST'])
    def change_agent_user(self, request, pk=None):
        client = Client.objects.filter(id=pk).first()
        if client:
            user_id = self.request.data.get('agent_user')
            if user_id:
                agent_user = User.objects.filter(id=user_id).first()
                if agent_user:
                    agents = client.agent_company.user_set.filter(roles__name=Role.AGENT)
                    if agent_user in agents:
                        client.agent_user = agent_user
                        client.save()
                        return Response({
                            'success': 'Агент изменён'
                        })
                    return Response({
                        'error': 'Агент не может быть изменён'
                    })
                return Response({
                    'error': 'Aгент не найден'
                })
            return Response({
                'error': 'Параметр не передан'
            })
        return Response({
            'error': 'Клиент не найден'
        })

    @drf_action(detail=True, methods=['POST'])
    def change_manager(self, request, pk=None):
        client = Client.objects.filter(id=pk).first()
        if client:
            user_id = self.request.data.get('agent_user')
            if user_id:
                agent_user = User.objects.filter(id=user_id).first()
                if agent_user:
                    managers = client.agent_company.user_set.filter(
                        roles__name=Role.MANAGER
                    )
                    if agent_user in managers:
                        client.manager = agent_user
                        client.save()
                        return Response({
                            'success': 'Агент изменён'
                        })
                    return Response({
                        'error': 'Агент не может быть изменён'
                    })
                return Response({
                    'error': 'Aгент не найден'
                })
            return Response({
                'error': 'Параметр не передан'
            })
        return Response({
            'error': 'Клиент не найден'
        })


class AgentsViewSet(viewsets.ViewSet):
    """
    Создание и просмотр агентов в системе
    """

    def list(self, request):
        if self.request.user.has_role(Role.SUPER_AGENT) or self.request.user.is_superuser:
            agents = Agent.objects.all()
        else:
            agents = Agent.objects.none()

        page_limit = request.GET.get('page_limit', 50)
        page = self.request.GET.get('page', 1)

        paginator = Paginator(agents, page_limit)
        paginated_clients = []
        if agents:
            try:
                paginated_clients = paginator.page(page)
            except PageNotAnInteger:
                paginated_clients = paginator.page(1)

        def get_manager(obj):
            manager = AgentManager.get_manager_by_agent(obj)
            if manager:
                return {"id": manager.id, 'first_name': manager.first_name}
            return None

        def get_managers(obj):
            from users.models import User, Role
            manager_list = []
            for man in User.objects.filter(roles__name=Role.MANAGER):
                manager_list.append({
                    "value": man.id,
                    "label": man.first_name + ' ' + man.last_name
                })
            return manager_list

        fields = [
            'id', 'short_name', 'inn', 'kpp', 'ogrn', 'created',
            'document_number', 'first_name', 'last_name', 'middle_name', 'phone', 'email',
            'confirmed_documents', {'field': 'manager_list', 'value': get_managers},
            {'field': 'manager', 'value': get_manager}
        ]
        serializer = generate_serializer(Agent, fields)
        return Response({
            'agents': serializer(paginated_clients, many=True).data,
            'page_count': paginator.num_pages if agents else 0,
        })

    @drf_action(detail=False, methods=['POST'])
    def change_document_status(self, *args, **kwargs):
        new_value = self.request.data
        current_user = User.objects.filter(id=new_value["user_id"]).first()
        agent_id = current_user.client.id

        agent_model = Agent.objects.get(id=agent_id)
        agent_model.confirmed_documents = new_value["confirmed_documents"]
        agent_model.save()

        return Response({
            'agents_new_value': new_value
        })

    @drf_action(detail=False, methods=['POST'])
    def change_agents(self, *args, **kwargs):
        new_value = self.request.data
        agent_manager_model = AgentManager.objects.all()
        agent_model = Agent.objects.all()
        agent_documents = AgentDocument.objects.all()

        for agent in new_value["agents"]:
            if agent["manager"] is not None:
                agent_manager_selected = agent_manager_model.filter(agent=agent["id"])
                if len(agent_manager_selected) > 0:
                    agent_manager_selected.update(manager=agent["manager"]["id"])
                else:
                    current_manager = User.objects.filter(
                        id=agent["manager"]["id"]
                    ).first()

                    current_agent = agent_model.filter(id=agent["id"]).first()
                    agent_manager_selected = AgentManager.objects.create(
                        manager=current_manager,
                        agent=current_agent
                    )
                    agent_manager_selected.save()

            if agent["confirmed_documents"] == 1:
                agent_doc = agent_documents.filter(agent=agent["id"])
                for a_d in agent_doc:
                    a_d.document_status = 1
                    a_d.comment = None
                    a_d.save()
            elif agent["confirmed_documents"] == 3:
                agent_doc = agent_documents.filter(agent=agent["id"])
                for a_d in agent_doc:
                    a_d.document_status = 3
                    a_d.save()

            agent_model_selected = agent_model.get(id=agent["id"])
            agent_model_selected.confirmed_documents = agent["confirmed_documents"]
            agent_model_selected.document_number = agent["document_number"]
            agent_model_selected.save()

        return Response({
            'agents_new_value': new_value
        })

    @drf_action(detail=False, methods=['GET'])
    def with_managers(self, *args, **kwargs):
        if self.request.user.has_role(Role.SUPER_AGENT):
            agents = Agent.objects.all()

            def get_manager(obj):
                manager = AgentManager.get_manager_by_agent(obj)
                if manager:
                    return manager.id
                return None

            fields = [
                'id', 'short_name', 'inn', 'kpp', 'ogrn',
                {'field': 'manager', 'value': get_manager}
            ]
            serializer = generate_serializer(Agent, fields)
            return Response({
                'agents': serializer(agents, many=True).data,
                'managers': UserSerializer(AgentManager.get_managers(), many=True).data
            })
        return Response({
            'error': 'Нет прав доступа'
        })

    @drf_action(detail=True, methods=['POST'])
    def change_manager(self, *args, **kwargs):
        if self.request.user.has_role(Role.SUPER_AGENT):
            agent = Agent.objects.filter(id=self.kwargs['pk']).first()
            manager_id = self.request.query_params.get('manager_id')
            reason = self.request.query_params.get('reason')
            date_from = self.request.query_params.get('date_from')
            date_to = self.request.query_params.get('date_to')
            manager = User.objects.filter(id=manager_id).first()
            if agent and manager and manager.has_role(Role.MANAGER):
                result = AgentManager.set_manager_to_agent(agent=agent, manager=manager,
                                                           reason=reason,
                                                           date_from=date_from,
                                                           date_to=date_to)
                if result:
                    return Response({
                        'result': True,
                    })
        return Response({
            'error': 'Нет прав доступа'
        })

    @drf_action(detail=False, methods=['GET'])
    def get_agent_users(self, *args, **kwargs):
        users = None
        if self.request.user.has_role(Role.SUPER_AGENT):
            users = User.objects.filter(roles__name=Role.AGENT)
        elif self.request.user.has_role(Role.MANAGER):
            users = self.request.user.client.user_set.filter(roles__name=Role.AGENT)
        fields = [
            'id',
            'first_name',
            'last_name',
            'middle_name',
            'email',
            'client_id',
        ]
        user_serializer = generate_serializer(User, fields)
        if users is not None:
            return Response({
                'agent_users': user_serializer(users.only(*fields), many=True).data
            })
        return Response({
            'error': 'Нет прав доступа'
        })

    @drf_action(detail=False, methods=['GET'])
    def get_managers(self, pk=None):
        if self.request.user.has_role(Role.SUPER_AGENT):
            managers_data = UserSerializer(
                User.objects.filter(roles__in=Role.objects.filter(name=Role.MANAGER)),
                many=True
            ).data
        elif self.request.user.has_role(Role.GENERAL_AGENT):
            managers_data = UserSerializer(
                self.request.user.client.get_actual_instance.user_set.filter(
                    roles__name=Role.MANAGER
                ),
                many=True
            ).data
        else:
            return Response({
                'error': 'Нет прав доступа'
            })
        return Response({
            'agents_managers': managers_data
        })

    @drf_action(detail=False, methods=['GET', 'POST'])
    def get_agent_rewards(self, *args, **kwargs):
        date = self.request.data.get('date')

        requests = AgentRewards.objects.all()
        requests = requests.filter(date__icontains=date)
        requests_data = AgentRewardsSerrializer(requests, many=True).data

        for elem in requests_data:
            elem["agent"] = Agent.objects.get(id=elem["agent_id"]).short_name
            elem["bank"] = Bank.objects.get(id=elem["bank_id"]).short_name

        return Response({
            'data': requests_data
        })


class AgentSettingsViewSet(viewsets.ViewSet):

    @drf_action(detail=False, methods=['GET', 'POST'])
    def registration_info(self, request, *args, **kwargs):
        user = request.user
        if request.method == 'POST':
            if HowClients.objects.all().first() is None:
                for key in HowClients.CHOICES:
                    HowClients.objects.create()

            company_id = request.data.get('company_id')
            if request.user.has_role(Role.GENERAL_AGENT) and company_id:
                agent = Agent.objects.filter(id=request.data.pop('company_id')).first()
            else:
                agent = Agent.objects.filter(id=user.client.id).first()
            errors = {}
            if agent:
                agent_profile_data = request.data.pop('agent_profile')
                agent_profile_data = {k: v for k, v in agent_profile_data.items() if v}
                if agent_profile_data:
                    agent_profile = AgentProfile.objects.filter(agent=agent).first()
                    if agent_profile:
                        agent_profile_serializer = AgentProfileSerializer(
                            agent_profile, data=agent_profile_data, partial=True
                        )
                    else:
                        agent_profile_data.update({'agent': agent.id})
                        agent_profile_serializer = AgentProfileSerializer(
                            data=agent_profile_data, partial=True
                        )
                    if agent_profile_serializer.is_valid():
                        agent_profile_serializer.save()
                    else:
                        errors = agent_profile_serializer.errors

                data = {k: v for k, v in request.data.items() if v}
                if agent.is_individual_entrepreneur:
                    agent_serializer = AgentIndividualEntrepreneurSerializer(
                        agent, data=data, partial=True
                    )
                elif agent.is_organization:
                    agent_serializer = AgentOrganizationSerializer(
                        agent, data=data, partial=True
                    )
                elif agent.is_physical_person:
                    agent_serializer = AgentPhysicalPersonSerializer(
                        agent, data=data, partial=True
                    )
                else:
                    return Response({
                        'errors': 'Ошибка определения типа агента'
                    })
                if agent_serializer.is_valid():
                    agent_serializer.save()
                else:
                    errors.update(agent_serializer.errors)
                if errors:
                    return Response({
                        'errors': errors
                    })

            return Response({
                'answer': 'поля обновлены'
            })

        if request.user.has_role(Role.GENERAL_AGENT) and request.query_params.get(
                'company_id'):
            agent = Agent.objects.filter(id=request.query_params['company_id']).first()
        else:
            agent = Agent.objects.filter(id=user.client.id).first()

        agent.check_confirmed()

        data = AgentSerializer(agent).data
        agent_profile = AgentProfile.objects.filter(agent=agent).first()
        agent_profile_data = AgentProfileSerializer(agent_profile).data

        data["bank_list"] = list()
        for bank in Bank.objects.filter(active=True):
            data["bank_list"].append({'value': bank.id, 'label': bank.short_name})

        current_company = Company.objects.filter(inn=data['inn']).first()
        is_physical_person = current_company.is_physical_person
        data["is_physical_person"] = is_physical_person

        if user.email is not None and len(user.email) > 0:
            data['email'] = user.email
        if user.phone is not None and len(user.phone) > 0:
            data['phone'] = user.phone

        return Response({
            'info': data,
            'is_individual_entrepreneur': agent.is_individual_entrepreneur,
            'is_physical_person': agent.is_physical_person,
            'is_organization': agent.is_organization,
            'agent_profile': agent_profile_data,
            'state_end_registration': agent.is_send_registration(),
        })

    @drf_action(detail=False, methods=['GET'])
    def info(self, *args, **kwargs):
        return Response({
            'info': AgentInfoSerializer(self.request.user.client.get_actual_instance).data
        })

    @drf_action(detail=False, methods=['GET', 'POST'])
    def data_about_company(self, *args, **kwargs):
        agent = self.request.user.client
        if self.request.method == 'POST':
            data = CompanyDataAboutOrganizationSerializer(agent, self.request.data)
            if data.is_valid():
                data.save()
            else:
                return Response({
                    'errors': data.errors
                })
        return Response({
            'data': CompanyDataAboutOrganizationSerializer(agent).data
        })

    @drf_action(detail=False, methods=['GET', 'POST'])
    def requisites(self, *args, **kwargs):
        if self.request.user.has_role(Role.SUPER_AGENT):
            if self.request.query_params.get('company_id'):
                agent = Agent.objects.filter(
                    id=self.request.query_params.get('company_id')).first()
            elif self.request.data.get('company_id'):
                agent = Agent.objects.filter(
                    id=self.request.data.pop('company_id')).first()
            else:
                agent = self.request.user.client.get_actual_instance
        else:
            agent = self.request.user.client.get_actual_instance
        if self.request.method == 'POST':
            data = AgentRequisitesSerializer(agent, self.request.data)
            if data.is_valid():
                data.save()
            else:
                return Response({
                    'errors': data.errors
                })

        agent.check_requisites()
        return Response({
            'requisites': AgentRequisitesSerializer(agent).data,
            'state_end_registration': agent.is_send_registration(),
        })


class AgentSettingsDocumentsViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentDocumentSerializer

    def get_queryset(self):
        agent = self.get_agent(self.request)
        return agent.agentdocument_set.all()

    def get_agent(self, request):
        if request.user.has_role(Role.SUPER_AGENT) and request.query_params.get(
                'company_id'):
            return Agent.objects.filter(id=request.query_params.get('company_id')).first()
        return self.request.user.client.get_actual_instance

    def list(self, request, *args, **kwargs):
        agent = self.get_agent(request)
        inn = request.query_params.get('inn')
        if inn:
            data = EgrulData.get_info(inn)
            return Response(data)
        documents_data = AgentDocumentSerializer(agent.agentdocument_set.all(),
                                                 many=True).data
        return Response({
            'documents': documents_data
        })

    @drf_action(detail=True, methods=['POST'])
    def add_comment(self, args, pk=None, *kwargs):
        new_value = self.request.data
        agent_documents = AgentDocument.objects.all()
        agent_doc = agent_documents.get(agent=new_value['company_id'], id=new_value["id"])
        agent_doc.comment = new_value["comment"]
        agent_doc.document_status = 3
        try:
            agent_doc.save()
        except Exception:
            pass
        return Response({
            'agent_doc': AgentDocumentSerializer(agent_documents).data
        })

    @drf_action(detail=True, methods=['POST'])
    def confirm_document(self, args, pk=None, *kwargs):
        every_doc_confirmed = False
        every_doc_un_confirmed = False
        new_value = self.request.data
        agent_documents = AgentDocument.objects.filter(agent=new_value['company_id'])
        agent_doc = agent_documents.get(id=new_value["id"])
        agent_doc.document_status = new_value["document_status"]
        if "comment" in new_value.keys():
            agent_doc.comment = new_value["comment"]

        try:
            agent_doc.save()
        except Exception:
            pass

        for a_d in agent_documents:
            if a_d.document_status == 1:
                every_doc_confirmed = True
            else:
                every_doc_confirmed = False
                break
        if every_doc_confirmed:
            agent_model = Agent.objects.get(id=new_value['company_id'])
            agent_model.confirmed_documents = 1
            agent_model.save()

        for a_d in agent_documents:
            if a_d.document_status == 3:
                every_doc_un_confirmed = True
                break
            else:
                every_doc_un_confirmed = False
        if every_doc_un_confirmed:
            agent_model = Agent.objects.get(id=new_value['company_id'])
            agent_model.confirmed_documents = 3
            agent_model.save()

        return Response({
            'agent_doc': AgentDocumentSerializer(agent_documents).data
        })

    @drf_action(detail=True, methods=['POST'])
    def upload(self, *args, **kwargs):
        agent = self.get_agent(self.request)
        document = self.get_object()
        file = self.request.data.get('file')
        if file:
            try:
                if document.file:
                    document.file.delete()
            except BaseFile.DoesNotExist:
                pass

            document.file = BaseFile.objects.create(
                file=file,
                author=agent,
            )
            document.save()
            return Response({
                'file': FileSerializer(document.file).data
            })

    @drf_action(detail=True, methods=['POST'])
    def delete(self, *args, **kwargs):
        document = self.get_object()
        if document.file:
            file = document.file
            file.delete()
            document.file = None
            document.save()
            return Response({
                'file': FileSerializer(document.file).data
            })


class AgentInformationViewSet(viewsets.ViewSet):

    @drf_action(detail=False, methods=['GET'])
    def work_rules(self, request, pk=None):
        client = request.user.client.get_actual_instance
        client.work_rules = 0
        client.save()
        rules = WorkRule.objects.order_by('-updated')
        return Response({
            'work_rules': WorkRuleSerializer(rules, many=True).data,
        })

    @drf_action(detail=False, methods=['GET'])
    def news(self, request, pk=None):
        agent = request.user.client.get_actual_instance
        agent.internal_news = 0
        agent.save()
        news = InternalNews.objects.filter(status=InternalNews.STATUS_PUBLISHED).filter(
            for_agents=True).order_by(
            '-created')
        return Response({
            'news': InternalNewsSerializer(news, many=True).data,
        })


class CompanyViewSet(viewsets.ViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer

    def get_queryset(self):
        return self.queryset

    def list(self, request, *args, **kwargs):
        if request.user.roles.filter(name=Role.SUPER_AGENT).first():
            return Response({
                'company_list': self.serializer_class(self.get_queryset(), many=True).data
            })


class CompanyInfoViewSet(viewsets.GenericViewSet):
    serializer_class = AgentSerializer

    def get_request(self, request_id, request_type):
        try:
            if request_type in ['request', 'BG']:
                return Request.objects.get(id=request_id)
            if request_type in ['loan', 'LOAN']:
                return LoanRequest.objects.get(id=request_id)
        except Exception:
            return None

    @drf_action(detail=False, methods=['GET'])
    def agent_info(self, *args, **kwargs):
        request_id = self.request.query_params.get('request_id')
        request_type = self.request.query_params.get('request_type')
        if request_type not in ['request', 'loan', 'BG', 'LOAN']:
            return Response({
                'errors': 'Недопустимый тип заявки'
            })
        request = self.get_request(request_id=request_id, request_type=request_type)
        if request:
            company = request.agent
            user = request.agent_user
            return Response({
                'company': AgentSerializer(company).data,
                'user': UserSerializer(user).data,
            })
        return Response({
            'errors': 'Заявка не найдена'
        })

    @drf_action(detail=False, methods=['GET'])
    def client_info(self, *args, **kwargs):
        request_id = self.request.query_params.get('request_id')
        request_type = self.request.query_params.get('request_type')
        if request_type not in ['request', 'loan', 'BG', 'LOAN']:
            return Response({
                'errors': 'Недопустимый тип заявки'
            })
        request = self.get_request(request_id=request_id, request_type=request_type)
        if request:
            company = request.client
            user = request.client.user_set.first()
            return Response({
                'company': ClientSerializer(company).data,
                'user': UserSerializer(user).data,
            })
        return Response({
            'errors': 'Заявка не найдена'
        })

    @drf_action(detail=False, methods=['GET'])
    def bank_info(self, *args, **kwargs):
        request_id = self.request.query_params.get('request_id')
        request_type = self.request.query_params.get('request_type')
        if request_type not in ['request', 'loan', 'BG', 'LOAN']:
            return Response({
                'errors': 'Недопустимый тип заявки'
            })
        request = self.get_request(request_id=request_id, request_type=request_type)
        if request:
            company = request.bank
            if company:
                user = request.bank.user_set.first()
                return Response({
                    'company': BankSerializer(company).data,
                    'user': UserSerializer(user).data,
                })
            else:
                return Response({
                    'company': {},
                    'user': {},
                })
        return Response({
            'errors': 'Заявка не найдена'
        })


class BankRejectionReasonTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = RequestRejectionReasonTemplateSerializer

    def get_queryset(self):
        return RequestRejectionReasonTemplate.objects.filter(
            user=self.request.user).order_by('id')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AgentInstructionsDocumentsViewSet(viewsets.ModelViewSet):
    serializer_class = AgentInstructionsDocumentsSerializer

    @drf_action(detail=False, methods=['GET', 'POST'])
    def get_documents_info(self, request, *args, **kwargs):
        roles = list(self.request.user.roles.all().values_list('name', flat=True))

        docs_list = list()
        instructions_documents = AgentInstructionsDocuments.objects.filter(
            show=True,
            active=True,
        )
        for document in instructions_documents:
            document = AgentInstructionsDocumentsSerializer(document).data
            for user_role in roles:
                if user_role in document["roles"]:
                    docs_list.append(document)
                    break

        return Response({
            'documents': docs_list
        })


class BankBlackListViewSet(viewsets.ModelViewSet):
    serializer_class = BankBlackListSerializer

    def get_queryset(self):
        return BankStopInn.objects.filter(
            credit_organization=self.request.user.client.bank).order_by('id')

    def perform_create(self, serializer):
        serializer.save(credit_organization=self.request.user.client.bank)
