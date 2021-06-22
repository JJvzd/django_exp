from cabinet.base_logic.printing_forms.helpers.base import BaseHelper
from clients.models import Bank, BankCode


class EastHelper(BaseHelper):

    def __init__(self, *args, **kwargs):
        super(EastHelper, self).__init__(*args, **kwargs)
        from cabinet.base_logic.bank_conclusions.east import GeneratorConclusion
        bank = Bank.objects.get(code=BankCode.CODE_EAST)
        self.gc_manager = GeneratorConclusion(self.request, bank)

    @property
    def get_conclusion(self):
        result = {
            "finance_state": None,
            "finance_scoring": None,
            "category": None,
            "total_scoring": None,
            "limit": None,
            "max_bg_limit": None,
            "bg_limit": None,
        }
        return result

    @property
    def get_stop_factors(self):
        tmp_data = self.gc_manager.get_data()['stop_factors']
        data = {
            'p1_scoring': tmp_data['p1']['scoring'],
            'p2_scoring': tmp_data['p2']['scoring'],
            'p3_scoring': tmp_data['p3']['scoring'],
            'p4_scoring': tmp_data['p4']['scoring'],
            'p5_scoring': tmp_data['p5']['scoring'],
            'p6_scoring': tmp_data['p6']['scoring'],
            'p7_scoring': tmp_data['p7']['scoring'],
            'p8_scoring': tmp_data['p8']['scoring'],
            'p9_scoring': tmp_data['p9']['scoring'],
            'p10_scoring': tmp_data['p10']['scoring'],
            'p11_scoring': tmp_data['p11']['scoring'],
            'p12_scoring': tmp_data['p12']['scoring'],
            'total': tmp_data['total'],
        }
        return data

    @property
    def get_principal_bo(self):
        tmp_data = self.gc_manager.get_data()['principal_bo']
        data = {
            'p1': tmp_data['p1'],
            'p2': tmp_data['p2'],
            'p3': tmp_data['p3'],
            'p4': tmp_data['p4'],
            'p5': tmp_data['p5'],
            'p6': tmp_data['p6'],
            'avg': tmp_data['avg']
        }
        return data

    @property
    def get_critical_factors(self):
        tmp_data = self.gc_manager.get_data()['critical_factors']
        data = {
            'p1': tmp_data['p1'],
            'p2': tmp_data['p2'],
            'p3': tmp_data['p3'],
            'avg': tmp_data['avg']
        }
        return data

    @property
    def get_other_factors(self):
        tmp_data = self.gc_manager.get_data()['other_factors']
        data = {
            'p1': tmp_data['p1'],
            'p2': tmp_data['p2'],
            'p3': tmp_data['p3'],
            'p4': tmp_data['p4'],
            'p5': tmp_data['p5'],
            'p6': tmp_data['p6'],
            'total': tmp_data['total']
        }
        return data

    @property
    def get_conditional_factors(self):
        tmp_data = self.gc_manager.get_data()['conditional_factors']
        data = {
            'p1': tmp_data['p1'],
            'p2': tmp_data['p2'],
            'p3': tmp_data['p3'],
            'p4': tmp_data['p4'],
        }
        return data

    @property
    def get_principal_experience(self):
        tmp_data = self.gc_manager.get_data()['principal_experience']
        data = {
            'p1': tmp_data['p1'],
            'p2': tmp_data['p2'],
            'avg': tmp_data['avg'],
        }
        return data
