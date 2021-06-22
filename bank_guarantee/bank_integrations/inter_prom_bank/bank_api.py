import json
import logging
import os

import requests
from django.conf import settings

from bank_guarantee.models import Request, ExternalRequest, RequestDocument
from base_request.discuss_logic import get_discuss
from base_request.helpers import BeforeSendToBankResult
from base_request.models import BankDocumentType
from bank_guarantee.bank_integrations.api.base import BaseSendRequest
from cabinet.constants.constants import Target, FederalLaw
from settings.configs.banks import BankCode
from settings.configs.interprom_documents import INTERPROM_DOCUMENTS
from settings.settings import CONTACTS
from utils.functions_for_tests import random_string

logger = logging.getLogger('django')


class SendRequest(BaseSendRequest):
    bank_code = BankCode.CODE_INTER_PROM_BANK

    def __init__(self, *args, **kwargs):
        self.login = os.getenv('TH_INTERPROM_LOGIN')
        self.password = os.getenv('TH_INTERPROM_PASSWORD')
        self.production_endpoint = os.getenv('TH_INTERPROM_ENDPOINT')
        super(SendRequest, self).__init__(*args, **kwargs)

    def get_headers(self):
        return {}

    def send_data_in_bank(self, url, params, request_type='POST'):
        url = self.production_endpoint + url
        request_kwargs = {
            'headers': self.get_headers(),
            'params' if request_type == 'GET' else 'data': params
        }
        response = requests.request(
            method=request_type, url=url, verify=False, **request_kwargs
        ).json()
        logger.info("Отправленные данные %s в %s" % (json.dumps(params), self.bank_code))
        logger.info("Полученные данные %s из %s" % (json.dumps(response), self.bank_code))
        return response

    def get_bank_endpoint(self):
        return self.production_endpoint

    def integration_enable(self):
        return self.bank.settings.send_via_integration

    def auth(self):
        response = self.send_data_in_bank(url="login", params={
            'login': self.login,
            'password': self.password,
            'action': 'api_authorization',
        }, request_type='POST')
        return response.get('hash_id')

    def send_file_in_bank(self, url, data, file):
        if not file['path']:
            return False

        response = requests.post(
            url=self.production_endpoint + url, data=data, verify=False,
            files={
                file['name']: open(file['path'], 'rb')
            }
        ).json()
        return response

    def order_attach(self, hash_id, ref_id):
        data = {
            'ref_id': ref_id,
            'action': 'ORDER_ATTACH',
            'hash': hash_id,
        }
        response = self.send_data_in_bank(url='Action', params=data, request_type='POST')
        logger.info("Отправленные данные %s в %s" % (json.dumps(data), self.bank_code))
        logger.info("Полученные данные %s из %s" % (json.dumps(response), self.bank_code))
        return response

    def get_bank_guarantee_type(self, request):
        if Target.PARTICIPANT in request.targets:
            return 'PART'
        if Target.EXECUTION in request.targets:
            return 'EXEC'
        return None

    def return_error_result(self, request, reason):
        discuss = get_discuss(request=request)
        discuss.add_message(author=self.bank.user_set.first(),
                            message="Причина отказа: %s" % reason)
        return BeforeSendToBankResult(reason=reason, result=False)

    def create_request(self, request: Request):
        hash_id = self.auth()
        if hash_id:
            code = self.get_bank_guarantee_type(request)
            if not code:
                return self.return_error_result(request, "Не допустимое назначение БГ")

            federal_law = {
                FederalLaw.LAW_44: '44',
                FederalLaw.LAW_223: '223',
                FederalLaw.LAW_185: '185',
                FederalLaw.LAW_615: '185'
            }.get(request.tender.federal_law, None)
            if not federal_law:
                return self.return_error_result(request, reason='Недопустимый закон')

            profile = request.client.profile

            last_quarter = request.client.accounting_report.get_last_closed_quarter()
            year_quarter = request.client.accounting_report.get_year_quarter()

            data = {
                'hash_id': hash_id,
                'inn': profile.reg_inn,
                'purchase_number': request.tender.notification_id,
                'guarantee_sum': float(request.required_amount),
                'contract_sum': float(request.suggested_price_amount),
                'date_guarantee_begin': request.interval_from.strftime('%Y-%m-%d'),
                'date_guarantee_end': request.interval_to.strftime('%Y-%m-%d'),
                'code': code,
                'fz': federal_law,
                'external_number': request.get_number(),
                'valn_1410': float(last_quarter.get_value(1410)),
                'valn_1510': float(last_quarter.get_value(1510)),
                'valq_2110': float(last_quarter.get_value(2110)),
                'valy_2110': float(year_quarter.get_value(2110)),
                'valn_2110P': 0,
                'valy_1500': float(year_quarter.get_value(1500)),
                'valy_1200': float(year_quarter.get_value(1200)),
                'valq_1500': float(last_quarter.get_value(1500)),
                'valq_1200': float(last_quarter.get_value(1200)),
                'lossy_2400': float(year_quarter.get_value(2400)),
                'lossy_1300': float(year_quarter.get_value(1300)),
                'lossq_2400': float(last_quarter.get_value(2400)),
                'lossq_1300': float(last_quarter.get_value(1300)),

            }
            response = self.send_data_in_bank('CreateOrder', data, 'POST')
            request.logs.create(message='Отправлено %s' % json.dumps(data))
            request.logs.create(message='Получено %s' % json.dumps(response))
            error = response.get('error_descr')
            short_answer = response.get('short_answer')

            if "К сожалению, мы не нашли указанную закупку." in error:
                if self.send_tender_data(hash_id, request):
                    return self.send_request(request)
                return self.return_error_result(
                    request=request,
                    reason="К сожалению, не удалось отправить заявку. "
                           "Обратитесь в техническую поддержку %s тел %s доб.6204" % (
                               CONTACTS['MAIN_OFFICE']['EMAIL_TECHNICAL_SUPPORT'],
                               CONTACTS['MAIN_OFFICE']['MAIN_PHONE'],
                           )
                )
            if response.get('result_code') == 'rejected':
                return self.return_error_result(request=request, reason=short_answer)

            if 'Указанная заявка (ИНН и номер закупки) уже зарегистрирована' in error:
                return self.return_error_result(
                    request=request,
                    reason='Указанная заявка (ИНН и номер закупки) уже зарегистрирована'
                )

            success_messages = [
                'Ваша заявка предварительно одобрена!',
                'Ваша заявка одобрена!'
            ]
            if (short_answer in success_messages) or response.get('success', False):
                ref_id = response.get('ref_id')
                ext_link = response.get('ext_link')
                external_request = ExternalRequest.save_record(
                    request=request, bank=self.bank, external_id=ref_id, status=1,
                    other_data={
                        'link': ext_link
                    })

                self.order_attach(hash_id, ref_id=ref_id)

                interprom_documents = INTERPROM_DOCUMENTS
                response = self.send_data_in_bank(
                    request_type='GET',
                    url='Get_fileslist',
                    params={
                        'hash_id': hash_id,
                        'ref_id': ref_id,
                    })
                logger.info(
                    "Документы, необходимые для заявки %s: %s" % (ref_id, response))
                ref_link_for_sign = self.send_data_in_bank(
                    url='Action',
                    params={
                        'hash_id': hash_id,
                        'ref_id': ref_id,
                        'action': 'GET_EXT_LINK',

                    }
                )
                discuss = get_discuss(request)
                message = "Добрый день!\nДля закрепления заявки за данным агентом, " \
                          "необходимо подписать документы по ссылке:\n " \
                          "%s" % ref_link_for_sign['msg']
                discuss.add_message(author=self.bank.user_set.first(), message=message)

                external_request_data = {
                    'files': []
                }
                for file in response.get('fileList', []):
                    file_type_id = file['fileTypeId']  # id документа в Интерпроме
                    direction_id = file['directionId']
                    file_status_id = file['fileStatusId']  # 4 - загрузить 5 - загружен
                    sign_status_id = file['signStatusId']  # 30 - подписать 40 - подписан
                    file_id = file['fileId']

                    if direction_id == 4:
                        if file_status_id == 4:
                            category_id = interprom_documents[file_type_id]['category_id']
                            document_category = BankDocumentType.objects.get(
                                id=category_id)
                            doc: RequestDocument = request.requestdocument_set.filter(
                                category=document_category).first()
                            if doc:
                                doc_full_name = doc.file.file.path
                                doc_name = doc.file.file.file_name
                                self.send_file_in_bank('fileUpload', data={
                                    'hash_id': hash_id,
                                    'ref_id': ref_id,
                                    'file_id': file_id,
                                }, file={
                                    'name': 'document',
                                    'path': doc_full_name,
                                    'filename': doc_name,
                                })

                                if sign_status_id == 30:
                                    separated_sign = doc.file.separatedsignature_set.filter(  # noqa
                                        author=request.client).first()
                                    if separated_sign:
                                        sig_file_name = os.path.join(
                                            settings.TEMP_DIR,
                                            '%s.sig' % random_string(10)
                                        )
                                        with open(sig_file_name, 'w') as f:
                                            f.write(separated_sign.sign)
                                        self.send_file_in_bank(
                                            'fileUpload', data={
                                                'hash_id': hash_id,
                                                'ref_id': ref_id,
                                                'file_id': file_id,
                                            },
                                            file={
                                                'name': 'signature',
                                                'path': sig_file_name,
                                                'filename': os.path.basename(
                                                    sig_file_name),
                                            }
                                        )
                                        os.unlink(sig_file_name)
                        else:
                            external_request_data['files'].append(file)
                    else:
                        external_request_data['files'].append(file)
                external_request_data.update(json.loads(external_request.other_data))
                external_request.other_data = external_request_data
                external_request.save()

                return BeforeSendToBankResult(result=True)
            return self.return_error_result(request=request, reason=error)
        return self.return_error_result(
            request=request, reason="Неудачная отправка заявки"
        )

    def get_data_for_send(self, request):
        return {}

    def get_data_from_bank(self, url, params):
        pass

    def send_tender_data(self, hash_id, request: Request):
        response = self.send_data_in_bank(
            'buying_post',
            params={
                'hash_id': hash_id,
                'beneficiar_inn': request.tender.beneficiary_inn,
                'beneficiar_name': request.tender.beneficiary_name,
                'buying_id': request.tender.notification_id,
                'buying_name': request.tender.subject,
                'buying_reference': request.tender.tender_url,
                'contract_start_price': request.tender.price,
                'okpd2': request.tender.okpd2
            }
        )
        return response.get('success', False)

    def change_request(self, request, external_request):
        logger.error(
            'Не реализован метод для редактирования заявки в %s' % self.bank_code
        )
        return BeforeSendToBankResult(result=True)

    def client_cancel_request(self, external_request: ExternalRequest):
        hash_id = self.auth()
        if hash_id:
            response = self.send_data_in_bank('Action', {
                'hash_id': hash_id,
                'ref_id': external_request.external_id,
                'action': 'CLIENT_REFUSED'
            })
            result = response.get('ret')
            if not result:
                logger.debug("Результат отмены заявки %s: %s" % (
                    external_request.external_id, response.get('msg')))
            else:
                logger.debug("Заявка в %s %s отменена" % (
                    self.bank_code, external_request.external_id))
                external_request.status = 128
                external_request.save()
            return result
        return False

    def get_status_display(self, status_id):
        status_map = {
            1: "Новая",
            2: "Запрос",
            8: "Предварительная",
            16: "Ожидание аукциона",
            32: "В работе",
            64: "Отказ Банка",
            128: "Отказ Клиента",
            256: "Согласование проекта",
            512: "На выдачу",
            1024: "Выдана",
        }
        return status_map.get(int(status_id), '-')

    def get_sent_request(self):
        hash_id = self.auth()
        if hash_id:
            response = self.send_data_in_bank(
                url='order', request_type='GET',
                params={
                    'hash_id': hash_id
                }
            )
            return response['order_list']
        return None
