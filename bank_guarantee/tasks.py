import logging

from django_rq import job

from bank_guarantee.models import Request
from clients.models import BankRating

logger = logging.getLogger('django')


@job
def task_generate_request_rating(request_id, force=False):
    """ Генерация всех рейтингов доступных для оценки"""
    logger.info("Расчет рейтинга для заявки #%s" % request_id)
    request = Request.objects.filter(id=request_id).first()
    if request:
        ratings = BankRating.objects.filter(active=True)
        for rating in ratings:
            rating.get_rating(request=request, force=force)


@job
def task_update_request_rating(request_id):
    """Обновление рейтинга для заявки"""
    logger.info("Расчет рейтинга для заявки #%s" % request_id)
    request = Request.objects.filter(id=request_id).first()
    if request:
        rating = request.bank.bankrating_set.last()
        if rating:
            rating.update_rating(request=request)
