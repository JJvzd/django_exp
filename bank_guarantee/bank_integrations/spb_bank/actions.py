from sentry_sdk import capture_exception

from base_request.actions import Action
from users.models import Role, User


class ChangeAssignedAction(Action):
    code = 'CHANGE_ASSIGNED'

    def allow_action(self):
        if self.request.bank_id == self.user.client_id:
            return True
        if self.user.has_role(Role.SUPER_AGENT):
            return True
        return False

    def get_options(self):
        if self.request.bank:
            users = self.request.bank.user_set.exclude(id=self.user.id)
        else:
            users = User.objects.none()
        allowed_roles = [Role.GENERAL_BANK, Role.BANK, Role.BANK_UNDERWRITER]
        if not self.request.assigned_id:
            users = users.filter(roles__in=Role.objects.filter(name__in=allowed_roles))

        variants = [
            {'value': user.id, 'label': user.full_name} for user in users
        ]
        if self.user.client_id == self.request.bank_id:
            variants = variants + [{'value': self.user.id, 'label': self.user.full_name}]
        return {
            'users': variants,
            'assigned_id': self.request.assigned_id,
        }

    def execute(self, params):
        try:
            new_assigned_id = int(params.get('assigned_id'))
            reason = params.get('reason', '')[:1000]
            new_assigned = self.request.get_allowed_assigned_users().filter(
                id=new_assigned_id
            ).first()
            if new_assigned:
                self.request.set_assigned(user=new_assigned, reason=reason)
                return self.success_result()
            return self.fail_result()
        except Exception as e:
            capture_exception(e)
            return self.fail_result()
