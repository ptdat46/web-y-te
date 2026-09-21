from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import User
from care.models import MedicalRecord
from doctors.models import ConnectionStatus, DoctorPatientConnection, DoctorProfile

from .models import ChatConversation
from .serializers import ChatConversationSerializer
from .services import build_patient_context, generate_reply
from .views import ConversationViewSet, can_access_patient


class ChatbotAuthorizationTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='doctor', email='doctor@example.com', password='pass', role='DOCTOR'
        )
        self.patient_a = User.objects.create_user(
            username='patient-a', email='a@example.com', password='pass', role='PATIENT'
        )
        self.patient_b = User.objects.create_user(
            username='patient-b', email='b@example.com', password='pass', role='PATIENT'
        )
        profile = DoctorProfile.objects.create(user=self.doctor)
        DoctorPatientConnection.objects.create(
            doctor=profile, patient=self.patient_a, status=ConnectionStatus.APPROVED
        )

    def test_doctor_can_access_only_approved_patient(self):
        self.assertTrue(can_access_patient(self.doctor, self.patient_a))
        self.assertFalse(can_access_patient(self.doctor, self.patient_b))

    def test_context_contains_only_selected_patient(self):
        MedicalRecord.objects.create(
            patient=self.patient_a, doctor=self.doctor, title='A record', notes='A-only note'
        )
        MedicalRecord.objects.create(
            patient=self.patient_b, doctor=self.doctor, title='B record', notes='B-secret note'
        )

        context = build_patient_context(self.patient_a)['content']

        self.assertIn('A-only note', context)
        self.assertNotIn('B-secret note', context)

    def test_patient_serializer_forces_self_target(self):
        request = SimpleNamespace(user=self.patient_a)
        serializer = ChatConversationSerializer(
            data={}, context={'request': request}
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['target_patient'], self.patient_a)

    def test_doctor_must_choose_target(self):
        request = SimpleNamespace(user=self.doctor)
        serializer = ChatConversationSerializer(data={}, context={'request': request})
        self.assertFalse(serializer.is_valid())
        self.assertIn('patient_id', serializer.errors)

    @patch('chatbot.services.call_inference_text', return_value={
        'visual_findings': 'Đã nhận được câu hỏi.',
        'red_flags_check': {'has_red_flag': False},
        'disclaimer': 'Tham khảo.',
    })
    def test_inference_payload_contains_one_context(self, call_inference):
        generate_reply(
            'Tình trạng hiện tại?',
            [],
            patient_context='Bệnh nhân: patient-a\nA-only note',
            requester_role='DOCTOR',
        )
        self.assertEqual(call_inference.call_args.args[0], 'Tình trạng hiện tại?')
        self.assertIn('patient-a', call_inference.call_args.args[2])
        self.assertNotIn('patient-b', call_inference.call_args.args[2])


class ChatbotEndpointTests(TestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='doctor', email='doctor@example.com', password='pass', role='DOCTOR'
        )
        self.patient = User.objects.create_user(
            username='patient', email='patient@example.com', password='pass', role='PATIENT'
        )
        profile = DoctorProfile.objects.create(user=self.doctor)
        DoctorPatientConnection.objects.create(
            doctor=profile, patient=self.patient, status=ConnectionStatus.APPROVED
        )

    def test_doctor_creates_targeted_conversation(self):
        request = APIRequestFactory().post(
            '/chat/conversations/', {'patient_id': self.patient.pk}, format='json'
        )
        force_authenticate(request, user=self.doctor)
        response = ConversationViewSet.as_view({'post': 'create'})(request)
        self.assertEqual(response.status_code, 201)
        conversation = ChatConversation.objects.get()
        self.assertEqual(conversation.user_id, self.doctor.pk)
        self.assertEqual(conversation.target_patient_id, self.patient.pk)

    def test_doctor_cannot_create_unconnected_conversation(self):
        other = User.objects.create_user(
            username='other', email='other@example.com', password='pass', role='PATIENT'
        )
        request = APIRequestFactory().post(
            '/chat/conversations/', {'patient_id': other.pk}, format='json'
        )
        force_authenticate(request, user=self.doctor)
        response = ConversationViewSet.as_view({'post': 'create'})(request)
        self.assertIn(response.status_code, (403, 404))
        self.assertFalse(ChatConversation.objects.exists())
