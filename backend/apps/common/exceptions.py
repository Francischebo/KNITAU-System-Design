from __future__ import annotations

from typing import Any
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class DomainError(Exception):
    """Typed domain rule violation raised by services and translated cleanly by DRF."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        field_errors: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        self.field_errors = field_errors or {}
        super().__init__(message)


def knitau_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DomainError):
        return Response(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "field_errors": exc.field_errors,
                }
            },
            status=exc.http_status,
        )

    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "error": {
                "code": getattr(exc, "default_code", "request_error"),
                "message": "Request validation or authorization failed.",
                "details": response.data,
            }
        }
    return response
