from datetime import datetime

from django.core.management import BaseCommand

from bank_guarantee.models import Request


class Command(BaseCommand):
    help = 'Очистка старых документов у новых заявок'

    def handle(self, *args, **options):
        date = datetime(day=1, month=11, year=2020)
        for request in Request.objects.filter(created_date__gte=date):
            for doc in request.requestdocument_set.all():
                if not doc.file.file.exists():
                    print('Will remove %s' % doc.file.file.path)
                    # doc.delete()
