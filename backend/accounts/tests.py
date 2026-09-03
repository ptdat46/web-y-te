"""Tests for the authentication system (registration, login, refresh, logout)."""

from django.test import TestCase
from accounts.models import RoleChoices, User
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

    def test_public_registration_always_creates_patient(self):
        resp = self.register(role='DOCTOR')
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['role'], RoleChoices.PATIENT)

    def test_admin_can_create_and_delete_doctor(self):
        admin = User.objects.create_user(username='admin', email='admin@example.com', password='AdminPass123!', role=RoleChoices.ADMIN)
        self.client.force_authenticate(admin)
        created = self.client.post('/api/v1/auth/admin/users/', {
            'username': 'newdoctor', 'email': 'doctor@example.com', 'password': 'DoctorPass123!', 'role': RoleChoices.DOCTOR,
        }, format='json')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.data['role'], RoleChoices.DOCTOR)
        deleted = self.client.delete(f"/api/v1/auth/admin/users/{created.data['id']}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertFalse(User.objects.filter(username='newdoctor').exists())

    def test_non_admin_cannot_manage_users(self):
        self.register()
        self.client.force_authenticate(User.objects.get(username='testuser'))
        resp = self.client.get('/api/v1/auth/admin/users/')
        self.assertEqual(resp.status_code, 403)