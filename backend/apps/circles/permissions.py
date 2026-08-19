from rest_framework.permissions import BasePermission


class IsCircleMember(BasePermission):
    """Object-level permission: request.user must belong to the Circle."""

    message = 'You are not a member of this circle.'

    def has_object_permission(self, request, view, obj) -> bool:
        return obj.members.filter(user=request.user).exists()
