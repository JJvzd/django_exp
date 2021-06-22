from bank_guarantee.bank_integrations.adapter import BaseBankAdapter
from bank_guarantee.bank_integrations.absolut_bank.absolut_bank import SendRequest


class Adapter(BaseBankAdapter):

    def init_request(self, request):
        sender = SendRequest()
        return sender.init_request(request)

    def check_request(self, request):
        sender = SendRequest()
        external_request = sender.get_external_request(request)
        return bool(external_request and external_request.external_id)

    def send_request_to_bank(self, request):
        sender = SendRequest()
        return sender.send_request(request)

    def get_request_status_in_bank(self, request):
        if self.check_request(request):
            sender = SendRequest()
            return sender.get_current_status(request)

    def before_accept_offer(self, request):
        if self.check_request(request):
            sender = SendRequest()
            return sender.before_accept_offer(request)
        return super(Adapter, self).before_accept_offer(request)

    def change_commission(self, request, commission, reason=None, files=None):
        if self.check_request(request):
            sender = SendRequest()
            return sender.change_commission(request, commission, reason, files)
        return super(Adapter, self).change_commission(request, commission, reason, files)

    def change_project_bg(self, request, file=None, message=None):
        if self.check_request(request):
            sender = SendRequest()
            return sender.change_project_bg(request, file, message)
        return super(Adapter, self).change_project_bg(request, file, message)

    def after_reject_offer(self, request):
        if self.check_request(request):
            sender = SendRequest()
            return sender.reject_request(request)
        return super(Adapter, self).after_reject_offer(request)

    def after_reject_request(self, request, reason=None):
        if self.check_request(request):
            sender = SendRequest()
            return sender.reject_request(request)
        super(Adapter, self).after_reject_request(request, reason=reason)

    def check_and_update_status(self, request):
        if self.check_request(request):
            sender = SendRequest()
            sender.check_and_update_status(request)

    def get_data_for_send_request_to_bank(self, request):
        sender = SendRequest()
        return sender.get_data_for_send(request)
