from __future__ import annotations

from typing import Any
from django.db import transaction

from apps.common.tracing import current_trace_id
from .models import AuditLog

_SENSITIVE_KEYS = frozenset(
    {"password", "pin", "mpesa_pin", "secret", "token", "access_token", "refresh_token", "national_id"}
)


def _redact_metadata(data: dict[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in _SENSITIVE_KEYS:
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = _redact_metadata(value)
        else:
            sanitized[key] = value
    return sanitized


@transaction.atomic
def record_audit_event(
    *,
    actor_id,
    actor_role: str,
    action: str,
    target_type: str,
    target_id: str,
    actor_sub_role: str = "",
    trace_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    latest = AuditLog.objects.select_for_update().order_by("-created_at").values("record_hash").first()
    prev_hash = latest["record_hash"] if latest else ("0" * 64)

    return AuditLog.objects.create(
        actor_id=actor_id,
        actor_role=actor_role,
        actor_sub_role=actor_sub_role,
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        trace_id=trace_id or current_trace_id(),
        metadata=_redact_metadata(metadata or {}),
        prev_hash=prev_hash,
    )
