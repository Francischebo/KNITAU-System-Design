from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import AdminSubRole, HasKnitauRole, KnitauRole
from apps.welfare.services import (
    approve_and_queue_stipend,
    process_mpesa_b2c_callback,
    verify_mpesa_webhook_signature,
)


class ApproveStipendView(APIView):
    permission_classes = [HasKnitauRole]
    required_roles = (KnitauRole.ADMIN,)
    required_admin_sub_roles = (AdminSubRole.FINANCE_OFFICER, AdminSubRole.EXECUTIVE)

    @extend_schema(summary="Approve and queue an intern stipend for isolated M-Pesa payout")
    def post(self, request, disbursement_id):
        idem_key = request.headers.get("X-Idempotency-Key", "")
        stipend = approve_and_queue_stipend(
            disbursement_id=disbursement_id,
            actor_id=request.user.id,
            actor_role=request.user.role,
            actor_sub_role=request.user.admin_sub_role,
            request_idempotency_key=idem_key,
        )
        return Response({"id": str(stipend.id), "status": stipend.status}, status=status.HTTP_202_ACCEPTED)


class MpesaB2CCallbackView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(summary="Verified Safaricom Daraja B2C webhook settlement endpoint")
    def post(self, request):
        sig = request.headers.get("X-Mpesa-Signature", "")
        if not verify_mpesa_webhook_signature(raw_body=request.body, provided_signature=sig):
            return Response({"error": "invalid_signature"}, status=status.HTTP_403_FORBIDDEN)

        result = request.data.get("Result", {})
        stipend = process_mpesa_b2c_callback(
            conversation_id=result.get("ConversationID", ""),
            result_code=int(result.get("ResultCode", -1)),
            receipt_number=result.get("TransactionID", ""),
            result_desc=result.get("ResultDesc", ""),
        )
        return Response({"status": stipend.status})
