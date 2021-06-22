from django.test import TestCase

from cabinet.base_logic.printing_forms.adapters.excel import ExcelBasePrintFormGenerator


class ExcelTestCase(TestCase):

    def test_parse_col_and_row(self):
        helper = ExcelBasePrintFormGenerator()
        self.assertEqual(helper.parse_row_and_col('A12'), [12, 1])
        self.assertEqual(helper.parse_row_and_col('ZZ1'), [1, 702])
