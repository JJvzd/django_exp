import datetime
import json
from collections import Iterable
from decimal import Decimal

import attr
from django.core.cache import cache
from django.db import models
from django.db.models import Q
from rest_framework import serializers
from sentry_sdk import capture_exception

from accounting_report.fields import QuarterData
from accounting_report.models import Quarter
from bank_guarantee.analysis.common import ProfessionalConclusionGenerator
from bank_guarantee.models import (
    RequestStatus, Offer, OfferDocument, Request, ExternalRequest, DocumentLinkToPerson,
    BankOfferDocumentCategory
)
from bank_guarantee.send_to_bank_logic.sending_to_bank_handler import (
    SendingToBanksHandler
)
from bank_guarantee.serializers import RequestSerializer
from bank_guarantee.signals import (
    request_create_offer, client_confirm_offer, finish_request, request_confirm_pay,
    get_ask_on_query
)
from base_request.actions import Action
from base_request.logic.actions import ActionHandler
from base_request.tasks import task_send_to_bank_from_verification
from cabinet.base_logic.scoring.base import ScoringLogic
from bank_guarantee.bank_integrations.spb_bank.actions import ChangeAssignedAction
from clients.models import Bank
from common.helpers import get_logger
from files.models import BaseFile
from notification.base import Notification
from permissions.rules import PEP
from questionnaire.logic import ProfileValidator
from questionnaire.models import (
    BankAccount, KindOfActivity, LicensesSRO, PassportDetails, Profile,
    ProfilePartnerLegalEntities
)
from settings.configs.other import PASSPORT_ID
from users.models import Role, User
from bank_guarantee.helpers.referal_sign import ReferalSign

logger = get_logger()


class EditAction(Action):
    code = 'EDIT'

    def allow_action(self):
        edit_statuses = [
            RequestStatus.CODE_DRAFT, RequestStatus.CODE_SENT_REQUEST,
            RequestStatus.CODE_VERIFIER_REQUIRE_MORE_INFO
        ]
        if self.request.status.code in edit_statuses:
            if self.request.agent_id == self.user.client_id:
                return True
            if self.request.client_id == self.user.client_id:
                return True
            if self.user.has_role(Role.SUPER_AGENT) or self.user.has_role(Role.MANAGER):
                return True
        if self.request.status.code in [RequestStatus.CODE_VERIFICATION]:
            if self.user.has_role(Role.VERIFIER):
                return True
        return False

    def clear_scoring(self):
        cache.delete(ScoringLogic.get_cache_name(self.request))

    def execute(self, params=None):
        if not params:
            return self.fail_result(errors='Не указана заявка')
        self.clear_scoring()
        request = params.get('request', {})
        # Обновления привязки паспортов паспортов
        if params.get('documents_link') is not None:
            documents_link = params.pop('documents_link')
            category = PASSPORT_ID
            for key, value in documents_link.items():
                DocumentLinkToPerson.set_link(
                    request_id=self.request.id,
                    document_category_id=category,
                    document_id=key,
                    person_id=value,
                )
            DocumentLinkToPerson.objects.filter(
                request=self.request,
                document_category__id=category,
            ).exclude(document__id__in=documents_link.keys()).delete()

        serializer = RequestSerializer(data=request, instance=self.request)
        if serializer.is_valid():
            serializer.save()
            # генерация печатных форм при изменении заявки при дозапросе
            if self.request.status.code == RequestStatus.CODE_SENT_REQUEST:
                self.request.refresh_from_db()
                self.request.generate_print_forms()
            return self.success_result(
                request=serializer.data
            )
        else:
            return self.fail_result(
                errors="Не корректно заполнена заявка", fields_errors=serializer.errors
            )

    def update_quarter(self, data, instance):
        data['data'] = QuarterData(data['data'])
        for key, val in data.items():
            if key == 'client':
                setattr(instance, 'client__id', val)
            elif key == 'id':
                pass
            else:
                setattr(instance, key, val)
        instance.save()

    def update_quarters(self, data):
        for obj in data:
            self.update_quarter(
                obj,
                Quarter.objects.get(pk=obj['id'])
            )

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
            if license_sro_id:
                license_sro = LicensesSRO.objects.filter(id=license_sro_id).first()
                self.update_from_dict(license_sro, license_sro_data)
            else:
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
        profile.profilepartnerindividual_set.exclude(
            Q(id__in=persons_save) | Q(is_general_director=True) | Q(is_booker=True)
        ).delete()

    def persons_without_general_director(self, persons):
        return [p for p in persons if not p['is_general_director']]

    def save_general_director(self, profile, general_director):
        if general_director:
            general_director_id = general_director.pop('id', None)
            passport_data = general_director.pop('passport', {})
            passport = self.save_passport(passport_data)
            general_director.update({'passport': passport})
            document_gen_dir_data = general_director.pop('document_gen_dir', {})
            general_director.pop('profile', None)
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
            profile.profilepartnerindividual_set.filter(
                is_general_director=True
            ).exclude(id=gen_dir.id).delete()

    def save_legal_sharehoders(self, profile, legal_shareholders):
        legal_shareholders_save = []
        passport_data = None
        for legal_shareholder_data in legal_shareholders:
            legal_shareholder_id = legal_shareholder_data.get('id')
            legal_shareholder_data.pop('profile', None)
            if legal_shareholder_data and legal_shareholder_data.get('passport'):
                passport_data = legal_shareholder_data.pop('passport')
            if legal_shareholder_id:
                legal_shareholder = ProfilePartnerLegalEntities.objects.filter(
                    id=legal_shareholder_id
                ).first()
            else:
                legal_shareholder = profile.profilepartnerlegalentities_set.create()
            if passport_data:
                self.update_from_dict(legal_shareholder.passport, passport_data)
            self.update_from_dict(legal_shareholder, legal_shareholder_data)
            legal_shareholders_save.append(legal_shareholder.id)
        ProfilePartnerLegalEntities.objects.filter(profile=profile).exclude(
            id__in=legal_shareholders_save
        ).delete()

    def update_profile(self, profile, profile_data):
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
        self.update_from_dict(profile, profile_data)


