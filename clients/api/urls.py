from django.urls import path
from rest_framework_nested import routers

from accounting_report.api.viewsets import AccountingReportViewSet
from bank_guarantee.api.viewsets import BGRequestsViewSet

from clients.api.viewsets import AgentInstructionsDocumentsViewSet

from clients.api.views import SetContractStateView, CompanyContactsView, \
    ClientStatisticView
from clients.api.viewsets import (
    ClientsViewSet, AgentsViewSet, AgentSettingsViewSet, AgentSettingsDocumentsViewSet,
    AgentInformationViewSet, CompanyViewSet, CompanyInfoViewSet,
    BankRejectionReasonTemplateViewSet, BankBlackListViewSet
)

router = routers.SimpleRouter()
router.register(r'clients', ClientsViewSet, basename='clients')
router.register(r'agents', AgentsViewSet, basename='agents')
router.register(r'accounting_report', AccountingReportViewSet,
                basename='accounting_report')

router.register(r'settings', AgentSettingsViewSet, basename='agent_settings')

router.register(r'settings/documents', AgentSettingsDocumentsViewSet,
                basename='agent_settings_documents')

router.register(r'settings/documents_info', AgentSettingsDocumentsViewSet,
                basename='agent_settings_documents')

router.register(r'agent_information', AgentInformationViewSet,
                basename='agent_information')

router.register(r'company', CompanyViewSet, basename='company')
router.register(r'requests/bank_guarantee', BGRequestsViewSet,
                basename='bank_guarantee')
router.register(r'company_info', CompanyInfoViewSet, basename='company_info')

router.register(r'agent_instructions_documents', AgentInstructionsDocumentsViewSet,
                basename='agent_instructions_documents')

router.register(r'bank_rejection_reason_templates',
                BankRejectionReasonTemplateViewSet,
                basename='bank_rejection_reason_template')

router.register(r'bank_black_list',
                BankBlackListViewSet,
                basename='bank_black_list')

urlpatterns = [
                  path('set_contract_state/<int:pk>/', SetContractStateView.as_view(),
                       name='set_contract_state'),
                  path('set_contract_state/', SetContractStateView.as_view(),
                       name='set_contract_state'),
                  path('company_contacts', CompanyContactsView.as_view(),
                       name='company_contacts'),
                  path('clients/statistic', ClientStatisticView.as_view(),
                       name='company_contacts'),
              ] + router.urls
