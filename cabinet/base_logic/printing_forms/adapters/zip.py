import zipfile
from base_request.models import AbstractRequest
from cabinet.base_logic.printing_forms.adapters.base import get_temp_path
from files.models import BaseFile


class ZipPrintFormGenerator:

    def __init__(self, request: AbstractRequest, print_form):
        self.request = request
        self.print_form = print_form

    def generate(self):
        yield None


class ZipAbsolutGenerator(ZipPrintFormGenerator):

    def generate(self):
        from bank_guarantee.bank_integrations.absolut_bank.absolut_bank import SendRequest
        helper = SendRequest()
        files_ids = self.request.requestdocument_set.filter(
            category_id__in=helper.all_documents_map.get(self.print_form.filename)
        ).values_list(
            'file',
            flat=True
        )
        path = get_temp_path('.zip')
        with zipfile.ZipFile(path, 'w') as my_zip:
            for file in BaseFile.objects.filter(id__in=files_ids):
                my_zip.write(file.file.path, file.get_download_name())
        yield path


class ZipBKSGenerator(ZipPrintFormGenerator):

    def generate(self):
        from bank_guarantee.bank_integrations.bks_bank.bank_api import SendRequest
        helper = SendRequest()
        files_ids = self.request.requestdocument_set.filter(
            category_id__in=helper.all_documents_map.get(self.print_form.filename)
        ).values_list(
            'file',
            flat=True
        )
        path = get_temp_path('.zip')
        with zipfile.ZipFile(path, 'w') as my_zip:
            for file in BaseFile.objects.filter(id__in=files_ids):
                my_zip.write(file.file.path, file.get_download_name())
        yield path
