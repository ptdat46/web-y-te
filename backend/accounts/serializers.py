from rest_framework import serializers
from .models import PatientProfile, RoleChoices, User


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'role', 'role_display', 'is_active', 'email_verified', 'must_change_password')
        read_only_fields = ('id', 'role', 'role_display', 'is_active', 'email_verified', 'must_change_password')


class PatientProfileSerializer(serializers.ModelSerializer):
    """Read/write profile fields for the authenticated account."""

    user = UserSerializer(read_only=True)
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)

    class Meta:
        model = PatientProfile
        fields = (
            'id', 'user', 'first_name', 'last_name', 'phone', 'address',
            'date_of_birth', 'gender', 'emergency_contact', 'blood_type',
            'allergies', 'underlying_conditions', 'current_medications',
            'avatar_url', 'created_at', 'updated_at',
        )
        read_only_fields = ('id', 'user', 'created_at', 'updated_at')

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {})
        if user_data:
            user = instance.user
            for field in ('first_name', 'last_name'):
                if field in user_data:
                    setattr(user, field, user_data[field])
            user.save(update_fields=[field for field in ('first_name', 'last_name') if field in user_data])
        return super().update(instance, validated_data)


class PublicUserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'role_display')


class RegisterSerializer(serializers.ModelSerializer):
    """
    Public registration always creates a PATIENT account.
    DOCTOR/ADMIN accounts are provisioned via `seed_demo` or admins.
    """
    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'first_name', 'last_name')
        extra_kwargs = {'password': {'write_only': True}}

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError('Mật khẩu phải có ít nhất 8 ký tự.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(role=RoleChoices.PATIENT, email_verified=False, **validated_data)
        user.set_password(password)
        user.save(update_fields=['password', 'email_verified'])
        return user

class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'password', 'role', 'is_active')
        read_only_fields = ('id',)

    def validate_role(self, value):
        if value not in (RoleChoices.PATIENT, RoleChoices.DOCTOR):
            raise serializers.ValidationError('Admin không được tạo thêm tài khoản ADMIN.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({'password': 'Mật khẩu là bắt buộc.'})
        user = User.objects.create_user(password=password, **validated_data)
        user.must_change_password = user.role == RoleChoices.DOCTOR
        user.save(update_fields=['must_change_password'])
        return user


class LoginSerializer(serializers.Serializer):
    # ``username`` remains supported for backwards compatibility. New clients
    # should send ``email`` instead.
    username = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if not (attrs.get('email') or attrs.get('username')):
            raise serializers.ValidationError({'email': 'Email hoặc username là bắt buộc.'})
        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Mật khẩu xác nhận không khớp.'})
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError({'new_password': 'Mật khẩu mới phải khác mật khẩu hiện tại.'})
        return attrs