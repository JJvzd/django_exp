from django.urls import path

from clients.views import AgentVerificationsPage, AgentVerificationDetail

urlpatterns = [
    path('verifications/', AgentVerificationsPage.as_view(),
         name='verifications_page'),
    path('verifications/<int:pk>/', AgentVerificationDetail.as_view(),
         name='verification_detail'),
]