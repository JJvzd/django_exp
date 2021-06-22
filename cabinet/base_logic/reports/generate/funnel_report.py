import datetime

from bank_guarantee.models import Request
from cabinet.base_logic.reports.generate.base import BaseReport, ExcelCellData
from clients.models import AgentManager


class SalesFunnelReport(BaseReport):
    template_name = 'system_files/report_templates/funnel_requests.xlsx'

    def __init__(self, from_month=None, from_year=None):
        super().__init__()
        if not from_month:
            from_month = 1
        if not from_year:
            from_year = datetime.datetime.now().year - 2
        self.date_from = datetime.date(year=from_year, month=from_month, day=1)

    def get_data(self):
        requests = Request.objects.filter(
            created_date__gte=self.date_from
        ).order_by('id').select_related('status', 'agent', 'client', 'tender', 'offer')
        current_row = 2
        request_fill = []
        for request in requests.iterator():
            request_data = self.get_funnel_request_data(request)
            column_id = 1
            for column_data in request_data:
                request_fill.append(ExcelCellData(
                    row=current_row,
                    column=column_id,
                    value=column_data,
                ))
                column_id += 1
            current_row += 1
        return {
            'requests': request_fill
        }

    def get_funnel_request_data(self, request):
        offer = request.offer if request.has_offer() else None
        manager = request.client.manager
        return [
            offer.id if offer else '',
            request.request_number.split('-')[0],
            request.get_number(),
            request.request_number_in_bank,
            request.created_date.strftime('%d.%m.%Y'),
            request.status_changed_date.strftime('%d.%m.%Y'),
            request.status.name,
            request.client.short_name,
            request.client.inn,
            request.bank.short_name if request.bank else '',
            request.bank.inn if request.bank else '',
            request.agent.short_name if request.agent_id else '',
            request.agent.inn if request.agent_id else '',
            request.required_amount,
            request.interval,
            request.tender.notification_id,
            request.protocol_number,
            request.protocol_date,
            request.tender.get_federal_law_display(),
            request.final_date,
            offer.default_commission if offer else '',
            offer.delta_commission if offer else '',
            offer.commission if offer else '',
            manager.full_name if manager else '',
            request.last_comment,
        ]
