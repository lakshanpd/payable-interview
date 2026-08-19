import threading
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from django.test import TransactionTestCase

from apps.circles.models import Circle
from apps.circles.services import CircleService
from apps.rounds.models import Contribution, Round
from apps.rounds.services import RoundService, calculate_penalty, calculate_payout

User = get_user_model()


def make_circle_with_members(n_members=4, contribution_amount=5000, penalty_rate=3):
    """Create a circle with `n_members` (including the admin at position 1)."""
    admin = User.objects.create_user(username='admin', email='admin@example.com', password='pw123456')
    circle = CircleService.create_circle(admin, 'Test Circle', contribution_amount, penalty_rate)
    users = [admin]
    for i in range(2, n_members + 1):
        u = User.objects.create_user(username=f'user{i}', email=f'user{i}@example.com', password='pw123456')
        CircleService.join_circle(u, circle.invite_code)
        users.append(u)
    return Circle.objects.get(id=circle.id), users


class PenaltyCalculationTests(APITestCase):
    def test_penalty_exact_percentage(self):
        self.assertEqual(calculate_penalty(5000, 3), 150)

    def test_penalty_rounds_half_up(self):
        # 3333 * 3 / 100 = 99.99 -> rounds up to 100
        self.assertEqual(calculate_penalty(3333, 3), 100)

    def test_payout_floors_after_one_percent_fee(self):
        # 20000 * 0.99 = 19800 exactly
        self.assertEqual(calculate_payout(20000), 19800)
        # 10001 * 0.99 = 9900.99 -> floors to 9900
        self.assertEqual(calculate_payout(10001), 9900)


class ContributionTests(APITestCase):
    def setUp(self):
        self.circle, self.users = make_circle_with_members(4, contribution_amount=5000, penalty_rate=3)
        self.round = self.circle.rounds.get(status=Round.Status.OPEN)
        # users[0] is admin/position 1/recipient of round 1

    def _contribute_as(self, user):
        self.client.force_authenticate(user)
        return self.client.post(reverse('round-contribute', args=[self.round.id]))

    def test_on_time_contribution_has_no_penalty(self):
        response = self._contribute_as(self.users[1])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        contribution = Contribution.objects.get(round=self.round, member__user=self.users[1])
        self.assertEqual(contribution.amount, 5000)
        self.assertEqual(contribution.penalty, 0)
        self.assertEqual(contribution.total_paid, 5000)
        self.assertFalse(contribution.is_late)

    def test_late_contribution_charges_penalty(self):
        self.round.deadline = timezone.now() - timedelta(days=1)
        self.round.save(update_fields=['deadline'])

        response = self._contribute_as(self.users[1])
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        contribution = Contribution.objects.get(round=self.round, member__user=self.users[1])
        self.assertTrue(contribution.is_late)
        self.assertEqual(contribution.penalty, 150)
        self.assertEqual(contribution.total_paid, 5150)

    def test_recipient_cannot_contribute(self):
        response = self._contribute_as(self.users[0])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_contribute_twice(self):
        self._contribute_as(self.users[1])
        response = self._contribute_as(self.users[1])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_round_moves_to_pending_approval_once_all_non_recipients_paid(self):
        self._contribute_as(self.users[1])
        self._contribute_as(self.users[2])
        self.round.refresh_from_db()
        self.assertEqual(self.round.status, Round.Status.OPEN)

        self._contribute_as(self.users[3])
        self.round.refresh_from_db()
        self.assertEqual(self.round.status, Round.Status.PENDING_APPROVAL)

    def test_round_closes_when_deadline_passes_even_if_not_everyone_paid(self):
        self._contribute_as(self.users[1])
        self.round.deadline = timezone.now() - timedelta(seconds=1)
        self.round.save(update_fields=['deadline'])

        self._contribute_as(self.users[2])
        self.round.refresh_from_db()
        self.assertEqual(self.round.status, Round.Status.PENDING_APPROVAL)


