from django.contrib import admin
from django.utils.safestring import mark_safe

from bank_guarantee.models import (
    RequestStatus, Request, Offer, RequestPrintForm, ClientDocument, DocumentLinkToPerson,
    BankOfferDocumentCategory, OfferDocumentCategory, OfferAdditionalDataField,
    OfferAdditionalData, OfferPrintForm, ExternalRequest, BankRatingResult,
    RequestPrintFormRule
)
from base_request.models import BankDocumentType
from base_request.tasks import task_send_to_bank
from cabinet.base_logic.package.base import PackageLogic
from users.models import User, Role


@admin.register(OfferDocumentCategory)
class AdminOfferDocumentCategory(admin.ModelAdmin):
    list_display = [
        'name',
        'required',
        'need_sign',
        'order',
        'active',
        'step',
    ]


@admin.register(BankOfferDocumentCategory)
class AdminBankOfferDocumentCategory(admin.ModelAdmin):
    list_display = ['bank', 'category']
    raw_id_fields = ['bank', 'category']


@admin.register(DocumentLinkToPerson)
class AdminDocumentLinkToPerson(admin.ModelAdmin):
    list_display = ('id', 'request', 'document_category', 'person', 'document')
    readonly_fields = ('request', 'document_category', 'person', 'document')

    def has_add_permission(self, request, obj=None):
        return False


admin.site.register(ClientDocument)


@admin.register(RequestStatus)
class AdminRequestStatuses(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'color')


def send_to_bank_action(modeladmin, request, queryset):
    for obj in queryset.filter(status__code=RequestStatus.CODE_SENDING_IN_BANK):
        task_send_to_bank.delay(
            request_id=obj.id,
            user_id=User.objects.filter(roles__name=Role.SUPER_AGENT).first().id,
            type='request'
        )


send_to_bank_action.short_description = "Отправка в банк | завершить процесс"


def calc_all_rating(modeladmin, request, queryset):
    from bank_guarantee.tasks import task_generate_request_rating
    for obj in queryset:
        task_generate_request_rating.delay(
            request_id=obj.id,
            force=True,
        )


calc_all_rating.short_description = "Расчет рейтинга"


def load_package_docs(modeladmin, request, queryset):
    for obj in queryset.filter(status__code=RequestStatus.CODE_DRAFT):
        PackageLogic.fill_documents_from_old_requests(obj)


load_package_docs.short_description = "Загрузить документы из старых заявок"


@admin.register(Request)
class AdminRequests(admin.ModelAdmin):
    list_filter = ['bank', 'status']
    list_display = (
        'id', 'request_number', 'request_number_in_bank', 'client', 'agent', 'bank'
    )
    readonly_fields = ['base_request']
    raw_id_fields = [
        'tender', 'client', 'agent', 'bank', 'agent_user', 'assigned', 'verifier'
    ]
    search_fields = ['id', 'request_number']
    actions = [send_to_bank_action, load_package_docs, calc_all_rating]
    def render_change_form(self, request, context, *args, **kwargs):
        context['adminform'].form.fields['tmp_manager'].queryset = User.objects.filter(
            roles__name=Role.MANAGER
        )
        return super(AdminRequests, self).render_change_form(
            request, context, *args, **kwargs
        )


@admin.register(Offer)
class AdminRequestOffers(admin.ModelAdmin):
    search_fields = ['request__id', 'request__request_number']
    list_display = ('id', 'request')
    raw_id_fields = ['request']


class RequestPrintFormRuleInline(admin.StackedInline):
    model = RequestPrintFormRule
    extra = 0


@admin.register(RequestPrintForm)
class PrintFormAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'filename', 'get_banks', 'roles', 'need_sign', 'active', 'in_conclusions',
        'download_name'
    ]
    search_fields = ['name', 'id']
    readonly_fields = ['bank']
    list_filter = ['need_sign', 'active', 'banks', 'roles']
    inlines = [RequestPrintFormRuleInline]

    @mark_safe
    def get_banks(self, obj):
        return "<br>".join(
            [p.bank.short_name.replace(' ', '&nbsp;') for p in obj.banks.all()]
        )

    get_banks.short_description = 'Видимо для банков'
    get_banks.allow_tags = True


@admin.register(OfferPrintForm)
class OfferPrintFormAdmin(admin.ModelAdmin):
    list_display = ['name', 'type']
    search_fields = ['name', 'id']


@admin.register(BankDocumentType)
class BankDocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'position', 'order', 'active']
    list_filter = ['position', 'active']
    search_fields = ['name', 'id']


@admin.register(OfferAdditionalDataField)
class OfferAdditionalDataFieldAdmin(admin.ModelAdmin):
    list_display = ['id', 'field_name', 'default_value', 'config']


@admin.register(OfferAdditionalData)
class OfferAdditionalDataAdmin(admin.ModelAdmin):
    pass


@admin.register(ExternalRequest)
class ExternalRequestAdmin(admin.ModelAdmin):
    search_fields = ['request__id', 'request__request_number', 'external_id']
    list_display = ('id', 'request', 'external_id')
    raw_id_fields = ['request']


@admin.register(BankRatingResult)
class BankRatingResultAdmin(admin.ModelAdmin):
    search_fields = ['request__id', 'request__request_number']
    list_display = ('id', 'request', 'bank_rating')
    raw_id_fields = ['request', 'bank_rating']


@admin.register(RequestPrintFormRule)
class RequestPrintFormRuleAdmin(admin.ModelAdmin):
    search_fields = ['print_form.name', 'print_form.download_name']
    list_display = ('id', 'print_form', 'template')
