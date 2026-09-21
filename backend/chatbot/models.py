from django.conf import settings
from django.db import models


class ChatConversation(models.Model):
    """A chat thread owned by a user and scoped to one patient."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_conversations')
    target_patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='chatbot_target_conversations')
    title = models.CharField(max_length=255, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [models.Index(fields=['user', 'target_patient', 'updated_at'], name='chatbot_conv_scope_idx')]

    def __str__(self):
        target = self.target_patient or self.user
        return f'{self.user.username} - {target.username} - {self.title or "Cuộc trò chuyện #" + str(self.pk)}'


class MessageRole(models.TextChoices):
    USER = 'USER', 'User'
    ASSISTANT = 'ASSISTANT', 'Assistant'


class ChatMessage(models.Model):
    """A message and the non-sensitive metadata for its server context."""
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name='messages')
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


class AttachmentStatus(models.TextChoices):
    QUARANTINED = 'QUARANTINED', 'Quarantined'
    READY = 'READY', 'Ready'
    REJECTED = 'REJECTED', 'Rejected'
    DELETED = 'DELETED', 'Deleted'


def chatbot_attachment_path(instance, filename):
    import uuid
    suffix = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'bin'
    return f'chatbot/{instance.patient_id}/{uuid.uuid4().hex}.{suffix}'


class ChatAttachment(models.Model):
    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, related_name='attachments')
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chatbot_attachments')
    file = models.FileField(upload_to=chatbot_attachment_path)
    original_name = models.CharField(max_length=255, blank=True, default='')
    content_type = models.CharField(max_length=100, blank=True, default='')
    size = models.PositiveBigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, default='')
    status = models.CharField(max_length=20, choices=AttachmentStatus.choices, default=AttachmentStatus.QUARANTINED)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['patient', 'sha256']),
            models.Index(fields=['status', 'created_at']),
        ]


class InferenceStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    SUCCEEDED = 'SUCCEEDED', 'Succeeded'
    FAILED = 'FAILED', 'Failed'


class VisionAnalysis(models.Model):
    attachment = models.OneToOneField(ChatAttachment, on_delete=models.CASCADE, related_name='analysis')
    status = models.CharField(max_length=20, choices=InferenceStatus.choices, default=InferenceStatus.PENDING)
    result = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=80, blank=True, default='')
    model_version = models.CharField(max_length=255, blank=True, default='')
    schema_version = models.CharField(max_length=80, blank=True, default='')
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'created_at'])]
