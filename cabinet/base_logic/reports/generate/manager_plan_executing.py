from django.db.models import Q, Sum

from bank_guarantee.constants import ProductChoices
from bank_guarantee.models import Request, RequestStatus, Offer
from cabinet.base_logic.reports.generate.base import BaseReport, ExcelCellData
from clients.models import AgentManager, Bank, MFO
from tender_loans.models import LoanRequest, LoanOffer
from users.models import Role, User


class ManagerPlanExecutingReport(BaseReport):
    template_name = 'system_files/report_templates/manager_plan_executing.xlsx'

    def __init__(self, date_from, date_to, product, manager):
        super().__init__()
        if manager == 'all':
            self.managers = User.objects.filter(roles__name=Role.MANAGER)
        else:
            self.managers = User.objects.filter(id=manager)
        self.date_from = date_from
        self.date_to = date_to
        self.product = product

    def get_output_filename(self):
        return ('Фактический_план_%s_%s-%s.xlsx' % (
            dict(ProductChoices.PRODUCT_CHOICES).get(self.product, '-'),
            self.date_from.strftime('%d.%m.%Y'),
            self.date_to.strftime('%d.%m.%Y')
        )).replace(' ', '_')

    def get_requests(self, manager):
        requests = Request.objects.filter(
            Q(status__code=RequestStatus.CODE_FINISHED) &
            Q(status_changed_date__gte=self.date_from) &
            Q(status_changed_date__lte=self.date_to)
        )
        if manager:
            requests = requests.filter(
                Q(agent_user=manager) |
                Q(agent__in=AgentManager.objects.filter(manager=manager).values_list('agent', flat=True)),
            )
        else:
            manager_ids = list(self.managers.values_list('id', flat=True))
            requests = requests.filter(
                Q(agent_user__id__in=manager_ids) |
                Q(agent__in=AgentManager.objects.filter(manager__id__in=manager_ids).values_list('agent', flat=True)),
            )
        return requests

    def fill_header(self, data, manager_name, start_row, end_row):
        data.append(ExcelCellData(cell='B4', value=self.date_from.strftime('%d.%m.%Y')))
        data.append(ExcelCellData(cell='C4', value=self.date_to.strftime('%d.%m.%Y')))
        data.append(
            ExcelCellData(cell='B5', value=dict(ProductChoices.PRODUCT_CHOICES).get(self.product, '-')))
        data.append(ExcelCellData(
            cell='B6',
            value=manager_name if isinstance(manager_name, str) else manager_name.full_name)
        )

        data.append(ExcelCellData(cell='B9', value='=SUM(B%s:B%s)' % (start_row, end_row - 1)))
        data.append(ExcelCellData(cell='B11', value='=SUM(C%s:C%s)' % (start_row, end_row - 1)))
        data.append(ExcelCellData(cell='B12', value='=SUM(D%s:D%s)' % (start_row, end_row - 1)))
        data.append(ExcelCellData(cell='B10', value='-'))
        return data

    def get_requests_table(self, data, start_row, manager=None):
        banks = Bank.objects.all()
        row = start_row
        for bank in banks:
            bank_requests = self.get_requests(manager).filter(bank=bank)
            bank_offers = Offer.objects.filter(request__in=bank_requests)
            total_commission = bank_offers.aggregate(total_commission=Sum('commission_bank'))['total_commission'] or 0
            total_sum = bank_offers.aggregate(total_sum=Sum('amount'))['total_sum'] or 0
            offer_counts = bank_offers.count()
            if offer_counts:
                data.append(ExcelCellData(row=row, column=1, value=bank.short_name))
                data.append(ExcelCellData(row=row, column=2, value=total_commission))
                data.append(ExcelCellData(row=row, column=3, value=offer_counts))
                data.append(ExcelCellData(row=row, column=4, value=total_sum))
                row += 1
        return data, row

    def requests_report(self):
        result = {}
        for manager in self.managers:
            data = list()
            data, end_row = self.get_requests_table(data, 15, manager)
            data = self.fill_header(data, manager, start_row=15, end_row=end_row)
            result[(manager.full_name, 'Лист1')] = data
        return result

    def get_data(self):
        self.add_sheet_for_remove('Лист1')
        if self.product == ProductChoices.PRODUCT_BG:
            return self.requests_report()
        if self.product == ProductChoices.PRODUCT_LOAN:
            return self.loans_report()
        if self.product == ProductChoices.PRODUCT_ALL:
            return self.all_type_requests_report()

    def get_loans(self, manager):
        loans = LoanRequest.objects.filter(
            Q(status__code='loan_issued') &
            Q(status_changed_date__gte=self.date_from) &
            Q(status_changed_date__lte=self.date_to)
        )
        if manager:
            loans = loans.filter(
                Q(agent_user=manager) |
                Q(agent__in=AgentManager.objects.filter(manager=manager).values_list('agent', flat=True)),
            )
        else:
            manager_ids = list(self.managers.values_list('id', flat=True))
            loans = loans.filter(
                Q(agent_user__id__in=manager_ids) |
                Q(agent__in=AgentManager.objects.filter(manager__id__in=manager_ids).values_list('agent', flat=True)),
            )
        return loans

    def get_loan_table(self, data, start_row, manager=None):
        banks = MFO.objects.all()
        row = start_row
        for bank in banks:
            bank_requests = self.get_loans(manager).filter(bank=bank)
            bank_offers = LoanOffer.objects.filter(request__in=bank_requests)
            total_commission = bank_offers.aggregate(total_commission=Sum('mfo_commission'))['total_commission'] or 0
            total_sum = bank_offers.aggregate(total_sum=Sum('amount'))['total_sum'] or 0
            offer_counts = bank_offers.count()
            if offer_counts:
                data.append(ExcelCellData(row=row, column=1, value=bank.short_name))
                data.append(ExcelCellData(row=row, column=2, value=total_commission))
                data.append(ExcelCellData(row=row, column=3, value=offer_counts))
                data.append(ExcelCellData(row=row, column=4, value=total_sum))
                row += 1
        return data, row

    def loans_report(self):
        result = {}
        for manager in self.managers:
            data = list()
            data, end_row = self.get_loan_table(data, 15, manager)
            data = self.fill_header(data, manager.full_name, start_row=15, end_row=end_row)
            result[(manager.full_name, 'Лист1')] = data
        return result

    def all_type_requests_report(self):
        result = {}
        for manager in self.managers:
            data = list()
            data, end_row = self.get_requests_table(data, 15, manager)
            data, end_row = self.get_loan_table(data, end_row, manager)
            data = self.fill_header(data, manager.full_name, start_row=15, end_row=end_row)
            result[(manager.full_name, 'Лист1')] = data
        data, end_row = self.get_requests_table(data, 15, None)
        data, end_row = self.get_loan_table(data, end_row, None)
        data = self.fill_header(data, 'Итог', start_row=15, end_row=end_row)
        result[('Итог', 'Лист1')] = data
        return result
