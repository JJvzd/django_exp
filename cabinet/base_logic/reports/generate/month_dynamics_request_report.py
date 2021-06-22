import datetime

from bank_guarantee.models import Request
from cabinet.base_logic.reports.generate.base import BaseReport, ExcelCellData
from clients.models import AgentManager


class MonthDynamicsRequestReport(BaseReport):
    template_name = 'system_files/report_templates/manager_report.xlsx'

    def __init__(self, month_dynamics, date):

        super().__init__()
        self.month_dynamics = {"data":month_dynamics}
        self.column_id = 27 + int(date.split('-')[1])
        self.request_fill = []

    def fill_excel(self, data):
        for request, values in data.items():
            request_data = self.get_month_dynamics_request_data(values)
            current_row = 3
            for column_data in request_data:
                self.request_fill.append(ExcelCellData(
                    row=current_row,
                    column=self.column_id,
                    value=column_data,
                ))
                current_row += 1
        
    def get_data(self):
        self.fill_excel(self.month_dynamics)
    
        return self.request_fill

    def get_month_dynamics_request_data(self, request):
        
        return [
            request["unique_agents"],
            request["unique_agents_issued"],
            request["unique_clients"],
            request["unique_clients_issued"],
            request["unique_requests_month"],
            request["unique_requests_month_exc_blank"],
            request["maxim_report"],
            request["unique_requests_month_exc_blank_to_workday"],
            request["maxim_report_to_workday"],
            request["requests_in_bank"],
            request["unique_requests_in_bank"],
            request["offer_requests"],
            request["unique_offer_requests"],
            request["month_issued"],
            request["conversion_issued_to_unique_requests_in_bank"],
            request["conversion_issued_to_requests_in_bank"],
            request["conversion_offer_to_requests_in_bank"],
            request["conversion_offer_to_issued"],
            request["conversion_offer_to_unique_issued"],
            request["conversion_issued_to_requests_in_bank"],
            request["unique_request_per_agent"],
            request["unique_requests_exc_blank_per_agent"],
            request["issued_per_agent_issued"],
            request["avg_receipt_bg"],
            request["avg_receipt_comission"],
            request["avg_receipt_comission_exc_issued"],
            request["all_commission_sum"],
            request["businessdays"],
        ]
