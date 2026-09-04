from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import RoleChoices, User
from doctors.models import ConnectionStatus, DoctorPatientConnection, DoctorProfile
from .models import Alert, AuditLog, MedicalRecord, VitalSign


def create_user(username, role):
    user = User.objects.create_user(
        username=username,
        email=f'{username}@test.com',
        password='Password123!',
    )
    user.role = role
    user.save(update_fields=['role'])
    return user


class MedicalRecordAuthorizationTests(TestCase):
    def setUp(self):
        self.patient_a = create_user('record.pt.a', RoleChoices.PATIENT)
        self.patient_b = create_user('record.pt.b', RoleChoices.PATIENT)
        self.doctor = create_user('record.dr', RoleChoices.DOCTOR)
        self.doctor_profile = DoctorProfile.objects.create(user=self.doctor)
        self.patient_client = APIClient()
        self.patient_client.force_authenticate(user=self.patient_a)
        self.doctor_client = APIClient()
        self.doctor_client.force_authenticate(user=self.doctor)

    def test_patient_cannot_create_record_for_another_patient(self):
        response = self.patient_client.post(
            '/api/v1/records/',
            {'patient_id': self.patient_b.id, 'title': 'Spoofed record'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(MedicalRecord.objects.exists())

    def test_doctor_cannot_create_record_without_approved_connection(self):
        response = self.doctor_client.post(
            '/api/v1/records/',
            {'patient_id': self.patient_a.id, 'title': 'Unauthorized record'},
            format='json',
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(MedicalRecord.objects.exists())

    def test_connected_doctor_can_create_record(self):
        DoctorPatientConnection.objects.create(
            doctor=self.doctor_profile,
            patient=self.patient_a,
            status=ConnectionStatus.APPROVED,
        )
        response = self.doctor_client.post(
            '/api/v1/records/',
            {'patient_id': self.patient_a.id, 'title': 'Approved record'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['patient']['id'], self.patient_a.id)

    def test_patient_created_record_has_no_doctor(self):
        response = self.patient_client.post(
            '/api/v1/records/',
            {'title': 'Self-reported record'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        record = MedicalRecord.objects.get(title='Self-reported record')
        self.assertIsNone(record.doctor_id)
        self.assertIsNone(response.data['doctor'])

    def test_connected_doctor_sees_records_created_before_connection(self):
        record = MedicalRecord.objects.create(
            patient=self.patient_a,
            title='Earlier record',
        )
        DoctorPatientConnection.objects.create(
            doctor=self.doctor_profile,
            patient=self.patient_a,
            status=ConnectionStatus.APPROVED,
        )
        response = self.doctor_client.get('/api/v1/records/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(record.id, [item['id'] for item in response.data])

    def test_record_patient_cannot_change(self):
        record = MedicalRecord.objects.create(
            patient=self.patient_a,
            doctor=self.doctor,
            title='Original',
        )
        response = self.patient_client.patch(
            f'/api/v1/records/{record.id}/',
            {'patient_id': self.patient_b.id},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        record.refresh_from_db()
        self.assertEqual(record.patient_id, self.patient_a.id)


class AuditLogImmutabilityTests(TestCase):
    def test_audit_log_cannot_be_updated_or_deleted(self):
        actor = create_user('audit.admin', RoleChoices.ADMIN)
        record = MedicalRecord.objects.create(patient=actor, title='Audit target')
        audit = AuditLog.objects.create(
            actor=actor,
            action='CREATE',
            content_type_id=1,
            object_id=record.id,
            summary='test',
        )
        with self.assertRaises(ValueError):
            audit.save()
        with self.assertRaises(ValueError):
            audit.delete()

class AdminDataPrivacyTests(TestCase):
    def test_admin_cannot_access_patient_doctor_data(self):
        admin = create_user('privacy.admin', RoleChoices.ADMIN)
        patient = create_user('privacy.patient', RoleChoices.PATIENT)
        doctor = create_user('privacy.doctor', RoleChoices.DOCTOR)
        doctor_profile = DoctorProfile.objects.create(user=doctor)
        MedicalRecord.objects.create(patient=patient, doctor=doctor, title='Private')
        VitalSign.objects.create(patient=patient, temperature=37)
        Alert.objects.create(patient=patient, created_by=patient, title='Private alert', message='Private')
        DoctorPatientConnection.objects.create(doctor=doctor_profile, patient=patient, status=ConnectionStatus.APPROVED)
        client = APIClient()
        client.force_authenticate(admin)
        for path in ('/api/v1/records/', '/api/v1/vitals/', '/api/v1/alerts/', '/api/v1/connections/'):
            response = client.get(path)
            self.assertEqual(response.status_code, 403)
