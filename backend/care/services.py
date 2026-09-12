"""
Scheduled reminder services for medication and appointments.
"""
from datetime import time as dt_time

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from messaging.realtime import create_notification


def _local_now():
    return timezone.localtime(timezone.now())


def _candidate_times(schedule):
    """
    All reminder times for a schedule as (hour, minute) tuples.

    Reads `reminder_times` (list of 'HH:MM'/'HH:MM:SS' strings) and falls back
    to the single `reminder_time` column for legacy rows. Invalid entries are
    skipped.
    """
    times = set()
    raw_list = schedule.reminder_times if isinstance(schedule.reminder_times, list) else []
    for entry in raw_list:
        if not isinstance(entry, str):
            continue
        parts = entry.strip().split(':')
        if len(parts) < 2:
            continue
        try:
            hour, minute = int(parts[0]), int(parts[1])
        except ValueError:
            continue
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            times.add((hour, minute))
    if not times and schedule.reminder_time is not None:
        times.add((schedule.reminder_time.hour, schedule.reminder_time.minute))
    return times


def process_medication_reminders(now=None):
    """
    Create MEDICATION_REMINDER notifications for schedules whose reminder
    times (from `reminder_times`, falling back to `reminder_time`) match the
    current local hour:minute.

    Idempotent per (patient, schedule, day, hour:minute): the link encodes the
    schedule id and reminder time, and a duplicate check re-reads the link
    before creating.
    """
    from care.models import MedicationSchedule, Notification, NotificationType

    now = now or _local_now()
    current = now.time().replace(second=0, microsecond=0)
    today = now.date()

    # Coarse DB filter: active schedules due today that have any reminder
    # source (single time in the current hour, or a reminder_times list);
    # per-time matching happens in Python below.
    schedules = MedicationSchedule.objects.select_related('patient').filter(
        is_active=True,
        reminder_enabled=True,
        start_date__lte=today,
    ).exclude(end_date__lt=today).filter(
        Q(reminder_time__isnull=False, reminder_time__hour=current.hour) | ~Q(reminder_times=[]),
    )

    created = 0
    for schedule in schedules:
        if not schedule.is_scheduled_on(today):
            continue

        for hour, minute in _candidate_times(schedule):
            if (hour, minute) != (current.hour, current.minute):
                continue

            # Per-(schedule, day, time) identity so different schedules and
            # different reminder times never suppress each other.
            link = f'/app/medications?schedule={schedule.pk}&time={hour:02d}:{minute:02d}'
            already = Notification.objects.filter(
                recipient=schedule.patient,
                notification_type=NotificationType.MEDICATION_REMINDER,
                link=link,
                created_at__year=today.year,
                created_at__month=today.month,
                created_at__day=today.day,
            ).exists()
            if already:
                continue

            time_label = f'{hour:02d}:{minute:02d}'
            create_notification(
                recipient=schedule.patient,
                notification_type=NotificationType.MEDICATION_REMINDER,
                title='Nhắc uống thuốc',
                message=f'Đến giờ uống thuốc: {schedule.name} ({time_label})',
                link=link,
            )
            created += 1

    return created


def process_appointment_reminders(now=None):
    """
    Send appointment reminders for UPCOMING appointments within 24 hours.

    Each appointment is claimed atomically with select_for_update inside a
    transaction; only the worker that flips `reminder_sent_at` from NULL
    sends the notification, so concurrent workers never double-send.
    """
    from care.models import Appointment, AppointmentStatus, NotificationType

    now = now or _local_now()
    in_24h = now + timezone.timedelta(hours=24)

    candidates = Appointment.objects.filter(
        status=AppointmentStatus.UPCOMING,
        reminder_enabled=True,
        reminder_sent_at__isnull=True,
        scheduled_at__lte=in_24h,
        scheduled_at__gt=now,
    ).values_list('pk', flat=True)

    created = 0
    for pk in candidates:
        # Claim inside a short transaction: re-check the NULL guard under a
        # row lock, flip it, and only then send.
        with transaction.atomic():
            claimed = (
                Appointment.objects
                .select_for_update()
                .filter(pk=pk, reminder_sent_at__isnull=True)
                .update(reminder_sent_at=now)
            )
            if not claimed:
                continue  # another worker already claimed it
            appt = (
                Appointment.objects
                .select_related('patient', 'doctor')
                .get(pk=pk)
            )
            doctor_name = appt.doctor.get_full_name() or appt.doctor.username
            patient_name = appt.patient.get_full_name() or appt.patient.username
            time_str = timezone.localtime(appt.scheduled_at).strftime('%H:%M %d/%m/%Y')

            create_notification(
                recipient=appt.patient,
                notification_type=NotificationType.APPOINTMENT,
                title='Nhắc lịch hẹn',
                message=f'Bạn có lịch hẹn với BS. {doctor_name} lúc {time_str}.',
                link='/app/appointments',
            )
            create_notification(
                recipient=appt.doctor,
                notification_type=NotificationType.APPOINTMENT,
                title='Nhắc lịch hẹn',
                message=f'Bạn có lịch hẹn với BN. {patient_name} lúc {time_str}.',
                link='/app/appointments',
            )
            created += 2

    return created


def process_missed_appointments(now=None):
    """
    Mark UPCOMING appointments whose end time has passed as MISSED.
    Returns count of newly marked missed appointments.
    """
    from care.models import Appointment, AppointmentStatus

    now = now or _local_now()

    missed_count = 0
    for appt in Appointment.objects.filter(status=AppointmentStatus.UPCOMING):
        end_time = appt.scheduled_at + timezone.timedelta(minutes=appt.duration_minutes)
        if now > end_time:
            appt.status = AppointmentStatus.MISSED
            appt.save(update_fields=['status', 'updated_at'])
            missed_count += 1

    return missed_count


def process_due_reminders(now=None):
    """
    Main entry point: run all scheduled reminder tasks.
    Returns dict with counts of created/processed items.
    """
    now = now or _local_now()

    medication_count = process_medication_reminders(now)
    appointment_count = process_appointment_reminders(now)
    missed_count = process_missed_appointments(now)

    return {
        'medication_reminders': medication_count,
        'appointment_reminders': appointment_count,
        'missed_appointments': missed_count,
    }
