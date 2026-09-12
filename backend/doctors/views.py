from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminUser, IsDoctorOrAdmin, IsPatientOrDoctor
from care.audit import log_audit
from care.models import NotificationType
from messaging.realtime import create_notification
from .models import ConnectionStatus, DoctorPatientConnection, DoctorProfile
from .serializers import (
    ConnectionCreateSerializer,
    ConnectionSerializer,
    DoctorProfileSerializer,
    PublicDoctorSerializer,
)


class IsProfileOwnerOrAdmin(IsDoctorOrAdmin):
    """Allow editing only by the profile owner (doctor) or an admin."""

    def has_object_permission(self, request, view, obj):
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.role == 'ADMIN' or obj.user_id == request.user.id


class DoctorProfileViewSet(viewsets.ModelViewSet):
    """
    Doctor profiles.

    * GET    /doctors/            -> public directory (filterable, searchable)
    * GET    /doctors/{id}/       -> public detail
    * GET    /doctors/me/         -> full profile of the authenticated doctor
    * POST   /doctors/            -> create profile (DOCTOR only)
    * PUT/PATCH /doctors/{id}/    -> update own profile or admin
    """
    queryset = DoctorProfile.objects.select_related('user').all()
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        'user__username',
        'user__first_name',
        'user__last_name',
        'specialty',
        'hospital',
        'bio',
    ]
    ordering_fields = ['years_of_experience', 'created_at', 'is_verified']
    ordering = ['-is_verified', 'user__last_name']

    def get_queryset(self):
        queryset = DoctorProfile.objects.select_related('user').all()
        # The public directory only exposes approved profiles. Admins retain
        # access to unverified profiles for review.
        if self.action in ('list', 'retrieve') and getattr(self.request.user, 'role', None) != 'ADMIN':
            queryset = queryset.filter(is_verified=True)
        return queryset

    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            return [AllowAny()]
        if self.action in ('verify', 'approve', 'reject'):
            return [IsAdminUser()]
        if self.action == 'me':
            return [IsAuthenticated()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsProfileOwnerOrAdmin()]
        return [IsDoctorOrAdmin()]

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return PublicDoctorSerializer
        return DoctorProfileSerializer

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def verify(self, request, pk=None):
        """Approve or reject a doctor's profile verification request."""
        profile = self.get_object()
        decision = str(request.data.get('status', request.data.get('decision', ''))).strip().upper()
        if decision in ('APPROVE', 'APPROVED', 'TRUE'):
            verified = True
        elif decision in ('REJECT', 'REJECTED', 'FALSE'):
            verified = False
        else:
            return Response({'status': 'Use APPROVED or REJECTED.'}, status=status.HTTP_400_BAD_REQUEST)
        profile.is_verified = verified
        profile.save(update_fields=['is_verified', 'updated_at'])
        create_notification(recipient=profile.user, notification_type=NotificationType.SYSTEM, title='Cập nhật xác minh hồ sơ bác sĩ', message='Hồ sơ bác sĩ của bạn đã được phê duyệt.' if verified else 'Hồ sơ bác sĩ của bạn chưa được phê duyệt.', link='/app/profile')
        return Response(DoctorProfileSerializer(profile).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser], url_path='approve')
    def approve(self, request, pk=None):
        profile = self.get_object()
        profile.is_verified = True
        profile.save(update_fields=['is_verified', 'updated_at'])
        return Response(DoctorProfileSerializer(profile).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser], url_path='reject')
    def reject(self, request, pk=None):
        profile = self.get_object()
        profile.is_verified = False
        profile.save(update_fields=['is_verified', 'updated_at'])
        return Response(DoctorProfileSerializer(profile).data)

    @action(detail=False, methods=['get', 'post'], permission_classes=[IsAuthenticated])
    def me(self, request):
        profile = DoctorProfile.objects.select_related('user').filter(user=request.user).first()
        if request.method == 'GET':
            if profile is None:
                return Response({'detail': 'Doctor profile not found.'}, status=status.HTTP_404_NOT_FOUND)
            serializer = DoctorProfileSerializer(profile)
            return Response(serializer.data)
        # POST: create or fully update own profile
        serializer = DoctorProfileSerializer(profile, data=request.data, partial=(profile is not None and request.query_params.get('partial') is not None))
        serializer.is_valid(raise_exception=True)
        if profile is None:
            serializer.save(user=request.user)
        else:
            serializer.save()
        return Response(serializer.data)


class ConnectionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Doctor-patient connections.

    * POST   /connections/            -> patient grants access
    * GET    /connections/            -> list my connections (doctor sees patients,
                                         patient sees doctors) filtered by ?status=
    * GET    /connections/{id}/       -> detail
    * DELETE /connections/{id}/       -> patient revokes access
    """
    serializer_class = ConnectionSerializer
    permission_classes = [IsAuthenticated, IsPatientOrDoctor]

    def get_queryset(self):
        qs = DoctorPatientConnection.objects.select_related('doctor', 'doctor__user', 'patient').all()
        user = self.request.user
        if user.role == 'DOCTOR':
            # Doctors need pending requests to accept/reject them, but never
            # see connections belonging to another doctor.
            qs = qs.filter(doctor__user=user)
        elif user.role == 'PATIENT':
            qs = qs.filter(patient=user)
        else:
            qs = qs.none()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param.upper())
        return qs

    def create(self, request, *args, **kwargs):
        serializer = ConnectionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Only the patient can grant access.
        doctor = serializer.validated_data['doctor']
        patient = serializer.validated_data['patient']
        user = request.user
        is_patient = user.role == 'PATIENT' and patient.id == user.id
        if not is_patient:
            return Response(
                {'detail': 'You can only create a connection involving yourself.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        conn, created = DoctorPatientConnection.objects.get_or_create(
            doctor=doctor,
            patient=patient,
            defaults={'status': ConnectionStatus.PENDING},
        )
        if not created:
            return Response(
                {'detail': 'A connection already exists for this doctor-patient pair.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        create_notification(
            recipient=doctor.user,
            notification_type=NotificationType.CONNECTION,
            title='Yêu cầu kết nối mới',
            message=f'{patient.get_full_name() or patient.username} muốn kết nối với bạn.',
            link='/app/connections',
        )
        return Response(ConnectionSerializer(conn).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        connection = self.get_object()
        if request.user.role != 'DOCTOR' or connection.doctor.user_id != request.user.id:
            return Response({'detail': 'Chỉ bác sĩ liên quan mới có thể xử lý yêu cầu.'}, status=status.HTTP_403_FORBIDDEN)
        requested_status = str(request.data.get('status', '')).upper()
        if requested_status not in (ConnectionStatus.APPROVED, ConnectionStatus.REJECTED):
            return Response({'status': 'Chỉ chấp nhận APPROVED hoặc REJECTED.'}, status=status.HTTP_400_BAD_REQUEST)
        if connection.status != ConnectionStatus.PENDING:
            return Response({'detail': 'Chỉ xử lý được yêu cầu đang chờ duyệt.'}, status=status.HTTP_400_BAD_REQUEST)
        connection.status = requested_status
        connection.save(update_fields=['status', 'updated_at'])
        log_audit(
            request,
            actor=request.user,
            action='UPDATE',
            obj=connection,
            summary=f'Connection {connection.pk} {requested_status}',
            details=f'doctor={connection.doctor.user.username}, patient={connection.patient.username}',
        )
        label = 'đã chấp nhận' if requested_status == ConnectionStatus.APPROVED else 'đã từ chối'
        create_notification(
            recipient=connection.patient,
            notification_type=NotificationType.CONNECTION,
            title='Cập nhật yêu cầu kết nối',
            message=f'Bác sĩ {connection.doctor.user.get_full_name() or connection.doctor.user.username} {label} yêu cầu kết nối của bạn.',
            link='/app/connections',
        )
        return Response(ConnectionSerializer(connection).data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if self.request.user.role != 'PATIENT' or instance.patient_id != self.request.user.id:
            return Response({'detail': 'Chỉ bệnh nhân mới được hủy kết nối.'}, status=status.HTTP_403_FORBIDDEN)
        doctor = instance.doctor.user
        patient = instance.patient
        # Keep the room record for audit/history, but deactivate it immediately.
        from care.models import ChatRoom
        ChatRoom.objects.filter(connection=instance).update(active=False)
        instance.delete()
        create_notification(
            recipient=doctor,
            notification_type=NotificationType.CONNECTION,
            title='Kết nối đã bị hủy',
            message=f'{patient.get_full_name() or patient.username} đã hủy kết nối với bạn.',
            link='/app/connections',
        )
        return Response(status=status.HTTP_204_NO_CONTENT)