class SendToBankAction(Action):
    """Отправить в банк"""
    code = 'SEND_TO_BANK'
    request_serializer = RequestSerializer
    bank_model = Bank
    send_request_helper = SendingToBanksHandler

    def check_request_filled_without_errors(self):
        profile_errors = ProfileValidator(self.request.client.profile).get_errors()
        request_fill_valid = not self.request.validate_request
        docs_errors = self.request.validate_docs()
        finance_fill_valid = self.request.client.accounting_report.full_filled

        result = not profile_errors and request_fill_valid
        result = result and finance_fill_valid and docs_errors is True
        return result

    def allow_action(self):
        if self.request.status and self.request.status.code == RequestStatus.CODE_DRAFT:
            if self.request.agent_id == self.user.client_id:
                return self.check_request_filled_without_errors()

            if self.request.client_id == self.user.client_id:
                return self.check_request_filled_without_errors()

            if self.user.has_role('super_agent'):
                return self.check_request_filled_without_errors()

            if self.user.has_role('manager') and \
                self.request.client.manager == self.user:
                return self.check_request_filled_without_errors()
        return False

    def execute(self, params=None):
        if not params:
            return self.fail_result()
        banks_ids = params.get('banks')
        if not isinstance(banks_ids, Iterable):
            banks_ids = [banks_ids]
        if not banks_ids:
            return self.fail_result(errors='Не указаны банки')
        if len(banks_ids) != len(list(set(banks_ids))):
            logger.error('Ошибка при отправке в банк banks_ids: %s' % str(banks_ids))
        # Убираем дубли
        banks_ids = list(set(banks_ids))
        banks = self.bank_model.objects.filter(id__in=banks_ids)
        if banks.count() != len(banks_ids):
            return self.fail_result(errors='Некорректные банки')
        helper = self.send_request_helper(self.user)
        result = helper.send_to_many_banks(self.request, banks)
        return self.success_result(requests_list=[{
            'id': r.id,
            'number': r.get_number(),
            'bank': r.bank.short_name or r.bank.full_name,
        } for r in result])


class SignRequestAction(Action):
    code = 'SIGN_REQUEST'

    def allow_action(self):
        allowed_statuses = [
            RequestStatus.CODE_SENT_REQUEST,
            RequestStatus.CODE_CLIENT_SIGN,
        ]
        if not self.request.has_offer() and self.request.status.code in allowed_statuses:
            if self.request.client_id == self.user.client_id:
                return True

        return False

    def get_options(self):
        if self.request.sign_url:
            return {
                'sign_url': self.request.sign_url
            }
        return super(SignRequestAction, self).get_options()


class ChangeRequestNumber(Action):
    code = 'CHANGE_REQUEST_NUMBER'
    allowed_roles = [
        Role.BANK, Role.GENERAL_BANK, Role.BANK_COMMON, Role.BANK_UNDERWRITER
    ]

    def allow_action(self):
        status = self.request.status
        if self.request.bank and status.code != RequestStatus.CODE_SEND_TO_BANK:
            if self.request.bank_id == self.user.client_id:
                return True
        return False

    def execute(self, params=None):
        request_number_in_bank = params.get('request_number_in_bank') if params else None
        self.request.request_number_in_bank = request_number_in_bank or ''
        self.request.save()

        return self.success_result()


