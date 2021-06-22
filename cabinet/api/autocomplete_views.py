from rest_framework.response import Response
from rest_framework.views import APIView

from clients.models import Agent, Client, Bank, MFO
from users.models import Role


class AgentsAutocompleteView(APIView):

    def get(self, request, *args, **kwargs):
        result = []
        if self.request.user.is_superuser or self.request.user.has_role(Role.SUPER_AGENT):
            agents = Agent.objects.all()
        else:
            agents = Agent.objects.none()

        for agent in agents.iterator():
            result.append( {
                'value': agent.id,
                'label': '%s (%s/%s)' % (agent.short_name, agent.inn, agent.ogrn),
                'users': [
                    {
                        'value': user.id,
                        'label': '%s %s %s' % (
                            user.last_name, user.first_name, user.middle_name
                        )
                    }
                    for user in agent.user_set.all()
                ]
            })
        return Response({
            'agents': result
        })


class ClientsAutocompleteView(APIView):

    def get(self, request, *args, **kwargs):
        result = {}
        if self.request.user.is_superuser or self.request.user.has_role(Role.SUPER_AGENT):
            clients = Client.objects.all()
        else:
            clients = Client.objects.none()

        for client in clients.iterator():
            result[client.id] = {
                'value': client.id,
                'label': '%s (%s/%s)' % (client.short_name, client.inn, client.ogrn),
                'users': [
                    {'value': user.id, 'label': '%s %s %s' % (
                        user.last_name, user.first_name, user.middle_name)}
                    for user in client.user_set.all()
                ]
            }
        return Response({
            'clients': result
        })


class BanksAutocompleteView(APIView):

    def get(self, request, *args, **kwargs):
        result = {}
        if self.request.user.is_superuser or self.request.user.has_role(Role.SUPER_AGENT):
            banks = Bank.objects.all()
        else:
            banks = Bank.objects.none()

        for bank in banks.iterator():
            result[bank.id] = {
                'value': bank.id,
                'label': '%s (%s/%s)' % (bank.short_name, bank.inn, bank.ogrn),
                'users': [
                    {
                        'value': user.id,
                        'label': '%s %s %s' % (
                            user.last_name, user.first_name, user.middle_name
                        )
                    }
                    for user in bank.user_set.all()
                ]
            }
        return Response({
            'banks': result
        })


class MFOAutocompleteView(APIView):

    def get(self, request, *args, **kwargs):
        result = {}
        if self.request.user.is_superuser or self.request.user.has_role(Role.SUPER_AGENT):
            mfos = MFO.objects.all()
        else:
            mfos = MFO.objects.none()

        for mfo in mfos.iterator():
            result[mfo.id] = {
                'value': mfo.id,
                'label': '%s (%s/%s)' % (mfo.short_name, mfo.inn, mfo.ogrn),
                'users': [
                    {
                        'value': user.id,
                        'label': '%s %s %s' % (
                            user.last_name, user.first_name, user.middle_name
                        )
                    }
                    for user in mfo.user_set.all()
                ]
            }
        return Response({
            'mfo': result
        })
