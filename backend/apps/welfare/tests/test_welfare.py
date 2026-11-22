from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from decimal import Decimal
import pytest

from apps.common.exceptions import DomainError
from apps.welfare.models import StipendDisbursement
from apps.welfare.services import (
    approve_and_queue_stipend,
    process_mpesa_b2c_callback,
    verify_mpesa_webhook_signature,
)


@pytest.mark.django_db
def test_stipend_approval_is_idempotent_and_settles_on_callback(monkeypatch):
    stipend = StipendDisbursement.objects.create(
        intern_user_id=uuid.uuid4(),
        phone_e164="+254712345678",
        amount_kes=Decimal("15000.00"),
        period_label="2026-11",
        idempotency_key=f"stipend-{uuid.uuid4()}",
    )

    queued = approve_and_queue_stipend(
        disbursement_id=stipend.id,
        actor_id=uuid.uuid4(),
        actor_role="admin",
        actor_sub_role="finance_officer",
        request_idempotency_key="req-approve-001",
    )
    assert queued.status == StipendDisbursement.Status.QUEUED

    with pytest.raises(DomainError) as dup_exc:
        approve_and_queue_stipend(
            disbursement_id=stipend.id,
            actor_id=uuid.uuid4(),
            actor_role="admin",
            actor_sub_role="finance_officer",
            request_idempotency_key="req-approve-001",
        )
    assert dup_exc.value.code == "duplicate_request"

    queued.status = StipendDisbursement.Status.DARAJA_ACCEPTED
    queued.mpesa_conversation_id = "AG_CONV_123"
    queued.save()

    settled = process_mpesa_b2c_callback(
        conversation_id="AG_CONV_123",
        result_code=0,
        receipt_number="UBK901XYZ",
    )
    assert settled.status == StipendDisbursement.Status.CONFIRMED
    assert settled.mpesa_receipt == "UBK901XYZ"


def test_mpesa_webhook_hmac_verification(settings):
    settings.MPESA_WEBHOOK_HMAC_SECRET = "test-webhook-secret"
    body = json.dumps({"Result": {"ResultCode": 0}}).encode("utf-8")
    valid_sig = hmac.new(b"test-webhook-secret", body, hashlib.sha256).hexdigest()

    assert verify_mpesa_webhook_signature(raw_body=body, provided_signature=valid_sig) is True
    assert verify_mpesa_webhook_signature(raw_body=body, provided_signature="tampered") is False
