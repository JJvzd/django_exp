from cabinet.base_logic.printing_forms.adapters.doc import (
    RequestDocBasePrintFormGenerator
)


class RIBConclusionForTH(RequestDocBasePrintFormGenerator):
    path = 'system_files/print_forms_templates/rib_th.docx'

    def __init__(self, request, print_form):
        self.request = request

    def get_result(self):
        return 0
