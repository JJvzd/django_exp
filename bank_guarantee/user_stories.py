from base_request.exceptions import RequestWrongAccessException
from cabinet.constants.constants import Target

from utils.helpers import ValidationErrors
from utils.re_patterns import EMAIL_PATTERN, PHONE_PATTERN, EMAIL_STRING_PATTERN


def can_view_request(request, user):
    from permissions.logic.bank_guarantee import CanViewRequest
    return CanViewRequest().execute(user, request=request)


def change_request_archive_state(request, archive, user) -> bool:
    assert archive in [True, False]
    from permissions.logic.bank_guarantee import CanSendRequestToArchive
    if CanSendRequestToArchive().execute(user, request=request):
        request.in_archive = archive
        request.save(update_fields=['in_archive'])
        return True
    raise RequestWrongAccessException


def validate_request(request) -> dict:
    errors = ValidationErrors()
    rules = {}
    if not request.agree:
        errors.add_error('agree', 'Отсутствует согласие на обработку персональных данных')
        rules['agree'] =\
            "val => !!val || 'Отсутствует согласие на обработку персональных данных'"

    if not request.tender_id:
        errors.add_common_error('Не указан конкурс')
        rules['tender_id'] = "val => !!val || 'Не указан конкурс'"

    if not request.tender.notification_id and request.contract_type != 'commercial':
        errors.add_error('tender.notification_id', 'Не указан номер извещения')
        rules['notification_id'] = "val => !!val || 'Не указан номер извещения'"

    if not request.required_amount:
        errors.add_error('required_amount', 'Не указана требуемая сумма')
        rules['required_amount'] = "val => !!val || 'Не указана требуемая сумма"

    if not request.interval_from:
        errors.add_error('interval_to', 'Не указана дата окончания')
        rules['interval_to'] = "val => !!val || 'Не указана дата окончания'"

    if not request.interval_to:
        errors.add_error('interval_from', 'Не указана дата выдачи')
        rules['interval_from'] = "val => !!val || 'Не указана дата выдачи'"

    if request.interval and request.interval < 0:
        errors.add_error('interval', 'Недопустимое количество дней')
        rules['interval'] = "val => val < 0 || 'Недопустимое количество дней'"

    if not request.targets:
        errors.add_error('targets', 'Не указан тип БГ')
        rules['targets'] = "val => val.length !== 0 || 'Не указан тип БГ'"

    if not request.suggested_price_amount:
        errors.add_error(
            'suggested_price_amount', 'Не указана предложенная цена контракта'
        )
        rules[
            'suggested_price_amount'] =\
            "val => val != 0 || 'Не указана предложенная цена контракта'," \
            " val => !!val || 'Не указана предложенная цена контракта'"

    if not request.final_date:
        errors.add_error('final_date', 'Не указан крайний срок выдачи')
        rules['final_date'] = "val => !!val || 'Не указан крайний срок выдачи'"

    if not request.tender.federal_law and request.contract_type != 'commercial':
        errors.add_error('tender.federal_law', 'Не указан ФЗ')
        rules['federal_law'] = "val => !!val || 'Не указан ФЗ'"

    if not request.tender.publish_date:
        errors.add_error('tender.publish_date', 'Не указана дата размещения извещения')
        rules['publish_date'] = "val => !!val || 'Не указана дата размещения извещения'"

    if not request.tender.subject:
        errors.add_error('tender.subject', 'Не указан предмет контракта')
        rules['subject'] = "val => !!val || 'Не указан предмет контракта'"

    if not request.tender.beneficiary_name:
        errors.add_error('tender.beneficiary_name', 'Не указано наименование заказчика')
        rules['beneficiary_name'] = "val => !!val || 'Не указано наименование заказчика'"

    if not request.tender.beneficiary_address:
        errors.add_error('tender.beneficiary_address', 'Не указан адрес заказчика')
        rules['beneficiary_address'] = "val => !!val || 'Не указан адрес заказчика'"

    if not request.tender.beneficiary_address:
        errors.add_error('tender.beneficiary_inn', 'Не указан ИНН заказчика')
        rules['beneficiary_inn'] = "val => !!val || 'Не указан ИНН заказчика'"

    if not request.tender.beneficiary_kpp:
        errors.add_error('tender.beneficiary_kpp', 'Не указан КПП заказчика')
        rules['beneficiary_kpp'] = "val => !!val || 'Не указан КПП заказчика'"

    if not request.tender.beneficiary_ogrn:
        errors.add_error('tender.beneficiary_ogrn', 'Не указан ОГРН заказчика')
        rules['beneficiary_ogrn'] = "val => !!val || 'Не указан ОГРН заказчика'"

    if request.tender.has_prepayment:
        if not request.tender.prepayment_amount:
            errors.add_error(
                'tender.prepayment_amount', 'Не указана сумма аванса контракта'
            )
            rules['prepayment_amount'] =\
                "val => !!val || 'Не указана сумма аванса контракта'"

    if not request.contract_type:
        errors.add_error(
            'contract_type', 'Не указано контракт государственный или муниципальный'
        )
        rules['contract_type'] =\
            "val => !!val || 'Не указано контракт государственный или муниципальный'"

    if Target.PARTICIPANT in request.targets:
        if not request.procuring_amount:
            errors.add_error(
                'procuring_amount', 'Не указан размер обеспечения исполнения контракта'
            )
            rules['procuring_amount'] =\
                "val => !!val || 'Не указан размер обеспечения исполнения контракта'"

    if Target.AVANS_RETURN in request.targets:
        if not request.prepaid_expense_amount:
            errors.add_error('prepaid_expense_amount', 'Не указан размер аванса')
            rules['prepaid_expense_amount'] = "val => !!val || 'Не указан размер аванса'"

    if Target.WARRANTY in request.targets:
        if not request.warranty_from:
            errors.add_error(
                'warranty_from', 'Не указано начало гарантийных обязательств'
            )
            rules['warranty_from'] = \
                "val => !!val || 'Не указано начало гарантийных обязательств'"

    if Target.WARRANTY in request.targets:
        if not request.warranty_to:
            errors.add_error(
                'warranty_to', 'Не указан конец гарантийных обязательств'
            )
            rules['warranty_to'] =\
                "val => !!val || 'Не указан конец гарантийных обязательств'"

    if not request.protocol_date:
        errors.add_error('request.protocol_date', 'Не указана дата протокола')
        rules['protocol_date'] = "val => !!val || 'Не указана дата протокола'"

    if not request.protocol_lot_number:
        errors.add_error('request.protocol_lot_number', 'Не указан номер лота')
        rules['protocol_lot_number'] = "val => !!val || 'Не указан номер лота'"

    if not request.creator_email:
        errors.add_error('request.creator_email', 'Не указан Email исполнителя')
        rules['creator_email'] =\
            "val => /{}/.test(val) ||" \
            " 'Не указан Email исполнителя'".format(EMAIL_STRING_PATTERN)

    if request.creator_email and not EMAIL_PATTERN.match(request.creator_email):
        errors.add_error('request.creator_email', 'Неверно указан Email исполнителя')
        rules['creator_email'] =\
            "val => /{}/.test(val) ||" \
            " 'Неверно указан Email исполнителя'".format(EMAIL_STRING_PATTERN)

    if not request.creator_phone:
        errors.add_error('request.creator_phone', 'Не указан Телефон исполнителя')
        rules['creator_phone'] = "val => !!val || 'Не указан Телефон исполнителя'"

    if request.creator_phone and not PHONE_PATTERN.match(request.creator_phone):
        errors.add_error('request.creator_phone', 'Неверно указан Телефон исполнителя')
        rules['creator_phone'] = "val => !!val || 'Неверно указан Телефон исполнителя'"

    if not request.creator_name:
        errors.add_error('request.creator_name', 'Неверно указано Имя исполнителя')
        rules['creator_name'] = "val => !!val || 'Неверно указано Имя исполнителя'"

    if not request.placement_way:
        errors.add_error(
            'placement_way', 'Не указан способ определения поставщика'
        )
        rules['placement_way'] = \
            "val => !!val || 'Не указан способ определения поставщика'"

    errors = errors.get_errors()
    if rules: errors['rules'] = rules

    return errors
