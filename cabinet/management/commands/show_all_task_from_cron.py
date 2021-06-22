from django.core.management.base import BaseCommand

from data.helpers import CronHelper


class Command(BaseCommand):
    help = 'Показывает все задачи из крона'

    def handle(self, *args, **options):
        cron_helper = CronHelper()
        jobs = cron_helper.get_jobs(with_times=True)

        for task, time in jobs:
            self.stdout.write('%s - %s' % (task, time))

        if not jobs:
            self.stdout.write('Empty')
