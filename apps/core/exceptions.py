from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if response.status_code >= 500:
            response.data = {
                "success": False,
                "error": "Internal server error",
            }
        elif "detail" in response.data:
            response.data = {
                "success": False,
                "error": response.data["detail"],
            }
        else:
            errors = {}
            for field, messages in response.data.items():
                if isinstance(messages, list):
                    errors[field] = " ".join(str(m) for m in messages)
                else:
                    errors[field] = str(messages)
            response.data = {
                "success": False,
                "errors": errors,
            }

    return response
