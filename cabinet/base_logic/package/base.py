import json
import logging
from typing import List

from django.utils.module_loading import import_string

from clients.models import Bank, BankSettings, MFOSettings, BankCode, MFO
from settings.settings import TESTING
from utils.helpers import clone_base_file

logger = logging.getLogger('django')


class ValidateBlock:

    def __init__(self, class_name, params):
        self.class_name = class_name
        self.params = params

    @staticmethod
    def get_class(class_name):
        try:
            return import_string('cabinet.base_logic.package.functions.%s' % class_name)
        except ImportError:
            logger.warning('Не найден класс пакета %s' % class_name)
            return None

    def validate(self, request, bank):
        """
        :param AbstractRequest request: заявка
        :param Bank bank: банк
        :return: bool
        """
        package_class = self.get_class(self.class_name)
        if package_class:
            package_class = package_class('', self.params)
            return package_class.validate(request, bank)
        return False


class ConditionalBlock:
    def __init__(self, operator, blocks):
        self.operator = operator
        self.blocks = blocks

    def validate(self, request, bank):
        results = []
        for block in self.blocks:
            if block.get('operator'):
                c = ConditionalBlock(
                    block.get('operator'),
                    block.get('blocks')
                )
                results.append(c.validate(request, bank))
            else:
                b = ValidateBlock(
                    block.get('class'),
                    block.get('params')
                )
                results.append(b.validate(request, bank))
        if self.operator == 'AND':
            return all(results + [True])
        if self.operator == 'OR':
            return any(results)
        return True


class PackageLogic:

    def __init__(self, request, bank: Bank):
        self.request = request
        self.bank = bank

    def collect_required_document_categories(self) -> List[str]:
        categories_ids = []
        bank_documents = self.bank.package.filter(active=True, required=True)
        for bank_document in bank_documents:
            conditionals = json.loads(bank_document.conditionals)
            c = ConditionalBlock(
                conditionals.get('operator'),
                conditionals.get('blocks')
            )
            if not c.validate(self.request, self.bank):
                continue

            categories_ids.append(str(bank_document.document_type_id))
        return list(set(categories_ids))

    @classmethod
    def get_first_relevant_bank(cls, request):
        from cabinet.models import System
        if not TESTING and System.objects.first().one_package_documents:
            return Bank.objects.get(code=BankCode.CODE_INBANK)
        bank = None
        for bank_settings in BankSettings.objects.all().order_by('priority'):
            if bank_settings.credit_organization.package.count() > 0:
                return bank_settings.credit_organization
        return bank

    @classmethod
    def get_first_relevant_mfo(cls, request):
        from cabinet.models import System
        if not TESTING and System.objects.first().one_package_documents:
            return MFO.objects.get(code='simple_finance')
        bank = None
        for bank_settings in MFOSettings.objects.all().order_by('priority'):
            if bank_settings.credit_organization.package.count() > 0:
                return bank_settings.credit_organization
        return bank

    @classmethod
    def can_update_package(cls, request, force=False):
        """
        :param AbstractRequest request:
        :param force: bool
        :return: bool
        """
        empty_package = [None, '', 'no_package']
        if request.in_archive:
            return False
        if request.package_class in empty_package or \
                (force and request.status.code == 'draft'):
            return True
        return False

    @classmethod
    def __get_old_requests_for_fill_documents(cls, request):
        from bank_guarantee.models import Request
        return Request.objects.filter(client_id=request.client_id).exclude(
            id=request.id
        ).order_by('-created_date')[:10]

    @classmethod
    def fill_documents_from_old_requests(cls, request):
        from bank_guarantee.models import Request, DocumentLinkToPerson
        if isinstance(request, Request):
            if request.requestdocument_set.count() == 0:
                categories = request.package_categories.split(',')
                old_requests = cls.__get_old_requests_for_fill_documents(request)
                docs = {}
                for category_id in categories:
                    if category_id not in docs.keys() and category_id:
                        for r in old_requests:
                            old_documents = r.requestdocument_set.filter(
                                category_id=category_id
                            )
                            if old_documents.first():
                                docs[category_id] = old_documents
                                break
                for category_id, old_documents in docs.items():
                    for old_doc in old_documents:
                        new_doc = request.requestdocument_set.create(
                            category_id=category_id,
                            file=clone_base_file(old_doc.file)
                        )
                        doc_link = None
                        if request.request_type == request.TYPE_BG:
                            doc_link = DocumentLinkToPerson.get_link(
                                old_doc.request_id,
                                category_id,
                                old_doc,
                            )
                        if doc_link:
                            DocumentLinkToPerson.set_link(
                                request.id,
                                category_id,
                                new_doc.id,
                                doc_link.person_id,
                            )

    @classmethod
    def save_empty_package(cls, request):
        from bank_guarantee.models import Request
        from tender_loans.models import LoanRequest
        if isinstance(request, Request):
            Request.objects.filter(id=request.id).update(
                package_class=None, package_categories=''
            )
        else:
            LoanRequest.objects.filter(id=request.id).update(
                package_class=None, package_categories=''
            )

    @classmethod
    def commit_package(cls, request, auto_save=True):
        from bank_guarantee.models import Request
        if isinstance(request, Request):
            bank = cls.get_first_relevant_bank(request)
        else:
            bank = cls.get_first_relevant_mfo(request)
        if bank:
            package_logic = PackageLogic(request, bank)
            ids = package_logic.collect_required_document_categories()
            request.package_class = bank.code
            request.package_categories = ','.join(ids)
            if auto_save:
                request.save()
            cls.fill_documents_from_old_requests(request=request)
        else:
            cls.save_empty_package(request)
