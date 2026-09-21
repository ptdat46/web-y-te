from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

import hashlib
import io
import time
from PIL import Image, UnidentifiedImageError
from django.core.files.base import ContentFile
from django.utils import timezone

from accounts.permissions import IsPatientOrDoctor
from care.audit import log_audit
from care.models import AuditAction
from doctors.models import ConnectionStatus, DoctorPatientConnection

from .models import (
    AttachmentStatus,
    ChatAttachment,
    ChatConversation,
    ChatMessage,
    InferenceStatus,
    MessageRole,
    VisionAnalysis,
)
from .serializers import ChatConversationDetailSerializer, ChatConversationSerializer, ChatSendSerializer
from .services import build_patient_context, call_inference_service, format_inference_reply, generate_reply


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

    @action(detail=True, methods=['post'])
    def vision(self, request, pk=None):
        """Analyze one private image through the internal inference service."""
        conversation = self.get_object()
        if not conversation.is_active:
            return Response({'detail': 'Cuộc trò chuyện đã đóng.'}, status=status.HTTP_400_BAD_REQUEST)
        target = resolve_conversation_target(conversation, request.user)
        context = build_patient_context(target)
        upload = request.FILES.get('image')
        if upload is None:
            return Response({'detail': 'Vui lòng chọn một ảnh.'}, status=status.HTTP_400_BAD_REQUEST)
        allowed = {'image/jpeg', 'image/png', 'image/webp'}
        if upload.content_type not in allowed:
            return Response({'detail': 'Chỉ hỗ trợ JPEG, PNG hoặc WebP.'}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
        if upload.size > 10 * 1024 * 1024:
            return Response({'detail': 'Ảnh vượt quá 10 MB.'}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
        data = upload.read()
        try:
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
        except (UnidentifiedImageError, OSError):
            return Response({'detail': 'File không phải ảnh hợp lệ.'}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)

        digest = hashlib.sha256(data).hexdigest()
        # Keep the original bytes in a private server path; the inference service receives only this request.
        attachment = ChatAttachment.objects.create(
            conversation=conversation,
            patient=target,
            original_name=upload.name[:255],
            content_type=upload.content_type,
            size=len(data),
            sha256=digest,
            status=AttachmentStatus.READY,
        )
        attachment.file.save(upload.name, ContentFile(data), save=True)
        analysis = VisionAnalysis.objects.create(attachment=attachment)
        question = str(request.data.get('message', '')).strip()[:2000]
        started = time.monotonic()
        try:
            result = call_inference_service(question, data, upload.name, upload.content_type, context['content'])
            analysis.result = result
            analysis.status = InferenceStatus.SUCCEEDED
            analysis.model_version = str(result.get('model_version', ''))[:255]
            analysis.schema_version = str(result.get('schema_version', ''))[:80]
            analysis.latency_ms = int((time.monotonic() - started) * 1000)
            analysis.completed_at = timezone.now()
            analysis.save(update_fields=['result', 'status', 'model_version', 'schema_version', 'latency_ms', 'completed_at'])
        except Exception:
            analysis.status = InferenceStatus.FAILED
            analysis.error_code = 'inference_unavailable'
            analysis.latency_ms = int((time.monotonic() - started) * 1000)
            analysis.completed_at = timezone.now()
            analysis.save(update_fields=['status', 'error_code', 'latency_ms', 'completed_at'])
        log_audit(request, actor=request.user, action=AuditAction.CREATE, obj=analysis, summary=f'Vision analysis created: {analysis.pk}')
        return Response({
            'analysis_id': analysis.pk,
            'status': analysis.status,
            'result': analysis.result if analysis.status == InferenceStatus.SUCCEEDED else None,
            'error_code': analysis.error_code,
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='analyses/(?P<analysis_id>[^/.]+)')
    def analysis(self, request, analysis_id=None):
        try:
            analysis = VisionAnalysis.objects.select_related('attachment__conversation').get(
                pk=analysis_id,
                attachment__conversation__user=request.user,
            )
        except VisionAnalysis.DoesNotExist as exc:
            raise NotFound('Kết quả phân tích không tồn tại.') from exc
        resolve_conversation_target(analysis.attachment.conversation, request.user)
        return Response({
            'analysis_id': analysis.pk,
            'status': analysis.status,
            'result': analysis.result if analysis.status == InferenceStatus.SUCCEEDED else None,
            'error_code': analysis.error_code,
        })
