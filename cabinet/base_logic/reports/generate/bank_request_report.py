import datetime

from bank_guarantee.models import Request
from cabinet.base_logic.reports.generate.base import BaseReport, ExcelCellData
from clients.models import AgentManager


class BankRequestReport(BaseReport):
    template_name = 'system_files/report_templates/manager_report.xlsx'

    def __init__(self, bank_data, overall_data, overall_unique_data):
        super().__init__()
        self.bank_data = bank_data
        self.overall_data = {"data":overall_data}
        self.overall_unique_data = {"data":overall_unique_data}
        self.current_row = 2
        self.request_fill = []

    def fill_excel(self, data):
        for request, values in data.items():
            request_data = self.get_bank_request_data(values)
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
        self.fill_excel(self.bank_data)
        self.fill_excel(self.overall_data)
        self.fill_excel(self.overall_unique_data)
    
        return self.request_fill

    def get_bank_request_data(self, request):
        
        return [
            request["name"],
            request["all_requests"],
            request["requests_done"],
            request["unreached_requests"],
            request["avg_bg_sum"],
            request["commission_requests"],
            request["conversion"],
            request["verification_requests"],
            request["issued"],
            request["avg_bg_sum_issued_request"],
            request["comissoion_issued"],
            request["conversion_issued_to_exhibited"],
            request["conversion_issued_to_exhibited_by_value"],
            request["conversion_issued_to_all"],
        ]
