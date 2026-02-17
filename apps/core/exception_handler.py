import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """Custom exception handler that:
    - Never leaks stack traces or internal details in production
    - Converts Django ValidationErrors to DRF responses
    - Logs all 5xx errors for monitoring
    """
    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            data = {"errors": exc.message_dict}
        else:
            data = {"errors": exc.messages if hasattr(exc, "messages") else [str(exc)]}
        return Response(data, status=status.HTTP_400_BAD_REQUEST)

    response = exception_handler(exc, context)

    if response is not None:
        response.data["status_code"] = response.status_code
        return response

    # Unhandled exception — log it, return safe generic message
    logger.exception(
        "Unhandled exception in %s",
        context.get("view", "unknown"),
    )
    return Response(
        {"error": "An internal server error occurred.", "status_code": 500},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
