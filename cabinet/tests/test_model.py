import os

from django.conf import settings
from django.test import TestCase

from cabinet.models import PlacementPlace


class PlacementPlaceTest(TestCase):
    fixtures = [os.path.join(settings.BASE_DIR, '../fixtures/cabinet.PlacementPlace.json')]

    def test_placement(self):
        placement = PlacementPlace.find_or_insert('ММВБ')
        placement_in_db = PlacementPlace.objects.filter(name='ММВБ').first()
        self.assertEqual(placement, placement_in_db)
        self.assertEqual(placement.alias, placement.code)
        self.assertEqual(placement_in_db.code, None)

        placement = PlacementPlace().find_or_insert('Test')
        placement_in_db = PlacementPlace.objects.filter(name='Test').first()
        self.assertEqual(placement, placement_in_db)
