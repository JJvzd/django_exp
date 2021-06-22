from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from cabinet.constants.constants import Target


class Adapter(BaseBankAdapter):

    def request_limit(self, request):
        if Target.PARTICIPANT in request.targets:
            return request.required_amount + request.procuring_amount
        return request.required_amount
