"""Tests for the chatbot: safe replies, red-flag detection, mock fallback."""

from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import RoleChoices, User
from chatbot.services import generate_reply



class LlmRoutingTests(TestCase):
    @patch('chatbot.services.call_ollama', return_value='Cần đánh giá thêm.')
    def test_symptoms_are_sent_to_model(self, call_ollama):
        reply, flag = generate_reply('Tôi đau ngực và khó thở', [], 'SpO2: 88%')
        self.assertEqual(reply, 'Cần đánh giá thêm.')
        self.assertFalse(flag)
        messages = call_ollama.call_args.args[0]
        self.assertIn('Tôi đau ngực và khó thở', messages[-1]['content'])
        self.assertIn('SpO2: 88%', messages[1]['content'])

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