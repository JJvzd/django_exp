import datetime
import logging
from collections import Iterable

import dateutil
import ujson
from django.core.paginator import Paginator, PageNotAnInteger
from django.db.models import Value, CharField, DateField, Q, IntegerField
from rest_framework import viewsets
from rest_framework.decorators import action as drf_action
from rest_framework.response import Response

from bank_guarantee.models import (
    Request, RequestDocument, DocumentLinkToPerson, ContractType, ContractPlacementWay,
    Request as BGRequest, RequestStatus, RequestedCategory
)
from bank_guarantee.serializers import (
    BankDocumentTypeSerializer, RequestDocumentSerializer, RequestedCategorySerializer
)
from base_request.models import RequestTender, BankDocumentType, AbstractRequest
from base_request.serializers import (
    RequestTenderSerializer, BaseRequestSerializer, RequestStatusSerializer,
    LoanRequestStatusSerializer
)
from cabinet.constants.constants import DeliveryType, FederalLaw, Target
from cabinet.models import PlacementPlace
from cabinet.serializers import FileSerializer
from clients.models import MFO, Bank, AgentManager, Agent
from clients.serializers import AgentInfoSerializer, BankInfoSerializer
from external_api.data_zakupki_tenderhelp_api import ZakupkiTenderhelpApi
from external_api.parsers_tenderhelp import ParsersApi
from files.models import BaseFile
from permissions.logic.bank_guarantee import GetUserAllowedRequests
from permissions.logic.tender_loans import GetUserAllowedLoanRequests
from settings.configs.money import MoneyTypes
from tender_loans.models import (
    LoanRequest, LoanRequestDocument, LoanDocumentLinkToPerson, LoanStatus
)
from tender_loans.serializers import LoanDocumentSerializer


from utils import helpers

logger = logging.getLogger('django')


class RequestTenderViewSet(viewsets.ViewSet):

    def retrieve(self, request, pk=None):
        data = RequestTender.objects.get(id=pk)
        return Response({
            'request_tender': RequestTenderSerializer(data).data
        })


class TendersViewSet(viewsets.ViewSet):

    @drf_action(detail=False, methods=['GET'])
    def search_notification(self, request, pk=None):
        api = ParsersApi()
        api2 = ZakupkiTenderhelpApi()
        notification_id = self.request.GET.get('notification_id', '')
        full_data = data = api.zakupki.get_tender(notification_id)
        try:
            data2 = api2.get_tender_data(notification_id)
        except Exception as e:
            logger.info(f'{e}')
        else:
            if data:
                if 'error' not in data2:
                    full_data = helpers.map_parsers_data(data, data2)
            else:
                full_data = data2
        return Response({
            'data': full_data,
        })


class LoanDocumentsViewSet(viewsets.ViewSet):

    @drf_action(detail=True, methods=['POST'])
    def upload(self, *args, **kwargs):
        request = LoanRequest.objects.filter(
            id=self.kwargs['tender_loans_pk']).first()
        category = BankDocumentType.objects.filter(id=self.kwargs['pk']).first()
        file = self.request.data.get('file')
        if file:
            file = BaseFile.objects.create(
                file=file,
                author=self.request.user.client,
            )
            LoanRequestDocument.objects.create(
                request=request,
                category=category,
                file=file
            )
            request.is_signed = False
            request.save()
            # добавления в архив документов клиента
            # ClientDocument.objects.create(
            #     client=request.client,
            #     file=file,
            #     category=category
            # )
            return Response({
                'file': FileSerializer(file).data
            })
        return Response({
            'error': 'Файл не передан'
        })

    @drf_action(detail=True, methods=['POST'])
    def delete(self, *args, **kwargs):
        request = LoanRequest.objects.filter(
            id=self.kwargs['tender_loans_pk']).first()
        document = request.requestdocument_set.filter(
            id=self.kwargs['pk']).first()
        if document:
            document.delete()
            request.is_signed = False
            request.save()
            return Response({
                'result': True
            })
        return Response({
            'result': False
        })

    def list(self, request, *args, **kwargs):
        request = LoanRequest.objects.filter(
            id=self.kwargs['tender_loans_pk']).first()
        documents = request.requestdocument_set.filter(
            category_id__isnull=False
        )
        package_name = MFO.objects.filter(code=request.package_class).first()
        package_name = package_name.short_name if package_name else ''
        return Response({
            'package': {
                'name': package_name,
                'class': request.package_class,
            },
            'is_rent_over': '',
            'documents': LoanDocumentSerializer(documents, many=True).data,
            'categories': BankDocumentTypeSerializer(request.get_categories(),
                                                     many=True).data,
            'requested_docs': '',
        })

    @drf_action(detail=False, methods=["GET"])
    def get_person_choices_for_passport(self, *args, **kwargs):
        request = LoanRequest.objects.filter(
            id=kwargs['tender_loan_pk']).first()
        possible_persons = request.client.profile.beneficiars_over_25
        person_choices = [{'label': i.get_name, 'value': i.id} for i in
                          possible_persons]
        if person_choices:
            person_choices += [{'label': 'Выберите пользователя', 'value': None}]
        return Response({
            'person_choices': person_choices
        })

    @drf_action(detail=True, methods=['POST'])
    def document_link_to_person(self, pk=None, *args, **kwargs):
        required_fields = (
            'category_id',
            'person_id',
            'document_id',
        )
        for field in required_fields:
            if not self.request.data.get(field):
                return Response({
                    'error': 'Переданы не все аргументы'
                })
        LoanDocumentLinkToPerson.set_link(pk,
                                          *[self.request.data.get(i) for i in
                                            required_fields]
                                          )
        return Response({
            'success': 'Документ привязан'
        })


