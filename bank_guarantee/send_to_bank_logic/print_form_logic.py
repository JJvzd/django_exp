from bank_guarantee.models import RequestDocument, Request, RequestStatus
from cabinet.base_logic.printing_forms.generate import RequestPrintFormGenerator


class PrintFormsGenerator:
    @staticmethod
    def _copy_document(document: RequestDocument, request: Request):
        document.id = None
        document.request = request

        file = document.file
        file.id = None
        file.file.save(document.file.file.filename, document.file.file.open('rb'))
        file.save()

        document.file = file
        document.save()

    @classmethod
    def generate_print_forms(cls, base_request, requests_for_send):
        """ Герерация печатных форм
        Создает печатные формы для базовой заявки и копирует их в дочерние
        :param base_request: Базовая заявка
        :param requests_for_send: Дочерние заявки
        :return:
        """
        exclude_statuses_for_generate = [
            RequestStatus.CODE_CLIENT_SIGN, RequestStatus.CODE_SENT_REQUEST
        ]

        if base_request.status.code not in exclude_statuses_for_generate:
            base_request.generate_print_forms()

        # Крепим сгенерированные формы к остальным заявкам
        for request in requests_for_send:
            if base_request.status.code in exclude_statuses_for_generate:
                continue
            helper = RequestPrintFormGenerator()
            print_forms_for_copy = helper.get_enabled_print_forms(request)

            # получение печатных форм базовой заявки
            base_request_documents = base_request.requestdocument_set.filter(
                print_form__in=print_forms_for_copy
            )
            for doc in base_request_documents:
                cls._copy_document(doc, request)

            # печатные формы, отсутствующие в базовой заявке, но требуемые банком
            base_request_print_forms_id = base_request_documents.values_list(
                'print_form_id', flat=True
            )
            missing_print_forms = print_forms_for_copy.exclude(
                id__in=base_request_print_forms_id
            )

            for print_form in missing_print_forms:
                helper.generate_print_form(request, print_form)
