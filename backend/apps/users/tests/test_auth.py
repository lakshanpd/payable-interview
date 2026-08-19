from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class RegistrationTests(APITestCase):
    def test_register_creates_user(self):
        response = self.client.post(reverse('auth-register'), {
            'username': 'alice',
            'email': 'alice@example.com',
            'password': 'str0ng-password',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='alice').exists())
        user = User.objects.get(username='alice')
        self.assertTrue(user.check_password('str0ng-password'))

    def test_register_duplicate_email_rejected(self):
        User.objects.create_user(username='bob', email='dupe@example.com', password='str0ng-password')
        response = self.client.post(reverse('auth-register'), {
            'username': 'bobby',
            'email': 'dupe@example.com',
            'password': 'str0ng-password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_duplicate_username_rejected(self):
        User.objects.create_user(username='carol', email='carol@example.com', password='str0ng-password')
        response = self.client.post(reverse('auth-register'), {
            'username': 'carol',
            'email': 'other@example.com',
            'password': 'str0ng-password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dan', email='dan@example.com', password='str0ng-password')

    def test_login_returns_jwt_pair(self):
        response = self.client.post(reverse('auth-login'), {
            'email': 'dan@example.com',
            'password': 'str0ng-password',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_wrong_password_rejected(self):
        response = self.client.post(reverse('auth-login'), {
            'email': 'dan@example.com',
            'password': 'wrong-password',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_unknown_email_rejected(self):
        response = self.client.post(reverse('auth-login'), {
            'email': 'ghost@example.com',
            'password': 'str0ng-password',
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
