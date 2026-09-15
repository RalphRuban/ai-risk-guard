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
from google.genai import types

from core.cache.gemini_cache import GeminiCache
from core.config import config
from core.llm.model_resolver import resolve_gemini_model
from utils.logger import logger

# Shared across all LLM features: a hard cap on concurrent Gemini calls and a
# self-healing guard that briefly suppresses follow-up calls after a 429, then
# recovers so a single rate-limit spike does not disable LLM features for the
# whole scan. The event remains for explicit "all models exhausted" breaks.
_gemini_semaphore = threading.Semaphore(2)
_gemini_rate_limited_event = threading.Event()
_gemini_rate_limited_until: float = 0.0


def _mark_rate_limited() -> None:
    global _gemini_rate_limited_until
    _gemini_rate_limited_until = (
        time.monotonic() + config.app.llm.rate_limit_cooldown_seconds
    )
    _gemini_rate_limited_event.set()


def is_rate_limited() -> bool:
    """True while the 429 cooldown is active or an explicit breaker is set."""
    if time.monotonic() < _gemini_rate_limited_until:
        return True
    return _gemini_rate_limited_event.is_set()


def reset_rate_limit_state() -> None:
    """Clear the rate-limit guard (scan start, or after a successful call)."""
    global _gemini_rate_limited_until
    _gemini_rate_limited_until = 0.0
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
        self._light_model_id: str | None = None
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

    @property
    def light_model_id(self) -> str:
        """Resolve the light/cheap model used for non-critical LLM calls.

        Prefers ``config.app.llm.light_model``; falls back to the primary
        quality-ordered chain when the light model is unavailable.
        """
        if self._light_model_id is None and self.client is not None:
            with self._model_lock:
                if self._light_model_id is None:
                    light = config.app.llm.light_model.strip()
                    chain = [light] if light else []
                    chain += [
                        m for m in config.app.llm.model_fallback_chain
                        if m.strip() and m not in chain
                    ]
                    if self._model_id:
                        chain.insert(0, self._model_id)
                    self._light_model_id = resolve_gemini_model(self.client, chain)
        return self._light_model_id or ""

    def _init_client(self) -> None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found — LLM analysis features disabled.", "LLM")
            return
        try:
            # Cap a single Gemini request so one slow model cannot stretch the
            # whole scan (HttpOptions.timeout is in milliseconds).
            timeout_ms = int(config.app.llm.request_timeout_seconds * 1000)
            self._client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(timeout=timeout_ms),
            )
            logger.info("Gemini client initialized for LLM analysis features", "LLM")
        except Exception as e:
            logger.error(f"Gemini client initialization failed: {e}", "LLM")
            self._client = None

    def _request_config(self) -> types.GenerateContentConfig | None:
        """Common generation config (max output tokens) for callers."""
        limited = int(config.app.llm.max_output_tokens)
        if limited <= 0:
            return None
        return types.GenerateContentConfig(max_output_tokens=limited)

    def generate(self, prompt: str, model_id: str | None = None) -> str | None:
        """Run a prompt through the resolved model.

        When *model_id* is given (e.g. the light model for non-critical calls),
        that model is used directly; otherwise the primary quality-ordered
        chain (``model_id``) is used.

        Returns the response text, or ``None`` when the client is unavailable,
        rate-limited, or the call failed (fail-open for callers).
        """
        if not self.enabled or self.client is None:
            return None
        if is_rate_limited():
            logger.warning("Gemini rate limited — skipping LLM call", "LLM")
            return None

        target_model = model_id or self.model_id
        if not target_model:
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
                    model=target_model,
                    contents=prompt,
                    config=self._request_config(),
                )
            content = response.text
            reset_rate_limit_state()
            if gemini_latency is not None:
                gemini_latency.observe(time.time() - gemini_start)
            if gemini_calls_total is not None:
                gemini_calls_total.labels(status="success").inc()
            return content
        except Exception as exc:
            if _is_rate_limit_error(exc):
                _mark_rate_limited()
                logger.warning(
                    f"Gemini rate limited — suppressing follow-up LLM calls for "
                    f"{config.app.llm.rate_limit_cooldown_seconds:.0f}s",
                    "LLM",
                )
            else:
                logger.error(f"Gemini generate failed: {exc}", "LLM")
            if gemini_calls_total is not None:
                gemini_calls_total.labels(status="failure").inc()
            return None

    def cached_generate(self, prompt: str, model_id: str | None = None) -> str | None:
        """Return a cached response for the prompt, else generate and cache it.

        Mirrors the LLM patcher's prompt-hash caching. ``None`` on failure.
        """
        cached = self.cache.get(prompt)
        if cached is not None:
            return cached
        text = self.generate(prompt, model_id=model_id)
        if text is not None:
            self.cache.set(prompt, text)
        return text

    def light_generate(self, prompt: str) -> str | None:
        """Run a non-critical prompt through the light model (falls back to primary)."""
        return self.generate(prompt, model_id=self.light_model_id)

    def cached_light_generate(self, prompt: str) -> str | None:
        """Cached variant of ``light_generate`` for low-cost repeat calls."""
        cached = self.cache.get(prompt)
        if cached is not None:
            return cached
        text = self.light_generate(prompt)
        if text is not None:
            self.cache.set(prompt, text)
        return text
