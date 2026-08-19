from django.shortcuts import get_object_or_404
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.rounds.models import Round
from apps.rounds.serializers import RoundSerializer
from apps.users.serializers import UserSerializer

from .models import Circle
from .permissions import IsCircleMember
from .serializers import CircleMemberSerializer, CircleSerializer, CreateCircleSerializer, JoinCircleSerializer
from .services import CircleService


class CreateCircleView(APIView):
    """POST /api/circles — create a circle; caller becomes admin at position 1."""

    def post(self, request):
        serializer = CreateCircleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        circle = CircleService.create_circle(
            user=request.user,
            name=serializer.validated_data['name'],
            contribution_amount=serializer.validated_data['contribution_amount'],
            penalty_rate=serializer.validated_data.get('penalty_rate'),
        )
        return Response(CircleSerializer(circle).data, status=status.HTTP_201_CREATED)


class JoinCircleView(APIView):
    """POST /api/circles/join — join an existing circle by invite code."""

    def post(self, request):
        serializer = JoinCircleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member = CircleService.join_circle(
            user=request.user,
            invite_code=serializer.validated_data['invite_code'],
        )
        data = CircleMemberSerializer(member).data
        data['circle'] = member.circle_id
        return Response(data, status=status.HTTP_201_CREATED)


class CircleDetailView(APIView):
    """GET /api/circles/{id} — circle info, members, current round, and
    each member's contribution status for that round. Powers the mobile
    Circle Screen in a single request.
    """

    permission_classes = [permissions.IsAuthenticated, IsCircleMember]

    def get(self, request, pk):
        circle = get_object_or_404(Circle.objects.select_related('admin'), pk=pk)
        self.check_object_permissions(request, circle)

        members = circle.members.select_related('user').order_by('position')
        current_round = (
            circle.rounds.exclude(status=Round.Status.COMPLETED).order_by('-created_at').first()
        )
        contributed_member_ids = set()
        if current_round is not None:
            contributed_member_ids = set(current_round.contributions.values_list('member_id', flat=True))

        member_data = []
        for member in members:
            member_data.append({
                'id': member.id,
                'user': UserSerializer(member.user).data,
                'position': member.position,
                'is_admin': member.user_id == circle.admin_id,
                'is_current_recipient': bool(
                    current_round and current_round.payout_recipient_id == member.id
                ),
                'has_contributed_current_round': (
                    member.id in contributed_member_ids if current_round else None
                ),
            })

        return Response({
            'circle': CircleSerializer(circle).data,
            'members': member_data,
            'current_round': RoundSerializer(current_round).data if current_round else None,
        })
