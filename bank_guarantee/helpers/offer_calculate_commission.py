class OfferDefaultCalcCommission:

    @classmethod
    def calculate(cls, offer):
        default_commission = float(offer.default_commission_bank) or 0
        delta_commission = float(offer.delta_commission_bank) or 0
        commission = float(offer.commission_bank) or 0
        return default_commission, delta_commission, commission


class InbankOfferCalcCommission(OfferDefaultCalcCommission):

    @classmethod
    def calculate(cls, offer):
        default_commission = round(
            float(offer.amount) * 0.03 / 365 * offer.request.interval, 2
        )
        if default_commission < offer.commission_bank:
            default_commission = offer.commission_bank
        default_commission = float(default_commission) or 0
        delta_commission = float(offer.commission_bank) - default_commission
        commission = float(offer.commission_bank) or 0
        return default_commission, delta_commission, commission
