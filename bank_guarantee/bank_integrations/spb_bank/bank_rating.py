from sentry_sdk import capture_exception

from bank_guarantee.rating import BankRatingResultData, BaseBankRating
from bank_guarantee.bank_integrations.spb_bank.client_rating_calculator import (
    ClientRatingTranslator,
)
from bank_guarantee.bank_integrations.spb_bank.helpers import (
    get_client_rating_calculator,
)


class BankRating(BaseBankRating):

    def calculate(self, request) -> BankRatingResultData:
        try:
            data = get_client_rating_calculator(
                request=request,
            )
            rating = ClientRatingTranslator.translate(data.calculated_score)
            return BankRatingResultData(
                data={
                    'negative_factors': data.calculated_negative_factors_rating,
                    'accounting_report': data.calculated_accounting_report_rating,
                    'principal_experience_rating': data.calculated_principal_experience_rating,  # noqa
                },
                risk_level=rating.level_risk,
                finance_state=rating.finance_state,
                score=rating.score,
                rating=rating.category
            )
        except Exception as e:
            capture_exception(e)
            return BankRatingResultData(
                data={},
                risk_level='-',
                finance_state='-',
                score='-',
                rating='-'
            )
