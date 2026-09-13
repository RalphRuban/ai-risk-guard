"""
Tests for exponential backoff retry decorator.
"""

import time
from unittest.mock import MagicMock, patch

from utils.retry import RETRY_ALL, RateLimitError, retry


class TestRateLimitError:
    def test_carries_retry_after(self):
        exc = RateLimitError(retry_after=10.0)
        assert exc.retry_after == 10.0
        assert str(exc) == "Rate limited"

    def test_default_retry_after(self):
        exc = RateLimitError()
        assert exc.retry_after == 5.0

    def test_custom_message(self):
        exc = RateLimitError(message="Custom message")
        assert str(exc) == "Custom message"


class TestRetryDecorator:
    def test_success_first_try(self):
        func = MagicMock(return_value=42)
        decorated = retry(max_attempts=3)(func)
        with patch.object(time, "sleep"):
            result = decorated()
        assert result == 42
        func.assert_called_once()

    def test_success_on_retry(self):
        func = MagicMock(side_effect=[ValueError("fail"), 42])
        decorated = retry(max_attempts=3, retryable_exceptions=(ValueError,))(func)
        with patch.object(time, "sleep") as mock_sleep:
            result = decorated()
        assert result == 42
        assert func.call_count == 2
        mock_sleep.assert_called_once()

    def test_fails_after_max_attempts(self):
        func = MagicMock(side_effect=ValueError("always fail"))
        decorated = retry(max_attempts=3, retryable_exceptions=(ValueError,))(func)
        with patch.object(time, "sleep"):
            import pytest
            with pytest.raises(ValueError, match="always fail"):
                decorated()
        assert func.call_count == 3

    def test_single_attempt_no_retry(self):
        func = MagicMock(side_effect=ValueError("fail"))
        decorated = retry(max_attempts=1)(func)
        with patch.object(time, "sleep"):
            import pytest
            with pytest.raises(ValueError):
                decorated()
        func.assert_called_once()

    def test_retryable_exceptions_filter_match(self):
        func = MagicMock(side_effect=ValueError("retry me"))
        decorated = retry(max_attempts=3, retryable_exceptions=(ValueError,))(func)
        with patch.object(time, "sleep"):
            import pytest
            with pytest.raises(ValueError):
                decorated()
        assert func.call_count == 3

    def test_retryable_exceptions_filter_no_match(self):
        func = MagicMock(side_effect=TypeError("not retryable"))
        decorated = retry(max_attempts=3, retryable_exceptions=(ValueError,))(func)
        with patch.object(time, "sleep"):
            import pytest
            with pytest.raises(TypeError, match="not retryable"):
                decorated()
        func.assert_called_once()

    def test_rate_limit_error_uses_retry_after(self):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError(retry_after=0.5)

        decorated = retry(max_attempts=2)(flaky)
        with patch.object(time, "sleep") as mock_sleep:
            result = decorated()
        assert result is None
        assert call_count == 2
        mock_sleep.assert_called_once_with(0.5)

    def test_rate_limit_error_capped_to_max_delay(self):
        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError(retry_after=999.0)

        decorated = retry(max_attempts=2, max_delay=5.0)(flaky)
        with patch.object(time, "sleep") as mock_sleep:
            decorated()
        mock_sleep.assert_called_once_with(5.0)

    def test_on_retry_callback(self):
        callback = MagicMock()
        func = MagicMock(side_effect=[ValueError("fail"), 42])
        decorated = retry(max_attempts=3, retryable_exceptions=(ValueError,), on_retry=callback)(func)
        with patch.object(time, "sleep"):
            result = decorated()
        assert result == 42
        callback.assert_called_once()
        args = callback.call_args[0]
        assert isinstance(args[0], ValueError)
        assert args[1] == 1
        assert args[2] > 0

    def test_exponential_backoff_increases(self):
        delays = []

        def record_delay(*args):
            delays.append(args[2])

        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        decorated = retry(max_attempts=4, base_delay=1.0, backoff=2.0, jitter=False, retryable_exceptions=(ValueError,), on_retry=record_delay)(flaky)
        with patch.object(time, "sleep"):
            import pytest
            with pytest.raises(ValueError):
                decorated()
        assert len(delays) == 3
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 4.0

    def test_max_delay_caps_backoff(self):
        delays = []

        def record_delay(*args):
            delays.append(args[2])

        call_count = 0

        def flaky():
            nonlocal call_count
            call_count += 1
            raise ValueError("fail")

        decorated = retry(max_attempts=5, base_delay=1.0, backoff=4.0, max_delay=10.0, jitter=False, retryable_exceptions=(ValueError,), on_retry=record_delay)(flaky)
        with patch.object(time, "sleep"):
            import pytest
            with pytest.raises(ValueError):
                decorated()
        assert delays == [1.0, 4.0, 10.0, 10.0]

    def test_decorator_preserves_function_metadata(self):
        def my_func(a, b):
            pass

        decorated = retry()(my_func)
        assert decorated.__name__ == "my_func"

    def test_passes_args_and_kwargs(self):
        func = MagicMock(return_value=42)
        decorated = retry(max_attempts=3)(func)
        with patch.object(time, "sleep"):
            result = decorated(1, 2, key="value")
        assert result == 42
        func.assert_called_once_with(1, 2, key="value")

    def test_default_filter_does_not_retry_generic_errors(self):
        """A generic exception must not be retried with the default filter —
        only self-describing rate-limit failures are transient by default.  An
        uncaught ValueError here would otherwise mask a programming error by
        silently hammering the call multiple times."""
        func = MagicMock(side_effect=ValueError("programming bug"))
        decorated = retry(max_attempts=3)(func)
        with patch.object(time, "sleep"):
            import pytest
            with pytest.raises(ValueError, match="programming bug"):
                decorated()
        func.assert_called_once()

    def test_retry_all_sentinel_retries_every_exception(self):
        """Opting into ``RETRY_ALL`` must retry *every* exception — the
        explicit alternative to the conservative default filter."""
        func = MagicMock(side_effect=[ValueError("first"), 42])
        decorated = retry(max_attempts=3, retryable_exceptions=RETRY_ALL)(func)
        with patch.object(time, "sleep"):
            result = decorated()
        assert result == 42
        assert func.call_count == 2
        assert result == 42
