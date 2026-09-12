from django.db.models import Q
from django.http import HttpResponse, StreamingHttpResponse
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAdminUser, IsPatientOrDoctor as PatientDoctorRolePermission
from doctors.models import ConnectionStatus, DoctorPatientConnection
from .audit import log_audit
from .models import (
    Alert, AlertSeverity, AlertStatus, AuditAction, AuditLog, Appointment,
    AppointmentStatus, MedicationLog, MedicationSchedule, MedicalRecord,
    Notification, NotificationType, VitalSign,
)
from .serializers import (
    AlertSerializer,
    AlertUpdateSerializer,
    AuditLogSerializer,
    MedicalRecordSerializer,
    VitalSignSerializer,
    NotificationSerializer, MedicationLogSerializer, MedicationScheduleSerializer,
    AppointmentSerializer,
)
from .pdf import build_medical_record_pdf
from messaging.realtime import create_notification
from .exports import apply_date_range, csv_row


class MedicationScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = MedicationScheduleSerializer
    permission_classes = [IsAuthenticated, PatientDoctorRolePermission]

    def get_queryset(self):
        qs = MedicationSchedule.objects.select_related('patient')
        user = self.request.user
        if user.role == 'PATIENT':
            return qs.filter(patient=user)
        if user.role == 'DOCTOR':
            patient_ids = DoctorPatientConnection.objects.filter(doctor__user=user, status=ConnectionStatus.APPROVED).values_list('patient_id', flat=True)
            return qs.filter(patient_id__in=patient_ids)
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        patient = serializer.validated_data.get('patient')
        if user.role != 'PATIENT' or (patient and patient != user):
            raise PermissionDenied('Only patients can create medication schedules for themselves.')
        serializer.save(patient=user)

    def perform_update(self, serializer):
        if self.request.user.role != 'PATIENT' or serializer.instance.patient_id != self.request.user.id:
            raise PermissionDenied('Only the patient can update this medication schedule.')
        if 'patient' in serializer.validated_data:
            raise ValidationError({'patient_id': 'The patient cannot be changed.'})
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'PATIENT' or self.get_object().patient_id != request.user.id:
            raise PermissionDenied('Only the patient can delete this medication schedule.')
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        schedule = self.get_object()
        if request.user.role != 'PATIENT' or schedule.patient_id != request.user.id:
            raise PermissionDenied('Only the patient can toggle this medication schedule.')
        schedule.is_active = not schedule.is_active
        schedule.save(update_fields=['is_active', 'updated_at'])
        return Response(self.get_serializer(schedule).data)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        schedule = self.get_object()
        if request.user.role != 'PATIENT' or schedule.patient_id != request.user.id:
            raise PermissionDenied('Only the schedule owner can confirm medication.')
        day = timezone.localdate()
        log = MedicationLog.objects.filter(schedule=schedule, scheduled_date=day).first()
        if log and log.status == MedicationLog.Status.TAKEN:
            return Response(self.get_serializer(schedule).data)
        log, _ = MedicationLog.objects.get_or_create(schedule=schedule, scheduled_date=day)
        log.status = MedicationLog.Status.TAKEN
        log.taken_at = timezone.now()
        if request.data.get('notes') is not None:
            log.notes = str(request.data['notes'])[:500]
        log.save(update_fields=['status', 'taken_at', 'notes', 'updated_at'])
        log_audit(
            self.request,
            actor=self.request.user,
            action=AuditAction.UPDATE,
            obj=log,
            summary=f'Medication {schedule.name} confirmed taken',
            details=f'schedule_id={schedule.pk}, log_id={log.pk}',
        )
        return Response(self.get_serializer(schedule).data)

    @action(detail=False, methods=['get'])
    def today(self, request):
        day = timezone.localdate()
        schedules = list(self.get_queryset().filter(is_active=True, start_date__lte=day).filter(Q(end_date__isnull=True) | Q(end_date__gte=day)))
        for schedule in schedules:
            MedicationLog.objects.get_or_create(schedule=schedule, scheduled_date=day)
        return Response(self.get_serializer(schedules, many=True).data)


