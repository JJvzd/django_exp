from django.contrib import admin

from clients.models import (
    Bank, MFO, BankSettings, AgentDocumentCategory, AgentDocument,
    AgentInstructionsDocuments, BankPackage, MFOPackage, TemplateChatBank,
    MoscombankDocument, MoscomIntergration, BankSigner, RequestRejectionReasonTemplate,
    BankRating, AgentRewards
)
from clients.models.agents import Agent, AgentProfile, AgentContractOffer, ContractOffer
from clients.models.clients import Client
from clients.models.common import InternalNews
from users.models import User, Role


@admin.register(MoscomIntergration)
class MoscomIntegrationAdmin(admin.ModelAdmin):
    list_display = ['request_id', 'date_from']


@admin.register(MoscombankDocument)
class MoscombankDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'doc_id', 'name']
    raw_id_fields = ['print_form', 'category', 'equal_doc']
    search_fields = ['id', 'doc_name', 'doc_id']


@admin.register(TemplateChatBank)
class TemplateChatBankAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'template']


class AgentDocumentInline(admin.StackedInline):
    model = AgentDocument
    extra = 0
    can_delete = False
    max_num = 0
    readonly_fields = ('category', 'file', 'certificate')


class CompanyUserInlineAdmin(admin.TabularInline):
    model = User
    readonly_fields = ['roles']
    fields = ['id', 'username', 'email', 'first_name', 'last_name', 'roles']
    extra = 0
    max_num = 0
    can_delete = False
    show_change_link = True


class AgentProfileStakedAdmin(admin.StackedInline):
    model = AgentProfile
    fields = ['your_city']
    extra = 0
    max_num = 0


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['id', 'short_name', 'inn', 'kpp', 'ogrn']
    inlines = [AgentProfileStakedAdmin, CompanyUserInlineAdmin, AgentDocumentInline]


@admin.register(AgentContractOffer)
class AgentContractAdmin(admin.ModelAdmin):
    list_display = ['id', 'contract_name', 'contract_date', 'agent',
                    'accept_contract', 'accept_date']
    search_fields = ['agent__inn', 'contract__name']


@admin.register(ContractOffer)
class ContractOfferAdmin(admin.ModelAdmin):
    list_display = ['id', 'start_date']


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    search_fields = ['short_name', 'full_name', 'inn', 'kpp', 'ogrn']
    list_display = ['id', 'short_name', 'inn', 'kpp', 'ogrn', 'manager']
    inlines = [CompanyUserInlineAdmin]

    def render_change_form(self, request, context, *args, **kwargs):
        context['adminform'].form.fields['manager'].queryset = User.objects.filter(
            roles__name=Role.MANAGER
        )
        return super(ClientAdmin, self).render_change_form(
            request, context, *args, **kwargs
        )


admin.site.register(MFO)


class BankSettingsAdmin(admin.StackedInline):
    model = BankSettings


class BankPackageInlineAdmin(admin.StackedInline):
    model = BankPackage


@admin.register(Bank)
class BankAdmin(admin.ModelAdmin):
    inlines = [CompanyUserInlineAdmin, BankSettingsAdmin, BankPackageInlineAdmin]
    list_display = ['id', 'short_name', 'inn', 'ogrn', 'active', 'settings_enable']

    def settings_enable(self, obj):
        return obj.settings.enable

    settings_enable.boolean = True
    settings_enable.verbose_name = 'Принимает заявки'


@admin.register(AgentInstructionsDocuments)
class AgentInstructionsDocumentsAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'name2']


@admin.register(RequestRejectionReasonTemplate)
class RequestRejectionReasonTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'reason']


@admin.register(AgentDocumentCategory)
class AgentDocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'order', 'active')
    readonly_fields = ['type']


@admin.register(AgentDocument)
class AgentDocument(admin.ModelAdmin):
    list_display = ['id', 'agent']


@admin.register(InternalNews)
class InternalNewsAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'created', 'updated', 'status', 'for_clients', 'for_agents', 'for_banks',
        'for_mfo'
    ]


@admin.register(BankPackage)
class BankPackageAdmin(admin.ModelAdmin):
    list_display = ['credit_organization', 'document_type', 'active', 'required']


@admin.register(MFOPackage)
class MFOPackageAdmin(admin.ModelAdmin):
    list_display = ['credit_organization', 'document_type', 'active', 'required']


@admin.register(BankSigner)
class BankSignerAdmin(admin.ModelAdmin):
    list_display = ['credit_organization', 'first_name', 'last_name', 'middle_name']


@admin.register(BankRating)
class BankRatingAdmin(admin.ModelAdmin):
    list_display = ['credit_organization', 'rating_class']


@admin.register(AgentRewards)
class RequestPrintFormRuleAdmin(admin.ModelAdmin):
    search_fields = ['date']
    list_display = ('id', 'date', 'agent')
