"""
core/llm/gemini_client.py

Shared Gemini wrapper used by all LLM-backed analysis features (patch
generation, triage, explanations, PR summaries).

Owns the process-wide rate-limit state and concurrency semaphore so every LLM
feature throttles together, and exposes a fail-open ``generate`` that returns
``None`` whenever the model is unavailable or rate-limited — callers must fall
back to their deterministic behavior in that case.
"""

import os
import threading
import time
from typing import Any

from google import genai

from core.cache.gemini_cache import GeminiCache
from core.config import config
from core.llm.model_resolver import resolve_gemini_model
from utils.logger import logger

# Shared across all LLM features: a hard cap on concurrent Gemini calls and a
# circuit breaker set when the API reports rate limiting.
_gemini_semaphore = threading.Semaphore(2)
_gemini_rate_limited_event = threading.Event()


def is_rate_limited() -> bool:
    """Return True when Gemini rate limiting has tripped the circuit breaker."""
    return _gemini_rate_limited_event.is_set()


def reset_rate_limit_state() -> None:
    """Clear the rate-limit circuit breaker (called at the start of each scan)."""
    _gemini_rate_limited_event.clear()


def _is_rate_limit_error(exc: Exception) -> bool:
    """Check if an exception indicates a Gemini API rate limit or quota exhaustion."""
    exc_str = str(exc).lower()
    return any(
        s in exc_str
        for s in ("429", "rate limit", "quota", "resource exhausted", "too many requests")
    )


class GeminiClient:
    """Lazily initialized Gemini client with rate-limit handling and caching."""

    def __init__(self):
        self._client: genai.Client | None = None
        self._model_id: str | None = None
        self._model_lock = threading.Lock()
        self.cache = GeminiCache()

    @property
    def enabled(self) -> bool:
        """True when a usable Gemini client/model is available."""
        return self.client is not None

    @property
    def client(self) -> genai.Client | None:
        if self._client is None:
            self._init_client()
        return self._client

    @property
    def model_id(self) -> str:
        if self._model_id is None and self.client is not None:
            with self._model_lock:
                if self._model_id is None:
                    self._model_id = resolve_gemini_model(
                        self.client, list(config.app.llm.model_fallback_chain)
                    )
        return self._model_id or ""

    def _init_client(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found — LLM analysis features disabled.", "LLM")
            return
        try:
            self._client = genai.Client(api_key=api_key)
            logger.info("Gemini client initialized for LLM analysis features", "LLM")
        except Exception as e:
            logger.error(f"Gemini client initialization failed: {e}", "LLM")
            self._client = None

    def generate(self, prompt: str) -> str | None:
        """Run a prompt through the resolved model.

        Returns the response text, or ``None`` when the client is unavailable,
        rate-limited, or the call failed (fail-open for callers).
        """
        if not self.enabled or self.client is None:
            return None
        if is_rate_limited():
            logger.warning("Gemini rate limited — skipping LLM call", "LLM")
            return None

        gemini_calls_total: Any | None = None
        gemini_latency: Any | None = None
        try:
            from app.metrics import gemini_calls_total as _gemini_calls_total
            from app.metrics import gemini_latency as _gemini_latency
            gemini_calls_total = _gemini_calls_total
            gemini_latency = _gemini_latency
        except ImportError:
            pass

        try:
            gemini_start = time.time()
            with _gemini_semaphore:
                response = self.client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                )
            content = response.text
            if gemini_latency is not None:
                gemini_latency.observe(time.time() - gemini_start)
            if gemini_calls_total is not None:
                gemini_calls_total.labels(status="success").inc()
            return content
        except Exception as exc:
            if _is_rate_limit_error(exc):
                _gemini_rate_limited_event.set()
                logger.error("Gemini rate limited — disabling LLM features for this scan", "LLM")
            else:
                logger.error(f"Gemini generate failed: {exc}", "LLM")
            if gemini_calls_total is not None:
                gemini_calls_total.labels(status="failure").inc()
            return None

    def cached_generate(self, prompt: str) -> str | None:
        """Return a cached response for the prompt, else generate and cache it.

        Mirror of the LLM patcher's prompt-hash caching. ``None`` on failure.
        """
        cached = self.cache.get(prompt)
        if cached is not None:
            return cached
        text = self.generate(prompt)
        if text is not None:
            self.cache.set(prompt, text)
        return text
