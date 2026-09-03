from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminUser
from doctors.models import ConnectionStatus, DoctorPatientConnection
from .audit import log_audit
from .models import Alert, AlertSeverity, AlertStatus, AuditAction, AuditLog, MedicalRecord, VitalSign
from .serializers import (
    AlertSerializer,
    AlertUpdateSerializer,
    AuditLogSerializer,
    MedicalRecordSerializer,
    VitalSignSerializer,
)


class IsPatientOrDoctorOrAdmin(permissions.BasePermission):
    """Allow authenticated users; object-level checks decide access."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == 'ADMIN':
            return True
        patient = getattr(obj, 'patient', None)
        if patient is None:
            return False
        if patient.id == user.id:
            return True
        if user.role == 'DOCTOR':
            # A doctor can access the record only if connected to the patient
            return DoctorPatientConnection.objects.filter(
                doctor__user=user,
                patient=patient,
                status=ConnectionStatus.APPROVED,
            ).exists()
        return False


class MedicalRecordViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Medical records. Patients see their own; doctors see records of connected
    patients; admins see everything.
    """
    serializer_class = MedicalRecordSerializer
    permission_classes = [IsAuthenticated, IsPatientOrDoctorOrAdmin]

    def get_queryset(self):
        qs = MedicalRecord.objects.select_related('patient', 'doctor', 'disease').all()
        user = self.request.user
        if user.role == 'ADMIN':
            return qs
        if user.role == 'PATIENT':
            return qs.filter(patient=user)
        # DOCTOR: records of connected patients + own authored records
        patient_ids = DoctorPatientConnection.objects.filter(
            doctor__user=user,
            status=ConnectionStatus.APPROVED,
        ).values_list('patient_id', flat=True)
        return qs.filter(Q(patient_id__in=patient_ids) | Q(doctor=user))

    def perform_create(self, serializer):
        user = self.request.user
        patient = serializer.validated_data.get('patient')
        if user.role == 'PATIENT':
            if patient is not None and patient != user:
                raise PermissionDenied('Patients can only create records for themselves.')
            patient = user
        elif patient is None:
            raise ValidationError({'patient_id': 'This field is required for doctors and admins.'})
        elif user.role == 'DOCTOR' and not DoctorPatientConnection.objects.filter(
            doctor__user=user,
            patient=patient,
            status=ConnectionStatus.APPROVED,
        ).exists():
            raise PermissionDenied('You cannot create a record for this patient.')
        record = serializer.save(patient=patient, doctor=user)
        log_audit(
            self.request,
            actor=user,
            action=AuditAction.CREATE,
            obj=record,
            summary=f'Medical record created: {record.title}',
        )

    def perform_update(self, serializer):
        record = self.get_object()
        if 'patient' in serializer.validated_data or 'doctor' in serializer.validated_data:
            raise ValidationError('Record ownership cannot be changed.')
        record = serializer.save()
        log_audit(
            self.request,
            actor=self.request.user,
            action=AuditAction.UPDATE,
            obj=record,
            summary=f'Medical record updated: {record.title}',
        )


class VitalSignViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Vital signs. Patients create their own readings; doctors can create for
    connected patients; everyone can read by same rules as medical records.
    """
    serializer_class = VitalSignSerializer
    permission_classes = [IsAuthenticated, IsPatientOrDoctorOrAdmin]

    def get_queryset(self):
        qs = VitalSign.objects.select_related('patient').all()
        user = self.request.user
        if user.role == 'ADMIN':
            return qs
        if user.role == 'PATIENT':
            return qs.filter(patient=user)
        patient_ids = DoctorPatientConnection.objects.filter(
            doctor__user=user,
            status=ConnectionStatus.APPROVED,
        ).values_list('patient_id', flat=True)
        return qs.filter(patient_id__in=patient_ids)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.validated_data.get('patient')
        user = request.user
        if patient is None:
            patient = user
            if user.role != 'PATIENT' and user.role != 'ADMIN':
                return Response(
                    {'detail': 'Doctors must specify a patient_id.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            allowed = user.role == 'ADMIN'
            allowed = allowed or (user.role == 'PATIENT' and patient.id == user.id)
            allowed = allowed or (user.role == 'DOCTOR' and DoctorPatientConnection.objects.filter(
                doctor__user=user,
                patient=patient,
                status=ConnectionStatus.APPROVED,
            ).exists())
            if not allowed:
                return Response(
                    {'detail': 'You cannot record vitals for this patient.'},
                    status=status.HTTP_403_FORBIDDEN,
                )
        vital = serializer.save(patient=patient)
        log_audit(
            self.request,
            actor=user,
            action=AuditAction.CREATE,
            obj=vital,
            summary=f'Vitals recorded for {patient.username}',
            details=(
                f'temp={vital.temperature}, HR={vital.heart_rate}, '
                f'BP={vital.blood_pressure_sys}/{vital.blood_pressure_dia}, SpO2={vital.oxygen_saturation}'
            ),
        )
        self._maybe_create_alert(vital)
        return Response(self.get_serializer(vital).data, status=status.HTTP_201_CREATED)

    def _maybe_create_alert(self, vital):
        reasons = vital.abnormal_reason()
        if not reasons:
            return
        alert = Alert.objects.create(
            patient=vital.patient,
            created_by=self.request.user,
            title='Abnormal vital signs detected',
            message='Abnormal reading(s): ' + ', '.join(reasons),
            severity=AlertSeverity.HIGH if len(reasons) >= 2 else AlertSeverity.MEDIUM,
            status=AlertStatus.OPEN,
            related_vital=vital,
        )
        log_audit(
            self.request,
            actor=self.request.user,
            action=AuditAction.CREATE,
            obj=alert,
            summary=f'Auto alert triggered for {vital.patient.username}',
            details=alert.message,
        )


class AlertViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Alerts. Read-only listing; status can be updated via PATCH /alerts/{id}/status/.
    """
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated, IsPatientOrDoctorOrAdmin]

    def get_queryset(self):
        qs = Alert.objects.select_related('patient', 'created_by', 'related_vital').all()
        user = self.request.user
        if user.role == 'ADMIN':
            return qs
        if user.role == 'PATIENT':
            return qs.filter(patient=user)
        patient_ids = DoctorPatientConnection.objects.filter(
            doctor__user=user,
            status=ConnectionStatus.APPROVED,
        ).values_list('patient_id', flat=True)
        return qs.filter(patient_id__in=patient_ids)

    @action(detail=True, methods=['patch'])
    def status(self, request, pk=None):
        alert = self.get_object()
        if request.user.role not in ('DOCTOR', 'ADMIN'):
            return Response(
                {'detail': 'Only doctors or admins can update alert status.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = AlertUpdateSerializer(alert, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        alert.status = new_status
        if new_status == AlertStatus.RESOLVED:
            alert.resolved_at = timezone.now()
        else:
            alert.resolved_at = None
        alert.save()
        log_audit(
            self.request,
            actor=request.user,
            action=AuditAction.UPDATE,
            obj=alert,
            summary=f'Alert {alert.pk} set to {new_status}',
        )
        return Response(self.get_serializer(alert).data)


class AuditLogViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Audit trail (ADMIN only). Filter by ?action=CREATE|UPDATE|DELETE,
    ?actor=<user_id>, or ?content_type=<model name>.
    """
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = AuditLog.objects.select_related('actor', 'content_type').all()

    def get_queryset(self):
        qs = super().get_queryset()
        action = self.request.query_params.get('action')
        if action:
            qs = qs.filter(action=action.upper())
        actor = self.request.query_params.get('actor')
        if actor:
            qs = qs.filter(actor_id=actor)
        content_type = self.request.query_params.get('content_type')
        if content_type:
            qs = qs.filter(content_type__model=content_type)
        return qs