from django.urls import path, include
from rest_framework_nested import routers

from cabinet.views import (
    ForceLoginView, WorkInProgress, InbankApi, RedirectMosKomBank,
    ReglamentView, PersonConfirmView
)


router = routers.SimpleRouter()
router.register(r'api/inbank', InbankApi, basename='inbank_api')

urlpatterns = [
    path('api/force_login', ForceLoginView.as_view(), name='force_login'),
    path('work_in_progress', WorkInProgress.as_view(), name='work_in_progress'),
    path('api/', include('cabinet.api.urls')),
    path('redirect_moskom_bank/', RedirectMosKomBank.as_view(),
         name='moskombank_redirect'),
    path('reglament/', ReglamentView.as_view(), name='reglament'),
    path('get_reglament_data/', ReglamentView.as_view(), name='get_reglament_data'),
    path('person_confirm/', PersonConfirmView.as_view(), name='person_confirm'),
] + router.urls
