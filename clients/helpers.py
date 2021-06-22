from django.utils import timezone

from base_request.models import CompanyDocument, BankDocumentType
from clients.models import Company
from clients.serializers import (
    AgentSerializer, ClientSerializer, BankSerializer, MFOSerializer
)


def get_company_serializer(client: Company):
    if client:
        serializer = {
            'Agent': AgentSerializer,
            'Client': ClientSerializer,
            'Bank': BankSerializer,
            'MFO': MFOSerializer
        }.get(client.get_actual_instance.__class__.__name__, ClientSerializer)
        return serializer(client.get_actual_instance)
    return None


class ChangeAgentValidator:

    def __init__(self, client):
        self.client = client

    def get_date_registration(self):
        return self.client.created

    def has_signed_reglament(self):
        document = CompanyDocument.objects.filter(
            company=self.client,
            category_id=BankDocumentType.DOCUMENT_TYPE_EDO,
        ).first()
        if not (document and (document.file.separatedsignature_set.first()
                              or document.file.sign_set.first())):
            return False
        return True

    def has_archive_requests(self):
        from bank_guarantee.models import Request
        return Request.objects.filter(
            client_id=self.client.id,
            in_archive=True,
            created_date__gte=(timezone.now() - timezone.timedelta(days=30))
        ).exists()

    def get_working_requests(self):
        from bank_guarantee.models import Request, RequestStatus
        return Request.objects.filter(
            client_id=self.client.id,
            in_archive=False,
        ).exclude(
            status__code__in=[
                RequestStatus.CODE_FINISHED, RequestStatus.CODE_REQUEST_DENY
            ],
        )

    def has_working_requests(self):
        return self.get_working_requests().exists()

    def is_not_free(self):
        # Временная заглушка
        return True
        # from bank_guarantee.models import RequestStatus, Request
        # now = timezone.now()
        # if self.client.created:
        #     created_less_90_days = (now - self.client.created).days <= 90
        # else:
        #     created_less_90_days = True
        #
        # result = [
        #     created_less_90_days,  # создан менее 90 дней
        #     bool(self.client.date_last_action and (
        #             (now.date() - self.client.date_last_action).days <= 90
        #     )),
        #     Request.objects.filter(
        #         status__code=RequestStatus.CODE_FINISHED, client=self.client
        #     ).exists(),  # наличия выданных БГ
        #     self.has_signed_reglament()  # подписан регламент
        # ]
        # return any(result)
