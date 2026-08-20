"""
Standard API error envelope (TRD §4.2, §7): every endpoint returns errors as
{"error": {"code", "message", "fields"}} so the frontend never special-cases
error shape per module.
"""

from rest_framework.views import exception_handler as drf_exception_handler


def _is_simplejwt_style_detail(detail):
    """
    djangorestframework-simplejwt's exceptions (DetailDictMixin) always
    serialize as {"detail": "...", "code": "..."} — a single error with an
    explicit code, not per-field validation errors. Unlike a plain DRF
    APIException, it stores the caller's `code=...` as a plain dict value
    rather than on the ErrorDetail itself (a peculiarity of its __init__,
    confirmed against the installed version), so this shape needs its own
    branch below or the code gets lost and "code" leaks into `fields`.
    """
    return isinstance(detail, dict) and set(detail.keys()) == {"detail", "code"}


def standard_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    fields = {}

    if _is_simplejwt_style_detail(detail):
        code = str(detail["code"])
        message = str(detail["detail"])
    elif isinstance(detail, dict):
        non_field = detail.pop("detail", None) or detail.pop("non_field_errors", None)
        fields = dict(detail.items())
        if non_field:
            message = non_field if isinstance(non_field, str) else str(non_field)
            code = str(getattr(non_field, "code", None) or _default_code(exc))
        elif fields:
            message = "Validation failed."
            code = _default_code(exc)
        else:
            message = "An error occurred."
            code = _default_code(exc)
    elif isinstance(detail, list):
        message = "; ".join(str(item) for item in detail)
        code = _default_code(exc)
    else:
        message = str(detail)
        code = str(getattr(detail, "code", None) or _default_code(exc))

    response.data = {
        "error": {
            "code": code,
            "message": message,
            "fields": fields,
        }
    }
    return response


def _default_code(exc):
    return str(getattr(exc, "default_code", exc.__class__.__name__))
