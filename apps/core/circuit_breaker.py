import signal
import sys
from contextlib import contextmanager
from typing import Callable, Optional
from cachetools import TTLCache

from django.conf import settings


class CircuitBreaker:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
        expected_exception: type = Exception,
        name: str = "default",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._state = self.CLOSED
        self._lock = False

    @property
    def state(self) -> str:
        if self._state == self.OPEN:
            import time
            if self._last_failure_time and time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = self.HALF_OPEN
        return self._state

    def record_success(self):
        self._failure_count = 0
        self._state = self.CLOSED
        self._last_failure_time = None

    def record_failure(self):
        self._failure_count += 1
        import time
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = self.OPEN

    def call(self, func: Callable, *args, **kwargs):
        if self.state == self.OPEN:
            raise CircuitBreakerOpen(f"Circuit breaker '{self.name}' is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.record_success()
            return result
        except self.expected_exception as e:
            self.record_failure()
            raise

    @contextmanager
    def __call__(self):
        yield self
        if self.state == self.HALF_OPEN:
            self.record_success()


class CircuitBreakerOpen(Exception):
    pass


class CircuitBreakerRegistry:
    _breakers: dict = {}
    _lock = False

    @classmethod
    def get(cls, name: str, **kwargs) -> CircuitBreaker:
        if name not in cls._breakers:
            config = getattr(settings, "CIRCUIT_BREAKER", {})
            cls._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=kwargs.get("failure_threshold", config.get("FAILURE_THRESHOLD", 5)),
                recovery_timeout=kwargs.get("recovery_timeout", config.get("RECOVERY_TIMEOUT", 30)),
                expected_exception=kwargs.get("expected_exception", config.get("EXPECTED_EXCEPTION", Exception)),
            )
        return cls._breakers[name]

    @classmethod
    def reset(cls, name: str = None):
        if name:
            cls._breakers.pop(name, None)
        else:
            cls._breakers.clear()


def circuit_breaker(name: str = None, **kwargs):
    def decorator(func: Callable) -> Callable:
        breaker_name = name or func.__module__ + "." + func.__name__
        
        def wrapper(*args, **kwargs):
            breaker = CircuitBreakerRegistry.get(breaker_name, **kwargs)
            return breaker.call(func, *args, **kwargs)
        
        wrapper._circuit_breaker_name = breaker_name
        wrapper._original_func = func
        return wrapper
    return decorator
