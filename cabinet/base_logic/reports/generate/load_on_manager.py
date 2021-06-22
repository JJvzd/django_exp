from django.db.models import F, Q

from bank_guarantee.constants import ProductChoices
from bank_guarantee.models import Request
from cabinet.base_logic.reports.generate.base import ExcelCellData, BaseReport
from clients.models import Agent, AgentManager
from tender_loans.models import LoanRequest
from users.models import User, Role


class LoadOnManagerReport(BaseReport):
    template_name = r'system_files/report_templates/load_on_manager.xlsx'

    def get_output_filename(self):
        return ('Нагрузка на менежера_%s_%s-%s.xlsx' % (
            dict(ProductChoices.PRODUCT_CHOICES).get(self.product, '-'),
            self.date_from.strftime('%d.%m.%Y'),
            self.date_to.strftime('%d.%m.%Y')
        )).replace(' ', '_')

    def __init__(self, date_from, date_to, product, manager, agent):
        super().__init__()
        if manager == 'all':
            self.managers = User.objects.filter(roles__name=Role.MANAGER)
        else:
            self.managers = User.objects.filter(id=manager, roles__name=Role.MANAGER)

        if agent == 'all':
            self.agents = Agent.objects.all()
        else:
            self.agents = Agent.objects.filter(id=agent)
        self.date_from = date_from
        self.date_to = date_to
        self.product = product

    def get_data(self):
        if self.product == ProductChoices.PRODUCT_BG:
            return self.requests_report()
        if self.product == ProductChoices.PRODUCT_LOAN:
            return self.loans_report()
        if self.product == ProductChoices.PRODUCT_ALL:
            return self.all_report()

    def fill_head(self, data):
        data.append(ExcelCellData(
            cell='B7',
            value=self.date_from.strftime('%d.%m.%Y')
        ))
        data.append(ExcelCellData(
            cell='C7',
            value=self.date_to.strftime('%d.%m.%Y')
        ))
        data.append(ExcelCellData(
            cell='B9',
            value=self.managers.first().full_name if self.managers.count() == 1 else 'Все'
        ))
        data.append(ExcelCellData(
            cell='B10',
            value=self.agents.first().short_name if self.agents.count() == 1 else 'Все'
        ))
        data.append(ExcelCellData(
            cell='B11',
            value=dict(ProductChoices.PRODUCT_CHOICES).get(self.product)
        ))
        return data


    def requests_report(self):
        data = []
        start_row = 18
        data = self.fill_head(data)
        for manager in self.managers:
            start_row_manager = start_row
            for agent in self.agents.filter(
                    id__in=AgentManager.objects.filter(manager=manager).values_list('agent_id', flat=True)):
                start_row = start_row + 1
                requests = Request.objects.filter(agent=agent)
                data.append(ExcelCellData(
                    cell='B%i' % start_row,
                    value=agent.short_name
                ))
                data.append(ExcelCellData(
                    cell='C%i' % start_row,
                    value=requests.filter(Q(base_request=F('id')) | Q(base_request__isnull=True)).count()
                ))
                data.append(ExcelCellData(
                    cell='D%i' % start_row,
                    value=requests.count()
                ))
                statuses = {
                    'E': 'Черновик',
                    'F': 'На подписании у клиента',
                    'G': 'Направлена в банк / МФО',
                    'H': 'Запрос',
                    'I': 'Отклонено скорингом',
                    'j': 'Отозванная клиентом заявка',
                    'K': 'На рассмотрении в банке / МФО',
                    'L': 'На рассмотрении у службы безопасности',
                    'M': 'На рассмотрении в кредитном комитете',
                    'N': 'Заявка отклонена банком / МФО',
                    'O': 'Одобрено банком / МФО',
                    'P': 'Предложение подготавливается банком / МФО',
                    'Q': 'Банк / МФО отправил предложение',
                    'R': 'Предложение отклонено клиентом',
                    'S': 'Предложение отозвано банком / МФО',
                    'T': 'Предложение принято, не оплачено',
                    'U': 'Подготавливается банковская гарантия',
                    'V': 'Банковская гарантия передана клиенту',
                    'W': 'Закреплен за другим агентом',
                    'X': 'Запрос отработан',
                }
                for key, value in statuses.items():
                    data.append(ExcelCellData(
                        cell='%s%i' % (key, start_row),
                        value=requests.filter(status__name=value).count()
                    ))
            if start_row == start_row_manager:
                continue
            columns = 'CDEFGHIJKLMNOPQRSTUVWX'
            data.append(ExcelCellData(
                cell='A%i' % start_row_manager,
                value='%s (Итого)' % manager.full_name,
                color='F4B183'
            ))
            data.append(ExcelCellData(
                cell='B%i' % start_row_manager,
                color='F4B183'
            ))
            for column in columns:
                data.append(ExcelCellData(
                    cell='%s%i' % (column, start_row_manager),
                    value='=SUM(%s%i:%s%i)' % (column, start_row_manager + 1, column, start_row),
                    color='F4B183'
                ))
            start_row += 1
        columns = 'CDEFGHIJKLMNOPQRSTUVWX'
        data.append(ExcelCellData(
            cell='A%i' % start_row,
            value='Итого',
            color='F4B183'
        ))
        data.append(ExcelCellData(
            cell='B%i' % start_row,
            color='F4B183'
        ))
        for column in columns:
            data.append(ExcelCellData(
                cell='%s%i' % (column, start_row),
                value='=SUM(%s%i:%s%i)/2' % (column, 18, column, start_row-1),
                color='F4B183'
            ))

        return {'Лист1': data}

    def loans_report(self):
        data = []
        start_row = 18
        data = self.fill_head(data)
        for manager in self.managers:
            start_row_manager = start_row
            for agent in self.agents.filter(
                    id__in=AgentManager.objects.filter(manager=manager).values_list('agent_id', flat=True)):
                start_row = start_row + 1
                requests = LoanRequest.objects.filter(agent=agent)
                data.append(ExcelCellData(
                    cell='B%i' % start_row,
                    value=agent.short_name
                ))
                data.append(ExcelCellData(
                    cell='C%i' % start_row,
                    value=requests.filter(Q(base_request=F('id')) | Q(base_request__isnull=True)).count()
                ))
                data.append(ExcelCellData(
                    cell='D%i' % start_row,
                    value=requests.count()
                ))
                statuses = {
                    'E': 'Черновик',
                    'F': 'На подписании у клиента',
                    'G': 'Направлена в банк / МФО',
                    'H': 'Запрос',
                    'I': 'Отклонено скорингом',
                    'j': 'Отозванная клиентом заявка',
                    'K': 'На рассмотрении в банке / МФО',
                    'L': 'На рассмотрении у службы безопасности',
                    'M': 'На рассмотрении в кредитном комитете',
                    'N': 'Заявка отклонена банком / МФО',
                    'O': 'Одобрено банком / МФО',
                    'P': 'Предложение подготавливается банком / МФО',
                    'Q': 'Банк / МФО отправил предложение',
                    'R': 'Предложение отклонено клиентом',
                    'S': 'Предложение отозвано банком / МФО',
                    'T': 'Предложение принято, не оплачено',
                    'U': 'Подготавливается банковская гарантия',
                    'V': 'Займ выдан',
                    'W': 'Закреплен за другим агентом',
                    'X': 'Запрос отработан',
                }
                for key, value in statuses.items():
                    data.append(ExcelCellData(
                        cell='%s%i' % (key, start_row),
                        value=requests.filter(status__name=value).count()
                    ))
            if start_row == start_row_manager:
                continue
            columns = 'CDEFGHIJKLMNOPQRSTUVWX'
            data.append(ExcelCellData(
                cell='A%i' % start_row_manager,
                value='%s (Итого)' % manager.full_name,
                color='F4B183'
            ))
            data.append(ExcelCellData(
                cell='B%i' % start_row_manager,
                color='F4B183'
            ))
            for column in columns:
                data.append(ExcelCellData(
                    cell='%s%i' % (column, start_row_manager),
                    value='=SUM(%s%i:%s%i)' % (column, start_row_manager + 1, column, start_row),
                    color='F4B183'
                ))
            start_row += 1
        columns = 'CDEFGHIJKLMNOPQRSTUVWX'
        data.append(ExcelCellData(
            cell='A%i' % start_row,
            value='Итого',
            color='F4B183'
        ))
        data.append(ExcelCellData(
            cell='B%i' % start_row,
            color='F4B183'
        ))
        for column in columns:
            data.append(ExcelCellData(
                cell='%s%i' % (column, start_row),
                value='=SUM(%s%i:%s%i)/2' % (column, 18, column, start_row - 1),
                color='F4B183'
            ))

        return {'Лист1': data}

    def all_report(self):
        data = []
        start_row = 18
        data = self.fill_head(data)
        for manager in self.managers:
            start_row_manager = start_row
            for agent in self.agents.filter(
                    id__in=AgentManager.objects.filter(manager=manager).values_list('agent_id', flat=True)) :
                start_row = start_row + 1
                requests = Request.objects.filter(agent=agent)
                loan_requests = LoanRequest.objects.filter(agent=agent)
                data.append(ExcelCellData(
                    cell='B%i' % start_row,
                    value=agent.short_name
                ))
                data.append(ExcelCellData(
                    cell='C%i' % start_row,
                    value=requests.filter(
                        Q(base_request=F('id')) | Q(base_request__isnull=True)
                    ).count() + loan_requests.filter(Q(base_request=F('id')) | Q(base_request__isnull=True)).count()
                ))
                data.append(ExcelCellData(
                    cell='D%i' % start_row,
                    value=requests.count() + loan_requests.count()
                ))
                statuses = {
                    'E': 'Черновик',
                    'F': 'На подписании у клиента',
                    'G': 'Направлена в банк / МФО',
                    'H': 'Запрос',
                    'I': 'Отклонено скорингом',
                    'j': 'Отозванная клиентом заявка',
                    'K': 'На рассмотрении в банке / МФО',
                    'L': 'На рассмотрении у службы безопасности',
                    'M': 'На рассмотрении в кредитном комитете',
                    'N': 'Заявка отклонена банком / МФО',
                    'O': 'Одобрено банком / МФО',
                    'P': 'Предложение подготавливается банком / МФО',
                    'Q': 'Банк / МФО отправил предложение',
                    'R': 'Предложение отклонено клиентом',
                    'S': 'Предложение отозвано банком / МФО',
                    'T': 'Предложение принято, не оплачено',
                    'U': 'Подготавливается банковская гарантия',
                    'V': ['Займ выдан', 'Банковская гарантия передана клиенту'],
                    'W': 'Закреплен за другим агентом',
                    'X': 'Запрос отработан',
                }
                for key, value in statuses.items():
                    if isinstance(value, str):
                        value = [value, ]
                    data.append(ExcelCellData(
                        cell='%s%i' % (key, start_row),
                        value=requests.filter(status__name__in=value).count() + loan_requests.filter(
                            status__name=value).count()
                    ))
            if start_row == start_row_manager:
                continue
            columns = 'CDEFGHIJKLMNOPQRSTUVWX'
            data.append(ExcelCellData(
                cell='A%i' % start_row_manager,
                value='%s (Итого)' % manager.full_name,
                color='F4B183'
            ))
            data.append(ExcelCellData(
                cell='B%i' % start_row_manager,
                color='F4B183'
            ))
            for column in columns:
                data.append(ExcelCellData(
                    cell='%s%i' % (column, start_row_manager),
                    value='=SUM(%s%i:%s%i)' % (column, start_row_manager + 1, column, start_row),
                    color='F4B183'
                ))
            start_row += 1
        columns = 'CDEFGHIJKLMNOPQRSTUVWX'
        data.append(ExcelCellData(
            cell='A%i' % start_row,
            value='Итого',
            color='F4B183'
        ))
        data.append(ExcelCellData(
            cell='B%i' % start_row,
            color='F4B183'
        ))
        for column in columns:
            data.append(ExcelCellData(
                cell='%s%i' % (column, start_row),
                value='=SUM(%s%i:%s%i)/2' % (column, 18, column, start_row - 1),
                color='F4B183'
            ))

        return {'Лист1': data}
