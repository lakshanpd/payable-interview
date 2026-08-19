from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.circles.models import Circle, CircleMember
from apps.rounds.models import Round

User = get_user_model()


class CreateCircleTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin1', email='admin1@example.com', password='pw123456')
        self.client.force_authenticate(self.user)

    def test_create_circle_makes_caller_admin_at_position_one(self):
        response = self.client.post(reverse('circle-create'), {
            'name': 'My Circle',
            'contribution_amount': 5000,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        circle = Circle.objects.get(id=response.data['id'])
        self.assertEqual(circle.admin, self.user)
        self.assertTrue(circle.invite_code)

        membership = CircleMember.objects.get(circle=circle, user=self.user)
        self.assertEqual(membership.position, 1)

    def test_create_circle_auto_creates_first_round_for_admin(self):
        response = self.client.post(reverse('circle-create'), {
            'name': 'My Circle',
            'contribution_amount': 5000,
        })
        circle = Circle.objects.get(id=response.data['id'])

        round_obj = circle.rounds.get()
        self.assertEqual(round_obj.status, Round.Status.OPEN)
        self.assertEqual(round_obj.payout_recipient.user, self.user)
        self.assertEqual(round_obj.contribution_amount, 5000)

    def test_invite_codes_are_unique_across_circles(self):
        r1 = self.client.post(reverse('circle-create'), {'name': 'Circle 1', 'contribution_amount': 1000})
        r2 = self.client.post(reverse('circle-create'), {'name': 'Circle 2', 'contribution_amount': 1000})
        self.assertNotEqual(r1.data['invite_code'], r2.data['invite_code'])

    def test_create_circle_requires_authentication(self):
        self.client.force_authenticate(None)
        response = self.client.post(reverse('circle-create'), {'name': 'X', 'contribution_amount': 100})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class JoinCircleTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin2', email='admin2@example.com', password='pw123456')
        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse('circle-create'), {'name': 'Join Test', 'contribution_amount': 2000})
        self.circle = Circle.objects.get(id=response.data['id'])
        self.invite_code = self.circle.invite_code

    def _join_as(self, username):
        user = User.objects.create_user(username=username, email=f'{username}@example.com', password='pw123456')
        client_user_pair = user
        self.client.force_authenticate(user)
        response = self.client.post(reverse('circle-join'), {'invite_code': self.invite_code})
        return client_user_pair, response

    def test_members_join_in_sequential_positions(self):
        _, r2 = self._join_as('member2')
        self.assertEqual(r2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r2.data['position'], 2)

        _, r3 = self._join_as('member3')
        self.assertEqual(r3.data['position'], 3)

    def test_cannot_join_same_circle_twice(self):
        user, r2 = self._join_as('member2')
        self.client.force_authenticate(user)
        r_again = self.client.post(reverse('circle-join'), {'invite_code': self.invite_code})
        self.assertEqual(r_again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_invite_code_returns_404(self):
        other = User.objects.create_user(username='outsider', email='outsider@example.com', password='pw123456')
        self.client.force_authenticate(other)
        response = self.client.post(reverse('circle-join'), {'invite_code': 'NOTREAL1'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_circle_rejects_fifth_member(self):
        self._join_as('member2')
        self._join_as('member3')
        self._join_as('member4')
        _, r5 = self._join_as('member5')
        self.assertEqual(r5.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.circle.members.count(), 4)


class CircleDetailTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username='admin3', email='admin3@example.com', password='pw123456')
        self.client.force_authenticate(self.admin)
        response = self.client.post(reverse('circle-create'), {'name': 'Detail Test', 'contribution_amount': 3000})
        self.circle = Circle.objects.get(id=response.data['id'])

    def test_detail_view_includes_members_and_current_round(self):
        response = self.client.get(reverse('circle-detail', args=[self.circle.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['members']), 1)
        self.assertIsNotNone(response.data['current_round'])
        self.assertEqual(response.data['members'][0]['is_admin'], True)

    def test_non_member_cannot_view_circle(self):
        outsider = User.objects.create_user(username='outsider2', email='outsider2@example.com', password='pw123456')
        self.client.force_authenticate(outsider)
        response = self.client.get(reverse('circle-detail', args=[self.circle.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
