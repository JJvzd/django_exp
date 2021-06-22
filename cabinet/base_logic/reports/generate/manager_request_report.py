import datetime

from bank_guarantee.models import Request
from cabinet.base_logic.reports.generate.base import BaseReport, ExcelCellData
from clients.models import AgentManager


class ManagerRequestReport(BaseReport):
    template_name = 'system_files/report_templates/manager_report.xlsx'

    def __init__(self, manager_data, total_data, requests_last_month, 
                requests_without_last_month, requests_to_businessdays,
                bank_statistic_data, month_dynamics, structure_data):
        super().__init__()
        self.manager_data = manager_data
        self.total_data = {"data":total_data}
        self.requests_without_last_month = {"data":requests_without_last_month}
        self.requests_last_month = {"data":requests_last_month}
        self.requests_to_businessdays = {"data":requests_to_businessdays}
        self.bank_statistic_data = bank_statistic_data
        self.month_dynamics = month_dynamics
        self.structure_data = structure_data
        self.current_row = 2
        self.request_fill = []

    def fill_excel(self, data):
        for request, values in data.items():
            request_data = self.get_manager_request_data(values)
            column_id = 1
            for column_data in request_data:
                self.request_fill.append(ExcelCellData(
                    row=self.current_row,
                    column=column_id,
                    value=column_data,
                ))
                column_id += 1
            self.current_row += 1
        
    def get_data(self):
        self.fill_excel(self.manager_data)
        self.fill_excel(self.total_data)
        self.fill_excel(self.requests_without_last_month)
        self.fill_excel(self.requests_last_month)
        self.fill_excel(self.requests_to_businessdays)

        return {
            'Статистика по менеджерам': self.request_fill,
            'Конверсия по банкам': self.bank_statistic_data.get_data(),
            'Динамика месяч.': self.month_dynamics.get_data(),
            'структура': self.structure_data.get_data()
        }

    def get_manager_request_data(self, request):
        
        return [
            request["name"],
            request["unique_request"] if "unique_request" in request.keys() else None,
            request["unique_request_exc_blank"],
            request["required_amount"] if "required_amount" in request.keys() else None,
            request["required_amount_done"] if "required_amount_done" in request.keys() else None,
            request["commission_bank"] if "commission_bank" in request.keys() else None,
            request["part_commission_bank"] if "part_commission_bank" in request.keys() else None,
            request["avg_required_amount"] if "avg_required_amount" in request.keys() else None,
            request["num_required_amount_done"] if "num_required_amount_done" in request.keys() else None,
            request["avg_term"] if "avg_term" in request.keys() else None,
            request["conversion"] if "conversion" in request.keys() else None,
            request["exhibited"] if "exhibited" in request.keys() else None,
            request["take_rate"] if "take_rate" in request.keys() else None,
        ]
