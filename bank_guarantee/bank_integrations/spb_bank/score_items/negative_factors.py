from .base import ScoreItemValidator, BaseScoreItem


class NegativeFactorFormula1(BaseScoreItem):
    score_map = [
        ScoreItemValidator(from_value=0, to_value=2, score=0),
        ScoreItemValidator(from_value=2, to_value=999, score=-0.5),
    ]

    def get_value(self):
        return self.data.another_company_data.number_changed_beneficiary_last_year


class NegativeFactorFormula2(BaseScoreItem):
    default_score = 0
    score_map = [
        ScoreItemValidator(check_bool=True, score=-1),
    ]

    def get_value(self):
        data = self.data.another_company_data
        return data.principal_has_share_in_stop_factors_companies


class NegativeFactorFormula3(BaseScoreItem):
    default_score = 0
    score_map = [
        ScoreItemValidator(check_bool=True, score=-1),
    ]

    def get_value(self):
        return self.data.another_company_data.has_large_debt


class NegativeFactorFormula4(BaseScoreItem):
    default_score = 0
    score_map = [
        ScoreItemValidator(check_bool=True, score=-1),
    ]

    def get_value(self):
        return (self.data.year_data.v1600 - (
                    self.data.year_data.v1400 +
                    self.data.year_data.v1500 -
                    self.data.year_data.v1530)
                ) < self.data.year_data.v1300
