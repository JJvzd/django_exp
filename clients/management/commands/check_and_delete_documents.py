from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from django.utils import timezone
from sentry_sdk import capture_exception

from bank_guarantee.models import RequestStatus, RequestDocument
from cabinet.base_logic.conclusions.check_passport import check_passport
from clients.models import Client


class Command(BaseCommand):
    help = 'Удаление файла-договора аренды/субаренды,' \
           ' если аренда/субаренда завершилась.' \
           ' Удаление файлов-паспартов, если паспорта недействительны.'

    def handle(self, *args, **options):
        # удаление аренды
        doc = RequestDocument.objects.filter(
            request__status__code=RequestStatus.CODE_DRAFT,
            request__client__profile__legal_address_to__lt=timezone.localdate(),
            category__code__in=[
                'dogovor-arendysubarendy-svidetelstvo-o-prave-sobstvennosti-i-td-dogovor'
                'a-arendysubarendy-zakliuchennye-na-srok-god-i-bolee-neobkhodimo-predost'
                'avliat-s-otmetkoi-o-registratsii-libo-svidetelstvo-o-prave-sobstvenno'
                'rsti'
            ])
        doc.delete()
        # удаление недействительных паспартов генеральных директоров и/или участников
        clients = Client.objects.all()
        for client in clients:
            try:
                profile = client.profile
            except ObjectDoesNotExist as e:
                capture_exception(e)
                continue

            if profile.general_director:
                result_gen = check_passport(
                    series=profile.general_director.passport.series,
                    number=profile.general_director.passport.number,
                )
            else:
                result_gen = None

            if result_gen:
                doc = RequestDocument.objects.filter(
                    request__status__code=RequestStatus.CODE_DRAFT,
                    request__client=client,
                    category__code__in=[
                        'pasport-edinolichnogo-ispolnitelnogo-organa-generalnogo-'
                        'direktora-direktora-i-td-vse-stranitsy'
                    ]
                )
                doc.delete()
                pass
            for legal_person in profile.persons_entities:
                result_legal_person = check_passport(
                    series=legal_person.passport.series,
                    number=legal_person.passport.number,
                )
                if result_legal_person:
                    doc = RequestDocument.objects.filter(
                        request__status__code=RequestStatus.CODE_DRAFT,
                        request__client=client,
                        category__code__in=[
                            'pasporta-aktsionerovuchastnikov-printsipala-fizicheski'
                            'kh-lits-vse-stranitsy'
                        ]
                    )
                    doc.delete()
                    break
            else:
                for person in profile.persons:
                    result_person = check_passport(
                        series=person.passport.series,
                        number=person.passport.number,
                    )
                    if result_person:
                        doc = RequestDocument.objects.filter(
                            request__status__code=RequestStatus.CODE_DRAFT,
                            request__client=client,
                            category__code__in=[
                                'pasporta-aktsionerovuchastnikov-printsipala-'
                                'fizicheskikh-lits-vse-stranitsy'
                            ]
                        )
                        doc.delete()
                        break
