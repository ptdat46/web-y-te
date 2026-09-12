"""Helpers for filtering and exporting care data."""
import csv
import io
from datetime import datetime, time

from django.utils import timezone
from rest_framework.exceptions import ValidationError


CSV_FORMULA_PREFIXES = ('=', '+', '-', '@')


def csv_safe(value):
    """Prevent spreadsheet applications from evaluating user data as formulas."""
    text = '' if value is None else str(value)
    if text.startswith(CSV_FORMULA_PREFIXES):
        return "'" + text
    return text


class _CsvEcho:
    def write(self, value):
        return value


def csv_row(values):
    """Serialize one row without retaining the complete export in memory."""
    writer = csv.writer(_CsvEcho())
    return writer.writerow([csv_safe(value) for value in values])


def parse_date_param(value, *, field_name, end_of_day=False):
    """Parse an ISO date or datetime string into a timezone-aware datetime.

    Accepts `YYYY-MM-DD` (interpreted as midnight or end-of-day) and full ISO
    datetimes. Returns ``None`` for empty/missing input. Raises a
    ValidationError on malformed values.
    """
    if value is None or value == '':
        return None
    try:
        # Try full datetime first.
        dt = datetime.fromisoformat(value)
    except ValueError:
        try:
            dt = datetime.strptime(value, '%Y-%m-%d')
        except ValueError as exc:
            raise ValidationError({field_name: 'Invalid date format. Use YYYY-MM-DD or ISO 8601.'}) from exc
    if dt.tzinfo is None:
        if end_of_day:
            dt = datetime.combine(dt.date(), time.max)
        dt = timezone.make_aware(dt)
    return dt


def apply_date_range(qs, params, *, created_field='created_at', from_field='from', to_field='to'):
    """Filter a queryset by an optional date range on the given field name."""
    raw_from = params.get(from_field)
    raw_to = params.get(to_field)
    from_dt = parse_date_param(raw_from, field_name=from_field)
    to_dt = parse_date_param(raw_to, field_name=to_field, end_of_day=True)
    if from_dt is not None:
        qs = qs.filter(**{f'{created_field}__gte': from_dt})
    if to_dt is not None:
        qs = qs.filter(**{f'{created_field}__lte': to_dt})
    return qs
