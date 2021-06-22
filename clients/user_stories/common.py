from clients.models import Client, Agent, AgentManager
from external_api.dadata_api import DaData
from utils.validators import validate_inn


class CompanyNotFound(Exception):
    pass


def get_company_info(inn):
    validate_inn(inn)
    api = DaData()
    data = api.get_company(inn).get('suggestions')
    if data:
        data = data[0]
        legal_address = data.get('data', {}).get('address', {}).get('value', '')
        short_name = data.get('data', {}).get('name', {}).get('short_with_opf', '')
        full_name = data.get('data', {}).get('name', {}).get('full_with_opf', '')
        inn = data.get('data', {}).get('inn', '')
        kpp = data.get('data', {}).get('kpp', '')
        ogrn = data.get('data', {}).get('ogrn', '')
        return {
            'full_name': full_name,
            'short_name': short_name,
            'legal_address': legal_address,
            'inn': inn,
            'ogrn': ogrn,
            'kpp': kpp,
        }
    raise CompanyNotFound


def create_client_company(inn, agent_user):
    company_info = get_company_info(inn)
    client = Client.objects.create(
        inn=inn,
        kpp=company_info['kpp'],
        ogrn=company_info['ogrn'],
        short_name=company_info['short_name'],
        full_name=company_info['full_name'],
        manager=AgentManager.get_manager_by_agent(agent_user.client.get_actual_instance)
    )
    client.change_agent(
        agent_company=agent_user.client.get_actual_instance, agent_user=agent_user
    )

    client.fill_questionnaire()
    return client


def create_agent_company(inn):
    company_info = get_company_info(inn)
    client = Agent.objects.create(
        inn=inn,
        kpp=company_info['kpp'],
        ogrn=company_info['ogrn'],
        short_name=company_info['short_name'],
        full_name=company_info['full_name'],
    )
    # TODO: добавить документы
    return client