class InProcessAction(Action):
    code = 'IN_PROCESS'

    def allow_action(self):
        if self.request.status.code in [RequestStatus.CODE_SEND_TO_BANK]:
            if self.request.bank_id == self.user.client_id:
                return True
        return False

    def execute(self, params=None):
        request_number_in_bank = params.get('request_number_in_bank') if params else None

        if self.request.set_status(RequestStatus.CODE_IN_BANK):
            self.request.request_number_in_bank = request_number_in_bank or ''
            self.request.set_assigned(self.user, 'Взята в работу')
            self.request.save()
            self.request.log('getToWork', user=self.user)
            Notification.trigger(
                event_code='bank_to_work',
                params=self.request.collect_notification_parameters()
            )
            return self.success_result()
        return self.fail_result(errors='Недопустимый переход')


class RejectAction(Action):
    code = 'REJECT'
    allowed_roles = [
        Role.BANK, Role.GENERAL_BANK, Role.BANK_UNDERWRITER, Role.BANK_DECISION_MAKER
    ]
    status_code = RequestStatus.CODE_REQUEST_DENY

    def allow_action(self):
        not_allowed_statuses = [
            RequestStatus.CODE_FINISHED,
            RequestStatus.CODE_REQUEST_DENY,
            RequestStatus.CODE_OFFER_SENT,
            RequestStatus.CODE_OFFER_WAIT_PAID,
            RequestStatus.CODE_ASSIGNED_TO_ANOTHER_AGENT,
            RequestStatus.CODE_SENT_REQUEST,
            RequestStatus.CODE_OFFER_REJECTED,
        ]
        if self.request.status.code not in not_allowed_statuses:
            if self.request.bank_id and self.request.bank_id == self.user.client_id:
                return True
        return False

    @classmethod
    def get_force_emails(cls, request):
        return []

    @classmethod
    def reject(cls, request, reason, user, force=False):
        reason = {
            'reject_by_credit_committee': 'Отказ кредитного комитета',
            'reject_by_service_security': 'Отказ службы безопасности',
            'reject_assigned_by_another_agent': 'Закреплен за другим агентом',
        }.get(reason, reason)

        if reason == 'Закреплен за другим агентом':
            request.set_status(RequestStatus.CODE_ASSIGNED_TO_ANOTHER_AGENT, force=force)
        else:
            request.set_status(cls.status_code, force=force)
        Offer.objects.filter(request_id=request.id).delete()
        request.log(action='deny', user=user)
        Notification.trigger(
            'bank_deny',
            force_emails=cls.get_force_emails(request=request),
            params=request.collect_notification_parameters()
        )
        discuss = request.discusses.filter(bank=request.bank, agent=request.agent).first()
        if discuss and discuss.can_write(user):
            discuss.add_message(
                author=user,
                message='Отклонение заявки по причине: %s' % reason
            )
        request.bank_reject_reason = reason
        request.bank_integration.after_reject_request(request, reason=reason)
        request.save()

    def execute(self, params=None):
        reason = params.get('reason')
        force = params.get('force', False)
        if not reason:
            return self.fail_result(errors='Не указана причина')
        self.reject(self.request, reason, self.user, force)
        return self.success_result()


class AssignedToAnotherAgentAction(Action):
    """ Отклоняет заяву с причиной что клиент закреплен за другим агентом """
    code = 'ASSIGNED_TO_ANOTHER_AGENT'
    allowed_roles = [Role.BANK, Role.BANK_UNDERWRITER, Role.GENERAL_BANK]
    deny_statuses = [
        RequestStatus.CODE_OFFER_BACK,
        RequestStatus.CODE_OFFER_SENT,
        RequestStatus.CODE_FINISHED,
        RequestStatus.CODE_REQUEST_DENY,
        RequestStatus.CODE_OFFER_WAIT_PAID,
        RequestStatus.CODE_OFFER_PREPARE,
        RequestStatus.CODE_ASSIGNED_TO_ANOTHER_AGENT,
        RequestStatus.CODE_SENT_REQUEST,
        RequestStatus.CODE_OFFER_REJECTED,
    ]

    def allow_action(self):
        if self.request.bank_id and self.request.bank_id == self.user.client_id:
            return True
        return False

    def execute(self, params=None):
        RejectAction.reject(self.request, 'reject_assigned_by_another_agent', self.user)
        return self.success_result()


