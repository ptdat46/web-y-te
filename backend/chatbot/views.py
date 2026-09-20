from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsPatientOrDoctor
from care.audit import log_audit
from care.models import AuditAction
from doctors.models import ConnectionStatus, DoctorPatientConnection

from .models import ChatConversation, ChatMessage, MessageRole
from .serializers import ChatConversationDetailSerializer, ChatConversationSerializer, ChatSendSerializer
from .services import build_patient_context, generate_reply


def can_access_patient(requester, patient):
    """Return whether requester may use chatbot context for exactly patient."""
    if requester.role == 'PATIENT':
        return requester.pk == patient.pk
    if requester.role != 'DOCTOR' or patient.role != 'PATIENT':
        return False
    return DoctorPatientConnection.objects.filter(
        doctor__user=requester,
        patient=patient,
        status=ConnectionStatus.APPROVED,
    ).exists()


def resolve_conversation_target(conversation, requester):
    target = conversation.target_patient
    if target is None and requester.role == 'PATIENT':
        target = requester
    if target is None or not can_access_patient(requester, target):
        raise NotFound('Cuộc trò chuyện không tồn tại.')
    return target


class ConversationViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Conversations whose health context is always scoped to one patient."""
    serializer_class = ChatConversationSerializer
    permission_classes = [IsAuthenticated, IsPatientOrDoctor]

    def get_queryset(self):
        queryset = (
            ChatConversation.objects.filter(user=self.request.user)
            .select_related('target_patient')
            .prefetch_related('messages')
        )
        if self.request.user.role == 'DOCTOR':
            queryset = queryset.filter(
                target_patient__role='PATIENT',
                target_patient__doctor_connections__doctor__user=self.request.user,
                target_patient__doctor_connections__status=ConnectionStatus.APPROVED,
            )
        else:
            queryset = queryset.filter(target_patient=self.request.user)
        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ChatConversationDetailSerializer
        return ChatConversationSerializer

    def perform_create(self, serializer):
        target = serializer.validated_data['target_patient']
        if not can_access_patient(self.request.user, target):
            raise PermissionDenied('Bạn không có quyền truy cập bệnh nhân này.')
        serializer.save(user=self.request.user, target_patient=target)

    def perform_destroy(self, instance):
        log_audit(
            self.request,
            actor=self.request.user,
            action=AuditAction.DELETE,
            obj=instance,
            summary=f'Chat conversation deleted: {instance.pk} for patient {instance.target_patient_id}',
        )
        instance.delete()

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        conversation = self.get_object()
        if not conversation.is_active:
            return Response({'detail': 'Cuộc trò chuyện đã đóng.'}, status=status.HTTP_400_BAD_REQUEST)
        target = resolve_conversation_target(conversation, request.user)
        serializer = ChatSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_text = serializer.validated_data['message']

        context = build_patient_context(target)
        user_message = ChatMessage.objects.create(
            conversation=conversation,
            role=MessageRole.USER,
            content=user_text,
            context_version=context['version'],
            context_hash=context['hash'],
            context_generated_at=context['generated_at'],
        )
        history = [
            {'role': 'assistant' if m.role == MessageRole.ASSISTANT else 'user', 'content': m.content}
            for m in conversation.messages.exclude(pk=user_message.pk)
        ]
        reply_text, red_flag = generate_reply(
            user_text,
            history,
            patient_context=context['content'],
            requester_role=request.user.role,
        )
        ChatMessage.objects.create(
            conversation=conversation,
            role=MessageRole.ASSISTANT,
            content=reply_text,
            red_flag=red_flag,
        )

        if not conversation.title:
            conversation.title = user_text[:50] + ('…' if len(user_text) > 50 else '')
        conversation.save(update_fields=['title', 'updated_at'])
        conversation._prefetched_objects_cache['messages'] = list(
            ChatMessage.objects.filter(conversation=conversation).order_by('created_at')
        )
        return Response(ChatConversationDetailSerializer(conversation).data, status=status.HTTP_200_OK)
