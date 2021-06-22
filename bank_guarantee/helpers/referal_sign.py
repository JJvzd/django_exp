from django.contrib.sites.models import Site


class ReferalSign:

    @staticmethod
    def generate_url(request_id, url_type='sign'):
        '''
        url_type: 
        sign - ссылка на подписание документов
        offer - ссылка на принятие предложения
        '''
        current_domain = Site.objects.get_current().domain
        url = ''
        if url_type == 'sign':
            url = 'https://{domain}/request/{request_id}/sign'.format(
                domain=current_domain, request_id=request_id)
        else:
            url = 'https://{domain}/client/request/{request_id}/sign_offer'.format(
                domain=current_domain, request_id=request_id)
        return url


def add_sign_url_for_request(request, user):
    discuss = request.discusses.filter(
        bank=request.bank,
        agent=request.agent
    ).first()
    if discuss and discuss.can_write(user):
        msg = 'Ссылка для подписания заявки: \
            <a href="{url}">{url}</a>'.format(
            url=ReferalSign.generate_url(request.id, 'sign')
        )
        request.sign_link_sent = True
        request.save()
        discuss.add_message(
            author=user,
            message=msg
        )


def need_sign_url(request):
    result = True
    if request.bank.settings.referal_sign_from_amount != 0:
        if request.required_amount < request.bank.settings.referal_sign_from_amount:
            result = False
    return result