class SendRequestAction(Action):
    code = 'SEND_REQUEST'
    allowed_roles = [Role.BANK, Role.GENERAL_BANK, Role.BANK_UNDERWRITER]

    def allow_action(self):
        not_allowed_statuses = [
            RequestStatus.CODE_OFFER_BACK,
            RequestStatus.CODE_OFFER_SENT,
            RequestStatus.CODE_FINISHED,
            RequestStatus.CODE_REQUEST_DENY,
            RequestStatus.CODE_OFFER_WAIT_PAID,
            RequestStatus.CODE_OFFER_PREPARE,
            RequestStatus.CODE_ASSIGNED_TO_ANOTHER_AGENT,
            RequestStatus.CODE_SENT_REQUEST,
            RequestStatus.CODE_OFFER_REJECTED,
        ]
        if not self.user.has_role(Role.BANK_UNDERWRITER):
            not_allowed_statuses += [RequestStatus.CODE_OFFER_CREATED]

        if self.request.status.code not in not_allowed_statuses:
            if self.request.bank_id and self.request.bank_id == self.user.client_id:
                return True
        return False

    def execute(self, params=None):
        request_text = params.get('request_text')
        if not request_text:
            self.fail_result(errors='Не указан текст запроса')

        discuss = self.request.discusses.filter(
            bank=self.request.bank, agent=self.request.agent
        ).first()
        if discuss and discuss.can_write(self.user):
            template_files_id = None
            if 'template_files' in params:
                template_files_id = [
                    item['id'] for item in json.loads(params.get('template_files'))
                ]
            discuss.add_message(
                author=self.user, message=request_text, files_id=template_files_id
            )
        self.request.set_status(RequestStatus.CODE_SENT_REQUEST)
        Notification.trigger(
            'bank_back', params=self.request.collect_notification_parameters()
        )
        self.request.log('backToClient', user=self.user)
        return self.success_result()


class AskOnRequestAction(Action):
    code = 'ASK_ON_REQUEST'
    external_request_model = ExternalRequest

    def allow_action(self):
        if self.request.status.code == RequestStatus.CODE_SENT_REQUEST:
            if self.request.agent_id == self.user.client_id:
                return True
            if self.request.client_id == self.user.client_id:
                return True
            if self.user.has_role('super_agent') or self.user.has_role('manager'):
                return True
        return False

    def execute(self, params=None):
        self.request.set_status(RequestStatus.CODE_ASK_ON_REQUEST)
        get_ask_on_query.send_robust(
            sender=self.__class__, request=self.request, user=self.user
        )
        self.request.log('query_finished', self.user)
        return self.success_result()


class ReturnToJobAction(Action):
    code = 'RETURN_TO_JOB'

    def allow_action(self):
        if self.request.status.code == RequestStatus.CODE_ASK_ON_REQUEST:
            if self.request.bank == self.user.client.get_actual_instance:
                return True
            if self.user.has_role('super_agent') or self.user.has_role('manager'):
                return True
        return False

    def execute(self, params=None):
        if self.request.set_status(RequestStatus.CODE_IN_BANK):
            self.request.log('getToWork', self.user)
            return self.success_result()
        return self.fail_result()


class ConfirmRequestAction(Action):
    code = 'BANK_CONFIRM_REQUEST'
    allowed_roles = [Role.BANK, Role.GENERAL_BANK, Role.BANK_UNDERWRITER]

    def allow_action(self):
        if self.request.status.code in [
            RequestStatus.CODE_IN_BANK,
            # RequestStatus.CODE_ASK_ON_REQUEST
        ]:
            if self.request.bank_id == self.user.client_id:
                return True
        return False

    def execute(self, params=None):
        if self.request.set_status(RequestStatus.CODE_REQUEST_CONFIRMED):
            self.request.log('creditApprove', user=self.user)
            Notification.trigger(
                'bank_credit_approve',
                params=self.request.collect_notification_parameters()
            )
            return self.success_result()
        return self.fail_result(errors='Недопустимый переход')


class NewOfferSerializer(serializers.Serializer):
    amount = serializers.DecimalField(required=True, decimal_places=2, max_digits=20)
    commission_bank = serializers.DecimalField(
        required=True, decimal_places=2, max_digits=20
    )
    default_commission_bank = serializers.DecimalField(
        required=True, decimal_places=2, max_digits=20
    )
    default_commission_bank_percent = serializers.DecimalField(
        required=True, decimal_places=2, max_digits=20
    )
    delta_commission_bank = serializers.DecimalField(
        required=True, decimal_places=2, max_digits=20
    )
    commission_bank_percent = serializers.DecimalField(
        required=True, decimal_places=2, max_digits=20
    )
    offer_active_end_date = serializers.DateField(required=True)
    contract_date_end = serializers.DateField(required=True)
    require_insurance = serializers.BooleanField(required=False)


