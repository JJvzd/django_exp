from django.db.models import Sum, Q, F

from bank_guarantee.constants import ProductChoices
from bank_guarantee.models import Request
from clients.models import Agent, AgentManager
from cabinet.base_logic.reports.generate.base import BaseReport, ExcelCellData
from tender_loans.models import LoanRequest
from users.models import User, Role


def get_count_and_amount(requests):
    unique_requests = requests.filter(Q(base_request=F('id')) | Q(base_request__isnull=True))
    # requests = requests.filter(
    #     Q(base_request__in=unique_requests) | Q(base_request__isnull=True)
    # )
    agent_total_requests = requests.count()
    agent_unique_requests = unique_requests.count()
    agent_total_amount = requests.aggregate(Sum('required_amount')).get('required_amount__sum') or 0
    return agent_total_requests, agent_unique_requests, agent_total_amount


class OperationManagerReport(BaseReport):
    template_name = 'system_files/report_templates/operation_manager_report.xlsx'

    def get_output_filename(self):
        return ('Оперативный отчет менеджера_%s_%s-%s.xlsx' % (
            dict(ProductChoices.PRODUCT_CHOICES).get(self.product, '-'),
            self.date_from.strftime('%d.%m.%Y'),
            self.date_to.strftime('%d.%m.%Y')
        )).replace(' ', '_')

    def __init__(self, date_from, date_to, product, manager, agent):
        super().__init__()
        if manager == 'all':
            self.managers = User.objects.filter(roles__name=Role.MANAGER)
        else:
            self.managers = User.objects.filter(id=manager)

        if agent == 'all':
            self.agents = Agent.objects.all()
        else:
            self.agents = Agent.objects.filter(id=agent)
        self.date_from = date_from
        self.date_to = date_to
        if self.date_to and self.date_from:
            self.filter_date = Q(status_changed_date__gte=self.date_from) & Q(status_changed_date__lte=self.date_to)
        self.product = product

    def get_data(self):
        # self.add_sheet_for_remove('Лист1')
        if self.product == ProductChoices.PRODUCT_BG:
            return self.requests_report()
        if self.product == ProductChoices.PRODUCT_LOAN:
            return self.loans_report()
        if self.product == ProductChoices.PRODUCT_ALL:
            return self.all_type_requests_report()

    def requests_report(self):
        start_row = 19
        data = []
        end_row = 20
        for manager in self.managers:
            data, end_row = self.get_requests_table(data, manager, start_row)
            if end_row == start_row:
                continue
            data.append(ExcelCellData(cell='A%i' % start_row, value='%s Итого' % manager.full_name))
            data.append((ExcelCellData(cell='B%i' % start_row, value='=SUM(B%i:B%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='C%i' % start_row, value='=SUM(C%i:C%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='L%i' % start_row, value='=SUM(L%i:L%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='M%i' % start_row, value='=SUM(M%i:M%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='N%i' % start_row, value='=SUM(N%i:N%i)' % (start_row + 1, end_row - 1))))
            for i in range(15):
                data.append(ExcelCellData(row=start_row, column=i + 1, color='ADB9CA'))
            start_row = end_row
        data = self.fill_header(data, start_row=19, end_row=end_row)
        return {'Лист1': data}

    def loans_report(self):
        start_row = 19
        data = []
        end_row = 20
        for manager in self.managers:
            data, end_row = self.get_loans_table(data, manager, start_row)
            if end_row == start_row:
                continue
            data.append(ExcelCellData(cell='A%i' % start_row, value='%s Итого' % manager.full_name))
            data.append((ExcelCellData(cell='B%i' % start_row, value='=SUM(B%i:B%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='C%i' % start_row, value='=SUM(C%i:C%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='L%i' % start_row, value='=SUM(L%i:L%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='M%i' % start_row, value='=SUM(M%i:M%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='N%i' % start_row, value='=SUM(N%i:N%i)' % (start_row + 1, end_row - 1))))
            for i in range(15):
                data.append(ExcelCellData(row=start_row, column=i + 1, color='ADB9CA'))
            start_row = end_row
        data = self.fill_header(data, start_row=19, end_row=end_row)
        return {'Лист1': data}

    def all_type_requests_report(self):
        start_row = 19
        data = []
        end_row = 20
        for manager in self.managers:
            data, end_row = self.get_all_table(data, manager, start_row)
            if end_row == start_row:
                continue
            data.append(ExcelCellData(cell='A%i' % start_row, value='%s Итого' % manager.full_name))
            data.append((ExcelCellData(cell='B%i' % start_row, value='=SUM(B%i:B%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='C%i' % start_row, value='=SUM(C%i:C%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='L%i' % start_row, value='=SUM(L%i:L%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='M%i' % start_row, value='=SUM(M%i:M%i)' % (start_row + 1, end_row - 1))))
            data.append((ExcelCellData(cell='N%i' % start_row, value='=SUM(N%i:N%i)' % (start_row + 1, end_row - 1))))
            for i in range(15):
                data.append(ExcelCellData(row=start_row, column=i + 1, color='ADB9CA'))
            start_row = end_row
        data = self.fill_header(data, start_row=19, end_row=end_row)
        return {'Лист1': data}

    def get_requests_table(self, data, manager, start_row):
        data_for_insert = []
        for agent in self.agents.filter(
                id__in=AgentManager.objects.filter(manager=manager).values_list('agent_id', flat=True)):
            # запоминаем, чтобы потом вставить суммирующие данные
            requests = agent.request_set.filter(self.filter_date)
            agent_total_requests, agent_unique_requests, agent_total_amount = get_count_and_amount(requests)
            agent_requests_for_insert = []
            for agent_request in requests.filter(Q(base_request=F('id')) | Q(base_request__isnull=True)):
                agent_unique_request_for_insert = {
                    'base': [
                        agent_request.get_number(),
                        agent_request.client.short_name,
                        agent_request.created_date,
                        'Архивная' if agent_request.in_archive else '',
                        agent_request.required_amount
                    ],
                    'requests': [[
                        request.get_number(),
                        request.client.short_name or request.client.full_name,
                        request.status_changed_date,
                        request.bank.short_name if request.bank else '',
                        request.status.name,
                        request.required_amount,
                        self.get_commission_bank(request),
                        'БГ' if request.request_type == Request.TYPE_BG else 'ТЗ',
                        request.get_current_bank_commission() and request.get_current_bank_commission()['commission'],
                    ] for request in agent_request.request_set.filter(self.filter_date)]
                }
                agent_requests_for_insert.append(agent_unique_request_for_insert)

            if agent_requests_for_insert:
                data_for_insert.append({
                    'total': [
                        agent.short_name,
                        agent_total_requests,
                        agent_unique_requests,
                        agent_total_amount
                    ],
                    'data': agent_requests_for_insert
                })
        if data_for_insert:
            row = start_row + 1
        else:
            row = start_row
        for d in data_for_insert:
            start_row_agent = row
            data.append(ExcelCellData(row=row, column=1, value=d['total'][0]))
            data.append(ExcelCellData(row=row, column=2, value=d['total'][1]))
            data.append(ExcelCellData(row=row, column=3, value=d['total'][2]))
            data.append(ExcelCellData(row=row, column=12, value=d['total'][3]))
            for i in range(2, 16):
                data.append(ExcelCellData(row=row, column=i, color='FFC000'))
            row += 1
            for unique_request_group in d['data']:
                data.append(ExcelCellData(row=row, column=4, value=unique_request_group['base'][0]))
                data.append(ExcelCellData(row=row, column=6, value=unique_request_group['base'][1]))
                data.append(
                    ExcelCellData(row=row, column=7, value=unique_request_group['base'][2].strftime('%d.%m.%Y')))
                data.append(ExcelCellData(row=row, column=9, value=unique_request_group['base'][3]))
                data.append(ExcelCellData(row=row, column=12, value=unique_request_group['base'][4]))
                row += 1
                for r in unique_request_group['requests']:
                    data.append(ExcelCellData(row=row, column=5, value=r[0]))
                    data.append(ExcelCellData(row=row, column=6, value=unique_request_group['base'][1]))
                    data.append(ExcelCellData(row=row, column=8, value=r[2].strftime('%d.%m.%Y')))
                    data.append(ExcelCellData(row=row, column=9, value=r[7]))
                    data.append(ExcelCellData(row=row, column=10, value=r[3]))
                    data.append(ExcelCellData(row=row, column=11, value=r[4]))
                    data.append(ExcelCellData(row=row, column=12, value=r[5]))
                    data.append(ExcelCellData(row=row, column=13, value=r[8] or ''))
                    data.append(ExcelCellData(row=row, column=14, value=r[6]))
                    row += 1
            data.append(ExcelCellData(
                merge='A%i:A%i' % (start_row_agent, row - 1)
            ))
        return data, row

    def get_loans_table(self, data, manager, start_row):
        data_for_insert = []
        for agent in self.agents.filter(
                id__in=AgentManager.objects.filter(manager=manager).values_list('agent_id', flat=True)):
            # запоминаем, чтобы потом вставить суммирующие данные
            requests = agent.loanrequest_set.filter(self.filter_date)
            agent_total_requests, agent_unique_requests, agent_total_amount = get_count_and_amount(requests)

            agent_requests_for_insert = []
            for agent_request in requests.filter(Q(base_request=F('id')) | Q(base_request__isnull=True)):
                agent_unique_request_for_insert = {
                    'base': [
                        agent_request.get_number(),
                        agent_request.client.short_name,
                        agent_request.created_date,
                        'Архивная' if agent_request.in_archive else '',
                        agent_request.required_amount
                    ],
                    'requests': [[
                        request.get_number(),
                        request.client.full_name,
                        request.status_changed_date,
                        request.bank.short_name if request.bank else '',
                        request.status.name,
                        request.required_amount,
                        self.get_commission_bank(request),
                        'БГ' if request.request_type == Request.TYPE_BG else 'ТЗ',
                        request.get_current_bank_commission() and request.get_current_bank_commission()['commission'],
                    ] for request in agent_request.loanrequest_set.filter(self.filter_date)]
                }
                agent_requests_for_insert.append(agent_unique_request_for_insert)
            if agent_requests_for_insert:
                data_for_insert.append({
                    'total': [
                        agent.short_name,
                        agent_total_requests,
                        agent_unique_requests,
                        agent_total_amount
                    ],
                    'data': agent_requests_for_insert
                })
        if data_for_insert:
            row = start_row + 1
        else:
            row = start_row
        for d in data_for_insert:
            start_row_agent = row
            data.append(ExcelCellData(row=row, column=1, value=d['total'][0]))
            data.append(ExcelCellData(row=row, column=2, value=d['total'][1]))
            data.append(ExcelCellData(row=row, column=3, value=d['total'][2]))
            data.append(ExcelCellData(row=row, column=12, value=d['total'][3]))
            for i in range(2, 16):
                data.append(ExcelCellData(row=row, column=i, color='FFC000'))
            row += 1
            for unique_request_group in d['data']:
                data.append(ExcelCellData(row=row, column=4, value=unique_request_group['base'][0]))
                data.append(ExcelCellData(row=row, column=6, value=unique_request_group['base'][1]))
                data.append(
                    ExcelCellData(row=row, column=7, value=unique_request_group['base'][2].strftime('%d.%m.%Y')))
                data.append(ExcelCellData(row=row, column=9, value=unique_request_group['base'][3]))
                data.append(ExcelCellData(row=row, column=12, value=unique_request_group['base'][4]))
                row += 1

                for r in unique_request_group['requests']:
                    data.append(ExcelCellData(row=row, column=5, value=r[0]))
                    data.append(ExcelCellData(row=row, column=6, value=unique_request_group['base'][1]))
                    data.append(ExcelCellData(row=row, column=8, value=r[2].strftime('%d.%m.%Y')))
                    data.append(ExcelCellData(row=row, column=9, value=r[7]))
                    data.append(ExcelCellData(row=row, column=10, value=r[3]))
                    data.append(ExcelCellData(row=row, column=11, value=r[4]))
                    data.append(ExcelCellData(row=row, column=12, value=r[5]))
                    data.append(ExcelCellData(row=row, column=13, value=r[8] or ''))
                    data.append(ExcelCellData(row=row, column=14, value=r[6]))
                    row += 1
            data.append(ExcelCellData(
                merge='A%i:A%i' % (start_row_agent, row - 1)
            ))
        return data, row

    def get_all_table(self, data, manager, start_row):
        data_for_insert = []
        row = start_row + 1
        for agent in self.agents.filter(
                id__in=AgentManager.objects.filter(manager=manager).values_list('agent_id', flat=True)):
            # запоминаем, чтобы потом вставить суммирующие данные
            requests = agent.request_set.filter(self.filter_date)
            agent_total_requests, agent_unique_requests, agent_total_amount = get_count_and_amount(requests)
            loan_requests = agent.loanrequest_set.filter(self.filter_date)
            agent_total_loan_requests, agent_unique_loan_requests, agent_total_amount_loan_requests = get_count_and_amount(
                loan_requests)
            agent_total_requests += agent_total_loan_requests
            agent_unique_requests += agent_unique_loan_requests
            agent_total_amount += agent_total_amount_loan_requests
            agent_requests_for_insert = []
            for agent_request in requests.filter(Q(base_request=F('id')) | Q(base_request__isnull=True)):
                agent_unique_request_for_insert = {
                    'base': [
                        agent_request.get_number(),
                        agent_request.client.short_name,
                        agent_request.created_date,
                        'Архивная' if agent_request.in_archive else '',
                        agent_request.required_amount
                    ],
                    'requests': [[
                        request.get_number(),
                        request.client.full_name,
                        request.status_changed_date,
                        request.bank.short_name if request.bank else '',
                        request.status.name,
                        request.required_amount,
                        self.get_commission_bank(request),
                        'БГ' if request.request_type == Request.TYPE_BG else 'ТЗ',
                        request.get_current_bank_commission() and request.get_current_bank_commission()['commission'],
                    ] for request in agent_request.request_set.filter(self.filter_date)]
                }
                agent_requests_for_insert.append(agent_unique_request_for_insert)
            for agent_request in loan_requests.filter(Q(base_request=F('id')) | Q(base_request__isnull=True)):
                agent_unique_request_for_insert = {
                    'base': [
                        agent_request.get_number(),
                        agent_request.client.full_name,
                        agent_request.created_date,
                        'Архивная' if agent_request.in_archive else '',
                        agent_request.required_amount
                    ],
                    'requests': [[
                        request.get_number(),
                        request.client.full_name,
                        request.status_changed_date,
                        request.bank.short_name if request.bank else '',
                        request.status.name,
                        request.required_amount,
                        self.get_commission_bank(request),
                        'БГ' if request.request_type == Request.TYPE_BG else 'ТЗ',
                        request.get_current_bank_commission() and request.get_current_bank_commission()['commission'],
                    ] for request in agent_request.loanrequest_set.filter(self.filter_date)]
                }
                agent_requests_for_insert.append(agent_unique_request_for_insert)
            if agent_requests_for_insert:
                data_for_insert.append({
                    'total': [
                        agent.short_name,
                        agent_total_requests,
                        agent_unique_requests,
                        agent_total_amount
                    ],
                    'data': agent_requests_for_insert
                })
        if data_for_insert:
            row = start_row + 1
        else:
            row = start_row
        for d in data_for_insert:
            start_row_agent = row
            data.append(ExcelCellData(row=row, column=1, value=d['total'][0]))
            data.append(ExcelCellData(row=row, column=2, value=d['total'][1]))
            data.append(ExcelCellData(row=row, column=3, value=d['total'][2]))
            data.append(ExcelCellData(row=row, column=12, value=d['total'][3]))
            for i in range(2, 16):
                data.append(ExcelCellData(row=row, column=i, color='FFC000'))
            row += 1
            for unique_request_group in d['data']:
                data.append(ExcelCellData(row=row, column=4, value=unique_request_group['base'][0]))
                data.append(ExcelCellData(row=row, column=6, value=unique_request_group['base'][1]))
                data.append(
                    ExcelCellData(row=row, column=7, value=unique_request_group['base'][2].strftime('%d.%m.%Y')))
                data.append(ExcelCellData(row=row, column=9, value=unique_request_group['base'][3]))
                data.append(ExcelCellData(row=row, column=12, value=unique_request_group['base'][4]))
                row += 1

                for r in unique_request_group['requests']:
                    data.append(ExcelCellData(row=row, column=5, value=r[0]))
                    data.append(ExcelCellData(row=row, column=6, value=unique_request_group['base'][1]))
                    data.append(ExcelCellData(row=row, column=8, value=r[2].strftime('%d.%m.%Y')))
                    data.append(ExcelCellData(row=row, column=9, value=r[7]))
                    data.append(ExcelCellData(row=row, column=10, value=r[3]))
                    data.append(ExcelCellData(row=row, column=11, value=r[4]))
                    data.append(ExcelCellData(row=row, column=12, value=r[5]))
                    data.append(ExcelCellData(row=row, column=13, value=r[8] or ''))
                    data.append(ExcelCellData(row=row, column=14, value=r[6]))
                    row += 1
            data.append(ExcelCellData(
                merge='A%i:A%i' % (start_row_agent, row - 1)
            ))
        return data, row

    @staticmethod
    def get_commission_bank(request):
        if not request.has_offer():
            return ''
        if request.request_type == request.TYPE_BG:
            return request.offer.commission_bank
        if request.request_type == request.TYPE_LOAN:
            return request.offer.mfo_commission

    def fill_header(self, data, start_row, end_row):
        data.append(ExcelCellData(cell='B9', value=self.date_from.strftime('%d.%m.%Y')))
        data.append(ExcelCellData(cell='C9', value=self.date_to.strftime('%d.%m.%Y')))
        data.append(
            ExcelCellData(cell='B10', value=dict(ProductChoices.PRODUCT_CHOICES).get(self.product, '-')))
        data.append(
            ExcelCellData(cell='B7', value='Все' if self.managers.count() > 1 else self.managers.first().full_name))
        data.append(
            ExcelCellData(cell='B8', value='Все' if self.agents.count() > 1 else self.agents.first().short_name))

        data.append(
            ExcelCellData(cell='B13', value='Все' if self.managers.count() > 1 else self.managers.first().full_name))
        data.append(ExcelCellData(cell='B14', value=self.date_from.strftime('%d.%m.%Y')))
        data.append(ExcelCellData(cell='C14', value=self.date_to.strftime('%d.%m.%Y')))
        data.append(
            ExcelCellData(cell='B10', value=dict(ProductChoices.PRODUCT_CHOICES).get(self.product, '-')))
        data.append(ExcelCellData(cell='B18', value='=SUM(B%i:B%i)/2' % (start_row, end_row)))
        data.append(ExcelCellData(cell='C18', value='=SUM(C%i:C%i)/2' % (start_row, end_row)))
        data.append(ExcelCellData(cell='L18', value='=SUM(L%i:L%i)/2' % (start_row, end_row)))
        data.append(ExcelCellData(cell='M18', value='=SUM(M%i:M%i)/2' % (start_row, end_row)))
        data.append(ExcelCellData(cell='N18', value='=SUM(N%i:N%i)/2' % (start_row, end_row)))
        return data
