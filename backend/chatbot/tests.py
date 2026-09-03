"""Tests for the chatbot: safe replies, red-flag detection, mock fallback."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import RoleChoices, User
from chatbot.services import contains_red_flag, generate_reply


class RedFlagDetectionTests(TestCase):
    def test_common_red_flags(self):
        for text in ['đau ngực', 'khó thở', 'yếu nửa người', 'nói khó', 'ngất', 'đau bụng dữ dội']:
            self.assertTrue(contains_red_flag(text), f'expected red flag: {text}')

    def test_normal_symptoms_are_not_flags(self):
        for text in ['sốt nhẹ', 'ho vài ngày', 'đau đầu nhẹ', 'ngứa da']:
            self.assertFalse(contains_red_flag(text), f'not a red flag: {text}')

    def test_generate_reply_returns_emergency_for_flags(self):
        reply, flag = generate_reply('Tôi đau ngực và khó thở', [])
        self.assertTrue(flag)
        self.assertIn('115', reply)

    def test_generate_reply_mock_fallback_when_ollama_down(self):
        with patch('chatbot.services.call_ollama', side_effect=Exception('down')):
            reply, flag = generate_reply('Tôi bị sốt và ho 2 ngày', [])
            self.assertFalse(flag)
            self.assertIn('không thay thế', reply)


class ChatbotApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='chat.user', email='chat@test.com', password='Password123!')
        self.user.role = RoleChoices.PATIENT
        self.user.save()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_create_conversation(self):
        resp = self.client.post('/api/v1/chat/conversations/', {}, format='json')
        self.assertEqual(resp.status_code, 201)

    def test_send_message_gets_reply(self):
        convo = self.client.post('/api/v1/chat/conversations/', {}, format='json')
        convo_id = convo.data['id']
        resp = self.client.post(
            f'/api/v1/chat/conversations/{convo_id}/send/',
            {'message': 'Tôi bị đau đầu'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        messages = resp.data['messages']
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]['role'], 'USER')
        self.assertEqual(messages[1]['role'], 'ASSISTANT')

    def test_red_flag_message_flagged_in_response(self):
        convo = self.client.post('/api/v1/chat/conversations/', {}, format='json')
        convo_id = convo.data['id']
        resp = self.client.post(
            f'/api/v1/chat/conversations/{convo_id}/send/',
            {'message': 'Đau ngực dữ dội'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.data['messages'][-1]['red_flag'])