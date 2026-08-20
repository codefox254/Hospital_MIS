"""
Standard API error envelope (TRD §4.2, §7): every endpoint returns errors as
{"error": {"code", "message", "fields"}} so the frontend never special-cases
error shape per module.
"""

from rest_framework.views import exception_handler as drf_exception_handler


def standard_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    fields = {}
    message = "An error occurred."
    code = getattr(exc, "default_code", exc.__class__.__name__)

    if isinstance(detail, dict):
        non_field = detail.pop("detail", None) or detail.pop("non_field_errors", None)
        fields = {k: v for k, v in detail.items()}
        if non_field:
            message = non_field if isinstance(non_field, str) else str(non_field)
        elif fields:
            message = "Validation failed."
        else:
            message = str(detail)
    elif isinstance(detail, list):
        message = "; ".join(str(item) for item in detail)
    else:
        message = str(detail)

    response.data = {
        "error": {
            "code": str(code),
            "message": message,
            "fields": fields,
        }
    }
    return response
