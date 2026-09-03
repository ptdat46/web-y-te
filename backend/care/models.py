from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from catalog.models import Disease


class MedicalRecord(models.Model):
    """
    A patient's medical record entry. Created by a doctor (or admin) for a patient.
    """
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medical_records',
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_records',
    )
    disease = models.ForeignKey(
        Disease,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='medical_records',
    )
    title = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    prescription = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'created_at']),
            models.Index(fields=['doctor']),
        ]

    def __str__(self):
        return f'{self.title} ({self.patient.username})'


class VitalSign(models.Model):
    """
    A patient's vitals reading. Typically recorded by the patient (self-reported)
    or by a connected doctor.
    """
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vitals',
    )
    temperature = models.FloatField(null=True, blank=True)          # °C
    heart_rate = models.PositiveIntegerField(null=True, blank=True)  # bpm
    blood_pressure_sys = models.PositiveIntegerField(null=True, blank=True)  # mmHg
    blood_pressure_dia = models.PositiveIntegerField(null=True, blank=True)  # mmHg
    oxygen_saturation = models.FloatField(null=True, blank=True)    # %
    recorded_at = models.DateTimeField(default=timezone.now)
    notes = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['patient', 'recorded_at']),
        ]

    def __str__(self):
        return f'Vitals for {self.patient.username} @ {self.recorded_at.isoformat()}'

    def is_abnormal(self):
        """
        Simple threshold check used to flag potentially dangerous readings.
        Returns True when any recorded value is outside the normal range.
        """
        checks = []
        if self.temperature is not None:
            checks.append(self.temperature > 38.5 or self.temperature < 35.0)
        if self.heart_rate is not None:
            checks.append(self.heart_rate > 120 or self.heart_rate < 50)
        if self.blood_pressure_sys is not None:
            checks.append(self.blood_pressure_sys > 180 or self.blood_pressure_sys < 90)
        if self.blood_pressure_dia is not None:
            checks.append(self.blood_pressure_dia > 110 or self.blood_pressure_dia < 60)
        if self.oxygen_saturation is not None:
            checks.append(self.oxygen_saturation < 90)
        return any(checks)

    def abnormal_reason(self):
        """Returns a human-readable list of abnormal values detected."""
        reasons = []
        if self.temperature is not None and (self.temperature > 38.5 or self.temperature < 35.0):
            reasons.append(f'temperature {self.temperature}°C')
        if self.heart_rate is not None and (self.heart_rate > 120 or self.heart_rate < 50):
            reasons.append(f'heart rate {self.heart_rate} bpm')
        if self.blood_pressure_sys is not None and (self.blood_pressure_sys > 180 or self.blood_pressure_sys < 90):
            reasons.append(f'systolic {self.blood_pressure_sys} mmHg')
        if self.blood_pressure_dia is not None and (self.blood_pressure_dia > 110 or self.blood_pressure_dia < 60):
            reasons.append(f'diastolic {self.blood_pressure_dia} mmHg')
        if self.oxygen_saturation is not None and self.oxygen_saturation < 90:
            reasons.append(f'SpO2 {self.oxygen_saturation}%')
        return reasons


class AlertSeverity(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    CRITICAL = 'CRITICAL', 'Critical'


class AlertStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Acknowledged'
    RESOLVED = 'RESOLVED', 'Resolved'


class Alert(models.Model):
    """
    A health alert triggered automatically (e.g. abnormal vitals) or manually.
    """
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alerts',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authored_alerts',
    )
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    severity = models.CharField(max_length=20, choices=AlertSeverity.choices, default=AlertSeverity.MEDIUM)
    status = models.CharField(max_length=20, choices=AlertStatus.choices, default=AlertStatus.OPEN)
    related_vital = models.ForeignKey(
        'VitalSign',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['severity']),
        ]

    def __str__(self):
        return f'{self.get_severity_display()} alert: {self.title}'


class AuditAction(models.TextChoices):
    CREATE = 'CREATE', 'Create'
    UPDATE = 'UPDATE', 'Update'
    DELETE = 'DELETE', 'Delete'


class AuditLog(models.Model):
    """
    Immutable audit trail of important actions on protected models.
    Uses a GenericForeignKey so any model can be tracked without coupling.
    """
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=10, choices=AuditAction.choices)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    summary = models.CharField(max_length=255)
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['actor', 'created_at']),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError('AuditLog entries are immutable.')
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('AuditLog entries cannot be deleted.')

    def __str__(self):
        return f'{self.action} {self.content_type.model} #{self.object_id} by {self.actor or "system"}'