class MedicationLogViewSet(viewsets.ModelViewSet):
    serializer_class = MedicationLogSerializer
    permission_classes = [IsAuthenticated, PatientDoctorRolePermission]

    def get_queryset(self):
        qs = MedicationLog.objects.select_related('schedule', 'schedule__patient')
        user = self.request.user
        if user.role == 'PATIENT':
            return qs.filter(schedule__patient=user)
        if user.role == 'DOCTOR':
            ids = DoctorPatientConnection.objects.filter(doctor__user=user, status=ConnectionStatus.APPROVED).values_list('patient_id', flat=True)
            return qs.filter(schedule__patient_id__in=ids)
        return qs.none()

    def perform_create(self, serializer):
        schedule = serializer.validated_data['schedule']
        if self.request.user.role != 'PATIENT' or schedule.patient_id != self.request.user.id:
            raise PermissionDenied('Only the schedule owner can create medication logs.')
        serializer.save()

    def perform_update(self, serializer):
        if self.request.user.role != 'PATIENT' or serializer.instance.schedule.patient_id != self.request.user.id:
            raise PermissionDenied('Only the schedule owner can update medication logs.')
        if 'schedule' in serializer.validated_data:
            raise ValidationError({'schedule_id': 'The schedule cannot be changed.'})
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if request.user.role != 'PATIENT' or self.get_object().schedule.patient_id != request.user.id:
            raise PermissionDenied('Only the schedule owner can delete medication logs.')
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        log = self.get_object()
        if request.user.role != 'PATIENT' or log.schedule.patient_id != request.user.id:
            raise PermissionDenied('Only the patient can confirm medication.')
        if log.scheduled_date > timezone.localdate():
            raise ValidationError({'scheduled_date': 'Cannot confirm a future medication dose.'})
        if log.status == MedicationLog.Status.TAKEN:
            return Response(self.get_serializer(log).data)
        log.status = MedicationLog.Status.TAKEN
        log.taken_at = timezone.now()
        if request.data.get('notes') is not None:
            log.notes = str(request.data['notes'])[:500]
        log.save(update_fields=['status', 'taken_at', 'notes', 'updated_at'])
        return Response(self.get_serializer(log).data)


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated, PatientDoctorRolePermission]
    http_method_names = ['get', 'post', 'put', 'patch', 'head', 'options']

    def get_queryset(self):
        qs = Appointment.objects.select_related('patient', 'doctor')
        user = self.request.user
        if user.role == 'PATIENT':
            qs = qs.filter(patient=user)
        elif user.role == 'DOCTOR':
            qs = qs.filter(doctor=user)
        else:
            return qs.none()
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        patient = serializer.validated_data.get('patient')
        doctor = serializer.validated_data.get('doctor')
        if user.role == 'PATIENT':
            if patient and patient != user:
                raise PermissionDenied('Patients can only create appointments for themselves.')
            patient = user
            if doctor is None:
                raise ValidationError({'doctor_id': 'This field is required.'})
            if not DoctorPatientConnection.objects.filter(doctor__user=doctor, patient=user, status=ConnectionStatus.APPROVED).exists():
                raise PermissionDenied('You can only book an appointment with a connected doctor.')
        elif user.role == 'DOCTOR':
            if doctor and doctor != user:
                raise PermissionDenied('Doctors can only create appointments for themselves.')
            doctor = user
            if patient is None:
                raise ValidationError({'patient_id': 'This field is required.'})
            if not DoctorPatientConnection.objects.filter(doctor__user=user, patient=patient, status=ConnectionStatus.APPROVED).exists():
                raise PermissionDenied('You can only create appointments for connected patients.')
        else:
            raise PermissionDenied('Only patients and doctors can create appointments.')
        appointment = serializer.save(patient=patient, doctor=doctor)
        create_notification(recipient=patient if user.role == 'DOCTOR' else doctor, notification_type=NotificationType.APPOINTMENT, title='Lịch hẹn mới', message='Bạn có một lịch hẹn mới.', link='/app/appointments')

    def update(self, request, *args, **kwargs):
        appointment = self.get_object()
        if appointment.status != AppointmentStatus.UPCOMING:
            return Response({'detail': 'Only upcoming appointments can be updated.'}, status=status.HTTP_400_BAD_REQUEST)
        if request.user.role == 'PATIENT' and appointment.patient_id != request.user.id:
            raise PermissionDenied()
        if request.user.role == 'DOCTOR' and appointment.doctor_id != request.user.id:
            raise PermissionDenied()
        if 'patient_id' in request.data or 'doctor_id' in request.data:
            return Response({'detail': 'Appointment participants cannot be changed.'}, status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        if request.user.role == 'PATIENT' and appointment.patient_id != request.user.id:
            raise PermissionDenied()
        if request.user.role == 'DOCTOR' and appointment.doctor_id != request.user.id:
            raise PermissionDenied()
        try:
            appointment.cancel()
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        appointment.save(update_fields=['status', 'updated_at'])
        log_audit(
            request,
            actor=request.user,
            action=AuditAction.UPDATE,
            obj=appointment,
            summary=f'Appointment {appointment.pk} cancelled',
            details=f'scheduled_at={appointment.scheduled_at}',
        )
        other = appointment.doctor if request.user == appointment.patient else appointment.patient
        create_notification(recipient=other, notification_type=NotificationType.APPOINTMENT, title='Lịch hẹn đã hủy', message='Một lịch hẹn của bạn đã bị hủy.', link='/app/appointments')
        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        appointment = self.get_object()
        if request.user.role != 'DOCTOR' or appointment.doctor_id != request.user.id:
            raise PermissionDenied('Only the attending doctor can complete an appointment.')
        try:
            appointment.complete()
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        appointment.save(update_fields=['status', 'updated_at'])
        log_audit(
            request,
            actor=request.user,
            action=AuditAction.UPDATE,
            obj=appointment,
            summary=f'Appointment {appointment.pk} completed',
            details=f'scheduled_at={appointment.scheduled_at}',
        )
        return Response(self.get_serializer(appointment).data)

    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        appointment = self.get_object()
        if request.user.role != 'DOCTOR' or appointment.doctor_id != request.user.id:
            raise PermissionDenied('Only the attending doctor can respond.')
        if appointment.status != AppointmentStatus.UPCOMING:
            return Response({'detail': 'Only upcoming appointments can receive a response.'}, status=status.HTTP_400_BAD_REQUEST)
        requested_status = str(request.data.get('status', AppointmentStatus.UPCOMING)).upper()
        if requested_status not in (AppointmentStatus.UPCOMING, AppointmentStatus.CANCELLED):
            return Response({'status': 'Only UPCOMING or CANCELLED is valid.'}, status=status.HTTP_400_BAD_REQUEST)
        appointment.doctor_response = str(request.data.get('response', request.data.get('doctor_response', '')))
        appointment.responded_at = timezone.now()
        if requested_status == AppointmentStatus.CANCELLED:
            try:
                appointment.cancel()
            except ValueError as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        appointment.save(update_fields=['status', 'doctor_response', 'responded_at', 'updated_at'])
        create_notification(recipient=appointment.patient, notification_type=NotificationType.APPOINTMENT, title='Phản hồi lịch hẹn', message=appointment.doctor_response or 'Bác sĩ đã phản hồi lịch hẹn của bạn.', link='/app/appointments')
        return Response(self.get_serializer(appointment).data)


class NotificationViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Notification.objects.filter(recipient=self.request.user)
        if self.request.query_params.get('unread') == 'true':
            queryset = queryset.filter(is_read=False)
        return queryset

    @action(detail=True, methods=['patch'])
    def read(self, request, pk=None):
        notification = self.get_object()
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read'])
        return Response(self.get_serializer(notification).data)

    @action(detail=False, methods=['post'], url_path='read-all')
    def read_all(self, request):
        updated = self.get_queryset().filter(is_read=False).update(is_read=True)
        return Response({'updated': updated})


class IsPatientOrDoctor(permissions.BasePermission):
    """Allow patients and doctors; object-level checks decide access."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ('PATIENT', 'DOCTOR'))

    def has_object_permission(self, request, view, obj):
        user = request.user
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
    permission_classes = [IsAuthenticated, IsPatientOrDoctor]

    def get_queryset(self):
        qs = MedicalRecord.objects.select_related('patient', 'doctor', 'disease').all()
        user = self.request.user
        if user.role == 'PATIENT':
            qs = qs.filter(patient=user)
        else:
            # Doctors can only see records while the patient is connected.
            patient_ids = DoctorPatientConnection.objects.filter(
                doctor__user=user,
                status=ConnectionStatus.APPROVED,
            ).values_list('patient_id', flat=True)
            qs = qs.filter(patient_id__in=patient_ids)
        # Date range + ?patient_id= for doctors.
        qs = apply_date_range(qs, self.request.query_params, created_field='created_at')
        patient_param = self.request.query_params.get('patient_id')
        if patient_param and user.role != 'PATIENT':
            try:
                pid = int(patient_param)
            except (TypeError, ValueError):
                raise ValidationError({'patient_id': 'patient_id must be an integer.'})
            if user.role == 'DOCTOR' and not DoctorPatientConnection.objects.filter(
                doctor__user=user,
                patient_id=pid,
                status=ConnectionStatus.APPROVED,
            ).exists():
                raise PermissionDenied('You are not connected to this patient.')
            qs = qs.filter(patient_id=pid)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        patient = serializer.validated_data.get('patient')
        if user.role == 'PATIENT':
            if patient is not None and patient != user:
                raise PermissionDenied('Patients can only create records for themselves.')
            patient = user
        elif patient is None:
            raise ValidationError({'patient_id': 'This field is required for doctors.'})
        elif user.role == 'DOCTOR' and not DoctorPatientConnection.objects.filter(
            doctor__user=user,
            patient=patient,
            status=ConnectionStatus.APPROVED,
        ).exists():
            raise PermissionDenied('You cannot create a record for this patient.')
        record = serializer.save(patient=patient, doctor=user if user.role == 'DOCTOR' else None)
        if user.role == 'DOCTOR':
            create_notification(recipient=patient, notification_type=NotificationType.MEDICAL_RECORD, title='Hồ sơ bệnh án mới', message=f'Bạn có hồ sơ bệnh án mới: {record.title}.', link='/app/records')
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

    @action(detail=False, methods=['get'], url_path='export/csv')
    def export_csv(self, request):
        """Export medical records visible to the current user as CSV."""
        qs = self.filter_queryset(self.get_queryset()).select_related(
            'patient', 'doctor', 'disease',
        )
        row_count = qs.count()
        log_audit(
            request,
            actor=request.user,
            action=AuditAction.READ,
            # An empty export has no record to point at, so anchor its audit
            # entry to the requesting user instead.
            obj=qs.order_by('pk').first() or request.user,
            summary=f'Exported {row_count} medical records to CSV',
            details=f'Rows={row_count}, patient_id={request.query_params.get("patient_id", "-")}',
        )

        def rows():
            yield '\ufeff'
            yield csv_row([
                'ID', 'Ngày tạo', 'Bệnh nhân', 'Bác sĩ', 'Bệnh',
                'Tiêu đề', 'Chẩn đoán', 'Đơn thuốc', 'Ghi chú',
            ])
            for r in qs.iterator(chunk_size=500):
                yield csv_row([
                    r.pk,
                    r.created_at.strftime('%Y-%m-%d %H:%M'),
                    r.patient.get_full_name() or r.patient.username,
                    (r.doctor.get_full_name() or r.doctor.username) if r.doctor else '',
                    r.disease.name_vi if r.disease else '',
                    r.title,
                    r.diagnosis,
                    r.prescription,
                    r.notes,
                ])

        response = StreamingHttpResponse(rows(), content_type='text/csv; charset=utf-8')
        filename = f'medical-records-{timezone.now().strftime("%Y%m%d-%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Render a single medical record as a PDF document."""
        record = self.get_object()
        pdf_bytes = build_medical_record_pdf(record)
        log_audit(
            request,
            actor=request.user,
            action=AuditAction.READ,
            obj=record,
            summary=f'Exported medical record #{record.pk} to PDF',
        )
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="medical-record-{record.pk}.pdf"'
        return response


class VitalSignViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Vital signs. Patients create their own readings; doctors can create for
    connected patients; everyone can read by same rules as medical records.
    """
    serializer_class = VitalSignSerializer
    permission_classes = [IsAuthenticated, IsPatientOrDoctor]

    def get_queryset(self):
        qs = VitalSign.objects.select_related('patient').all()
        user = self.request.user
        if user.role == 'PATIENT':
            qs = qs.filter(patient=user)
        else:
            patient_ids = DoctorPatientConnection.objects.filter(
                doctor__user=user,
                status=ConnectionStatus.APPROVED,
            ).values_list('patient_id', flat=True)
            qs = qs.filter(patient_id__in=patient_ids)
        # Optional ?patient_id= for doctors (must be a connected patient).
        patient_param = self.request.query_params.get('patient_id')
        if patient_param and user.role != 'PATIENT':
            try:
                pid = int(patient_param)
            except (TypeError, ValueError):
                raise ValidationError({'patient_id': 'patient_id must be an integer.'})
            if pid not in qs.values_list('patient_id', flat=True):
                raise PermissionDenied('You are not connected to this patient.')
            qs = qs.filter(patient_id=pid)
        # Date range filter on recorded_at.
        qs = apply_date_range(qs, self.request.query_params, created_field='recorded_at')
        # Optional ?limit= cap (default 200, max 1000), list only. Slicing
        # here would break DRF's retrieve action because get_object() adds a
        # primary-key filter after get_queryset().
        if self.action == 'list':
            limit_param = self.request.query_params.get('limit')
            limit = 200
            if limit_param is not None and limit_param != '':
                try:
                    limit = int(limit_param)
                except (TypeError, ValueError):
                    raise ValidationError({'limit': 'limit must be an integer.'})
                if limit < 1:
                    limit = 1
                elif limit > 1000:
                    limit = 1000
            qs = qs[:limit]
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.validated_data.get('patient')
        user = request.user
        if patient is None:
            patient = user
            if user.role != 'PATIENT':
                return Response(
                    {'detail': 'Doctors must specify a patient_id.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            allowed = user.role == 'PATIENT' and patient.id == user.id
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
                f'BP={vital.blood_pressure_sys}/{vital.blood_pressure_dia}, SpO2={vital.oxygen_saturation}, '
                f'weight={vital.weight_kg}, glucose={vital.blood_glucose}'
            ),
        )
        self._maybe_create_alert(vital)
        return Response(self.get_serializer(vital).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        """Allow only the patient owner to edit a reading; never expose DELETE."""
        vital = self.get_object()
        if request.user.role != 'PATIENT' or vital.patient_id != request.user.id:
            return Response({'detail': 'Only the patient owner can update vitals.'}, status=status.HTTP_403_FORBIDDEN)
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(vital, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        updated = serializer.save()
        log_audit(
            request,
            actor=request.user,
            action=AuditAction.UPDATE,
            obj=updated,
            summary=f'Vitals updated for {updated.patient.username}',
        )
        return Response(self.get_serializer(updated).data)

    def _maybe_create_alert(self, vital):
        reasons = vital.abnormal_reason()
        if not reasons:
            return
        alert = Alert.objects.create(
            patient=vital.patient,
            created_by=self.request.user,
            title='Phát hiện chỉ số sức khỏe bất thường',
            message='Chỉ số bất thường: ' + ', '.join(reasons),
            severity=AlertSeverity.HIGH if len(reasons) >= 2 else AlertSeverity.MEDIUM,
            status=AlertStatus.OPEN,
            related_vital=vital,
        )
        create_notification(
            recipient=vital.patient,
            notification_type=NotificationType.ALERT,
            title=alert.title,
            message=alert.message,
            link='/app/alerts',
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
    permission_classes = [IsAuthenticated, IsPatientOrDoctor]

    def get_queryset(self):
        qs = Alert.objects.select_related('patient', 'created_by', 'related_vital').all()
        user = self.request.user
        if user.role == 'PATIENT':
            return qs.filter(patient=user)
        patient_ids = DoctorPatientConnection.objects.filter(
            doctor__user=user,
            status=ConnectionStatus.APPROVED,
        ).values_list('patient_id', flat=True)
        return qs.filter(patient_id__in=patient_ids)

    @action(detail=True, methods=['post', 'patch'])
    def read(self, request, pk=None):
        """Mark this patient's alert notifications read (not clinical status)."""
        alert = self.get_object()
        if request.user.role != 'PATIENT' or alert.patient_id != request.user.id:
            return Response({'detail': 'Only the patient can mark this alert read.'}, status=status.HTTP_403_FORBIDDEN)
        Notification.objects.filter(recipient=request.user, notification_type=NotificationType.ALERT, title=alert.title, is_read=False).update(is_read=True)
        return Response(self.get_serializer(alert).data)

    @action(detail=True, methods=['post'], url_path='contact-doctor')
    def contact_doctor(self, request, pk=None):
        """Notify every approved doctor connected to the patient."""
        alert = self.get_object()
        if request.user.role != 'PATIENT' or alert.patient_id != request.user.id:
            return Response({'detail': 'Only the patient can contact a doctor.'}, status=status.HTTP_403_FORBIDDEN)
        connections = DoctorPatientConnection.objects.filter(patient=request.user, status=ConnectionStatus.APPROVED).select_related('doctor__user')
        doctors = [conn.doctor.user for conn in connections]
        if not doctors:
            return Response({'detail': 'Bạn chưa có bác sĩ nào được kết nối.'}, status=status.HTTP_400_BAD_REQUEST)
        message = str(request.data.get('message', '')).strip() or f'Bệnh nhân muốn được tư vấn về cảnh báo: {alert.title}.'
        for doctor in doctors:
            create_notification(recipient=doctor, notification_type=NotificationType.MESSAGE, title='Bệnh nhân cần được tư vấn', message=message, link='/app/alerts')
        return Response({'detail': 'Đã gửi yêu cầu liên hệ bác sĩ.', 'notified_doctors': len(doctors)})

    @action(detail=True, methods=['patch'])
    def status(self, request, pk=None):
        alert = self.get_object()
        if request.user.role != 'DOCTOR':
            return Response(
                {'detail': 'Only doctors can update alert status.'},
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