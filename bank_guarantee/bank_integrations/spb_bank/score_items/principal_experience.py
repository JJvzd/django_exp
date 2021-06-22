from .base import BaseScoreItem, ScoreItemValidator


class PrincipalExperienceFormula1(BaseScoreItem):
    """ Возраст Принципала """
    score_map = [
        ScoreItemValidator(from_value=3, to_value=9999, score=3),
        ScoreItemValidator(from_value=2, to_value=3, score=2),
        ScoreItemValidator(from_value=1, to_value=2, score=1),
        ScoreItemValidator(from_value=0.5, to_value=1, score=0),
    ]

    def get_value(self):
        return self.data.company_age_months / 12


class PrincipalExperienceFormula2(BaseScoreItem):
    """
    Количество исполненных контрактов в рамках 44-ФЗ, 223-ФЗ (за последние 3 года)
    """
    score_map = [
        ScoreItemValidator(from_value=4, to_value=999999, score=3),
        ScoreItemValidator(from_value=2, to_value=4, score=2),
        ScoreItemValidator(from_value=1, to_value=2, score=1),
        ScoreItemValidator(from_value=0, to_value=1, score=0),
    ]

    def get_value(self):
        return self.data.tender_counts_total


class PrincipalExperienceFormula3(BaseScoreItem):
    """
    Количество исполненных сопоставимых контрактов 223-ФЗ/44-ФЗ за 3 последних года
    (стоимостью более либо равной контракту, по которому испрашивается гарантия)
    """
    score_map = [
        ScoreItemValidator(from_value=2, to_value=99999999, score=3),
        ScoreItemValidator(from_value=1, to_value=2, score=2),
        ScoreItemValidator(from_value=0, to_value=1, score=0),
    ]

    def get_value(self):
        return self.data.number_of_similar_contracts
