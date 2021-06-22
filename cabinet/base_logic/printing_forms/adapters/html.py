from django.template.loader import get_template

from cabinet.base_logic.printing_forms.adapters.base import (
    BasePrintFormGenerator, get_temp_path
)
from cabinet.base_logic.printing_forms.adapters.mixins import RequestPrintFormMixin


class HTMLPrintFormGenerator(RequestPrintFormMixin, BasePrintFormGenerator):

    def __init__(self, request, print_form):
        super(HTMLPrintFormGenerator, self).__init__(request, print_form)
        template_name = {
            'request': 'print_forms_templates/html/request.html',
            'anket': 'print_forms_templates/html/profile.html',
            'bo': 'print_forms_templates/html/accounting_report.html',
            'loan_request': 'print_forms_templates/html/request.html',
            'loan_questionnaire': 'print_forms_templates/html/profile.html',
            'loan_bo': 'print_forms_templates/html/loan_accounting_report.html',
        }.get(print_form.filename, None)
        self.set_template(get_template(template_name))
        self.set_data(self._get_context(request))

    def generate(self):
        result = self.template.render(self.data)
        result = result.replace('None', '')
        result = result.replace('False', '')
        temp_path = get_temp_path('.html')
        with open(temp_path, 'w', encoding='utf-8') as output_file:
            output_file.write(result)
        yield temp_path

class HTMLGenerator(HTMLPrintFormGenerator):

    def __init__(self, template_name, context):
        self.set_template(get_template(template_name))
        self.set_data(context)
