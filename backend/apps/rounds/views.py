from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Round
from .permissions import IsCircleAdmin, IsRoundCircleMember
from .serializers import RoundSerializer
from .services import RoundService


class RoundDetailView(APIView):
    """GET /api/rounds/{id} — a single round with its contributions."""

    permission_classes = [IsAuthenticated, IsRoundCircleMember]

    def get(self, request, pk):
        round_obj = get_object_or_404(
            Round.objects.select_related('circle', 'payout_recipient__user'), pk=pk
        )
        self.check_object_permissions(request, round_obj)
        return Response(RoundSerializer(round_obj).data)


class ContributeView(APIView):
    """POST /api/rounds/{id}/contribute — pay into the round's pot."""

    def post(self, request, pk):
        contribution = RoundService.contribute(user=request.user, round_id=pk)
        round_obj = contribution.round
        round_obj.refresh_from_db()
        return Response(RoundSerializer(round_obj).data, status=status.HTTP_201_CREATED)


class ApproveRoundView(APIView):
    """POST /api/rounds/{id}/approve — admin-only payout approval."""

    permission_classes = [IsAuthenticated, IsCircleAdmin]

    def post(self, request, pk):
        round_obj = get_object_or_404(Round.objects.select_related('circle'), pk=pk)
        self.check_object_permissions(request, round_obj)

        approved_round = RoundService.approve_round(admin_user=request.user, round_id=pk)
        return Response(RoundSerializer(approved_round).data)
