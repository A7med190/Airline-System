import logging
import signal
import sys
import threading
import time
from contextlib import contextmanager
from typing import Callable, List

from django.conf import settings

logger = logging.getLogger(__name__)


class GracefulShutdownHandler:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._shutdown_callbacks: List[Callable] = []
        self._shutdown_event = threading.Event()
        self._is_shutting_down = False

    def register_callback(self, callback: Callable):
        self._shutdown_callbacks.append(callback)

    def trigger_shutdown(self, signum=None, frame=None):
        if self._is_shutting_down:
            return
        
        self._is_shutting_down = True
        logger.info(f"Shutdown initiated by signal {signum if signum else 'direct call'}")
        
        for callback in self._shutdown_callbacks:
            try:
                if callable(callback):
                    callback()
            except Exception as e:
                logger.error(f"Error in shutdown callback: {e}")

        self._shutdown_event.set()
        logger.info("Graceful shutdown completed")

    @property
    def is_shutting_down(self) -> bool:
        return self._is_shutting_down

    def wait_for_shutdown(self, timeout: float = None) -> bool:
        return self._shutdown_event.wait(timeout)


class GracefulShutdownMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        handler = GracefulShutdownHandler()
        
        if handler.is_shutting_down:
            from django.http import JsonResponse
            return JsonResponse(
                {"error": "Server is shutting down"},
                status=503,
            )

        response = self.get_response(request)
        return response


def setup_graceful_shutdown():
    handler = GracefulShutdownHandler()
    
    import sys
    if sys.platform != 'win32':
        signal.signal(signal.SIGTERM, handler.trigger_shutdown)
        signal.signal(signal.SIGINT, handler.trigger_shutdown)
        signal.signal(signal.SIGHUP, handler.trigger_shutdown)


@contextmanager
def shutdown_protected():
    handler = GracefulShutdownHandler()
    try:
        yield handler
    finally:
        if handler.is_shutting_down:
            raise SystemExit(0)


def shutdown_callback(func: Callable) -> Callable:
    handler = GracefulShutdownHandler()
    handler.register_callback(func)
    return func


@shutdown_callback
def close_celery_connections():
    from django_celery_results.models import TaskResult
    from django_celerybeat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
    
    logger.info("Closing Celery connections...")


@shutdown_callback
def flush_caches():
    from django.core.cache import cache
    logger.info("Flushing caches...")
    try:
        cache.clear()
    except Exception as e:
        logger.error(f"Error flushing cache: {e}")


@shutdown_callback
def close_database_connections():
    from django.db import connection
    logger.info("Closing database connections...")
    try:
        connection.close()
    except Exception as e:
        logger.error(f"Error closing database connection: {e}")


class IdempotencyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)


class HealthCheckSync:
    @staticmethod
    def perform_sync():
        from django.core.management import call_command
        try:
            pass
        except Exception as e:
            logger.error(f"Health check sync failed: {e}")


setup_graceful_shutdown()
