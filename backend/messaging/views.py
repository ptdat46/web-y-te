from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from django.db.models import Sum
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.models import RoleChoices
from care.audit import log_audit
from care.models import AuditAction, ChatRoom, P2PMessage, PatientFile, NotificationType
from doctors.models import ConnectionStatus, DoctorPatientConnection
from .serializers import ChatRoomSerializer, P2PMessageSerializer, PatientFileSerializer
from .realtime import create_notification, push_chat_message


def approved_connection(user, connection_id):
    return DoctorPatientConnection.objects.select_related('doctor__user', 'patient').filter(
        pk=connection_id, status=ConnectionStatus.APPROVED
    ).filter(doctor__user=user) if user.role == RoleChoices.DOCTOR else DoctorPatientConnection.objects.select_related('doctor__user', 'patient').filter(
        pk=connection_id, patient=user, status=ConnectionStatus.APPROVED
    )


class ChatRoomViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        connections = DoctorPatientConnection.objects.filter(status=ConnectionStatus.APPROVED)
        if user.role == RoleChoices.DOCTOR:
            connections = connections.filter(doctor__user=user)
        elif user.role == RoleChoices.PATIENT:
            connections = connections.filter(patient=user)
        else:
            connections = connections.none()
        # Bulk-provision rooms for approved connections without per-connection get_or_create.
        approved_ids = list(connections.values_list('id', flat=True))
        if approved_ids:
            existing = set(ChatRoom.objects.filter(connection_id__in=approved_ids).values_list('connection_id', flat=True))
            missing = [ChatRoom(connection_id=cid) for cid in approved_ids if cid not in existing]
            if missing:
                ChatRoom.objects.bulk_create(missing, ignore_conflicts=True)
        qs = ChatRoom.objects.select_related('connection__doctor__user', 'connection__patient').filter(connection__status=ConnectionStatus.APPROVED)
        if user.role == RoleChoices.DOCTOR:
            return qs.filter(connection__doctor__user=user)
        if user.role == RoleChoices.PATIENT:
            return qs.filter(connection__patient=user)
        return qs.none()

    def create(self, request, *args, **kwargs):
        connection = approved_connection(request.user, request.data.get('connection_id')).first()
        if not connection:
            raise PermissionDenied('An approved connection is required.')
        room, _ = ChatRoom.objects.get_or_create(connection=connection, defaults={'active': True})
        if not room.active:
            room.active = True
            room.save(update_fields=['active', 'updated_at'])
        return Response(self.get_serializer(room).data, status=status.HTTP_200_OK)

    def _room(self):
        room = self.get_object()
        if not room.active or not room.connection or room.connection.status != ConnectionStatus.APPROVED:
            raise PermissionDenied('This chat room is inactive.')
        return room

    @action(detail=False, methods=['post'])
    def open(self, request):
        connection = approved_connection(request.user, request.data.get('connection_id')).first()
        if not connection:
            raise PermissionDenied('An approved connection is required.')
        room, _ = ChatRoom.objects.get_or_create(connection=connection, defaults={'active': True})
        if not room.active:
            room.active = True; room.save(update_fields=['active', 'updated_at'])
        return Response(self.get_serializer(room).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get', 'post'], parser_classes=[MultiPartParser, FormParser, JSONParser], url_path='messages')
    def messages(self, request, pk=None):
        room = self._room()
        if request.method == 'GET':
            qs = room.messages.select_related('sender').all()
            after = request.query_params.get('after') or request.query_params.get('after_id')
            if after:
                try: qs = qs.filter(pk__gt=int(after))
                except ValueError: pass
            return Response(P2PMessageSerializer(qs, many=True, context={'request': request}).data)
        serializer = P2PMessageSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        message = serializer.save(room=room, sender=request.user)
        log_audit(
            request,
            actor=request.user,
            action=AuditAction.CREATE,
            obj=message,
            summary=f'Chat message sent in room {room.pk}',
            details=f'has_attachment={bool(message.attachment)}',
        )
        recipient = room.connection.patient if request.user.role == RoleChoices.DOCTOR else room.connection.doctor.user
        create_notification(recipient=recipient, notification_type=NotificationType.MESSAGE,
            title='Tin nhắn mới', message=f'{request.user.get_full_name() or request.user.username} đã gửi tin nhắn.', link=f'/app/chat/doctor/{room.pk}')
        push_chat_message(room.pk, P2PMessageSerializer(message, context={'request': request}).data)
        return Response(P2PMessageSerializer(message, context={'request': request}).data, status=status.HTTP_201_CREATED)


class PatientFileViewSet(viewsets.ModelViewSet):
    serializer_class = PatientFileSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ['get', 'post', 'head', 'options', 'delete']

    def get_queryset(self):
        user = self.request.user
        if user.role == RoleChoices.PATIENT:
            return PatientFile.objects.filter(patient=user)
        if user.role == RoleChoices.DOCTOR:
            pids = DoctorPatientConnection.objects.filter(doctor__user=user, status=ConnectionStatus.APPROVED).values_list('patient_id', flat=True)
            qs = PatientFile.objects.filter(patient_id__in=pids)
            patient_id = self.request.query_params.get('patient_id')
            if patient_id:
                qs = qs.filter(patient_id=patient_id)
            return qs
        return PatientFile.objects.none()

    @action(detail=False, methods=['get'])
    def quota(self, request):
        if request.user.role != RoleChoices.PATIENT:
            raise PermissionDenied('Only patients have a medical file quota.')
        limit = 100 * 1024 * 1024
        used = PatientFile.objects.filter(patient=request.user).aggregate(total=Sum('size')).get('total') or 0
        return Response({'used_bytes': used, 'limit_bytes': limit, 'remaining_bytes': max(limit - used, 0), 'used_mb': round(used / (1024 * 1024), 2), 'limit_mb': 100, 'remaining_mb': round(max(limit - used, 0) / (1024 * 1024), 2)})

    def perform_create(self, serializer):
        if self.request.user.role != RoleChoices.PATIENT:
            raise PermissionDenied('Only patients can upload files.')
        instance = serializer.save(patient=self.request.user)
        log_audit(
            self.request,
            actor=self.request.user,
            action=AuditAction.CREATE,
            obj=instance,
            summary=f'Patient file uploaded: {instance.original_name}',
            details=f'size={instance.size}',
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if request.user.role != RoleChoices.PATIENT or instance.patient_id != request.user.id:
            raise PermissionDenied('Only the patient can delete files.')
        log_audit(
            request,
            actor=request.user,
            action=AuditAction.DELETE,
            obj=instance,
            summary=f'Patient file deleted: {instance.original_name}',
        )
        if instance.file:
            instance.file.delete(save=False)
        return super().destroy(request, *args, **kwargs)
