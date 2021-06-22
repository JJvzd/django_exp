import json
import logging

from constance import config
from django.conf import settings
from django.contrib.auth import login
from django.contrib.sites.models import Site
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import models
from django.db.models import Q
from rest_framework import generics
from rest_framework import status
from rest_framework.generics import UpdateAPIView
from rest_framework.parsers import FileUploadParser
from rest_framework.permissions import AllowAny
from rest_framework.renderers import TemplateHTMLRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from bank_guarantee.models import ClientDocument, Request, RequestStatus, RequestPrintForm
from bank_guarantee.serializers import ClientDocumentSerializer
from base_request.models import RequestTender, BankDocumentType
from base_request.serializers import (
    RequestTenderSerializer, RequestStatusSerializer, PrintFormSerializer
)
from cabinet.base_logic.printing_forms.generate import RequestPrintFormGenerator
from cabinet.constants.constants import OrganizationForm, TaxationType
from cabinet.models import Country
from cabinet.serializers import ProfileSerializer, ChangePasswordSerializer
from cabinet.views import count_keys
from clients.models import BaseFile
from clients.models.base import Bank
from clients.models.clients import Client, TenderHelpAgentComment
from clients.serializers import TenderHelpAgentCommentSerializer, BankSerializer
from external_api.searchtenderhelp_api import SearchTenderhelpApi
from permissions.logic.profile import CanViewProfile, CanEditProfile
from questionnaire.logic import ProfileValidator
from questionnaire.models import (
    Profile, ProfilePartnerLegalEntities, LicensesSRO, KindOfActivity, BankAccount,
    PassportDetails
)
from settings.authentications import OldTenderhelpAuthenticationBackend
from settings.configs.profile import AUTOSAVE_TIME
from settings.configs.website import HTML_MESSAGE
from users.models import User, Role
from users.permissions import allowed_roles
from utils.convertors import parse_str_to_list
from utils.serializaters import generate_serializer

logger = logging.getLogger('django')


