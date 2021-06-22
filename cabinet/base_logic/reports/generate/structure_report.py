import datetime

from bank_guarantee.models import Request
from cabinet.base_logic.reports.generate.base import BaseReport, ExcelCellData
from clients.models import AgentManager


class StructureRequestReport(BaseReport):
    template_name = 'system_files/report_templates/manager_report.xlsx'
    
    def __init__(self, issued_dict, approve_dict, offer_dict, 
                accepted_dict,total_col):
        super().__init__()
        self.issued_dict = {"data":issued_dict}
        self.approve_dict = {"data":approve_dict}
        self.offer_dict = {"data":offer_dict}
        self.accepted_dict = {"data":accepted_dict}
        self.total_col = {"data":total_col}
        self.current_row = 3
        self.request_fill = []

    def fill_excel(self, data, column_id=2):
        for request, values in data.items():
            request_data = self.get_structure_data(values)
            for column_data in request_data:
                self.request_fill.append(ExcelCellData(
                    row=self.current_row,
                    column=column_id,
                    value=column_data,
                ))
                column_id += 1
            self.current_row += 1

    def get_data_percent(self, data):
        percent_data = dict()
        percent_data["to_1_mln"] = 0
        percent_data["1-5_mln"] = 0
        percent_data["5-15_mln"] = 0
        percent_data["from_15_mln"] = 0
        if data["total_row"] is not None and data["total_row"]!=0:
            percent_data["to_1_mln"] = data["to_1_mln"]/data["total_row"]
            percent_data["1-5_mln"] = data["1-5_mln"]/data["total_row"]
            percent_data["5-15_mln"] = data["5-15_mln"]/data["total_row"]
            percent_data["from_15_mln"] = data["from_15_mln"]/data["total_row"]

        return {"data":percent_data}
        
    def get_data(self):
        self.fill_excel(self.get_data_percent(self.issued_dict["data"]))
        self.fill_excel(self.get_data_percent(self.approve_dict["data"]))
        self.fill_excel(self.get_data_percent(self.offer_dict["data"]))
        self.fill_excel(self.get_data_percent(self.accepted_dict["data"]))
        self.fill_excel(self.get_data_percent(self.total_col["data"]))

        self.current_row = 3

        self.fill_excel(self.issued_dict, 9)
        self.fill_excel(self.approve_dict, 9)
        self.fill_excel(self.offer_dict, 9)
        self.fill_excel(self.accepted_dict, 9)
        self.fill_excel(self.total_col, 9)
    
        return self.request_fill

    def get_structure_data(self, request):

        return [
            request["to_1_mln"] if "to_1_mln" in request.keys() else None,
            request["1-5_mln"] if "1-5_mln" in request.keys() else None,
            request["5-15_mln"]if "5-15_mln" in request.keys() else None,
            request["from_15_mln"]if "from_15_mln" in request.keys() else None,
            request["total_row"]if "total_row" in request.keys() else None,
        ]
