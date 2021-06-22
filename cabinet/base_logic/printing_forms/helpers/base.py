import json
from functools import reduce

from django.utils import timezone
from django.utils.functional import cached_property

from bank_guarantee.models import Offer
from base_request.models import AbstractRequest
from cabinet.base_logic.contracts.base import ContractsLogic
from cabinet.constants.constants import Target
from cabinet.models import EgrulData
from external_api.dadata_api import DaData
from utils.helpers import number2string


class BaseHelper:

    def get_profile(self, request):
        return request.client.profile

    def __init__(self, request: AbstractRequest, bank):
        self.request = request
        self.bank = bank
        self.profile = self.get_profile(request)
        self.client = request.client

    @cached_property
    def print_required_amount(self):
        return number2string(self.request.required_amount)

    def get_main_okved(self):
        okved = self.profile.kindofactivity_set.first()
        if okved:
            return okved.value.split(' ')[0]
        return ''

    @cached_property
    def get_bank_commission(self):
        if self.request.banks_commissions:
            banks_commissions = json.loads(self.request.banks_commissions)
            if banks_commissions:
                banks_commissions = banks_commissions.get(self.bank.code, {})
                if isinstance(banks_commissions, dict):
                    banks_commissions = banks_commissions.get('commission', 0)
                return round(float(banks_commissions), 2)
        return None

    def get_target_display(self):
        if Target.PARTICIPANT in self.request.targets:
            return 'тендер'
        if Target.EXECUTION in self.request.targets:
            return 'контракт'
        return ''

    def finished_guaranties(self):
        result = []
        total = 0
        now = timezone.now()
        offers = Offer.objects.filter(
            request__status__code='bg_to_client',
            request__bank=self.bank,
            request__client=self.request.client,
        ).exclude(
            request_id=self.request.id
        )
        for offer in offers:
            result.append({
                'cost': offer.amount,
                'from': offer.contract_date or offer.request.intreval_from,
                'to': offer.request.interval_to
            })
            if offer.request.interval_to > now.date():
                total += offer.amount
        return {
            'data': result,
            'total': total
        }

    @cached_property
    def get_all_sum_bgs(self):
        data = self.finished_guaranties()
        return data['total'] + self.request.required_amount

    @cached_property
    def finished_contracts(self):
        return ContractsLogic(self.client).get_finished_contracts()

    @cached_property
    def _finished_contracts(self):
        contracts = self.finished_contracts
        data = {}
        for contract in contracts:
            d = contract.get('start_date')
            data.setdefault(d, [])
            data[d].append(contract)

        data = [(k, data[k]) for k in sorted(data.keys())]
        result = []
        for year, d in data:
            result.append({
                'year': year,
                'count': len(d),
                'sum': reduce(lambda sum, el: sum + el.get('price'), d, 0)
            })
        return result

    def getAddressFromEGRUL(self):
        egrul_data = EgrulData.get_info(self.profile.reg_inn)
        if egrul_data:
            result = egrul_data.get(
                'section-ur-adress', {}
            ).get('full_address', '') or self.profile.legal_address
        else:
            result = self.profile.legal_address
        if self.client.is_individual_entrepreneur:
            return self.format_address(result)
        return result

    def getLegalAddress(self):
        result = self.getAddressFromEGRUL()
        if self.profile.legal_address_status:
            return result
        return '%s c %s по %s' % (
            result,
            self.profile.legal_address_from.strftime('%d.%m.%Y'),
            self.profile.legal_address_to.strftime('%d.%m.%Y')
        )

    def format_address(self, address):
        api = DaData()
        result = api.clean_address(address)
        return '%s, %s' % (result[0]['postal_code'], result[0]['result'])

    def getFactAddress(self):
        if self.profile.fact_is_legal_address:
            return self.getLegalAddress()
        result = self.profile.fact_address
        if self.client.is_individual_entrepreneur:
            result = self.format_address(result)
        if self.profile.fact_address_status:
            return result
        return '%s c %s по %s' % (
            result,
            self.profile.fact_address_from.strftime('%d.%m.%Y'),
            self.profile.fact_address_to.strftime('%d.%m.%Y')
        )

    def get_company_full_name(self):
        egrul_data = EgrulData.get_info(self.profile.reg_inn)
        if egrul_data:
            result = egrul_data.get(
                'section-ur-lico', {}
            ).get('full-name-ur-lico', '') or self.profile.full_name
        else:
            result = self.profile.full_name
        if self.client.is_individual_entrepreneur:
            if not result.lower().startswith('ип '):
                return 'ИП %s' % result
        return result

    @cached_property
    def offer_additional_data(self):
        if self.request.has_offer():
            return self.request.offer.full_additional_data
