import os

from django.conf import settings
from docx import Document

from cabinet.base_logic.printing_forms.adapters.doc import DocBasePrintFormGenerator

PATH_TEST_DOC = os.path.join(settings.BASE_DIR, 'cabinet/tests/files/template_test.docx')


def test_print_form():
    template = DocBasePrintFormGenerator()
    template.set_template(PATH_TEST_DOC)
    for n in range(3):
        context = {'test': 'doc_test#{}'.format(n + 1)}
        template.set_data(context)
        for path in template.generate():
            doc = Document(path)
            os.remove(path)
            assert doc.paragraphs[0].text == context['test']