class RoundDetailTests(APITestCase):
    def setUp(self):
        self.circle, self.users = make_circle_with_members(2, contribution_amount=5000, penalty_rate=3)
        self.round = self.circle.rounds.get(status=Round.Status.OPEN)

    def test_member_can_view_round(self):
        self.client.force_authenticate(self.users[1])
        response = self.client.get(reverse('round-detail', args=[self.round.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.round.id)

    def test_non_member_cannot_view_round(self):
        outsider = User.objects.create_user(username='outsider', email='outsider@example.com', password='pw123456')
        self.client.force_authenticate(outsider)
        response = self.client.get(reverse('round-detail', args=[self.round.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ApprovalTests(APITestCase):
    def setUp(self):
        self.circle, self.users = make_circle_with_members(4, contribution_amount=5000, penalty_rate=3)
        self.round = self.circle.rounds.get(status=Round.Status.OPEN)
        for u in self.users[1:]:
            self.client.force_authenticate(u)
            self.client.post(reverse('round-contribute', args=[self.round.id]))
        self.round.refresh_from_db()

    def test_round_is_pending_approval_before_approving(self):
        self.assertEqual(self.round.status, Round.Status.PENDING_APPROVAL)

    def test_non_admin_cannot_approve(self):
        self.client.force_authenticate(self.users[1])
        response = self.client.post(reverse('round-approve', args=[self.round.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_approve_and_payout_is_computed(self):
        self.client.force_authenticate(self.users[0])
        response = self.client.post(reverse('round-approve', args=[self.round.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.round.refresh_from_db()
        self.assertEqual(self.round.status, Round.Status.COMPLETED)
        # 3 contributors * 5000 = 15000; floor(15000 * 0.99) = 14850
        self.assertEqual(self.round.payout_amount, 14850)

    def test_approve_rejected_when_not_pending(self):
        self.client.force_authenticate(self.users[0])
        self.client.post(reverse('round-approve', args=[self.round.id]))
        response = self.client.post(reverse('round-approve', args=[self.round.id]))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_approve_creates_next_round_for_next_position(self):
        self.client.force_authenticate(self.users[0])
        self.client.post(reverse('round-approve', args=[self.round.id]))

        next_round = self.circle.rounds.get(status=Round.Status.OPEN)
        self.assertEqual(next_round.payout_recipient.user, self.users[1])

    def test_no_round_created_after_final_member_paid(self):
        # Walk all 4 rounds to completion.
        current = self.round
        for expected_recipient in self.users:
            self.assertEqual(current.payout_recipient.user, expected_recipient)
            self.client.force_authenticate(self.users[0])
            self.client.post(reverse('round-approve', args=[current.id]))
            current = self.circle.rounds.filter(status=Round.Status.OPEN).first()
            if expected_recipient != self.users[-1]:
                # Contribute for the next round so it can also be approved.
                next_round = current
                for u in self.users:
                    if u == next_round.payout_recipient.user:
                        continue
                    self.client.force_authenticate(u)
                    self.client.post(reverse('round-contribute', args=[next_round.id]))
                current = Round.objects.get(id=next_round.id)

        self.assertIsNone(self.circle.rounds.filter(status=Round.Status.OPEN).first())
        self.assertEqual(self.circle.rounds.filter(status=Round.Status.COMPLETED).count(), 4)


class ConcurrencyTests(TransactionTestCase):
    """Real multi-threaded tests exercising the DB-level locking, run with
    TransactionTestCase so each thread sees genuinely committed data
    (a plain TestCase wraps the whole test in one rolled-back transaction,
    which would hide races entirely).
    """

    def setUp(self):
        self.circle, self.users = make_circle_with_members(4, contribution_amount=5000, penalty_rate=3)
        self.round = self.circle.rounds.get(status=Round.Status.OPEN)

    def test_simultaneous_contributions_from_same_member_only_one_succeeds(self):
        member_user = self.users[1]
        results = []
        barrier = threading.Barrier(2)

        def attempt():
            barrier.wait()
            try:
                RoundService.contribute(user=member_user, round_id=self.round.id)
                results.append('ok')
            except Exception as exc:
                results.append(f'error:{exc}')

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(results.count('ok'), 1)
        self.assertEqual(len(results) - results.count('ok'), 1)
        self.assertEqual(
            Contribution.objects.filter(round=self.round, member__user=member_user).count(), 1
        )

    def test_double_approval_only_completes_once(self):
        for u in self.users[1:]:
            RoundService.contribute(user=u, round_id=self.round.id)
        self.round.refresh_from_db()
        self.assertEqual(self.round.status, Round.Status.PENDING_APPROVAL)

        admin = self.users[0]
        results = []
        barrier = threading.Barrier(2)

        def attempt():
            barrier.wait()
            try:
                RoundService.approve_round(admin_user=admin, round_id=self.round.id)
                results.append('ok')
            except Exception as exc:
                results.append(f'error:{exc}')

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(results.count('ok'), 1)
        self.round.refresh_from_db()
        self.assertEqual(self.round.status, Round.Status.COMPLETED)
        # Exactly one follow-on round should exist, not two.
        self.assertEqual(self.circle.rounds.filter(status=Round.Status.OPEN).count(), 1)
        self.assertEqual(self.circle.rounds.count(), 2)
