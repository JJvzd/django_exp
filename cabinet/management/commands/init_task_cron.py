from django.conf import settings
from django.core.management.base import BaseCommand

from common.helpers import CronHelper
from base_request.jobs import to_archive


class Command(BaseCommand):
    help = 'Запускает задачи в крон'

    def handle(self, *args, **options):
        if settings.DEBUG:
            self.stdout.write("DEBUG VAR SET AS TRUE, EXIT")
            # return

        timeout = 60 * 60 * 24
        tasks = [
            {
                'cron_string': '23 * * * *',
                'func': to_archive,
                'args': [],
                'kwargs': {
                },
                'timeout': timeout,
            }
        ]

        cron_helper = CronHelper()
        for old_job in cron_helper.get_jobs(False):
            cron_helper.delete_job(old_job)

        for task in tasks:
            cron_helper.create_job(task, overwrite=True)