class CreateOfferAction(Action):
    code = 'CREATE_OFFER'
    serializer_offer_class = NewOfferSerializer
    offer_model = Offer
    offer_document_model = OfferDocument

    def allow_action(self):
        return PEP.is_allowed(
            user=self.user, obj=self.request, action='can_action_create_offer'
        )

    def get_options(self):
        result = {}
        if self.user.has_role(Role.BANK_UNDERWRITER):
            users = self.request.bank.user_set.filter(
                roles__name=Role.BANK_DECISION_MAKER
            )
            filtered_users = []
            for user in users:
                interval_from, interval_to = user.get_visible_interval()
                amount_from, amount_to = user.get_visible_amount()
                if (amount_from <= self.request.required_amount <= amount_to) and (
                    interval_from <= self.request.interval <= interval_to):
                    filtered_users.append(user)
            filtered_users = [{
                'value': user.id,
                'label': user.full_name
            } for user in filtered_users]
            result.update({
                'users': filtered_users
            })
        if self.request.has_offer() and BankOfferDocumentCategory.objects.filter(
            bank=self.request.bank,
            print_form__isnull=False,
            category__step=1
        ).exists():
            result.update({
                'need_ask_generate': True
            })
        return result

    def get_document_for_category(self, category):
        return self.offer_document_model.objects.filter(
            offer=self.request.offer, category=category
        )

    def get_change_offer(self, data):
        if not self.request.has_offer():
            return True
        elif self.request.request_type == self.request.TYPE_LOAN:
            return False

        serializer = self.serializer_offer_class(data=data)
        if serializer.is_valid():
            new_data = serializer.data
            old_data = self.serializer_offer_class(instance=self.request.offer).data
            for key, val in new_data.items():
                if old_data[key] != val:
                    return True
        old_assigned = self.request.requestassignedhistory_set.filter(
            assigner__roles__name=Role.BANK_DECISION_MAKER
        ).order_by('created').last()
        if old_assigned:
            old_assigned = old_assigned.assigner
        if str(data.get('assigned_id')) != str(old_assigned and old_assigned.id):
            return True
        additional_data = self.request.offer.get_additional_data
        for param, value in data.items():
            if param.startswith('additional_data'):
                field_name = param.split('[')[-1]
                field_name = field_name[:-1]

                empty_values = ['undefined', 'null', 'NaN']
                value = value if value and value not in empty_values else None
                if str(additional_data.get(field_name)) != str(value):
                    return True
        return False

    def execute(self, params=None):
        data = self.serializer_offer_class(data=params)
        if data.is_valid():
            assigned_id = params.get('assigned_id')
            assigned = None
            if params.get('request_interval_from') and params.get(
                'request_interval_to') and params.get('amount'):
                if self.request.interval_from != datetime.datetime.strptime(
                    params.get('request_interval_from'),
                    '%Y-%m-%d').date() \
                    or self.request.interval_to != datetime.datetime.strptime(
                    params.get('request_interval_to'),
                    '%Y-%m-%d').date() or self.request.required_amount != Decimal(
                    params.get('amount')):
                    self.request.interval_from = datetime.datetime.strptime(
                        params.get('request_interval_from'), '%Y-%m-%d')
                    self.request.interval_to = datetime.datetime.strptime(
                        params.get('request_interval_to'), '%Y-%m-%d')
                    self.request.required_amount = params.get('amount')
                    self.request.save(
                        update_fields=['interval_from', 'interval_to', 'required_amount'])
            if assigned_id and assigned_id not in ['null', 'undefined']:
                assigned = self.request.bank.user_set.filter(id=assigned_id).first()
            has_offer = self.request.has_offer()
            categories = self.offer_model.get_categories(
                self.request.bank, step=1, has_offer=has_offer
            )
            if not params.get('not_documents'):
                for category in categories:
                    if not params.get('category_%s' % category.id) and category.required:
                        if has_offer and self.get_document_for_category(category):
                            continue
                        return self.fail_result(
                            errors='Не прикреплены обязательные документы'
                        )
            cleared_data = data.validated_data
            offer, created = self.offer_model.objects.update_or_create(
                request=self.request,
                defaults=cleared_data
            )
            offer.update_agent_commissions()
            offer.save()
            for param, value in params.items():
                if param.startswith('additional_data'):
                    field_name = param.split('[')[-1]
                    field_name = field_name[:-1]
                    empty_values = ['undefined', 'null', 'NaN']
                    value = value if value and value not in empty_values else None
                    offer.save_additional_data(field_name, value)
            exclude_categories = []
            for category in categories:
                file_input_name = 'category_%s' % category.id
                new_doc = params.get(file_input_name, None)

                if new_doc:
                    exclude_categories.append(category)
                    self.offer_document_model.objects.filter(
                        offer=offer, category=category
                    ).delete()
                    if new_doc != 'undefined':
                        self.offer_document_model.objects.create(
                            offer=offer,
                            category=category,
                            file=BaseFile.objects.create(
                                file=new_doc,
                                author_id=self.user.client_id
                            )
                        )
            if self.request.status.code != RequestStatus.CODE_OFFER_SENT:
                offer.request.set_status(RequestStatus.CODE_OFFER_CREATED)
                offer.request.log('createOffer', user=self.user)

            request_create_offer.send_robust(sender=self.__class__, request=self.request)
            self.request.refresh_from_db()
            if assigned:
                self.request.additional_status = "underwriter_confirmed"
                self.request.set_assigned(assigned, reason='')
            if params.get('need_generate_print_forms') or created:
                offer.generate_print_forms(step=1, exclude_categories=exclude_categories)
            return self.success_result(offer_id=offer.id)

        else:
            return self.fail_result(**data.errors)


