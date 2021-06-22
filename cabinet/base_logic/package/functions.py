from sentry_sdk import capture_exception

from cabinet.base_logic.contracts.base import ContractsLogic
from cabinet.base_logic.package.base import ValidateBlock
from cabinet.constants.constants import OrganizationForm, TaxationType
from external_api.clearspending_api import ClearsSpendingApi


class OrgValidationBlock(ValidateBlock):
    for_ip_result = True
    for_org_result = True

    def validate(self, request, bank):
        if request.client.is_organization:
            return self.validate_for_organizations(request, bank)
        else:
            return self.validate_for_ip(request, bank)

    def validate_for_organizations(self, request, bank):
        return self.for_org_result

    def validate_for_ip(self, request, bank):
        return self.for_ip_result


class hasBeneficiars(ValidateBlock):

    def validate(self, request, bank):
        return request.client.profile.profilepartnerindividual_set.filter(
            share__gte=25, is_general_director=False
        ).count() > 0


class hasContractsExperience(ValidateBlock):

    def validate(self, request, bank):
        try:
            find_on_clears_spending = ClearsSpendingApi().check_experience(
                inn=request.client.inn, kpp=request.client.kpp
            )
        except Exception as e:
            capture_exception(e)
            find_on_clears_spending = False

        try:
            find_in_parsers = bool(
                ContractsLogic(request.client).get_finished_contracts_count()
            )
        except Exception as e:
            capture_exception(e)
            find_in_parsers = False

        return find_on_clears_spending or find_in_parsers or request.experience_general_contractor  # noqa


class hasLicencies(ValidateBlock):

    def validate(self, request, bank):
        return request.client.profile.has_license_sro


class hasPoA(ValidateBlock):

    def validate(self, request, bank):
        return request.power_of_attorney


class isAO(OrgValidationBlock):
    def validate_for_organizations(self, request, bank):
        return request.client.profile.organization_form == OrganizationForm.TYPE_AO


class isBigDeal(ValidateBlock):
    def validate(self, request, bank):
        return request.is_big_deal


class isENVD(ValidateBlock):
    def validate(self, request, bank):
        return request.client.profile.tax_system == TaxationType.TYPE_ENVD


class isESHN(ValidateBlock):
    def validate(self, request, bank):
        return request.client.profile.tax_system == TaxationType.TYPE_ESHN


class isGenBuhNotGenDir(ValidateBlock):
    def validate(self, request, bank):
        profile = request.client.profile

        return profile.general_director and profile.booker \
               and profile.general_director.id != profile.booker.id


class isIpOrg(ValidateBlock):
    def validate(self, request, bank):
        return not request.client.is_organization


class isUrOrg(ValidateBlock):
    def validate(self, request, bank):
        return request.client.is_organization


class isOAO(OrgValidationBlock):
    def validate_for_organizations(self, request, bank):
        return request.client.profile.organization_form == OrganizationForm.TYPE_OAO


class isOOO(OrgValidationBlock):
    def validate_for_organizations(self, request, bank):
        return request.client.profile.organization_form == OrganizationForm.TYPE_OOO


class isOSN(ValidateBlock):
    def validate(self, request, bank):
        return request.client.profile.tax_system == TaxationType.TYPE_OSN


class isOtherOrg(OrgValidationBlock):
    def validate_for_organizations(self, request, bank):
        return request.client.profile.organization_form == OrganizationForm.TYPE_OTHER


class isPAO(OrgValidationBlock):
    def validate_for_organizations(self, request, bank):
        return request.client.profile.organization_form == OrganizationForm.TYPE_PAO


class isZAO(OrgValidationBlock):
    def validate_for_organizations(self, request, bank):
        return request.client.profile.organization_form == OrganizationForm.TYPE_ZAO


class isPSN(ValidateBlock):
    def validate(self, request, bank):
        return request.client.profile.tax_system == TaxationType.TYPE_PSN


class isUSN(ValidateBlock):
    def validate(self, request, bank):
        return request.client.profile.tax_system == TaxationType.TYPE_USN


class sumInRange(ValidateBlock):
    def validate(self, request, bank):
        return self.params[0] <= request.required_amount <= self.params[1]


class sumNotInRange(ValidateBlock):
    def validate(self, request, bank):
        return not (self.params[0] <= request.required_amount <= self.params[1])