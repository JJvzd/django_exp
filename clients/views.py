from django.views.generic import ListView, DetailView

from clients.models import AgentVerification


class AgentVerificationsPage(ListView):
    model = AgentVerification
    template_name = 'clients/agent/agent_verifications_list.html'
    ordering = '-updated'


class AgentVerificationDetail(DetailView):
    model = AgentVerification
    template_name = 'clients/agent/agent_verifications_detail.html'
    pk_url_kwarg = 'pk'
