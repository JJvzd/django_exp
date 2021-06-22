class OrganizationForm:
    TYPE_OOO = 'OOO'
    TYPE_ZAO = 'ZAO'
    TYPE_OAO = 'OAO'
    TYPE_AO = 'AO'
    TYPE_PAO = 'PAO'
    TYPE_MUP = 'MUP'
    TYPE_GUP = 'GUP'
    TYPE_OTHER = 'OTHER'
    TYPE_FGUP = 'FGUP'

    CHOICES = (
        (TYPE_OOO, 'ООО'),
        (TYPE_ZAO, 'ЗАО'),
        (TYPE_OAO, 'ОАО'),
        (TYPE_AO, "АО"),
        (TYPE_PAO, "ПАО"),
        (TYPE_MUP, "МУП"),
        (TYPE_GUP, "ГУП"),
        (TYPE_FGUP, 'ФГУП'),

        (TYPE_OTHER, "Другие")
    )


class FederalLaw:
    LAW_44 = 'fz44'
    LAW_223 = 'fz223'
    LAW_185 = 'fz185'
    LAW_615 = 'fz615'
    LAW_207 = 'fz207'
    LAW_94 = 'fz94'
    LAW_EMPTY = ''

    CHOICES = (
        (LAW_EMPTY, 'Не выбрано'),
        (LAW_44, '44-ФЗ'),
        (LAW_223, '223-ФЗ'),
        (LAW_185, '185-ФЗ'),
        (LAW_615, '615-ПП'),
        (LAW_207, '207-ПП'),
        (LAW_94, '94-ФЗ'),
    )


class TaxationType:
    TYPE_OSN = 'OSN'
    TYPE_USN = 'USN'
    TYPE_ENVD = 'ENVD'
    TYPE_PSN = 'PSN'
    TYPE_ESHN = 'ESHN'

    CHOICES = (
        (TYPE_OSN, "ОСН"),
        (TYPE_USN, "УСН"),
        (TYPE_ENVD, "ЕНВД"),
        (TYPE_PSN, "ПСН"),
        (TYPE_ESHN, "ЕСХН"),
    )


class Target:
    EXECUTION = 'execution'
    PARTICIPANT = 'participant'
    AVANS_RETURN = 'avans_return'
    WARRANTY = 'warranty'
    CHOICES = (
        (EXECUTION, 'На исполнение'),
        (PARTICIPANT, 'На участие'),
        (AVANS_RETURN, 'Возврат аванса'),
        (WARRANTY, 'Гарантийные обязательства'),
    )

    TARGETS_ABBREVIATION = {
        EXECUTION: 'И',
        PARTICIPANT: 'У',
        AVANS_RETURN: 'ВА',
        WARRANTY: 'ГО',
    }

    POSSIBLE_COMBINATIONS = [
        {EXECUTION},
        {EXECUTION, AVANS_RETURN},
        {EXECUTION, WARRANTY},
        {EXECUTION, AVANS_RETURN, WARRANTY},
        {PARTICIPANT},
        {PARTICIPANT, AVANS_RETURN},
        {PARTICIPANT, WARRANTY},
        {PARTICIPANT, AVANS_RETURN, WARRANTY},
        {AVANS_RETURN},
        {WARRANTY},
    ]


class DeliveryType:
    DELIVERY_MAIL_RUS = 1
    DELIVERY_PICKUP = 2
    DELIVERY_COURIER = 3
    DELIVERY_CHOICES = (
        (DELIVERY_MAIL_RUS, 'Почта России'),
        (DELIVERY_PICKUP, 'Самовывоз'),
        (DELIVERY_COURIER, 'Курьерская служба')
    )