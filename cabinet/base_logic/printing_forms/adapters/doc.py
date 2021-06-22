import copy
import logging
import os

from django.conf import settings

import jinja2
from docxtpl import DocxTemplate
from jinja2 import TemplateSyntaxError, UndefinedError

from bank_guarantee.models import Request
from base_request.logic.request_log import RequestLogger
from base_request.models import AbstractRequest
from cabinet.base_logic.printing_forms.adapters.base import (
    BasePrintFormGenerator, get_temp_path
)
from cabinet.base_logic.printing_forms.adapters.jinja_custom_filter import (
    Jinja_custom_filter
)
from cabinet.base_logic.printing_forms.adapters.mixins import RequestPrintFormMixin
from cabinet.constants.constants import Target, FederalLaw

logger = logging.getLogger('django')


def silent_none(value):
    if value is None:
        return ''
    return value


class DocBasePrintFormGenerator(BasePrintFormGenerator):

    def __init__(self):
        super(DocBasePrintFormGenerator, self).__init__()
        self.extension = '.docx'

    def _get_jinja_env(self):
        jcm = Jinja_custom_filter()
        jinja_env = jinja2.Environment()
        jinja_env.finalize = silent_none
        for key, value in jcm.dict_filter.items():
            jinja_env.filters[key] = value
        return jinja_env

    def _render_and_save_doc(self, path_to_save):
        word = DocxTemplate(self.template)
        try:
            word.render(self.data, self._get_jinja_env())
        except Exception as error:
            if hasattr(self, 'request'):
                RequestLogger.log(self.request, 'переделать шаблон %s/nОшибка: %s' % (
                    self.template, error
                ))
            if settings.DEBUG:
                raise error
        word.save(path_to_save)

    def generate(self):
        if self.template:
            temp_path = get_temp_path(self.extension)
            self._render_and_save_doc(temp_path)
            yield temp_path


class RequestDocBasePrintFormGenerator(RequestPrintFormMixin, DocBasePrintFormGenerator):

    def __init__(self, request: AbstractRequest, print_form):
        super(RequestDocBasePrintFormGenerator, self).__init__()
        self.request = request
        self.print_form = print_form
        self.data = self._get_context(request)
        template = print_form.get_template(request=request, bank=request.bank)
        if template:
            self.set_template(os.path.join(
                settings.BASE_DIR, template
            ))


class MetallInvestProfilePrintForm(RequestDocBasePrintFormGenerator):

    def __init__(self, request, print_form):
        super(MetallInvestProfilePrintForm, self).__init__(request, print_form)
        template = {
            True: 'metall_invest_anketa_ul.docx',
            False: 'metall_invest_anketa_ip.docx',
        }.get(request.client.is_organization)
        self.set_template(os.path.join(
            settings.BASE_DIR, 'system_files/print_forms_templates/',
            template
        ))


class MosComBankExecutionPrintForm(RequestDocBasePrintFormGenerator):

    def __init__(self, *args, **kwargs):
        super(MosComBankExecutionPrintForm, self).__init__(*args, **kwargs)
        template = None
        federal_law = self.request.tender.federal_law
        fz_185_615 = [FederalLaw.LAW_185, FederalLaw.LAW_615]
        targets = self.request.targets
        if federal_law == FederalLaw.LAW_44 and Target.WARRANTY in targets:
            template = 'moscombank_warranty_44fz.docx'
        if federal_law == FederalLaw.LAW_223 and Target.WARRANTY in targets:
            template = 'moscombank_warranty_223fz.docx'

        if federal_law == FederalLaw.LAW_44 and Target.EXECUTION in targets:
            template = 'moscombank_execution_44fz.docx'

        if federal_law == FederalLaw.LAW_223 and Target.EXECUTION in targets:
            template = 'moscombank_execution_223fz.docx'

        if federal_law in fz_185_615 and Target.EXECUTION in targets:
            template = 'moscombank_execution_185fz.docx'

        if federal_law == FederalLaw.LAW_44 and Target.EXECUTION in targets and \
                Target.WARRANTY in targets:
            template = 'moscombank_execution_and_warranty_44fz.docx'

        if federal_law == FederalLaw.LAW_223 and Target.EXECUTION in targets and \
                Target.WARRANTY in targets:
            template = 'moscombank_execution_and_warranty_223fz.docx'

        if federal_law == FederalLaw.LAW_44 and Target.PARTICIPANT in targets:
            template = 'moscombank_participation_44fz.docx'

        if federal_law == FederalLaw.LAW_223 and Target.PARTICIPANT in targets:
            template = 'moscombank_participation_223fz.docx'

        if federal_law in fz_185_615 and Target.PARTICIPANT in targets:
            template = 'moscombank_participation_185fz.docx'

        if template:
            self.set_template(os.path.join(
                settings.BASE_DIR, 'system_files/print_forms_templates/',
                template
            ))
        else:
            self.set_template(None)


class InbankRequestPrintForm(RequestDocBasePrintFormGenerator):

    def __init__(self, request: Request, print_form):
        super(InbankRequestPrintForm, self).__init__(request, print_form)
        template = None
        if Target.PARTICIPANT in request.targets:
            if request.tender.federal_law == FederalLaw.LAW_223:
                template = 'inbank_participant_223fz.docx'
            if request.tender.federal_law == FederalLaw.LAW_44:
                template = 'inbank_participant_44fz.docx'
        elif Target.WARRANTY in request.targets:
            if request.tender.federal_law == FederalLaw.LAW_223:
                template = 'inbank_warranty_223fz.docx'
            if request.tender.federal_law == FederalLaw.LAW_44:
                template = 'inbank_warranty_44fz.docx'
        elif Target.EXECUTION in request.targets:
            if request.tender.federal_law == FederalLaw.LAW_223:
                template = 'inbank_execute_223fz.docx'
            if request.tender.federal_law == FederalLaw.LAW_44:
                template = 'inbank_execute_44fz.docx'
        if template:
            self.set_template(os.path.join(
                settings.BASE_DIR, 'system_files/print_forms_templates/',
                template
            ))
        else:
            self.set_template(None)


