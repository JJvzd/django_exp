import json

from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.decorators import action as drf_action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from bank_guarantee.actions import RequestActionHandler
from bank_guarantee.commission_logic import OfferCalculateCommissionLogic
from bank_guarantee.export_data import ExportRequest
from bank_guarantee.models import (
    Request as BGRequest, ClientDocument, RequestDocument, Request, Offer, OfferDocument,
    OfferPrintForm, ContractType, OfferAdditionalDataField
)
from bank_guarantee.serializers import (
    RequestSerializer, OfferDocumentCategorySerializer, DiscussSerializer,
    RequestHistorySerializer, OfferSerializer, RequestDocumentSerializer
)
from base_request.discuss_logic import (
    mark_user_read_messages, get_discuss_templates, get_discuss_title,
    get_discuss_messages, get_discuss
)
from base_request.serializers import PrintFormSerializer
from cabinet.base_logic.printing_forms.generate import OfferPrintGenerator
from cabinet.constants.constants import FederalLaw
from cabinet.serializers import FileSerializer
from clients.models import Bank, AgentManager, AgentRewards
from clients.serializers import (
    TemplateChatBankSerializer, TemplateChatAgentSerializer, AgentRewardsSerrializer
)
from common.mixins.request_viewset import MixinRequestViewSet
from dynamic_forms.logic.fields import config_field
from files.models import BaseFile
from permissions.logic.bank_guarantee import GetPrintForms
from settings.configs.banks import BankCode
from users.models import Role, User


