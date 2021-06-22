import datetime
import json
import re

from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.core.paginator import Paginator, PageNotAnInteger
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy, resolve
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action as drf_action
from rest_framework.response import Response

from rest_framework.views import APIView

from accounting_report.serializers import QuarterSerializerInbank
from bank_guarantee.models import Request
from bank_guarantee.serializers import (
    FullRequestSerializerInbank, RequestSerializerInbank
)
from base_request.models import CompanyDocument, BankDocumentType
from cabinet.serializers import ProfileSerializerInbank, FileSerializer
from clients.models import Company, Client
from files.models import BaseFile
from questionnaire.models import Profile
from settings.configs.cabinets_enabled import CABINETS_ENABLED
from users.models import User, Role


class WorkInProgress(TemplateView):
    template_name = 'cabinet/work_in_progress.html'



class CheckRoleMixin:
    allowed_role = None

    def need_check_reglament(self) -> bool:
        role = self.request.user.client.get_role()
        if role in ['Client']:
            return True
        if role in ['Bank', 'MFO']:
            bank = self.request.user.client.get_actual_instance
            without_ecp = bank.settings.work_without_ecp
            if not without_ecp:
                return True
        return False

    def get(self, request, *args, **kwargs):
        if not CABINETS_ENABLED:
            if not self.request.user.has_role(Role.SUPER_AGENT):
                return redirect(reverse_lazy('work_in_progress'))

        if not self.request.user.client:
            return self.render_to_response({
                'errors': 'Доступ запрещен'
            })
        current_url = resolve(request.path_info).url_name
        if self.need_check_reglament():
            if not self.check_reglament():
                if current_url != 'reglament':
                    return redirect(reverse_lazy('reglament'))
                else:
                    return super(CheckRoleMixin, self).get(request, *args, **kwargs)
            else:
                if not self.check_person_confirm():
                    if current_url != 'person_confirm':
                        return redirect(reverse_lazy('person_confirm'))
                    else:
                        return super(CheckRoleMixin, self).get(request, *args, **kwargs)
        if self.request.user.client.get_role() != self.allowed_role:
            return redirect(reverse_lazy('cabinet'))
        return super(CheckRoleMixin, self).get(request, *args, **kwargs)

    def check_person_confirm(self):
        document = CompanyDocument.objects.filter(
            company=self.request.user.client,
            category_id=BankDocumentType.DOCUMENT_TYPE_PERSON_CONFIRM,
        ).first()
        if not (document and document.file.is_signed):
            return False
        return True

    def check_reglament(self):
        document = CompanyDocument.objects.filter(
            company=self.request.user.client,
            category_id=BankDocumentType.DOCUMENT_TYPE_EDO,
        ).first()
        if not (document and document.file.is_signed):
            return False
        return True


def generate_document(context, template, output_filename, category_id, user):
    rendered = render_to_string(template, context)
    base_file = BaseFile.objects.create(
        author=user.client,
    )
    base_file.file.save(output_filename, ContentFile('%s' % rendered))
    client_document, _ = CompanyDocument.objects.get_or_create(
        category_id=category_id,
        company=user.client,
    )
    if client_document.file:
        client_document.file.delete()
    client_document.file = base_file
    client_document.uploaded = timezone.now()
    client_document.save()
    return client_document


class ReglamentView(APIView):

    def post(self, request, *args, **kwargs):
        role = {
            'Client': 'клиента',
            'Agent': 'агента',
            'Bank': 'банка',
            'MFO': 'МФО',
        }.get(self.request.user.client.get_role())
        data = json.loads(self.request.body)
        context = {
            'client': self.request.user.client,
            'user': self.request.user,
            'document': data.get('document', '').split(),
            'role': role,
        }
        client_document = generate_document(
            context=context,
            template='cabinet/document_templates/edo_template.html',
            user=self.request.user,
            category_id=BankDocumentType.DOCUMENT_TYPE_EDO,
            output_filename='edo_confirm.html'
        )
        return JsonResponse({
            'documents_for_sign': [FileSerializer(client_document.file).data]
        })


class PersonConfirmView(LoginRequiredMixin, TemplateView):
    template_name = 'cabinet/person_confirm.html'

    def post(self, request, *args, **kwargs):
        errorsList = list()
        data = json.loads(self.request.body)
        context = {
            'first_name': data.get('first_name'),
            'last_name': data.get('last_name'),
            'middle_name': data.get('middle_name'),
            'series': data.get('series'),
            'number': data.get('number'),
            'issued_when': data.get('issued_when'),
            'issued_where': data.get('issued_where'),
            'issued_code': data.get('issued_code'),
            'registration_address': data.get('registration_address'),
        }
        client_document = generate_document(
            context=context,
            template='cabinet/document_templates/person_confirm_template.html',
            user=self.request.user,
            category_id=BankDocumentType.DOCUMENT_TYPE_PERSON_CONFIRM,
            output_filename='person_confirm.html'
        )
        name_pattern_1 = r'^([а-яА-ЯёЁ\s])*$'
        name_pattern_2 = r'^(([а-яА-ЯёЁ\s]*)-([а-яА-ЯёЁ]+))*$'

        if not (re.fullmatch(name_pattern_1, context['first_name'])
                or re.fullmatch(name_pattern_2, context['first_name'])):
            errorsList.append('first_name')

        if not (re.fullmatch(name_pattern_1, context['last_name']) or re.fullmatch(
                name_pattern_2, context['last_name'])):
            errorsList.append('last_name')
        if not (re.fullmatch(name_pattern_1,
                             context['middle_name']) or re.fullmatch(
                name_pattern_2, context['middle_name'])):
            errorsList.append('middle_name')
        if not (context['series'].isdigit() or isinstance(context['series'], int)):
            errorsList.append('series_1')
        if not len(context['series']) == 4:
            errorsList.append('series_2')
        if not (context['number'].isdigit() or isinstance(context['number'], int)):
            errorsList.append('number_1')
        if len(context['number']) != 6:
            errorsList.append('number_2')
        if not (re.fullmatch(r'^[№#а-яА-ЯёЁ0-9\s]*$', context['issued_where'])):
            errorsList.append('issued_where')
        if not (re.fullmatch(r'^([0-9]{4}-[0-9]{2}-[0-9]{2})*$', context['issued_when'])):
            errorsList.append('issued_when')
        if not (re.fullmatch(r'^([0-9]{3}-[0-9]{3})*$', context['issued_code'])):
            errorsList.append('issued_code')
        if not (re.fullmatch(r'^[,.а-яА-ЯёЁ0-9\s]*$', context['registration_address'])):
            errorsList.append('registration_address')

        if len(errorsList) > 0:
            return JsonResponse({'error': errorsList})
        else:
            return JsonResponse({
                'documents_for_sign': [FileSerializer(client_document.file).data]
            })


