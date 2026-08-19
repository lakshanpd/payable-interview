from rest_framework import serializers

from apps.users.serializers import UserSerializer

from .models import Circle, CircleMember


class CircleMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = CircleMember
        fields = ('id', 'user', 'position', 'joined_at')


class CircleSerializer(serializers.ModelSerializer):
    admin = UserSerializer(read_only=True)

    class Meta:
        model = Circle
        fields = (
            'id', 'name', 'invite_code', 'admin', 'contribution_amount',
            'penalty_rate', 'max_members', 'created_at',
        )
        read_only_fields = ('id', 'invite_code', 'admin', 'created_at')


class CreateCircleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    contribution_amount = serializers.IntegerField(min_value=1)
    penalty_rate = serializers.IntegerField(min_value=0, required=False)


class JoinCircleSerializer(serializers.Serializer):
    invite_code = serializers.CharField(max_length=12)
