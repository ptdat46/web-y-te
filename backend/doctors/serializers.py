from rest_framework import serializers

from accounts.models import User
from accounts.serializers import PublicUserSerializer
from .models import ConnectionStatus, DoctorPatientConnection, DoctorProfile


class DoctorProfileSerializer(serializers.ModelSerializer):
    """
    Full profile serializer. Used by the owner (doctor) or admins.
    """
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = DoctorProfile
        fields = (
            'id', 'user_id', 'username', 'email',
            'specialty', 'hospital', 'address', 'phone',
            'bio', 'years_of_experience', 'is_verified',
            'created_at', 'updated_at',
        )
        read_only_fields = ('is_verified',)


class PublicDoctorSerializer(serializers.ModelSerializer):
    """
    Public view of a doctor for the search directory. Never exposes contact details.
    """
    user = PublicUserSerializer(read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = DoctorProfile
        fields = (
            'id', 'user', 'full_name',
            'specialty', 'hospital', 'bio',
            'years_of_experience', 'is_verified',
        )

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


class ConnectionSerializer(serializers.ModelSerializer):
    """
    Read/list serializer for doctor-patient connections.
    """
    doctor = PublicDoctorSerializer(read_only=True)
    patient = PublicUserSerializer(read_only=True)

    class Meta:
        model = DoctorPatientConnection
        fields = ('id', 'doctor', 'patient', 'status', 'created_at', 'updated_at')
        read_only_fields = ('status',)


class ConnectionCreateSerializer(serializers.ModelSerializer):
    """
    Create a new connection request. Status is forced to PENDING on creation.
    """
    doctor_id = serializers.PrimaryKeyRelatedField(
        source='doctor',
        queryset=DoctorProfile.objects.all(),
    )
    patient_id = serializers.PrimaryKeyRelatedField(
        source='patient',
        queryset=User.objects.all(),
    )

    class Meta:
        model = DoctorPatientConnection
        fields = ('doctor_id', 'patient_id')

    def validate(self, attrs):
        doctor = attrs['doctor']
        patient = attrs['patient']
        if doctor.user_id == patient.id:
            raise serializers.ValidationError('A doctor cannot connect with themselves.')
        if patient.role != 'PATIENT':
            raise serializers.ValidationError('Connections can only be created for patient accounts.')
        return attrs

    def create(self, validated_data):
        validated_data['status'] = ConnectionStatus.PENDING
        return super().create(validated_data)


class ConnectionStatusUpdateSerializer(serializers.ModelSerializer):
    """Approve / reject a connection request."""
    class Meta:
        model = DoctorPatientConnection
        fields = ('status',)

    def validate_status(self, value):
        if value not in (ConnectionStatus.APPROVED, ConnectionStatus.REJECTED):
            raise serializers.ValidationError('Only APPROVED or REJECTED are allowed here.')
        return value