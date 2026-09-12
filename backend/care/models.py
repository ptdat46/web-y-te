from pathlib import Path
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
    weight_kg = models.FloatField(null=True, blank=True)            # kg
    blood_glucose = models.FloatField(null=True, blank=True)        # mmol/L
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
        if self.blood_glucose is not None:
            checks.append(self.blood_glucose < 3.9 or self.blood_glucose > 7.8)
        return any(checks)

    def abnormal_reason(self):
        """Returns a human-readable list of abnormal values detected."""
        reasons = []
        if self.temperature is not None and (self.temperature > 38.5 or self.temperature < 35.0):
            reasons.append(f'nhiệt độ {self.temperature}°C')
        if self.heart_rate is not None and (self.heart_rate > 120 or self.heart_rate < 50):
            reasons.append(f'nhịp tim {self.heart_rate} nhịp/phút')
        if self.blood_pressure_sys is not None and (self.blood_pressure_sys > 180 or self.blood_pressure_sys < 90):
            reasons.append(f'huyết áp tâm thu {self.blood_pressure_sys} mmHg')
        if self.blood_pressure_dia is not None and (self.blood_pressure_dia > 110 or self.blood_pressure_dia < 60):
            reasons.append(f'huyết áp tâm trương {self.blood_pressure_dia} mmHg')
        if self.oxygen_saturation is not None and self.oxygen_saturation < 90:
            reasons.append(f'SpO₂ {self.oxygen_saturation}%')
        if self.blood_glucose is not None and (self.blood_glucose < 3.9 or self.blood_glucose > 7.8):
            reasons.append(f'đường huyết {self.blood_glucose} mmol/L')
        return reasons


class AlertSeverity(models.TextChoices):
    LOW = 'LOW', 'Thấp'
    MEDIUM = 'MEDIUM', 'Trung bình'
    HIGH = 'HIGH', 'Cao'
    CRITICAL = 'CRITICAL', 'Nghiêm trọng'


class AlertStatus(models.TextChoices):
    OPEN = 'OPEN', 'Mở'
    ACKNOWLEDGED = 'ACKNOWLEDGED', 'Đã ghi nhận'
    RESOLVED = 'RESOLVED', 'Đã xử lý'


class NotificationType(models.TextChoices):
    ALERT = 'ALERT', 'Cảnh báo sức khỏe'
    MEDICAL_RECORD = 'MEDICAL_RECORD', 'Hồ sơ bệnh án'
    CONNECTION = 'CONNECTION', 'Kết nối'
    MESSAGE = 'MESSAGE', 'Tin nhắn'
    MEDICATION_REMINDER = 'MEDICATION_REMINDER', 'Nhắc uống thuốc'
    APPOINTMENT = 'APPOINTMENT', 'Lịch hẹn'
    SYSTEM = 'SYSTEM', 'Hệ thống'


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', 'created_at']),
        ]

    def __str__(self):
        return f'{self.title} ({self.recipient.username})'


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


class MedicationSchedule(models.Model):
    """A recurring medication plan owned by a patient."""
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='medication_schedules')
    name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100, blank=True)
    frequency = models.CharField(max_length=100, blank=True)
    instructions = models.TextField(blank=True)
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    reminder_time = models.TimeField(null=True, blank=True)
    reminder_enabled = models.BooleanField(default=True)
    reminder_times = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'reminder_time', 'name']
        indexes = [models.Index(fields=['patient', 'is_active']), models.Index(fields=['start_date', 'end_date'])]

    def __str__(self):
        return f'{self.name} ({self.patient.username})'

    def is_scheduled_on(self, day=None):
        day = day or timezone.localdate()
        return self.start_date <= day and (self.end_date is None or day <= self.end_date)


class MedicationLog(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Chưa uống'
        TAKEN = 'TAKEN', 'Đã uống'
        MISSED = 'MISSED', 'Bỏ lỡ'

    schedule = models.ForeignKey(MedicationSchedule, on_delete=models.CASCADE, related_name='logs')
    scheduled_date = models.DateField(default=timezone.localdate)
    taken_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    notes = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_date', '-taken_at', '-created_at']
        constraints = [models.UniqueConstraint(fields=['schedule', 'scheduled_date'], name='unique_medication_log_day')]
        indexes = [models.Index(fields=['schedule', 'scheduled_date'])]

    def __str__(self):
        return f'{self.schedule.name} on {self.scheduled_date}: {self.status}'


class AppointmentStatus(models.TextChoices):
    UPCOMING = 'UPCOMING', 'Sắp tới'
    COMPLETED = 'COMPLETED', 'Đã hoàn thành'
    CANCELLED = 'CANCELLED', 'Đã hủy'
    MISSED = 'MISSED', 'Đã lỡ'


class Appointment(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_appointments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor_appointments')
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    reason = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)
    location = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=12, choices=AppointmentStatus.choices, default=AppointmentStatus.UPCOMING)
    doctor_response = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    reminder_enabled = models.BooleanField(default=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at']
        indexes = [models.Index(fields=['patient', 'scheduled_at']), models.Index(fields=['doctor', 'scheduled_at']), models.Index(fields=['status', 'scheduled_at'])]

    def __str__(self):
        return f'Appointment {self.pk}: {self.patient.username} / {self.doctor.username}'

    def cancel(self):
        if self.status != AppointmentStatus.UPCOMING:
            raise ValueError('Only upcoming appointments can be cancelled.')
        self.status = AppointmentStatus.CANCELLED

    def complete(self):
        if self.status != AppointmentStatus.UPCOMING:
            raise ValueError('Only upcoming appointments can be completed.')
        self.status = AppointmentStatus.COMPLETED

    def mark_missed(self):
        if self.status != AppointmentStatus.UPCOMING:
            raise ValueError('Only upcoming appointments can be marked as missed.')
        self.status = AppointmentStatus.MISSED


class ChatRoom(models.Model):
    connection = models.OneToOneField('doctors.DoctorPatientConnection', on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_room')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [models.Index(fields=['active', 'updated_at'])]


def chat_attachment_path(instance, filename):
    safe = Path(filename).name.replace(' ', '_')
    room = getattr(instance, 'room', None)
    conn = getattr(room, 'connection', None) if room else None
    pid = getattr(conn, 'patient_id', None)
    if pid is None:
        return f'chat/orphan/{getattr(instance, "room_id", "unknown")}/{safe}'
    return f'chat/{pid}/{instance.room_id}/{safe}'


class P2PMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to=chat_attachment_path, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [models.Index(fields=['room', 'created_at'])]


def patient_file_path(instance, filename):
    return f'medical-files/{instance.patient_id}/{filename}'


class PatientFile(models.Model):
    patient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_files')
    file = models.FileField(upload_to=patient_file_path)
    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveBigIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [models.Index(fields=['patient', 'uploaded_at'])]

    def save(self, *args, **kwargs):
        if self.file:
            self.original_name = self.original_name or self.file.name.rsplit('/', 1)[-1]
            self.size = self.file.size
            self.content_type = getattr(self.file, 'content_type', '') or self.content_type
        return super().save(*args, **kwargs)


class AuditAction(models.TextChoices):
    CREATE = 'CREATE', 'Create'
    READ = 'READ', 'Read'
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