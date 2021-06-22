import attr


@attr.s
class BankRatingResultData:
    rating = attr.ib(kw_only=True)
    finance_state = attr.ib(kw_only=True)
    risk_level = attr.ib(kw_only=True)
    score = attr.ib(kw_only=True)
    data = attr.ib(kw_only=True)


class BaseBankRating:

    def calculate(self, request) -> BankRatingResultData:
        raise ValueError("Требует реализации")
