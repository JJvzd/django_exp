import os
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from django.db.models import Q

from base_request.models import AbstractMessage, AbstractDiscuss
from users.models import Role


class ExportRequest:

    def __get_request_docs(self, request, docs, export_separated_signs=True):
        docs_data = []
        separated_signs_data = []
        for request_doc in docs:
            if request_doc.file:
                if export_separated_signs:
                    sep_sign = request_doc.file.separatedsignature_set.filter(
                        author_id=request.client_id
                    ).first()
                    if sep_sign:
                        separated_signs_data.append({
                            'file': request_doc.file.file,
                            'sign': sep_sign.sign,
                            'download_name': request_doc.file.get_download_name()
                        })
                    docs_data.append({
                        'file': request_doc.file.file,
                        'download_name': request_doc.file.get_download_name()
                    })
                else:
                    sign = request_doc.file.sign_set.filter(
                        author_id=request.client_id
                    ).first()
                    if sign:
                        docs_data.append({
                            'file': sign.signed_file,
                            'download_name': '%s.sig' %
                                             request_doc.file.get_download_name()
                        })
                    else:
                        docs_data.append({
                            'file': request_doc.file.file,
                            'download_name': request_doc.file.get_download_name()
                        })
        return docs_data, separated_signs_data

    def fill_docs(self, zip_file, subfolder, docs_data, separated_signs_data):
        for file_dict in docs_data:
            file_path = file_dict['file']
            download_name = file_dict['download_name']
            download_name = download_name.split('/')

            download_name = download_name[-1]

            zip_path = os.path.join(subfolder, download_name)
            try:
                zip_file.write(file_path.path, zip_path)
            except FileNotFoundError:
                pass

        for sign_data in separated_signs_data:
            download_name = sign_data['download_name']
            zip_path = os.path.join(subfolder, '%s.sig' % download_name)
            zip_file.writestr(zip_path, sign_data['sign'])
        return zip_file

    def export_as_zip(self, request, user, export_separated_signs=True,
                      print_form_path: str = 'печатные_формы/',
                      documents_path: str = 'документы/',
                      offer_path: str = 'предложение/'):

        print_forms = request.requestdocument_set.filter(print_form__isnull=False)
        # TODO: Сделать условие для всех ролей банка
        if user.has_role(Role.BANK):
            print_forms = print_forms.filter(
                Q(print_form__bank_id=user.client_id) | Q(print_form__bank__isnull=True)
            )

        zip_print_forms, separated_signs_pf = self.__get_request_docs(
            request, print_forms, export_separated_signs=export_separated_signs
        )

        requests_docs = request.requestdocument_set.filter(category__isnull=False)

        requests_docs_files, separated_signs_docs = self.__get_request_docs(
            request,
            requests_docs,
            export_separated_signs=export_separated_signs
        )
        if request.has_offer():
            offer_docs_files, separated_signs_offer_docs = self.__get_request_docs(
                request,
                request.offer.offerdocument_set.all(),
                export_separated_signs=export_separated_signs
            )
        else:
            offer_docs_files = []
            separated_signs_offer_docs = []

        mem_zip = BytesIO()
        with ZipFile(mem_zip, mode="w", compression=ZIP_DEFLATED) as zip_file:
            self.fill_docs(
                zip_file, print_form_path, zip_print_forms, separated_signs_pf
            )
            self.fill_docs(
                zip_file, documents_path, requests_docs_files, separated_signs_docs
            )
            self.fill_docs(
                zip_file, offer_path, offer_docs_files, separated_signs_offer_docs
            )

            for file in zip_file.filelist:
                file.create_system = 0
        return mem_zip

    def __get_messages_files(self, message, client):
        docs_data = []
        separated_signs_data = []

        for file in message.files.all():
            if file.file:
                sep_sign = file.file.separatedsignature_set.filter(
                    author_id=client.id
                ).first()
                if sep_sign:
                    separated_signs_data.append({
                        'file': file.file.file,
                        'sign': sep_sign.sign,
                        'download_name': file.file.get_download_name().split('/')[-1],
                    })

                sign = file.file.sign_set.filter(author_id=client.id).first()
                if sign:
                    docs_data.append({
                        'file': sign.signed_file,
                        'download_name': file.file.get_download_name()
                    })
                else:
                    docs_data.append({
                        'file': file.file.file,
                        'download_name': file.file.get_download_name()
                    })
        return docs_data, separated_signs_data

    def export_message_files_as_zip(self, discuss: AbstractDiscuss,
                                    message: AbstractMessage):
        message_files, separated_signs_files = self.__get_messages_files(
            message=message, client=discuss.request.client
        )
        mem_zip = BytesIO()
        with ZipFile(mem_zip, mode="w", compression=ZIP_DEFLATED) as zf:
            self.fill_docs(zf, '/', message_files, separated_signs_files)

            for file in zf.filelist:
                file.create_system = 0
        return mem_zip

    def export_discuss_files_as_zip(self, discuss: AbstractDiscuss):
        all_message_files = []
        all_separated_signs = []
        for message in discuss.messages.all():
            message_files, separated_signs_files = self.__get_messages_files(
                message=message, client=discuss.request.client
            )
            all_message_files += message_files
            all_separated_signs += separated_signs_files
        mem_zip = BytesIO()
        with ZipFile(mem_zip, mode="w", compression=ZIP_DEFLATED) as zf:
            self.fill_docs(zf, '/', all_message_files, all_separated_signs)

            for file in zf.filelist:
                file.create_system = 0
        return mem_zip
