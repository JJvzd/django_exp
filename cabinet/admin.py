from django.contrib import admin

from questionnaire.models import (
    KindOfActivity, LicensesSRO, PassportDetails,
    DocumentGenDir, ProfilePartnerIndividual, ProfilePartnerLegalEntities
)
from .models import (
    PlacementPlace, OrganizationForms, TaxSystems, CertifyingCenter, SignHistory,
    WorkRule, System, Region
)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code')


@admin.register(PlacementPlace)
class PlacementPlaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'alias', 'code')


@admin.register(CertifyingCenter)
class CertifyingCenterAdmin(admin.ModelAdmin):
    """ Панель управления центрами сертификации"""
    list_display = ('id', 'inn')


@admin.register(OrganizationForms)
class OrganizationFormsAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code')


@admin.register(TaxSystems)
class TaxSystemsAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code')


@admin.register(KindOfActivity)
class ProfileViewActivityAdmin(admin.ModelAdmin):
    list_display = ('id', 'profile', 'value')


@admin.register(LicensesSRO)
class LicensesSROAdmin(admin.ModelAdmin):
    list_display = ('id', 'number_license', 'view_activity')


@admin.register(PassportDetails)
class PassportDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'series', 'number')


@admin.register(DocumentGenDir)
class DocumentGenDirAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_and_number')


@admin.register(ProfilePartnerIndividual)
class ProfilePartnerIndividualAdmin(admin.ModelAdmin):
    list_display = ('id', 'last_name', 'first_name', 'middle_name')


@admin.register(ProfilePartnerLegalEntities)
class ProfilePartnerLegalEntitiesAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'place')


@admin.register(SignHistory)
class SignHistoryAdmin(admin.ModelAdmin):
    pass


@admin.register(WorkRule)
class WorkRuleAdmin(admin.ModelAdmin):
    list_display = ['text', 'bank', 'updated', 'created']


@admin.register(System)
class SystemAdmin(admin.ModelAdmin):
    pass
