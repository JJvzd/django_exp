import json
import logging
import os

import requests

from bank_guarantee.bank_integrations.spb_bank.data_translators.offer_ready import \
    OfferReadyDataTranslator
from bank_guarantee.models import Request
from bank_guarantee.bank_integrations.spb_bank.client_rating_calculator import (
    ClientRatingTranslator
)
from bank_guarantee.bank_integrations.spb_bank.helpers import (
    get_client_rating_calculator, SPBContractsInfo
)
from utils.curl import request_as_curl
from utils.helpers import (
    convert_date, generate_log_tags
)

logger = logging.getLogger('django')


class SPBApi:
    url = os.getenv('TH_SPB_STUNNEL_OUT')

    def get_url(self, path):
        return '%s%s' % (self.url, path)

    def get_request_data(self, request) -> dict:
        contracts_info = SPBContractsInfo(request=request)
        data = get_client_rating_calculator(
            request=request,
        )
        raiting = ClientRatingTranslator.translate(data.calculated_score)
        persons = []
        for person in request.client.profile.profilepartnerindividual_set.all():
            if request.client.is_individual_entrepreneur:
                person_type = 'entrepreneur'
            else:
                if person.is_general_director:
                    person_type = 'employee'
                else:
                    person_type = 'personFounder'
            persons.append({
                'type': person_type,
                'displayName': person.get_name,
                'lastName': person.last_name,
                'firstName': person.first_name,
                'secondName': person.middle_name,

                'birthDate': convert_date(
                    person.passport.date_of_birth),
                'inn': person.fiz_inn,
                'identityDocument': {
                    'identityDocumentTypeRefId': 'passportRF',
                    'issuedDate': convert_date(
                        person.passport.when_issued),
                    'issuingAuthority': person.passport.issued_by,
                    'subCode': person.passport.issued_code,
                    'number': person.passport.number,
                    'series': person.passport.series,
                }
            })

        count_similar_contracts = len(contracts_info.finished_last_3_year_contracts) or 1

        data = {
            'orderNumber': request.request_number_in_bank,
            'amount': float(request.required_amount),
            'durationDays': request.interval,
            'agentId': 'TH',
            'beneficiary': {
                'inn': request.tender.beneficiary_inn,
                'ogrn': request.tender.beneficiary_ogrn,
                'kpp': request.tender.beneficiary_kpp,
                'okpo': '',
                'fullName': request.tender.beneficiary_name,
                'displayName': request.tender.beneficiary_name,
            },
            'principalCompany': {
                'inn': request.client.profile.reg_inn,
                'ogrnip': request.client.profile.reg_ogrn,
                'ogrn': request.client.profile.reg_ogrn,
                'kpp': request.client.profile.reg_kpp,
                'okpo': request.client.profile.reg_okpo,
                'fullName': request.client.profile.full_name,
                'displayName': request.client.profile.short_name,
                'finStateValue': raiting.finance_state.lower().capitalize(),
                'persons': persons,
            },
            'purchaseNumber': request.tender.notification_id,
            'numberOfSimilarContracts': count_similar_contracts,
            'ourSale': False,
        }
        return data

    def get_request(self, request_id) -> dict:
        response = requests.get(self.get_url('/order/%s' % request_id)).json()
        return response

    def offer_ready_data(self, request: Request) -> dict:
        return OfferReadyDataTranslator().get_data(request)

    def send_offer_ready(self, request: Request, request_id) -> bool:
        if request.has_offer():
            data = self.offer_ready_data(request)
            logger.info("Отправленные данные в СПб %s %s" % (
                self.clear_offer_ready_data_for_log(data),
                generate_log_tags(request=request))
                        )
            response = requests.post(self.get_url(
                '/counterparty/order/%s/message/contractReady' % request_id),
                json=data)

            result = False
            if response.status_code == 200:
                result = True

            try:
                response = response.json()
                logger.info("Полученные данные из СПб %s %s" % (
                    response, generate_log_tags(request=request)))
            except Exception as e:
                logger.info("Полученны не JSON данные из СПб %s %s" % (
                    response.content, generate_log_tags(request=request))
                            )

            return result
        return False

    def send_request(self, request):
        data = self.get_request_data(request)
        logger.info("Отправленные данные в СПб %s %s" % (
            self.clear_offer_ready_data_for_log(data),
            generate_log_tags(request=request))
                    )
        response = requests.post(
            self.get_url('/counterparty/order/'),
            json=data
        )
        logger.info(request_as_curl(response.request))
        response = response.json()
        logger.info("Полученные данные из СПб %s %s" % (
            response, generate_log_tags(request=request)))
        from base_request.logic.request_log import RequestLogger
        RequestLogger.log(request, json.dumps(response))
        id = response.get('id')
        return id

    def clear_offer_ready_data_for_log(self, data):
        output_data = data.copy()
        output_data['contractDocBase64'] = '...base64_content...'
        return output_data

    def request_reject(self, request: Request, request_id, reason: str = None):
        data = {
            'lostReason': reason,
        }
        logger.info("Отправленные данные в СПб %s => %s %s" % (
            request_id, data, generate_log_tags(request=request)))
        logger.info(
            self.get_url('/counterparty/order/%s/message/cancel' % request_id)
        )
        response = requests.post(
            self.get_url('/counterparty/order/%s/message/cancel' % request_id),
            json=data
        )

        result = False
        if response.status_code == 200:
            result = True

        logger.info("Полученны не JSON данные из СПб %s %s" % (
            response.content, generate_log_tags(request=request)))

        return result