class GetProfile(APIView):

    def get(self, request, pk):
        client = Client.objects.filter(id=pk).first()
        can_view = CanViewProfile().execute(request.user, profile=client.profile)
        if can_view:
            errors = ProfileValidator(client.profile).get_errors()
            len_errors = count_keys(errors)

            return Response({
                'autosave_time': AUTOSAVE_TIME or 500,
                'can_edit': CanEditProfile().execute(
                    request.user, profile=client.profile
                ),
                'is_ur_org': True,
                'profile': ProfileSerializer(client.profile).data,
                'tax_systems': [{'value': k, 'label': v} for k, v in
                                TaxationType.CHOICES],
                'countries': Country.objects.all().values_list('name', flat=True),
                'organization_forms': [{
                    'value': k,
                    'label': v
                } for k, v in OrganizationForm.CHOICES],
                'errors': errors,
                'len_errors': len_errors,
                'error': '',
            })
        else:
            return Response({
                'error': 'Profile not found'
            })

    def save_bank_accounts(self, profile, bank_accounts):
        bank_accounts_save = []
        for bank_account_data in bank_accounts:
            bank_account_id = bank_account_data.get('id')
            bank_account_data.pop('profile', None)
            if bank_account_id:
                bank_account = BankAccount.objects.filter(id=bank_account_id).first()
                self.update_from_dict(bank_account, bank_account_data)
            else:
                bank_account = profile.bankaccount_set.create()
                self.update_from_dict(bank_account, bank_account_data)
            bank_accounts_save.append(bank_account.id)
        BankAccount.objects.filter(profile=profile).exclude(
            id__in=bank_accounts_save
        ).delete()

    def save_activities(self, profile, activities):
        activities_save = []
        for activity_data in activities:
            activity_id = activity_data.get('id')
            activity_data.pop('profile', None)
            if activity_id:
                activity = KindOfActivity.objects.filter(id=activity_id).first()
                self.update_from_dict(activity, activity_data)
            else:
                activity = profile.kindofactivity_set.create()
                self.update_from_dict(activity, activity_data)
            activities_save.append(activity.id)
        KindOfActivity.objects.filter(profile=profile).exclude(
            id__in=activities_save
        ).delete()

    def save_licenses(self, profile, licenses):
        licenses_sro_save = []
        for license_sro_data in licenses:
            license_sro_id = license_sro_data.pop('id', None)
            license_sro_data.pop('profile')
            license_sro = None
            if license_sro_id:
                license_sro = LicensesSRO.objects.filter(id=license_sro_id).first()
            if not license_sro:
                license_sro = profile.licensessro_set.create()
            self.update_from_dict(license_sro, license_sro_data)
            licenses_sro_save.append(license_sro.id)
        LicensesSRO.objects.filter(profile=profile).exclude(
            id__in=licenses_sro_save
        ).delete()

    def person_empty(self, person):
        return all([not value for key, value in person.items() if
                    key in ['first_name', 'last_name', 'middle_name', 'fiz_inn']])

    def update_from_dict(self, obj, data):
        if data:
            for key, value in data.items():
                if hasattr(obj, key):
                    if obj._meta.get_field(key).__class__ is models.DateField:
                        if not value:
                            value = None
                    if key not in ['id']:
                        setattr(obj, key, value)
        obj.save()

    def save_passport(self, passport_data):
        passport_id = passport_data.pop('id', None)
        if not passport_id:
            passport = PassportDetails.objects.create()
        else:
            passport = PassportDetails.objects.filter(id=passport_id).first()
        self.update_from_dict(passport, passport_data)
        return passport

    def save_persons(self, profile: Profile, persons):
        persons_save = []
        for person_data in persons:
            if not self.person_empty(person_data):
                if person_data['resident'] is None:
                    person_data['resident'] = False
                passport_data = person_data.pop('passport', {})
                passport = self.save_passport(passport_data)
                person_data.update({'passport': passport})
                # не нужно сохранять для обычного участника
                person_data.pop('document_gen_dir', {})
                person_data.pop('profile', None)

                person_id = person_data.pop('id', None)
                if person_id:
                    person = profile.profilepartnerindividual_set.filter(
                        id=person_id
                    ).first()
                else:
                    person = profile.profilepartnerindividual_set.create()
                self.update_from_dict(person, person_data)
                persons_save.append(person_id)
        logger.info(
            'Delete persons without ids %s, not gen dir and not booker' % persons_save
        )
        records = profile.profilepartnerindividual_set.exclude(
            Q(id__in=persons_save) | Q(is_general_director=True) | Q(is_booker=True)
        )
        logger.info('Will delete %s ids' % list(records.values_list('id', flat=True)))
        records.delete()

    def persons_without_general_director(self, persons):
        return [p for p in persons if not p['is_general_director']]

    def save_general_director(self, profile, general_director):
        if general_director:
            general_director_id = general_director.pop('id', None)
            passport_data = general_director.pop('passport', {})
            passport = self.save_passport(passport_data)
            general_director.update({'passport': passport})
            general_director.update({'profile': profile})
            if general_director.get('share') == 100:
                general_director.update({'is_beneficiary': True})
            document_gen_dir_data = general_director.pop('document_gen_dir', {})
            gen_dir = None
            if general_director_id:
                gen_dir = profile.profilepartnerindividual_set.filter(
                    id=general_director_id
                ).first()
            if not gen_dir:
                gen_dir = profile.profilepartnerindividual_set.create(
                    is_general_director=True
                )

            self.update_from_dict(gen_dir, general_director)
            self.update_from_dict(gen_dir.document_gen_dir, document_gen_dir_data)
            logger.info('Delete persons with gen_dir=True without %s' % gen_dir.id)
            records = profile.profilepartnerindividual_set.filter(
                is_general_director=True
            ).exclude(id=gen_dir.id)
            logger.info('Will delete %s ids' % list(records.values_list('id', flat=True)))
            records.delete()

    def save_legal_sharehoders(self, profile, legal_shareholders):
        legal_shareholders_save = []
        for legal_shareholder_data in legal_shareholders:
            legal_shareholder_id = legal_shareholder_data.get('id')
            legal_shareholder_data.pop('profile', None)
            if legal_shareholder_data.get('passport'):
                passport_data = legal_shareholder_data.get('passport')
                if passport_data.get('id'):
                    passport = PassportDetails.objects.filter(
                        id=passport_data.pop('id')
                    ).first()
                else:
                    passport = PassportDetails.objects.create()
                self.update_from_dict(passport, passport_data)
                legal_shareholder_data.update({'passport': passport})
            if legal_shareholder_id:
                legal_shareholder = ProfilePartnerLegalEntities.objects.filter(
                    id=legal_shareholder_id
                ).first()
                self.update_from_dict(legal_shareholder, legal_shareholder_data)
            else:
                legal_shareholder = profile.profilepartnerlegalentities_set.create()
                self.update_from_dict(legal_shareholder, legal_shareholder_data)
            legal_shareholders_save.append(legal_shareholder.id)
        ProfilePartnerLegalEntities.objects.filter(profile=profile).exclude(
            id__in=legal_shareholders_save
        ).delete()

    def post(self, request, pk):
        client = Client.objects.filter(id=pk).first()

        profile = client.profile
        profile_data = request.data['profile']

        self.save_bank_accounts(
            profile=profile,
            bank_accounts=profile_data.pop('bank_accounts') or []
        )

        self.save_activities(
            profile=profile,
            activities=profile_data.pop('activities') or []
        )

        self.save_licenses(
            profile=profile,
            licenses=profile_data.pop('licenses_sro') or []
        )

        self.save_general_director(
            profile=profile,
            general_director=profile_data.pop('general_director') or {}
        )

        self.save_persons(
            profile=profile,
            persons=self.persons_without_general_director(
                profile_data.pop('persons') or []
            )
        )

        self.save_legal_sharehoders(
            profile=profile,
            legal_shareholders=profile_data.pop('legal_shareholders') or []
        )
        profile_data.pop('booker', None)
        self.update_from_dict(client.profile, profile_data)
        return self.get(request, pk)


