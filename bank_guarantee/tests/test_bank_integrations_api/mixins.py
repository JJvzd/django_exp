from datetime import timedelta

from django.core.files.base import ContentFile
from django.utils import timezone

from clients.models import Bank, BankCode, User, Role, BaseFile
from files.models import Sign
from tests.conf.load_db.load_request import create_bg_request


class MixinTestApi:
    sender_class = None
    code_bank = None

    @property
    def bank(self):
        return Bank.objects.get(code=self.code_bank)

    @staticmethod
    def fill_client(client):
        profile = client.profile
        # Заполнения паспортных данных физ лиц
        for person in profile.profilepartnerindividual_set.all():
            passport = person.passport
            passport.series = '0000'
            passport.number = '000000'
            passport.issued_by = 'test_issued_by'
            passport.when_issued = timezone.now().date() - timedelta(days=750)
            passport.date_of_birth = timezone.now().date() - timedelta(days=7300)
            passport.place_of_birth = 'test_place_of_birth'
            passport.place_of_registration = 'test_place_of_registration'
            passport.issued_code = '000-000'
            passport.save()
        # Заполнение папортных данных юр лиц
        for person in profile.profilepartnerlegalentities_set.all():
            passport = person.passport
            passport.series = '0000'
            passport.number = '000000'
            passport.issued_by = 'test_issued_by'
            passport.when_issued = timezone.now().date() - timedelta(days=750)
            passport.date_of_birth = timezone.now().date() - timedelta(days=7300)
            passport.place_of_birth = 'test_place_of_birth'
            passport.place_of_registration = 'test_place_of_registration'
            passport.issued_code = '000-000'
            passport.save()
        # заполненеие документа ген дира
        gen_dir = profile.general_director
        gen_dir.share = 100
        gen_dir.save()
        doc = gen_dir.document_gen_dir
        doc.name_and_number = 'test_name_and_number'
        doc.date_protocol_EIO = timezone.now().date() - timedelta(days=300)
        doc.number_protocol_EIO = 'test_number_protocol_EIO'
        doc.is_indefinitely = True
        doc.save()
        client.refresh_from_db()
        return client

    def update_bank(self):
        bank = self.bank
        # Обновления настроек
        settings = bank.settings
        settings.enable = True
        settings.send_via_integration = True
        settings.update_via_integration = True
        settings.save()
        # добавления user для банка
        if not bank.user_set.all().exists():
            user = User.objects.create_user('taki-bank', 'taki@bank.ru', '1111111')
            user.roles.set(Role.objects.filter(
                name__in=[Role.BANK, Role.GENERAL_BANK]
            ))
            user.client = bank
            user.save()

    def attach_file(self, request):
        sender = self.sender_class()
        for name, categories in sender.all_documents_map.items():
            for category in categories:
                name = 'test_%s.docx' % name
                base_file = BaseFile.objects.create(
                    download_name=name,
                    author=request.client
                )
                base_file.file.save(name, ContentFile(name.encode('utf8')))
                request.requestdocument_set.create(
                    file_id=base_file.id,
                    category_id=category
                )

    @staticmethod
    def sign_request(request):
        for file in request.get_documents_for_sign_by_client():
            Sign.objects.filter(file=file, author=request.client).delete()
            sign = Sign.objects.create(
                file=file,
                author=request.client
            )
            name = file.get_download_name()
            sign.signed_file.save(name, ContentFile(name.encode('utf8')))

    @staticmethod
    def sign_offer(request):
        documents = []
        if not request.is_signed:
            documents += list(request.get_documents_for_sign_by_client().values_list(
                'id', flat=True
            ))

        documents += list(request.offer.offerdocument_set.filter(
            file__isnull=False
        ).values_list('file', flat=True))
        for file in BaseFile.objects.filter(id__in=documents):
            Sign.objects.filter(file=file, author=request.client).delete()
            sign = Sign.objects.create(
                file=file,
                author=request.client
            )
            name = file.get_download_name()
            sign.signed_file.save(name, ContentFile(name.encode('utf8')))

    def mock_file_download(self, rm, data):
        sender = self.sender_class()
        for doc in data['documents']:
            rm.register_uri(
                'GET',
                url=sender.get_bank_endpoint() + '/order/test' + '/file/' +
                    doc['files'][0][
                        'fileId'],
                content=('test_%s' % doc['type']).encode('utf8')
            )

    @staticmethod
    def update_request(request):
        days = 60
        now = timezone.now().date()
        request.interval_from = now
        request.final_date = now
        request.interval_to = now + timedelta(days=days)
        request.interval = days
        request.save()

    def get_client(self, setup_db):
        return self.fill_client(setup_db['client'])

    def get_request(self, client):
        request = create_bg_request(client)
        self.attach_file(request)
        self.update_request(request)
        return request
