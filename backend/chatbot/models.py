from django.conf import settings
from django.db import models


class ChatConversation(models.Model):
    """A chat thread owned by a user and scoped to one patient."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_conversations',
    )
    target_patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chatbot_target_conversations',
    )
    title = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(
                fields=['user', 'target_patient', 'updated_at'],
                name='chatbot_conv_scope_idx',
            ),
        ]

    def __str__(self):
        target = self.target_patient or self.user
        return f'{self.user.username} - {target.username} - {self.title or "Cuộc trò chuyện #" + str(self.pk)}'


class MessageRole(models.TextChoices):
    USER = 'USER', 'User'
    ASSISTANT = 'ASSISTANT', 'Assistant'


class ChatMessage(models.Model):
    """A message and the non-sensitive metadata for its server context."""
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages',
    )
    role = models.CharField(max_length=10, choices=MessageRole.choices)
    content = models.TextField()
    red_flag = models.BooleanField(default=False)
    context_version = models.CharField(max_length=32, blank=True, default='')
    context_hash = models.CharField(max_length=64, blank=True, default='')
    context_generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.get_role_display()} [{self.conversation_id}]: {self.content[:50]}'
