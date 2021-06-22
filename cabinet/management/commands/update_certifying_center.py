import requests
from django.core.management import BaseCommand, CommandError
from lxml.etree import XMLParser, XML

from cabinet.models import CertifyingCenter


class Command(BaseCommand):
    help = 'Обновление модели удостоверяющих центров'

    def handle(self, *args, **options):
        xml = requests.get(r'https://e-trust.gosuslugi.ru/CA/DownloadTSL?schemaVersion=0')
        if xml.status_code != 200:
            raise CommandError('Невозможно обновить')
        p = XMLParser(huge_tree=True)
        certifying_centers = XML(xml.text, p).findall('УдостоверяющийЦентр')
        for element in certifying_centers:
            certifying_center = CertifyingCenter()
            certifying_center.inn = element.find('ИНН').text
            certifying_center.save()
        self.stdout.write(self.style.SUCCESS('Модель удостоверяющих центров обновилось'))
        self.stdout.write(self.style.SUCCESS('Всего записей %s' % len(CertifyingCenter.objects.all())))