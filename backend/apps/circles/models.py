from django.conf import settings
from django.db import models


class Circle(models.Model):
    """A rotating-savings circle ("chama"/"tanda") of up to ``max_members`` users."""

    name = models.CharField(max_length=100)
    invite_code = models.CharField(max_length=12, unique=True)
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='administered_circles'
    )
    # Stored as an integer (smallest currency unit, e.g. cents) — see
    # README "Assumptions" for why all money fields are plain integers.
    contribution_amount = models.PositiveIntegerField()
    # Whole-percent penalty rate applied to late contributions, e.g. 3 == 3%.
    penalty_rate = models.PositiveIntegerField(default=3)
    max_members = models.PositiveSmallIntegerField(default=4)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'{self.name} ({self.invite_code})'


class CircleMember(models.Model):
    """Membership of a user in a circle, with a fixed payout rotation position."""

    circle = models.ForeignKey(Circle, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='circle_memberships')
    position = models.PositiveSmallIntegerField()
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['circle', 'user'], name='unique_circle_user'),
            models.UniqueConstraint(fields=['circle', 'position'], name='unique_circle_position'),
        ]
        ordering = ['position']

    def __str__(self) -> str:
        return f'{self.user} @ {self.circle} (pos {self.position})'
