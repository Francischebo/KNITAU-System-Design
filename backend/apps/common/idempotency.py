from __future__ import annotations

from contextlib import contextmanager
from django.core.cache import cache
from rest_framework import status

from .exceptions import DomainError


@contextmanager
def acquire_idempotency_lock(scope: str, idempotency_key: str, ttl_seconds: int = 300):
    """
    Distributed Redis/cache lock preventing duplicate M-Pesa payouts or offline sync replays.
    Raises DomainError(409) if the exact operation key is already in-flight or completed.
    """
    if not idempotency_key or len(idempotency_key) > 128:
        raise DomainError(
            code="invalid_idempotency_key",
            message="A valid X-Idempotency-Key header is required.",
            http_status=status.HTTP_400_BAD_REQUEST,
        )

    cache_key = f"idemp:{scope}:{idempotency_key}"
    acquired = cache.add(cache_key, "locked", timeout=ttl_seconds)
    if not acquired:
        raise DomainError(
            code="duplicate_request",
            message="This operation has already been processed or is currently in progress.",
            http_status=status.HTTP_409_CONFLICT,
        )
    try:
        yield cache_key
    except Exception:
        # Release lock only on unexpected failure so safe retries remain possible
        cache.delete(cache_key)
        raise
