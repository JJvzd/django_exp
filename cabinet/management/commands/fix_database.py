from django.core.management import BaseCommand
from django.core.management.color import no_style
from django.db import connections


class Command(BaseCommand):
    help = 'Исправление автоинкрементных полей'

    def handle(self, *args, **options):
        from django.apps import apps
        app_labels = [
            'bank_guarantee', 'tender_loans', 'files', 'clients', 'notification',
            'questionnaire', 'users'
        ]

        app_configs = [apps.get_app_config(app_label) for app_label in app_labels]
        connection = connections['default']
        for app_config in app_configs:
            models = app_config.get_models(include_auto_created=True)
            sequence_sql = connection.ops.sequence_reset_sql(no_style(), list(models))

            with connection.cursor() as cursor:
                for sql in sequence_sql:
                    self.stdout.write('EXECUTE %s' % sql)
                    cursor.execute(sql)