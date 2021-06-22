from clients.models import Company, Bank, MFO
from users.models import User


def common_info(inquirer: Company, company: Company, user: User = None):
    if not user:
        user = company.user_set.first()
    data = {
        'id': company.id,
        'user_id': user.id,
        'name': company.short_name,
        'inn': company.inn,
        'ogrn': company.ogrn,
        'kpp': company.kpp,
    }
    if not isinstance(inquirer, Bank) or isinstance(inquirer, MFO):
        data.update({
            'contact_name': user.full_name if user else '',
            'contact_phone': user.phone if user else '',
            'contact_phone_2': user.phone2 if user else '',
            'contact_email': user.email if user else '',
        })
        if isinstance(company, Bank):
            data.update({
                'legal_address': company.legal_address,
                'okpto': company.okpto,
            })
    return data