def count_keys(some_dict):
    count = 0
    for key in some_dict:
        if isinstance(some_dict[key], dict):
            count += count_keys(some_dict[key])
        else:
            count += 1
    return count


class ForceLoginView(APIView):

    def return_token(self, user):
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})

    def force_login(self, user):
        if user.is_active:
            if '_sha256' in user.password:
                backend = 'django.contrib.auth.backends.ModelBackend'
            else:
                backend = 'settings.authentications.OldTenderhelpAuthenticationBackend'
            need_set_super_agent = self.request.user.has_role(Role.SUPER_AGENT)
            need_set_head_agent = self.request.user.has_role(Role.HEAD_AGENT)
            need_set_manager = self.request.user.has_role(Role.MANAGER)
            agent_name = self.request.user.username
            login(self.request, user, backend=backend)
            self.request.session['agent_name'] = agent_name
            if need_set_super_agent:
                self.request.session['super_agent'] = 1
            else:
                self.request.session['super_agent'] = 0

            if need_set_head_agent:
                self.request.session['head_agent'] = 1
            else:
                self.request.session['head_agent'] = 0

            if need_set_manager:
                self.request.session['manager'] = 1
            else:
                self.request.session['manager'] = 0
        return self.return_token(user)

    def post(self, request, *args, **kwargs):
        company_id = self.request.POST.get('company_id')
        username = self.request.POST.get('username')
        user_id = self.request.POST.get('user_id')
        if company_id or username:
            if company_id:
                company = Company.objects.filter(id=company_id).first()
                if company:
                    user = None
                    if user_id:
                        try:
                            user = company.user_set.filter(id=user_id).first()
                        except Exception:
                            pass
                    if not user:
                        user = company.user_set.first()
                    if user:
                        return self.force_login(user)
            if username:
                user = User.objects.filter(username=username).first()
                if user:
                    return self.force_login(user)
        return self.return_token(self.request.user)


class InbankApi(viewsets.ViewSet):

    @drf_action(detail=False, url_path=r'requests/(?P<pk>[^/.]+)')
    def request_each(self, request, pk=None):
        request = Request.objects.filter(id=pk).first()
        if not request:
            return Response({
                'error': 'Заявки не существует'
            })
        if int(self.request.query_params.get('full')) == 1:

            return Response({
                'request': FullRequestSerializerInbank(request).data
            })
        else:
            return Response({
                'request': RequestSerializerInbank(request).data
            })

    @drf_action(detail=False, url_path=r'requests')
    def requests(self, *args, **kwargs):
        date = self.request.query_params.get('date')
        if not date:
            date = timezone.now()
        else:
            date = datetime.date(*[int(i) for i in date.split('-')])

        requests = Request.objects.filter(updated_date__date=date)
        page_limit = 200
        page = self.request.query_params.get('page', 1)
        paginator = Paginator(requests, page_limit)
        paginated_requests = []
        if requests:
            try:
                paginated_requests = paginator.page(page)
            except PageNotAnInteger:
                paginated_requests = paginator.page(1)

        return Response({
            'requests': RequestSerializerInbank(paginated_requests, many=True).data
        })

    @drf_action(detail=False, url_path=r'anketa/(?P<pk>[^/.]+)')
    def anketa(self, request, pk=None):
        profile = Profile.objects.filter(id=pk).first()
        if profile:
            return Response({
                'anketa': ProfileSerializerInbank(profile).data
            })
        else:
            return Response({
                'error': "Анкеты с id: %i" % pk
            })

    @drf_action(detail=False, url_path=r'accounting_report/(?P<pk>[^/.]+)')
    def accounting_report(self, request, pk=None):
        client = Client.objects.filter(id=pk).first()
        if client:
            return Response({
                'accounting_report': QuarterSerializerInbank(
                    client.accounting_report.get_quarters_for_fill(),
                    many=True).data
            })
        else:
            return Response({
                'error': 'Отчётности с данным id не найдено'
            })


class RedirectMosKomBank(APIView):

    def get(self, request, format=None):
        """Получения токена"""
        token = request.query_params.get('token')
        if not token:
            return Response({
                'error': 'Токен не получен'
            })
        cache.set('moskombank_token', token, 24 * 60 * 60 - 30)
        return Response({
            'success': True,
        })
