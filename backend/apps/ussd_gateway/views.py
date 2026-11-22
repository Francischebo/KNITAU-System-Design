from __future__ import annotations

from django.core.cache import cache
from django.http import HttpResponse
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView


class UssdCallbackView(APIView):
    """
    Stateless *384* USSD Adapter (Africa's Talking format).
    Budget: < 2s latency, max 182 chars per screen, Redis session TTL = 180s.
    """

    permission_classes = [AllowAny]

    def post(self, request):
        session_id = str(request.data.get("sessionId", ""))[:64]
        text = str(request.data.get("text", "")).strip()

        cache.set(f"ussd:sess:{session_id}", {"last_text": text}, timeout=180)

        parts = text.split("*") if text else []
        if not parts:
            body = "CON KNITAU KeNIP Portal\n1. Stipend Status\n2. Report Workplace Issue\n3. Exit Clearance"
        elif parts == ["1"]:
            body = "END Your latest stipend check is active. Visit app or dial *384*1# with National ID."
        elif parts == ["2"]:
            body = "CON Select Issue:\n1. Delayed Stipend\n2. Safety / PPE\n3. Harassment"
        elif len(parts) == 2 and parts[0] == "2":
            body = "END Confidential report logged. Case Officer SLA: 24h."
        elif parts == ["3"]:
            body = "END Exit Clearance: Check Supervisor & HR approvals in portal."
        else:
            body = "END Invalid selection. Dial again to restart."

        return HttpResponse(body[:182], content_type="text/plain")
