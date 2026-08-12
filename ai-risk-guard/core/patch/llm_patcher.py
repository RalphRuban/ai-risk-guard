"""
LLM-based Patch Generation Engine.
Uses Gemini models via the modern google-genai SDK with fallback chain.
"""

import ast
import os
import random
import re
import time
from typing import Any

from google import genai

from core.cache.gemini_cache import GeminiCache
from core.config import config
from core.llm.gemini_client import (
    _gemini_rate_limited_event,
    _gemini_semaphore,
    _is_rate_limit_error,
    is_rate_limited,  # noqa: F401
    reset_rate_limit_state,  # noqa: F401
)
from core.llm.model_resolver import ModelResolutionError, resolve_gemini_model
from utils.logger import logger


def _backoff_delay(attempt: int, base: float = 2.0, max_delay: float = 30.0) -> float:
    """Exponential backoff with jitter for Gemini retries."""
    delay = min(base * (2 ** attempt), max_delay)
    return delay * random.uniform(0.5, 1.5)


class LLMPatcher:
    """
    Service to generate multiple secure code patch candidates using LLMs.
    Uses a quality-ordered fallback chain of Gemini models with automated zero-cost code sanitization.
    """

    def __init__(self):
        self.gemini_cache = GeminiCache()
        self._fallback_chain = list(config.app.llm.model_fallback_chain)
        self._model_index = 0
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not found. LLM patching will be disabled.", "PATCH")
            self.enabled = False
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=api_key)

                # Stage 2: Resolve model via shared utility with fallback chain
                self.model_id = resolve_gemini_model(self.client, self._fallback_chain)
                self._model_index = self._fallback_chain.index(self.model_id) if self.model_id in self._fallback_chain else 0

                logger.info(f"LLM Patcher active (Model: {self.model_id})", "PATCH")
                self.enabled = True
            except (ModelResolutionError, Exception) as e:
                logger.error(f"LLM Patcher initialization failed: {e}", "PATCH")
                self.enabled = False

    def _sanitize_prompt_code(self, code: str) -> str:
        """Redact credentials and sensitive data before sending code to LLM cloud."""
        sanitized = code
        sanitized = re.sub(r'AKIA[0-9A-Z]{16}', 'REDACTED_AWS_KEY', sanitized)
        sanitized = re.sub(r'(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])', 'REDACTED_SECRET', sanitized)
        sanitized = re.sub(r'ghp_[A-Za-z0-9]{36}', 'REDACTED_GITHUB_TOKEN', sanitized)
        sanitized = re.sub(r'xoxb-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24}', 'REDACTED_SLACK_TOKEN', sanitized)
        sanitized = re.sub(r'xoxp-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32}', 'REDACTED_SLACK_TOKEN', sanitized)
        sanitized = re.sub(
            r'(?i)(secret|password|api_key|token|private_key)\s*[=:]\s*["\'][^"\']{8,}["\']',
            r'\1="REDACTED_VALUE"',
            sanitized
        )
        sanitized = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', 'X.X.X.X', sanitized)
        return sanitized

    def _observe_gemini(self, status: str):
        try:
            from app.metrics import gemini_calls_total
            gemini_calls_total.labels(status=status).inc()
        except ImportError:
            pass

    def _try_next_model(self, prompt: str, gemini_start: float, attempt_start: int = 1) -> str | None:
        """Try the next model in the fallback chain. Returns content or None if all models exhausted."""
        for next_idx in range(self._model_index + 1, len(self._fallback_chain)):
            next_model = self._fallback_chain[next_idx]
            attempt = attempt_start + (next_idx - self._model_index - 1)
            try:
                delay = _backoff_delay(attempt)
                logger.info(f"Waiting {delay:.1f}s before trying {next_model}...", "PATCH")
                time.sleep(delay)
                gemini_start = time.time()
                with _gemini_semaphore:
                    response = self.client.models.generate_content(
                        model=next_model,
                        contents=prompt,
                    )
                content = response.text
                from app.metrics import gemini_latency
                gemini_latency.observe(time.time() - gemini_start)
                self._observe_gemini("success")
                self.model_id = next_model
                self._model_index = next_idx
                logger.info(f"Gemini switched to {next_model}", "PATCH")
                return content
            except Exception as switch_err:
                if _is_rate_limit_error(switch_err):
                    logger.warning(
                        f"Rate limited on {next_model} too, trying next...", "PATCH"
                    )
                    continue
                logger.error(
                    f"Gemini {next_model} failed: {switch_err}", "PATCH"
                )
                self._observe_gemini("failure")
                logger.warning(
                    f"Trying next model after {next_model} failure...", "PATCH"
                )
                continue
        return None

    def generate_candidates(self, code: str, vulnerabilities: list[dict[str, Any]], n: int = 3) -> tuple[list[str], str | None, str | None]:
        """
        Generate N secure variants of the provided code.

        Returns (candidates, prompt, raw_response).
        prompt and raw_response are None on error/fallback paths.
        """
        if not self.enabled or not self.client:
            return ([code], None, None)
        if _gemini_rate_limited_event.is_set():
            logger.warning("Gemini rate limited — skipping LLM patch generation for this scan", "PATCH")
            return ([code], None, None)

        # Sanitize code before passing to cloud prompt (Zero-Cost Privacy Guard)
        sanitized_code = self._sanitize_prompt_code(code)

        # Construct the context-aware prompt
        vuln_descriptions = "\n".join([
            f"- {v['type']} at line {v['line']}: {v['message']}" 
            for v in vulnerabilities
        ])

        prompt = f"""
You are an Expert Security Researcher and Senior Python Engineer.

### CONTEXT
The following Python code contains critical vulnerabilities. Your task is to provide {n} distinct, high-quality remediated versions of this code.

### DETECTED VULNERABILITIES
{vuln_descriptions}

### REMEDIATION REQUIREMENTS
1. FIX ALL: Every variant MUST address all listed vulnerabilities.
2. FUNCTIONAL PARITY: Maintain the original business logic. Do not remove features unless they are fundamentally insecure.
3. SECURITY FIRST:
   - Replace `os.system` with `subprocess.run(..., shell=False)`.
   - Replace `eval`/`exec` with `ast.literal_eval` or safe logical equivalents.
   - Replace `pickle`/`marshal` with `json` or `msgpack`.
    - Move secrets to `os.getenv("KEY", "dummy_default")` with a fallback default value. Never raise an exception for missing environment variables.
   - Replace dynamic SQL strings with parameterized queries (e.g. `execute("...", (param,))`).
   - Sanitize path inputs using `os.path.basename` to prevent path traversal.
   - Validate URL schemes (http/https only) and restrict target hostnames (prevent localhost/internal/cloud metadata) to secure requests.
   - Replace weak cryptographic hash algorithms (MD5, SHA1) with secure alternatives (SHA256).
 4. CODE QUALITY: Use PEP 8 standards. Include robust error handling (try/except) for new security logic.
 5. BLOCKED IMPORTS: Do NOT import or use these modules — they are blocked and will cause validation failure: `socket`, `ctypes`, `multiprocessing`. If the original code requires them, remove the feature instead of importing them.
 6. STRICT OUTPUT: Return ONLY the Python code. No preamble, no explanation text. Do NOT use Markdown code fences or any other formatting.

### FORMAT
Separate the {n} variants using this exact marker on its own line:
---VARIANT_BOUNDARY---

Example output for n=2:

import subprocess
import shlex

def ping_host(host: str):
    validated = shlex.quote(host)
    return subprocess.run(["ping", "-c", "1", validated], check=True)
---VARIANT_BOUNDARY---
import subprocess

def ping_host(host: str):
    if not host.isalnum():
        raise ValueError("Invalid host")
    return subprocess.run(["ping", "-c", "1", host], check=True)

### CODE TO REMEDIATE
```python
{sanitized_code}
```
"""
        cached_response = self.gemini_cache.get(prompt)
        if cached_response is not None:
            self._observe_gemini("cache_hit")
            logger.info("Gemini cache hit — using cached patch candidates", "PATCH")
            content = cached_response
        else:
            try:
                gemini_start = time.time()
                logger.info(f"Prompt size: {len(prompt)} chars ({len(prompt)//4} tokens est.)", "PATCH")
                with _gemini_semaphore:
                    response = self.client.models.generate_content(
                        model=self.model_id,
                        contents=prompt,
                    )
                content = response.text
                from app.metrics import gemini_latency
                gemini_latency.observe(time.time() - gemini_start)
                self._observe_gemini("success")
                logger.info(f"Gemini response received in {time.time() - gemini_start:.1f}s", "PATCH")
            except Exception as first_err:
                if _is_rate_limit_error(first_err):
                    logger.warning(
                        f"Gemini rate limited on {self.model_id}, retrying once: {first_err}", "PATCH"
                    )
                    delay = _backoff_delay(0)
                    time.sleep(delay)
                    try:
                        gemini_start = time.time()
                        with _gemini_semaphore:
                            response = self.client.models.generate_content(
                                model=self.model_id,
                                contents=prompt,
                            )
                        content = response.text
                        from app.metrics import gemini_latency
                        gemini_latency.observe(time.time() - gemini_start)
                        self._observe_gemini("success")
                        logger.info(f"Gemini response received (retry) in {time.time() - gemini_start:.1f}s", "PATCH")
                    except Exception as retry_err:
                        if _is_rate_limit_error(retry_err):
                            logger.warning(
                                f"Rate limited on {self.model_id}, trying next model in chain", "PATCH"
                            )
                            content = self._try_next_model(prompt, gemini_start, attempt_start=1)
                            if content is None:
                                _gemini_rate_limited_event.set()
                                logger.error(
                                    "All Gemini models rate limited — disabling AI for this scan. "
                                    "Try upgrading to a paid plan or wait for quota reset.",
                                    "PATCH"
                                )
                                self._observe_gemini("failure")
                                return ([code], None, None)
                        else:
                            logger.error(
                                f"LLM Patch generation failed on retry: {retry_err}", "PATCH"
                            )
                            self._observe_gemini("failure")
                            return ([code], None, None)
                else:
                    self._observe_gemini("failure")
                    logger.error(f"LLM Patch generation failed: {first_err}", "PATCH")
                    return ([code], None, None)
        
        # Split variants based on boundary markers
        # Try exact marker first, then fuzzy regex matching
        if "---VARIANT_BOUNDARY---" in content:
            variants = content.split("---VARIANT_BOUNDARY---")
        else:
            pattern = r'\n-{3,}\s*[Vv][Aa][Rr][Ii][Aa][Nn][Tt][_\s]?[Bb][Oo][Uu][Nn][Dd][Aa][Rr][Yy]\s*-{3,}\n?'
            variants = re.split(pattern, content)
            if len(variants) <= 1:
                # Try plain dash separator (LLM sometimes uses --- as horizontal rule)
                variants = re.split(r'\n-{3,}\n', content)

        # Clean up Markdown artifacts if LLM included them
        cleaned_candidates = []
        for v in variants:
            cleaned = v.strip()
            if cleaned.startswith("```python"):
                cleaned = cleaned[9:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            cleaned = cleaned.removesuffix("```")
            cleaned = cleaned.strip()
            if cleaned:
                cleaned_candidates.append(cleaned)

        # Validate each candidate with AST parsing to catch malformed LLM output
        valid_candidates = []
        for c in cleaned_candidates:
            try:
                ast.parse(c)
                valid_candidates.append(c)
            except SyntaxError as e:
                logger.warning(f"LLM variant has syntax errors — discarding: {e}", "PATCH")

        if not valid_candidates:
            logger.warning(
                "All LLM variants had syntax errors — using unsplit response as single candidate",
                "PATCH"
            )
            valid_candidates = cleaned_candidates

        logger.info(f"Generated {len(valid_candidates)} patch candidates via LLM", "PATCH")
        return (valid_candidates, prompt, content)
