import json
import time
import uuid
from typing import Any, Dict, Optional

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View


class IdempotencyService:
    def __init__(self):
        config = getattr(settings, "IDEMPOTENCY", {})
        self.key_prefix = config.get("KEY_PREFIX", "idempotency")
        self.timeout = config.get("TIMEOUT", 86400)
        self.header_name = config.get("HEADER_NAME", "X-Idempotency-Key")

    def get_key(self, key: str) -> str:
        return f"{self.key_prefix}:{key}"

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        cache_key = self.get_key(key)
        data = cache.get(cache_key)
        if data:
            return json.loads(data)
        return None

    def set(self, key: str, value: Dict[str, Any], timeout: int = None):
        cache_key = self.get_key(key)
        cache.set(cache_key, json.dumps(value), timeout or self.timeout)

    def set_processing(self, key: str):
        self.set(key, {"status": "processing", "started_at": time.time()})

    def set_completed(self, key: str, response_data: Dict[str, Any], status_code: int = 200):
        self.set(key, {
            "status": "completed",
            "completed_at": time.time(),
            "response_data": response_data,
            "status_code": status_code,
        })

    def set_failed(self, key: str, error: str):
        self.set(key, {
            "status": "failed",
            "failed_at": time.time(),
            "error": error,
        })

    def is_processing(self, key: str) -> bool:
        data = self.get(key)
        return data and data.get("status") == "processing"

    def is_completed(self, key: str) -> bool:
        data = self.get(key)
        return data and data.get("status") == "completed"

    def delete(self, key: str):
        cache.delete(self.get_key(key))


class IdempotentResponse(JsonResponse):
    def __init__(self, data: Any, status: int = 200, idempotent: bool = False, **kwargs):
        kwargs["status"] = status
        super().__init__(data, **kwargs)
        if idempotent:
            self["X-Idempotent-Replayed"] = "true"


class IdempotencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.service = IdempotencyService()
        self.header_name = self.service.header_name

    def __call__(self, request):
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return self.get_response(request)

        idempotency_key = request.headers.get(self.header_name)
        if not idempotency_key:
            return self.get_response(request)

        existing = self.service.get(idempotency_key)
        
        if existing:
            if existing.get("status") == "processing":
                return JsonResponse(
                    {"error": "Request is still being processed", "idempotency_key": idempotency_key},
                    status=409,
                )
            
            if existing.get("status") == "completed":
                response = IdempotentResponse(
                    existing.get("response_data", {}),
                    status=existing.get("status_code", 200),
                    idempotent=True,
                )
                return response
            
            if existing.get("status") == "failed":
                return JsonResponse(
                    {"error": existing.get("error", "Previous request failed")},
                    status=500,
                )

        self.service.set_processing(idempotency_key)
        request.idempotency_key = idempotency_key
        
        response = self.get_response(request)

        if 200 <= response.status_code < 300:
            try:
                response_data = json.loads(response.content.decode())
            except:
                response_data = {"success": True}
            self.service.set_completed(idempotency_key, response_data, response.status_code)
        else:
            self.service.set_failed(idempotency_key, response.content.decode()[:500])

        return response


def idempotent(key_func: callable = None):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            service = IdempotencyService()
            key = key_func(request) if key_func else request.headers.get(service.header_name)
            
            if key:
                existing = service.get(key)
                if existing and existing.get("status") == "completed":
                    return IdempotentResponse(
                        existing.get("response_data", {}),
                        status=existing.get("status_code", 200),
                        idempotent=True,
                    )
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


@method_decorator
class IdempotentViewMixin(View):
    idempotency_timeout = 86400

    def get_idempotency_key(self, request) -> Optional[str]:
        service = IdempotencyService()
        return request.headers.get(service.header_name)

    def dispatch(self, request, *args, **kwargs):
        key = self.get_idempotency_key(request)
        
        if key and request.method in ("POST", "PUT", "PATCH"):
            service = IdempotencyService()
            existing = service.get(key)
            
            if existing and existing.get("status") == "completed":
                return IdempotentResponse(
                    existing.get("response_data", {}),
                    status=existing.get("status_code", 200),
                    idempotent=True,
                )
            
            if existing and existing.get("status") == "processing":
                return JsonResponse(
                    {"error": "Request is still being processed"},
                    status=409,
                )
        
        return super().dispatch(request, *args, **kwargs)


@shared_task
def cleanup_expired_idempotency_keys():
    pass
