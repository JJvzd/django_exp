from datetime import timedelta

from django.core.management import BaseCommand
from django.db.models import Q
from django.utils import timezone

from bank_guarantee.models import Request
from cabinet.models import System
from clients.models import Bank


class Command(BaseCommand):
    help = 'Отрпавка заявок в архиве'

    def handle(self, *args, **options):
        system_days_before_archive = System.get_setting('archive_days')
        print("System auto archive days = %s" % system_days_before_archive)
        archive_before_date = timezone.now() - timedelta(days=system_days_before_archive)
        print("Will move to archive request, without bank and last changed before %s" %
              archive_before_date)
        requests = Request.objects.filter(
            Q(bank__isnull=True) &
            Q(
                status_changed_date__lt=archive_before_date,
                in_archive=False
            )
        )
        for request in requests.iterator():
            print("\t%s will move to archive" % request)
        requests.update(in_archive=True)
        for bank in Bank.objects.all():
            days_before_archive = bank.settings.archive_days or system_days_before_archive
            print("Bank auto archive days = %s" % days_before_archive)

            requests = Request.objects.filter(
                status_changed_date__lt=timezone.now() - timedelta(
                    days=days_before_archive
                ),
                in_archive=False,
                bank=bank
            )
            for request in requests.iterator():
                print("\t%s will move to archive" % request)
            requests.update(in_archive=True)