class SendOfferAction(Action):
    code = 'SEND_OFFER'

    def allow_action(self):
        return PEP.is_allowed(
            user=self.user, obj=self.request, action='can_action_send_offer'
        )

    def execute(self, params=None):
        self.request.set_status(RequestStatus.CODE_OFFER_SENT)
        if not self.request.bank.settings.is_handle_bank:
            discuss = self.request.discusses.filter(
                bank=self.request.bank,
                agent=self.request.agent
            ).first()
            if discuss and discuss.can_write(self.user):
                url = ReferalSign.generate_url(self.request.id, 'offer')
                discuss.add_message(
                    author=self.user,
                    message='Ссылка для принятия предложения: '
                            '<a href="{url}">{url}</a>'.format(url=url)
                )
        Notification.trigger(
            'bank_create_offer', params=self.request.collect_notification_parameters()
        )
        self.request.log('sendOffer', user=self.user)
        return self.success_result()


class OfferBackAction(Action):
    code = 'BACK_OFFER'

    def allow_action(self):
        status = self.request.status
        if self.request.status and status.code == RequestStatus.CODE_OFFER_SENT:
            if self.request.bank_id == self.user.client_id:
                return True
        return False

    def execute(self, params=None):
        self.request.set_status(RequestStatus.CODE_OFFER_BACK)
        self.request.log('offerBack', user=self.user)
        return self.success_result()


class RejectOfferAction(Action):
    code = 'REJECT_OFFER'

    @classmethod
    def deny(cls, request, user, log=True):
        request.set_status(RequestStatus.CODE_OFFER_REJECTED)
        Notification.trigger(
            'client_offer_deny',
            params=request.collect_notification_parameters()
        )
        if log:
            request.log('offerDeny', user=user)
        # отмена заявки по апи
        request.bank_integration.after_reject_offer(request)

    def allow_action(self):
        status = self.request.status
        if self.request.status and status.code == RequestStatus.CODE_OFFER_SENT:
            if self.request.agent_id == self.user.client_id:
                return True
            if self.request.client_id == self.user.client_id:
                return True
            if self.user.has_role('super_agent') or self.user.has_role('manager'):
                return True
        return False

    def execute(self, params=None):
        self.deny(self.request, self.user)
        return self.success_result()


class ConfirmOfferAction(Action):
    code = 'CLIENT_CONFIRM_OFFER'

    def allow_action(self):
        status = self.request.status
        if self.request.status and status.code == RequestStatus.CODE_OFFER_SENT:
            if self.request.client_id == self.user.client_id:
                return True
        return False

    def execute(self, params=None):
        self.request.set_status(RequestStatus.CODE_OFFER_WAIT_PAID)
        client_confirm_offer.send_robust(sender=self.__class__, request=self.request)
        self.request.log('ApplyBG', self.user)
        self.request.bank_integration.after_client_offer_confirm(self.request)
        Notification.trigger(
            'client_offer_apply', params=self.request.collect_notification_parameters()
        )
        requests = Request.objects.filter(
            base_request=self.request.base_request,
            client=self.request.client).exclude(id=self.request.id)

        for request in requests:
            if request.has_offer():
                RejectOfferAction.deny(request, self.user, log=False)
                log_str = "Заявка автоматически переведена в статус отказано " \
                          "при принятии предложения №%s"

                request.log(
                    action=log_str % self.request.offer.id,
                    user=self.request.bank.user_set.first()
                )
            else:
                log_str = "Заявка автоматически переведена в статус " \
                          "'Отозванная клиентом заявка' при принятии предложения №%s "
                request.log(
                    action=log_str % self.request.offer.id,
                    user=self.request.bank.user_set.first()
                )
                request.set_status(RequestStatus.CODE_REQUEST_BACK)
                # отмена заявки по апи
                request.bank_integration.after_reject_request(
                    request, reason='Заявка отменена клиентом'
                )

        return self.success_result()


class OfferPaidAction(Action):
    code = 'OFFER_PAID'

    def allow_action(self):
        if self.request.status.code == RequestStatus.CODE_OFFER_WAIT_PAID:
            if self.request.bank_id == self.user.client_id:
                return True
        return False

    def execute(self, params=None):
        self.request.set_status(RequestStatus.CODE_OFFER_PREPARE)
        Notification.trigger(
            'bank_confirm_pay', params=self.request.collect_notification_parameters()
        )
        request_confirm_pay.send_robust(sender=self.__class__, request=self.request)
        self.request.log('prepareBG', user=self.user)
        return self.success_result()


