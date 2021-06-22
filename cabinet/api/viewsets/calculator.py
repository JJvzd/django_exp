from rest_framework import viewsets
from rest_framework.decorators import action as drf_action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from cabinet.constants.constants import FederalLaw
from common.excel import BGCalculator


class CalculateBGViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    types_bg = (
        ('', 'Не вабрано'),
        (1, 'На исполнение'),
        (2, 'На участие'),
        (3, 'Возврат аванса'),
        (4, 'Гарантийные обязательства')
    )

    @drf_action(detail=False, methods=['GET'])
    def get_laws(self, *args, **kwargs):
        return Response({
            'laws': FederalLaw.CHOICES
        })

    @drf_action(detail=False, methods=['GET'])
    def get_types_bg(self, *args, **kwargs):
        return Response({
            'types_bg': self.types_bg
        })

    @drf_action(detail=False, methods=['POST'])
    def get_commissions(self, *args, **kwargs):
        calc = BGCalculator()
        sum_bg = self.request.data.get('sum_bg')
        space = self.request.data.get('space')
        law = self.request.data.get('law')

        if not sum_bg or not space or not law:
            return Response({
                'errors': ['Не все поля заполнены']
            })
        return Response({
            'commissions': calc.calculate(
                amount=float(str(sum_bg).replace(' ', '').replace(',', ',')),
                interval=int(space),
                law=law,
                guarantee_type=self.request.data.get('contract_type', [])
            )
        })