"""Mark overdue appointments as MISSED.

Usage:
    python manage.py mark_missed_appointments
    python manage.py mark_missed_appointments --grace-minutes 30

Appointment status is never mutated from a read path (GET). This command is the
single reconciliation point and is intended to be run by a scheduler (cron,
systemd timer, Celery beat, ...). It is idempotent: running it twice changes
nothing the second time.

An appointment is considered missed when it is still UPCOMING after its
scheduled start plus its duration (and optional grace period) has elapsed.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from care.models import Appointment, AppointmentStatus


class Command(BaseCommand):
    help = 'Mark UPCOMING appointments whose end time has passed as MISSED.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--grace-minutes',
            type=int,
            default=0,
            help='Extra minutes to wait past the appointment end before marking it missed.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report the appointments that would change without writing anything.',
        )

    def handle(self, *args, **options):
        grace_minutes = max(options['grace_minutes'] or 0, 0)
        now = timezone.now()
        cutoff = now - timezone.timedelta(minutes=grace_minutes)

        # `duration_minutes` is a per-row column, so end time cannot be
        # expressed portably in SQL. Filter coarsely in the database, then
        # confirm each candidate in Python.
        candidates = Appointment.objects.filter(
            status=AppointmentStatus.UPCOMING,
            scheduled_at__lt=cutoff,
        ).only('pk', 'scheduled_at', 'duration_minutes')

        ids = [
            appointment.pk
            for appointment in candidates
            if appointment.scheduled_at + timezone.timedelta(minutes=appointment.duration_minutes) <= cutoff
        ]

        if not ids:
            self.stdout.write('No overdue appointments found.')
            return

        if options['dry_run']:
            self.stdout.write(f'[dry-run] Would mark {len(ids)} appointment(s) as MISSED: {ids}')
            return

        updated = Appointment.objects.filter(
            pk__in=ids, status=AppointmentStatus.UPCOMING
        ).update(status=AppointmentStatus.MISSED, updated_at=now)

        self.stdout.write(self.style.SUCCESS(f'Marked {updated} appointment(s) as MISSED.'))
