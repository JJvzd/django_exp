from django.core.cache import cache
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = 'Очистка кэша'

    def handle(self, *args, **options):
        cache.clear()
