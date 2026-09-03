from django.conf import settings
from django.db import models


class ConnectionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    BLOCKED = 'BLOCKED', 'Blocked'


class DoctorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_profile',
    )
    specialty = models.CharField(max_length=255, blank=True)
    hospital = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    bio = models.TextField(blank=True)
    years_of_experience = models.PositiveIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_verified', 'user__last_name', 'user__first_name']
        indexes = [
            models.Index(fields=['specialty']),
            models.Index(fields=['is_verified']),
        ]

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.username} - {self.specialty}'


class DoctorPatientConnection(models.Model):
    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name='connections',
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='doctor_connections',
    )
    status = models.CharField(
        max_length=20,
        choices=ConnectionStatus.choices,
        default=ConnectionStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('doctor', 'patient')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f'{self.doctor} <-> {self.patient.username} [{self.status}]'

    def approve(self):
        self.status = ConnectionStatus.APPROVED
        self.save(update_fields=['status', 'updated_at'])

    def reject(self):
        self.status = ConnectionStatus.REJECTED
        self.save(update_fields=['status', 'updated_at'])