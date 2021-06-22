from clients.models import Client
from questionnaire.models import Profile


def update_contact_info_profile_by_user(company, user):
    assert isinstance(company.get_actual_instance, Client)
    profile = Profile.objects.filter(client=company).first()

    if not profile.contact_name:
        profile.contact_name = user.full_name
    if not profile.contact_phone:
        profile.contact_phone = user.phone
    if not profile.contact_email:
        profile.contact_email = user.email
    profile.save()
