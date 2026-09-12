import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.utils import timezone


class RoleChoices(models.TextChoices):
    PATIENT = 'PATIENT', 'Patient'
    DOCTOR = 'DOCTOR', 'Doctor'
    ADMIN = 'ADMIN', 'Admin'


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.PATIENT)
    is_active = models.BooleanField(default=True)
    must_change_password = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['email']),
        ]
        ordering = ['username']

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'


class PatientProfile(models.Model):
    """Extended demographic and clinical information for a patient account."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_profile',
    )
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=30, blank=True)
    emergency_contact = models.CharField(max_length=255, blank=True)
    blood_type = models.CharField(max_length=10, blank=True)
    allergies = models.TextField(blank=True)
    underlying_conditions = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    # Stores a small data URL so local avatar uploads work without object storage.
    avatar_url = models.TextField(max_length=5_000_000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'Patient profile: {self.user.get_full_name() or self.user.username}'


class AuthTokenPurpose(models.TextChoices):
    EMAIL_VERIFICATION = 'EMAIL_VERIFICATION', 'Email verification'
    PASSWORD_RESET = 'PASSWORD_RESET', 'Password reset'


class AuthToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='auth_tokens')
    purpose = models.CharField(max_length=32, choices=AuthTokenPurpose.choices)
    token_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'purpose', 'created_at'])]

    @classmethod
    def issue(cls, user, purpose, ttl_minutes=10):
        raw = secrets.token_urlsafe(32)
        now = timezone.now()
        cls.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=now)
        cls.objects.create(
            user=user,
            purpose=purpose,
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            expires_at=now + timedelta(minutes=ttl_minutes),
        )
        return raw

    @classmethod
    def consume(cls, raw, purpose):
        if not raw:
            return None
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        with transaction.atomic():
            token = cls.objects.select_for_update().select_related('user').filter(
                token_hash=token_hash,
                purpose=purpose,
                used_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).first()
            if token is None:
                return None
            token.used_at = timezone.now()
            token.save(update_fields=['used_at'])
            return token.user
