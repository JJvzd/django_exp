from django.urls import path, include
from rest_framework_nested import routers

from accounting_report.api.viewsets import AccountingReportViewSet
from bank_guarantee.api.viewsets import BGRequestsViewSet
from cabinet.api.autocomplete_views import (
    AgentsAutocompleteView, ClientsAutocompleteView, MFOAutocompleteView,
    BanksAutocompleteView
)
from cabinet.api.views import (
    FindBik, GetProfile, Viewer, RequestTenderRetrieve, ChangeUserLoginToBank,
    ChangeUserLoginToClient, ClientDocumentApi, ClientChangeWinnerNotification,
    TenderHelpAgentCommentListCreate, Feedback, GetDevelopUsers, DeveloperChangeBank,
    DeveloperChangeStatus, DeveloperUpdatePrintForm, ChangePasswordView
)
from cabinet.api.viewsets.calculator import CalculateBGViewSet
from cabinet.api.viewsets.discuss import DiscussViewSet, TemplateChatViewSet
from cabinet.api.viewsets.notifications import NotificationsViewSet
from cabinet.api.viewsets.reports import ReportViewSet
from cabinet.api.viewsets.requests_common import (
    RequestsViewSet, RequestTenderViewSet, TendersViewSet, LoanDocumentsViewSet,
    RequestDocumentsViewSet
)

from tender_loans.api.viewsets import LoanRequestViewSet
from users.api.viewsets import UsersViewSet

router = routers.SimpleRouter()
router.register(r'accounting_report', AccountingReportViewSet,
                basename='accounting_report')

router.register(r'users', UsersViewSet, basename='users')
router.register(r'requests', RequestsViewSet, basename='requests')
router.register(r'request_tender', RequestTenderViewSet, basename='request_tender')
router.register(r'discuss', DiscussViewSet, basename='discuss')
router.register(r'tenders', TendersViewSet, basename='tenders')
router.register(r'notifications', NotificationsViewSet, basename='notification')
router.register(r'calculator_bg', CalculateBGViewSet, basename='calculator_bg')
router.register(r'reports', ReportViewSet, basename='reports')
router.register(r'template_chat', TemplateChatViewSet, basename='template_chat')
router.register(r'requests/tender_loans', LoanRequestViewSet, basename='tender_loans')
router.register(r'requests/bank_guarantee', BGRequestsViewSet, basename='bank_guarantee')

tender_loan_router = routers.NestedSimpleRouter(
    router, r'requests/tender_loans', lookup='tender_loans'
)

tender_loan_router.register(r'documents', LoanDocumentsViewSet, basename='loan_documents')

bank_guarantee_router = routers.NestedSimpleRouter(
    router, r'requests/bank_guarantee', lookup='bank_guarantee'
)

bank_guarantee_router.register(
    r'documents', RequestDocumentsViewSet, basename='request_documents'
)

develop_panel_urls = [
    path('get_users', GetDevelopUsers.as_view(), name='develop_get_users'),
    path('change_bank', DeveloperChangeBank.as_view(), name='develop_change_bank'),
    path('change_status', DeveloperChangeStatus.as_view(), name='develop_change_status'),
    path('update_print_form', DeveloperUpdatePrintForm.as_view(),
         name='develop_update_print_form'),
]

urlpatterns = [
    path('develop/', include(develop_panel_urls)),
    path('get_profile/<int:pk>/', GetProfile.as_view(), name='get profile'),
    path('request_tender/<int:pk>/', RequestTenderRetrieve.as_view(),
         name='request_tender_retrieve'),
    path('client_document/<int:pk>/', ClientDocumentApi.as_view(),
         name='client_document'),
    path(
        'client_change_winner_notification/<int:pk>/',
        ClientChangeWinnerNotification.as_view(),
        name='client_change_winner_notification'
    ),
    path('find_bik/', FindBik.as_view(), name='find_bik'),
    path('viewer/', Viewer.as_view(), name='viewer'),
    path(
        'change_user_login_to_bank/<int:pk>/',
        ChangeUserLoginToBank.as_view(),
        name='change_user_login_to_bank'
    ),
    path(
        'change_user_login_to_client/<int:pk>/',
        ChangeUserLoginToClient.as_view(),
        name='change_user_login_to_client'
    ),
    path(
        'tender_help_agent_comment_list_create/',
        TenderHelpAgentCommentListCreate.as_view(),
        name='tender_help_agent_comment_list_create'
    ),
    path('feedback/', Feedback.as_view(), name='feedback_cabinet'),
    path('change_password/', ChangePasswordView.as_view(), name='change_password'),
    path('agents_autocomplete/', AgentsAutocompleteView.as_view()),
    path('clients_autocomplete/', ClientsAutocompleteView.as_view()),
    path('banks_autocomplete/', BanksAutocompleteView.as_view()),
    path('mfo_autocomplete/', MFOAutocompleteView.as_view()),
]
urlpatterns += router.urls + tender_loan_router.urls + bank_guarantee_router.urls
