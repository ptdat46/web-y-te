"""System checks to ensure everything is wired correctly."""

from django.test import TestCase
from django.urls import reverse, resolve


class UrlWiringTests(TestCase):
    def test_health_endpoint_resolves(self):
        match = resolve('/api/v1/health/')
        self.assertIsNotNone(match.func)

    def test_auth_routes_resolve(self):
        for route in ['/api/v1/auth/register/', '/api/v1/auth/login/', '/api/v1/auth/refresh/']:
            resolve(route)

    def test_resource_routes_resolve(self):
        for route in [
            '/api/v1/doctors/',
            '/api/v1/connections/',
            '/api/v1/records/',
            '/api/v1/vitals/',
            '/api/v1/alerts/',
            '/api/v1/audit-logs/',
            '/api/v1/chat/conversations/',
            '/api/v1/catalog/diseases/',
            '/api/v1/catalog/symptoms/',
        ]:
            resolve(route)