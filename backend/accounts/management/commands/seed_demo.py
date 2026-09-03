"""Seed the database with demo users and sample data.

Usage:
    python manage.py seed_demo

Creates:
    - admin / admin-secure-pass-2026 (ADMIN)
    - dr.nguyen / Test1234! (DOCTOR, verified, Cardiology)
    - patient.tran / Test1234! (PATIENT)
    - dr.le / Test1234! (DOCTOR, verified, Neurology)
    - Approved connection doctor<->patient
    - A couple of vitals + one alert
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import RoleChoices, User
from care.models import Alert, AlertSeverity, AlertStatus, MedicalRecord, VitalSign
from doctors.models import ConnectionStatus, DoctorPatientConnection, DoctorProfile


class Command(BaseCommand):
    help = 'Seed demo users and sample medical data.'

    def handle(self, *args, **options):
        # --- Users ---
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={'email': 'admin@healthcare.dev', 'role': RoleChoices.ADMIN},
        )
        admin.role = RoleChoices.ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.set_password('admin-secure-pass-2026')
        admin.save()

        doctor, _ = User.objects.get_or_create(
            username='dr.nguyen',
            defaults={
                'email': 'dr.nguyen@healthcare.dev',
                'role': RoleChoices.DOCTOR,
                'first_name': 'Nguyen',
                'last_name': 'Van A',
            },
        )
        doctor.role = RoleChoices.DOCTOR
        doctor.first_name = 'Nguyen'
        doctor.last_name = 'Van A'
        doctor.set_password('Test1234!')
        doctor.save()

        patient, _ = User.objects.get_or_create(
            username='patient.tran',
            defaults={
                'email': 'patient.tran@healthcare.dev',
                'role': RoleChoices.PATIENT,
                'first_name': 'Tran',
                'last_name': 'Van B',
            },
        )
        patient.role = RoleChoices.PATIENT
        patient.first_name = 'Tran'
        patient.last_name = 'Van B'
        patient.set_password('Test1234!')
        patient.save()

        doctor2, _ = User.objects.get_or_create(
            username='dr.le',
            defaults={
                'email': 'dr.le@healthcare.dev',
                'role': RoleChoices.DOCTOR,
                'first_name': 'Le',
                'last_name': 'Thi C',
            },
        )
        doctor2.role = RoleChoices.DOCTOR
        doctor2.first_name = 'Le'
        doctor2.last_name = 'Thi C'
        doctor2.set_password('Test1234!')
        doctor2.save()

        # --- Doctor profiles ---
        profile1, _ = DoctorProfile.objects.get_or_create(
            user=doctor,
            defaults={
                'specialty': 'Cardiology',
                'hospital': 'Hanoi Heart Hospital',
                'bio': 'Cardiologist with 15 years of experience.',
                'years_of_experience': 15,
                'is_verified': True,
            },
        )
        DoctorProfile.objects.filter(pk=profile1.pk).update(is_verified=True)

        DoctorProfile.objects.get_or_create(
            user=doctor2,
            defaults={
                'specialty': 'Neurology',
                'hospital': 'Bach Mai Hospital',
                'bio': 'Neurologist focusing on headaches and stroke prevention.',
                'years_of_experience': 10,
                'is_verified': True,
            },
        )

        # --- Connection (approved) ---
        DoctorPatientConnection.objects.get_or_create(
            doctor=profile1,
            patient=patient,
            defaults={'status': ConnectionStatus.APPROVED},
        )

        # --- Vitals history (last 7 days) ---
        now = timezone.now()
        for days_ago in range(7, 0, -1):
            recorded = now - timedelta(days=days_ago)
            VitalSign.objects.get_or_create(
                patient=patient,
                recorded_at=recorded,
                defaults={
                    'temperature': round(random.uniform(36.5, 37.4), 1),
                    'heart_rate': random.randint(62, 88),
                    'blood_pressure_sys': random.randint(105, 138),
                    'blood_pressure_dia': random.randint(65, 89),
                    'oxygen_saturation': round(random.uniform(96.0, 99.0), 1),
                    'notes': 'Self-reported reading',
                },
            )

        # One abnormal vital + alert
        abnormal, _ = VitalSign.objects.get_or_create(
            patient=patient,
            recorded_at=now - timedelta(hours=2),
            defaults={
                'temperature': 39.2,
                'heart_rate': 122,
                'blood_pressure_sys': 152,
                'blood_pressure_dia': 96,
                'oxygen_saturation': 93.0,
                'notes': 'Fever and rapid heartbeat',
            },
        )
        if abnormal.is_abnormal():
            Alert.objects.get_or_create(
                patient=patient,
                related_vital=abnormal,
                defaults={
                    'created_by': patient,
                    'title': 'Abnormal vital signs detected',
                    'message': 'Abnormal reading(s): ' + ', '.join(abnormal.abnormal_reason()),
                    'severity': AlertSeverity.HIGH,
                    'status': AlertStatus.OPEN,
                },
            )

        # --- Medical record ---
        MedicalRecord.objects.get_or_create(
            patient=patient,
            doctor=doctor,
            title='Annual checkup',
            defaults={
                'notes': 'Patient reports occasional mild headaches.',
                'diagnosis': 'Stage 1 hypertension',
                'prescription': 'Amlodipine 5mg daily, follow-up in 3 months.',
            },
        )

        self.stdout.write(self.style.SUCCESS('Demo data seeded.'))
        self.stdout.write('  admin        / admin-secure-pass-2026 (ADMIN)')
        self.stdout.write('  dr.nguyen    / Test1234! (DOCTOR)')
        self.stdout.write('  dr.le        / Test1234! (DOCTOR)')
        self.stdout.write('  patient.tran / Test1234! (PATIENT)')