class RequestDocumentsViewSet(viewsets.ViewSet):

    @drf_action(detail=True, methods=['POST'])
    def upload(self, *args, **kwargs):
        request = Request.objects.filter(
            id=self.kwargs['bank_guarantee_pk']).first()
        category = BankDocumentType.objects.filter(id=self.kwargs['pk']).first()
        file = self.request.FILES.get('file')
        if file:
            file = BaseFile.objects.create(
                file=file,
                author=self.request.user.client,
            )
            doc = RequestDocument.objects.create(
                request=request,
                category=category,
                file=file
            )
            request.is_signed = False
            request.save()
            # добавление привязки к участникам
            if (self.request.query_params.get('person_id') and
                    self.request.query_params.get('person_id') != 'undefined'):
                DocumentLinkToPerson.objects.update_or_create(
                    request=request,
                    document_category=category,
                    person_id=self.request.query_params.get('person_id'),
                    document=doc
                )

            # добавления в архив документов клиента
            # ClientDocument.objects.create(
            #     client=request.client,
            #     file=file,
            #     category=category
            # )
            return Response({
                'file': FileSerializer(file).data
            })
        return Response({
            'error': 'Файл не передан'
        })

    @drf_action(detail=True, methods=['POST'])
    def delete(self, *args, **kwargs):
        request = Request.objects.filter(
            id=self.kwargs['bank_guarantee_pk']).first()
        document = request.requestdocument_set.filter(
            id=self.kwargs['pk']).first()
        if document:
            # file = document.file
            document.delete()
            request.is_signed = False
            request.save()
            # # удаление из архива документов клиента
            # ClientDocument.objects.filter(file=file).delete()
            # # удаления из черновиков
            # RequestDocument.objects.filter(
            #     request__status__code=RequestStatus.CODE_DRAFT,
            #     file=file,
            # ).delete()
            # LoanRequestDocument.objects.filter(
            #     request__status__code=LoanStatus.CODE_DRAFT,
            #     file=file,
            # ).delete()
            return Response({
                'result': True
            })
        return Response({
            'result': False
        })

    def list(self, request, *args, **kwargs):
        request = Request.objects.filter(
            id=self.kwargs['bank_guarantee_pk']).first()
        documents = request.requestdocument_set.filter(
            Q(category_id__isnull=False) | Q(requested_category__isnull=False)
        )
        package_name = Bank.objects.filter(code=request.package_class).first()
        package_name = package_name.short_name if package_name else ''
        return Response({
            'package': {
                'name': package_name,
                'class': request.package_class,
            },
            'is_rent_over': '',
            'documents': RequestDocumentSerializer(documents, many=True).data,
            'categories': BankDocumentTypeSerializer(request.get_categories(),
                                                     many=True).data,
            'requested_docs': '',
            'requested_categories': RequestedCategorySerializer(
                RequestedCategory.objects.filter(request=request),
                many=True).data
        })

    @drf_action(detail=False, methods=["POST"])
    def add_requested_category(self, request, *args, **kwargs):
        request = Request.objects.filter(
            id=self.kwargs['bank_guarantee_pk']).first()
        RequestedCategory.objects.create(
            name=self.request.data.get('name'),
            request=request,
        )
        return Response({
            'success': 'Запрос сделан'
        })

    @drf_action(detail=True, methods=["POST"])
    def upload_requested_document(self, request, *args, **kwargs):
        request = Request.objects.filter(
            id=self.kwargs['bank_guarantee_pk']).first()
        category = RequestedCategory.objects.filter(
            id=self.kwargs['pk']).first()
        file = self.request.FILES.get('file')
        if file:
            file = BaseFile.objects.create(
                file=file,
                author=self.request.user.client,
            )
            RequestDocument.objects.create(
                request=request,
                requested_category=category,
                file=file
            )
            request.is_signed = False
            request.save()
            return Response({
                'file': FileSerializer(file).data
            })
        return Response({
            'error': 'Файл не передан'
        })

    @drf_action(detail=False, methods=["GET"])
    def get_person_choices_for_passport(self, *args, **kwargs):
        request = Request.objects.filter(id=kwargs['bank_guarantee_pk']).first()
        possible_persons = request.client.profile.persons.filter(
            share__gte=25, is_general_director=False
        )
        person_choices = [{
            'label': i.get_name,
            'value': i.id
        } for i in possible_persons]

        if person_choices:
            person_choices += [{'label': 'Выберите пользователя', 'value': None}]
        return Response({
            'person_choices': person_choices
        })

    @drf_action(detail=True, methods=['POST'])
    def document_link_to_person(self, pk=None, *args, **kwargs):
        required_fields = (
            'category_id',
            'person_id',
            'document_id',
        )
        for field in required_fields:
            if not self.request.data.get(field):
                return Response({
                    'error': 'Переданы не все аргументы'
                })
        DocumentLinkToPerson.set_link(pk,
                                      *[self.request.data.get(i) for i in
                                        required_fields]
                                      )
        return Response({
            'success': 'Документ привязан'
        })


