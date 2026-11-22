from __future__ import annotations

import hashlib
import hmac
from django.conf import settings
from django.db import transaction
from rest_framework import status

from apps.audit.services import record_audit_event
from apps.common.events import DomainEvent, publish_event
from apps.common.exceptions import DomainError
from apps.common.idempotency import acquire_idempotency_lock

from .models import StipendDisbursement
from .tasks import dispatch_mpesa_b2c_task


@transaction.atomic
def approve_and_queue_stipend(
    *,
    disbursement_id,
    actor_id,
    actor_role: str,
    actor_sub_role: str,
    request_idempotency_key: str,
) -> StipendDisbursement:
    with acquire_idempotency_lock("welfare.stipend_approve", request_idempotency_key):
        stipend = (
            StipendDisbursement.objects.select_for_update()
            .active()
            .filter(id=disbursement_id)
            .first()
        )
        if not stipend:
            raise DomainError("stipend_not_found", "Stipend record not found.", status.HTTP_404_NOT_FOUND)

        if stipend.status not in {StipendDisbursement.Status.DRAFT, StipendDisbursement.Status.FAILED}:
            raise DomainError(
                "invalid_stipend_transition",
                f"Cannot queue stipend from status '{stipend.status}'.",
                status.HTTP_409_CONFLICT,
            )

        stipend.status = StipendDisbursement.Status.QUEUED
        stipend.approved_by_id = actor_id
        stipend.save(update_fields=["status", "approved_by_id", "updated_at"])

        record_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            actor_sub_role=actor_sub_role,
            action="welfare.stipend.queued",
            target_type="StipendDisbursement",
            target_id=str(stipend.id),
            metadata={"amount_kes": str(stipend.amount_kes), "period": stipend.period_label},
        )

        transaction.on_commit(lambda: dispatch_mpesa_b2c_task.delay(str(stipend.id)))
        return stipend


def verify_mpesa_webhook_signature(*, raw_body: bytes, provided_signature: str) -> bool:
    secret = getattr(settings, "MPESA_WEBHOOK_HMAC_SECRET", "") or ""
    if not secret or not provided_signature:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_signature.strip())


@transaction.atomic
def process_mpesa_b2c_callback(
    *,
    conversation_id: str,
    result_code: int,
    receipt_number: str = "",
    result_desc: str = "",
) -> StipendDisbursement:
    stipend = (
        StipendDisbursement.objects.select_for_update()
        .filter(mpesa_conversation_id=conversation_id)
        .first()
    )
    if not stipend:
        raise DomainError("unknown_conversation", "Unknown M-Pesa conversation.", status.HTTP_404_NOT_FOUND)

    if stipend.status == StipendDisbursement.Status.CONFIRMED:
        return stipend

    if result_code == 0:
        stipend.status = StipendDisbursement.Status.CONFIRMED
        stipend.mpesa_receipt = receipt_number
        stipend.failure_reason = ""
        action = "welfare.stipend.confirmed"
    else:
        stipend.status = StipendDisbursement.Status.FAILED
        stipend.failure_reason = result_desc[:255]
        action = "welfare.stipend.failed"

    stipend.save(update_fields=["status", "mpesa_receipt", "failure_reason", "updated_at"])

    record_audit_event(
        actor_id=None,
        actor_role="system_mpesa",
        action=action,
        target_type="StipendDisbursement",
        target_id=str(stipend.id),
        metadata={"receipt": receipt_number, "result_code": result_code},
    )

    publish_event(
        DomainEvent(
            event_name=action,
            payload={"disbursement_id": str(stipend.id), "intern_user_id": str(stipend.intern_user_id)},
        )
    )
    return stipend
