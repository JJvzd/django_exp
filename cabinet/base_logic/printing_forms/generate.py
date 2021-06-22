import os

from django.conf import settings
from django.core.files import File
from django.utils.module_loading import import_string

from bank_guarantee.models import RequestPrintForm, Request, BankOfferDocumentCategory
from cabinet.base_logic.printing_forms.base import PrintForm
from files.models import BaseFile
from tender_loans.models import LoanPrintForm


class RequestPrintFormGenerator:

    def __init__(self):
        self.path_for_save = os.path.join(settings.MEDIA_ROOT, 'generated_print_forms')
        os.makedirs(self.path_for_save, exist_ok=True)
        self.adapters = {x[0]: import_string(x[1]) for x in PrintForm.TYPE_ADAPTERS}

    def get_enabled_print_forms(self, request):
        bank = request.bank
        if request.request_type == 'BG':
            model_print_form = RequestPrintForm
        elif request.request_type == 'LOAN':
            model_print_form = LoanPrintForm
        return model_print_form.objects.filter(
            banks__in=[bank],
            active=True,
            filename__isnull=False,
        ).distinct()

    def generate_print_form_download_name(self, file_name, request: Request,
                                          print_form) -> str:
        if print_form.download_name:
            extension = file_name.split('.')[-1]
            download_name = print_form.download_name
            context = {
                '{CLIENT_NAME}': request.client.short_name,
                '{CLIENT_INN}': request.client.inn,
                '{CLIENT_OGRN}': request.client.ogrn,
                '{REQUEST_ID}': request.id,
                '{REQUEST_NUMBER}': request.get_number(),
            }
            for key, value in context.items():
                download_name = download_name.replace(key, str(value))
                download_name = download_name.replace(key.lower(), str(value))
            return '%s.%s' % (download_name, extension)
        return ''

    def generate_print_form(self, request: Request, print_form):
        adapter = self.adapters.get(print_form.type, None)
        if adapter:

            adapter = adapter(request=request, print_form=print_form)
            request.requestdocument_set.filter(print_form=print_form).delete()
            files = adapter.generate()
            for temp_path in files:
                filename = os.path.basename(temp_path)

                file = BaseFile.objects.create(
                    author=request.client,
                    download_name=self.generate_print_form_download_name(
                        file_name=filename,
                        request=request,
                        print_form=print_form
                    )
                )
                file.file.save(
                    os.path.join(self.path_for_save, filename),
                    open(temp_path, 'rb'),
                    save=True
                )

                doc = request.requestdocument_set.create(
                    print_form=print_form,
                    file=file
                )
                try:
                    os.unlink(filename)
                except FileNotFoundError:
                    pass
                return doc

    def generate_print_forms(self, request: Request):
        print_forms = self.get_enabled_print_forms(request)
        for print_form in print_forms:
            self.generate_print_form(request, print_form)


class OfferPrintGenerator(RequestPrintFormGenerator):

    def _get_category(self, request, print_form):
        return BankOfferDocumentCategory.objects.filter(
            print_form=print_form, bank=request.bank
        ).first().category

    def _save_print_form(self, request, files, print_form):
        category = self._get_category(request, print_form)
        if category:
            request.offer.offerdocument_set.filter(
                category=category
            ).delete()

        for temp_path in files:
            filename = os.path.basename(temp_path)
            with open(temp_path, 'rb') as generated_file:
                file = BaseFile.objects.create(
                    author=request.client,
                    file=File(generated_file),
                    download_name=self.generate_print_form_download_name(
                        file_name=filename,
                        request=request,
                        print_form=print_form
                    )
                )

            if print_form.bankofferdocumentcategory_set.filter(
                bank=request.bank,
                category=category
            ).first().category.step == 1:
                request.offer.offerdocument_set.create(
                    file=file,
                    category=category,
                )
            else:
                request.offer.tempofferdoc_set.create(
                    print_form=print_form,
                    file=file,
                )

    def _generate(self, request, print_form):
        adapter = self.adapters.get(print_form.type, None)
        if adapter:
            adapter = adapter(request=request, print_form=print_form)
            return list(adapter.generate())
        return []

    def generate_print_form(self, request: Request, print_form):
        files = self._generate(request, print_form)
        self._save_print_form(request, files, print_form)

