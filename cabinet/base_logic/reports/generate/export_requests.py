from base_request.models import AbstractRequest
from cabinet.base_logic.reports.generate.base import BaseReport, ExcelCellData
from common.helpers import format_decimal
from users.models import Role


class ExportRequests(BaseReport):
    template_name = r'system_files/report_templates/export_request.xlsx'

    def __init__(self, requests=None, loans=None, role=Role.AGENT):
        super().__init__()
        self.requests = requests
        self.loans = loans
        self.role = role
        self.is_bank = Role.BANK in self.role or Role.MFO in self.role


    def fill_requests_table(self, data, row, requests):
        for request in requests:
            # data.append(ExcelCellData(
            #     row=row,
            #     column=1,
            #     value=request.offer.id if request.has_offer() else ''
            # ))
            data.append(ExcelCellData(
                row=row,
                column=1,
                value=request.request_number
            ))
            data.append(ExcelCellData(
                row=row,
                column=2,
                value=request.request_number_in_bank
            ))
            data.append(ExcelCellData(
                row=row,
                column=3,
                value=request.sent_to_bank_date,
                format='date'
            ))
            data.append(ExcelCellData(
                row=row,
                column=4,
                value=request.status_changed_date,
                format='date'
            ))
            data.append(ExcelCellData(
                row=row,
                column=5,
                value=request.status.name,
                color=request.status.color[1:] if request.status.color else ''
            ))
            data.append(ExcelCellData(
                row=row,
                column=6,
                value='%s, \nИНН: %s' % (request.client.short_name, request.client.profile.reg_inn),
            ))
            data.append(ExcelCellData(
                row=row,
                column=7,
                value=request.bank.short_name if request.bank else ''
            ))
            data.append(ExcelCellData(
                row=row,
                column=8,
                value=request.agent.short_name if request.agent else '',
            ))
            data.append(ExcelCellData(
                row=row,
                column=9,
                value=request.get_targets_display(),
            ))
            data.append(ExcelCellData(
                row=row,
                column=10,
                value=request.required_amount,
                format='money'
            ))
            data.append(ExcelCellData(
                row=row,
                column=11,
                value=request.interval if request.request_type == AbstractRequest.TYPE_BG else '',
            ))
            data.append(ExcelCellData(
                row=row,
                column=12,
                value=request.tender.price,
                format='money'
            ))
            data.append(ExcelCellData(
                row=row,
                column=13,
                value=request.client.accounting_report.get_year_quarter().get_value(
                    2110
                ) * 1000,
                format='money'
            ))
            data.append(ExcelCellData(
                row=row,
                column=14,
                value=request.tender.notification_id,
                href=request.tender.tender_url,
            ))
            # data.append(ExcelCellData(
            #     row=row,
            #     column=13,
            #     value=request.protocol_number if request.request_type == AbstractRequest.TYPE_BG else ''
            # ))
            # data.append(ExcelCellData(
            #     row=row,
            #     column=14,
            #     value=request.protocol_date.strftime('%d.%m.%Y') if request.request_type == AbstractRequest.TYPE_BG and request.protocol_date else ''
            # ))
            data.append(ExcelCellData(
                row=row,
                column=15,
                value=request.tender.get_federal_law_display()
            ))

            final_date = None
            if request.request_type == AbstractRequest.TYPE_BG:
                if request.final_date:
                    final_date = request.final_date
            else:
                final_date = request.date_end
            data.append(ExcelCellData(
                row=row,
                column=16,
                value=final_date,
                format='date'
            ))
            default_commission = None
            delta_commission = None
            commission = None
            if request.request_type == AbstractRequest.TYPE_BG:
                if request.has_offer():
                    if self.is_bank:
                        default_commission = request.offer.default_commission_bank
                        delta_commission = request.offer.delta_commission_bank
                        commission = request.offer.commission_bank
                    else:
                        default_commission = request.offer.default_commission
                        delta_commission = request.offer.delta_commission
                        commission = request.offer.commission
                else:
                    if request.bank:
                        default_commission = (request.get_commission_for_bank_code(
                            request.bank.code
                        ) or {}).get('commission', 0)
                        delta_commission = 0
                        commission = 0
            else:
                if request.has_offer():
                    default_commission = request.offer.commission
                    if self.is_bank:
                        commission = request.offer.mfo_commission
                    else:
                        commission = request.offer.agent_commission
                        if commission and default_commission:
                            delta_commission = commission - default_commission
                        else:
                            delta_commission = 0

            data.append(ExcelCellData(
                row=row,
                column=17,
                value=default_commission,
                format='money'
            ))
            data.append(ExcelCellData(
                row=row,
                column=18,
                value=delta_commission,
                format='money'
            ))
            data.append(ExcelCellData(
                row=row,
                column=19,
                value=commission,
                format='money'
            ))
            manager = request.client.manager
            manager = manager.full_name if manager else ''

            data.append(ExcelCellData(
                row=row,
                column=20,
                value=manager,
            ))
            if not self.is_bank:
                last_comment = request.get_last_comments().first()
                if last_comment:
                    last_comment = last_comment.text
                else:
                    last_comment = ''
                data.append(ExcelCellData(
                    row=row,
                    column=21,
                    value=last_comment
                ))
            if request.has_offer():
                data.append(ExcelCellData(
                    row=row,
                    column=22,
                    value=request.offer.contract_number
                ))
                data.append((ExcelCellData(
                    row=row,
                    column=23,
                    value=request.offer.contract_date,
                    format='date'
                )))
            row += 1
        return data, row

    def get_data(self):
        if ((self.requests and self.requests.count() > 0) or
                (self.loans and self.loans.count() > 0)):
            self.add_sheet_for_remove('requests')
        if self.is_bank:
            self.delete_col(21)
        result = {}
        if self.requests:
            self.add_insert_rows(2, len(self.requests)-1)
            data = []
            row = 2
            data, row = self.fill_requests_table(data, row, self.requests)
            count = self.requests.count()
            data.append(ExcelCellData(
                row=row,
                column=1,
                value='Итог',
            ))
            row += 1
            data.append(ExcelCellData(
                row=row,
                column=1,
                value=count
            ))
            data.append(ExcelCellData(
                cell='J%i' % row,
                value='=SUM(J%i:J%i)' % (2, row - 2)
            ))
            data.append(ExcelCellData(
                cell='Q%i' % row,
                value='=SUM(Q%i:Q%i)' % (2, row - 2)
            ))
            data.append(ExcelCellData(
                cell='R%i' % row,
                value='=SUM(R%i:R%i)' % (2, row - 2)
            ))
            data.append(ExcelCellData(
                cell='S%i' % row,
                value='=SUM(S%i:S%i)' % (2, row - 2)
            ))
            result.update({('Банковские гарантии', 'requests'): data})
        if self.loans:
            data = []
            row = 2
            data, row = self.fill_requests_table(data, row, self.loans)
            count = self.loans.count()
            row += 1
            data.append(ExcelCellData(
                row=row,
                column=1,
                value=count
            ))
            data.append(ExcelCellData(
                cell='J%i' % row,
                value='=SUM(J%i:J%i)' % (2, row - 2)
            ))
            data.append(ExcelCellData(
                cell='Q%i' % row,
                value='=SUM(Q%i:Q%i)' % (2, row - 2)
            ))
            data.append(ExcelCellData(
                cell='R%i' % row,
                value='=SUM(R%i:R%i)' % (2, row - 2)
            ))
            data.append(ExcelCellData(
                cell='S%i' % row,
                value='=SUM(S%i:S%i)' % (2, row - 2)
            ))
            result.update({('Тендерные займы', 'requests'): data})
        return result

    def get_output_filename(self, extension=None):
        if not extension:
            extension = 'xlsx'
        return 'export_requests.%s' % extension
