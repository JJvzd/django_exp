import copy
import os
from decimal import Decimal
from json import JSONDecodeError

import ujson
from django.conf import settings
from django.core.files import File
from django.db.models import Q
from django.utils.functional import cached_property

from bank_guarantee.bank_integrations.api.base import BaseSendRequest, push_error
from bank_guarantee.models import RequestPrintForm, ExternalRequest, RequestedCategory, \
    OfferDocument
from base_request.helpers import BeforeSendToBankResult
from base_request.logic.request_log import RequestLogger
from cabinet.base_logic.printing_forms.generate import RequestPrintFormGenerator
from common.helpers import generate_password
from files.models import BaseFile
from users.models import Role
from utils.helpers import requests_retry_session, download_file


class FarzoomSendRequest(BaseSendRequest):
    production_endpoint = ''
    write_to_log = True
    default_date_format = '%Y-%m-%d'
    key_clients_doc_type = 'clients_doc_type'
    requested_doc_key = 'requested_docs'
    print_form_type = None
    print_form_zip_type = None

    def __init__(self):
        self.enabled = self.bank.settings.send_via_integration

    def is_test(self):
        return settings.DEBUG

    def get_bank_endpoint(self):
        return self.production_endpoint

    def get_headers(self):
        return {}

    def send_data_in_bank(self, url, data, method='POST', as_params=False):
        client = requests_retry_session()

        data_key = 'params' if as_params else 'json'
        kwargs = {
            'method': method,
            'url': self.get_bank_endpoint() + url,
            'headers': self.get_headers(),
            data_key: data
        }
        response = client.request(**kwargs)
        try:
            result = response.json()
        except JSONDecodeError:
            result = {'status': response.status_code,
                      'content': response.content.decode('utf8')}
        return result

    def clear_output_data_for_log(self, data):
        output_data = copy.deepcopy(data)
        if 'documents' in output_data.keys():
            filtered_documents = []
            for document in output_data['documents']:
                filtered_files = []
                for file in document.get('files', []):
                    file['value'] = '...'
                    filtered_files.append(file)
                document['files'] = filtered_files
                filtered_documents.append(document)
            output_data['documents'] = filtered_documents
        return output_data

    def get_data_from_bank(self, url, params=None):
        client = requests_retry_session()
        url = self.get_bank_endpoint() + url
        if not params:
            params = {}
        kwargs = {
            'headers': self.get_headers(),
            'verify': False,
        }
        response = client.get(url=url, params=params, **kwargs).json()
        return response

    def get_need_status(self, external_request):
        data = external_request.get_other_data_for_key(self.key_status_response)
        return data or {}

    def get_need_doc_list(self, external_request):
        data = self.get_need_status(external_request)
        docs = data.get('documents')
        if docs:
            return list(map(lambda x: x['type'], docs))

    def get_zip_client_docs(self, request, doc_type):
        print_form, created = RequestPrintForm.objects.get_or_create(
            filename=doc_type,
            type=self.print_form_zip_type,
            name=self.get_info_doc(doc_type).get('docName'),
            active=False,
        )
        if created:
            print_form.roles = [
                Role.CLIENT,
                Role.AGENT,
                Role.GENERAL_AGENT,
                Role.SUPER_AGENT,
                Role.MANAGER
            ]
            print_form.save()
        doc = request.requestdocument_set.filter(
            print_form=print_form
        ).first()
        if doc is None:
            generator = RequestPrintFormGenerator()
            doc = generator.generate_print_form(request, print_form)
        return doc.file_id

    @property
    def documents_map(self):
        return {}

    def get_info_doc(self, doc_type):
        return self.docs_info.get(doc_type) or {}

    def pack_files(self, file_ids, signer=None):
        """

        :param doc:
        :param bank_guarantee.models.Request request:
        :param document_ids:
        """
        data = []
        files = BaseFile.objects.filter(id__in=file_ids)
        for file in files:
            file_name = file.get_download_name()
            sign = None
            if signer:
                sign = file.sign_set.filter(author__client=signer).first()
            if sign:
                file = sign.signed_file
            else:
                file = file.file
            try:
                data.append({
                    'fileName': file_name,
                    'mimeType': file.mimetype,
                    'value': file.get_base64(),
                })
            except Exception as e:
                raise e
        return data

    def get_client_docs(self, request, need_documents=None):
        documents = []
        for type, docs in self.documents_map.items():
            if need_documents and type not in need_documents:
                continue
            files_ids = request.requestdocument_set.filter(
                category_id__in=docs
            ).values_list(
                'file',
                flat=True
            )
            if len(files_ids):
                if (len(files_ids) > 1) and (
                    not self.get_info_doc(type).get('isMultiple')):
                    files_ids = [self.get_zip_client_docs(request, type)]
                documents.append({
                    'type': type,
                    'files': self.pack_files(
                        files_ids,
                        request.client
                    )
                })

        if request.client.is_organization:
            files_ids = request.requestdocument_set.filter(
                category_id=2
            ).values_list(
                'file',
                flat=True
            )
            if (len(files_ids) > 1) and (not self.get_info_doc(
                'doc_principalCharter'
            ).get('isMultiple')):
                files_ids = [self.get_zip_client_docs(request, 'doc_principalCharter')]
            documents.append({
                'type': 'doc_principalCharter',
                'files': self.pack_files(
                    files_ids,
                    request.client
                )
            })
        external_request = self.get_external_request(request)
        external_request.set_other_data_for_key(
            self.key_clients_doc_type,
            list(
                set(
                    list(
                        map(
                            lambda x: x['type'],
                            documents
                        )
                    ) + (external_request.get_other_data_for_key(
                        self.key_clients_doc_type) or [])
                )
            )
        )
        return documents

    def get_additional_files(self, request):
        files = BaseFile.objects.filter(
            Q(messagefile__message__discuss__request=request) & (
                Q(messagefile__message__author__in=request.client.user_set.all()) |
                Q(messagefile__message__author__in=request.agent.user_set.all())
            )
        )
        if files.count():
            return [{
                'type': 'doc_otherOrder',
                'files': self.pack_files(
                    files.values_list('id', flat=True),
                    request.client
                )
            }]
        return []

    def get_current_documents(self, external_request):
        result = self.get_need_status(external_request)
        return result.get('documents') or []

    def get_file_from_bank(self, order_id, file_id, file_name):
        saved_filename = generate_password() + file_name
        url = self.get_bank_endpoint() + '/order/' + order_id + '/file/' + file_id
        downloaded_filepath = download_file(url=url, target_name=saved_filename,
                                            headers=self.get_headers())
        return downloaded_filepath

    def get_file_for_type(self, request, type_doc):
        external_request = self.get_external_request(request)
        docs = self.get_current_documents(external_request)
        doc = None
        try:
            doc = next(filter(lambda x: x['type'] == type_doc, docs))
        except StopIteration:
            pass
        if doc is None:
            return None
        doc = doc['files'][0]
        external_request = self.get_external_request(request)
        return self.get_file_from_bank(external_request.external_id, doc['fileId'],
                                       doc['fileName'])

    def get_print_forms(self, request, need_documents=None):
        documents = []
        print_forms = RequestPrintForm.objects.filter(
            type=self.print_form_type
        )
        if need_documents:
            print_forms = print_forms.filter(filename__in=need_documents)
        for print_form in print_forms:
            documents.append({
                'type': print_form.filename,
                'files': self.pack_files(
                    request.requestdocument_set.filter(print_form=print_form).values_list(
                        'file', flat=True),
                    request.client
                )
            })
        return documents

    def get_offer_docs(self, request):
        documents = []
        for type, val in self.offer_map.items():
            offer_doc = request.offer.offerdocument_set.filter(category=val).first()
            if offer_doc:
                documents.append({
                    'type': type,
                    'files': self.pack_files([offer_doc.file.id], request.client)
                })
        return documents

    @staticmethod
    def clear_docs(docs):
        return list(filter(lambda x: len(x['files']) != 0, docs))

    @staticmethod
    def convert_float(value):
        if isinstance(value, str):
            value = value.strip()
        if not value:
            value = 0
        return float(value) or 0

    @property
    def offer_map(self):
        return {}

    def get_print_forms_for_generate(self, data, external_request):
        exclude = (list(self.offer_map.keys()) +
                   (external_request.get_other_data_for_key(
                       self.key_clients_doc_type) or []) +
                   list(map(lambda x: x['type'],
                            external_request.get_other_data_for_key(
                                self.requested_doc_key) or [])))
        return list(filter(
            lambda x: ((x['type'] not in exclude) and
                       (len(x.get('files', [])) > 0) and
                       all(map(lambda x2: x2['fileId'], x['files']))),
            data.get('documents', [])
        ))

    def get_doc_name(self, doc):
        return self.docs_info.get(doc['type'])['docName']

    def generate_print_forms(self, data, external_request):
        external_request.refresh_from_db()
        generator = RequestPrintFormGenerator()
        for doc in self.get_print_forms_for_generate(data, external_request):
            print_form, created = RequestPrintForm.objects.get_or_create(
                filename=doc['type'],
                type=self.print_form_type,
                active=False,
                name=self.get_doc_name(doc)
            )
            if created:
                print_form.roles = [
                    Role.CLIENT,
                    Role.AGENT,
                    Role.GENERAL_AGENT,
                    Role.SUPER_AGENT,
                    Role.MANAGER
                ]
                print_form.save()
            if not external_request.request.requestdocument_set.filter(
                print_form__type=self.print_form_type,
                print_form__filename=doc['type']
            ).exists():
                new_doc = generator.generate_print_form(external_request.request,
                                                        print_form)
                file = new_doc.file
                file.download_name = doc['files'][0]['fileName']
                file.save()
                external_request.request.update_signed(
                    external_request.request.client.user_set.first()
                )

    def send_request(self, request):
        if self.enabled:
            return super().send_request(request)
        else:
            return BeforeSendToBankResult(result=True)

    def create_request(self, request):
        data_for_send = self.get_data_for_send(request)
        data_for_send = self.clear_data(data_for_send)
        response = self.send_data_in_bank('/order', data_for_send)
        RequestLogger.log(request,
                          'Создание заявки в %s: %s' % (self.bank_code, ujson.dumps(
                              self.clear_output_data_for_log(data_for_send)
                          )))
        RequestLogger.log(
            request,
            'Ответ из банка %s: %s' % (self.bank_code, ujson.dumps(response)))
        external_id = response.get('orderId')
        if external_id:
            ExternalRequest.save_record(
                request=request,
                bank=self.bank,
                external_id=external_id,
                status=None,
                other_data={}
            )
            return BeforeSendToBankResult(result=True)
        else:
            RequestLogger.log(request, 'Банк %s отклонил заявку, ответ %s' % (
                self.bank_code, response))
            return BeforeSendToBankResult(result=False, reason='Банк отклонил заявку')

    def clear_data(self, data):
        if isinstance(data, list):
            keys = list(range(len(data)))
        elif isinstance(data, dict):
            keys = list(data)
        elif isinstance(data, Decimal):
            return float(data)
        else:
            return data
        if len(keys) == 0:
            return self.null
        del_keys = []
        for key in keys:
            temp = self.clear_data(data[key])
            if isinstance(temp, type(self.null)) and (self.null == temp):
                del_keys.append(key)
            else:
                data[key] = temp
        if len(del_keys) == len(keys):
            return self.null
        for key in del_keys:
            del data[key]
        return data

    def get_data_for_send(self, request):
        return {}

    def push_message(self, request, message):
        discuss = request.discusses.filter(
            bank=request.bank,
            agent=request.agent
        ).first()
        user = self.bank.get_first_user()
        if discuss and discuss.can_write(user):
            discuss.add_message(
                author=user,
                message=message
            )

    @staticmethod
    def get_base_file(temp_path, name, author):
        base_file = BaseFile.objects.create(
            download_name=name,
            author=author
        )
        with open(temp_path, 'rb') as f:
            base_file.file.save(name, File(f))
        os.unlink(temp_path)
        return base_file

    def get_offer_docs_for_generate(self, data):
        files = {}
        only = list(self.offer_map.keys())
        for document in data.get('documents', []):
            type = document['type']
            if type not in only:
                continue
            files[type] = []
            for file_data in document.get('files') or []:
                file_id = file_data['fileId']
                file_path = self.get_file_from_bank(data.get('orderId'), file_id,
                                                    file_data['fileName'])
                if file_path:
                    files[type].append(
                        self.get_base_file(file_path, file_data['fileName'], self.bank).id
                    )
        return files

    def get_request_status_data(self, external_request):
        return self.get_data_from_bank('/order/' + external_request.external_id)

    @push_error(return_value=None)
    def get_current_status(self, request):
        external_request = self.get_external_request(request)
        if self.bank.settings.update_via_integration and external_request:
            response = self.get_request_status_data(external_request)
            RequestLogger.log(request, 'Ответ из банка %s: %s' % (
                self.bank_code, ujson.dumps(response)))
            self.update_status(external_request, data=response)
            return response
        return None

    def create_offer_doc(self, external_request, offer_files):
        external_request.refresh_from_db()
        offer = external_request.request.offer
        for type, category_id in self.offer_map.items():
            if type in offer_files.keys() and offer_files[type]:
                offer.offerdocument_set.filter(category_id=category_id).delete()
                for file_id in offer_files[type]:
                    OfferDocument.objects.create(
                        category_id=category_id,
                        file_id=file_id,
                        offer_id=offer.id
                    )

    def get_errors(self, request, data):
        requirements = data.get('requirements', {})
        external_request = self.get_external_request(request)
        requested_docs = external_request.get_other_data_for_key(
            self.requested_doc_key) or []
        not_need = list(map(lambda x: x.get('type'), requested_docs)) + list(
            self.documents_map.keys())
        errors = []
        for key, val_list in requirements.items():
            if isinstance(val_list, list):
                for val in val_list:
                    if key == 'documents' and val.get('type') not in not_need:
                        requested_docs.append(val)
                        RequestedCategory.objects.create(
                            request=request,
                            name=val.get('title')
                        )
                    errors.append(
                        '%s: %s' % (val.get('title'), val.get('error'))
                    )
        external_request.set_other_data_for_key(self.requested_doc_key, requested_docs)
        return errors

    def get_external_request(self, request):
        result, created = ExternalRequest.objects.get_or_create(request=request,
                                                                bank=self.bank)
        return result

    def change_request(self, request, external_request):
        data = self.clear_data(self.get_data_for_send(request))
        RequestLogger.log(request, self.clear_output_data_for_log(data))
        self.send_data_in_bank('/order/' + external_request.external_id,
                               data,
                               method='PUT')
        return BeforeSendToBankResult(result=True)

    def get_documents_type(self):
        response = self.get_data_from_bank('/doc/types', params=dict())
        return response

    def get_documents(self, request):
        documents = []
        documents += self.get_client_docs(request)
        documents += self.get_additional_files(request)
        documents += self.get_print_forms(request)

        if request.has_offer():
            try:
                documents += self.get_offer_docs(request)
            except Exception as error:
                pass
        return self.clear_docs(documents)

    @property
    def all_documents_map(self):
        temp = self.documents_map
        temp['doc_principalCharter'] = [2]
        return temp

    @push_error()
    def reject_request(self, request):
        external_request = self.get_external_request(request)
        if external_request.status not in ['RejectedByBank', 'InProcess']:
            self.send_data_in_bank(
                '/order/' + external_request.external_id,
                {
                    "decision": {
                        "resultCode": "REJECT",
                        'comment': 'Отказ от заявки'
                    }
                },
                method='PUT'
            )

    @cached_property
    def docs_info(self):
        return self.get_documents_type()
