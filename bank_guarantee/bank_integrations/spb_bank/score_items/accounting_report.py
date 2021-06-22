import logging

from .base import ScoreItemValidator, BaseScoreItem

logger = logging.getLogger('django')


class AccountingReportFormula1(BaseScoreItem):
    score_map = [
        ScoreItemValidator(to_value=0.7, score=0),
        ScoreItemValidator(from_value=0.7, to_value=0.9, score=1),
        ScoreItemValidator(from_value=0.9, to_value=1.5, score=2),
        ScoreItemValidator(from_value=1.5, score=3),
    ]

    def get_value(self):
        return self.data.year_data.v2110 / self.data.tender_start_price


class AccountingReportFormula2(BaseScoreItem):
    score_map = [
        ScoreItemValidator(from_value=-9999, to_value=0, score=0),
        ScoreItemValidator(from_value=0, to_value=0.1, score=1),
        ScoreItemValidator(from_value=0.1, to_value=0.2, score=2),
        ScoreItemValidator(from_value=0.2, score=3),
    ]

    def get_value(self):
        return (self.data.last_quarter_data.v2300 +
                self.data.last_quarter_data.v2330 -
                self.data.last_quarter_data.v2320) / self.data.last_quarter_data.v2110


class AccountingReportFormula3(BaseScoreItem):
    score_map = [
        ScoreItemValidator(from_value=6, to_value=9999, score=0),
        ScoreItemValidator(from_value=4, to_value=6, score=1),
        ScoreItemValidator(from_value=2, to_value=4, score=2),
        ScoreItemValidator(from_value=-9999, to_value=2, score=3),
    ]

    def get_value(self):
        return (self.data.last_quarter_data.v1410 + self.data.last_quarter_data.v1510)\
               / (self.data.last_quarter_data.v2300 +
                  self.data.last_quarter_data.v2330 -
                  self.data.last_quarter_data.v2320)


class AccountingReportFormula4(BaseScoreItem):
    score_map = [
        ScoreItemValidator(from_value=6, to_value=9999, score=0),
        ScoreItemValidator(from_value=4, to_value=6, score=1),
        ScoreItemValidator(from_value=2, to_value=4, score=2),
        ScoreItemValidator(from_value=-9999, to_value=2, score=3),
    ]

    def get_value(self):
        return (self.data.last_quarter_data.v1410 + self.data.last_quarter_data.v1510)\
               / self.data.last_quarter_data.v1300


class AccountingReportFormula5(BaseScoreItem):
    score_map = [
        ScoreItemValidator(from_value=0, to_value=0.5, score=0),
        ScoreItemValidator(from_value=0.5, to_value=1, score=1),
        ScoreItemValidator(from_value=1, to_value=1.5, score=2),
        ScoreItemValidator(from_value=1.5, to_value=9999, score=3),
    ]

    def get_value(self):
        return self.data.last_quarter_data.v1200 / self.data.last_quarter_data.v1500


class AccountingReportFormula6(BaseScoreItem):
    score_map = [
        ScoreItemValidator(from_value=-9999, to_value=0, score=0),
        ScoreItemValidator(from_value=0, to_value=0.05, score=1),
        ScoreItemValidator(from_value=0.05, to_value=0.1, score=2),
        ScoreItemValidator(from_value=0.1, to_value=9999, score=3),
    ]

    def get_value(self):
        return (self.data.last_quarter_data.v1300 - self.data.last_quarter_data.v1100)\
               / self.data.last_quarter_data.v1200