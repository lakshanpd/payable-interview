from rest_framework.permissions import BasePermission


class IsCircleAdmin(BasePermission):
    """Object-level permission: request.user must be the admin of the
    Round's circle. Used on the approve-payout endpoint.
    """

    message = 'Only the circle admin can approve payouts.'

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.circle.admin_id == request.user.id


class IsRoundCircleMember(BasePermission):
    """Object-level permission: request.user must belong to the Round's circle."""

    message = 'You are not a member of this circle.'

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.circle.members.filter(user=request.user).exists()
