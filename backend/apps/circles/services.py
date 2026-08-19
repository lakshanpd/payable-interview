"""Business logic for circle creation and membership.

Kept separate from views/serializers so it can be unit-tested and reused
without touching HTTP concerns (see apps/rounds/services.py for the same
pattern applied to round/contribution logic).
"""
import secrets
import string

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from apps.common.exceptions import ServiceError

from .models import Circle, CircleMember

User = get_user_model()

INVITE_CODE_ALPHABET = string.ascii_uppercase + string.digits
INVITE_CODE_LENGTH = 8
DEFAULT_PENALTY_RATE = 3


def _generate_invite_code() -> str:
    return ''.join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(INVITE_CODE_LENGTH))


class CircleService:
    @staticmethod
    @transaction.atomic
    def create_circle(user: User, name: str, contribution_amount: int, penalty_rate: int | None = None) -> Circle:
        # Local import: avoids a module-load-time cycle since rounds.models
        # imports apps.circles.models. RoundService is only needed here, at
        # call time, to spin up the circle's first round.
        from apps.rounds.services import RoundService

        circle = None
        # Invite codes are randomly generated; collisions are astronomically
        # unlikely (36^8 space) but we still retry on the rare IntegrityError
        # rather than trusting uniqueness blindly.
        for _ in range(5):
            try:
                circle = Circle.objects.create(
                    name=name,
                    invite_code=_generate_invite_code(),
                    admin=user,
                    contribution_amount=contribution_amount,
                    penalty_rate=penalty_rate if penalty_rate is not None else DEFAULT_PENALTY_RATE,
                )
                break
            except IntegrityError:
                continue
        if circle is None:
            raise ServiceError('Could not generate a unique invite code, please retry.', status_code=500)

        CircleMember.objects.create(circle=circle, user=user, position=1)
        RoundService.create_next_round(circle)
        return circle

    @staticmethod
    @transaction.atomic
    def join_circle(user: User, invite_code: str) -> CircleMember:
        try:
            # select_for_update() + the SQLite `BEGIN IMMEDIATE` transaction
            # mode (see settings.DATABASES) together ensure that if two
            # requests try to join the same circle at the same instant, the
            # second one only proceeds after the first has committed its
            # membership row - so the member-count check below can never be
            # stale, and two joiners can never be handed the same position.
            circle = Circle.objects.select_for_update().get(invite_code=invite_code)
        except Circle.DoesNotExist:
            raise ServiceError('Invalid invite code.', status_code=404, code='not_found')

        if CircleMember.objects.filter(circle=circle, user=user).exists():
            raise ServiceError('You have already joined this circle.', status_code=400, code='already_joined')

        current_count = circle.members.count()
        if current_count >= circle.max_members:
            raise ServiceError('This circle is already full.', status_code=400, code='circle_full')

        return CircleMember.objects.create(circle=circle, user=user, position=current_count + 1)
