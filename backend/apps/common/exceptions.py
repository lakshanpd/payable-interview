"""Shared DRF exception handling.

Business-rule violations are raised as ``ServiceError`` from the service
layer (kept independent of DRF/HTTP concerns) and translated to a
consistent JSON error response here.
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler


class ServiceError(Exception):
    """Raised by service-layer code when a business rule is violated.

    Carries an HTTP status code so the view layer does not need to
    re-derive it from the error type.
    """

    def __init__(self, message: str, code: str = 'error', status_code: int = status.HTTP_400_BAD_REQUEST):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


def custom_exception_handler(exc, context):
    if isinstance(exc, ServiceError):
        return Response({'detail': exc.message, 'code': exc.code}, status=exc.status_code)

    return exception_handler(exc, context)
