from rest_framework import serializers

from apps.circles.serializers import CircleMemberSerializer

from .models import Contribution, Round


class ContributionSerializer(serializers.ModelSerializer):
    member = CircleMemberSerializer(read_only=True)

    class Meta:
        model = Contribution
        fields = ('id', 'member', 'amount', 'penalty', 'total_paid', 'is_late', 'created_at')


class RoundSerializer(serializers.ModelSerializer):
    payout_recipient = CircleMemberSerializer(read_only=True)
    contributions = ContributionSerializer(many=True, read_only=True)

    class Meta:
        model = Round
        fields = (
            'id', 'circle', 'payout_recipient', 'status', 'contribution_amount',
            'deadline', 'payout_amount', 'approved_at', 'created_at', 'contributions',
        )