class FindBik(APIView):

    def get(self, request):
        search_tenderhelp = SearchTenderhelpApi()
        return Response(search_tenderhelp.find_bik(request.query_params['bik']))


class Viewer(APIView):
    renderer_classes = [TemplateHTMLRenderer]
    office_extensions = [
        "doc", "docx", "xls", "xlsx", "xlsm", "xltm", "ppt", "pptx", "txt", "rtf"
    ]
    pdf_extentions = ['pdf']
    html_extenstions = ['html']
    image_extensions = ["jpg", "jpeg", "svg", "png", "gif"]

    def get(self, request):
        file = BaseFile.objects.filter(id=request.query_params.get('file_id')).first()
        domain = Site.objects.get_current().domain
        if file:
            filename = file.file.url
            office = any(
                [filename.endswith('.%s' % ext) for ext in self.office_extensions]
            )
            pdf = any([filename.endswith('.%s' % ext) for ext in self.pdf_extentions])
            image = any([filename.endswith('.%s' % ext) for ext in self.image_extensions])
            html = any([filename.endswith('.%s' % ext) for ext in self.html_extenstions])
            url = file.file.url
            if office:
                url = "https://view.officeapps.live.com/op/view.aspx?src=https://%s%s" % (
                    domain, file.file.url
                )
            if pdf or image:
                url = file.file.url
            content = None
            if html:
                content = open(file.file.path, 'r').read()

            return Response({
                'file': file,
                'content': content,
                'url': url,
                'is_image': image
            }, template_name='cabinet/api/file_viewer.html')


class RequestTenderRetrieve(generics.RetrieveAPIView):
    serializer_class = RequestTenderSerializer
    queryset = RequestTender.objects.all()


class MetaChangeUserLogin(APIView):
    permission_role = Role.SUPER_AGENT

    def _login_without_pass(self, user):
        login(
            self.request,
            user,
            settings.AUTHENTICATION_BACKENDS[1]
        )

    def check_permission(self):
        requset_user_role = self.request.user.roles.all()
        requset_user_role = requset_user_role.filter(name=self.permission_role)
        if not requset_user_role.exists():
            raise PermissionDenied

    def get_change_user(self):
        pass

    def get(self, request, pk):
        self.check_permission()
        self._login_without_pass(self.get_change_user())
        self.request.session['logging_by_super_agent'] = True
        return Response(
            status=status.HTTP_200_OK
        )


class ChangeUserLoginToBank(MetaChangeUserLogin):

    def get_change_user(self):
        bank = Bank.objects.get(id=self.kwargs['pk'])
        users_bank = User.objects.filter(client=bank)
        users_bank = users_bank.filter(
            roles=Role.objects.get(name=Role.GENERAL_BANK)
        )
        user_bank = users_bank.first()
        return user_bank


class ChangeUserLoginToClient(MetaChangeUserLogin):

    def get_change_user(self):
        client = Client.objects.get(id=self.kwargs['pk'])
        users_client = User.objects.get(client=client)
        return users_client


