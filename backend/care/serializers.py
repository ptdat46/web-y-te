from rest_framework import serializers

from accounts.models import User
from accounts.serializers import PublicUserSerializer
from catalog.models import Disease
from .models import Alert, AlertStatus, AuditLog, MedicalRecord, VitalSign


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
            'oxygen_saturation', 'recorded_at', 'notes', 'is_abnormal',
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