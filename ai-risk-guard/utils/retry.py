"""
Exponential backoff retry decorator with jitter, max attempts, and optional
retryable-exception filter.  No external dependencies.

Retrying is an explicit statement about *transient* failure. The default filter
retries only ``RateLimitError`` (a self-describing 429). Use ``RETRY_ALL`` or a
concrete exception tuple when a call genuinely needs to retry other errors —
never assume every exception is worth retrying, or programming errors get
retried too.
"""

import random
import time
from collections.abc import Callable
from functools import wraps


class _RetryAllMeta(type):
    def __instancecheck__(cls, instance) -> bool:
        return True


class RETRY_ALL(metaclass=_RetryAllMeta):
    """Sentinel that matches every exception (explicit opt-in to retry-all)."""


class RateLimitError(Exception):
    """
    Raised when an HTTP 429 (Rate Limited) response is received.

    Carries the ``retry_after`` value (in seconds) extracted from the
    ``Retry-After`` response header so the retry decorator can respect the
    server's requested delay.
    """
    def __init__(self, retry_after: float = 5.0, message: str = "Rate limited"):
        self.retry_after = retry_after
        super().__init__(message)


def _is_retryable(exc: Exception, spec: tuple[type[Exception], ...] | None) -> bool:
    """Decide whether *exc* qualifies for a retry under the given filter."""
    if spec is RETRY_ALL:
        return True
    if spec is None:
        return isinstance(exc, RateLimitError)
    return isinstance(exc, spec)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff: float = 2.0,
    jitter: bool = True,
retryable_exceptions: tuple[type[Exception], ...] | None = None,
        on_retry: Callable[[Exception, int, float], None] | None = None,
    ):
    """
    Decorator that retries a callable with exponential backoff.

    If the caught exception has a ``retry_after`` attribute (e.g.
    ``RateLimitError``), that value (capped to ``max_delay``) is used
    as the delay instead of the calculated exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (default 3).
        base_delay: Initial delay in seconds (default 1.0).
        max_delay: Maximum delay in seconds (default 30.0).
        backoff: Multiplier applied to delay after each attempt (default 2.0).
        jitter: Add random jitter ±25% to each delay (default True).
        retryable_exceptions: Tuple of exception classes that trigger a retry,
            or ``RETRY_ALL`` to retry every exception. ``None`` (default)
            retries only ``RateLimitError`` — callers retrying programming
            errors can mask bugs and hammer external APIs.
        on_retry: Optional callback called before each retry.  Receives the
            exception, attempt number (1-indexed), and next delay in seconds.

    Returns:
        The decorated function's return value.

    Raises:
        The last exception raised by the wrapped function after all attempts
        are exhausted.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if not _is_retryable(exc, retryable_exceptions):
                        raise
                    if attempt == max_attempts:
                        raise

                    delay = getattr(exc, "retry_after", None)
                    if delay is not None:
                        delay = min(delay, max_delay)
                    else:
                        delay = min(base_delay * (backoff ** (attempt - 1)), max_delay)
                        if jitter:
                            delay *= random.uniform(0.75, 1.25)

                    if on_retry:
                        on_retry(exc, attempt, delay)
                    time.sleep(delay)

            raise last_exc  # should not be reached
        return wrapper
    return decorator
