from __future__ import annotations

from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from .models import StipendDisbursement


@shared_task(queue="payments_mpesa", bind=True, max_retries=3, default_retry_delay=30)
def dispatch_mpesa_b2c_task(self, disbursement_id: str) -> str:
    """
    Isolated Celery task running strictly on worker_payments (-Q payments_mpesa).
    Submits Daraja B2C payout using disbursement.idempotency_key as OriginatorConversationID.
    """
    stipend = StipendDisbursement.objects.filter(id=disbursement_id).first()
    if not stipend or stipend.status != StipendDisbursement.Status.QUEUED:
        return "skipped"

    # Integration boundary: replace with Safaricom Daraja HTTPS client using server secrets
    stipend.status = StipendDisbursement.Status.DARAJA_ACCEPTED
    stipend.mpesa_conversation_id = f"AG_{stipend.id.hex[:20]}"
    stipend.save(update_fields=["status", "mpesa_conversation_id", "updated_at"])
    return stipend.mpesa_conversation_id


@shared_task(queue="payments_mpesa")
def reconcile_stale_disbursements() -> int:
    """Periodic beat job checking Daraja accepted payouts older than 15 minutes."""
    cutoff = timezone.now() - timedelta(minutes=15)
    stale_count = StipendDisbursement.objects.filter(
        status=StipendDisbursement.Status.DARAJA_ACCEPTED,
        updated_at__lt=cutoff,
    ).count()
    return stale_count
