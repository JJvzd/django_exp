import datetime

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver

from bank_guarantee.models import (
    Request, RequestDocument, ClientDocument, RequestHistory, RequestStatus
)
from base_request.models import RequestTender
from clients.models import BankRating, BankPackage, MFOPackage

from common.helpers import delete_file_doc
from files.models import BaseFile


@receiver(post_save, sender=Request)
def create_rating_post_save(sender, instance, created, **kwargs):
    """ Генерация начального рейтинга для заявки """
    if created:
        rating = BankRating.objects.filter(credit_organization=None).last()
        if rating:
            rating.get_rating(instance)


@receiver(post_save, sender=Request)
def post_save_request(sender, instance, created, **kwargs):
    if not instance.base_request:
        try:
            Request.objects.filter(id=instance.id).update(base_request=instance.id)
        except Exception:
            pass

    if created and instance.client:
        from accounting_report.parsers import AutoLoaderAccountingReport
        AutoLoaderAccountingReport.load_data(instance.client)


@receiver(pre_save, sender=Request)
def request_package_update(sender, instance, **kwargs):
    """ Перед сохранением объекта обновляем пакет документов """
    instance.check_package(force=True, auto_save=False)


@receiver(pre_save, sender=Request)
def request_status_changed_update(sender, instance, **kwargs):
    """
    Перед сохранением объекта проверяем поменялся ли у него статус
    Если статус изменем записываем время
    """
    if instance.id:
        if 'status' in instance.changed_fields:
            instance.status_changed = datetime.datetime.now()
    if not instance.tender_id:
        instance.tender = RequestTender.objects.create()


@receiver(post_delete, sender=RequestDocument)
def pre_delete_request_document(sender, instance, **kwargs):
    try:
        delete_file_doc(instance.file)
    except BaseFile.DoesNotExist:
        pass


@receiver(post_delete, sender=ClientDocument)
def pre_delete_client_document(sender, instance, **kwargs):
    try:
        delete_file_doc(instance.file)
    except BaseFile.DoesNotExist:
        pass


@receiver(post_save, sender=RequestHistory)
def update_client_last_action(sender, instance=None, **kwargs):
    user = instance.user
    if user and user.client and user.client.get_role() == 'Client':
        client = instance.user.client.get_actual_instance
        client.date_last_action = instance.created.date()
        client.save()


@receiver(post_save, sender=ClientDocument)
def post_save_client_document(sender, instance, **kwargs):
    """ изменения черновиков БГ """
    from tender_loans.models import LoanRequest, LoanRequestDocument

    banks = BankPackage.objects.filter(document_type=instance.category)
    if banks.exists():
        requests = Request.objects.filter(
            package_class__in=banks.values_list('credit_organization__code', flat=True),
            status__code=RequestStatus.CODE_DRAFT
        )
        for request in requests:
            RequestDocument.objects.filter(
                file=instance.file,
                request=request,
                category=instance.category,
            )

    # изменения черновиков ТЗ
    banks = MFOPackage.objects.filter(document_type=instance.category)
    if banks.exists():
        requests = LoanRequest.objects.filter(
            package_class__in=banks.values_list('credit_organization__code', flat=True),
            status__code=RequestStatus.CODE_DRAFT
        )
        for request in requests:
            LoanRequestDocument.objects.filter(
                file=instance.file,
                request=request,
                category=instance.category,
            )
