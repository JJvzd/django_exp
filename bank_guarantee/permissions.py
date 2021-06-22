from bank_guarantee.models import RequestStatus
from permissions.policy_algoritms import DenyUnlessPermit
from permissions.rules import PolicySet, Condition, Policy, Rule
from users.models import Role

permissions = [
    PolicySet(
        target=[Condition(
            attribute='action', value='can_action_send_offer', operation='Eq'
        )],
        alghoritm=DenyUnlessPermit(),
        policies=[Policy(
            description="Отправить предложение может обычный сотрудник банка или "
                        "ЛПР, если предложение в статусе",
            target=[
                Condition(
                    attribute='obj.status.code', value=[
                        RequestStatus.CODE_OFFER_CREATED,
                        RequestStatus.CODE_OFFER_BACK
                    ],
                    operation='In'
                )
            ],
            alghoritm=DenyUnlessPermit(),
            rules=[
                Rule(
                    target=[
                        Condition(
                            attribute='user.get_roles',
                            value=[
                                Role.BANK_DECISION_MAKER, Role.BANK, Role.GENERAL_BANK
                            ],
                            operation='AnyIn'
                        )
                    ],
                    condition=[
                        Condition(
                            attribute='obj.bank_id', value='user.client_id',
                            operation='ContextEq'
                        ),
                    ]
                )
            ]
        )]
    ),
    PolicySet(
        target=[Condition(
            attribute='action', value='can_action_create_offer', operation='Eq'
        )],
        alghoritm=DenyUnlessPermit(),
        policies=[Policy(
            description="Изменить предложение может обычный сотрудник банка, если заявка"
                        " находится в подходящих для этого статуса, андерайтер, если "
                        "предложение только создается, лпр, если предложение "
                        "уже создано и выпускающий, если предложение было отозвано "
                        "для изменения",
            target=[
                Condition(
                    attribute='obj.status.code', value=[
                        RequestStatus.CODE_REQUEST_CONFIRMED,
                        RequestStatus.CODE_OFFER_CREATED,
                        RequestStatus.CODE_OFFER_BACK,
                        RequestStatus.CODE_OFFER_SENT,
                    ],
                    operation='In'
                )
            ],
            alghoritm=DenyUnlessPermit(),
            rules=[
                Rule(
                    target=[
                        Condition(
                            attribute='user.get_roles', value=[Role.BANK_ISSUER],
                            operation='AnyIn'
                        )
                    ],
                    condition=[
                        Condition(
                            attribute='obj.status.code',
                            value=RequestStatus.CODE_OFFER_BACK, operation='Eq'
                        ),
                        Condition(
                            attribute='obj.assigned_id', value='user.id',
                            operation='ContextEq'
                        ),
                    ]
                ),
                Rule(
                    target=[
                        Condition(
                            attribute='user.get_roles', value=[Role.BANK_DECISION_MAKER],
                            operation='AnyIn'
                        )
                    ],
                    condition=[
                        Condition(attribute='obj.status.code',
                                  value=[
                                      RequestStatus.CODE_OFFER_CREATED,
                                      RequestStatus.CODE_OFFER_BACK
                                  ],
                                  operation='In'
                                  ),
                        Condition(
                            attribute='obj.assigned_id', value='user.id',
                            operation='ContextEq'
                        ),
                    ]
                ),
                Rule(
                    target=[
                        Condition(
                            attribute='user.get_roles', value=[Role.BANK_UNDERWRITER],
                            operation='AnyIn'
                        )
                    ],
                    condition=[
                        Condition(
                            attribute='obj.status.code',
                            value=[RequestStatus.CODE_OFFER_CREATED,
                                   RequestStatus.CODE_OFFER_BACK,
                                   RequestStatus.CODE_REQUEST_CONFIRMED],
                            operation='In'
                        ),
                        Condition(
                            attribute='obj.assigned_id', value='user.id',
                            operation='ContextEq'
                        ),
                    ]
                ),
                Rule(
                    target=[
                        Condition(
                            attribute='user.get_roles',
                            value=[Role.BANK, Role.GENERAL_BANK], operation='AnyIn'
                        )
                    ],
                    condition=[
                        Condition(
                            attribute='obj.bank_id', value='user.client_id',
                            operation='ContextEq'
                        ),
                    ]
                ),
            ]
        )]
    )
]