class OfferSecondStepSerializer(serializers.Serializer):
    contract_number = serializers.CharField(max_length=50)
    registry_number = serializers.CharField(
        max_length=50, required=False, allow_blank=True
    )
    contract_date = serializers.DateField()


class RequestFinishedAction(Action):
    """ Завершает выдачу БГ """
    code = 'REQUEST_FINISHED'

    def allow_action(self):
        if self.request.status.code == RequestStatus.CODE_OFFER_PREPARE:
            if self.request.bank_id == self.user.client_id:
                return True
        return False

    def execute(self, params=None):
        data = OfferSecondStepSerializer(data=params)
        if data.is_valid():
            categories = Offer.get_categories(self.request.bank, step=2, has_offer=True)
            if not params.get('not_documents'):
                for category in categories:
                    if not params.get('category_%s' % category.id) and category.required:
                        return self.fail_result(
                            errors='Не прикреплены обязательные документы'
                        )
            cleared_data = data.validated_data
            Offer.objects.filter(id=self.request.offer.id).update(
                **cleared_data
            )
            self.request.refresh_from_db()
            for category in categories:
                file_input_name = 'category_%s' % category.id
                new_doc = params.get(file_input_name, None)
                if new_doc and new_doc != 'undefined':
                    OfferDocument.objects.create(
                        offer=self.request.offer,
                        category=category,
                        file=BaseFile.objects.create(
                            file=new_doc,
                            author_id=self.user.client_id
                        )
                    )
            self.request.set_status(RequestStatus.CODE_FINISHED)
            self.request.log('sendBG', user=self.user)
            Notification.trigger(
                'bank_send_bg', params=self.request.collect_notification_parameters()

            )
            finish_request.send_robust(sender=self.__class__, request=self.request)
            return self.success_result()

        else:
            return self.fail_result(**data.errors)


class RequestApprovedByVerifier(Action):
    code = 'VERIFIER_APPROVED_REQUEST'

    def allow_action(self):
        status = self.request.status
        if self.request.status and status.code == RequestStatus.CODE_VERIFICATION:
            if self.user.has_role(Role.VERIFIER):
                return True
        return False

    def execute(self, params=None):
        task_send_to_bank_from_verification.delay(
            request_id=self.request.id, type='request', user_id=self.user.id
        )
        return self.success_result()


class RequestChangeVerifier(Action):
    code = 'CHANGE_VERIFIER'

    def allow_action(self):
        status = self.request.status
        if status and status.code == RequestStatus.CODE_VERIFICATION:
            if self.user.has_role(Role.VERIFIER):
                return True
        return False

    def get_options(self):
        users = User.objects.filter(roles__in=Role.objects.filter(name=Role.VERIFIER))

        variants = [
            {'value': user.id, 'label': user.full_name} for user in users
        ]
        return {
            'users': variants,
            'verifier_id': self.request.verifier_id,
        }

    def execute(self, params=None):
        try:
            new_verifier_id = int(params.get('verifier_id'))
            new_verifier = User.objects.filter(
                roles__in=Role.objects.filter(name=Role.VERIFIER)
            ).filter(
                id=new_verifier_id
            ).first()
            if new_verifier:
                self.request.verifier = new_verifier
                self.request.save()
                return self.success_result()
            return self.fail_result()
        except Exception as e:
            capture_exception(e)
            return self.fail_result()


class RequestDenyByVerifier(RejectAction):
    code = 'VERIFIER_DENY'
    status_code = RequestStatus.CODE_DENY_BY_VERIFIER
    allowed_statuses = [RequestStatus.CODE_VERIFICATION]
    allowed_roles = [Role.VERIFIER]

    def allow_action(self):
        status = self.request.status
        if status and status.code == RequestStatus.CODE_VERIFICATION:
            if self.user.has_role(Role.VERIFIER):
                return True
        return False

    @classmethod
    def get_force_emails(cls, request):
        emails = []
        if request.verifier:
            emails.append(request.verifier.email)
        if request.agent.email:
            emails.append(request.agent.email)
        return emails


class VerifierRequireMoreInfo(Action):
    code = 'VERIFIER_REQUIRE_MORE_INFO'

    def allow_action(self):
        status = self.request.status
        if status and status.code == RequestStatus.CODE_VERIFICATION:
            if self.user.has_role(Role.VERIFIER):
                return True
        return False

    def execute(self, params=None):
        self.request.set_status(RequestStatus.CODE_VERIFIER_REQUIRE_MORE_INFO)
        self.request.log('Верификатор отправил заявку на доработку', user=self.user)
        return self.success_result()


