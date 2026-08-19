"""Business logic for round lifecycle, contributions, and payout approval.

Concurrency notes (see also README "Concurrency Strategy"):

Every mutating entry point here runs inside ``transaction.atomic()`` and
takes a ``select_for_update()`` lock on the ``Round`` row it operates on.
On Postgres/MySQL that is a real row lock: a second concurrent request for
the same round blocks at the database until the first transaction commits
or rolls back, then re-reads the now-current row state. On SQLite,
``select_for_update()`` itself is a no-op (SQLite has no row-level
locking), so we additionally configure the connection to open every
transaction with ``BEGIN IMMEDIATE`` (settings.DATABASES OPTIONS), which
takes SQLite's whole-database write lock at the *start* of the
transaction instead of on the first write. That reproduces the same
"only one writer at a time" guarantee for this project's SQLite database,
which is what makes the re-check-after-lock pattern below safe on either
backend.

We never rely on in-memory flags/locks: every invariant (one contribution
per member per round, one OPEN round per circle, no double approval) is
also backed by a unique constraint or an explicit re-check of DB state
after acquiring the lock, so it holds even across multiple server
processes.
"""
from datetime import timedelta
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from apps.circles.models import Circle, CircleMember
from apps.common.exceptions import ServiceError

from .models import Contribution, Round

User = get_user_model()

ROUND_DURATION = timedelta(days=7)
PAYOUT_RATE = Decimal('0.99')  # 1% platform/service fee taken out of the pot on payout


def calculate_penalty(amount: int, penalty_rate: int) -> int:
    """penalty = round_half_up(amount * penalty_rate / 100), integer in/out."""
    raw = Decimal(amount) * Decimal(penalty_rate) / Decimal(100)
    return int(raw.quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def calculate_payout(total_collected: int) -> int:
    """final_payout = floor(total_collected * 0.99), integer in/out."""
    raw = Decimal(total_collected) * PAYOUT_RATE
    return int(raw.quantize(Decimal('1'), rounding=ROUND_FLOOR))


class RoundService:
    @staticmethod
    def _next_unpaid_member(circle: Circle) -> CircleMember | None:
        """Smallest-position member who has never been the recipient of a
        COMPLETED round. Returns None once every member has been paid once.
        """
        paid_member_ids = CircleMember.objects.filter(
            rounds_as_recipient__circle=circle,
            rounds_as_recipient__status=Round.Status.COMPLETED,
        ).values_list('id', flat=True)
        return circle.members.exclude(id__in=paid_member_ids).order_by('position').first()

    @staticmethod
    def create_next_round(circle: Circle) -> Round | None:
        """Create the circle's next OPEN round, or return None if either
        (a) every member has already received a payout, or
        (b) an OPEN round already exists for this circle.

        Callers (CircleService.create_circle, RoundService.approve_round)
        already hold the relevant lock for the duration of their own
        atomic transaction, so no additional locking happens here. The
        partial unique index on Round(circle, status=OPEN) is the final
        backstop against ever creating two OPEN rounds for one circle.
        """
        if circle.rounds.filter(status=Round.Status.OPEN).exists():
            return None

        recipient = RoundService._next_unpaid_member(circle)
        if recipient is None:
            return None

        try:
            return Round.objects.create(
                circle=circle,
                payout_recipient=recipient,
                status=Round.Status.OPEN,
                contribution_amount=circle.contribution_amount,
                deadline=timezone.now() + ROUND_DURATION,
            )
        except IntegrityError:
            # Lost a race against another transaction creating an OPEN
            # round for this circle; nothing more to do.
            return None

    @staticmethod
    def _maybe_close_round(round_obj: Round) -> None:
        """Move an OPEN round to PENDING_APPROVAL once every non-recipient
        member has contributed, or once the deadline has passed. Must be
        called while still holding the row lock acquired by the caller.
        """
        non_recipient_ids = set(
            round_obj.circle.members.exclude(id=round_obj.payout_recipient_id).values_list('id', flat=True)
        )
        contributed_ids = set(round_obj.contributions.values_list('member_id', flat=True))
        all_contributed = non_recipient_ids.issubset(contributed_ids)
        deadline_passed = timezone.now() > round_obj.deadline

        if all_contributed or deadline_passed:
            round_obj.status = Round.Status.PENDING_APPROVAL
            round_obj.save(update_fields=['status'])

    @staticmethod
    @transaction.atomic
    def contribute(user: User, round_id: int) -> Contribution:
        try:
            # Lock the round row. This is what makes two simultaneous
            # contribute() calls for the same round safe: whichever
            # transaction gets there first finishes (including the
            # "already contributed" and round-closing checks) before the
            # second one is even allowed to read the row.
            round_obj = Round.objects.select_for_update().select_related('circle').get(id=round_id)
        except Round.DoesNotExist:
            raise ServiceError('Round not found.', status_code=404, code='not_found')

        if round_obj.status != Round.Status.OPEN:
            raise ServiceError('This round is not open for contributions.', status_code=400, code='round_not_open')

        try:
            member = round_obj.circle.members.get(user=user)
        except CircleMember.DoesNotExist:
            raise ServiceError('You are not a member of this circle.', status_code=403, code='not_a_member')

        if member.id == round_obj.payout_recipient_id:
            raise ServiceError(
                'The payout recipient cannot contribute in their own round.', status_code=400, code='is_recipient'
            )

        # Belt-and-suspenders: the DB unique constraint is the real
        # guarantee against a duplicate contribution slipping through; this
        # check just turns that failure into a friendly error message.
        if Contribution.objects.filter(round=round_obj, member=member).exists():
            raise ServiceError(
                'You have already contributed to this round.', status_code=400, code='already_contributed'
            )

        is_late = timezone.now() > round_obj.deadline
        amount = round_obj.contribution_amount
        penalty = calculate_penalty(amount, round_obj.circle.penalty_rate) if is_late else 0

        try:
            contribution = Contribution.objects.create(
                round=round_obj,
                member=member,
                amount=amount,
                penalty=penalty,
                total_paid=amount + penalty,
                is_late=is_late,
            )
        except IntegrityError:
            raise ServiceError(
                'You have already contributed to this round.', status_code=400, code='already_contributed'
            )

        RoundService._maybe_close_round(round_obj)
        return contribution

    @staticmethod
    @transaction.atomic
    def approve_round(admin_user: User, round_id: int) -> Round:
        try:
            # Locking here is what makes double-approval safe: if Approve
            # is pressed twice back-to-back, the second call's SELECT
            # blocks until the first call's transaction (status update +
            # next-round creation) has fully committed, at which point it
            # re-reads status=COMPLETED and is rejected below - instead of
            # both calls racing to pay out and create duplicate rounds.
            round_obj = Round.objects.select_for_update().select_related('circle').get(id=round_id)
        except Round.DoesNotExist:
            raise ServiceError('Round not found.', status_code=404, code='not_found')

        if round_obj.circle.admin_id != admin_user.id:
            raise ServiceError('Only the circle admin can approve payouts.', status_code=403, code='not_admin')

        if round_obj.status != Round.Status.PENDING_APPROVAL:
            raise ServiceError(
                'Round is not pending approval.', status_code=400, code='invalid_round_state'
            )

        total_collected = round_obj.contributions.aggregate(total=Sum('total_paid'))['total'] or 0

        round_obj.payout_amount = calculate_payout(total_collected)
        round_obj.status = Round.Status.COMPLETED
        round_obj.approved_at = timezone.now()
        round_obj.save(update_fields=['payout_amount', 'status', 'approved_at'])

        RoundService.create_next_round(round_obj.circle)
        return round_obj
