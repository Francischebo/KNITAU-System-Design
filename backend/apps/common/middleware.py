from __future__ import annotations

import uuid
from .tracing import set_trace_id


class RequestTraceMiddleware:
    """Propagates X-Request-ID across HTTP views, services, and immutable AuditLog entries."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        incoming = request.headers.get("X-Request-ID", "").strip()
        trace_id = incoming[:64] if incoming else str(uuid.uuid4())
        set_trace_id(trace_id)
        request.trace_id = trace_id

        response = self.get_response(request)
        response["X-Request-ID"] = trace_id
        return response
