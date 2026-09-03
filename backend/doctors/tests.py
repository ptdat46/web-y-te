"""Tests for doctor profiles, patient-doctor connections, and object-level access."""

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import RoleChoices, User
from doctors.models import ConnectionStatus, DoctorPatientConnection, DoctorProfile


def create_user(username, role):
    user = User.objects.create_user(username=username, email=f'{username}@test.com', password='Password123!')
    user.role = role
    user.save()
    return user


class DoctorFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.doctor = create_user('dr.test', RoleChoices.DOCTOR)
        self.doctor_profile = DoctorProfile.objects.create(
            user=self.doctor,
            specialty='Cardiology',
            hospital='Test Hospital',
            is_verified=True,
        )
        self.patient = create_user('pt.test', RoleChoices.PATIENT)
        self.other_doctor = create_user('dr.other', RoleChoices.DOCTOR)
        DoctorProfile.objects.create(user=self.other_doctor, specialty='Neurology')

        self.client.force_authenticate(user=self.patient)
        self.patient_client = self.client
        self.doctor_client = APIClient()
        self.doctor_client.force_authenticate(user=self.doctor)

    def test_public_doctor_search(self):
        client = APIClient()
        resp = client.get('/api/v1/doctors/?search=cardio')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        # Public serializer must not leak email/phone
        self.assertNotIn('email', resp.data[0])

    def test_patient_sends_connection_request(self):
        resp = self.patient_client.post(
            '/api/v1/connections/',
            {'doctor_id': self.doctor_profile.id, 'patient_id': self.patient.id},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data['status'], 'PENDING')

    def test_duplicate_connection_rejected(self):
        self.patient_client.post(
            '/api/v1/connections/',
            {'doctor_id': self.doctor_profile.id, 'patient_id': self.patient.id},
            format='json',
        )
        resp = self.patient_client.post(
            '/api/v1/connections/',
            {'doctor_id': self.doctor_profile.id, 'patient_id': self.patient.id},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)

    def test_doctor_approves_own_request(self):
        conn = DoctorPatientConnection.objects.create(
            doctor=self.doctor_profile,
            patient=self.patient,
            status=ConnectionStatus.PENDING,
        )
        resp = self.doctor_client.post(
            f'/api/v1/connections/{conn.id}/respond/',
            {'status': 'APPROVED'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        conn.refresh_from_db()
        self.assertEqual(conn.status, 'APPROVED')

    def test_other_doctor_cannot_approve(self):
        conn = DoctorPatientConnection.objects.create(
            doctor=self.doctor_profile,
            patient=self.patient,
            status=ConnectionStatus.PENDING,
        )
        other_client = APIClient()
        other_client.force_authenticate(user=self.other_doctor)
        resp = other_client.post(
            f'/api/v1/connections/{conn.id}/respond/',
            {'status': 'APPROVED'},
            format='json',
        )
        # Queryset scoping hides other doctors' connections entirely -> 404
        self.assertEqual(resp.status_code, 404)


class ObjectPermissionTests(TestCase):
    def setUp(self):
        self.doctor = create_user('dr.perm', RoleChoices.DOCTOR)
        self.profile = DoctorProfile.objects.create(
            user=self.doctor,
            specialty='Cardiology',
            is_verified=True,
        )
        self.patient_a = create_user('pt.a', RoleChoices.PATIENT)
        self.patient_b = create_user('pt.b', RoleChoices.PATIENT)
        self.other = create_user('dr.perm2', RoleChoices.DOCTOR)

        self.pa_client = APIClient()
        self.pa_client.force_authenticate(user=self.patient_a)
        self.pb_client = APIClient()
        self.pb_client.force_authenticate(user=self.patient_b)
        self.doctor_client = APIClient()
        self.doctor_client.force_authenticate(user=self.doctor)

        # Approved connection doctor <-> patient A only
        DoctorPatientConnection.objects.create(
            doctor=self.profile,
            patient=self.patient_a,
            status=ConnectionStatus.APPROVED,
        )

    def test_patient_cannot_see_others_vitals(self):
        # patient B creates a vital
        self.pb_client.post('/api/v1/vitals/', {'heart_rate': 70}, format='json')
        # patient A must not see it
        resp = self.pa_client.get('/api/v1/vitals/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_unconnected_doctor_cannot_see_patient(self):
        other_client = APIClient()
        other_client.force_authenticate(user=self.other)
        resp = other_client.get('/api/v1/vitals/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 0)

    def test_connected_doctor_sees_patient(self):
        self.pa_client.post('/api/v1/vitals/', {'heart_rate': 72}, format='json')
        resp = self.doctor_client.get('/api/v1/vitals/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_vital_abnormal_creates_alert(self):
        resp = self.pa_client.post(
            '/api/v1/vitals/',
            {'temperature': 39.5, 'heart_rate': 130},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data['is_abnormal'])
        alerts = self.pa_client.get('/api/v1/alerts/')
        self.assertEqual(len(alerts.data), 1)
        self.assertEqual(alerts.data[0]['severity'], 'HIGH')