class ClientDocumentApi(APIView):
    model = ClientDocument
    serializer_class = ClientDocumentSerializer
    parser_class = (FileUploadParser,)

    def get_queryset(self):
        queryset = self.model.objects.all()
        queryset = queryset.filter(client__id=self.kwargs['pk'])
        return queryset

    def get_serializer_data(self, queryset):
        return self.serialaizer_class(queryset, many=True).data

    def get(self, request, pk, *args, **kwargs):
        data = self.get_queryset()
        documenttypes = BankDocumentType.objects.all()
        data_dict = {
        }
        for x in BankDocumentType.POSITION_CHOICES:
            data_dict[x[0]] = {}
            data_dict[x[0]] = {'position': x[1], 'data': []}
            for category in documenttypes.filter(position=x[0]):
                tmp_dict = {}
                tmp_dict['category_name'] = category.name
                tmp_dict['category_id'] = category.id
                client_document = self.get_serializer_data(data.filter(category=category))
                tmp_dict['client_document_list'] = client_document

                data_dict[x[0]]['data'].append(tmp_dict)

        return Response({
            'data': data_dict
        })

    def _get_request_for_post(self):
        data = {}
        data['category_id'] = int(self.request.query_params['category_id'])
        data['file_to_upload'] = self.request.data['file']
        data['client_id'] = int(self.kwargs['pk'])
        return data

    def create(self, data):
        base_file = BaseFile.objects.create(
            file=data['file_to_upload'],
            author=self.request.user.client
        )
        instance = self.model()
        instance.category_id = data['category_id']
        instance.client_id = data['client_id']
        instance.file = base_file
        instance.save()
        return instance

    def post(self, request, pk):
        file_id = self.request.query_params.get('file_id', None)
        if file_id:
            self.model.objects.filter(file_id=int(file_id)).delete()
            return Response(
                status=status.HTTP_200_OK
            )
        data = self._get_request_for_post()
        self.create(data)
        return Response(
            status=status.HTTP_200_OK
        )


class ClientChangeWinnerNotification(APIView):

    def get(self, request, pk, *args, **kwargs):
        client = Client.objects.get(id=self.kwargs['pk'])
        client.winner_notification = not client.winner_notification
        client.save()
        return Response(
            status=status.HTTP_200_OK
        )


class TenderHelpAgentCommentListCreate(generics.ListCreateAPIView):
    serializer_class = TenderHelpAgentCommentSerializer
    queryset = TenderHelpAgentComment.objects.all()

    def perform_create(self, serializer):
        serializer.validated_data['user'] = self.request.user
        serializer.save()


class Feedback(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, pk=None, *args, **kwargs):
        fields = request.data
        errors = []
        if not fields.get('name'):
            errors.append('Поле ФИО не может быть пустым')
        if not fields.get('email'):
            errors.append('Поле E-mail не может быть пустым')
        if not fields.get('phone'):
            errors.append('Поле Телефон не может быть пустым')
        if not fields.get('accept'):
            errors.append('Нет согласия на обработку персональных данных')
        errors = '\n'.join(errors)
        if errors:
            return Response({
                'errors': errors
            })
        html_msg = HTML_MESSAGE.format(
            name=fields['name'],
            email=fields['email'],
            phone=fields['phone'],
            text=fields['text'],
        )
        text_msg = "name:{name},email:{email},phone:{phone}\n{text}".format(
            name=fields['name'],
            email=fields['email'],
            phone=fields['phone'],
            text=fields['text'],
        )
        subject = 'Письмо с портала(Обратная связь)'
        from_email = settings.EMAIL_HOST_USER
        to_emails = parse_str_to_list(config.EMAIL_FOR_FEEDBACK)
        send_mail(subject, text_msg, from_email, to_emails, html_message=html_msg)
        return Response({
            'success': True
        })