class RequestsViewSet(viewsets.ViewSet):

    @drf_action(detail=False, methods=['GET'])
    def get_choices_delivery_methods(self, *args, **kwargs):
        return Response({
            'choices_delivery_methods': DeliveryType.DELIVERY_CHOICES
        })

    @staticmethod
    def convert_choices(choices):
        return [{'label': choice[1], 'value': choice[0]} for choice in choices]

    @drf_action(detail=False, methods=['GET'])
    def additional_data(self, pk=None):
        return Response({
            "law_choices": self.convert_choices(FederalLaw.CHOICES),
            'contract_type_choices': self.convert_choices(ContractType.CHOICES),
            'contract_type_loan_request_choices': self.convert_choices(
                LoanRequest.CONTRACT_TYPE_CHOICES),
            "contract_placement_way_choices": self.convert_choices(
                ContractPlacementWay.CHOICES),
            "money_choices": self.convert_choices(MoneyTypes.CHOICES),
            "targets": self.convert_choices(Target.CHOICES),
            "placement_place_choices": PlacementPlace.objects.all().values_list(
                'name', flat=True)
        })

    @drf_action(detail=False, methods=['GET'])
    def search_placement_places(self, *args, **kwargs):
        return Response({
            'search_placement_places': PlacementPlace.objects.filter(
                name__icontains=self.request.query_params.get('search')
            ).values_list('name', flat=True)
        })

    def selected_request_fields(self):
        return (
            'id',
            'request_number',
            'created_date',
            'request_number_in_bank',
            'status_changed_date',
            'status',
            'tender__notification_id',
            'tender__id',
            'required_amount',
            'commission',
            'bank__short_name',
            'is_signed',
            'in_archive',
            'client',
            'client__short_name',
            'client__ogrn',
            'client__inn',
            'client__kpp',
            'client__full_name',
            'client__agent_company__phone',
            'client__agent_company__email',
            'client__id',
            'agent__id',
            'agent__inn',
            'agent__short_name',
            'agent_user',
            'agent_user__first_name',
            'agent_user__last_name',
            'agent_user__middle_name',
            'agent_user__username',
            'bank__id',
            'placement_way',
            'bank_reject_reason',
            'targets',
            # следующие три поля всегда должны стоять в конце, иначе для разных моделей
            # смещаются поля после добавления отсутствующих полей
            'assigned',
            'protocol_date',
            'interval',
            'request_type',
        )

    def get_queryset(self):
        archive = self.request.GET.get('archive', 'false') == 'true'
        requests = BGRequest.objects.select_related().annotate(
            request_type=Value(AbstractRequest.TYPE_BG, CharField())
        ).select_related().filter(in_archive=archive)
        loan_requests = LoanRequest.objects.select_related().annotate(
            placement_way=Value(None, CharField()),
            bank_reject_reason=Value(None, CharField()),
            targets=Value(None, CharField()),
            assigned=Value(None, IntegerField(null=True)),
            protocol_date=Value(None, DateField()),
            interval=Value(None, CharField()),
            request_type=Value(AbstractRequest.TYPE_LOAN, CharField()),

        ).select_related().filter(in_archive=archive)

        requests = GetUserAllowedRequests().execute(
            self.request.user,
            requests=requests
        ).select_related()

        loan_requests = GetUserAllowedLoanRequests().execute(
            self.request.user,
            requests=loan_requests
        ).select_related()

        if requests.first():
            requests = self.filter_queryset(self.request.GET, requests)

        if loan_requests.first():
            loan_requests = self.filter_queryset(
                self.request.GET,
                loan_requests
            )

        requests = requests.values(*self.selected_request_fields())
        loan_requests = loan_requests.values(*self.selected_request_fields())
        return requests.union(loan_requests).order_by('-status_changed_date')

    def list(self, *args, **kwargs):
        requests = self.get_queryset()
        page_limit = self.request.GET.get('limit', 50)
        len_requests = len(requests)
        len_requests_unique = len(requests.filter(request_number__in="-"))
        page = self.request.GET.get('page', 1)
        paginator = Paginator(requests, page_limit)
        paginated_requests = []
        if requests:
            try:
                paginated_requests = paginator.page(page)
            except PageNotAnInteger:
                paginated_requests = paginator.page(1)

        return Response({
            'requests': BaseRequestSerializer(
                paginated_requests,
                many=True
            ).data,
            'request_statuses': RequestStatusSerializer(
                RequestStatus.objects.all(), many=True
            ).data,
            'loan_statuses': LoanRequestStatusSerializer(
                LoanStatus.objects.all(), many=True
            ).data,
            'agents': AgentInfoSerializer(
                Agent.objects.filter(active=True, confirmed=True),
                many=True
            ).data,
            'page_count': paginator.num_pages if requests else 0,
            'len_requests': len_requests,
            'len_requests_unique': len_requests_unique,
            'banks': BankInfoSerializer(
                Bank.objects.filter(active=True),
                many=True
            ).data,
            'mfo': BankInfoSerializer(
                MFO.objects.filter(active=True),
                many=True
            ).data,
            'managers': [{
                'value': manager.id, 'label': manager.full_name
            } for manager in AgentManager.get_managers()]
        })

    @staticmethod
    def filter_queryset(request_get, queryset):
        filter_value = ujson.loads(request_get['filter'])
        if filter_value:
            if filter_value.get('request_number'):
                queryset = queryset.filter(
                    request_number__icontains=filter_value['request_number']
                )

            if filter_value.get('client'):
                queryset = queryset.filter(
                    Q(client__inn__icontains=filter_value['client']) |
                    Q(client__full_name__icontains=filter_value['client']) |
                    Q(client__short_name__icontains=filter_value['client'])
                )

            if filter_value.get('bank'):
                if isinstance(filter_value['bank'], str):
                    filter_value['bank'] = [int(filter_value['bank'])]
                elif not isinstance(filter_value['bank'], Iterable):
                    filter_value['bank'] = [filter_value['bank']]
                queryset = queryset.filter(bank__id__in=filter_value['bank'])

            if filter_value.get('required_amount_from'):
                queryset = queryset.filter(
                    required_amount__gte=filter_value['required_amount_from']
                )

            if filter_value.get('required_amount_to'):
                queryset = queryset.filter(
                    required_amount__lte=filter_value['required_amount_to']
                )

            if filter_value.get('created_date_from'):
                date_from = dateutil.parser.parse(
                    filter_value['created_date_from'])
                queryset = queryset.filter(
                    created_date__gte=datetime.datetime(
                        year=date_from.year,
                        month=date_from.month,
                        day=date_from.day,
                        hour=0,
                        minute=0
                    )
                )

            if filter_value.get('created_date_to'):
                date_to = dateutil.parser.parse(filter_value['created_date_to'])
                queryset = queryset.filter(
                    created_date__lte=datetime.datetime(
                        year=date_to.year,
                        month=date_to.month,
                        day=date_to.day,
                        hour=23,
                        minute=59
                    )
                )
            if filter_value.get('tender'):
                queryset = queryset.filter(
                    tender__notification_id__icontains=filter_value['tender']
                )

            if filter_value.get('status'):
                statuses = filter_value.get('status', [])
                if isinstance(statuses, str):
                    statuses = [statuses]
                queryset = queryset.filter(status__code__in=statuses)

            if filter_value.get('agent'):
                if isinstance(filter_value['agent'], str):
                    filter_value['agent'] = [int(filter_value['agent'])]
                elif not isinstance(filter_value['agent'], Iterable):
                    filter_value['agent'] = [filter_value['agent']]
                queryset = queryset.filter(agent_id__in=filter_value['agent'])

            if filter_value.get('manager'):
                if isinstance(filter_value['manager'], str):
                    filter_value['manager'] = [int(filter_value['manager'])]
                elif not isinstance(filter_value['manager'], list):
                    filter_value['manager'] = [filter_value['manager']]
                agents = AgentManager.objects.filter(
                    manager_id__in=filter_value['manager']
                ).values_list('agent_id', flat=True)
                queryset = queryset.filter(agent_id__in=agents)
        return queryset
