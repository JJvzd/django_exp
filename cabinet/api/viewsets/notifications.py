from rest_framework import viewsets
from rest_framework.decorators import action as drf_action
from rest_framework.response import Response

from notification.models import Notifications, NotificationsUsers
from notification.serializers import NotificationsUsersSerializer
from users.models import Role, User


class NotificationsViewSet(viewsets.ViewSet):
    serializer_class = NotificationsUsersSerializer

    def list(self, request, *args, **kwargs):
        for notification in Notifications.objects.all():
            if NotificationsUsers.can_subscribe(request.user, notification):
                NotificationsUsers.objects.get_or_create(
                    user=request.user,
                    notification=notification,
                    defaults={
                        'is_active': True
                    }
                )
        return Response({
            'notifications': self.serializer_class(
                request.user.notifications.all(), many=True
            ).data
        })

    @drf_action(detail=False, methods=['POST'])
    def change_active(self, *args, **kwargs):
        notifications = self.request.data.get('notifications')
        for notification in notifications:
            notification_user = self.request.user.notifications.filter(
                id=int(notification['id'])).first()
            notification_user.is_active = notification['is_active']
            notification_user.save(update_fields=['is_active'])
        return Response({
            'success': "Поля изменены"
        })

    @drf_action(detail=True, methods=['GET'])
    def client(self, request, *args, pk=None, **kwargs):
        if self.request.user.has_role(Role.SUPER_AGENT):
            user = User.objects.filter(id=pk).first()
            return Response({
                'notifications': self.serializer_class(
                    user.notifications.all(), many=True
                ).data
            })
        return Response({
            'error': 'Нет прав доступа'
        })

    @drf_action(detail=True, methods=["POST"])
    def change_active_for_client(self, request, *args, pk=None, **kwargs):
        if self.request.user.has_role(Role.SUPER_AGENT):
            user = User.objects.filter(id=pk).first()
            notifications_users = user.notifications.all()
            notifications = self.request.data.get('notifications')
            for notification in notifications:
                notification_user = notifications_users.filter(
                    id=int(notification['id'])
                ).first()
                notification_user.is_active = notification['is_active']
                notification_user.save()
            return Response({
                'success': "Поля изменены"
            })
        return Response({
            'error': 'Нет прав доступа'
        })