class BGRequestsViewSet(MixinRequestViewSet, viewsets.ModelViewSet):
    request_type = 'bg'
    queryset = BGRequest.objects.all()
    serializer_class = RequestSerializer
    actions_handler_class = RequestActionHandler
    bank_model = Bank

    @staticmethod
    def update_documents_from_client(request):
        categories = request.get_categories()
        for category in categories:
            documents = ClientDocument.objects.filter(
                client=request.client, category=category
            )
            for document in documents:
                try:
                    RequestDocument.objects.create(
                        request=request,
                        category=category,
                        file=document.file,
                    )
                except Exception:
                    pass

    @staticmethod
    def get_document_links_choices(request):
        document_links = request.documentlinktoperson_set.all()
        return {link.document_id: link.person.id for link in document_links}

    def create_request(self, client, status):
        delivery_fio = ''
        delivery_email = ''
        delivery_phone = ''
        delivery_dop_phone = ''

        if self.request.user.has_role(Role.AGENT) or \
                self.request.user.has_role(Role.CLIENT):
            if isinstance(self.request.user.middle_name, type(None)):
                middle_name = ''
            else:
                middle_name = self.request.user.middle_name
            delivery_fio = '%s %s %s' % (
                self.request.user.last_name, self.request.user.first_name, middle_name
            )
            delivery_email = self.request.user.email
            delivery_phone = self.request.user.phone
            delivery_dop_phone = self.request.user.phone2

        request_data = self.request.data.get('request')

        tender_data = request_data.pop('tender')
        # автоматическая проставновка типа контракта
        if not request_data.get('contract_type') and tender_data.get('federal_law'):
            fz_44_185 = [FederalLaw.LAW_44, FederalLaw.LAW_615, FederalLaw.LAW_185]
            if tender_data['federal_law'] in fz_44_185:
                request_data['contract_type'] = ContractType.STATE

            if tender_data['federal_law'] == FederalLaw.LAW_223:
                request_data['contract_type'] = ContractType.MUNICIPAL
        request = Request.objects.create(
            contract_type=request_data.get('contract_type'),
            required_amount=request_data.get('required_amount'),
            interval_from=parse_date(request_data.get('interval_from')),
            interval_to=parse_date(request_data.get('interval_to')),
            interval=request_data.get('interval'),
            placement_way=request_data.get('placement_way'),
            targets=request_data.get('targets'),
            delivery_fio=delivery_fio,
            delivery_email=delivery_email,
            delivery_phone=delivery_phone,
            delivery_dop_phone=delivery_dop_phone,
            client=client,
            agent_user=client.agent_user,
            agent=client.agent_company,
        )
        request.tender.publish_date = parse_date(tender_data.pop('publish_date'))

        for field, value in tender_data.items():
            setattr(request.tender, field, value)

        request.tender.save()
        request.set_status(status)
        return request

    @drf_action(detail=True, methods=['GET'])
    def offer_documents(self, request, pk=None):
        request = self.queryset.filter(id=pk).first()
        step = self.request.GET.get('step', None)
        categories = Offer.get_categories(
            request.bank, step=step, has_offer=request.has_offer()
        )
        return Response({
            'categories': OfferDocumentCategorySerializer(
                categories,
                many=True,
                context={'request': request}
            ).data
        })

    @drf_action(detail=True, methods=['POST'])
    def generate_offer_print_form(self, request, pk=None):
        request = self.queryset.filter(id=pk).first()
        print_form = OfferPrintForm.objects.filter(
            id=self.request.data.get('print_form'),
        ).first()
        additional_data = self.request.data.get('additional_data')
        if additional_data:
            for key, val in additional_data.items():
                request.offer.save_additional_data(key, val)
        if print_form:
            OfferPrintGenerator().generate_print_form(request, print_form)
            return Response({
                'success': True
            })
        return Response({
            'error': 'Не задана печатная форма'
        })

    @drf_action(detail=True, methods=['GET'])
    def auto_calculate_offer_values(self, request, pk=None):
        request = self.queryset.filter(id=pk).first()
        data = {}
        if request.bank.code == BankCode.CODE_SPB_BANK:
            data['offer_active_end_date'] = (
                    timezone.now() + timezone.timedelta(days=30)
            ).strftime('%Y-%m-%d')

            if not request.has_offer():
                if request.required_amount > 50000000:
                    data['require_insurance'] = True

        return Response(data)

    @drf_action(detail=True, methods=['POST'])
    def calculate_offer_commission(self, request, pk=None):
        request = self.queryset.filter(id=pk).first()
        return Response(OfferCalculateCommissionLogic(
            request=request,
            data=self.request.data
        ).calculate())

    @drf_action(detail=True, methods=['GET', 'POST'])
    def discuss(self, *args, **kwargs):
        request = self.get_object()
        discuss = get_discuss(request)

        if self.request.method == 'POST':
            message = self.request.data.get('message')
            files = self.request.FILES.getlist('files[]')
            template_files_id = []
            if 'template_files' in self.request.data:
                for file in json.loads(self.request.data.get('template_files')):
                    base_file_from_template = BaseFile.objects.get(pk=file['id'])
                    content_file = ContentFile(base_file_from_template.file.read())
                    content_file.name = file.get('file_name', 'file_name')
                    new_file = BaseFile.objects.create(
                        file=content_file,
                        author_id=self.request.user.client_id
                    )
                    template_files_id.append(new_file.id)
            discuss.add_message(
                author=self.request.user, message=message, files=files,
                files_id=template_files_id
            )
        user = self.request.user
        templates = get_discuss_templates(user)
        templates_serializer_data = None
        if user.has_role('verifier') or user.has_role('manager'):
            templates_serializer_data = TemplateChatAgentSerializer(templates,
                                                                    many=True).data
        elif user.has_role('bank'):
            templates_serializer_data = TemplateChatBankSerializer(templates,
                                                                   many=True).data
        discuss_title = get_discuss_title(discuss=discuss, current_user=self.request.user)
        mark_user_read_messages(discuss=discuss, current_user=self.request.user)
        return Response({
            'discuss': DiscussSerializer(discuss).data,
            'messages': get_discuss_messages(
                discuss=discuss, current_user=self.request.user
            ),
            'templates': templates_serializer_data,
            'discuss_title': discuss_title
        })

    @drf_action(detail=True, methods=['GET'])
    def history(self, request, pk=None):
        request = self.queryset.filter(id=pk).first()
        return Response({
            'history': RequestHistorySerializer(
                request.requesthistory_set.order_by('id'),
                context={'request': self.request}, many=True
            ).data,
        })

    @drf_action(detail=True, methods=['GET'])
    def offer(self, pk=None):
        request = self.queryset.filter(id=pk).first()
        if request:
            return Response({
                'offer': OfferSerializer(request.offer).data,
            })
        return Response({
            'error': 'Заявка не найдена'
        })

    @drf_action(detail=True, methods=['GET'])
    def print_forms(self, request, pk=None):
        request = self.queryset.filter(id=pk).first()
        print_forms = GetPrintForms().execute(self.request.user)
        print_forms_ids = print_forms.values_list('id', flat=True)
        documents = request.requestdocument_set.filter(print_form_id__in=print_forms_ids)
        return Response({
            'print_forms': PrintFormSerializer(
                print_forms, many=True
            ).data if print_forms else None,
            'documents': RequestDocumentSerializer(
                documents, many=True
            ).data,
        })

    @drf_action(detail=True, methods=['POST'])
    def change_print_form(self, request, pk=None):
        request = self.queryset.filter(id=pk).first()
        print_form_id = self.request.data.get('print_form_id')
        file_id = self.request.data.get('file_id')
        base_file: RequestDocument = request.requestdocument_set.filter(
            print_form__id=print_form_id, file_id=file_id
        ).first()
        if not base_file:
            return Response({
                'errors': 'Файл не найден'
            }, status=403)
        if self.request.user.has_role(Role.VERIFIER):
            handler = RequestActionHandler(request=request, user=self.request.user)
            if 'EDIT' in handler.get_allowed_actions():
                file = self.request.FILES.get('file')
                if not file:
                    return Response({
                        'errors': 'Файл не передан'
                    }, status=403)

                old_file = base_file.file
                base_file.file = BaseFile.objects.create(
                    file=file, author_id=request.client_id
                )
                base_file.save()
                if RequestDocument.objects.filter(file_id=old_file.id).count() == 0:
                    old_file.delete()
                return Response({
                    'result': True
                }, status=200)
        return Response({
            'errors': 'Доступ запрещен'
        }, status=403)

    def check_object_permissions(self, request, obj):
        if not self.access_to_request(obj):
            raise PermissionDenied('Доступ запрещен')

    @drf_action(detail=True, methods=['GET'])
    def docs_for_sign(self, request, pk=None):
        request = self.queryset.filter(id=pk).first()
        self.check_object_permissions(self.request, request)
        files = FileSerializer(request.get_documents_for_sign_by_client(), many=True).data
        if len(list(filter(
                lambda x: x['sign'].get('sign_file') and x['old_sign'].get('sign_file'),
                files
        ))):
            request.update_signed(self.request.user)
        return Response({
            'documents_for_sign': files
        })

    @drf_action(detail=True, methods=['GET'])
    def offer_docs_for_sign(self, request, pk=None):
        request = self.queryset.filter(id=pk).first()

        if request.has_offer():
            documents = []
            if not request.is_signed and self.request.user.has_role(Role.CLIENT):
                documents += list(request.get_documents_for_sign_by_client().values_list(
                    'id', flat=True
                ))

            documents += list(request.offer.offerdocument_set.filter(
                file__isnull=False
            ).values_list('file', flat=True))
            files = FileSerializer(
                BaseFile.objects.filter(id__in=documents),
                many=True,
                context={'signer': self.request.user.client}
            ).data

            has_sign = len(list(filter(
                lambda x: x['sign'].get('sign_file') and x['old_sign'].get('sign_file'),
                files
            )))

            if has_sign:
                request.update_signed(self.request.user)
                request.offer.update_signed(self.request.user)
            return Response({
                'documents_for_sign': files
            })
        return Response({
            'documents_for_sign': []
        })

    @drf_action(detail=True, methods=['GET'])
    def delete_offer_document(self, *args, **kwargs):
        document_id = self.request.query_params.get('document_id')
        document = OfferDocument.objects.get(id=document_id)
        if not document:
            return Response({
                'error': "Файл не найден"
            })
        document.delete()
        return Response({
            'success': 'Файл удален'
        })

    @drf_action(detail=True, methods=['GET'])
    def export_as_zip(self, *args, **kwargs):
        request = self.get_object()
        helper = ExportRequest()
        mem_zip = helper.export_as_zip(request, self.request.user)
        response = HttpResponse(content_type="application/zip")
        filename = 'request_%s.zip' % request.request_number
        response["Content-Disposition"] = "attachment; filename=%s" % filename

        response.write(mem_zip.getvalue())

        return response

    @drf_action(detail=False, methods=['GET', 'POST'])
    def get_month_sales(self, *args, **kwargs):
        date = self.request.data.get('date')

        managers = User.objects.filter(roles__name=Role.MANAGER)
        agent_manager_model = AgentManager.objects.all()
        agent_rewards = AgentRewards.objects.all()

        requests = Request.objects.filter(status=26).order_by('id').select_related(
            'status', 'agent', 'client', 'tender', 'offer'
        )
        requests = requests.filter(offer__contract_date__icontains=date)
        requests_data = RequestSerializer(requests, many=True).data

        for request in requests_data:
            if request["agent"] is not None:
                agent_rewards = agent_rewards.filter(
                    agent_id=request["agent"]["id"]
                ).filter(bank_id=request["bank"]["id"])
                agent_rewards_data = AgentRewardsSerrializer(
                    agent_rewards, many=True
                ).data
                request["agent"]["percent"] = agent_rewards_data[0]["percent"]

                request["agent"]["manager"] = dict()
                manager_id = agent_manager_model.get(
                    agent_id=request["agent"]["id"]
                ).manager_id
                manager_data = managers.get(id=manager_id)
                request["agent"]["manager"]["id"] = manager_data.id
                request["agent"]["manager"]["first_name"] = manager_data.first_name

            if request["tmp_manager"] is not None:
                tmp_manager_id = request["tmp_manager"]
                request["tmp_manager"] = dict()
                tmp_manager_data = managers.get(id=tmp_manager_id)
                request["tmp_manager"]["id"] = tmp_manager_data.id
                request["tmp_manager"]["first_name"] = tmp_manager_data.first_name
            else:
                request["tmp_manager"] = dict()
                request["tmp_manager"]["id"] = None
                request["tmp_manager"]["first_name"] = "-----"

        return Response({
            'data': requests_data
        })

    @drf_action(detail=False, methods=['POST'])
    def save_data(self, *args, **kwargs):
        sales_data = self.request.data["sales_data"]
        requests_model = Request.objects.all()

        agent_rewards_model = AgentRewards.objects.all()
        offer_model = Offer.objects.all()

        for sale in sales_data:
            agent_rewards = agent_rewards_model.filter(
                agent_id=sale["agent"]["id"]
            ).filter(bank_id=sale["bank"]["id"])
            if sale["agent"]["percent"] is not None:
                agent_rewards.update(percent=sale["agent"]["percent"])


            offer = offer_model.filter(request_id=sale["id"])
            if sale["offer"]["default_commission_bank"] is not None:
                offer.update(
                    default_commission_bank=sale["offer"]["default_commission_bank"]
                )
            if sale["offer"]["delta_commission_bank"] is not None:
                offer.update(delta_commission_bank=sale["offer"]["delta_commission_bank"])
            if sale["offer"]["delta_commission"] is not None:
                offer.update(delta_commission=sale["offer"]["delta_commission"])
            if sale["agent"]["ruchnaya_korrect"] is not None:
                offer.update(ruchnaya_korrect=sale["agent"]["ruchnaya_korrect"])
            if sale["agent"]["kv_previsheniya"] is not None:
                offer.update(kv_previsheniya=sale["agent"]["kv_previsheniya"])

            if sale["tmp_manager"] is not None:
                requests = requests_model.filter(id=sale["id"])
                requests.update(tmp_manager=sale["tmp_manager"]["id"])
            else:
                requests.update(tmp_manager=None)

        return Response({
            'agents_new_value': sales_data
        })

    @drf_action(detail=True, methods=['GET'])
    def before_accept_offer(self, request, pk=None):
        request = self.queryset.filter(id=pk).first()
        bank_integration = request.bank_integration
        result = bank_integration.before_accept_offer(request)
        return Response(result)

    @drf_action(detail=True, methods=['GET'])
    def discuss_last_message(self, *args, **kwargs):
        request = self.get_object()
        discuss = get_discuss(request)
        return Response({
            'messages': get_discuss_messages(
                discuss=discuss, current_user=self.request.user
            )
        })

    @drf_action(detail=False, methods=['POST'])
    def change_additional_offer_choices(self, *args, **kwargs):
        data = self.request.data.get('field')
        offer_additional_data_field = OfferAdditionalDataField.objects.get(
            id=data['field_id']
        )
        offer_additional_data_field.config = json.dumps(
            data['config'],
            ensure_ascii=False
        )
        offer_additional_data_field.save()
        return Response({
            'additional_field': config_field(offer_additional_data_field)
        })
