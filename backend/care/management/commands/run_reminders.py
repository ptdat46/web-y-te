"""
Background reminder worker — runs in a loop and processes all scheduled reminders.

Usage:
    python manage.py run_reminders                # loop every 60s
    python manage.py run_reminders --interval 30  # loop every 30s
    python manage.py run_reminders --once         # run once and exit
"""
import time
import logging
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from care.services import process_due_reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run scheduled reminders (medication, appointment, missed) in a loop.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Seconds between runs (default: 60).',
        )
        parser.add_argument(
            '--once',
            action='store_true',
            help='Run once and exit instead of looping.',
        )

    def handle(self, *args, **options):
        interval = max(options['interval'], 10)
        once = options['once']

        self.stdout.write(self.style.SUCCESS(
            f'Reminder worker started (interval={interval}s, once={once})'
        ))

        while True:
            close_old_connections()
            try:
                result = process_due_reminders()
                total = sum(result.values())
                if total > 0:
                    self.stdout.write(
                        f'  Processed: medication={result["medication_reminders"]}, '
                        f'appointment={result["appointment_reminders"]}, '
                        f'missed={result["missed_appointments"]}'
                    )
            except Exception:
                logger.exception('Error in reminder worker')
                self.stderr.write(self.style.ERROR('  Error processing reminders — see log'))

            if once:
                break

            time.sleep(interval)
