from django.contrib.contenttypes.models import ContentType

from .models import AuditAction, AuditLog


def log_audit(request, *, actor, action, obj, summary, details=''):
    """
    Create an AuditLog entry for an action performed on a model instance.

    Args:
        request: The DRF request (used to capture the client IP).
        actor: The user performing the action (may be None for system actions).
        action: One of AuditAction values.
        obj: The model instance that was acted upon.
        summary: Short human-readable description.
        details: Optional longer description / diff.
    """
    content_type = ContentType.objects.get_for_model(type(obj))
    ip = None
    if request is not None:
        ip = _client_ip(request)
    AuditLog.objects.create(
        actor=actor,
        action=action,
        content_type=content_type,
        object_id=obj.pk,
        summary=summary,
        details=details,
        ip_address=ip,
    )


def _client_ip(request):
    """Best-effort extraction of the client IP from a request object."""
    try:
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    except Exception:
        return None