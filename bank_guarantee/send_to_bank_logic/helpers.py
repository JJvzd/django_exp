from bank_guarantee.models import Request
from tender_loans.models import LoanRequest


class SendResult:
    errors = []
    info = []
    deny = []

    def add_error(self, error):
        self.errors.append(error)

    def add_info(self, info):
        self.info.append(info)

    def add_deny(self, deny):
        self.deny.append(deny)

    def to_json(self):
        return {
            'errors': self.errors,
            'info': self.info,
            'deny': self.deny,
        }


def get_request_model(request):
    if isinstance(request, Request):
        return Request
    if isinstance(request, LoanRequest):
        return LoanRequest
