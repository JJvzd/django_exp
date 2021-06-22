from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, Max, Value, CharField, F
from rest_framework import viewsets, status
from rest_framework.decorators import action as drf_action
from rest_framework.response import Response

from bank_guarantee.models import Message, Discuss
from bank_guarantee.serializers import BaseShortDiscussSerializer
from base_request.models import AbstractRequest
from clients.models import TemplateChatBank, MFO, Bank, Agent, Client, BaseFile, \
    TemplateChatAgent
from clients.serializers import TemplateChatBankSerializer, TemplateChatAgentSerializer
from tender_loans.models import LoanMessage, LoanDiscuss
from users.models import Role


class TemplateChatViewSet(viewsets.ViewSet):

    def list(self, request):
        if request.user.has_role('bank'):
            templates_chat = TemplateChatBank.objects.filter(
                bank=request.user.client
            ).order_by('id')
            return Response({
                'templates': TemplateChatBankSerializer(templates_chat, many=True).data
            })
        elif request.user.has_role('manager') or request.user.has_role('verifier'):
            templates_chat = TemplateChatAgent.objects.filter(
                user=request.user
            ).order_by('id')
            return Response({
                'templates': TemplateChatAgentSerializer(templates_chat, many=True).data
            })
        return Response({
            'error': 'Отказано в доступе',
            'code': status.HTTP_403_FORBIDDEN,
        }, status=status.HTTP_403_FORBIDDEN)

    @drf_action(detail=True, methods=['POST'])
    def update_template(self, request, pk=None):
        if request.user.has_role('bank'):
            template_chat = TemplateChatBank.objects.get(id=pk)
            template = TemplateChatBankSerializer(template_chat, data=request.data)
        elif request.user.has_role('manager') or request.user.has_role('verifier'):
            template_chat = TemplateChatAgent.objects.get(id=pk)
            template = TemplateChatAgentSerializer(template_chat, data=request.data)
        else:
            return Response({
                'error': 'Отказано в доступе',
                'code': status.HTTP_403_FORBIDDEN,
            }, status=status.HTTP_403_FORBIDDEN)
        if template.is_valid():
            base_files = []
            files = self.request.FILES.getlist('files')
            for file in files:
                base_file = BaseFile.objects.create(
                    file=file, author=template.validated_data['bank']
                )
                base_files.append(base_file)
            if base_files:
                template_chat.files.add(*base_files)
            else:
                template.save()
            return Response({
                'success': True
            })
        return Response({
            'error': template.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    @drf_action(detail=True, methods=['POST'])
    def delete(self, request, pk=None):
        try:
            if request.user.has_role('bank'):
                request.user.client.bank.templatechatbank_set.filter(id=pk).delete()
            elif request.user.has_role('manager') or request.user.has_role('verifier'):
                request.user.templatechatagent_set.filter(id=pk).delete()
            else:
                return Response({
                    'error': 'Отказано в доступе',
                    'code': status.HTTP_403_FORBIDDEN,
                }, status=status.HTTP_403_FORBIDDEN)
        except ObjectDoesNotExist:
            return Response({
                'success': False
            })
        else:
            return Response({
                'success': True
            })

    @drf_action(detail=True, methods=['POST'])
    def remove_file(self, request, pk=None):
        try:
            if request.user.has_role('bank'):
                templates = request.user.client.bank.templatechatbank_set.all()
            elif request.user.has_role('manager') or request.user.has_role('verifier'):
                templates = request.user.templatechatagent_set.all()
            else:
                return Response({
                    'error': 'Отказано в доступе',
                    'code': status.HTTP_403_FORBIDDEN,
                }, status=status.HTTP_403_FORBIDDEN)

            for template in templates:
                template.files.filter(id=pk).delete()
                break
        except ObjectDoesNotExist:
            return Response({
                'success': False
            })
        else:
            return Response({
                'success': True
            })

    @drf_action(detail=False, methods=['POST'])
    def add(self, request):
        if request.user.has_role('bank'):
            template = TemplateChatBankSerializer(data=request.data)
        elif request.user.has_role('manager') or request.user.has_role('verifier'):
            template = TemplateChatAgentSerializer(data=request.data,
                                                   context={'request': request})
        else:
            return Response({
                'error': 'Отказано в доступе',
                'code': status.HTTP_403_FORBIDDEN,
            }, status=status.HTTP_403_FORBIDDEN)

        if template.is_valid():
            base_files = []
            files = self.request.FILES.getlist('files')
            for file in files:
                base_file = BaseFile.objects.create(
                    file=file, author=request.user.client
                )
                base_files.append(base_file)
            template.save(files=base_files)
            return Response({
                'success': True
            })
        return Response({
            'errors': template.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class DiscussViewSet(viewsets.ViewSet):

    def selected_request_fields(self):
        return (
            'id',
            'bank__short_name',
            'request__client__short_name',
            'request__client__inn',

            'request__id',
            'request__request_number',
            'request__request_number_in_bank',
            'last_message',
            'message_count',
            'request_type',
        )

    def get_discusses(self, role, **kwargs):
        try:
            company = self.request.user.client.get_actual_instance
        except Exception:
            return Discuss.objects.none()

        if not isinstance(company, MFO):
            discuss_list = Message.objects.filter(
                **{'%s_read' % role: 0}
            ).values_list('discuss', flat=True).distinct()
            discuss = Discuss.objects.filter(id__in=discuss_list).filter(**kwargs)
        else:
            discuss = Discuss.objects.none()
        return discuss

    def get_loan_discusses(self, role, **kwargs):
        try:
            company = self.request.user.client.get_actual_instance
        except Exception:
            return LoanDiscuss.objects.none()

        if not isinstance(company, Bank):
            loan_discuss_list = LoanMessage.objects.filter(
                **{'%s_read' % role: 0}
            ).values_list('discuss', flat=True).distinct()

            loan_discuss = LoanDiscuss.objects.filter(
                id__in=loan_discuss_list
            ).filter(**kwargs)
        else:
            loan_discuss = LoanDiscuss.objects.none()
        return loan_discuss

    def get_queryset_data(self, role, **kwargs):
        discuss = self.get_discusses(role, **kwargs)
        loan_discuss = self.get_loan_discusses(role, **kwargs)

        discuss = discuss.select_related().annotate(
            message_count=Count('messages'),
            last_message=Max('messages__created'),
            request_type=Value(AbstractRequest.TYPE_BG, CharField()),
        ).values(*self.selected_request_fields())

        loan_discuss = loan_discuss.select_related().annotate(
            message_count=Count('message'),
            last_message=Max('message__created'),
            request_type=Value(AbstractRequest.TYPE_LOAN, CharField()),
        ).values(*self.selected_request_fields())
        return discuss.union(loan_discuss).order_by('-last_message')[:200]

    def get_queryset(self):
        try:
            company = self.request.user.client.get_actual_instance
        except Exception:
            return self.get_queryset_data(role='').none()
        if isinstance(company, Bank) or isinstance(company, MFO):
            return self.get_queryset_data(
                role='bank', bank=company, request__in_archive=False
            )

        if isinstance(company, Agent):
            if self.request.user.has_role(Role.SUPER_AGENT):
                return self.get_queryset_data(role='agent')
            if self.request.user.has_role(Role.MANAGER):
                return self.get_queryset_data(
                    role='agent',
                    request__client__manager_id=self.request.user,
                    request__in_archive=False
                )
            return self.get_queryset_data(
                role='agent', agent=company, request__in_archive=False
            )

        if isinstance(company, Client):
            return self.get_queryset_data(
                role='client', request__client=company, agent=F('request__agent'),
                request__in_archive=False
            )
        return self.get_queryset_data(role='').none()

    def list(self, *args, **kwargs):
        data = BaseShortDiscussSerializer(self.get_queryset(), many=True).data
        return Response({
            'data': data
        })

    @drf_action(detail=False, methods=['GET'])
    def count(self, request, pk=None):
        try:
            company = self.request.user.client.get_actual_instance
        except Exception:
            return Response({
                'count': 0
            })
        role = company.get_role().lower()
        if role == 'mfo':
            role = 'bank'
        filter_kwargs = {
            '%s_read' % role: 0
        }
        if role == 'bank':
            filter_kwargs['discuss__bank_id'] = company.id
        if role == 'agent':
            filter_kwargs['discuss__agent_id'] = company.id
        if role == 'client':
            filter_kwargs['discuss__request__client_id'] = company.id
        messages_count = Message.objects.filter(**filter_kwargs).count()
        loan_messages_count = LoanMessage.objects.filter(**filter_kwargs).count()
        count = 0
        try:
            count = messages_count + loan_messages_count
        except Exception:
            pass
        return Response({
            'count': count
        })
