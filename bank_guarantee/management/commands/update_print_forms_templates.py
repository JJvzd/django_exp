from django.core.management import BaseCommand

from bank_guarantee.models import RequestPrintForm, OfferPrintForm

from cabinet.base_logic.printing_forms.base import PrintForm
from tender_loans.models import LoanPrintForm


class Command(BaseCommand):
    help = 'Обновление шаблонов печатных форм'

    def handle(self, *args, **options):
        maps = {
            PrintForm.TYPE_DOC: 'docx',
            PrintForm.TYPE_HTML: 'html',
            PrintForm.TYPE_SF_AGREEMENT: 'docx',
            PrintForm.TYPE_SGB_EXCEL: 'xlsx',
            PrintForm.TYPE_INBANK_BG: 'docx',
            PrintForm.TYPE_SGB_BG: 'docx',
            PrintForm.TYPE_SGB_ADDITIONAL8: 'docx',
            PrintForm.TYPE_SGB_ADDITIONAL81: 'docx',
            PrintForm.TYPE_METALL_INVEST_ANKETA: 'docx',
            PrintForm.TYPE_METALL_INVEST_EXCEL: 'xlsx',
            PrintForm.TYPE_METALL_INVEST_CONCLUSION: 'docx',
            PrintForm.TYPE_METALL_INVEST_BENEFICIARS: 'docx',
            PrintForm.TYPE_VORONEJ_EXCEL: 'xlsx',
            PrintForm.TYPE_RTBK_ANKETA_EXCEL: 'xlsx',
            PrintForm.TYPE_RTBK_GUARANTOR_EXCEL: 'xlsx',
            PrintForm.TYPE_RIB_TH: 'docx',
            PrintForm.TYPE_RIB: 'docx',
            PrintForm.TYPE_MOSCOMBANK_EXECUTION: 'docx',
            PrintForm.TYPE_MOSCOMBANK_CONCLUSION: 'xlsx',
            PrintForm.TYPE_EAST_EXCEL: 'xlsx',
            PrintForm.TYPE_EAST_CONCLUSION: 'docx',
            PrintForm.TYPE_SPB_GUARANTEE: 'docx',
            PrintForm.TYPE_SPB_CONCLUSION: 'xlsx',
            PrintForm.TYPE_SPB_EXTRADITION_DECISION: 'xlsx',
            PrintForm.TYPE_INBANK_CONCLUSION: 'xlsx',
        }

        for print_form in RequestPrintForm.objects.all():
            for form_type, ext in maps.items():
                if print_form.type == form_type:
                    if print_form.filename and not print_form.filename.endswith(ext):
                        print_form.filename = '%s.%s' % (print_form.filename, ext)
                        print_form.save()

        for print_form in OfferPrintForm.objects.all():
            for form_type, ext in maps.items():
                if print_form.type == form_type:
                    if print_form.filename and not print_form.filename.endswith(ext):
                        print_form.filename = '%s.%s' % (print_form.filename, ext)
                        print_form.save()

        for print_form in LoanPrintForm.objects.all():
            for form_type, ext in maps.items():
                if print_form.type == form_type:
                    if print_form.filename and not print_form.filename.endswith(ext):
                        print_form.filename = '%s.%s' % (print_form.filename, ext)
                        print_form.save()

