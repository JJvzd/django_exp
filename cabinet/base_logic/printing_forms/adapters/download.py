import shutil

from base_request.logic.request_log import RequestLogger
from base_request.models import AbstractRequest
from cabinet.base_logic.printing_forms.adapters.base import get_temp_path
from conclusions_app.conclusions.common import EGRULConclusion
from conclusions_app.conclusions_logic import ConclusionsLogic
from external_api.zakupki_html import ZakupkiHTML
from settings.configs.banks import BankCode


class DownloadPrintFormGenerator:

    def __init__(self, request: AbstractRequest, print_form):
        self.request = request
        self.print_form = print_form

    def generate(self):
        yield None


class ContractDraftFromZakupki(DownloadPrintFormGenerator):

    def generate(self):
        try:
            api = ZakupkiHTML()
            yield api.get_draft_contract(self.request)
        except Exception as error:
            pass


class ProtocolZakupki(DownloadPrintFormGenerator):

    def generate(self):
        try:
            api = ZakupkiHTML()
            yield api.get_protocol(self.request)
        except Exception as error:
            pass


class FromBankGenerator(DownloadPrintFormGenerator):
    bank_code = ''

    def get_file(self):
        return None

    def generate(self):
        try:
            external_request = self.request.externalrequest_set.filter(
                bank__code=self.bank_code
            ).first()
            external_id = external_request and external_request.external_id
            if external_id is None:
                external_id = self.request.bank_integration.init_request(self.request)
            if external_id:
                file = self.get_file()
                if file:
                    return [file, ]
        except Exception as error:
            RequestLogger.log(self.request, str(error))
        return []


class MoscombankAnketa(FromBankGenerator):
    bank_code = BankCode.CODE_MOSCOMBANK

    def get_file(self):
        path = self.request.bank_integration.api.download_profile(self.request)
        if path:
            return path


class EgrulAdapter(DownloadPrintFormGenerator):

    def generate(self):
        path = ConclusionsLogic.get_conclusion_result(
            client=self.request.client,
            conclusion=EGRULConclusion
        ).file[1:]
        temp_path = get_temp_path('.pdf')
        shutil.copyfile(path, temp_path)
        yield temp_path


class AbsolutBankGenerator(FromBankGenerator):
    bank_code = BankCode.CODE_ABSOLUT

    def get_file(self):
        from bank_guarantee.bank_integrations.absolut_bank.absolut_bank import SendRequest
        helper = SendRequest()
        path = helper.get_file_for_type(self.request, self.print_form.filename)
        if path:
            return path


class BKSPrintFormGenerator(FromBankGenerator):
    bank_code = BankCode.CODE_BKS_BANK

    def get_file(self):
        from bank_guarantee.bank_integrations.bks_bank.bank_api import SendRequest
        helper = SendRequest()
        path = helper.get_file_for_type(self.request, self.print_form.filename)
        if path:
            return path
