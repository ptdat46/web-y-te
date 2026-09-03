from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsPatientOrDoctor
from care.audit import log_audit
from care.models import Alert, AuditAction, MedicalRecord, VitalSign
from .models import ChatConversation, ChatMessage, MessageRole
from .serializers import (
    ChatConversationDetailSerializer,
    ChatConversationSerializer,
    ChatSendSerializer,
)
from .services import generate_reply

def build_patient_context(user):
    records = MedicalRecord.objects.filter(patient=user).select_related('disease')[:50]
    vitals = VitalSign.objects.filter(patient=user)[:50]
    alerts = Alert.objects.filter(patient=user)[:50]
    lines = [f'Người dùng: {user.get_full_name() or user.username}; vai trò: {user.role}', 'Bệnh án:']
    lines += [
        f'- {record.created_at.isoformat()} | {record.title} | bệnh: '
        f'{record.disease.name_vi if record.disease else ""} | ghi chú: {record.notes} | '
        f'chẩn đoán: {record.diagnosis} | đơn thuốc: {record.prescription}'
        for record in records
    ]
    lines.append('Sinh hiệu:')
    lines += [
        f'- {vital.recorded_at.isoformat()} | nhiệt độ: {vital.temperature}; '
        f'nhịp tim: {vital.heart_rate}; huyết áp: '
        f'{vital.blood_pressure_sys}/{vital.blood_pressure_dia}; SpO2: '
        f'{vital.oxygen_saturation}; ghi chú: {vital.notes}'
        for vital in vitals
    ]
    lines.append('Cảnh báo:')
    lines += [
        f'- {alert.created_at.isoformat()} | {alert.severity} | {alert.status} | '
        f'{alert.title}: {alert.message}'
        for alert in alerts
    ]
    return '\n'.join(lines)


class ConversationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Chat conversations with the symptom assistant.

    * GET    /chat/conversations/              -> my conversations
    * POST   /chat/conversations/              -> start a new conversation
    * GET    /chat/conversations/{id}/         -> detail incl. messages
    * POST   /chat/conversations/{id}/send/    -> send a message + get reply
    * DELETE /chat/conversations/{id}/         -> delete a conversation
    """
    serializer_class = ChatConversationSerializer
    permission_classes = [IsAuthenticated, IsPatientOrDoctor]

    def get_queryset(self):
        return ChatConversation.objects.filter(user=self.request.user).prefetch_related('messages')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatConversationDetailSerializer
        return ChatConversationSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        log_audit(
            self.request,
            actor=self.request.user,
            action=AuditAction.DELETE,
            obj=instance,
            summary=f'Chat conversation deleted: {instance.pk}',
        )
        instance.delete()

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        conversation = self.get_object()
        serializer = ChatSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_text = serializer.validated_data['message']

        user_message = ChatMessage.objects.create(
            conversation=conversation,
            role=MessageRole.USER,
            content=user_text,
        )

        # Build history for the provider from prior messages (exclude the just-saved user msg)
        history = [
            {'role': 'assistant' if m.role == MessageRole.ASSISTANT else 'user', 'content': m.content}
            for m in conversation.messages.exclude(pk=user_message.pk)
        ]

        reply_text, red_flag = generate_reply(
            user_text,
            history,
            patient_context=build_patient_context(request.user),
        )

        assistant_message = ChatMessage.objects.create(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content=reply_text,
            red_flag=red_flag,
        )

        if not conversation.title:
            title = user_text[:50]
            conversation.title = title + ('…' if len(user_text) > 50 else '')
            conversation.save(update_fields=['title'])

        conversation.save(update_fields=['updated_at'])

        # Refresh the prefetched messages cache so the serializer returns fresh data
        if conversation._prefetched_objects_cache:
            conversation._prefetched_objects_cache['messages'] = list(
                ChatMessage.objects.filter(conversation=conversation).order_by('created_at')
            )

        return Response(
            ChatConversationDetailSerializer(conversation).data,
            status=status.HTTP_200_OK,
        )