from django.utils import timezone

from common.helpers import get_month_text


class RequestPrintFormMixin:

    def _get_context(self, request):
        now = timezone.now()
        profile = request.client.profile
        context = {
            'request': request,
            'client': request.client,
            'anketa': request.client.profile,
            'helper': self._get_helper(request),
            'values': {
                "date": now.strftime('%d.%m.%Y'),
                "day": now.strftime("%d"),
                "month": now.strftime("%m"),
                "month_text": get_month_text(now.strftime("%m")).lower(),
                "year": now.strftime("%Y"),
            },
            'legal_shareholders': profile.profilepartnerlegalentities_set.all(),
            'physical_shareholders': profile.profilepartnerindividual_set.all(),
            'offer': request.offer if request.has_offer() else None,
        }
        return context

    def _get_helper(self, request):
        helper = request.bank_integration.get_print_forms_helper()
        return helper(request, request.bank)
