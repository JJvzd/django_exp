from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = 'Установка фикстур для теста'

    def handle(self, *args, **options):
        call_command('loaddata', '../fixtures/cabinet.Country.json')
        call_command('loaddata', '../fixtures/cabinet.PlacementPlace.json')
        call_command('loaddata', '../fixtures/cabinet.Region.json')
        call_command('loaddata', '../fixtures/bank_guarantee.OfferDocumentCategory.json')
        call_command('loaddata',
                     '../fixtures/tender_loans.LoanOfferDocumentCategory.json')

        call_command('loaddata', '../fixtures/tender_loans.LoanStatus.json')
        call_command('loaddata', '../fixtures/bank_guarantee.RequestStatus.json')
        call_command('loaddata', '../fixtures/base_request.BankDocumentType.json')
        call_command('loaddata', '../fixtures/users.Role.json')
        call_command('loaddata', '../fixtures/clients.Company.json')
        call_command('loaddata', '../fixtures/clients.Bank.json')
        call_command('loaddata', '../fixtures/clients.MFO.json')
        call_command('loaddata', '../fixtures/clients.BankSettings.json')
        call_command('loaddata', '../fixtures/clients.BankPackage.json')
        call_command('loaddata', '../fixtures/conclusions_app.Conclusion.json')
        call_command('loaddata',
                     '../fixtures/bank_guarantee.BankOfferDocumentCategory.json')

        call_command('loaddata', '../fixtures/bank_guarantee.OfferPrintForm.json')
        call_command('loaddata', '../fixtures/bank_guarantee.RequestPrintForm.json')

        call_command('loaddata', '../fixtures/clients.AgentDocumentCategory.json')
        call_command('loaddata', '../fixtures/clients.Agent.json')
        call_command('loaddata', '../fixtures/clients.AgentDocument.json')

        call_command('loaddata', '../fixtures/users.User.json')
        call_command('loaddata', '../fixtures/clients.AgentManager.json')

        call_command('loaddata', '../fixtures/notification.Notifications.json')
        call_command('loaddata', '../fixtures/notification.NotificationsRoles.json')

        call_command('loaddata', '../fixtures/cabinet.System.json')
