from __future__ import annotations

from django.db import models

from apps.common.models import SoftDeleteModel


class StipendDisbursement(SoftDeleteModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        QUEUED = "queued", "Queued for M-Pesa"
        DARAJA_ACCEPTED = "daraja_accepted", "Daraja Accepted"
        CONFIRMED = "confirmed", "M-Pesa Confirmed"
        FAILED = "failed", "Failed"
        REVERSED = "reversed", "Reversed"

    intern_user_id = models.UUIDField(db_index=True)
    approved_by_id = models.UUIDField(null=True, blank=True)
    phone_e164 = models.CharField(max_length=20)
    amount_kes = models.DecimalField(max_digits=12, decimal_places=2)
    period_label = models.CharField(max_length=40, db_index=True)
    idempotency_key = models.CharField(max_length=128, unique=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT, db_index=True)
    mpesa_conversation_id = models.CharField(max_length=96, blank=True, default="", db_index=True)
    mpesa_receipt = models.CharField(max_length=48, blank=True, default="")
    failure_reason = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(check=models.Q(amount_kes__gt=0), name="stipend_amount_positive"),
        ]
