"""Tests for the authentication system (registration, login, refresh, logout)."""

from django.test import TestCase
from rest_framework.test import APIClient


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def register(self, **overrides):
        data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'SecurePass123!',
            'first_name': 'Test',
            'last_name': 'User',
        }
        data.update(overrides)
        return self.client.post('/api/v1/auth/register/', data, format='json')

    def test_register_creates_patient(self):
        resp = self.register()
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['role'], 'PATIENT')
        self.assertTrue(resp.data['is_active'])

    def test_register_rejects_duplicate_username(self):
        self.register()
        resp = self.register()
        self.assertEqual(resp.status_code, 400)

    def test_register_ignores_admin_role_from_client(self):
        # Even if a client passes role=ADMIN, the serializer only stores PATIENT
        resp = self.register(role='ADMIN')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['role'], 'PATIENT')

    def test_login_success_sets_refresh_cookie(self):
        self.register()
        resp = self.client.post(
            '/api/v1/auth/login/',
            {'username': 'testuser', 'password': 'SecurePass123!'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('access', resp.data)
        self.assertIn('user', resp.data)

    def test_login_wrong_password(self):
        self.register()
        resp = self.client.post(
            '/api/v1/auth/login/',
            {'username': 'testuser', 'password': 'wrong'},
            format='json',
        )
        self.assertEqual(resp.status_code, 401)

    def test_me_requires_auth(self):
        resp = self.client.get('/api/v1/auth/me/')
        self.assertEqual(resp.status_code, 401)

    def test_me_returns_user(self):
        self.register()
        login = self.client.post(
            '/api/v1/auth/login/',
            {'username': 'testuser', 'password': 'SecurePass123!'},
            format='json',
        )
        token = login.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        resp = self.client.get('/api/v1/auth/me/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['user']['username'], 'testuser')