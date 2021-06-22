import datetime

from bank_guarantee.models import Request
from cabinet.base_logic.reports.generate.base import BaseReport, ExcelCellData
from clients.models import AgentManager


class RequestReport(BaseReport):
    template_name = 'system_files/report_templates/request_report.xlsx'

    def __init__(self, request_data=None):
        super().__init__()
        self.date = request_data["date"]
        self.submitedRequestNum_44 = 0 if request_data["submitedRequestNum_44"] is None else request_data["submitedRequestNum_44"]
        self.submitedRequestNum_223 = 0 if request_data["submitedRequestNum_223"] is None else request_data["submitedRequestNum_223"]
        self.winRequestNum_44 = 0 if request_data["winRequestNum_44"] is None else request_data["winRequestNum_44"]
        self.winRequestNum_223 = 0 if request_data["winRequestNum_223"] is None else request_data["winRequestNum_223"]
        self.winRequestNum_615 = 0 if request_data["winRequestNum_615"] is None else request_data["winRequestNum_615"]
        self.unique_request_44 = 0 if request_data["unique_request_44"] is None else request_data["unique_request_44"]
        self.unique_request_223 = 0 if request_data["unique_request_223"] is None else request_data["unique_request_223"]
        self.unique_request_615 = 0 if request_data["unique_request_615"] is None else request_data["unique_request_615"]
        self.other = 0 if request_data["other"] is None else request_data["other"]
        self.all_num_per_day = self.submitedRequestNum_44 + self.submitedRequestNum_223
        self.all_num_win = self.winRequestNum_44 +self.winRequestNum_223 + self.winRequestNum_615
        self.unique_request = self.unique_request_44 + self.unique_request_223 + self.unique_request_615
        self.row_number = request_data["row_number"]

    def get_data(self):
        current_row = self.row_number
        request_fill = []
        column_id = 1

        request_data = [
            self.date,
            self.all_num_per_day,
            self.all_num_win,
            self.submitedRequestNum_44,
            self.submitedRequestNum_223,
            self.winRequestNum_44,
            self.winRequestNum_223,
            self.unique_request,
            self.unique_request_44,
            self.unique_request_223,
            self.unique_request_615,
            self.other,
        ]
        for column_data in request_data:
            request_fill.append(ExcelCellData(
                row=current_row,
                column=column_id,
                value=column_data,
            ))
            column_id += 1
        return {
            'requests': request_fill
        }