class InbankRequestPrintFormOffer(InbankRequestPrintForm):

    def __init__(self, request: Request, print_form):
        super().__init__(request, print_form)
        temp = self.template.split('.') if self.template else self.template
        self.template = ''.join([temp[0], '_offer', '.' + temp[1]])


class RIBRequestPrintForm(RequestDocBasePrintFormGenerator):

    def __init__(self, *args, **kwargs):
        super(RIBRequestPrintForm, self).__init__(*args, **kwargs)
        template = None
        federal_law = self.request.tender.federal_law
        targets = self.request.targets
        if federal_law == FederalLaw.LAW_44 and Target.EXECUTION in targets:
            template = 'rib_fz44_contract.docx'

        if federal_law == FederalLaw.LAW_223 and Target.EXECUTION in targets:
            template = 'rib_fz223_contract.docx'

        if federal_law == FederalLaw.LAW_615 and Target.EXECUTION in targets:
            template = 'rib_fz615_contract.docx'

        if federal_law == FederalLaw.LAW_44 and Target.PARTICIPANT in targets:
            template = 'rib_fz44_request.docx'

        if federal_law == FederalLaw.LAW_223 and Target.PARTICIPANT in targets:
            template = 'rib_fz223_request.docx'

        if template:
            self.set_template(os.path.join(
                settings.BASE_DIR, 'system_files/print_forms_templates/',
                template
            ))
        else:
            self.set_template(None)


class SGBBGExcelPrintForm(RequestDocBasePrintFormGenerator):
    pass


class SGBAdditional8ExcelPrintForm(RequestDocBasePrintFormGenerator):
    pass


class SGBAdditional81ExcelPrintForm(RequestDocBasePrintFormGenerator):
    pass


class MetallInvestConclusionPrintForm(RequestDocBasePrintFormGenerator):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        template = None

        if Target.EXECUTION in self.request.targets:
            template = 'metall_invest_execution.docx'

        if Target.PARTICIPANT in self.request.targets:
            template = 'metall_invest_participation.docx'

        if template:
            self.set_template(os.path.join(
                settings.BASE_DIR, 'system_files/print_forms_templates/',
                template
            ))
        else:
            self.set_template(None)


class MetallInvestBeneficiarsPrintForm(RequestDocBasePrintFormGenerator):

    def generate(self):
        if self.template:
            for beneficiar in self.data['anketa'].beneficiars_over_25:
                temp_path = get_temp_path(self.extension)
                self.update_data_values('ben', beneficiar)
                self._render_and_save_doc(temp_path)
                yield temp_path


class SFAssigmentPrintForm(RequestDocBasePrintFormGenerator):

    def _render_and_save_doc(self, path_to_save, data=None):
        if not data:
            data = self.data
        word = DocxTemplate(self.template)
        try:
            word.render(data, self._get_jinja_env())
        except (UndefinedError, TemplateSyntaxError) as error:
            logger.warning(self.__class__)
            logger.warning('переделать шаблон %s/nОшибка: %s' % (self.template, error))
        word.save(path_to_save)

    def generate(self):
        if self.template:
            for ben in self.data['anketa'].beneficiars:
                data = copy.deepcopy(self.data)
                data['values'].update({
                    'ben': ben
                })
                temp_path = get_temp_path(self.extension)
                self._render_and_save_doc(temp_path, data=data)
                yield temp_path


class EastConclusionPrintForm(RequestDocBasePrintFormGenerator):
    pass


class SPBGuaranteePrintForm(RequestDocBasePrintFormGenerator):
    regions_lo = ['47']
    regions_msk = ['77', '97', '99']
    regions_klg = ['39']
    regions_spb = ['78']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        template = None

        if self.request.tender.federal_law == FederalLaw.LAW_44:
            if Target.EXECUTION in self.request.targets:
                template = 'spb_fz44_execution'
            elif Target.PARTICIPANT in self.request.targets:
                template = 'spb_fz44_tender'
            elif Target.WARRANTY in self.request.targets:
                template = 'spb_fz44_warranty'
        elif self.request.tender.federal_law == FederalLaw.LAW_223:
            if Target.EXECUTION in self.request.targets:
                template = 'spb_fz223_execution'
            elif Target.WARRANTY in self.request.targets:
                template = 'spb_fz223_warranty'
            elif Target.PARTICIPANT in self.request.targets:
                template = 'spb_fz223_tender'
            elif Target.AVANS_RETURN in self.request.targets:
                template = 'spb_fz223_return_avans'
        elif self.request.tender.federal_law in [FederalLaw.LAW_185, FederalLaw.LAW_615]:
            inn = str(self.request.tender.beneficiary_inn)[:2]
            kpp = (str(self.request.tender.beneficiary_kpp) or '  ')[:2]
            if inn in self.regions_lo or kpp in self.regions_lo:
                template = 'spb_fz615_lo'
            elif inn in self.regions_msk or kpp in self.regions_msk:
                template = 'spb_fz615_msk'
            elif inn in self.regions_klg or kpp in self.regions_klg:
                template = 'spb_fz615_klg'
            elif inn in self.regions_spb or kpp in self.regions_spb:
                template = 'spb_fz615_spb'
            else:
                template = 'spb_fz615'

        if template:
            self.set_template(os.path.join(
                settings.BASE_DIR,
                'system_files/print_forms_templates/',
                '%s.docx' % template
            ))
        else:
            self.set_template(None)
