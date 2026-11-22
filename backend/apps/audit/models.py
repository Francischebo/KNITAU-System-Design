from __future__ import annotations

import hashlib
import json
from django.db import models

from apps.common.models import UUIDTimeStampedModel


class AuditLog(UUIDTimeStampedModel):
    """
    Append-only compliance ledger.
    NOTE FOR POSTGRESQL MIGRATION: Also apply `REVOKE UPDATE, DELETE ON audit_auditlog FROM knitau_app;`
    via an explicit migration SQL step so DB-level immutability is guaranteed.
    """

    actor_id = models.UUIDField(null=True, blank=True, db_index=True)
    actor_role = models.CharField(max_length=32, db_index=True)
    actor_sub_role = models.CharField(max_length=32, blank=True, default="")
    action = models.CharField(max_length=96, db_index=True)
    target_type = models.CharField(max_length=64, db_index=True)
    target_id = models.CharField(max_length=128, db_index=True)
    trace_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    metadata = models.JSONField(default=dict)
    prev_hash = models.CharField(max_length=64, default="0" * 64)
    record_hash = models.CharField(max_length=64, editable=False, unique=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["target_type", "target_id", "-created_at"]),
        ]

    def compute_hash(self) -> str:
        canonical = json.dumps(
            {
                "id": str(self.id),
                "actor_id": str(self.actor_id) if self.actor_id else None,
                "actor_role": self.actor_role,
                "action": self.action,
                "target_type": self.target_type,
                "target_id": self.target_id,
                "metadata": self.metadata,
                "prev_hash": self.prev_hash,
                "created_at": self.created_at.isoformat(),
            },
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs) -> None:
        if not self._state.adding:
            raise PermissionError("AuditLog entries are append-only and cannot be modified.")
        if not self.record_hash:
            self.record_hash = self.compute_hash()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("AuditLog entries cannot be deleted.")
