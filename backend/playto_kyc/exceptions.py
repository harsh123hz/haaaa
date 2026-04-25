from rest_framework.views import exception_handler


def standard_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None

    detail = response.data
    if isinstance(detail, dict) and "errors" in detail:
        return response
    if isinstance(detail, dict):
        response.data = {"errors": detail}
    elif isinstance(detail, list):
        response.data = {"errors": {"non_field_errors": detail}}
    else:
        response.data = {"errors": {"detail": detail}}
    return response

