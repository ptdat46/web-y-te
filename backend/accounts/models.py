from django.contrib.auth.models import AbstractUser
from django.db import models


class RoleChoices(models.TextChoices):
    PATIENT = 'PATIENT', 'Patient'
    DOCTOR = 'DOCTOR', 'Doctor'
    ADMIN = 'ADMIN', 'Admin'


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.PATIENT)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=['role']),
            models.Index(fields=['email']),
        ]
        ordering = ['username']

    def __str__(self):
        return f'{self.username} ({self.get_role_display()})'