from django.core.management.base import BaseCommand

from common.helpers import CronHelper


class Command(BaseCommand):
    help = 'Удаляет все задачи из крона'

    def handle(self, *args, **options):
        cron_helper = CronHelper()
        for job in cron_helper.get_jobs(with_times=False):
            cron_helper.delete_job(job)
        self.stdout.write("All tasks cleared.")







