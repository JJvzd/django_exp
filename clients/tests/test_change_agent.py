import pytest

from clients.models import AgentManager
from users.models import User
from utils.functions_for_tests import create_client, create_agent


@pytest.mark.django_db
def test_change_agent(initial_data_db):

    first_agent = create_agent()
    client = create_client(agent=first_agent)
    another_agent = create_agent()
    assert client.agent_company == first_agent
    manager = client.manager
    another_manager = AgentManager.get_manager_by_agent(another_agent)
    assert manager != another_manager
    assert isinstance(manager, User)
    client.change_agent(
        agent_company=another_agent,
        agent_user=another_agent.user_set.first()
    )
    assert client.manager == AgentManager.get_manager_by_agent(another_agent)
    AgentManager.set_manager_to_agent(manager=manager, agent=another_agent)
    assert AgentManager.get_manager_by_agent(another_agent) == manager
    client.refresh_from_db()
    assert client.manager == manager