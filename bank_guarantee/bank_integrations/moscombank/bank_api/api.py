import base64
import json
import os
import re
import zipfile
from datetime import datetime

import pdfkit
import requests
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone
from requests import Session

from bank_guarantee.models import ExternalRequest, MessageFile
from base_request.discuss_logic import get_discuss
from bank_guarantee.bank_integrations.api.farzoom.base import FarzoomSendRequest
from cabinet.base_logic.printing_forms.adapters.base import get_temp_path
from cabinet.base_logic.printing_forms.adapters.html import HTMLGenerator
from clients.models import MoscombankDocument, BaseFile
from common.helpers import get_logger
from external_api.searchtenderhelp_api import SearchTenderhelpApi
from questionnaire.models import ProfilePartnerLegalEntities
from settings.configs.banks import BankCode
from settings.settings import BASE_DIR
from users.models import Role

logger = get_logger()


class MoscomException(BaseException):
    pass


def check_response(func):
    def f(*args, **kwargs):
        for _ in range(3):
            response = func(*args, **kwargs)
            if isinstance(response, dict):
                if response.get('error') == 'Токен не валидный':
                    args[0].clear_token()
                    continue
                if response.get('error'):
                    raise MoscomException(str(response['error']))
            return response

    return f


class MoscombankApi(FarzoomSendRequest):
    bank_code = BankCode.CODE_MOSCOMBANK
    TOKEN_CACHE_TIME = 12 * 60 * 60 - 60
    TOKEN_CACHE_NAME = 'moskombank_token'
    CODE_CACHE_NAME = 'moskombank_code'

    def __init__(self, adapter):
        self.production_endpoint = settings.MOSCOMBANK_ENDPOINT
        self.app_id = settings.MOSCOMBANK_APP_ID
        self.secret = settings.MOSCOMBANK_SECRET
        self.redirect_url = settings.MOSCOMBANK_REDIRECT_URL
        self.adapter = adapter
        self.logs = []

    @staticmethod
    def check_response2(response):
        return response is None or response.get('error')

    def print_log(self, *args):
        self.logs.append(str(args))

    def get_redirect_url(self):
        return self.redirect_url

    def get_url(self, url):
        return self.production_endpoint + url

    def get_headers(self, token=True):
        if token:
            return {
                'token': self.get_token()
            }
        return {}

    def clear_token(self):
        cache.delete(self.TOKEN_CACHE_NAME)

    @check_response
    def get_data(self, url, params=None, token=True):
        headers = self.get_headers(token=token)
        if not params:
            params = {}
        client = Session()
        client.verify = False
        url = self.get_url(url)
        self.print_log('url', url)
        self.print_log('params', params)
        self.print_log('headers', headers)
        response = client.get(url, params=params, headers=headers, verify=False)
        if response.status_code != 200:
            return None
        response = response.json()
        self.print_log('response', response)

        if self.write_to_log:
            pass
        return response

    @check_response
    def send_file(self, url, file, data=None):
        headers = self.get_headers()
        if not data:
            data = {}
        url = self.get_url(url)
        client = Session()
        client.verify = False
        self.print_log(url)
        self.print_log(data)
        self.print_log(headers)
        response = client.post(
            url,
            files={'file': file},
            data=data,
            headers=headers,
        )
        if self.write_to_log:
            pass
        return response.json()

    @check_response
    def send_data(self, url, data=None):
        headers = self.get_headers()
        if not data:
            data = {}
        client = Session()
        client.verify = False
        url = self.get_url(url)
        self.print_log('data:', data)
        response = client.post(url, json=data, headers=headers)
        self.print_log('url', url)
        self.print_log('headers', headers)
        try:
            self.print_log(response.json())
            if self.write_to_log:
                pass
            return response.json()
        except json.decoder.JSONDecodeError:
            return None

    def get_code(self):
        """ Получение кода для OAuth2 аутентификации"""
        code = cache.get(self.CODE_CACHE_NAME)
        if not code:
            url = r'/api_v1/OAuth2/code'
            params = {
                'app_id': self.app_id,
                'redirect_url': self.get_redirect_url(),
                'secret': self.secret
            }
            response = self.get_data(url, params=params, token=False)
            if self.check_response2(response):
                if self.write_to_log:
                    pass
                return False
            code = response.get('code')
            cache.set(self.CODE_CACHE_NAME, code, self.TOKEN_CACHE_TIME)

        return cache.get(self.CODE_CACHE_NAME)

    def get_token(self):
        """ Получение токена для OAth2 аутентификации"""
        # return self.TOKEN

        token = cache.get(self.TOKEN_CACHE_NAME)

        if not token:
            code = self.get_code()
            if not code:
                if self.write_to_log:
                    pass
                return False
            params = {
                'code': code,
                'secret': self.secret
            }

            url = r'/api_v1/OAuth2/token'

            try:
                response = self.get_data(url, params=params, token=False)
            except requests.exceptions.ConnectionError as error:
                self.print_log(error)
                response = None
                val = re.search(r'token=\S+', str(error))
                if val:
                    response = {
                        'token': val[0][6:]
                    }

            token = response.get('token')
            cache.set(self.TOKEN_CACHE_NAME, token, self.TOKEN_CACHE_TIME)

        return cache.get(self.TOKEN_CACHE_NAME)

    def registration_client(self):
        url = r'/api_v1/user/register'
        data = self.adapter.get_client_registration_data()
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                self.print_log(response.get('error'))
            return False
        return response.get('user_hash')

    def get_user_hash(self):
        user_hash = self.adapter.external_request.get_other_data_for_key('user_hash')
        if not user_hash:
            user_hash = self.registration_client()
            self.adapter.external_request.set_other_data_for_key('user_hash', user_hash)
        return user_hash

    def update_profile(self):
        url = r'/api_v1/profile/common/update'
        response = self.send_data(url, data={
            'user_hash': self.get_user_hash(),
            'User': self.adapter.get_user_data(),
            'UserUl': self.adapter.get_user_ul_data(),
        })
        if self.write_to_log:
            pass
        return response

    def get_all_licenses(self, user_hash):
        url = r'/api_v1/profile/license/GetAll/%s' % user_hash
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response.get('data')

    def add_licenses(self, user_hash, license_ids):
        url = r'/api_v1/profile/license/add'
        data = {
            'user_hash': user_hash,
            'Licenses': self.adapter.get_licences_data(license_ids=license_ids)
        }
        response = self.send_data(url, data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_license(self, user_hash, id, license):
        url = r'/api_v1/profile/license/update/%s' % id
        response = self.send_data(url, data={
            'user_hash': user_hash,
            'License': self.adapter.get_license_data(license)
        })
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def delete_license(self, user_hash, id):
        url = r'/api_v1/profile/license/delete/%s' % id
        response = self.send_data(url, data={
            'user_hash': user_hash
        })
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_all_licenses(self):
        user_hash = self.get_user_hash()
        read_licenses = self.get_all_licenses(user_hash)
        if not read_licenses:
            read_licenses = []
        add_licenses = []
        for each_license in self.adapter.request.client.profile.licenses:
            select_license = list(filter(
                lambda x: x['license'] == each_license.number_license,
                read_licenses
            ))
            self.print_log(select_license)
            if select_license:
                select_license = select_license[0]
                select_license.update({
                    'not_delete': True
                })
                self.update_license(user_hash, select_license['id'], each_license)
            else:
                add_licenses.append(each_license.id)
        if len(add_licenses) > 0:
            self.add_licenses(user_hash, add_licenses)
        for el in filter(lambda x: not x.get('not_delete'), read_licenses):
            self.delete_license(user_hash, el['id'])
        return True

    def get_all_bank_accounts(self, user_hash):
        url = r'/api_v1/profile/account/GetAll/%s' % user_hash
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
        return response['data']

    def add_bank_account(self, user_hash, accounts):
        url = r'/api_v1/profile/account/add'
        data = {
            'user_hash': user_hash,
            'Accounts': self.adapter.get_bank_accounts_data(accounts=accounts)
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_account(self, user_hash, id, account):
        url = r'/api_v1/profile/account/update/%s' % id
        data = {
            'user_hash': user_hash,
            'Account': self.adapter.get_bank_account_data(account),
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def delete_account(self, user_hash, id):
        url = r'/api_v1/profile/account/delete/%s' % id
        data = {
            'user_hash': user_hash
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_all_accounts(self):
        user_hash = self.get_user_hash()
        read_accounts = self.get_all_bank_accounts(user_hash)
        add_accounts = []
        for account in self.adapter.request.client.profile.profileaccounts:
            select_account = list(filter(
                lambda x: x['current'] == account.bank_account_number,
                read_accounts
            ))
            if select_account:
                select_account = select_account[0]
                select_account.update({
                    'not_delete': True
                })
                self.update_account(user_hash, select_account['id'], account)
            else:
                add_accounts.append(account)
        self.print_log(self.add_bank_account(user_hash, add_accounts))
        for el in filter(lambda x: not x.get('not_delete'), read_accounts):
            self.delete_account(user_hash, el['id'])
        return True

    def get_all_address(self, user_hash):
        url = r'/api_v1/profile/address/GetAll/%s' % user_hash
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response.get('data')

    def update_address(self):
        url = r'/api_v1/profile/address/update'
        response = self.send_data(url, data=self.adapter.get_address_data())
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def get_all_phone(self, user_hash):
        url = r'/api_v1/profile/phone/GetAll/%s' % user_hash
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['data']

    def add_phones(self, user_hash, phones):
        url = r'/api_v1/profile/phone/add'
        data = {
            'user_hash': user_hash,
            'Phones': [{'phone': i} for i in phones],
        }
        response = self.send_data(url, data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_phone(self, user_hash, id, phone):
        url = r'/api_v1/profile/phone/update/%s' % id
        data = {
            'user_hash': user_hash,
            'Phone': phone,
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def delete_phone(self, user_hash, id):
        url = r'/api_v1/profile/phone/delete/%s' % id
        data = {
            'user_hash': user_hash
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_contact_phone(self):
        user_hash = self.get_user_hash()
        phones = self.get_all_phone(user_hash)
        if phones:
            self.delete_phone(
                user_hash,
                phones[0]['id'],
            )
        self.add_phones(
            user_hash,
            [self.adapter.request.client.profile.contact_phone]
        )
        return True

    def get_all_persons(self, user_hash):
        url = r'/api_v1/profile/person/GetAll/%s' % user_hash
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['data']

    def set_persons_id(self, external_request: ExternalRequest):
        data = self.get_all_persons(external_request.get_other_data_for_key('user_hash'))
        general_director_id = None
        booker_id = None
        dict_persons = {}
        for i in data:
            person = self.adapter.profile.profilepartnerindividual_set.filter(
                fiz_inn=i['inn']
            ).first()
            dict_persons.update({
                person.id: i['id']
            })
            if person.is_general_director:
                general_director_id = person.id
            if person.is_booker:
                booker_id = person.id
        external_request.set_other_data_for_key(
            'general_director_id', general_director_id
        )
        external_request.set_other_data_for_key('booker_id', booker_id)
        external_request.set_other_data_for_key('dict_persons', dict_persons)

    def add_persons(self, user_hash, persons):
        if not persons:
            return None
        url = r'/api_v1/profile/person/add'
        data = {
            'user_hash': user_hash,
            'Persons': self.adapter.get_persons_data(persons),
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_person(self, user_hash, id, person):
        url = r'/api_v1/profile/person/update/%s' % id
        data = {
            'user_hash': user_hash,
            'Person': self.adapter.get_person_data(person),
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def delete_person(self, user_hash, id):
        url = r'/api_v1/profile/person/delete/%s' % id
        data = {
            'user_hash': user_hash,
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_all_persons(self):
        user_hash = self.get_user_hash()
        read_persons = self.get_all_persons(user_hash)
        add_persons = []
        persons = self.adapter.request.client.profile.profilepartnerindividual_set.all()
        for person in persons:
            select_person = list(filter(
                lambda x: x['inn'] == person.fiz_inn,
                read_persons
            ))
            if select_person:
                select_person = select_person[0]
                select_person.update({
                    'not_delete': True
                })
                self.update_person(user_hash, select_person['id'], person)
            else:
                add_persons.append(person)
        self.add_persons(user_hash, add_persons)
        for el in filter(lambda x: not x.get('not_delete'), read_persons):
            self.delete_person(user_hash, el['id'])

        self.set_persons_id(self.adapter.external_request)
        return True

    def get_chief(self):
        url = r'/api_v1/profile/chief/Get/%s' % self.get_user_hash()
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['data']

    def update_chief(self):
        url = r'/api_v1/profile/chief/update'
        data = self.adapter.get_chief_data()
        response = self.send_data(url, data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def get_accountant(self):
        url = r'/api_v1/profile/accountant/Get/%s' % self.get_user_hash()
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['data']

    def update_accountant(self):
        url = r'/api_v1/profile/accountant/update'

        data = self.adapter.get_accountant_data(self.adapter.external_request)
        response = self.send_data(url, data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def get_all_individual_founder(self):
        url = r'/api_v1/profile/individualFounder/GetAll/%s' % self.get_user_hash()
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['data']

    def add_individual_founder(self, user_hash, persons):
        if not persons:
            return None
        url = r'/api_v1/profile/individualFounder/add'
        external_request = self.adapter.external_request
        dict_persons = external_request.get_other_data_for_key('dict_persons')
        self.print_log(dict_persons)
        individuals = []
        for person in persons:
            individuals.append({
                'person_id': dict_persons[str(person.id)],
                'percentage': '%.2f' % person.share,
            })
        data = {
            'user_hash': user_hash,
            'Individuals': individuals,
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_individual_founder(self, user_hash, id, person):
        url = r'/api_v1/profile/individualFounder/update/%s' % id
        external_request = self.adapter.external_request
        dict_persons = external_request.get_other_data_for_key('dict_persons')
        data = {
            'user_hash': user_hash,
            'Individual': {
                'person_id': dict_persons[str(person.id)],
                'percentage': '%.2f' % person.share,
            }
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def delete_individual_founder(self, user_hash, id):
        url = r'/api_v1/profile/individualFounder/delete/%s' % id
        data = {
            'user_hash': user_hash
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_all_individual_founder(self):
        user_hash = self.get_user_hash()
        read_individual_founder = self.get_all_individual_founder()
        dict_persons = self.adapter.external_request.get_other_data_for_key(
            'dict_persons'
        )
        self.print_log(dict_persons)
        add_individual_founder = []
        for person in self.adapter.request.client.profile.persons.filter(share__gt=0):
            select_individual_founder = list(filter(
                lambda x: x['person_id'] == dict_persons[str(person.id)],
                read_individual_founder)
            )
            if select_individual_founder:
                select_individual_founder = select_individual_founder[0]
                select_individual_founder.update({
                    'not_delete': True
                })
                self.update_individual_founder(
                    user_hash, select_individual_founder['id'], person
                )
            else:
                add_individual_founder.append(person)
        self.add_individual_founder(user_hash, add_individual_founder)

        for el in filter(lambda x: not x.get('not_delete'), read_individual_founder):
            self.delete_individual_founder(user_hash, el['id'])

        return True

    def get_all_entity_founders(self, user_hash):
        url = r'/api_v1/profile/entityFounder/GetAll/%s' % user_hash
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['data']

    def set_all_entity_founders(self, external_request: ExternalRequest):
        entity_founders = self.get_all_entity_founders(
            self.get_user_hash(),
        )
        if not entity_founders:
            if self.write_to_log:
                pass
            return False
        dict_entity_founder = {}
        for entity_founder in entity_founders:
            partner_legal = ProfilePartnerLegalEntities.objects.filter(
                inn=entity_founder['inn']
            ).first()
            dict_entity_founder.update({
                partner_legal.id: entity_founder['id']
            })
        external_request.set_other_data_for_key(
            'dict_entity_founders', dict_entity_founder
        )
        return True

    def add_entity_founder(self, user_hash, entity_founders):
        if not entity_founders:
            return None
        url = r'/api_v1/profile/entityFounder/add'
        data = {
            'user_hash': user_hash,
            'EntityFounder': self.adapter.get_entity_founders_data(
                entity_founders=entity_founders
            )
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_entity_founder(self, user_hash, id, entity_founder):
        url = r'/api_v1/profile/entityFounder/update/%s' % id
        data = {
            'user_hash': user_hash,
            'EntityFounder': self.adapter.get_entity_founder_data(
                entity_founder=entity_founder
            )
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def delete_entity_founder(self, id, user_hash):
        url = r'/api_v1/profile/entityFounder/delete/%s' % id
        data = {
            'user_hash': user_hash
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_all_entity_founder(self):
        user_hash = self.get_user_hash()
        read_entity_founder = self.get_all_entity_founders(user_hash)
        if not read_entity_founder:
            read_entity_founder = []
        add_entity_founder = []
        for entity_founder in self.adapter.request.client.profile.persons_entities:
            select_entity_founder = list(filter(
                lambda x: x['inn'] == entity_founder.inn,
                read_entity_founder
            ))
            if select_entity_founder:
                select_entity_founder = select_entity_founder[0]
                select_entity_founder.update({
                    'not_delete': True
                })
                self.print_log(self.update_entity_founder(
                    user_hash, select_entity_founder['id'], entity_founder
                ))

            else:
                add_entity_founder.append(entity_founder)
        self.add_entity_founder(user_hash, add_entity_founder)

        for el in filter(lambda x: not x.get('not_delete'), read_entity_founder):
            self.delete_individual_founder(user_hash, el['id'])

        self.set_all_entity_founders(self.adapter.external_request)

        return True

    def get_all_beneficiaries(self, user_hash):
        url = r'/api_v1/profile/beneficiary/GetAll/%s' % user_hash
        response = self.get_data(url)
        self.print_log(response)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['data']

    def add_beneficiary(self, user_hash, beneficiaries):
        if not beneficiaries:
            return None
        url = r'/api_v1/profile/beneficiary/add'
        beneficiaries_list = []
        dict_persons = self.adapter.external_request.get_other_data_for_key(
            'dict_persons'
        )
        for beneficiary in beneficiaries:
            beneficiaries_list.append({
                'person_id': dict_persons[str(beneficiary.id)],
                'percentage': float(beneficiary.share)
            })
        data = {
            'user_hash': user_hash,
            'Beneficiaries': beneficiaries_list,
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_beneficiary(self, user_hash, id, beneficiary):
        url = r'/api_v1/profile/beneficiary/update/%s' % id
        dict_persons = self.adapter.external_request.get_other_data_for_key(
            'dict_persons'
        )
        data = {
            'user_hash': user_hash,
            'Beneficiary': {
                'person_id': dict_persons.get(beneficiary.id),
                'percentage': float(beneficiary.share)
            }
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def delete_beneficiary(self, user_hash, id):
        url = r'/api_v1/profile/beneficiary/delete/%s' % id
        data = {
            'user_hash': user_hash
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_all_beneficiaries(self):
        user_hash = self.get_user_hash()
        read_beneficiaries = self.get_all_beneficiaries(user_hash)
        if not read_beneficiaries:
            read_beneficiaries = []
        dict_persons = self.adapter.external_request.get_other_data_for_key(
            'dict_persons'
        )
        add_beneficiaries = []
        profile = self.adapter.request.client.profile
        beneficiaries = profile.profilepartnerindividual_set.filter(share__gte=25.0)
        for beneficiary in beneficiaries:
            select_beneficiary = list(filter(
                lambda x: x.get('person_id') == dict_persons.get(beneficiary.id),
                read_beneficiaries
            ))
            if select_beneficiary:
                select_beneficiary = select_beneficiary[0]
                select_beneficiary.update({
                    'not_delete': True
                })
                self.update_beneficiary(user_hash, select_beneficiary['id'], beneficiary)
            else:
                add_beneficiaries.append(beneficiary)

        self.add_beneficiary(user_hash, add_beneficiaries)

        for el in filter(lambda x: not x.get('not_delete'), read_beneficiaries):
            self.delete_beneficiary(user_hash, el['id'])

        return True

    def get_all_guarantee(self, user_hash):
        url = r'/api_v1/guarantee/common/GetAll/%s' % user_hash
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['data']

    def get_guarantee_contract_data(self):
        return {
            'user_hash': self.adapter.external_request.get_other_data_for_key(
                'user_hash'
            ),
            'Guarantee': self.adapter.get_guarantee_data(),
            'GuaranteeLot': self.adapter.get_guarantee_lot_data(),
            'GuaranteeContract': self.adapter.get_guarantee_contract_data(),
            'UserUl': self.adapter.get_short_user_ul_data(),
        }

    def add_guarantee_contract(self):
        url = r'/api_v1/guarantee/contract/add'
        data = self.get_guarantee_contract_data()
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        self.adapter.external_request.external_id = response['guarantee_id']
        self.adapter.external_request.save()
        return response['guarantee_id']

    def update_guarantee_contract(self):
        external_id = self.adapter.external_request
        url = r'/api_v1/guarantee/contract/update/%s' % external_id
        data = self.get_guarantee_contract_data()
        for key, value in dict(data['GuaranteeContract']).items():
            if value is None:
                data['GuaranteeContract'].pop(key)
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return self.adapter.external_request.external_id

    def get_guarantee_tender_data(self):
        return {
            'user_hash': self.adapter.external_request.get_other_data_for_key(
                'user_hash'
            ),
            'Guarantee': self.adapter.get_guarantee_data(),
            'GuaranteeLot': self.adapter.get_guarantee_lot_data(),
            'GuaranteeTender': self.adapter.get_guarantee_tender_data(),
            'UserUl': self.adapter.get_short_user_ul_data(),
            'contract_number_this': '0',
        }

    def add_guarantee_tender(self):
        url = r'/api_v1/guarantee/tender/add'
        data = self.get_guarantee_tender_data()
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        self.adapter.external_request.external_id = response['guarantee_id']
        self.adapter.external_request.save()
        return response['guarantee_id']

    def update_guarantee_tender(self):
        external_id = self.adapter.external_request.external_id
        url = r'/api_v1/guarantee/tender/update/%s' % external_id
        data = self.get_guarantee_tender_data()
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return self.adapter.external_request.external_id

    def get_guarantee_quality_data(self):
        return {
            'user_hash': self.adapter.external_request.get_other_data_for_key(
                'user_hash'
            ),
            'Guarantee': self.adapter.get_guarantee_data(),
            'GuaranteeLot': self.adapter.get_guarantee_lot_data(),
            'GuaranteeQuality': self.adapter.get_guarantee_quality_data(),
            'UserUl': self.adapter.get_short_user_ul_data(),
            'contract_number_this': '0',
        }

    def add_guarantee_quality(self):
        url = r'/api_v1/guarantee/quality/add'
        data = self.get_guarantee_quality_data()
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        self.adapter.external_request.external_id = response['guarantee_id']
        self.adapter.external_request.save()
        return response['guarantee_id']

    def update_guarantee_quality(self):
        external_id = self.adapter.external_request.external_id
        url = r'/api_v1/guarantee/quality/update/%s' % external_id
        data = self.get_guarantee_quality_data()
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return self.adapter.external_request.external_id

    def get_guarantee_advance_data(self):
        return {
            'user_hash': self.adapter.external_request.get_other_data_for_key(
                'user_hash'
            ),
            'Guarantee': self.adapter.get_guarantee_data(),
            'GuaranteeLot': self.adapter.get_guarantee_lot_data(),
            'GuaranteeAdvance': self.adapter.get_guarantee_advance_data(),
            'UserUl': self.adapter.get_short_user_ul_data(),
            'contract_number_this': '0',
        }

    def add_guarantee_advance(self):
        url = r'/api_v1/guarantee/advance/add'
        data = self.get_guarantee_advance_data()
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        self.adapter.external_request.external_id = response['guarantee_id']
        self.adapter.external_request.save()
        return response['guarantee_id']

    def update_guarantee_advance(self):
        external_id = self.adapter.external_request.external_id
        url = r'/api_v1/guarantee/advance/update/%s' % external_id
        data = self.get_guarantee_advance_data()
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return self.adapter.external_request.external_id

    def get_similar_contract(self, external_request: ExternalRequest):
        url = r'/api_v1/guarantee/similarContract/GetAll/%s/%s' % (
            self.get_user_hash(),
            external_request.external_id,
        )
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['data']

    def add_similar_contract(self, contracts, external_request: ExternalRequest):
        """Добавления контрактов
            сontracts [
                {
                    'costumer': Заказчик и ИНН Заказчика,
                    'term': Срок Контракта,
                    'value': Стоимость контракта, тыс. руб.,
                    'work': Виды выполняемых работ,
                }
                ...
            ]
        """
        bg_id = external_request.external_id
        if bg_id is None:
            return False
        url = r'/api_v1/guarantee/similarContract/add/%s' % bg_id
        data = {
            'user_hash': external_request.get_other_data_for_key('user_hash'),
            'GuaranteeSimilarContracts': contracts,
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return True

    def update_similar_contract(self, contract_id, user_hash, contract):
        """Обновления контракта
            contract {
                'customer': Заказчик и ИНН Заказчика,
                'term': Срок Контракта,
                'value': Стоимость контракта, тыс. руб.,
                'work': Виды выполяемых работ,
            }
        """
        url = r'/api_v1/guarantee/similarContract/update/%s' % contract_id
        data = {
            'user_hash': user_hash,
            'GuaranteeSimilarContract': contract,
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def delete_similar_contract(self, contract_id, user_hash):
        url = r'/api_v1/guarantee/similarContract/delete/%s' % contract_id
        data = {
            'user_hash': user_hash
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def update_all_similar_contracts(self):
        api = SearchTenderhelpApi()
        contracts = api.get_contracts('7451334464')
        data = []
        for contract in contracts:
            try:
                period = contracts['data']['executionPeriod']
                data.append({
                    'work': contract['data']['products']['product']['name'],
                    'customer': contract['data']['customer']['shortName'],
                    'value': contract['price'],
                    'term': '%i дней' % (datetime(*period['endDate'].split('-'))
                                         - datetime(*period['startDate'].split('-'))).days

                })
            except Exception:
                continue

        if len(data) == 0:
            data.append({
                'work': 'Нет',
                'customer': 'Нет',
                'value': 'Нет',
                'term': 'Нет',
            })
        contracts_delete = self.get_similar_contract(self.adapter.external_request)
        self.print_log(contracts_delete)
        user_hash = self.get_user_hash()
        for contract_delete in contracts_delete:
            self.delete_similar_contract(contract_delete['id'], user_hash)
        self.add_similar_contract(data, self.adapter.external_request)

    def get_actual_finance_period(self):
        url = r'/api_v1/guarantee/finance/GetPeriod'
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def add_finance(self):
        url = r'/api_v1/guarantee/finance/AddBalance'
        response = self.get_actual_finance_period()
        data = {
            'user_hash': self.adapter.external_request.get_other_data_for_key(
                'user_hash'
            ),
            'Balance': self.adapter.get_finance(response['data'])
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def get_document_list(self):
        external_request = self.adapter.external_request
        url = r'/api_v1/document/list/%s/%s' % (
            external_request.get_other_data_for_key('user_hash'),
            external_request.external_id,
        )
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        external_request = self.adapter.external_request
        return list(filter(
            lambda x: x['document_id'] != external_request.get_other_data_for_key(
                'documents_from_client'
            ),
            response['documents']
        ))

    def get_file_for_upload(self, data):
        if data['type'] == 'bank':
            return self.get_file_for_upload_bank(data)
        if data['type'] == 'additional':
            return self.get_file_for_upload_additional(data)

    def get_additional_file(self, doc_id):
        requested_category_id = self.adapter.external_request.get_other_data_for_key(
            'requested_categories'
        )
        if requested_category_id is not None:
            requested_category_id = requested_category_id.get(doc_id)
        if requested_category_id:
            return self.adapter.request.requestedcategory_set.get(
                id=requested_category_id
            )

    def get_file_for_upload_additional(self, data):
        requested_category = self.get_additional_file(data['document_id'])
        if requested_category:
            file_list = requested_category.requestdocument_set.all()
            return self.get_zip(file_list)
        return None, None, None

    def get_file_for_upload_bank(self, data):
        moscom_doc, created = MoscombankDocument.objects.get_or_create(doc_id=data['id'])
        if created:
            moscom_doc.name = data['name']

            moscom_doc.doc_type = data['type']
            moscom_doc.save()

            logger.error('Сопоставьте документ %s для Москомбанка' % data['name'])
            return None, None, None
        if moscom_doc.category.first() or moscom_doc.print_form.first():
            file_list = self.adapter.request.requestdocument_set.filter(
                Q(category__in=moscom_doc.category.all()) |
                Q(print_form__in=moscom_doc.print_form.all())
            )
            if file_list.count() == 0:
                if moscom_doc.equal_doc:
                    file_list = self.adapter.request.requestdocument_set.filter(
                        Q(category__in=moscom_doc.equal_doc.category.all()) |
                        Q(print_form__in=moscom_doc.equal_doc.print_form.all())
                    )
        else:
            logger.error('Сопоставьте документ %s для Москомбанка' % data['name'])
            return None, None, None
        count = file_list.count()
        if count == 0:
            return None, None, None
        else:
            return self.get_zip(file_list)

    def get_zip(self, file_list):
        path = get_temp_path('.zip')
        name = None
        is_signed = False
        with zipfile.ZipFile(path, 'w') as my_zip:
            for file in file_list:
                file_paths = self.get_file(file.file)
                name = '.'.join(file_paths[0][1].split('.')[:-1])
                my_zip.write(file_paths[0][0], file_paths[0][1])
                if len(file_paths) > 1:
                    is_signed = True
                    my_zip.write(file_paths[1][0], file_paths[1][1])
                    my_zip.write(file_paths[2][0], file_paths[2][1])
                    os.remove(file_paths[1][0])
                    os.remove(file_paths[2][0])
        return path, name, is_signed

    def get_file(self, base_file):
        files = [(base_file.file.path, base_file.file.filename), ]
        sign = base_file.separatedsignature_set.filter(
            author=self.adapter.request.client
        ).first()
        if sign:
            name = base_file.file.filename + '.sig'
            protocol_name = base_file.file.filename + '.protocol.pdf'
            temp_protocol_path = self.generate_protocol_sign(base_file, sign)
            protocol_path = temp_protocol_path.split('.')[0] + '.pdf'
            pdfkit.from_file(temp_protocol_path, protocol_path)
            os.remove(temp_protocol_path)
            path = os.path.join(
                BASE_DIR, 'temp', name
            )
            with open(path, 'wb') as f:
                f.write(base64.b64decode(sign.sign))
            files.append((path, name))
            files.append((protocol_path, protocol_name))
        return files

    def upload_document(self, file_path, doc_id, doc_type, guarantee_id,
                        sign=False, file_name=None):
        url = r'/api_v1/document/upload/%s' % guarantee_id
        response = self.send_file(
            url,
            file=open(file_path, 'rb'),
            data={
                'user_hash': self.get_user_hash(),
                'document_id': doc_id,
                'document_type': doc_type,
                'document_status': 'signed' if sign else 'pending',
                'document_name': file_name
            },
        )
        self.print_log(response)
        return response

    def upload_all_document(self):
        doc_list = self.get_document_list()

        for file in filter(lambda x: x['status'], doc_list):
            self.delete_document(file['document_id'])

        for doc in doc_list:
            path, name, is_signed = self.get_file_for_upload(doc)
            if path is None:
                continue
            self.print_log(os.path.exists(path))
            try:
                self.upload_document(
                    path, doc['id'], doc['type'],
                    self.adapter.external_request.external_id, sign=is_signed,
                    file_name=name
                )
            except json.decoder.JSONDecodeError:
                pass
            os.remove(path)
            self.print_log(path)

    def delete_document(self, request_document_id):
        url = r'/api_v1/document/delete/%s' % request_document_id
        data = {
            'user_hash': self.adapter.external_request.get_other_data_for_key('user_hash')
        }
        response = self.send_data(url, data=data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False

        return response

    def jump_status(self, status_id):
        external_id = self.adapter.external_request.external_id
        url = r'/api_v1/guarantee/status/update/%s' % external_id
        data = {
            'user_hash': self.get_user_hash(),
            'new_status_id': status_id,
        }
        response = self.send_data(url, data)
        return response

    def get_all_status(self):
        url = r'/api_v1/guarantee/status/GetAll/'
        return self.get_data(url)['data']

    def get_status(self):
        url = r'/api_v1/guarantee/status/get/%s/%s' % (
            self.get_user_hash(),
            self.adapter.external_request.external_id,
        )
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['data']

    def set_status(self, string_status):
        list_status = self.get_all_status()
        need_status = list(filter(
            lambda x: x['description'] == string_status,
            list_status
        ))[0]
        return self.jump_status(need_status['id'])

    def upload_document_from_bank(self):
        url = r'/api_v1/document/listLayout/%s/%s' % (
            self.get_user_hash(),
            self.adapter.external_request.external_id
        )
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['documents']

    def download_document(self, doc_id, doc_type):
        url = r'/api_v1/document/download/%s/%s/%s/%s' % (
            self.get_user_hash(),
            self.adapter.external_request.external_id,
            doc_id,
            doc_type
        )
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['documents']

    def get_posts(self):
        url = r'/api_v1/guarantee/common/GetPosts/%s/%s' % (
            self.get_user_hash(),
            self.adapter.external_request.external_id
        )
        response = self.get_data(url)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response['data']

    @staticmethod
    def update_datetime_messages(messages):
        for message in messages:
            message['created'] = datetime.strptime(
                message['created'], '%Y-%m-%d %H:%M:%S'
            )
        return messages

    def get_last_post(self):
        messages = self.get_posts()
        if len(messages) > 0:
            last_message = messages[-1]
            return last_message

    def push_post(self, message, is_agent=False):
        external_id = self.adapter.external_request.external_id
        url = r'/api_v1/guarantee/common/WritePost/%s' % external_id
        response = self.send_data(url, data={
            'user_hash': self.get_user_hash(),
            'messages': message,
            "is_agent": int(is_agent)
        })
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def add_document(self, name) -> dict:
        external_id = self.adapter.external_request.external_id
        url = r'/api_v1/document/AddDocumentClient/%s' % external_id
        data = {
            'user_hash': self.get_user_hash(),
            'text': name,
        }
        response = self.send_data(url, data)
        if self.check_response2(response):
            if self.write_to_log:
                pass
            return False
        return response

    def get_dict_documents_from_client(self, request):
        documents_from_client = self.adapter.external_request.get_other_data_for_key(
            'documents_from_client'
        )
        if isinstance(documents_from_client, list):
            documents_from_client = self.list_to_dict_doc_from_client(
                self.adapter.request
            )
        if documents_from_client is None:
            documents_from_client = {}
        return documents_from_client

    def upload_free_document(self, name, file_id):
        documents_from_client = self.get_dict_documents_from_client(self.adapter.request)
        add_document = documents_from_client.get(str(file_id))
        if add_document is None:
            add_document = self.add_document(name)['document_id']
            documents_from_client.update({str(file_id): add_document})
            self.adapter.external_request.set_other_data_for_key(
                'documents_from_client', documents_from_client
            )

        if add_document:
            # заносим в список документов от клиента
            sign = False
            base_file = BaseFile.objects.get(id=file_id)
            files = self.get_file(base_file)
            if len(files) > 1:
                sign = True
                path = get_temp_path('.zip')
                with zipfile.ZipFile(path, 'w') as my_zip:
                    my_zip.write(files[0][0], files[0][1])
                    my_zip.write(files[1][0], files[1][1])
                    my_zip.write(files[2][0], files[2][1])
                    os.remove(files[1][0])
                    os.remove(files[2][0])
            else:
                path = files[0][0]
            self.upload_document(
                path,
                add_document,
                'additional',
                self.adapter.external_request.external_id,
                sign,
                base_file.file.filename
            )
            if len(files) > 1:
                os.remove(path)
            return True
        return False

    def list_to_dict_doc_from_client(self, request):
        documents_from_client = self.adapter.external_request.get_other_data_for_key(
            'documents_from_client'
        )
        if isinstance(documents_from_client, list):
            discuss = get_discuss(request)
            files = list(MessageFile.objects.filter(
                message__in=discuss.messages.filter(
                    author__roles__name__in=[Role.AGENT, Role.CLIENT]
                )
            ).order_by('id').values_list('file_id', flat=True))
            result = {key: val for key, val in zip(files, documents_from_client)}
            self.adapter.external_request.set_other_data_for_key(
                'documents_from_client', result
            )
            return result
        return documents_from_client

    @staticmethod
    def generate_protocol_sign(file, separated_sign):
        template = r'print_forms_templates/html/protocol_sign.html'
        context = {
            'file': file,
            'separated_sign': separated_sign,
            'date_now': timezone.now(),
        }
        adapter = HTMLGenerator(template, context)
        for path in adapter.generate():
            return path
