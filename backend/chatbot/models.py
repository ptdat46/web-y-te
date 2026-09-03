from django.conf import settings
from django.db import models


class ChatConversation(models.Model):
    """
    A chat thread between a user and the symptom assistant.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_conversations',
    )
    title = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.user.username} - {self.title or "Cuộc trò chuyện #" + str(self.pk)}'


class MessageRole(models.TextChoices):
    USER = 'USER', 'User'
    ASSISTANT = 'ASSISTANT', 'Assistant'


class ChatMessage(models.Model):
    """
    A single message inside a conversation.
    """
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=10, choices=MessageRole.choices)
    content = models.TextField()
    red_flag = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.get_role_display()} [{self.conversation_id}]: {self.content[:50]}'