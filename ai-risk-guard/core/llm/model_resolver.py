"""
Shared Gemini model discovery utility.
Validates models from a quality-ordered fallback chain, returning the first available.
"""

from google import genai

from utils.logger import logger

FALLBACK_CHAIN = [
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]


class ModelResolutionError(Exception):
    """Raised when no usable Gemini model can be found."""


def resolve_gemini_model(client: genai.Client, fallback_chain: list[str] | None = None) -> str:
    """
    Resolve a usable Gemini model ID from an ordered fallback chain.

    Iterates the chain in order and returns the first model that validates
    via ``client.models.get()``. Raises ``ModelResolutionError`` if none
    are available.

    Args:
        client: An authenticated ``google.genai.Client`` instance.
        fallback_chain: Ordered list of model IDs to try (best first).

    Returns:
        A valid model ID string (e.g. ``"gemini-2.0-flash"``).

    Raises:
        ModelResolutionError: If no model could be validated.
    """
    if fallback_chain is None:
        fallback_chain = FALLBACK_CHAIN

    for model_id in fallback_chain:
        try:
            client.models.get(model=model_id)
            logger.info(f"Gemini model validated: {model_id}", "LLM")
            return model_id
        except Exception:
            logger.info(f"Gemini model {model_id} not available, trying next...", "LLM")
            continue

    raise ModelResolutionError(
        f"No Gemini model available from chain: {fallback_chain}"
    )
