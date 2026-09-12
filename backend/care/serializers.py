from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from accounts.serializers import PublicUserSerializer
from catalog.models import Disease
from .models import (
    Alert, AlertStatus, AuditLog, Appointment, AppointmentStatus,
    MedicalRecord, MedicationLog, MedicationSchedule, Notification, VitalSign,
)


class MedicationScheduleSerializer(serializers.ModelSerializer):
    patient = PublicUserSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(source='patient', queryset=User.objects.filter(role='PATIENT'), write_only=True, required=False)
    taken_today = serializers.SerializerMethodField()

    class Meta:
        model = MedicationSchedule
        fields = ('id', 'patient', 'patient_id', 'name', 'dosage', 'frequency', 'instructions', 'start_date', 'end_date', 'reminder_time', 'reminder_enabled', 'reminder_times', 'is_active', 'taken_today', 'created_at', 'updated_at')
        read_only_fields = ('created_at', 'updated_at', 'taken_today')

    def get_taken_today(self, obj):
        return obj.logs.filter(scheduled_date=timezone.localdate(), status=MedicationLog.Status.TAKEN).exists()

    def validate(self, attrs):
        start, end = attrs.get('start_date', getattr(self.instance, 'start_date', None)), attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if end and start and end < start:
            raise serializers.ValidationError({'end_date': 'End date must be on or after start date.'})
        return attrs


class MedicationLogSerializer(serializers.ModelSerializer):
    schedule = MedicationScheduleSerializer(read_only=True)
    schedule_id = serializers.PrimaryKeyRelatedField(source='schedule', queryset=MedicationSchedule.objects.all(), write_only=True)

    class Meta:
        model = MedicationLog
        fields = ('id', 'schedule', 'schedule_id', 'scheduled_date', 'taken_at', 'status', 'notes', 'created_at', 'updated_at')
        read_only_fields = ('taken_at', 'created_at', 'updated_at')

    def validate(self, attrs):
        schedule = attrs.get('schedule', self.instance.schedule if self.instance else None)
        day = attrs.get('scheduled_date', self.instance.scheduled_date if self.instance else timezone.localdate())
        if schedule and not schedule.is_scheduled_on(day):
            raise serializers.ValidationError({'scheduled_date': 'Date is outside the medication schedule.'})
        if attrs.get('status') == MedicationLog.Status.TAKEN:
            attrs['taken_at'] = timezone.now()
        return attrs


class AppointmentSerializer(serializers.ModelSerializer):
    patient = PublicUserSerializer(read_only=True)
    doctor = PublicUserSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(source='patient', queryset=User.objects.filter(role='PATIENT'), write_only=True, required=False)
    doctor_id = serializers.PrimaryKeyRelatedField(source='doctor', queryset=User.objects.filter(role='DOCTOR'), write_only=True, required=False)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Appointment
        fields = ('id', 'patient', 'patient_id', 'doctor', 'doctor_id', 'scheduled_at', 'duration_minutes', 'reason', 'notes', 'location', 'status', 'status_label', 'doctor_response', 'responded_at', 'reminder_enabled', 'reminder_sent_at', 'created_at', 'updated_at')
        read_only_fields = ('status', 'status_label', 'doctor_response', 'responded_at', 'reminder_sent_at', 'created_at', 'updated_at')

    def validate_scheduled_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('Appointment date must be in the future.')
        return value

    def validate(self, attrs):
        doctor = attrs.get('doctor', getattr(self.instance, 'doctor', None))
        patient = attrs.get('patient', getattr(self.instance, 'patient', None))
        if doctor and doctor.role != 'DOCTOR':
            raise serializers.ValidationError({'doctor_id': 'Appointment doctor must have a doctor account.'})
        if patient and patient.role != 'PATIENT':
            raise serializers.ValidationError({'patient_id': 'Appointment patient must have a patient account.'})
        return attrs


class MedicalRecordSerializer(serializers.ModelSerializer):
    patient = PublicUserSerializer(read_only=True)
    doctor = PublicUserSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        source='patient',
        queryset=User.objects.filter(role='PATIENT'),
        write_only=True,
        required=False,
    )
    disease_id = serializers.PrimaryKeyRelatedField(
        source='disease',
        queryset=Disease.objects.all(),
        write_only=True,
        required=False,
    )
    disease_name = serializers.CharField(source='disease.name_vi', read_only=True)

    class Meta:
        model = MedicalRecord
        fields = (
            'id', 'patient', 'doctor', 'patient_id', 'disease', 'disease_id', 'disease_name',
            'title', 'notes', 'diagnosis', 'prescription',
            'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def validate_patient_id(self, value):
        if value.role != 'PATIENT':
            raise serializers.ValidationError('Medical records can only target patient accounts.')
        if self.instance is not None and value != self.instance.patient:
            raise serializers.ValidationError('The patient cannot be changed after creation.')
        return value


class NotificationSerializer(serializers.ModelSerializer):
    notification_type_label = serializers.CharField(source='get_notification_type_display', read_only=True)

    class Meta:
        model = Notification
        fields = (
            'id', 'notification_type', 'notification_type_label', 'title', 'message',
            'link', 'is_read', 'created_at',
        )
        read_only_fields = fields


class VitalSignSerializer(serializers.ModelSerializer):
    patient = PublicUserSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        source='patient',
        queryset=User.objects.all(),
        write_only=True,
        required=False,
    )
    is_abnormal = serializers.SerializerMethodField()

    class Meta:
        model = VitalSign
        fields = (
            'id', 'patient', 'patient_id',
            'temperature', 'heart_rate',
            'blood_pressure_sys', 'blood_pressure_dia',
            'oxygen_saturation', 'weight_kg', 'blood_glucose',
            'recorded_at', 'notes', 'is_abnormal',
            'created_at', 'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def get_is_abnormal(self, obj):
        return obj.is_abnormal()


class AlertSerializer(serializers.ModelSerializer):
    patient = PublicUserSerializer(read_only=True)
    created_by = PublicUserSerializer(read_only=True)

    class Meta:
        model = Alert
        fields = (
            'id', 'patient', 'created_by',
            'title', 'message', 'severity', 'status',
            'related_vital', 'created_at', 'resolved_at',
        )
        read_only_fields = ('created_at', 'resolved_at', 'created_by')


class AlertUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = ('status',)

    def validate_status(self, value):
        if value not in AlertStatus.values:
            raise serializers.ValidationError('Invalid alert status.')
        return value


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Read-only view of the audit trail, used by admins.
    """
    actor = PublicUserSerializer(read_only=True)
    content_type_name = serializers.CharField(source='content_type.model', read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            'id', 'actor', 'action', 'content_type', 'content_type_name',
            'object_id', 'summary', 'details', 'ip_address', 'created_at',
        )
        read_only_fields = fields