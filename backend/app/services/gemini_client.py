"""Centralized Google GenAI client and config helpers."""

from __future__ import annotations

from collections.abc import Iterable

from app.core.config import settings


AUTH_ERROR_MARKERS = (
    "401",
    "UNAUTHENTICATED",
    "ACCESS_TOKEN_TYPE_UNSUPPORTED",
    "invalid authentication",
    "API key not valid",
)
QUOTA_ERROR_MARKERS = (
    "429",
    "RESOURCE_EXHAUSTED",
    "quota",
    "Quota",
    "rate limit",
    "RATE_LIMIT",
)


class GeminiConfigurationError(RuntimeError):
    """Raised when Gemini credentials or configured models are not usable."""


def is_gemini_auth_error(exc: BaseException | str) -> bool:
    """Return whether an exception/string is a Gemini auth failure."""
    text = str(exc)
    return any(marker in text for marker in AUTH_ERROR_MARKERS)


def is_gemini_quota_error(exc: BaseException | str) -> bool:
    """Return whether an exception/string is a Gemini quota/rate-limit failure."""
    text = str(exc)
    return any(marker in text for marker in QUOTA_ERROR_MARKERS)


def _normalize_model_name(model_name: str) -> str:
    normalized = model_name.strip()
    if normalized.startswith("models/"):
        normalized = normalized.removeprefix("models/")
    return normalized


def split_gemini_model_names(*raw_values: str) -> list[str]:
    """Parse one or more comma-separated Gemini model settings."""
    models: list[str] = []
    for raw_value in raw_values:
        for item in str(raw_value or "").split(","):
            model_name = _normalize_model_name(item)
            if model_name and model_name not in models:
                models.append(model_name)
    return models


def get_gemini_client():
    """Create a Google GenAI client from configured API credentials."""
    if not settings.effective_gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required to use Gemini.")
    from google import genai

    return genai.Client(api_key=settings.effective_gemini_api_key.strip())


def preflight_gemini_models(model_names: Iterable[str]) -> dict[str, object]:
    """Verify that Gemini auth works and all configured models are visible.

    This intentionally uses the lightweight models metadata endpoint instead
    of ``generate_content`` so a preflight does not consume generation quota.
    """
    requested = split_gemini_model_names(*model_names)
    if not requested:
        return {"ok": True, "available_models": [], "requested_models": [], "missing_models": []}

    try:
        client = get_gemini_client()
        visible_models = {
            _normalize_model_name(str(getattr(model, "name", "") or ""))
            for model in client.models.list()
            if getattr(model, "name", None)
        }
    except Exception as exc:
        if is_gemini_auth_error(exc):
            raise GeminiConfigurationError(
                "Gemini authentication failed. Set GEMINI_API_KEY or GOOGLE_API_KEY to a valid Google AI Studio "
                "API key; do not use an OAuth token, browser cookie, or service-account token."
            ) from exc
        raise GeminiConfigurationError(f"Gemini model preflight failed: {exc}") from exc

    missing = [model_name for model_name in requested if model_name not in visible_models]
    if missing:
        raise GeminiConfigurationError(
            "Configured Gemini model(s) are not available to this API key: "
            f"{', '.join(missing)}. Available examples: {', '.join(sorted(visible_models)[:8])}."
        )

    return {
        "ok": True,
        "requested_models": requested,
        "missing_models": [],
        "available_models": sorted(visible_models),
    }


def _generation_http_options(*, timeout_seconds: int, retry_attempts: int):
    """Return Google GenAI HTTP options with explicit timeout/retry policy."""
    from google.genai import types

    return types.HttpOptions(
        timeout=timeout_seconds * 1000,
        retry_options=types.HttpRetryOptions(attempts=max(1, retry_attempts)),
    )


def generation_http_options():
    """Return document extraction timeout/retry options."""
    return _generation_http_options(timeout_seconds=settings.ai_request_timeout_seconds, retry_attempts=5)


def tutor_generation_http_options():
    """Return low-latency tutor chat timeout/retry options."""
    return _generation_http_options(
        timeout_seconds=settings.gemini_tutor_timeout_seconds,
        retry_attempts=settings.gemini_tutor_retry_attempts,
    )


def semantic_helper_http_options():
    """Return low-latency semantic helper timeout/retry options."""
    return _generation_http_options(
        timeout_seconds=settings.gemini_semantic_helper_timeout_seconds,
        retry_attempts=settings.gemini_semantic_helper_retry_attempts,
    )


def document_generation_config(response_schema):
    """Return structured-output config for document extraction."""
    from google.genai import types

    return types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_schema,
        http_options=generation_http_options(),
        temperature=0.0,
        max_output_tokens=8192,
    )


def tutor_generation_config(system_prompt: str, *, temperature: float = 0.4, max_output_tokens: int = 1024):
    """Return config for normal tutor answer generation."""
    from google.genai import types

    return types.GenerateContentConfig(
        http_options=tutor_generation_http_options(),
        system_instruction=system_prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


def embedding_config(task_type: str):
    """Return Gemini embedding config for document/query vectors."""
    from google.genai import types

    return types.EmbedContentConfig(task_type=task_type, output_dimensionality=768)
