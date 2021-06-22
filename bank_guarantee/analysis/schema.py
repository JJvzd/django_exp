from datetime import datetime, date
from typing import List

import attr


@attr.s(auto_attribs=True)
class QuarterValue:
    code: int
    value: float


@attr.s(auto_attribs=True)
class Quarter:
    period: str
    values: List[QuarterValue]


@attr.s(auto_attribs=True)
class RatingResult:
    created: datetime
    data: dict
    score: str
    rating: str
    risk_level: str
    finance_state: str


@attr.s(auto_attribs=True)
class ContractsByLaw:
    count_created: int
    sum_created: float
    count_finished: int
    sum_finished: float


@attr.s(auto_attribs=True)
class ContractsInfo:
    period: str
    law_44fz: ContractsByLaw
    law_223fz: ContractsByLaw


@attr.s(auto_attribs=True)
class MaxContractPriceExperience:
    percent: int
    count: int


@attr.s(auto_attribs=True)
class ContractExperience:
    count_participant_in_contracts: int
    count_win_in_contracts: int
    statistic: List[ContractsInfo]
    max_contract_price_experience: List[MaxContractPriceExperience]


@attr.s(auto_attribs=True)
class BankGuarantee:
    amount: float
    date_from: date
    date_to: date
    bank: str
    beneficiary: str
    notification: str


@attr.s(auto_attribs=True)
class CourtInfo:
    total_sum_not_finished: float
    total_sum_finished: float
    data_not_finished: dict
    data_finished: dict


@attr.s(auto_attribs=True)
class ProfessionalConclusionResult:
    company_name: str
    company_inn: str
    company_region: str

    beneficiary_region: str
    beneficiary_inn_region: str
    federal_law: str

    required_amount: float
    suggested_price: float
    price: float
    interval: int

    last_quarter: Quarter
    year_quarter: Quarter
    rating: RatingResult
    contracts: ContractExperience
    bank_guarantees_in_work: List[BankGuarantee]
    bank_guarantees_finished: List[BankGuarantee]
    tax_system: str
    contract_interval: int
    fssp: str
    starting_price: float
    court_info: CourtInfo