class ReturnToVerifier(Action):
    code = 'RETURN_TO_VERIFIER'

    def allow_action(self):
        status = self.request.status
        if status and status.code == RequestStatus.CODE_VERIFIER_REQUIRE_MORE_INFO:
            if self.user.has_role(Role.SUPER_AGENT):
                return True
            if self.user.has_role(Role.CLIENT) and \
                self.user.client_id == self.request.client_id:
                return True
            if self.user.has_role(Role.GENERAL_AGENT) and \
                self.user.client_id == self.request.agent_id:
                return True
            if self.user.has_role(Role.AGENT) and \
                self.user.id == self.request.agent_user_id:
                return True

        return False

    def execute(self, params=None):
        self.request.set_status(RequestStatus.CODE_VERIFICATION)
        if self.request.verifier:
            Notification.trigger(
                event_code='return_to_verification',
                force_emails=self.request.verifier.email,
                params=self.request.collect_notification_parameters()
            )
        self.request.log('Заявка отправлена на повторную верификацию', user=self.user)
        return self.success_result()


class RequestAnalysisAction(Action):
    code = 'REQUEST_ANALYSIS'

    def allow_action(self):
        if (self.user.has_role(Role.SUPER_AGENT) or self.user.has_role(Role.MANAGER) or
                self.user.has_role(Role.VERIFIER)):
            return True
        return False

    def execute(self, params=None):
        data = ProfessionalConclusionGenerator.get_data(
            client=self.request.client, request=self.request
        )
        return self.success_result(**attr.asdict(data))


class CloneRequestAction(Action):
    code = 'CLONE_REQUEST'

    def allow_action(self):
        if self.user.has_role(Role.SUPER_AGENT):
            return True
        if self.user.has_role(Role.CLIENT) and \
            self.user.client_id == self.request.client_id:
            return True
        if self.user.has_role(Role.GENERAL_AGENT) and \
            self.user.client_id == self.request.client.agent_company_id:
            return True
        if self.user.has_role(Role.AGENT) and \
            self.user.id == self.request.client.agent_user_id:
            return True
        if self.user.has_role(Role.MANAGER):
            return True
        return False

    def execute(self, params=None):
        new_request = self.request.clone_request(save_relation=False)
        return self.success_result(request_id=new_request.id)


class RequestCreateSignUrl(Action):
    code = 'CREATE_SIGN_URL'

    def allow_action(self):
        status = self.request.status
        if status:
            if self.user.has_role(Role.BANK):
                return True
            if self.user.has_role(Role.SUPER_AGENT):
                return True
            if self.user.has_role(Role.MANAGER):
                return True
        return False

    def execute(self, params=None):
        try:
            discuss = self.request.discusses.filter(
                bank=self.request.bank,
                agent=self.request.agent
            ).first()
            if discuss and discuss.can_write(self.user):
                msg = 'Ссылка для подписания заявки: <a href="{url}">{url}</a>'.format(
                    url=ReferalSign.generate_url(self.request.id, 'sign')
                )
                if self.request.status.code == RequestStatus.CODE_OFFER_SENT:
                    url = ReferalSign.generate_url(self.request.id, 'offer')
                    msg = 'Ссылка для принятия предложения: ' \
                          '<a href="{url}">{url}</a>'.format(url=url)
                discuss.add_message(
                    author=self.user,
                    message=msg
                )
            return self.success_result()
        except Exception as e:
            capture_exception(e)
            return self.fail_result()


class RequestActionHandler(ActionHandler):
    registered_actions = [
        EditAction,
        SendToBankAction,
        VerifierRequireMoreInfo,
        RequestApprovedByVerifier,
        RequestDenyByVerifier,
        SignRequestAction,
        # SignOfferAction,
        RequestChangeVerifier,
        ReturnToVerifier,
        InProcessAction,
        RejectAction,
        SendRequestAction,
        RejectOfferAction,
        ConfirmOfferAction,
        OfferPaidAction,
        RequestFinishedAction,
        AssignedToAnotherAgentAction,
        ConfirmRequestAction,
        SendOfferAction,
        CreateOfferAction,
        OfferBackAction,
        AskOnRequestAction,
        ReturnToJobAction,
        ChangeRequestNumber,
        ChangeAssignedAction,
        CloneRequestAction,
        RequestAnalysisAction,
        RequestCreateSignUrl,
    ]

    def call_action(self, action_code, params=None):

        for action in self.prepared_actions(self.user):
            if action.code == action_code:
                if action.validate_access():
                    response = action.execute(params=params)
                    return response
                else:
                    return {
                        'result': False,
                        'errors': 'Недопустимое действие с заявкой %s' % action_code
                    }
                break
        return {
            'result': False,
            'errors': 'Не найдено действие %s' % action_code
        }

    def prepared_actions(self, user):
        allowed = []
        for action in self.registered_actions:
            allowed.append(action(request=self.request, user=user))
        return allowed

    def get_allowed_actions(self):
        allowed = {}
        for action in self.prepared_actions(self.user):
            if action.validate_access():
                allowed[action.code] = action.get_options()
        return allowed
