# Generated manually for medication schedules, logs and appointments.
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('care', '0004_rename_care_notifi_recipie_6d9a42_idx_care_notifi_recipie_75af2a_idx_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='notification_type',
            field=models.CharField(max_length=30, choices=[
                ('ALERT', 'Cảnh báo sức khỏe'), ('MEDICAL_RECORD', 'Hồ sơ bệnh án'),
                ('CONNECTION', 'Kết nối'), ('MESSAGE', 'Tin nhắn'),
                ('MEDICATION_REMINDER', 'Nhắc uống thuốc'), ('APPOINTMENT', 'Lịch hẹn'),
                ('SYSTEM', 'Hệ thống'),
            ]),
        ),
        migrations.CreateModel(
            name='MedicationSchedule',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('dosage', models.CharField(blank=True, max_length=100)),
                ('frequency', models.CharField(blank=True, max_length=100)),
                ('instructions', models.TextField(blank=True)),
                ('start_date', models.DateField(default=django.utils.timezone.localdate)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('reminder_time', models.TimeField(blank=True, null=True)),
                ('reminder_enabled', models.BooleanField(default=True)),
                ('reminder_times', models.JSONField(blank=True, default=list)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='medication_schedules', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['start_date', 'reminder_time', 'name'], 'indexes': [models.Index(fields=['patient', 'is_active'], name='care_medica_patient_1c38ec_idx'), models.Index(fields=['start_date', 'end_date'], name='care_medica_start_d6c85c_idx')]},
        ),
        migrations.CreateModel(
            name='Appointment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_at', models.DateTimeField()),
                ('duration_minutes', models.PositiveIntegerField(default=30)),
                ('reason', models.CharField(blank=True, max_length=500)),
                ('notes', models.TextField(blank=True)),
                ('location', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(choices=[('UPCOMING', 'Sắp tới'), ('COMPLETED', 'Đã hoàn thành'), ('CANCELLED', 'Đã hủy'), ('MISSED', 'Đã lỡ')], default='UPCOMING', max_length=12)),
                ('doctor_response', models.TextField(blank=True)),
                ('responded_at', models.DateTimeField(blank=True, null=True)),
                ('reminder_enabled', models.BooleanField(default=True)),
                ('reminder_sent_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('doctor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='doctor_appointments', to=settings.AUTH_USER_MODEL)),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='patient_appointments', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['scheduled_at'], 'indexes': [models.Index(fields=['patient', 'scheduled_at'], name='care_appoin_patient_8e1a10_idx'), models.Index(fields=['doctor', 'scheduled_at'], name='care_appoin_doctor_5f2a2e_idx'), models.Index(fields=['status', 'scheduled_at'], name='care_appoin_status_0f1f80_idx')]},
        ),
        migrations.CreateModel(
            name='MedicationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scheduled_date', models.DateField(default=django.utils.timezone.localdate)),
                ('taken_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDING', 'Chưa uống'), ('TAKEN', 'Đã uống'), ('MISSED', 'Bỏ lỡ')], default='PENDING', max_length=10)),
                ('notes', models.CharField(blank=True, max_length=500)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='logs', to='care.medicationschedule')),
            ],
            options={'ordering': ['-scheduled_date', '-taken_at', '-created_at'], 'indexes': [models.Index(fields=['schedule', 'scheduled_date'], name='care_medica_schedule_b2e60d_idx')]},
        ),
        migrations.AddConstraint(
            model_name='medicationlog',
            constraint=models.UniqueConstraint(fields=('schedule', 'scheduled_date'), name='unique_medication_log_day'),
        ),
    ]
