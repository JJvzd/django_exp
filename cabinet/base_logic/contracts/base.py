from django.core.cache import cache

from external_api.clearspending_api import ClearsSpendingApi
from external_api.parsers_tenderhelp import ParsersApi


class ContractsLogic:

    def __init__(self, client):
        self.client = client

    def has_finished_contracts(self):
        api = ClearsSpendingApi()
        return api.check_experience(inn=self.client.inn, kpp=self.client.kpp)

    def get_finished_contracts_count(self):
        return len(self.get_finished_contracts())

    def get_finished_contracts(self):
        contracts = self.get_contracts()
        finished_contracts = []
        api = ParsersApi()

        for contract_type in contracts:
            finished_contracts.extend(
                api.zakupki.filter_by_status(contracts[contract_type], 'EC')
            )
        return finished_contracts

    def get_execution_contracts(self):
        contracts = self.get_contracts()
        executing_contracts = []
        api = ParsersApi()

        for contract_type in contracts:
            executing_contracts.extend(
                api.zakupki.filter_by_status(contracts[contract_type], 'E')
            )
        return executing_contracts

    def get_contracts(self):
        cache_key = 'contracts_%s' % self.client.inn
        result = cache.get(cache_key, None)
        if result is None:
            api = ParsersApi()
            contracts = api.zakupki.get_contracts(self.client.inn)
            cache.set(cache_key, contracts, 60 * 60 * 12)

        return cache.get(cache_key)

    def get_similar_contracts(self, notification_id):
        api = ParsersApi()
        data_contract = api.zakupki.get_tender(tender_id=notification_id)
        if data_contract.get('okpd2') is None:
            return []
        client_contracts = self.get_contracts()
        result = []
        for okpd2 in data_contract['okpd2']:
            for contracts_type in client_contracts:
                search_okved = '.'.join(okpd2.split('.')[:2])
                for contract in client_contracts[contracts_type]['contracts']:
                    okved = '.'.join(contract['okpd2'].split('.')[:2])
                    if search_okved == okved:
                        result.append(contract)
                        client_contracts.remove(contract)
        return result
