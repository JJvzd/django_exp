import os

import requests
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property
from sentry_sdk import capture_exception

from accounting_report.fields import QuarterData
from accounting_report.models import Quarter
from bank_guarantee.models import RequestStatus, Request
from base_request.models import RequestTender
from clients.models import Client, Agent
from common.helpers import generate_password
from questionnaire.models import (
    PassportDetails, Profile, LicensesSRO, KindOfActivity, BankAccount,
    ProfilePartnerLegalEntities
)
from users.models import Role, User


class CopyRequest:
    from_url = r'http://tenderhelp.ru/'
    token = os.environ.get('TOKEN_FOR_COPY_REQUEST')

    def __init__(self, from_request_id, from_url=None, token=None):
        self.from_request_id = from_request_id
        if from_url:
            self.from_url = from_url
        if token:
            self.token = token

    def get_data(self, url, params=None):
        if params is None:
            params = {}
        result = requests.get(
            self.from_url + url,
            params=params,
            headers={'Authorization': 'Token %s' % self.token},
            verify=False
        )
        try:
            return result.json()
        except Exception as error:
            capture_exception(error)
            raise error

    def get_request_data(self):
        url = r'api/requests/bank_guarantee/%s/' % str(self.from_request_id)
        result = self.get_data(url)
        return result.get('request')

    def get_profile_data(self):
        url = r'api/requests/bank_guarantee/%s/profile/' % str(self.from_request_id)
        result = self.get_data(url)
        return result.get('profile')

    def get_accountint_report_data(self, client_id):
        url = r'api/accounting_report/%s/' % client_id
        result = self.get_data(url)
        return result.get('quarters')

    @cached_property
    def agent(self):
        agent = Agent.objects.filter(inn=5010050218).first()
        if agent is None:
            agent = Agent.objects.first()
            if agent is None:
                BaseException('Нету созданных агентов')
        return agent

    @cached_property
    def agent_user(self):
        user = self.agent.user_set.first()
        if user is None:
            BaseException('У агента инн: %s нету пользователей' % self.agent.inn)
        return user

    @cached_property
    def manager(self):
        user = User.objects.filter(roles__name=Role.MANAGER).first()
        if user is None:
            BaseException('В системе нет менеджеров, создайте!')
        return user

    @cached_property
    def manager_fio(self):
        return self.manager.full_name

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
            license_sro_data.pop('profile', None)
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

    @staticmethod
    def persons_without_general_director(persons):
        return [p for p in persons if not p['is_general_director']]

    def save_general_director(self, profile, general_director):
        if general_director:
            general_director_id = general_director.pop('id', None)
            passport_data = general_director.pop('passport', {})
            passport = self.save_passport(passport_data)
            general_director.update({'passport': passport})
            general_director.update({'profile': profile})
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
            profile.profilepartnerindividual_set.filter(
                is_general_director=True
            ).exclude(id=gen_dir.id).delete()

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

    @classmethod
    def clear_id(cls, data):
        if isinstance(data, list):
            for d in data:
                cls.clear_id(d)
        if isinstance(data, dict):
            temp = list(data.keys())
            for key in temp:
                if key in ['id', 'profile'] and isinstance(data[key], int):
                    del data[key]
                else:
                    cls.clear_id(data[key])

    def update_profile(self, client):
        profile = client.profile
        profile_data = self.get_profile_data()
        self.clear_id(profile_data)
        if profile.general_director:
            profile_data['general_director']['id'] = profile.general_director.id
            profile_data['general_director']['passport']['id'] = profile.general_director.passport.id  # noqa
            profile_data['general_director']['document_gen_dir']['id'] = profile.general_director.document_gen_dir.id  # noqa

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

    def update_accounting_report(self, new_client, old_client_id):
        data = self.get_accountint_report_data(old_client_id)
        for d in data:
            quarter, create = Quarter.objects.update_or_create(
                quarter=d['quarter'],
                year=d['year'],
                client=new_client,
                defaults={'data': QuarterData(d['data']), 'no_data': d['no_data']}
            )

    def get_client(self, data):
        inn = data['inn']
        kpp = data['kpp']
        data['agent_company'] = self.agent
        data['agent_user'] = self.agent_user
        data['manager'] = self.manager
        data['managet_fio'] = self.manager_fio
        client_id = data['id']
        fields_for_delete = [
            'id',
            'inn',
            'kpp',
            'profile',
            'agent_user_id',
            'agent_company_id',
            'agent_company_inn',
            'agent_company_short_name',
            'email',
            'last_login',
            'managet_fio',
            'phone',

        ]
        for field in fields_for_delete:
            del data[field]
        client, create = Client.objects.update_or_create(inn=inn, kpp=kpp, defaults=data)
        self.update_profile(client)
        self.update_accounting_report(client, client_id)
        if create:
            self.create_user(client)
        return client

    def create_user(self, client, roles=[Role.CLIENT]):
        email = '%s@test.ru' % client.inn
        password = generate_password()
        user = User.objects.create_user(email, password=password)
        user.client = client
        user.roles.set(Role.objects.filter(name__in=roles))
        user.save()

    @staticmethod
    def get_tender(data):
        fields_for_delete = [
            'read_only_fields',
            'procuring_amount',
            'placement',
            'get_federal_law_display'

        ]
        for field in fields_for_delete:
            del data[field]
        return RequestTender.objects.create(**data)

    @staticmethod
    def get_status():
        return RequestStatus.objects.get(code=RequestStatus.CODE_DRAFT)

    def copy_request(self):
        data = self.get_request_data()
        fields_for_delete = [
            'id',
            'bank',
            'offer',
            'offer_additional_fields',
            'assigned',
            'additional_status',
            'rating',
            'base_request',
            'decision_maker',
            'request_number',
            'request_number_in_bank',
            'is_signed',
            'status_changed_date',
            'sent_to_bank_date',
            'created_date',
            'updated_date',
            'agent_user_id',
        ]
        for field in fields_for_delete:
            data.pop(field, None)
        data['banks_commissions'] = '{}'
        data['client'] = self.get_client(data['client'])
        data['tender'] = self.get_tender(data['tender'])
        data['status'] = self.get_status()
        data['agent'] = self.agent
        data['agent_user'] = self.agent.user_set.first()
        data['interval_to'] = timezone.datetime(*[
            int(i) for i in data['interval_to'].split('-')
        ])
        data['interval_from'] = timezone.datetime(*[
            int(i) for i in data['interval_from'].split('-')
        ])
        Request.objects.create(**data)
