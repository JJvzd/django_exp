from django.contrib.auth import user_logged_in
from django.db.models.expressions import F
from django.db.models.signals import post_save, pre_save
from django.dispatch.dispatcher import receiver
from django.utils.timezone import now

from clients.models import (
    Agent, MFO, MFOSettings, Bank, BankSettings, Client, ClientChangeAgentHistory
)
from clients.models.common import InternalNews
from questionnaire.models import Profile
from users.models import User, Role


@receiver(post_save, sender=Agent)
def post_save_agent_add_documents(sender, instance=None, created=False, **kwargs):
    if not instance.agentdocument_set.count():
        from clients.models import AgentDocumentCategory, AgentDocument
        objects = AgentDocumentCategory.objects.none()
        if instance.is_individual_entrepreneur:
            objects = AgentDocumentCategory.objects.filter(
                for_individual_entrepreneur=True, active=True
            )
        if instance.is_organization:
            objects = AgentDocumentCategory.objects.filter(
                for_organization=True, active=True
            )
        if instance.is_physical_person:
            objects = AgentDocumentCategory.objects.filter(
                for_physical_person=True, active=True
            )

        for obj in objects:
            AgentDocument.objects.update_or_create(
                agent=instance,
                category=obj
            )


@receiver(post_save, sender=MFO)
def post_save_mfo_create_mfo_settings(sender, instance=None, created=False, **kwargs):
    if created:
        MFOSettings.objects.get_or_create(credit_organization=instance)


@receiver(post_save, sender=Bank)
def post_save_bank_create_bank_settings(sender, instance=None, created=False, **kwargs):
    if created:
        BankSettings.objects.get_or_create(credit_organization=instance)


@receiver(post_save, sender=Client)
def post_save_client_create_profile(sender, instance=None, created=False,
                                    **kwargs):
    try:
        instance.profile
    except Profile.DoesNotExist:
        Profile.objects.get_or_create(client=instance, reg_inn=instance.inn)
        instance.update_kpp_ogrn_region()


@receiver(pre_save, sender=Client)
def check_change_agent(sender, instance, *args, **kwargs):
    if instance.id:
        old_client = Client.objects.get(id=instance.id)
        if old_client.agent_user != instance.agent_user:
            instance.winner_notification = True
            if instance.agent_company and instance.agent_user:
                ClientChangeAgentHistory.objects.create(
                    agent_company=instance.agent_company,
                    agent_user=instance.agent_user,
                    client=old_client
                )
        if old_client.agent_company != instance.agent_company:
            if old_client.agent_company:
                from notification.base import Notification
                Notification.trigger('client_fixed_for_new_agent', params={
                    'agent': old_client.agent_company,
                    'client': old_client,
                })


@receiver(post_save, sender=Client)
def init_client_change_agent(sender, instance, **kwargs):
    if (instance.agent_company and instance.agent_user and
            not ClientChangeAgentHistory.objects.filter(client=instance).exists()):
        ClientChangeAgentHistory.objects.create(
            agent_company=instance.agent_company,
            agent_user=instance.agent_user,
            client=instance
        )


@receiver(post_save, sender=Client)
def load_quarters(sender, instance, **kwargs):
    from accounting_report.parsers import AutoLoaderAccountingReport
    AutoLoaderAccountingReport.load_data(instance)


@receiver(pre_save, sender=Client)
def set_manager(sender, instance, *args, **kwargs):
    if not instance.manager:
        manager = User.objects.filter(roles__name=Role.MANAGER).first()
        instance.manager = manager


@receiver(user_logged_in, sender=User)
def update_date_last_action(sender, user, request, **kwargs):
    if user.client and user.client.get_role() == 'Client':
        client = user.client.get_actual_instance
        client.date_last_action = now()
        client.save()


@receiver(post_save, sender=InternalNews)
def add_internal_news(sender, instance, **kwargs):
    from clients.models import Agent
    if instance.for_agents and (instance.status == InternalNews.STATUS_PUBLISHED):
        Agent.objects.all().update(internal_news=F('internal_news') + 1)
