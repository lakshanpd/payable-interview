from django.db import models

from apps.circles.models import Circle, CircleMember


class Round(models.Model):
    """One contribution/payout cycle within a circle."""

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        PENDING_APPROVAL = 'PENDING_APPROVAL', 'Pending Approval'
        COMPLETED = 'COMPLETED', 'Completed'

    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name='rounds')
    payout_recipient = models.ForeignKey(
        CircleMember, on_delete=models.CASCADE, related_name='rounds_as_recipient'
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    # Snapshot of Circle.contribution_amount at round-creation time, so a
    # later change to the circle's contribution amount never rewrites the
    # amount owed for an already-open round.
    contribution_amount = models.PositiveIntegerField()
    deadline = models.DateTimeField()
    payout_amount = models.PositiveIntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        constraints = [
            # Enforced in application code too (see RoundService.create_next_round),
            # but a partial unique index gives us a hard DB-level guarantee that
            # two concurrent "create round" calls can never both succeed.
            models.UniqueConstraint(
                fields=['circle'],
                condition=models.Q(status='OPEN'),
                name='unique_open_round_per_circle',
            ),
        ]

    def __str__(self) -> str:
        return f'Round {self.pk} - {self.circle} ({self.status})'


class Contribution(models.Model):
    """A single member's payment into a round's pot."""

    round = models.ForeignKey(Round, on_delete=models.CASCADE, related_name='contributions')
    member = models.ForeignKey(CircleMember, on_delete=models.CASCADE, related_name='contributions')
    amount = models.PositiveIntegerField()
    penalty = models.PositiveIntegerField(default=0)
    total_paid = models.PositiveIntegerField()
    is_late = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['round', 'member'], name='unique_contribution_per_round_member'),
        ]
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'{self.member} -> {self.round} ({self.total_paid})'
