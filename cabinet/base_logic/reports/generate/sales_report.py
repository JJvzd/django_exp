import datetime

from bank_guarantee.models import Request
from cabinet.base_logic.reports.generate.base import BaseReport, ExcelCellData
from clients.serializers import AgentRewardsSerrializer
from clients.models import AgentManager
from users.models import Role, User

class SalesReport(BaseReport):
    template_name = 'system_files/report_templates/sales_report.xlsx'

    def __init__(self, date=None,):
        super().__init__()
        self.date = date

    def get_data(self):
        requests = Request.objects.filter(status=12).order_by('id').select_related('status', 'agent', 'client', 'tender', 'offer')
        requests = requests.filter(offer__contract_date__icontains=self.date)
        current_row = 2
        request_fill = list()
        for request in requests.iterator():
            request_data = self.get_sales_data(request)
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

    def get_sales_data(self, request):
        try:
            offer = request.offer if request.has_offer() else None
            agent_manager_model = AgentManager.objects.all()
            managers = User.objects.filter(roles__name=Role.MANAGER)
            manager_id = agent_manager_model.get(agent_id=request.agent.id).manager_id
            manager_first_name = managers.get(id=manager_id).first_name
            agent_rewards = AgentRewards.objects.all()

            tmp_manager = None
            if request.tmp_manager_id is not None:
                managers = User.objects.filter(roles__name=Role.MANAGER)
                tmp_manager_data = managers.get(id=request.tmp_manager_id)
                tmp_manager = tmp_manager_data.first_name
            
            if request.agent is not None:
                agent_rewards = agent_rewards.filter(agent_id=request.agent.id).filter(bank_id=request.bank.id)
                agent_rewards_data = AgentRewardsSerrializer(agent_rewards, many=True).data
                percent = agent_rewards_data[0]["percent"]
        
            return [
                offer.contract_date,
                request.agent.short_name,
                request.client.short_name,
                request.client.inn,
                request.bank.short_name if request.bank is not None else None,
                offer.amount,
                offer.default_commission_bank,
                offer.delta_commission_bank,
                offer.delta_commission,
                offer.commission_bank,
                percent,
                "1",
                manager_first_name,
                tmp_manager,
                request.agent.ruchnaya_korrect,
                request.agent.kv_previsheniya,
            ]
        except Exception as e:
            pass