class GetDevelopUsers(APIView):
    permission_classes = [allowed_roles([Role.DEVELOPER])]

    def get(self, *args, **kwargs):
        route_name = self.request.query_params.get('router_name')
        route_params = json.loads(self.request.query_params.get('router_params'))
        data = {}
        serializer = generate_serializer(User, [
            'id', 'full_name', 'client_id', 'username',
            {'field': 'roles', 'value': lambda x: ', '.join(x.get_roles)}
        ])
        if route_name == 'bg_request_page':
            request = route_params.get('id')
            request = Request.objects.get(id=request)
            bank_users = [] if not request.bank else serializer(
                request.bank.user_set.all(), many=True
            ).data

            client_users = serializer(request.client.user_set.all(), many=True).data
            verificators = serializer(User.objects.filter(
                roles__name=Role.VERIFIER
            ), many=True).data

            request_agent = serializer(request.agent.user_set.all(), many=True).data
            print_forms = RequestPrintForm.objects.filter(active=True)
            data = {
                'users': {
                    'bank_users': bank_users,
                    'client_users': client_users,
                    'verificators': verificators,
                    'request_agents': request_agent,
                },
                'statuses': RequestStatusSerializer(
                    RequestStatus.objects.all(), many=True
                ).data,
                'banks': BankSerializer(Bank.objects.all(), many=True).data,
                'print_forms': PrintFormSerializer(print_forms, many=True).data,
            }
        if route_name == 'loan_request_page':
            request = route_params.get('id')
            request = Request.objects.get(id=request)

            bank_users = [] if not request.bank else serializer(
                request.bank.user_set.all(), many=True
            ).data
            client_users = serializer(request.client.user_set.all(), many=True).data
            verificators = serializer(User.objects.filter(
                roles__name=Role.VERIFIER
            ), many=True).data
            request_agent = serializer(request.agent.user_set.all(), many=True).data
            data = {
                'users': {
                    'bank_users': bank_users,
                    'client_users': client_users,
                    'verificators': verificators,
                    'request_agents': request_agent,

                }
            }
        response_data = {
            "route_name": route_name,
            "route_params": route_params,
        }
        response_data.update(data)
        return Response(response_data)


class DeveloperChangeBank(APIView):
    permission_classes = [allowed_roles([Role.DEVELOPER])]

    def post(self, *args, **kwargs):
        request_id = self.request.data.get('request_id')
        bank_id = self.request.data.get('bank_id')
        request = Request.objects.filter(id=request_id).first()
        bank = Bank.objects.filter(id=bank_id).first()
        if request and bank:
            request.set_bank(bank)
            request.save()
            return Response({
                'result': True
            })
        return Response({
            'result': False
        })


class DeveloperChangeStatus(APIView):
    permission_classes = [allowed_roles([Role.DEVELOPER])]

    def post(self, *args, **kwargs):
        request_id = self.request.data.get('request_id')
        status_id = self.request.data.get('status_id')
        request = Request.objects.filter(id=request_id).first()
        status = RequestStatus.objects.filter(id=status_id).first()
        if request and status:
            request.set_status(status.code, force=True)
            return Response({
                'result': True
            })
        return Response({
            'result': False
        })


class DeveloperUpdatePrintForm(APIView):
    permission_classes = [allowed_roles([Role.DEVELOPER])]

    def post(self, *args, **kwargs):
        request_id = self.request.data.get('request_id')
        pf_id = self.request.data.get('pf_id')
        request = Request.objects.filter(id=request_id).first()
        pf = RequestPrintForm.objects.filter(id=pf_id).first()
        if request and pf:
            helper = RequestPrintFormGenerator()
            helper.generate_print_form(request=request, print_form=pf)
            return Response({
                'result': True
            })
        return Response({
            'result': False
        })


class ChangePasswordView(UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    model = User

    def get_object(self, queryset=None):
        object = self.request.user
        return object

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # проверка старого пароля
            if not self.object.check_password(serializer.data.get("old_password")):
                old_auth_backend = OldTenderhelpAuthenticationBackend()
                if not old_auth_backend.check_password(self.object, serializer.data.get(
                    "old_password")):
                    return Response(
                        {
                            "status": "error",
                            "code": status.HTTP_400_BAD_REQUEST,
                            "detail": "Вы ввели некорректный текущий(старый) пароль."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            # проверка не совпадения новых паролей
            if serializer.data.get("new_password1") != serializer.data.get(
                "new_password2"):
                return Response(
                    {
                        "status": "error",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "detail": "Новые пароли не совпадают."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # проверка совпадения нового и старого пароля
            if serializer.data.get("new_password1") == serializer.data.get(
                "old_password"):
                return Response(
                    {
                        "status": "error",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "detail": "Новый пароль должен отличаться от старого."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # проверка длины нового пароля
            if not (8 <= len(serializer.data.get("new_password1")) <= 128):
                return Response(
                    {
                        "status": "error",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "detail": "Новый пароль должен содержать от 8 до 128 символов."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            self.object.set_password(serializer.data.get("new_password1"))
            self.object.save()
            login(self.request, self.object, backend=settings.AUTHENTICATION_BACKENDS[1])
            return Response(
                {
                    "status": "success",
                    "code": status.HTTP_200_OK,
                    "detail": "Пароль успешно изменен.",
                }
            )
        return Response(
            {
                "status": "error",
                "code": status.HTTP_400_BAD_REQUEST,
                "detail": serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
