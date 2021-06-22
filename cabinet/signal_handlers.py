from django.db.models.expressions import F
from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver

from cabinet.models import WorkRule


@receiver(post_save, sender=WorkRule)
def add_work_rule(sender, instance, **kwargs):
    from clients.models import Agent
    Agent.objects.all().update(work_rules=F('work_rules') + 1)
