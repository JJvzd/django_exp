import os
import re

import dbf
from django.core.management import BaseCommand

from cabinet.models import Region
from common.helpers import get_logger

logger = get_logger()


class Command(BaseCommand):
    help = 'Ининцализация регионов'

    def handle(self, *args, **options):  # noqa: MC0001
        path = os.path.join(
            os.path.dirname(__file__), '../../static/cabinet/soun',  'SOUN1.dbf'
        )

        table = dbf.Table(path, codepage='cp866')
        table.open()
        for row in table:
            try:
                name = row[14].split(',')[2]
                if not name:
                    for i in row[14].split(','):
                        if re.search(r'.* г$', i):
                            name = i[:-2]
                        if re.search(r'.*г\.', i):
                            name = i[4:]
                        if re.search(r'.*Респ$', i):
                            name = i[:-5]
                        if 'обл' in i:
                            if 'Московская' not in i:
                                name = i
                        if 'пгт' in i:
                            name = i
                        if 'Чита-46' == i:
                            name = i
                        if 'Иркутская' == i:
                            name = 'Иркутская область'
                    if not name:
                        logger.error('регион не определён %s' % row[14])
                if re.search(r'.* г$', name):
                    name = name[:-2]
                if re.search(r'.* Респ$', name):
                    name = name[:-5]
                if "Московская" in name:
                    name += row[14].split(',')[3]
                code = row[0]
                if Region.objects.filter(code=code).first():
                    continue
                Region.objects.create(name=name, code=code)
            except IndexError:
                continue
