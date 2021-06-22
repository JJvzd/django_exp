import calendar
from decimal import Decimal

from django.utils import timezone
from django.utils.dateparse import parse_date

from common.excel import BGCalculator


class OfferCalculateCommissionLogic:

    def __init__(self, request, data):
        self.data = data
        self.request = request
        self.changed = self.data.get('changed')
        self.default_commission_bank = Decimal(
            self.data.get('default_commission_bank') or 0
        )
        self.default_commission_percent = Decimal(
            self.data.get('default_commission_percent') or 0
        )
        self.delta_commission_bank = Decimal(self.data.get('delta_commission_bank') or 0)
        self.commission_bank = Decimal(self.data.get('commission_bank') or 0)
        self.commission_bank_percent = Decimal(
            self.data.get('commission_bank_percent') or 0
        )
        self.interval_to = parse_date(self.data.get('interval_to'))
        self.interval_from = parse_date(self.data.get('interval_from'))

        self.amount = Decimal.from_float(float(self.data.get('amount') or 0))

    def first_calculation(self):
        self.default_commission_bank = 0
        self.default_commission_percent = 0
        self.delta_commission_bank = 0
        self.commission_bank = 0
        self.commission_bank_percent = 0

        self.amount = self.request.required_amount
        self.interval_to = self.request.interval_to
        self.interval_from = self.request.interval_from

    @property
    def interval(self):
        return (self.interval_to - self.interval_from).days

    @property
    def days_in_current_year(self):
        now = timezone.now()
        return 365 + (1 if calendar.isleap(now.year) else 0)

    def calculate_commission(self):
        self.commission_bank = self.default_commission_bank + self.delta_commission_bank
        days = self.days_in_current_year
        if self.delta_commission_bank == 0:
            self.commission_bank_percent = self.default_commission_percent
        else:
            self.commission_bank_percent = self.commission_bank * days * 100 / \
                                           self.amount / self.interval

    def control_not_less_minimal_commission(self, minimal_commission, minimal_percent):
        if self.default_commission_bank <= minimal_commission:
            self.default_commission_bank = minimal_commission
            self.default_commission_percent = minimal_percent
        else:
            self.default_commission_percent = self.default_commission_bank * \
                                              self.days_in_current_year * 100 \
                                              / self.interval / self.amount

    def calculate(self):
        default_commission = BGCalculator().calculate_for_bank(
            amount=self.amount,
            interval=self.interval,
            law=self.request.tender.federal_law,
            guarantee_type=set(self.request.targets),
            bank_code=self.request.bank.code,
        )
        if default_commission:
            minimal_commission = Decimal.from_float(default_commission['commission'])
            minimal_percent = Decimal.from_float(default_commission['percent'])
        else:
            minimal_commission = 0
            minimal_percent = 0

        if self.changed:
            if self.changed in ['amount', 'interval_from', 'interval_to',
                                'default_commission_bank', 'delta_commission_bank']:
                self.control_not_less_minimal_commission(
                    minimal_commission, minimal_percent
                )
                self.calculate_commission()

            if self.changed == 'default_commission_percent':
                self.default_commission_bank = self.amount * \
                                               (self.default_commission_percent/100) * \
                                               self.interval / self.days_in_current_year
                self.control_not_less_minimal_commission(
                    minimal_commission, minimal_percent
                )
                self.calculate_commission()

            if self.changed == 'commission_bank_percent':
                self.control_not_less_minimal_commission(
                    minimal_commission, minimal_percent
                )
                if self.default_commission_percent == self.commission_bank_percent:
                    self.delta_commission_bank = 0
                else:

                    self.commission_bank = self.commission_bank_percent * self.amount * \
                                           self.interval / self.days_in_current_year / 100
                    self.delta_commission_bank = self.commission_bank - \
                                                 self.default_commission_bank
        else:
            self.first_calculation()
            self.control_not_less_minimal_commission(
                minimal_commission, minimal_percent
            )
            self.calculate_commission()

        return {
            'default_commission_bank': self.default_commission_bank,
            'default_commission_percent': round(self.default_commission_percent, 2),
            'delta_commission_bank': self.delta_commission_bank,
            'commission_bank': self.commission_bank,
            'commission_bank_percent': round(self.commission_bank_percent, 2),
            'minimal_commission': minimal_commission,
            'minimal_percent': minimal_percent,
        }
